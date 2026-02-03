#!/usr/bin/env python3
# main.py — NeonLedger Discord Bot  ⚡
# ─────────────────────────────────────────────────────────────────────────────
# Economic Political Simulator  |  Cyberpunk Neo-Tokyo  |  discord.py v2+
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ── Env ──────────────────────────────────────────────────────────────────────
load_dotenv()
TOKEN   = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD   = int(os.getenv("DISCORD_GUILD_ID", "0"))

if not TOKEN:
    sys.exit("❌  DISCORD_BOT_TOKEN is not set.  Check your .env file.")

# ── Intents ──────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members         = True

# ── Bot ──────────────────────────────────────────────────────────────────────
bot = commands.Bot(
    command_prefix="!",          # legacy prefix (unused but harmless)
    intents=intents,
    debug_guilds=[GUILD] if GUILD else None,
)

# ── Cog list ─────────────────────────────────────────────────────────────────
COGS = [
    "cogs.player",
    "cogs.implants",
    "cogs.factions",
    "cogs.trading",
    "cogs.heists",
    "cogs.territory",
    "cogs.events",
    "cogs.skills",
    "cogs.pvp",
    "cogs.story",
    "cogs.leaderboard",
]


# ── Startup ──────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"⚡  Logged in as {bot.user}  (ID: {bot.user.id})")
    print("━" * 50)

    # ── Initialise DB ──────────────────────────────────
    from utils.database import init_db
    await init_db()
    print("✅  Database initialised.")

    # ── Seed factions ──────────────────────────────────
    await _seed_factions()

    # ── Seed territories ───────────────────────────────
    await _seed_territories()

    # ── Load cogs ──────────────────────────────────────
    for cog in COGS:
        try:
            bot.load_extension(cog)
            print(f"  📦  Loaded  {cog}")
        except Exception as e:
            print(f"  ❌  Failed to load {cog}: {e}")

    print("━" * 50)
    print("🚀  NeonLedger is live.  Neo-Tokyo awaits.")


# ── Seeds ────────────────────────────────────────────────────────────────────
async def _seed_factions():
    from utils.database import get_db
    from utils.game_data import FACTIONS_SEED
    async with await get_db() as db:
        cur = await db.execute("SELECT COUNT(*) as cnt FROM factions")
        row = await cur.fetchone()
        if row["cnt"] == 0:
            for f in FACTIONS_SEED:
                await db.execute(
                    "INSERT INTO factions (key, name, description, color, aggression) VALUES (?,?,?,?,?)",
                    (f["key"], f["name"], f["description"], f["color"], f["aggression"])
                )
            await db.commit()
            print("  🏢  Seeded 5 factions.")


async def _seed_territories():
    from utils.database import get_db
    from utils.game_data import TERRITORIES_SEED
    async with await get_db() as db:
        cur = await db.execute("SELECT COUNT(*) as cnt FROM territories")
        row = await cur.fetchone()
        if row["cnt"] == 0:
            for t in TERRITORIES_SEED:
                await db.execute(
                    "INSERT INTO territories (key, name, description, income, defense) VALUES (?,?,?,?,?)",
                    (t["key"], t["name"], t["description"], t["income"], t["defense"])
                )
            await db.commit()
            print("  🗺️   Seeded 8 territories.")


# ── /help ────────────────────────────────────────────────────────────────────
@bot.slash_command(name="help", description="NeonLedger command overview.")
async def help_cmd(ctx: discord.ApplicationContext):
    from utils.styles import NeonEmbed, LINE, NEON_CYAN
    embed = NeonEmbed(title="⚡ NEONLEDGER — Command Guide", color=NEON_CYAN)
    embed.description = (
        "`Economic Political Simulator — Neo-Tokyo`\n"
        f"{LINE}"
    )
    sections = {
        "👤 Identity":         "/register  /profile  /balance  /heal  /inventory",
        "🔧 Implants":         "/implants list  shop  install  remove",
        "🏢 Factions":         "/factions list  join  war  wars",
        "💱 Trading":          "/trade board  sell  buy  cancel  /shop  /shopbuy",
        "🚨 Heists":           "/heist targets  create  join  execute  list",
        "🗺️  Territory":       "/territory map  info  attack  fortify",
        "🧬 Skills":           "/skills tree  my  learn  upgrade",
        "⚔️  PvP":             "/pvp <@opponent>",
        "📖 Story":            "/story play  status  restart",
        "🏆 Leaderboard":      "/leaderboard credits  level  rep",
        "📢 Events":           "Auto-triggered every 30 min  |  /trigger_event (admin)",
    }
    for title, cmds in sections.items():
        embed.add_field(name=title, value=f"`{cmds}`", inline=False)
    embed.add_field(
        name="💡 Getting Started",
        value="1️⃣  `/register YourName`\n2️⃣  `/factions join <faction>`\n3️⃣  `/story play`\n4️⃣  Explore!",
        inline=False
    )
    await ctx.respond(embed=embed)


# ── Error handler ────────────────────────────────────────────────────────────
@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error):
    from utils.styles import NeonEmbed, NEON_RED
    print(f"  ⚠️  Command error in /{ctx.command.name}: {error}")
    embed = NeonEmbed(title="💥 Error", description=f"Something went wrong.\n`{error}`", color=NEON_RED)
    try:
        await ctx.respond(embed=embed, ephemeral=True)
    except Exception:
        pass


# ── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(TOKEN)
