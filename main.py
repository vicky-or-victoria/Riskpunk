# main.py

import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ── Env ──────────────────────────────────────────────────────────────────────
load_dotenv()
TOKEN   = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD   = int(os.getenv("DISCORD_GUILD_ID", "0"))
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not TOKEN:
    print("❌  DISCORD_BOT_TOKEN is not set.")
    print("💡 Set it as an environment variable or in a .env file")
    print("   Example: export DISCORD_BOT_TOKEN='your_token_here'")
    sys.exit(1)

if not DATABASE_URL:
    print("❌  DATABASE_URL is not set.")
    print("💡 Get your Neon PostgreSQL connection string from https://neon.tech")
    print("   Example: postgresql://user:pass@host/dbname")
    sys.exit(1)

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
            await bot.load_extension(cog)
            print(f"  📦  Loaded  {cog}")
        except Exception as e:
            print(f"  ❌  Failed to load {cog}: {e}")

    print("━" * 50)
    print("🚀  Riskpunk is live.  Risk City awaits.")


# ── Cleanup on shutdown ──────────────────────────────────────────────────────
@bot.event
async def on_close():
    from utils.database import close_pool
    await close_pool()
    print("🔌  Database connection pool closed.")


# ── Seeds ────────────────────────────────────────────────────────────────────
async def _seed_factions():
    from utils.database import get_pool
    from utils.game_data import FACTIONS_SEED
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM factions")
        if count == 0:
            for f in FACTIONS_SEED:
                await conn.execute(
                    "INSERT INTO factions (key, name, description, color, aggression) VALUES ($1, $2, $3, $4, $5)",
                    f["key"], f["name"], f["description"], f["color"], f["aggression"]
                )
            print("  🏢  Seeded 5 factions.")


async def _seed_territories():
    from utils.database import get_pool
    from utils.game_data import TERRITORIES_SEED
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM territories")
        if count == 0:
            for t in TERRITORIES_SEED:
                await conn.execute(
                    "INSERT INTO territories (key, name, description, income, defense) VALUES ($1, $2, $3, $4, $5)",
                    t["key"], t["name"], t["description"], t["income"], t["defense"]
                )
            print("  🗺️   Seeded 8 territories.")


# ── /help ────────────────────────────────────────────────────────────────────
@bot.slash_command(name="help", description="NeonLedger command overview.")
async def help_cmd(ctx: discord.ApplicationContext):
    from utils.styles import NeonEmbed, LINE, NEON_CYAN
    embed = NeonEmbed(title="⚡ NEONLEDGER — Command Guide", color=NEON_CYAN)
    embed.description = (
        "`Economic Political Simulator — Riskpunk`\n"
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
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌  Invalid token! Check your DISCORD_BOT_TOKEN")
        sys.exit(1)
    except Exception as e:
        print(f"❌  Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
