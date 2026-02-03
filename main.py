# main.py

import os
import sys
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ── Logging Setup ────────────────────────────────────────────────────────────
# Configure logging to stdout for container environments
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('riskpunk')

# ── Env ──────────────────────────────────────────────────────────────────────
logger.info("Loading environment variables...")
load_dotenv()
TOKEN   = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD   = int(os.getenv("DISCORD_GUILD_ID", "0"))
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not TOKEN:
    logger.error("❌  DISCORD_BOT_TOKEN is not set.")
    logger.error("💡 Set it as an environment variable or in a .env file")
    logger.error("   Example: export DISCORD_BOT_TOKEN='your_token_here'")
    sys.exit(1)

if not DATABASE_URL:
    logger.error("❌  DATABASE_URL is not set.")
    logger.error("💡 Get your Neon PostgreSQL connection string from https://neon.tech")
    logger.error("   Example: postgresql://user:pass@host/dbname")
    sys.exit(1)

logger.info("✅ Environment variables loaded successfully")

# ── Intents ──────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members         = True

# ── Bot ──────────────────────────────────────────────────────────────────────
class RiskpunkBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            debug_guilds=[GUILD] if GUILD else None,
        )
    
    async def setup_hook(self):
        """This is called when the bot is starting up, before it connects to Discord"""
        logger.info("━" * 60)
        logger.info("🔧  STARTING BOT SETUP...")
        logger.info("━" * 60)
        
        try:
            # ── Initialise DB ──────────────────────────────────
            logger.info("📊 Initializing database connection...")
            from utils.database import init_db
            await init_db()
            logger.info("✅  Database initialized successfully.")
            
            # ── Seed factions ──────────────────────────────────
            logger.info("🏢 Seeding factions...")
            await self._seed_factions()
            
            # ── Seed territories ───────────────────────────────
            logger.info("🗺️  Seeding territories...")
            await self._seed_territories()
            
            # ── Load cogs ──────────────────────────────────────
            logger.info("📦 Loading cogs...")
            cogs = [
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
            
            loaded_count = 0
            failed_count = 0
            
            for cog in cogs:
                try:
                    logger.info(f"  → Loading {cog}...")
                    await self.load_extension(cog)
                    logger.info(f"  ✅ Loaded  {cog}")
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"  ❌ Failed to load {cog}: {e}")
                    failed_count += 1
                    import traceback
                    logger.error(traceback.format_exc())
            
            logger.info("━" * 60)
            logger.info(f"📦 COG LOADING SUMMARY:")
            logger.info(f"   ✅ Loaded: {loaded_count}/{len(cogs)}")
            logger.info(f"   ❌ Failed: {failed_count}/{len(cogs)}")
            logger.info("━" * 60)
            
            if failed_count > 0:
                logger.warning(f"⚠️  {failed_count} cog(s) failed to load. Check errors above.")
            
            logger.info("✅ SETUP HOOK COMPLETED SUCCESSFULLY")
            logger.info("━" * 60)
            
        except Exception as e:
            logger.critical(f"💥 CRITICAL ERROR IN SETUP HOOK: {e}")
            import traceback
            logger.critical(traceback.format_exc())
            raise
    
    async def _seed_factions(self):
        """Seed initial factions if database is empty"""
        try:
            from utils.database import get_pool
            from utils.game_data import FACTIONS_SEED
            pool = await get_pool()
            async with pool.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM factions")
                if count == 0:
                    logger.info(f"  → Seeding {len(FACTIONS_SEED)} factions...")
                    for f in FACTIONS_SEED:
                        await conn.execute(
                            "INSERT INTO factions (key, name, description, color, aggression) VALUES ($1, $2, $3, $4, $5)",
                            f["key"], f["name"], f["description"], f["color"], f["aggression"]
                        )
                    logger.info(f"  ✅ Seeded {len(FACTIONS_SEED)} factions.")
                else:
                    logger.info(f"  ℹ️  Factions already seeded ({count} exist)")
        except Exception as e:
            logger.error(f"  ❌ Error seeding factions: {e}")
            raise
    
    async def _seed_territories(self):
        """Seed initial territories if database is empty"""
        try:
            from utils.database import get_pool
            from utils.game_data import TERRITORIES_SEED
            pool = await get_pool()
            async with pool.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM territories")
                if count == 0:
                    logger.info(f"  → Seeding {len(TERRITORIES_SEED)} territories...")
                    for t in TERRITORIES_SEED:
                        await conn.execute(
                            "INSERT INTO territories (key, name, description, income, defense) VALUES ($1, $2, $3, $4, $5)",
                            t["key"], t["name"], t["description"], t["income"], t["defense"]
                        )
                    logger.info(f"  ✅ Seeded {len(TERRITORIES_SEED)} territories.")
                else:
                    logger.info(f"  ℹ️  Territories already seeded ({count} exist)")
        except Exception as e:
            logger.error(f"  ❌ Error seeding territories: {e}")
            raise
    
    async def on_ready(self):
        """Called when bot successfully connects to Discord"""
        logger.info("━" * 60)
        logger.info(f"⚡ LOGGED IN AS: {self.user}  (ID: {self.user.id})")
        logger.info(f"🌐 CONNECTED TO: {len(self.guilds)} guild(s)")
        if self.guilds:
            for guild in self.guilds:
                logger.info(f"   → {guild.name} (ID: {guild.id})")
        logger.info("━" * 60)
        logger.info("🚀 RISKPUNK IS LIVE — Risk City awaits.")
        logger.info("━" * 60)
        
        # Log loaded commands
        slash_commands = [cmd.name for cmd in self.pending_application_commands]
        if slash_commands:
            logger.info(f"📋 Registered {len(slash_commands)} slash commands:")
            for cmd in slash_commands:
                logger.info(f"   → /{cmd}")
        else:
            logger.warning("⚠️  No slash commands registered!")
    
    async def on_connect(self):
        """Called when the bot connects to Discord"""
        logger.info("🔗 Connected to Discord gateway")
    
    async def on_disconnect(self):
        """Called when the bot disconnects from Discord"""
        logger.warning("⚠️  Disconnected from Discord gateway")
    
    async def on_resumed(self):
        """Called when the bot resumes a session"""
        logger.info("🔄 Resumed Discord session")
    
    async def close(self):
        """Called when bot is shutting down"""
        logger.info("🔌 Shutting down bot...")
        try:
            from utils.database import close_pool
            await close_pool()
            logger.info("✅ Database connection pool closed.")
        except Exception as e:
            logger.error(f"❌ Error closing database pool: {e}")
        await super().close()
        logger.info("👋 Bot shutdown complete")


# Create bot instance
logger.info("Creating bot instance...")
bot = RiskpunkBot()


# ── /help ────────────────────────────────────────────────────────────────────
@bot.slash_command(name="help", description="Riskpunk command overview.")
async def help_cmd(ctx: discord.ApplicationContext):
    from utils.styles import NeonEmbed, LINE, NEON_CYAN
    embed = NeonEmbed(title="⚡ RISKPUNK — Command Guide", color=NEON_CYAN)
    embed.description = (
        "`Economic Political Simulator — Risk City`\n"
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
    logger.error(f"⚠️  Command error in /{ctx.command.name}: {error}")
    logger.error(f"   User: {ctx.author} (ID: {ctx.author.id})")
    logger.error(f"   Guild: {ctx.guild.name if ctx.guild else 'DM'}")
    
    import traceback
    logger.error(traceback.format_exc())
    
    embed = NeonEmbed(title="💥 Error", description=f"Something went wrong.\n`{error}`", color=NEON_RED)
    try:
        await ctx.respond(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Failed to send error message to user: {e}")


# ── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        logger.info("━" * 60)
        logger.info("🎮 STARTING RISKPUNK BOT")
        logger.info("━" * 60)
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Discord.py version: {discord.__version__}")
        logger.info("━" * 60)
        
        bot.run(TOKEN)
        
    except discord.LoginFailure:
        logger.critical("❌  Invalid token! Check your DISCORD_BOT_TOKEN")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("⌨️  Keyboard interrupt received, shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"❌  Critical error: {e}")
        import traceback
        logger.critical(traceback.format_exc())
        sys.exit(1)
