import os
import sys
import logging
import traceback

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)
logger = logging.getLogger('riskpunk')

logger.info("=" * 70)
logger.info("RISKPUNK BOT STARTING")
logger.info("=" * 70)

try:
    import discord
    from discord.ext import commands
    logger.info(f"Discord.py version: {discord.__version__}")
except ImportError as e:
    logger.critical(f"Failed to import discord: {e}")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD = os.getenv("DISCORD_GUILD_ID", "0")
DATABASE_URL = os.getenv("DATABASE_URL", "")

logger.info(f"TOKEN: {'Set' if TOKEN else 'NOT SET'}")
logger.info(f"DATABASE_URL: {'Set' if DATABASE_URL else 'NOT SET'}")
logger.info(f"GUILD_ID: {GUILD if GUILD != '0' else 'Not set'}")

if not TOKEN or not DATABASE_URL:
    logger.critical("Missing required environment variables!")
    sys.exit(1)

try:
    GUILD = int(GUILD) if GUILD != "0" else None
except:
    GUILD = None

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class RiskpunkBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            debug_guilds=[GUILD] if GUILD else None,
        )
        self.cogs_loaded = False
    
    async def on_connect(self):
        logger.info("Connected to Discord!")
    
    async def on_ready(self):
        if self.cogs_loaded:
            logger.info("Bot reconnected")
            return
        
        logger.info("=" * 70)
        logger.info(f"Bot ready: {self.user} (ID: {self.user.id})")
        logger.info(f"Guilds: {len(self.guilds)}")
        logger.info("=" * 70)
        
        logger.info("[1/4] Initializing database...")
        try:
            from utils.database import init_db, get_pool
            await init_db()
            
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            logger.info("  ✅ Database ready")
        except Exception as e:
            logger.error(f"  ❌ Database failed: {e}")
            logger.error(traceback.format_exc())
            return
        
        logger.info("[2/4] Seeding game data...")
        try:
            await self._seed_factions()
            await self._seed_territories()
            logger.info("  ✅ Data seeded")
        except Exception as e:
            logger.error(f"  ⚠️  Seeding error: {e}")
        
        logger.info("[3/4] Loading cogs...")
        cogs = [
            "cogs.player",
            "cogs.implants",
            "cogs.factions",
            "cogs.trading",
            "cogs.equipment",  # NEW: Equipment system
            "cogs.heists",
            "cogs.territory",
            "cogs.events",
            "cogs.skills",
            "cogs.pvp",
            "cogs.story",
            "cogs.leaderboard",
            "cogs.companies",
            "cogs.territory_visual_map",
            "cogs.scheduled_tasks",  # NEW: Automated game systems
        ]
        
        loaded = 0
        for cog in cogs:
            try:
                logger.info(f"  Loading {cog}...")
                self.load_extension(cog)
                logger.info(f"    ✅ Loaded")
                loaded += 1
            except Exception as e:
                logger.error(f"    ❌ Failed: {e}")
                logger.error(f"    {traceback.format_exc()}")
        
        logger.info(f"  Loaded {loaded}/{len(cogs)} cogs")
        
        logger.info("[4/4] Commands will sync automatically...")
        try:
            slash_commands = [cmd for cmd in self.pending_application_commands]
            logger.info(f"  ✅ Registered {len(slash_commands)} slash commands")
            
            if slash_commands:
                cmd_names = [cmd.name for cmd in slash_commands]
                logger.info(f"  Commands: {', '.join(cmd_names[:10])}{'...' if len(cmd_names) > 10 else ''}")
        except Exception as e:
            logger.error(f"  ⚠️  Command listing failed: {e}")
        
        self.cogs_loaded = True
        
        logger.info("=" * 70)
        logger.info("🚀 RISKPUNK IS LIVE")
        logger.info("=" * 70)
    
    async def _seed_factions(self):
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
                logger.info(f"    Seeded {len(FACTIONS_SEED)} factions")
            else:
                logger.info(f"    {count} factions exist")
    
    async def _seed_territories(self):
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
                logger.info(f"    Seeded {len(TERRITORIES_SEED)} territories")
            else:
                logger.info(f"    {count} territories exist")
    
    async def close(self):
        logger.info("Shutting down...")
        try:
            from utils.database import close_pool
            await close_pool()
        except:
            pass
        await super().close()

logger.info("Creating bot instance...")
bot = RiskpunkBot()
logger.info("Bot instance created")

@bot.slash_command(name="help", description="Riskpunk command overview")
async def help_cmd(ctx: discord.ApplicationContext):
    from utils.styles import RiskEmbed, LINE, NEON_CYAN
    embed = RiskEmbed(title="RISKPUNK — Command Guide", color=NEON_CYAN)
    embed.description = f"`Economic Political Simulator — Risk City`\n{LINE}"
    
    sections = {
        "👤 Identity": "/register  /profile  /balance  /heal",
        "🔧 Implants": "/implants list  shop  install  remove",
        "⚙️ Equipment": "/equip list  item  remove",
        "🏢 Factions": "/factions list  join  war  wars",
        "💼 Companies": "/company list  start  status  collect  invest  close",
        "💱 Trading": "/trade board  sell  buy  cancel  /shop  /shopbuy",
        "🚨 Heists": "/heist targets  create  join  execute  list",
        "🗺️  Territory": "/territory map  info  attack  fortify  /map",
        "🧬 Skills": "/skills tree  my  learn  upgrade",
        "⚔️  PvP": "/pvp <@opponent>",
        "📖 Story": "/story play  status  restart",
        "🏆 Leaderboard": "/leaderboard credits  level  rep",
    }
    
    for title, cmds in sections.items():
        embed.add_field(name=title, value=f"`{cmds}`", inline=False)
    
    embed.add_field(
        name="🤖 Automated Systems",
        value=(
            "```\n"
            "• Daily territory income distribution\n"
            "• Random city events every 30 mins\n"
            "• Daily faction war battles\n"
            "```"
        ),
        inline=False
    )
    
    await ctx.respond(embed=embed)

@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error):
    from utils.styles import RiskEmbed, NEON_RED
    logger.error(f"Command error: {error}")
    logger.error(traceback.format_exc())
    
    embed = RiskEmbed(
        title="💥 Error",
        description=f"`{error}`",
        color=NEON_RED
    )
    try:
        await ctx.respond(embed=embed, ephemeral=True)
    except:
        pass

logger.info("Starting bot...")
try:
    bot.run(TOKEN)
except Exception as e:
    logger.critical(f"Fatal error: {e}")
    logger.critical(traceback.format_exc())
    sys.exit(1)
