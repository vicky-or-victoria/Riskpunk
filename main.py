# main.py

import os
import sys
import logging
import asyncio
import traceback

# ── Critical Logging Setup (MUST BE FIRST) ──────────────────────────────────
# Force unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

# Configure logging immediately
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)
logger = logging.getLogger('riskpunk')

# Log immediately to verify logging works
logger.info("=" * 70)
logger.info("RISKPUNK BOT STARTING UP")
logger.info("=" * 70)
logger.info(f"Python version: {sys.version}")

# ── Import Discord ───────────────────────────────────────────────────────────
try:
    import discord
    from discord.ext import commands
    logger.info(f"✅ Discord.py version: {discord.__version__}")
except ImportError as e:
    logger.critical(f"❌ Failed to import discord.py: {e}")
    logger.critical("Run: pip install py-cord")
    sys.exit(1)

# ── Environment Variables ────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("✅ dotenv loaded")
except ImportError:
    logger.warning("⚠️  python-dotenv not available, using environment variables only")

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD = os.getenv("DISCORD_GUILD_ID", "0")
DATABASE_URL = os.getenv("DATABASE_URL", "")

logger.info(f"Environment check:")
logger.info(f"  TOKEN: {'✅ Set' if TOKEN else '❌ Missing'}")
logger.info(f"  DATABASE_URL: {'✅ Set' if DATABASE_URL else '❌ Missing'}")
logger.info(f"  GUILD_ID: {GUILD if GUILD != '0' else '❌ Not set (will register globally)'}")

if not TOKEN:
    logger.error("❌ DISCORD_BOT_TOKEN is not set!")
    logger.error("Set it as: export DISCORD_BOT_TOKEN='your_token_here'")
    sys.exit(1)

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL is not set!")
    logger.error("Get your connection string from https://neon.tech")
    logger.error("Format: postgresql://user:pass@host/dbname")
    sys.exit(1)

# Convert GUILD to int
try:
    GUILD = int(GUILD) if GUILD != "0" else None
except ValueError:
    logger.warning(f"⚠️  Invalid GUILD_ID '{GUILD}', ignoring")
    GUILD = None

# ── Intents ──────────────────────────────────────────────────────────────────
logger.info("Setting up intents...")
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
logger.info("✅ Intents configured")

# ── Bot Class ────────────────────────────────────────────────────────────────
class RiskpunkBot(commands.Bot):
    def __init__(self):
        logger.info("Initializing bot instance...")
        super().__init__(
            command_prefix="!",
            intents=intents,
            debug_guilds=[GUILD] if GUILD else None,
        )
        self.startup_failed = False
        logger.info("✅ Bot instance created")
    
    async def setup_hook(self):
        """This is called when the bot is starting up"""
        logger.info("=" * 70)
        logger.info("SETUP HOOK STARTED")
        logger.info("=" * 70)
        
        try:
            # ── Test Database Connection ───────────────────────
            logger.info("Step 1: Testing database connection...")
            try:
                from utils.database import get_pool
                pool = await get_pool()
                async with pool.acquire() as conn:
                    result = await conn.fetchval("SELECT 1")
                    logger.info(f"✅ Database connection successful (test query returned: {result})")
            except Exception as db_err:
                logger.error(f"❌ Database connection failed: {db_err}")
                logger.error(traceback.format_exc())
                raise
            
            # ── Initialize Database ────────────────────────────
            logger.info("Step 2: Initializing database schema...")
            try:
                from utils.database import init_db
                await init_db()
                logger.info("✅ Database schema initialized")
            except Exception as init_err:
                logger.error(f"❌ Database initialization failed: {init_err}")
                logger.error(traceback.format_exc())
                raise
            
            # ── Seed Factions ──────────────────────────────────
            logger.info("Step 3: Seeding factions...")
            try:
                await self._seed_factions()
            except Exception as faction_err:
                logger.error(f"❌ Faction seeding failed: {faction_err}")
                logger.error(traceback.format_exc())
                # Don't raise - this is not critical
            
            # ── Seed Territories ───────────────────────────────
            logger.info("Step 4: Seeding territories...")
            try:
                await self._seed_territories()
            except Exception as territory_err:
                logger.error(f"❌ Territory seeding failed: {territory_err}")
                logger.error(traceback.format_exc())
                # Don't raise - this is not critical
            
            # ── Load Cogs ──────────────────────────────────────
            logger.info("Step 5: Loading cogs...")
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
            
            loaded = []
            failed = []
            
            for cog in cogs:
                try:
                    logger.info(f"  Loading {cog}...")
                    await self.load_extension(cog)
                    logger.info(f"  ✅ {cog}")
                    loaded.append(cog)
                except Exception as cog_err:
                    logger.error(f"  ❌ {cog}: {cog_err}")
                    logger.error(f"     {traceback.format_exc()}")
                    failed.append((cog, str(cog_err)))
            
            logger.info("=" * 70)
            logger.info(f"COG LOADING COMPLETE: {len(loaded)}/{len(cogs)} loaded")
            if loaded:
                logger.info(f"✅ Loaded: {', '.join(loaded)}")
            if failed:
                logger.warning(f"❌ Failed: {', '.join(c for c, _ in failed)}")
                for cog, err in failed:
                    logger.warning(f"   {cog}: {err}")
            logger.info("=" * 70)
            
            logger.info("✅ SETUP HOOK COMPLETED SUCCESSFULLY")
            
        except Exception as e:
            logger.critical("=" * 70)
            logger.critical(f"💥 CRITICAL FAILURE IN SETUP HOOK: {e}")
            logger.critical(traceback.format_exc())
            logger.critical("=" * 70)
            self.startup_failed = True
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
                    logger.info(f"  Inserting {len(FACTIONS_SEED)} factions...")
                    for f in FACTIONS_SEED:
                        await conn.execute(
                            "INSERT INTO factions (key, name, description, color, aggression) VALUES ($1, $2, $3, $4, $5)",
                            f["key"], f["name"], f["description"], f["color"], f["aggression"]
                        )
                    logger.info(f"  ✅ Seeded {len(FACTIONS_SEED)} factions")
                else:
                    logger.info(f"  ℹ️  Factions table has {count} entries, skipping seed")
        except Exception as e:
            logger.error(f"  Faction seeding error: {e}")
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
                    logger.info(f"  Inserting {len(TERRITORIES_SEED)} territories...")
                    for t in TERRITORIES_SEED:
                        await conn.execute(
                            "INSERT INTO territories (key, name, description, income, defense) VALUES ($1, $2, $3, $4, $5)",
                            t["key"], t["name"], t["description"], t["income"], t["defense"]
                        )
                    logger.info(f"  ✅ Seeded {len(TERRITORIES_SEED)} territories")
                else:
                    logger.info(f"  ℹ️  Territories table has {count} entries, skipping seed")
        except Exception as e:
            logger.error(f"  Territory seeding error: {e}")
            raise
    
    async def on_connect(self):
        """Called when bot connects to Discord"""
        logger.info("🔗 CONNECTED to Discord gateway")
    
    async def on_ready(self):
        """Called when bot is fully ready"""
        logger.info("=" * 70)
        logger.info(f"⚡ BOT IS READY")
        logger.info(f"   Username: {self.user}")
        logger.info(f"   User ID: {self.user.id}")
        logger.info(f"   Guilds: {len(self.guilds)}")
        
        if self.guilds:
            for guild in self.guilds:
                logger.info(f"     → {guild.name} (ID: {guild.id}, {guild.member_count} members)")
        
        # Count registered commands
        app_commands = await self.http.get_global_commands(self.user.id)
        logger.info(f"   Global commands: {len(app_commands)}")
        
        if GUILD:
            try:
                guild_commands = await self.http.get_guild_commands(self.user.id, GUILD)
                logger.info(f"   Guild commands: {len(guild_commands)}")
            except:
                pass
        
        logger.info("=" * 70)
        logger.info("🚀 RISKPUNK IS LIVE")
        logger.info("=" * 70)
    
    async def on_disconnect(self):
        """Called when bot disconnects"""
        logger.warning("⚠️  DISCONNECTED from Discord")
    
    async def on_resumed(self):
        """Called when bot resumes"""
        logger.info("🔄 SESSION RESUMED")
    
    async def close(self):
        """Cleanup on shutdown"""
        logger.info("🔌 SHUTTING DOWN...")
        try:
            from utils.database import close_pool
            await close_pool()
            logger.info("✅ Database pool closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
        await super().close()
        logger.info("👋 SHUTDOWN COMPLETE")


# ── Create Bot ───────────────────────────────────────────────────────────────
logger.info("Creating bot instance...")
try:
    bot = RiskpunkBot()
    logger.info("✅ Bot created")
except Exception as e:
    logger.critical(f"❌ Failed to create bot: {e}")
    logger.critical(traceback.format_exc())
    sys.exit(1)


# ── Help Command ─────────────────────────────────────────────────────────────
@bot.slash_command(name="help", description="Riskpunk command overview.")
async def help_cmd(ctx: discord.ApplicationContext):
    from utils.styles import NeonEmbed, LINE, NEON_CYAN
    embed = NeonEmbed(title="⚡ RISKPUNK — Command Guide", color=NEON_CYAN)
    embed.description = (
        "`Economic Political Simulator — Risk City`\n"
        f"{LINE}"
    )
    sections = {
        "👤 Identity": "/register  /profile  /balance  /heal",
        "🔧 Implants": "/implants list  shop  install  remove",
        "🏢 Factions": "/factions list  join  war  wars",
        "💱 Trading": "/trade board  sell  buy  cancel  /shop  /shopbuy",
        "🚨 Heists": "/heist targets  create  join  execute  list",
        "🗺️  Territory": "/territory map  info  attack  fortify",
        "🧬 Skills": "/skills tree  my  learn  upgrade",
        "⚔️  PvP": "/pvp <@opponent>",
        "📖 Story": "/story play  status  restart",
        "🏆 Leaderboard": "/leaderboard credits  level  rep",
    }
    for title, cmds in sections.items():
        embed.add_field(name=title, value=f"`{cmds}`", inline=False)
    embed.add_field(
        name="💡 Getting Started",
        value="1️⃣ `/register`  2️⃣ `/factions join`  3️⃣ `/story play`  4️⃣ Explore!",
        inline=False
    )
    await ctx.respond(embed=embed)


# ── Error Handler ────────────────────────────────────────────────────────────
@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error):
    from utils.styles import NeonEmbed, NEON_RED
    logger.error(f"Command error: /{ctx.command.name} by {ctx.author}")
    logger.error(f"Error: {error}")
    logger.error(traceback.format_exc())
    
    embed = NeonEmbed(
        title="💥 Error",
        description=f"Something went wrong.\n`{error}`",
        color=NEON_RED
    )
    try:
        await ctx.respond(embed=embed, ephemeral=True)
    except:
        pass


# ── Main Entry Point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("STARTING BOT...")
    logger.info("=" * 70)
    
    try:
        # Run the bot
        bot.run(TOKEN)
        
    except discord.LoginFailure:
        logger.critical("=" * 70)
        logger.critical("❌ LOGIN FAILED - Invalid token!")
        logger.critical("Check your DISCORD_BOT_TOKEN environment variable")
        logger.critical("=" * 70)
        sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("⌨️  Keyboard interrupt - shutting down gracefully")
        sys.exit(0)
        
    except Exception as e:
        logger.critical("=" * 70)
        logger.critical(f"💥 FATAL ERROR: {e}")
        logger.critical(traceback.format_exc())
        logger.critical("=" * 70)
        sys.exit(1)
    
    finally:
        logger.info("Process exiting")
