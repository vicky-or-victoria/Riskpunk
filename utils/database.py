# utils/database.py
import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "neonledger.db")


async def get_db() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON;")
    return conn


async def init_db():
    async with await get_db() as db:
        # ── Players ──────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id          INTEGER PRIMARY KEY,
                discord_id  INTEGER UNIQUE NOT NULL,
                name        TEXT    NOT NULL DEFAULT 'Drifter',
                credits     REAL    NOT NULL DEFAULT 5000,
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

        # ── Implants ─────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS implants (
                id          INTEGER PRIMARY KEY,
                player_id   INTEGER NOT NULL,
                implant_key TEXT    NOT NULL,
                slot        TEXT    NOT NULL,
                installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(id),
                UNIQUE(player_id, slot)
            )
        """)

        # ── Factions ─────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS factions (
                id          INTEGER PRIMARY KEY,
                key         TEXT    UNIQUE NOT NULL,
                name        TEXT    NOT NULL,
                description TEXT,
                color       TEXT    NOT NULL DEFAULT '#ff0000',
                war_target  INTEGER,
                aggression  INTEGER NOT NULL DEFAULT 50
            )
        """)

        # ── Faction Wars ─────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS faction_wars (
                id          INTEGER PRIMARY KEY,
                faction_a   INTEGER NOT NULL,
                faction_b   INTEGER NOT NULL,
                started_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at    TIMESTAMP,
                winner      INTEGER,
                FOREIGN KEY (faction_a) REFERENCES factions(id),
                FOREIGN KEY (faction_b) REFERENCES factions(id)
            )
        """)

        # ── Territories ──────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS territories (
                id          INTEGER PRIMARY KEY,
                key         TEXT    UNIQUE NOT NULL,
                name        TEXT    NOT NULL,
                description TEXT,
                owner_faction INTEGER,
                income      REAL    NOT NULL DEFAULT 200,
                defense     INTEGER NOT NULL DEFAULT 50,
                FOREIGN KEY (owner_faction) REFERENCES factions(id)
            )
        """)

        # ── Active Trades ───────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id          INTEGER PRIMARY KEY,
                seller_id   INTEGER NOT NULL,
                buyer_id    INTEGER,
                item_name   TEXT    NOT NULL,
                quantity    INTEGER NOT NULL DEFAULT 1,
                price       REAL    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'open',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (seller_id) REFERENCES players(id)
            )
        """)

        # ── Inventory ────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id          INTEGER PRIMARY KEY,
                player_id   INTEGER NOT NULL,
                item_name   TEXT    NOT NULL,
                quantity    INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (player_id) REFERENCES players(id),
                UNIQUE(player_id, item_name)
            )
        """)

        # ── Skill Trees ──────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id          INTEGER PRIMARY KEY,
                player_id   INTEGER NOT NULL,
                skill_key   TEXT    NOT NULL,
                level       INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (player_id) REFERENCES players(id),
                UNIQUE(player_id, skill_key)
            )
        """)

        # ── Active Heists ───────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS heists (
                id          INTEGER PRIMARY KEY,
                leader_id   INTEGER NOT NULL,
                target      TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'recruiting',
                reward      REAL    NOT NULL DEFAULT 10000,
                difficulty  INTEGER NOT NULL DEFAULT 5,
                crew        TEXT    NOT NULL DEFAULT '',
                phase       TEXT    NOT NULL DEFAULT 'planning',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (leader_id) REFERENCES players(id)
            )
        """)

        # ── Story Progress ───────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS story_progress (
                id          INTEGER PRIMARY KEY,
                player_id   INTEGER NOT NULL,
                chapter     INTEGER NOT NULL DEFAULT 1,
                node        TEXT    NOT NULL DEFAULT 'start',
                choices     TEXT    NOT NULL DEFAULT '',
                FOREIGN KEY (player_id) REFERENCES players(id),
                UNIQUE(player_id)
            )
        """)

        # ── Random Events Log ────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS event_log (
                id          INTEGER PRIMARY KEY,
                event_key   TEXT    NOT NULL,
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved    INTEGER NOT NULL DEFAULT 0
            )
        """)

        # ── PvP Match Log ────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pvp_log (
                id          INTEGER PRIMARY KEY,
                p1_id       INTEGER NOT NULL,
                p2_id       INTEGER NOT NULL,
                winner_id   INTEGER,
                rounds      INTEGER NOT NULL DEFAULT 0,
                log_text    TEXT,
                fought_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (p1_id) REFERENCES players(id),
                FOREIGN KEY (p2_id) REFERENCES players(id)
            )
        """)

        await db.commit()


# ─── Player Helpers ─────────────────────────────────────────────────────────

async def get_player(discord_id: int):
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM players WHERE discord_id = ?", (discord_id,))
        return await cur.fetchone()


async def get_player_by_id(player_id: int):
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        return await cur.fetchone()


async def ensure_player(discord_id: int, name: str = "Drifter"):
    player = await get_player(discord_id)
    if player:
        return player
    async with await get_db() as db:
        cur = await db.execute(
            "INSERT INTO players (discord_id, name) VALUES (?, ?) RETURNING *",
            (discord_id, name)
        )
        await db.commit()
        return await cur.fetchone()


async def update_player_credits(discord_id: int, amount: float):
    async with await get_db() as db:
        await db.execute(
            "UPDATE players SET credits = credits + ? WHERE discord_id = ?",
            (amount, discord_id)
        )
        await db.commit()


async def update_player_hp(discord_id: int, amount: int):
    async with await get_db() as db:
        await db.execute("""
            UPDATE players
            SET hp = MIN(max_hp, MAX(0, hp + ?))
            WHERE discord_id = ?
        """, (amount, discord_id))
        await db.commit()


async def update_player_xp(discord_id: int, xp_gain: int):
    async with await get_db() as db:
        cur = await db.execute("SELECT level, xp FROM players WHERE discord_id = ?", (discord_id,))
        row = await cur.fetchone()
        if not row:
            return 0, 0
        new_xp = row["xp"] + xp_gain
        new_level = row["level"]
        xp_needed = new_level * 500
        leveled = False
        while new_xp >= xp_needed:
            new_xp -= xp_needed
            new_level += 1
            leveled = True
            xp_needed = new_level * 500
            # Stat boosts on level up
            await db.execute("""
                UPDATE players SET
                    max_hp = max_hp + 10,
                    hp    = hp + 10,
                    atk   = atk + 2,
                    def   = def + 1,
                    spd   = spd + 1
                WHERE discord_id = ?
            """, (discord_id,))
        await db.execute(
            "UPDATE players SET level = ?, xp = ? WHERE discord_id = ?",
            (new_level, new_xp, discord_id)
        )
        await db.commit()
        return new_level, new_xp


async def set_player_faction(discord_id: int, faction_id: int):
    async with await get_db() as db:
        await db.execute(
            "UPDATE players SET faction_id = ? WHERE discord_id = ?",
            (faction_id, discord_id)
        )
        await db.commit()


# ─── Implant Helpers ─────────────────────────────────────────────────────────

async def get_player_implants(player_id: int):
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM implants WHERE player_id = ?", (player_id,))
        return await cur.fetchall()


async def install_implant(player_id: int, implant_key: str, slot: str):
    async with await get_db() as db:
        # Remove existing in that slot
        await db.execute("DELETE FROM implants WHERE player_id = ? AND slot = ?", (player_id, slot))
        await db.execute(
            "INSERT INTO implants (player_id, implant_key, slot) VALUES (?, ?, ?)",
            (player_id, implant_key, slot)
        )
        await db.commit()


async def remove_implant(player_id: int, slot: str):
    async with await get_db() as db:
        await db.execute("DELETE FROM implants WHERE player_id = ? AND slot = ?", (player_id, slot))
        await db.commit()


# ─── Faction Helpers ─────────────────────────────────────────────────────────

async def get_all_factions():
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM factions")
        return await cur.fetchall()


async def get_faction(faction_id: int):
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM factions WHERE id = ?", (faction_id,))
        return await cur.fetchone()


async def get_faction_members(faction_id: int):
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM players WHERE faction_id = ?", (faction_id,))
        return await cur.fetchall()


async def declare_war(faction_a: int, faction_b: int):
    async with await get_db() as db:
        cur = await db.execute(
            "INSERT INTO faction_wars (faction_a, faction_b) VALUES (?, ?) RETURNING *",
            (faction_a, faction_b)
        )
        await db.commit()
        return await cur.fetchone()


async def get_active_wars():
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM faction_wars WHERE ended_at IS NULL")
        return await cur.fetchall()


async def resolve_war(war_id: int, winner: int):
    async with await get_db() as db:
        await db.execute(
            "UPDATE faction_wars SET winner = ?, ended_at = CURRENT_TIMESTAMP WHERE id = ?",
            (winner, war_id)
        )
        await db.commit()


# ─── Territory Helpers ───────────────────────────────────────────────────────

async def get_all_territories():
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM territories")
        return await cur.fetchall()


async def get_territory(key: str):
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM territories WHERE key = ?", (key,))
        return await cur.fetchone()


async def claim_territory(key: str, faction_id: int):
    async with await get_db() as db:
        await db.execute(
            "UPDATE territories SET owner_faction = ? WHERE key = ?",
            (faction_id, key)
        )
        await db.commit()


async def damage_territory(key: str, amount: int):
    async with await get_db() as db:
        await db.execute(
            "UPDATE territories SET defense = MAX(0, defense - ?) WHERE key = ?",
            (amount, key)
        )
        await db.commit()


# ─── Trade Helpers ───────────────────────────────────────────────────────────

async def create_trade(seller_id: int, item_name: str, quantity: int, price: float):
    async with await get_db() as db:
        cur = await db.execute(
            "INSERT INTO trades (seller_id, item_name, quantity, price) VALUES (?, ?, ?, ?) RETURNING *",
            (seller_id, item_name, quantity, price)
        )
        await db.commit()
        return await cur.fetchone()


async def get_open_trades():
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM trades WHERE status = 'open' ORDER BY created_at DESC LIMIT 25")
        return await cur.fetchall()


async def fulfill_trade(trade_id: int, buyer_id: int):
    async with await get_db() as db:
        await db.execute(
            "UPDATE trades SET status = 'fulfilled', buyer_id = ? WHERE id = ?",
            (buyer_id, trade_id)
        )
        await db.commit()


async def cancel_trade(trade_id: int):
    async with await get_db() as db:
        await db.execute("UPDATE trades SET status = 'cancelled' WHERE id = ?", (trade_id,))
        await db.commit()


# ─── Inventory Helpers ───────────────────────────────────────────────────────

async def get_inventory(player_id: int):
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM inventory WHERE player_id = ?", (player_id,))
        return await cur.fetchall()


async def add_item(player_id: int, item_name: str, qty: int = 1):
    async with await get_db() as db:
        await db.execute("""
            INSERT INTO inventory (player_id, item_name, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id, item_name) DO UPDATE SET quantity = quantity + ?
        """, (player_id, item_name, qty, qty))
        await db.commit()


async def remove_item(player_id: int, item_name: str, qty: int = 1) -> bool:
    async with await get_db() as db:
        cur = await db.execute(
            "SELECT quantity FROM inventory WHERE player_id = ? AND item_name = ?",
            (player_id, item_name)
        )
        row = await cur.fetchone()
        if not row or row["quantity"] < qty:
            return False
        if row["quantity"] == qty:
            await db.execute(
                "DELETE FROM inventory WHERE player_id = ? AND item_name = ?",
                (player_id, item_name)
            )
        else:
            await db.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE player_id = ? AND item_name = ?",
                (qty, player_id, item_name)
            )
        await db.commit()
        return True


# ─── Skill Helpers ───────────────────────────────────────────────────────────

async def get_player_skills(player_id: int):
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM skills WHERE player_id = ?", (player_id,))
        return await cur.fetchall()


async def get_skill(player_id: int, skill_key: str):
    async with await get_db() as db:
        cur = await db.execute(
            "SELECT * FROM skills WHERE player_id = ? AND skill_key = ?",
            (player_id, skill_key)
        )
        return await cur.fetchone()


async def set_skill(player_id: int, skill_key: str, level: int = 1):
    async with await get_db() as db:
        await db.execute("""
            INSERT INTO skills (player_id, skill_key, level)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id, skill_key) DO UPDATE SET level = ?
        """, (player_id, skill_key, level, level))
        await db.commit()


# ─── Heist Helpers ───────────────────────────────────────────────────────────

async def create_heist(leader_id: int, target: str, reward: float, difficulty: int):
    async with await get_db() as db:
        cur = await db.execute(
            "INSERT INTO heists (leader_id, target, reward, difficulty, crew) VALUES (?, ?, ?, ?, ?) RETURNING *",
            (leader_id, target, reward, difficulty, str(leader_id))
        )
        await db.commit()
        return await cur.fetchone()


async def get_heist(heist_id: int):
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM heists WHERE id = ?", (heist_id,))
        return await cur.fetchone()


async def get_active_heists():
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM heists WHERE status IN ('recruiting', 'planning', 'active')")
        return await cur.fetchall()


async def join_heist(heist_id: int, player_id: int):
    heist = await get_heist(heist_id)
    if not heist:
        return False
    crew_ids = [int(x) for x in heist["crew"].split(",") if x]
    if player_id in crew_ids:
        return False
    crew_ids.append(player_id)
    async with await get_db() as db:
        await db.execute(
            "UPDATE heists SET crew = ? WHERE id = ?",
            (",".join(str(x) for x in crew_ids), heist_id)
        )
        await db.commit()
    return True


async def advance_heist_phase(heist_id: int, new_phase: str, new_status: str = None):
    async with await get_db() as db:
        if new_status:
            await db.execute(
                "UPDATE heists SET phase = ?, status = ? WHERE id = ?",
                (new_phase, new_status, heist_id)
            )
        else:
            await db.execute(
                "UPDATE heists SET phase = ? WHERE id = ?",
                (new_phase, heist_id)
            )
        await db.commit()


# ─── Story Helpers ───────────────────────────────────────────────────────────

async def get_story_progress(player_id: int):
    async with await get_db() as db:
        cur = await db.execute("SELECT * FROM story_progress WHERE player_id = ?", (player_id,))
        return await cur.fetchone()


async def set_story_progress(player_id: int, chapter: int, node: str, choice: str = ""):
    async with await get_db() as db:
        cur = await db.execute("SELECT choices FROM story_progress WHERE player_id = ?", (player_id,))
        row = await cur.fetchone()
        if row:
            old = row["choices"]
            new_choices = f"{old},{choice}" if choice else old
            await db.execute(
                "UPDATE story_progress SET chapter = ?, node = ?, choices = ? WHERE player_id = ?",
                (chapter, node, new_choices, player_id)
            )
        else:
            await db.execute(
                "INSERT INTO story_progress (player_id, chapter, node, choices) VALUES (?, ?, ?, ?)",
                (player_id, chapter, node, choice)
            )
        await db.commit()


# ─── Leaderboard ─────────────────────────────────────────────────────────────

async def get_leaderboard(sort_by: str = "credits", limit: int = 10):
    col = sort_by if sort_by in ("credits", "level", "rep") else "credits"
    async with await get_db() as db:
        cur = await db.execute(
            f"SELECT * FROM players ORDER BY {col} DESC LIMIT ?", (limit,)
        )
        return await cur.fetchall()


# ─── Event Log ───────────────────────────────────────────────────────────────

async def log_event(event_key: str):
    async with await get_db() as db:
        await db.execute("INSERT INTO event_log (event_key) VALUES (?)", (event_key,))
        await db.commit()


# ─── PvP Log ─────────────────────────────────────────────────────────────────

async def log_pvp(p1_id: int, p2_id: int, winner_id: int, rounds: int, log_text: str):
    async with await get_db() as db:
        await db.execute(
            "INSERT INTO pvp_log (p1_id, p2_id, winner_id, rounds, log_text) VALUES (?, ?, ?, ?, ?)",
            (p1_id, p2_id, winner_id, rounds, log_text)
        )
        await db.commit()
