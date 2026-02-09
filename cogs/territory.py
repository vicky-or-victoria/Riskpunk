# cogs/territory.py
# ENHANCED TERRITORY SYSTEM - More complex and challenging
import discord
from discord.ext import commands
import random
from datetime import datetime, timedelta
from utils.database import (
    get_pool, get_player, get_faction,
    update_player_credits, update_player_xp,
    get_all_territories, get_territory
)
from utils.styles import RiskEmbed, NEON_CYAN, NEON_GREEN, NEON_RED, NEON_BLUE, NEON_YELLOW, LINE

# Import the visual map function
try:
    from cogs.territory_visual_map import MapView, generate_map_image, create_text_map, PIL_AVAILABLE
    VISUAL_MAP_AVAILABLE = True
except:
    VISUAL_MAP_AVAILABLE = False
    print("[TERRITORY] Warning: Visual map not available")


def territory_card(t, owner_name, recent_activity=None):
    """Enhanced territory card with more details"""
    e = RiskEmbed(title=f"📍 {t['name']}", color=NEON_CYAN)
    
    # Add territory tier/value indicator
    tier = "★" * min(5, int(t['income'] / 200))
    
    desc = f"`{t['description']}`\n{LINE}\n"
    desc += f"**Tier:** {tier or '☆'} (Value based on income)\n"
    if recent_activity:
        desc += f"**Status:** {recent_activity}\n"
    e.description = desc
    
    e.add_field(name="🏢 Owner", value=owner_name, inline=True)
    e.add_field(name="💰 Income", value=f"`{t['income']:,.0f} ₵/day`", inline=True)
    e.add_field(name="🛡️ Defense", value=f"`{t['defense']}/100`", inline=True)
    
    # New fields
    if t.get('garrison_size'):
        e.add_field(name="👥 Garrison", value=f"`{t['garrison_size']} troops`", inline=True)
    if t.get('last_attacked'):
        e.add_field(name="⚔️ Last Attack", value=f"<t:{int(t['last_attacked'].timestamp())}:R>", inline=True)
    if t.get('connected_to'):
        e.add_field(name="🗺️ Connected To", value=t['connected_to'], inline=False)
    
    return e


class Territory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Track ongoing sieges (territory_key -> {attacker_faction, start_time, siege_hp})
        self.active_sieges = {}
    
    territory_grp = discord.SlashCommandGroup("territory", "Territory warfare commands")

    # ── /territory map ───────────────────────────────────────
    @territory_grp.command(name="map", description="View visual territory control map")
    async def territory_map(self, ctx: discord.ApplicationContext):
        """Visual map showing all territories and control"""
        player = await get_player(ctx.author.id)
        if not player:
            return await ctx.respond("⚠️ Register first with `/register`.", ephemeral=True)
        
        await ctx.defer()
        
        # Try visual map first
        if VISUAL_MAP_AVAILABLE and PIL_AVAILABLE:
            try:
                img = await generate_map_image(player['faction_id'])
                if img:
                    file = discord.File(img, filename="map.png")
                    embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
                    embed.description = "Click district buttons below to interact with territories."
                    embed.set_image(url="attachment://map.png")
                    view = MapView(player['id'], player['faction_id'], has_image=True)
                    return await ctx.followup.send(embed=embed, file=file, view=view)
            except Exception as e:
                print(f"[TERRITORY MAP] Image generation failed: {e}")
        
        # Fallback to text map
        if VISUAL_MAP_AVAILABLE:
            try:
                text_map = await create_text_map(player['faction_id'])
                embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
                embed.description = text_map
                view = MapView(player['id'], player['faction_id'], has_image=False)
                return await ctx.followup.send(embed=embed, view=view)
            except Exception as e:
                print(f"[TERRITORY MAP] Text map failed: {e}")
        
        # Ultra fallback - enhanced list with more info
        territories = await get_all_territories()
        embed = RiskEmbed(title="🗺️ RISK CITY TERRITORIES", color=NEON_BLUE)
        embed.description = "Territory overview - control the city grid\n" + LINE
        
        for t in territories:
            owner_name = "Unclaimed"
            if t["owner_faction"]:
                fac = await get_faction(t["owner_faction"])
                owner_name = fac["name"] if fac else "Unknown"
            
            status = "🟢" if t["owner_faction"] == player['faction_id'] else "🔴" if t["owner_faction"] else "⚪"
            
            # Show siege status if active
            siege_indicator = ""
            if t['key'] in self.active_sieges:
                siege_indicator = " **[UNDER SIEGE]**"
            
            embed.add_field(
                name=f"{status} {t['name']}{siege_indicator}",
                value=f"Owner: **{owner_name}** | Def: `{t['defense']}/100` | `{t['income']:,} ₵/day`",
                inline=False
            )
        await ctx.followup.send(embed=embed)

    # ── /territory info ──────────────────────────────────────
    @territory_grp.command(name="info", description="Detailed info on a single territory.")
    @discord.option("territory_key", description="Territory key (e.g. industrial_sector)")
    async def territory_info(self, ctx: discord.ApplicationContext, territory_key: str):
        t = await get_territory(territory_key.lower())
        if not t:
            await ctx.respond(embed=RiskEmbed(title="❌ Not Found", description=f"`{territory_key}` is not a valid territory.", color=NEON_RED), ephemeral=True)
            return
        
        owner_name = "Unclaimed"
        recent_activity = None
        
        if t["owner_faction"]:
            fac = await get_faction(t["owner_faction"])
            owner_name = fac["name"] if fac else "Unknown"
        
        # Check for active siege
        if territory_key.lower() in self.active_sieges:
            siege = self.active_sieges[territory_key.lower()]
            attacker_fac = await get_faction(siege['attacker_faction'])
            recent_activity = f"⚔️ **UNDER SIEGE** by {attacker_fac['name'] if attacker_fac else 'Unknown'}"
        
        await ctx.respond(embed=territory_card(t, owner_name, recent_activity))

    # ── /territory attack ────────────────────────────────────
    @territory_grp.command(name="attack", description="Launch an attack on a territory")
    @discord.option("territory_key", description="Territory key")
    @discord.option("attack_type", description="Type of attack", choices=["raid", "assault", "siege"])
    async def territory_attack(self, ctx: discord.ApplicationContext, territory_key: str, attack_type: str):
        """
        ENHANCED ATTACK SYSTEM:
        - RAID: Quick hit-and-run, low cost, can steal credits, doesn't capture
        - ASSAULT: Standard attack, medium cost, can capture weakened territories
        - SIEGE: Multi-phase attack, high cost, required for heavily defended territories
        """
        player = await get_player(ctx.author.id)
        
        # Must be registered and in a faction
        if not player:
            await ctx.respond(content="⚠️ You must register first with `/register`.", ephemeral=True)
            return
        
        if not player["faction_id"]:
            await ctx.respond(
                embed=RiskEmbed(
                    title="❌ No Faction", 
                    description="You must join a faction to participate in territorial warfare.\n\nUse `/faction join` to align yourself.",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        t = await get_territory(territory_key.lower())
        if not t:
            await ctx.respond(embed=RiskEmbed(title="❌ Not Found", color=NEON_RED), ephemeral=True)
            return
        
        if t["owner_faction"] == player["faction_id"]:
            await ctx.respond(
                embed=RiskEmbed(
                    title="Already Controlled", 
                    description="Your faction already controls this territory. Use `/territory fortify` to strengthen its defenses.",
                    color=NEON_CYAN
                ), 
                ephemeral=True
            )
            return
        
        # Get faction member count for scaling
        pool = await get_pool()
        async with pool.acquire() as conn:
            faction_members = await conn.fetch(
                "SELECT * FROM players WHERE faction_id = $1", 
                player["faction_id"]
            )
        
        member_count = len(faction_members)
        
        # ATTACK TYPE: RAID
        if attack_type == "raid":
            cost = 300
            if player["credits"] < cost:
                await ctx.respond(
                    embed=RiskEmbed(
                        title="💸 Insufficient Funds", 
                        description=f"Raid costs `{cost:,} ₵`", 
                        color=NEON_RED
                    ), 
                    ephemeral=True
                )
                return
            
            await update_player_credits(player['id'], -cost)
            
            # Raid success based on speed and luck
            player_power = player["spd"] * 2 + player["atk"] + random.randint(1, 80)
            territory_defense = t["defense"] + random.randint(1, 60)
            
            if player_power > territory_defense:
                # Successful raid - steal some credits based on territory income
                stolen_credits = int(t["income"] * random.uniform(0.3, 0.7))
                await update_player_credits(player['id'], stolen_credits)
                await update_player_xp(player['id'], 150)
                
                embed = RiskEmbed(title="⚡ RAID SUCCESSFUL", color=NEON_GREEN)
                embed.description = (
                    f"Your swift strike on **{t['name']}** succeeded!\n\n"
                    f"You hit their supply lines and escaped before reinforcements arrived.\n{LINE}\n"
                    f"**Rewards:**\n"
                    f"• Stolen: `{stolen_credits:,} ₵`\n"
                    f"• +150 XP\n"
                    f"• Territory weakened (defense -5)"
                )
                
                # Weaken territory defense slightly
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE territories SET defense = GREATEST(0, defense - 5) WHERE key = $1",
                        territory_key.lower()
                    )
            else:
                # Failed raid
                damage = random.randint(15, 35)
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE players SET hp = GREATEST(0, hp - $1) WHERE id = $2",
                        damage, player['id']
                    )
                
                embed = RiskEmbed(title="⚡ RAID FAILED", color=NEON_RED)
                embed.description = (
                    f"Your raid on **{t['name']}** was detected!\n\n"
                    f"Their defenses were ready and you had to retreat.\n{LINE}\n"
                    f"**Losses:**\n"
                    f"• -{damage} HP\n"
                    f"• -{cost} ₵"
                )
            
            await ctx.respond(embed=embed)
        
        # ATTACK TYPE: ASSAULT
        elif attack_type == "assault":
            cost = 800
            if player["credits"] < cost:
                await ctx.respond(
                    embed=RiskEmbed(
                        title="💸 Insufficient Funds", 
                        description=f"Assault costs `{cost:,} ₵`", 
                        color=NEON_RED
                    ), 
                    ephemeral=True
                )
                return
            
            # Assault requires faction support - you need at least 2 faction members
            if member_count < 2:
                await ctx.respond(
                    embed=RiskEmbed(
                        title="⚠️ Insufficient Forces",
                        description="Assaults require at least 2 faction members. Recruit more runners!",
                        color=NEON_YELLOW
                    ),
                    ephemeral=True
                )
                return
            
            await update_player_credits(player['id'], -cost)
            
            # Assault success based on combined stats and faction size
            faction_bonus = member_count * 15
            player_power = (player["atk"] + player["def"] + player["spd"]) + faction_bonus + random.randint(1, 100)
            territory_defense = t["defense"] * 2 + random.randint(1, 100)
            
            if player_power > territory_defense:
                # Victory - capture the territory
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE territories SET owner_faction = $1, defense = 30, last_attacked = CURRENT_TIMESTAMP WHERE key = $2",
                        player["faction_id"], territory_key.lower()
                    )
                
                await update_player_xp(player['id'], 800)
                
                fac = await get_faction(player["faction_id"])
                embed = RiskEmbed(title="⚔️ ASSAULT VICTORY!", color=NEON_GREEN)
                embed.description = (
                    f"**{t['name']}** has been captured in a fierce assault!\n\n"
                    f"Now controlled by **{fac['name'] if fac else 'your faction'}**.\n{LINE}\n"
                    f"**Rewards:**\n"
                    f"• Territory captured\n"
                    f"• +800 XP\n"
                    f"• Daily income: `{t['income']:,} ₵`\n"
                    f"• Defense reset to 30 (needs fortification)"
                )
            else:
                # Defeat
                damage = random.randint(20, 45)
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE players SET hp = GREATEST(0, hp - $1) WHERE id = $2",
                        damage, player['id']
                    )
                
                await update_player_xp(player['id'], 200)
                
                embed = RiskEmbed(title="⚔️ ASSAULT REPELLED", color=NEON_RED)
                embed.description = (
                    f"Your assault on **{t['name']}** failed!\n\n"
                    f"The defenders held their position and pushed you back.\n{LINE}\n"
                    f"**Losses:**\n"
                    f"• -{damage} HP\n"
                    f"• -{cost} ₵\n"
                    f"• +200 XP (combat experience)"
                )
            
            await ctx.respond(embed=embed)
        
        # ATTACK TYPE: SIEGE
        elif attack_type == "siege":
            # Sieges are for heavily defended territories (defense > 60)
            if t["defense"] < 60:
                await ctx.respond(
                    embed=RiskEmbed(
                        title="⚠️ Siege Not Required",
                        description=f"**{t['name']}** (Def: {t['defense']}) can be taken with an assault. Sieges are for heavily fortified territories (60+ defense).",
                        color=NEON_YELLOW
                    ),
                    ephemeral=True
                )
                return
            
            cost = 2000
            if player["credits"] < cost:
                await ctx.respond(
                    embed=RiskEmbed(
                        title="💸 Insufficient Funds",
                        description=f"Starting a siege costs `{cost:,} ₵` for supplies and troops.",
                        color=NEON_RED
                    ),
                    ephemeral=True
                )
                return
            
            # Sieges require a larger faction
            if member_count < 3:
                await ctx.respond(
                    embed=RiskEmbed(
                        title="⚠️ Insufficient Forces",
                        description="Sieges require at least 3 faction members. Rally more support!",
                        color=NEON_YELLOW
                    ),
                    ephemeral=True
                )
                return
            
            # Check if there's already an active siege
            if territory_key.lower() in self.active_sieges:
                existing_siege = self.active_sieges[territory_key.lower()]
                if existing_siege['attacker_faction'] == player['faction_id']:
                    await ctx.respond(
                        embed=RiskEmbed(
                            title="⚠️ Siege Already Active",
                            description=f"Your faction is already besieging **{t['name']}**. Use `/territory siege_status` to check progress.",
                            color=NEON_YELLOW
                        ),
                        ephemeral=True
                    )
                else:
                    await ctx.respond(
                        embed=RiskEmbed(
                            title="⚠️ Territory Under Siege",
                            description=f"**{t['name']}** is already under siege by another faction.",
                            color=NEON_YELLOW
                        ),
                        ephemeral=True
                    )
                return
            
            await update_player_credits(player['id'], -cost)
            
            # Start the siege
            self.active_sieges[territory_key.lower()] = {
                'attacker_faction': player['faction_id'],
                'start_time': datetime.utcnow(),
                'siege_hp': 100,  # Siege needs to wear down defense
                'territory_defense': t['defense']
            }
            
            fac = await get_faction(player["faction_id"])
            embed = RiskEmbed(title="🏰 SIEGE INITIATED", color=NEON_CYAN)
            embed.description = (
                f"**{fac['name'] if fac else 'Your faction'}** has begun a siege of **{t['name']}**!\n\n"
                f"This is a war of attrition. The siege will last several phases.\n{LINE}\n"
                f"**Siege Info:**\n"
                f"• Territory Defense: `{t['defense']}`\n"
                f"• Siege HP: `100/100`\n"
                f"• Cost: `{cost:,} ₵` (initial)\n\n"
                f"**Next Steps:**\n"
                f"Faction members can use `/territory siege_attack` to continue the assault.\n"
                f"Each attack costs credits but wears down the defense.\n"
                f"The siege succeeds when Siege HP reaches 0."
            )
            
            await ctx.respond(embed=embed)

    # ── /territory siege_attack ──────────────────────────────
    @territory_grp.command(name="siege_attack", description="Continue an ongoing siege")
    @discord.option("territory_key", description="Territory under siege")
    async def siege_attack(self, ctx: discord.ApplicationContext, territory_key: str):
        """Attack during an active siege"""
        player = await get_player(ctx.author.id)
        
        if not player or not player["faction_id"]:
            await ctx.respond(content="You must be in a faction to participate in sieges.", ephemeral=True)
            return
        
        if territory_key.lower() not in self.active_sieges:
            await ctx.respond(
                embed=RiskEmbed(
                    title="❌ No Active Siege",
                    description=f"There is no active siege on **{territory_key}**.",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        siege = self.active_sieges[territory_key.lower()]
        
        if siege['attacker_faction'] != player['faction_id']:
            await ctx.respond(
                embed=RiskEmbed(
                    title="❌ Not Your Siege",
                    description="This siege is being conducted by another faction.",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        cost = 500
        if player["credits"] < cost:
            await ctx.respond(
                embed=RiskEmbed(
                    title="💸 Insufficient Funds",
                    description=f"Siege attacks cost `{cost:,} ₵` for ammunition and supplies.",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        await update_player_credits(player['id'], -cost)
        
        # Calculate damage to siege HP
        damage = random.randint(15, 30) + (player['atk'] // 2)
        siege['siege_hp'] -= damage
        
        # Random chance of taking damage
        if random.random() < 0.3:
            hp_loss = random.randint(10, 20)
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE players SET hp = GREATEST(0, hp - $1) WHERE id = $2",
                    hp_loss, player['id']
                )
            damage_msg = f"\n• Casualties: -{hp_loss} HP"
        else:
            damage_msg = ""
        
        # Check if siege is complete
        if siege['siege_hp'] <= 0:
            # Siege successful - capture the territory
            t = await get_territory(territory_key.lower())
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE territories SET owner_faction = $1, defense = 25, last_attacked = CURRENT_TIMESTAMP WHERE key = $2",
                    player["faction_id"], territory_key.lower()
                )
            
            # Remove siege from active list
            del self.active_sieges[territory_key.lower()]
            
            await update_player_xp(player['id'], 1200)
            
            fac = await get_faction(player["faction_id"])
            embed = RiskEmbed(title="🏆 SIEGE VICTORY!", color=NEON_GREEN)
            embed.description = (
                f"The siege of **{t['name']}** is complete!\n\n"
                f"After sustained assault, the defenders have surrendered.\n"
                f"**{fac['name'] if fac else 'Your faction'}** now controls this strategic position.\n{LINE}\n"
                f"**Rewards:**\n"
                f"• Territory captured\n"
                f"• +1200 XP\n"
                f"• Daily income: `{t['income']:,} ₵`\n"
                f"• Defense heavily damaged (25) - needs fortification"
            )
        else:
            # Siege continues
            embed = RiskEmbed(title="🏰 SIEGE CONTINUES", color=NEON_CYAN)
            embed.description = (
                f"Your forces bombard **{territory_key}** defenses!\n\n"
                f"The siege wears on...\n{LINE}\n"
                f"**Damage Dealt:** -{damage} to siege HP\n"
                f"**Remaining:** `{max(0, siege['siege_hp'])}/100` siege HP{damage_msg}\n\n"
                f"Continue the assault with more `/territory siege_attack` commands!"
            )
        
        await ctx.respond(embed=embed)

    # ── /territory fortify ───────────────────────────────────
    @territory_grp.command(name="fortify", description="Strengthen territory defenses (costs credits)")
    @discord.option("territory_key", description="Territory key")
    @discord.option("amount", description="Defense points to add (each costs 100₵)", min_value=1, max_value=20)
    async def territory_fortify(self, ctx: discord.ApplicationContext, territory_key: str, amount: int = 5):
        """Enhanced fortification with variable amounts"""
        player = await get_player(ctx.author.id)
        
        if not player or not player["faction_id"]:
            await ctx.respond(
                embed=RiskEmbed(
                    title="❌ No Faction",
                    description="You must be in a faction to fortify territories.",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        t = await get_territory(territory_key.lower())
        if not t:
            await ctx.respond(embed=RiskEmbed(title="❌ Not Found", color=NEON_RED), ephemeral=True)
            return
        
        if t["owner_faction"] != player["faction_id"]:
            await ctx.respond(
                embed=RiskEmbed(
                    title="❌ Not Yours",
                    description="Can only fortify your faction's territories!",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        if t["defense"] >= 100:
            await ctx.respond(
                embed=RiskEmbed(
                    title="Maximum Defense",
                    description="This territory is already at maximum defense (100).",
                    color=NEON_YELLOW
                ),
                ephemeral=True
            )
            return
        
        # Cost scales: 100₵ per defense point
        fortify_cost = amount * 100
        
        # Cap amount to not exceed 100 defense
        actual_amount = min(amount, 100 - t["defense"])
        actual_cost = actual_amount * 100
        
        if player["credits"] < actual_cost:
            await ctx.respond(
                embed=RiskEmbed(
                    title="💸 Insufficient Funds",
                    description=f"Fortifying by {actual_amount} defense costs `{actual_cost:,} ₵`",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        await update_player_credits(player['id'], -actual_cost)
        
        new_defense = t["defense"] + actual_amount
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE territories SET defense = $1 WHERE key = $2",
                new_defense, territory_key.lower()
            )
        
        embed = RiskEmbed(title="🛡️ DEFENSES REINFORCED", color=NEON_GREEN)
        embed.description = (
            f"**{t['name']}** fortifications strengthened!\n\n"
            f"Defensive structures upgraded.\n{LINE}\n"
            f"**Changes:**\n"
            f"• Defense: `{t['defense']}` → `{new_defense}`\n"
            f"• Investment: `{actual_cost:,} ₵`\n"
            f"• XP Gained: +{actual_amount * 10}"
        )
        
        await update_player_xp(player['id'], actual_amount * 10)
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Territory(bot))