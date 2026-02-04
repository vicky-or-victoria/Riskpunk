# utils/database.py
# PostgreSQL/Neon Database Layer
import asyncpg
import os
from typing import Optional

# Database connection from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Connection pool
_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the database connection pool"""
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL not set. Get your Neon PostgreSQL connection string "
                "from https://neon.tech and set it as an environment variable."
            )
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
    return _pool


async def close_pool():
    """Close the database connection pool"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def init_db():
    """Initialize database tables"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # ── Players ──────────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id          SERIAL PRIMARY KEY,
                discord_id  BIGINT UNIQUE NOT NULL,
                name        TEXT    NOT NULL DEFAULT 'Drifter',
                credits     NUMERIC(15, 2) NOT NULL DEFAULT 5000,
                rep         INTEGER NOT NULL DEFAULT 0,
                level       INTEGER NOT NULL DEFAULT 1,
                xp          INTEGER NOT NULL DEFAULT 0,
                faction_id  INTEGER,
                hp          INTEGER NOT NULL DEFAULT 100,
                max_hp      INTEGER NOT NULL DEFAULT 100,
                atk         INTEGER NOT NULL DEFAULT 10,
                def         INTEGER NOT NULL DEFAULT 5,
                spd         INTEGER NOT NULL DEFAULT 8,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_players_discord_id ON players(discord_id)")

        # ── Implants ─────────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS implants (
                id          SERIAL PRIMARY KEY,
                player_id   INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                implant_key TEXT    NOT NULL,
                slot        TEXT    NOT NULL,
                installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_id, slot)
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_implants_player_id ON implants(player_id)")

        # ── Factions ─────────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS factions (
                id          SERIAL PRIMARY KEY,
                key         TEXT    UNIQUE NOT NULL,
                name        TEXT    NOT NULL,
                description TEXT,
                color       TEXT    NOT NULL DEFAULT '#ff0000',
                war_target  INTEGER,
                aggression  INTEGER NOT NULL DEFAULT 50
            )
        """)

        # ── Faction Wars ─────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS faction_wars (
                id          SERIAL PRIMARY KEY,
                faction_a   INTEGER NOT NULL REFERENCES factions(id),
                faction_b   INTEGER NOT NULL REFERENCES factions(id),
                started_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at    TIMESTAMP,
                winner      INTEGER REFERENCES factions(id)
            )
        """)

        # ── Territories ──────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS territories (
                id          SERIAL PRIMARY KEY,
                key         TEXT    UNIQUE NOT NULL,
                name        TEXT    NOT NULL,
                description TEXT,
                owner_faction INTEGER REFERENCES factions(id),
                income      NUMERIC(10, 2) NOT NULL DEFAULT 200,
                defense     INTEGER NOT NULL DEFAULT 50
            )
        """)

        # ── Active Trades ───────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id          SERIAL PRIMARY KEY,
                seller_id   INTEGER NOT NULL REFERENCES players(id),
                buyer_id    INTEGER REFERENCES players(id),
                item_name   TEXT    NOT NULL,
                quantity    INTEGER NOT NULL DEFAULT 1,
                price       NUMERIC(15, 2) NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'open',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")

        # ── Inventory ────────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id          SERIAL PRIMARY KEY,
                player_id   INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                item_name   TEXT    NOT NULL,
                quantity    INTEGER NOT NULL DEFAULT 1,
                UNIQUE(player_id, item_name)
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_inventory_player_id ON inventory(player_id)")

        # ── Skill Trees ──────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id          SERIAL PRIMARY KEY,
                player_id   INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                skill_key   TEXT    NOT NULL,
                level       INTEGER NOT NULL DEFAULT 1,
                UNIQUE(player_id, skill_key)
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_skills_player_id ON skills(player_id)")

        # ── Active Heists ───────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS heists (
                id          SERIAL PRIMARY KEY,
                leader_id   INTEGER NOT NULL REFERENCES players(id),
                target      TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'recruiting',
                reward      NUMERIC(15, 2) NOT NULL DEFAULT 10000,
                difficulty  INTEGER NOT NULL DEFAULT 5,
                crew        TEXT    NOT NULL DEFAULT '',
                phase       TEXT    NOT NULL DEFAULT 'planning',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_heists_status ON heists(status)")

        # ── Story Progress ───────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS story_progress (
                id          SERIAL PRIMARY KEY,
                player_id   INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                chapter     INTEGER NOT NULL DEFAULT 1,
                node        TEXT    NOT NULL DEFAULT 'start',
                choices     TEXT    NOT NULL DEFAULT '',
                UNIQUE(player_id)
            )
        """)

        # ── Random Events Log ────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS event_log (
                id          SERIAL PRIMARY KEY,
                event_key   TEXT    NOT NULL,
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved    INTEGER NOT NULL DEFAULT 0
            )
        """)

        # ── PvP Match Log ────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pvp_log (
                id          SERIAL PRIMARY KEY,
                p1_id       INTEGER NOT NULL REFERENCES players(id),
                p2_id       INTEGER NOT NULL REFERENCES players(id),
                winner_id   INTEGER REFERENCES players(id),
                rounds      INTEGER NOT NULL DEFAULT 0,
                log_text    TEXT,
                fought_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── Companies ────────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id                  SERIAL PRIMARY KEY,
                owner_id            INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                company_type        TEXT NOT NULL,
                name                TEXT NOT NULL,
                stockpiled_minutes  NUMERIC(15, 2) NOT NULL DEFAULT 0,
                total_invested      NUMERIC(15, 2) NOT NULL DEFAULT 0,
                total_earned        NUMERIC(15, 2) NOT NULL DEFAULT 0,
                last_collect        TIMESTAMP NOT NULL DEFAULT NOW(),
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_companies_owner ON companies(owner_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_companies_type ON companies(company_type)")


# ─── Player Helpers ─────────────────────────────────────────────────────────

async def get_player(discord_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM players WHERE discord_id = $1", discord_id)


async def get_player_by_id(player_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM players WHERE id = $1", player_id)


async def ensure_player(discord_id: int, name: str = "Drifter"):
    player = await get_player(discord_id)
    if player:
        return player
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "INSERT INTO players (discord_id, name) VALUES ($1, $2) RETURNING *",
            discord_id, name
        )


async def update_player_credits(player_id: int, amount: float):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET credits = credits + $1 WHERE id = $2",
            amount, player_id
        )


async def update_player_stats(player_id: int, hp: int = None, atk: int = None, def_: int = None, spd: int = None):
    pool = await get_pool()
    updates = []
    params = []
    param_count = 1
    
    if hp is not None:
        updates.append(f"hp = ${param_count}")
        params.append(hp)
        param_count += 1
    if atk is not None:
        updates.append(f"atk = ${param_count}")
        params.append(atk)
        param_count += 1
    if def_ is not None:
        updates.append(f"def = ${param_count}")
        params.append(def_)
        param_count += 1
    if spd is not None:
        updates.append(f"spd = ${param_count}")
        params.append(spd)
        param_count += 1
    
    if updates:
        params.append(player_id)
        query = f"UPDATE players SET {', '.join(updates)} WHERE id = ${param_count}"
        async with pool.acquire() as conn:
            await conn.execute(query, *params)


async def update_player_xp(player_id: int, xp_gain: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        player = await conn.fetchrow(
            "UPDATE players SET xp = xp + $1 WHERE id = $2 RETURNING xp, level",
            xp_gain, player_id
        )
        new_xp = player['xp']
        level = player['level']
        xp_needed = level * 1000
        if new_xp >= xp_needed:
            await conn.execute(
                "UPDATE players SET level = level + 1, xp = $1 WHERE id = $2",
                new_xp - xp_needed, player_id
            )
            return True
        return False


async def update_player_rep(player_id: int, rep_change: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET rep = rep + $1 WHERE id = $2",
            rep_change, player_id
        )


async def heal_player(player_id: int, amount: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET hp = LEAST(hp + $1, max_hp) WHERE id = $2",
            amount, player_id
        )


async def update_player_hp(discord_id: int, hp_change: int):
    """Update player HP by discord_id (can be positive or negative)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET hp = GREATEST(0, LEAST(hp + $1, max_hp)) WHERE discord_id = $2",
            hp_change, discord_id
        )


async def set_player_faction(player_id: int, faction_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET faction_id = $1 WHERE id = $2",
            faction_id, player_id
        )


# ─── Implant Helpers ────────────────────────────────────────────────────────

async def get_player_implants(player_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM implants WHERE player_id = $1", player_id)


async def install_implant(player_id: int, implant_key: str, slot: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """INSERT INTO implants (player_id, implant_key, slot) 
               VALUES ($1, $2, $3) 
               ON CONFLICT (player_id, slot) DO UPDATE 
               SET implant_key = $2, installed_at = CURRENT_TIMESTAMP 
               RETURNING *""",
            player_id, implant_key, slot
        )


async def remove_implant(player_id: int, slot: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM implants WHERE player_id = $1 AND slot = $2",
            player_id, slot
        )


# ─── Faction Helpers ────────────────────────────────────────────────────────

async def get_all_factions():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM factions ORDER BY id")


async def get_faction(faction_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM factions WHERE id = $1", faction_id)


async def get_faction_by_key(key: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM factions WHERE key = $1", key)


async def get_faction_members(faction_id: int):
    """Get all players belonging to a faction"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM players WHERE faction_id = $1", faction_id)


async def set_faction_war(faction_id: int, target_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE factions SET war_target = $1 WHERE id = $2",
            target_id, faction_id
        )


async def create_faction_war(faction_a: int, faction_b: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "INSERT INTO faction_wars (faction_a, faction_b) VALUES ($1, $2) RETURNING *",
            faction_a, faction_b
        )


async def declare_war(faction_a: int, faction_b: int):
    """Alias for create_faction_war for compatibility"""
    return await create_faction_war(faction_a, faction_b)


async def resolve_war(war_id: int, winner_id: int):
    """End a war and declare a winner"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE faction_wars SET ended_at = CURRENT_TIMESTAMP, winner = $1 WHERE id = $2",
            winner_id, war_id
        )


async def get_active_wars():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM faction_wars WHERE ended_at IS NULL")


async def end_faction_war(war_id: int, winner_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE faction_wars SET ended_at = CURRENT_TIMESTAMP, winner = $1 WHERE id = $2",
            winner_id, war_id
        )


# ─── Territory Helpers ──────────────────────────────────────────────────────

async def get_all_territories():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM territories ORDER BY id")


async def get_territory_by_key(key: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM territories WHERE key = $1", key)


async def get_territory(territory_id: int):
    """Get territory by ID"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM territories WHERE id = $1", territory_id)


async def claim_territory(territory_key: str, faction_id: int):
    """Claim a territory for a faction"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE territories SET owner_faction = $1 WHERE key = $2",
            faction_id, territory_key
        )


async def damage_territory(territory_id: int, damage: int):
    """Reduce territory defense"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE territories SET defense = GREATEST(0, defense - $1) WHERE id = $2",
            damage, territory_id
        )


async def set_territory_owner(territory_id: int, faction_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE territories SET owner_faction = $1 WHERE id = $2",
            faction_id, territory_id
        )


async def fortify_territory(territory_id: int, defense_boost: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE territories SET defense = defense + $1 WHERE id = $2",
            defense_boost, territory_id
        )


# ─── Trading Helpers ────────────────────────────────────────────────────────

async def create_trade(seller_id: int, item_name: str, quantity: int, price: float):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "INSERT INTO trades (seller_id, item_name, quantity, price) VALUES ($1, $2, $3, $4) RETURNING *",
            seller_id, item_name, quantity, price
        )


async def get_open_trades():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM trades WHERE status = 'open' ORDER BY created_at DESC LIMIT 25")


async def fulfill_trade(trade_id: int, buyer_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE trades SET status = 'fulfilled', buyer_id = $1 WHERE id = $2",
            buyer_id, trade_id
        )


async def cancel_trade(trade_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE trades SET status = 'cancelled' WHERE id = $1", trade_id)


# ─── Inventory Helpers ───────────────────────────────────────────────────────

async def get_inventory(player_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM inventory WHERE player_id = $1", player_id)


async def add_item(player_id: int, item_name: str, qty: int = 1):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO inventory (player_id, item_name, quantity)
               VALUES ($1, $2, $3)
               ON CONFLICT(player_id, item_name) DO UPDATE 
               SET quantity = inventory.quantity + $3""",
            player_id, item_name, qty
        )


async def remove_item(player_id: int, item_name: str, qty: int = 1) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT quantity FROM inventory WHERE player_id = $1 AND item_name = $2",
            player_id, item_name
        )
        if not row or row['quantity'] < qty:
            return False
        if row['quantity'] == qty:
            await conn.execute(
                "DELETE FROM inventory WHERE player_id = $1 AND item_name = $2",
                player_id, item_name
            )
        else:
            await conn.execute(
                "UPDATE inventory SET quantity = quantity - $1 WHERE player_id = $2 AND item_name = $3",
                qty, player_id, item_name
            )
        return True


# ─── Skill Helpers ───────────────────────────────────────────────────────────

async def get_player_skills(player_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM skills WHERE player_id = $1", player_id)


async def get_skill(player_id: int, skill_key: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM skills WHERE player_id = $1 AND skill_key = $2",
            player_id, skill_key
        )


async def set_skill(player_id: int, skill_key: str, level: int = 1):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO skills (player_id, skill_key, level)
               VALUES ($1, $2, $3)
               ON CONFLICT(player_id, skill_key) DO UPDATE SET level = $3""",
            player_id, skill_key, level
        )


# ─── Heist Helpers ───────────────────────────────────────────────────────────

async def create_heist(leader_id: int, target: str, reward: float, difficulty: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "INSERT INTO heists (leader_id, target, reward, difficulty, crew) VALUES ($1, $2, $3, $4, $5) RETURNING *",
            leader_id, target, reward, difficulty, str(leader_id)
        )


async def get_heist(heist_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM heists WHERE id = $1", heist_id)


async def get_active_heists():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM heists WHERE status IN ('recruiting', 'planning', 'active')")


async def join_heist(heist_id: int, player_id: int):
    heist = await get_heist(heist_id)
    if not heist:
        return False
    crew_ids = [int(x) for x in heist['crew'].split(",") if x]
    if player_id in crew_ids:
        return False
    crew_ids.append(player_id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE heists SET crew = $1 WHERE id = $2",
            ",".join(str(x) for x in crew_ids), heist_id
        )
    return True


async def advance_heist_phase(heist_id: int, new_phase: str, new_status: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if new_status:
            await conn.execute(
                "UPDATE heists SET phase = $1, status = $2 WHERE id = $3",
                new_phase, new_status, heist_id
            )
        else:
            await conn.execute(
                "UPDATE heists SET phase = $1 WHERE id = $2",
                new_phase, heist_id
            )


# ─── Story Helpers ───────────────────────────────────────────────────────────

async def get_story_progress(player_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM story_progress WHERE player_id = $1", player_id)


async def set_story_progress(player_id: int, chapter: int, node: str, choice: str = ""):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT choices FROM story_progress WHERE player_id = $1", player_id)
        if row:
            old = row['choices']
            new_choices = f"{old},{choice}" if choice else old
            await conn.execute(
                "UPDATE story_progress SET chapter = $1, node = $2, choices = $3 WHERE player_id = $4",
                chapter, node, new_choices, player_id
            )
        else:
            await conn.execute(
                "INSERT INTO story_progress (player_id, chapter, node, choices) VALUES ($1, $2, $3, $4)",
                player_id, chapter, node, choice
            )


# ─── Leaderboard ─────────────────────────────────────────────────────────────

async def get_leaderboard(sort_by: str = "credits", limit: int = 10):
    col = sort_by if sort_by in ("credits", "level", "rep") else "credits"
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            f"SELECT * FROM players ORDER BY {col} DESC LIMIT $1", limit
        )


# ─── Event Log ───────────────────────────────────────────────────────────────

async def log_event(event_key: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO event_log (event_key) VALUES ($1)", event_key)


# ─── PvP Log ─────────────────────────────────────────────────────────────────

async def log_pvp(p1_id: int, p2_id: int, winner_id: int, rounds: int, log_text: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO pvp_log (p1_id, p2_id, winner_id, rounds, log_text) VALUES ($1, $2, $3, $4, $5)",
            p1_id, p2_id, winner_id, rounds, log_text
        )
