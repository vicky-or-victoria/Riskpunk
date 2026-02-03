# main.py

import os
import sys
import logging
import traceback

# ── Critical Logging Setup (MUST BE FIRST) ──────────────────────────────────
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)
logger = logging.getLogger('riskpunk')

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
    sys.exit(1)

# ── Environment Variables ────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("✅ dotenv loaded")
except ImportError:
    logger.warning("⚠️  python-dotenv not available")

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD = os.getenv("DISCORD_GUILD_ID", "0")
DATABASE_URL = os.getenv("DATABASE_URL", "")

logger.info(f"Environment check:")
logger.info(f"  TOKEN: {'✅ Set' if TOKEN else '❌ Missing'}")
logger.info(f"  DATABASE_URL: {'✅ Set' if DATABASE_URL else '❌ Missing'}")
logger.info(f"  GUILD_ID: {GUILD if GUILD != '0' else '⚠️  Not set (will register globally)'}")

if not TOKEN:
    logger.error("❌ DISCORD_BOT_TOKEN is not set!")
    sys.exit(1)

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL is not set!")
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
            # IMPORTANT: Set debug_guilds for instant command registration
            debug_guilds=[GUILD] if GUILD else None,
        )
        self.cogs_loaded = []
        self.cogs_failed = []
        logger.info("✅ Bot instance created")
    
    async def setup_hook(self):
        """Called during bot startup - BEFORE on_ready"""
        logger.info("=" * 70)
        logger.info("⚙️  SETUP_HOOK CALLED - STARTING INITIALIZATION")
        logger.info("=" * 70)
        
        try:
            # ── Database Setup ─────────────────────────────────
            logger.info("Step 1/4: Database connection...")
            try:
                from utils.database import get_pool, init_db
                
                # Test connection
                pool = await get_pool()
                async with pool.acquire() as conn:
                    result = await conn.fetchval("SELECT 1")
                logger.info(f"  ✅ Database connected (test: {result})")
                
                # Initialize schema
                await init_db()
                logger.info("  ✅ Database schema ready")
                
            except Exception as db_err:
                logger.error(f"  ❌ Database error: {db_err}")
                logger.error(traceback.format_exc())
                raise
            
            # ── Seed Data ──────────────────────────────────────
            logger.info("Step 2/4: Seeding game data...")
            try:
                await self._seed_factions()
                await self._seed_territories()
                logger.info("  ✅ Game data seeded")
            except Exception as seed_err:
                logger.error(f"  ⚠️  Seeding warning: {seed_err}")
                # Don't fail on seeding errors
            
            # ── Load Cogs ──────────────────────────────────────
            logger.info("Step 3/4: Loading cogs...")
            logger.info("=" * 70)
            
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
            
            for cog in cogs:
                try:
                    logger.info(f"  📦 Loading {cog}...")
                    await self.load_extension(cog)
                    self.cogs_loaded.append(cog)
                    logger.info(f"     ✅ SUCCESS")
                except Exception as cog_err:
                    self.cogs_failed.append((cog, str(cog_err)))
                    logger.error(f"     ❌ FAILED: {cog_err}")
                    logger.error(f"     {traceback.format_exc()}")
            
            logger.info("=" * 70)
            logger.info(f"📊 Cog Loading Summary:")
            logger.info(f"   ✅ Loaded: {len(self.cogs_loaded)}/{len(cogs)}")
            logger.info(f"   ❌ Failed: {len(self.cogs_failed)}/{len(cogs)}")
            
            if self.cogs_loaded:
                logger.info(f"   Loaded cogs: {', '.join(self.cogs_loaded)}")
            if self.cogs_failed:
                logger.warning(f"   Failed cogs: {', '.join(c for c, _ in self.cogs_failed)}")
            
            logger.info("=" * 70)
            
            # ── Sync Commands ──────────────────────────────────
            logger.info("Step 4/4: Syncing slash commands...")
            try:
                if GUILD:
                    # Sync to specific guild (instant)
                    logger.info(f"  Syncing to guild {GUILD}...")
                    synced = await self.sync_commands(guild_ids=[GUILD])
                    logger.info(f"  ✅ Synced {len(synced)} commands to guild")
                else:
                    # Sync globally (takes up to 1 hour)
                    logger.info("  Syncing globally (may take up to 1 hour)...")
                    synced = await self.sync_commands()
                    logger.info(f"  ✅ Synced {len(synced)} commands globally")
                    logger.warning("  ⚠️  Global commands take up to 1 hour to appear!")
                
                # Log command names
                if synced:
                    cmd_names = [cmd.name for cmd in synced]
                    logger.info(f"  Commands: {', '.join(cmd_names)}")
                    
            except Exception as sync_err:
                logger.error(f"  ❌ Command sync error: {sync_err}")
                logger.error(traceback.format_exc())
            
            logger.info("=" * 70)
            logger.info("✅ SETUP_HOOK COMPLETED")
            logger.info("=" * 70)
            
        except Exception as e:
            logger.critical("=" * 70)
            logger.critical(f"💥 SETUP_HOOK FAILED: {e}")
            logger.critical(traceback.format_exc())
            logger.critical("=" * 70)
            raise
    
    async def _seed_factions(self):
        """Seed initial factions"""
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
                logger.info(f"  ✅ Seeded {len(FACTIONS_SEED)} factions")
            else:
                logger.info(f"  ℹ️  {count} factions already exist")
    
    async def _seed_territories(self):
        """Seed initial territories"""
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
                logger.info(f"  ✅ Seeded {len(TERRITORIES_SEED)} territories")
            else:
                logger.info(f"  ℹ️  {count} territories already exist")
    
    async def on_connect(self):
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
                logger.info(f"     → {guild.name} (ID: {guild.id})")
        
        # Count commands
        total_cmds = len([cmd for cmd in self.walk_application_commands()])
        logger.info(f"   Total commands registered: {total_cmds}")
        
        logger.info("=" * 70)
        logger.info("🚀 RISKPUNK IS LIVE")
        logger.info("=" * 70)
        
        # Log loaded cogs summary again
        if self.cogs_loaded:
            logger.info(f"Active cogs ({len(self.cogs_loaded)}): {', '.join(self.cogs_loaded)}")
        if self.cogs_failed:
            logger.warning(f"Failed cogs ({len(self.cogs_failed)}): {', '.join(c for c, _ in self.cogs_failed)}")
        
        logger.info("=" * 70)
    
    async def on_disconnect(self):
        logger.warning("⚠️  DISCONNECTED from Discord")
    
    async def on_resumed(self):
        logger.info("🔄 SESSION RESUMED")
    
    async def close(self):
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
bot = RiskpunkBot()


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
        bot.run(TOKEN)
        
    except discord.LoginFailure:
        logger.critical("❌ LOGIN FAILED - Invalid token!")
        sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("⌨️  Keyboard interrupt")
        sys.exit(0)
        
    except Exception as e:
        logger.critical(f"💥 FATAL ERROR: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)
