# utils/database.py
# PostgreSQL/Neon Database Layer - ENHANCED VERSION with Companies & Guild Settings
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
    """Initialize database tables - ENHANCED VERSION with Companies & Guild Settings"""
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

        # ── Territories - ENHANCED ───────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS territories (
                id              SERIAL PRIMARY KEY,
                key             TEXT    UNIQUE NOT NULL,
                name            TEXT    NOT NULL,
                description     TEXT,
                owner_faction   INTEGER REFERENCES factions(id),
                income          NUMERIC(10, 2) NOT NULL DEFAULT 200,
                defense         INTEGER NOT NULL DEFAULT 50,
                last_attacked   TIMESTAMP,
                garrison_size   INTEGER DEFAULT 0,
                connected_to    TEXT
            )
        """)

        # ── Siege History - NEW ──────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS siege_history (
                id                  SERIAL PRIMARY KEY,
                territory_key       TEXT    NOT NULL,
                attacker_faction    INTEGER REFERENCES factions(id),
                defender_faction    INTEGER REFERENCES factions(id),
                started_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at            TIMESTAMP,
                result              TEXT,
                total_cost          NUMERIC(15, 2),
                participants        TEXT[]
            )
        """)

        # ── Combat Log - NEW ─────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS combat_log (
                id              SERIAL PRIMARY KEY,
                player_id       INTEGER REFERENCES players(id),
                action_type     TEXT    NOT NULL,
                territory_key   TEXT    NOT NULL,
                result          TEXT    NOT NULL,
                credits_spent   NUMERIC(15, 2),
                credits_gained  NUMERIC(15, 2),
                xp_gained       INTEGER,
                hp_lost         INTEGER,
                timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_combat_log_player ON combat_log(player_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_combat_log_timestamp ON combat_log(timestamp)")

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
        
        # ── Equipped Items ───────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS equipped_items (
                id          SERIAL PRIMARY KEY,
                player_id   INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                item_name   TEXT    NOT NULL,
                slot        TEXT    NOT NULL,
                UNIQUE(player_id, slot)
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_equipped_player_id ON equipped_items(player_id)")

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

        # ── PvP Rankings ────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pvp_stats (
                id          SERIAL PRIMARY KEY,
                player_id   INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                wins        INTEGER NOT NULL DEFAULT 0,
                losses      INTEGER NOT NULL DEFAULT 0,
                elo         INTEGER NOT NULL DEFAULT 1000,
                UNIQUE(player_id)
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_pvp_stats_elo ON pvp_stats(elo DESC)")

        # ── Companies ────────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id                  SERIAL PRIMARY KEY,
                owner_id            INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                company_type        TEXT    NOT NULL,
                name                TEXT    NOT NULL,
                last_collect        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                stockpiled_minutes  NUMERIC(15, 2) NOT NULL DEFAULT 0,
                total_earned        NUMERIC(15, 2) NOT NULL DEFAULT 0,
                total_invested      NUMERIC(15, 2) NOT NULL DEFAULT 0,
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_companies_owner ON companies(owner_id)")
        
        # ── Guild Settings ───────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                id              SERIAL PRIMARY KEY,
                guild_id        BIGINT UNIQUE NOT NULL,
                company_limit   INTEGER NOT NULL DEFAULT 3,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_guild_settings_guild_id ON guild_settings(guild_id)")


# ═══════════════════════════════════════════════════════════════════════════
# PLAYER HELPERS
# ═══════════════════════════════════════════════════════════════════════════

async def ensure_player(discord_id: int, name: str = "Drifter"):
    """Creates a player if not exists; always returns player row."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM players WHERE discord_id = $1", discord_id)
        if row:
            return row
        return await conn.fetchrow(
            "INSERT INTO players (discord_id, name) VALUES ($1, $2) RETURNING *",
            discord_id, name
        )


async def get_player(discord_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM players WHERE discord_id = $1", discord_id)


async def get_player_by_id(player_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM players WHERE id = $1", player_id)


async def update_player_credits(discord_id: int, delta: float):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET credits = GREATEST(0, credits + $1) WHERE discord_id = $2",
            delta, discord_id
        )


async def update_player_xp(discord_id: int, delta: int):
    """Updates XP, auto-level-ups if needed. Returns new level."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE discord_id = $1", discord_id)
        if not player:
            return 1
        new_xp = player['xp'] + delta
        new_level = player['level']
        threshold = new_level * 500
        while new_xp >= threshold:
            new_level += 1
            new_xp -= threshold
            threshold = new_level * 500
        await conn.execute(
            "UPDATE players SET xp = $1, level = $2 WHERE discord_id = $3",
            new_xp, new_level, discord_id
        )
        return new_level


async def update_player_hp(discord_id: int, delta: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE discord_id = $1", discord_id)
        if not player:
            return
        new_hp = max(0, min(player['max_hp'], player['hp'] + delta))
        await conn.execute("UPDATE players SET hp = $1 WHERE discord_id = $2", new_hp, discord_id)


async def set_hp_absolute(discord_id: int, hp: int):
    """Set player HP to an absolute value (for PvP results)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        player = await conn.fetchrow("SELECT max_hp FROM players WHERE discord_id = $1", discord_id)
        if not player:
            return
        # Clamp HP between 0 and max_hp
        safe_hp = max(0, min(player['max_hp'], hp))
        await conn.execute("UPDATE players SET hp = $1 WHERE discord_id = $2", safe_hp, discord_id)


async def update_player_stats(player_id: int, atk: int = 0, defense: int = 0, spd: int = 0):
    """Increase player combat stats"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET atk = atk + $1, def = def + $2, spd = spd + $3 WHERE id = $4",
            atk, defense, spd, player_id
        )


# ═══════════════════════════════════════════════════════════════════════════
# FACTION HELPERS
# ═══════════════════════════════════════════════════════════════════════════

async def get_faction(faction_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM factions WHERE id = $1", faction_id)


async def get_faction_by_key(key: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM factions WHERE key = $1", key.lower())


async def get_all_factions():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM factions")


async def get_faction_members(faction_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM players WHERE faction_id = $1", faction_id)


async def join_faction(discord_id: int, faction_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET faction_id = $1 WHERE discord_id = $2", faction_id, discord_id)


async def leave_faction(discord_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET faction_id = NULL WHERE discord_id = $1", discord_id)


async def set_player_faction(discord_id: int, faction_id: int):
    """Set player's faction (alias for join_faction for compatibility)"""
    await join_faction(discord_id, faction_id)


# ═══════════════════════════════════════════════════════════════════════════
# FACTION WAR HELPERS
# ═══════════════════════════════════════════════════════════════════════════

async def declare_war(faction_a: int, faction_b: int):
    """Declare war between two factions"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """INSERT INTO faction_wars (faction_a, faction_b, started_at)
               VALUES ($1, $2, CURRENT_TIMESTAMP)
               RETURNING *""",
            faction_a, faction_b
        )


async def get_active_wars():
    """Get all active faction wars"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM faction_wars WHERE ended_at IS NULL"
        )


async def resolve_war(war_id: int, winner_faction_id: int):
    """Mark a war as ended with a winner"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE faction_wars 
               SET ended_at = CURRENT_TIMESTAMP, winner = $1
               WHERE id = $2""",
            winner_faction_id, war_id
        )


async def claim_territory(territory_key: str, faction_id: int):
    """Claim/capture a territory for a faction (simplified version)"""
    await capture_territory(territory_key, faction_id, new_defense=50)


# ═══════════════════════════════════════════════════════════════════════════
# TERRITORY HELPERS - ENHANCED
# ═══════════════════════════════════════════════════════════════════════════

async def get_all_territories():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM territories")


async def get_territory(key: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM territories WHERE key = $1", key.lower())


async def get_faction_territories(faction_id: int):
    """Get all territories owned by a faction"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM territories WHERE owner_faction = $1", faction_id)


async def capture_territory(territory_key: str, faction_id: int, new_defense: int = 30):
    """Capture a territory and set new defense value"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE territories 
               SET owner_faction = $1, defense = $2, last_attacked = CURRENT_TIMESTAMP 
               WHERE key = $3""",
            faction_id, new_defense, territory_key.lower()
        )


async def fortify_territory(territory_key: str, defense_increase: int):
    """Increase territory defense (max 100)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE territories SET defense = LEAST(100, defense + $1) WHERE key = $2",
            defense_increase, territory_key.lower()
        )


async def weaken_territory(territory_key: str, defense_decrease: int):
    """Decrease territory defense (min 0)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE territories SET defense = GREATEST(0, defense - $1) WHERE key = $2",
            defense_decrease, territory_key.lower()
        )


async def update_territory_garrison(territory_key: str, garrison_size: int):
    """Update garrison size for a territory"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE territories SET garrison_size = $1 WHERE key = $2",
            garrison_size, territory_key.lower()
        )


# ═══════════════════════════════════════════════════════════════════════════
# COMBAT LOG HELPERS - NEW
# ═══════════════════════════════════════════════════════════════════════════

async def log_combat(player_id: int, action_type: str, territory_key: str, result: str, 
                     credits_spent: float = 0, credits_gained: float = 0, 
                     xp_gained: int = 0, hp_lost: int = 0):
    """Log combat action for statistics and history"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO combat_log 
               (player_id, action_type, territory_key, result, credits_spent, credits_gained, xp_gained, hp_lost)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            player_id, action_type, territory_key, result, credits_spent, credits_gained, xp_gained, hp_lost
        )


async def get_player_combat_history(player_id: int, limit: int = 10):
    """Get recent combat history for a player"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM combat_log WHERE player_id = $1 ORDER BY timestamp DESC LIMIT $2",
            player_id, limit
        )


async def get_territory_combat_history(territory_key: str, limit: int = 10):
    """Get recent combat history for a territory"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM combat_log WHERE territory_key = $1 ORDER BY timestamp DESC LIMIT $2",
            territory_key, limit
        )


# ═══════════════════════════════════════════════════════════════════════════
# SIEGE HELPERS - NEW
# ═══════════════════════════════════════════════════════════════════════════

async def start_siege(territory_key: str, attacker_faction: int, defender_faction: int):
    """Record the start of a siege"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """INSERT INTO siege_history 
               (territory_key, attacker_faction, defender_faction, started_at)
               VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
               RETURNING *""",
            territory_key, attacker_faction, defender_faction
        )


async def end_siege(siege_id: int, result: str, total_cost: float):
    """Record the end of a siege"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE siege_history 
               SET ended_at = CURRENT_TIMESTAMP, result = $1, total_cost = $2
               WHERE id = $3""",
            result, total_cost, siege_id
        )


async def get_active_sieges():
    """Get all currently active sieges"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM siege_history WHERE ended_at IS NULL"
        )


async def get_siege_history(territory_key: str, limit: int = 5):
    """Get recent siege history for a territory"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            """SELECT * FROM siege_history 
               WHERE territory_key = $1 
               ORDER BY started_at DESC 
               LIMIT $2""",
            territory_key, limit
        )


# ═══════════════════════════════════════════════════════════════════════════
# IMPLANT HELPERS
# ═══════════════════════════════════════════════════════════════════════════

async def get_player_implants(player_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM implants WHERE player_id = $1", player_id)


async def install_implant(player_id: int, implant_key: str, slot: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO implants (player_id, implant_key, slot)
               VALUES ($1, $2, $3)
               ON CONFLICT(player_id, slot) DO UPDATE SET implant_key = $2""",
            player_id, implant_key, slot
        )


async def remove_implant(player_id: int, slot: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM implants WHERE player_id = $1 AND slot = $2",
            player_id, slot
        )


# ═══════════════════════════════════════════════════════════════════════════
# TRADE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

async def create_trade(seller_id: int, item_name: str, quantity: int, price: float):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "INSERT INTO trades (seller_id, item_name, quantity, price) VALUES ($1, $2, $3, $4) RETURNING *",
            seller_id, item_name, quantity, price
        )


async def get_open_trades(limit: int = 20):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM trades WHERE status = 'open' ORDER BY created_at DESC LIMIT $1",
            limit
        )


async def get_trade(trade_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM trades WHERE id = $1", trade_id)


async def complete_trade(trade_id: int, buyer_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE trades SET status = 'completed', buyer_id = $1 WHERE id = $2",
            buyer_id, trade_id
        )


async def cancel_trade(trade_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM trades WHERE id = $1", trade_id)


async def fulfill_trade(trade_id: int, buyer_id: int):
    """Fulfill/complete a trade (alias for complete_trade for compatibility)"""
    await complete_trade(trade_id, buyer_id)


# ═══════════════════════════════════════════════════════════════════════════
# INVENTORY HELPERS
# ═══════════════════════════════════════════════════════════════════════════

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
    """Remove qty of item from inventory; returns False if not enough."""
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


# ═══════════════════════════════════════════════════════════════════════════
# EQUIPMENT HELPERS
# ═══════════════════════════════════════════════════════════════════════════

async def get_equipped_items(player_id: int):
    """Get all equipped items for a player"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM equipped_items WHERE player_id = $1", player_id)


async def equip_item(player_id: int, item_name: str, slot: str):
    """Equip an item to a slot"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO equipped_items (player_id, item_name, slot)
               VALUES ($1, $2, $3)
               ON CONFLICT(player_id, slot) DO UPDATE SET item_name = $2""",
            player_id, item_name, slot
        )


async def unequip_item(player_id: int, slot: str):
    """Unequip an item from a slot"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM equipped_items WHERE player_id = $1 AND slot = $2",
            player_id, slot
        )


# ═══════════════════════════════════════════════════════════════════════════
# SKILL HELPERS
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# HEIST HELPERS
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# STORY HELPERS
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# LEADERBOARD
# ═══════════════════════════════════════════════════════════════════════════

async def get_leaderboard(sort_by: str = "credits", limit: int = 10):
    col = sort_by if sort_by in ("credits", "level", "rep") else "credits"
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            f"SELECT * FROM players ORDER BY {col} DESC LIMIT $1", limit
        )


# ═══════════════════════════════════════════════════════════════════════════
# EVENT LOG
# ═══════════════════════════════════════════════════════════════════════════

async def log_event(event_key: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO event_log (event_key) VALUES ($1)", event_key)


# ═══════════════════════════════════════════════════════════════════════════
# PVP LOG
# ═══════════════════════════════════════════════════════════════════════════

async def log_pvp(p1_id: int, p2_id: int, winner_id: int, rounds: int, log_text: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO pvp_log (p1_id, p2_id, winner_id, rounds, log_text) VALUES ($1, $2, $3, $4, $5)",
            p1_id, p2_id, winner_id, rounds, log_text
        )