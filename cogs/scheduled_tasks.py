# cogs/scheduled_tasks.py
# Automated game systems: territory income, random events, faction wars
import discord
from discord.ext import commands, tasks
import random
import logging

from utils.database import get_pool, update_player_credits, get_player
from utils.game_data import RANDOM_EVENTS
from utils.styles import RiskEmbed, NEON_CYAN, NEON_GREEN, NEON_RED, NEON_YELLOW

logger = logging.getLogger('riskpunk')


class ScheduledTasks(commands.Cog):
    """Background tasks for territory income, events, and faction wars"""
    
    def __init__(self, bot):
        self.bot = bot
        self.events_channel_id = None  # Will be set via config or first channel found
        
    @commands.Cog.listener()
    async def on_ready(self):
        """Start all scheduled tasks when bot is ready"""
        if not self.territory_income.is_running():
            self.territory_income.start()
            logger.info("✅ Territory income task started (weekly)")
        
        if not self.random_events.is_running():
            self.random_events.start()
            logger.info("✅ Random events task started (every 30 min)")
        
        if not self.faction_wars.is_running():
            self.faction_wars.start()
            logger.info("✅ Faction wars task started (daily)")
    
    def cog_unload(self):
        """Stop tasks when cog unloads"""
        self.territory_income.cancel()
        self.random_events.cancel()
        self.faction_wars.cancel()
    
    # ── TERRITORY INCOME (Daily) ──────────────────────────
    @tasks.loop(hours=24)  # Every 24 hours (daily)
    async def territory_income(self):
        """Distribute daily income from controlled territories to faction members"""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                # Get all territories with owners
                territories = await conn.fetch(
                    "SELECT * FROM territories WHERE owner_faction IS NOT NULL"
                )
                
                if not territories:
                    logger.info("No territories owned, skipping income distribution")
                    return
                
                # Group by faction
                faction_income = {}
                for terr in territories:
                    faction_id = terr['owner_faction']
                    if faction_id not in faction_income:
                        faction_income[faction_id] = []
                    faction_income[faction_id].append({
                        'name': terr['name'],
                        'income': terr['income']
                    })
                
                # Distribute to faction members
                total_distributed = 0
                for faction_id, terr_list in faction_income.items():
                    # Get faction info
                    faction = await conn.fetchrow("SELECT * FROM factions WHERE id = $1", faction_id)
                    if not faction:
                        continue
                    
                    # Get all faction members
                    members = await conn.fetch(
                        "SELECT * FROM players WHERE faction_id = $1", faction_id
                    )
                    
                    if not members:
                        continue
                    
                    # Calculate total income
                    total_income = sum(t['income'] for t in terr_list)
                    
                    # Divide equally among members
                    per_member = total_income / len(members)
                    
                    # Distribute
                    for member in members:
                        await update_player_credits(member['discord_id'], per_member)
                        total_distributed += per_member
                    
                    logger.info(f"Distributed {total_income:,.0f} ₵ to {len(members)} members of {faction['name']}")
                
                # Announce in a channel
                channel = await self.get_announcement_channel()
                if channel:
                    embed = RiskEmbed(
                        title="💰 DAILY INCOME DISTRIBUTED",
                        description=f"Territory income paid out to faction members.\n**Total: {total_distributed:,.0f} ₵**",
                        color=NEON_GREEN
                    )
                    
                    for faction_id, terr_list in faction_income.items():
                        faction = await conn.fetchrow("SELECT * FROM factions WHERE id = $1", faction_id)
                        if faction:
                            terr_names = ", ".join(t['name'] for t in terr_list)
                            total = sum(t['income'] for t in terr_list)
                            embed.add_field(
                                name=f"{faction['name']}",
                                value=f"`{terr_names}`\n💵 {total:,.0f} ₵",
                                inline=False
                            )
                    
                    await channel.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Territory income distribution failed: {e}")
            import traceback
            traceback.print_exc()
    
    # ── RANDOM EVENTS (Every 30 minutes) ────────────────────────
    @tasks.loop(minutes=30)
    async def random_events(self):
        """Trigger random city events"""
        try:
            # 20% chance to trigger event each cycle
            if random.random() > 0.2:
                return
            
            event = random.choice(RANDOM_EVENTS)
            
            pool = await get_pool()
            async with pool.acquire() as conn:
                # Log the event
                await conn.execute("INSERT INTO event_log (event_key) VALUES ($1)", event['key'])
                
                # Apply effects
                if event['credit_mod'] != 0:
                    # Apply to all players
                    await conn.execute(
                        "UPDATE players SET credits = GREATEST(0, credits + $1)",
                        event['credit_mod']
                    )
                
                if event['rep_mod'] != 0:
                    await conn.execute(
                        "UPDATE players SET rep = rep + $1",
                        event['rep_mod']
                    )
                
                # Special effects
                if event['key'] == 'virus_outbreak':
                    # All players lose 15 HP unless they have a MedKit
                    await conn.execute("""
                        UPDATE players SET hp = GREATEST(0, hp - 15)
                        WHERE id NOT IN (
                            SELECT player_id FROM inventory WHERE item_name = 'MedKit'
                        )
                    """)
                
                elif event['key'] == 'gang_war':
                    # Boost Void Street defense (if it exists in new schema)
                    # This territory might not exist, so try but don't fail
                    try:
                        await conn.execute(
                            "UPDATE territories SET defense = LEAST(100, defense + 20) WHERE key = 'undercity'"
                        )
                    except:
                        pass
            
            # Announce event
            channel = await self.get_announcement_channel()
            if channel:
                embed = RiskEmbed(
                    title=f"⚠️ {event['title']}",
                    description=event['description'],
                    color=NEON_YELLOW
                )
                embed.add_field(name="Effect", value=event['effect'], inline=False)
                await channel.send(embed=embed)
                
            logger.info(f"Random event triggered: {event['key']}")
            
        except Exception as e:
            logger.error(f"Random event failed: {e}")
            import traceback
            traceback.print_exc()
    
    # ── FACTION WARS (Daily combat) ─────────────────────────────
    @tasks.loop(hours=24)
    async def faction_wars(self):
        """Process ongoing faction wars"""
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                # Get active wars
                wars = await conn.fetch(
                    "SELECT * FROM faction_wars WHERE ended_at IS NULL"
                )
                
                if not wars:
                    return
                
                for war in wars:
                    faction_a = await conn.fetchrow("SELECT * FROM factions WHERE id = $1", war['faction_a'])
                    faction_b = await conn.fetchrow("SELECT * FROM factions WHERE id = $1", war['faction_b'])
                    
                    if not faction_a or not faction_b:
                        continue
                    
                    # Get members and calculate total power
                    members_a = await conn.fetch("SELECT * FROM players WHERE faction_id = $1", war['faction_a'])
                    members_b = await conn.fetch("SELECT * FROM players WHERE faction_id = $1", war['faction_b'])
                    
                    power_a = sum(m['atk'] + m['def'] + m['spd'] for m in members_a) if members_a else 0
                    power_b = sum(m['atk'] + m['def'] + m['spd'] for m in members_b) if members_b else 0
                    
                    # Add faction aggression bonus
                    power_a += faction_a['aggression'] * len(members_a)
                    power_b += faction_b['aggression'] * len(members_b)
                    
                    # Add randomness
                    power_a += random.randint(0, 100)
                    power_b += random.randint(0, 100)
                    
                    # Determine winner
                    winner_id = war['faction_a'] if power_a > power_b else war['faction_b']
                    loser_id = war['faction_b'] if power_a > power_b else war['faction_a']
                    winner_name = faction_a['name'] if power_a > power_b else faction_b['name']
                    loser_name = faction_b['name'] if power_a > power_b else faction_a['name']
                    
                    # Winner takes a random territory from loser
                    loser_territories = await conn.fetch(
                        "SELECT * FROM territories WHERE owner_faction = $1",
                        loser_id
                    )
                    
                    captured_territory = None
                    if loser_territories:
                        captured_territory = random.choice(loser_territories)
                        await conn.execute(
                            "UPDATE territories SET owner_faction = $1 WHERE id = $2",
                            winner_id, captured_territory['id']
                        )
                    
                    # Check if war should end (loser has no territories left)
                    remaining = await conn.fetchval(
                        "SELECT COUNT(*) FROM territories WHERE owner_faction = $1",
                        loser_id
                    )
                    
                    if remaining == 0:
                        # War ends, winner declared
                        await conn.execute(
                            "UPDATE faction_wars SET ended_at = CURRENT_TIMESTAMP, winner = $1 WHERE id = $2",
                            winner_id, war['id']
                        )
                        
                        # Announce war end
                        channel = await self.get_announcement_channel()
                        if channel:
                            embed = RiskEmbed(
                                title="🏆 WAR CONCLUDED",
                                description=f"**{winner_name}** has completely conquered **{loser_name}**!",
                                color=NEON_GREEN
                            )
                            await channel.send(embed=embed)
                        
                        logger.info(f"War ended: {winner_name} defeated {loser_name}")
                    else:
                        # War continues, announce battle result
                        channel = await self.get_announcement_channel()
                        if channel:
                            embed = RiskEmbed(
                                title="⚔️ WAR BATTLE",
                                description=f"**{winner_name}** vs **{loser_name}**",
                                color=NEON_RED
                            )
                            embed.add_field(
                                name="Winner",
                                value=f"**{winner_name}** (Power: {power_a if power_a > power_b else power_b})",
                                inline=True
                            )
                            embed.add_field(
                                name="Loser", 
                                value=f"**{loser_name}** (Power: {power_b if power_a > power_b else power_a})",
                                inline=True
                            )
                            if captured_territory:
                                embed.add_field(
                                    name="Territory Captured",
                                    value=f"📍 **{captured_territory['name']}**",
                                    inline=False
                                )
                            await channel.send(embed=embed)
                        
                        logger.info(f"War battle: {winner_name} captured {captured_territory['name'] if captured_territory else 'nothing'}")
                
        except Exception as e:
            logger.error(f"Faction wars processing failed: {e}")
            import traceback
            traceback.print_exc()
    
    # ── HELPER METHODS ──────────────────────────────────────────
    async def get_announcement_channel(self):
        """Get the first available text channel for announcements"""
        if self.events_channel_id:
            channel = self.bot.get_channel(self.events_channel_id)
            if channel:
                return channel
        
        # Find first text channel we can send to
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    self.events_channel_id = channel.id
                    return channel
        
        return None


def setup(bot):
    bot.add_cog(ScheduledTasks(bot))
