import discord
from discord.ext import commands
import random
from utils.database import (
    get_pool, get_player, get_faction,
    update_player_credits, update_player_xp,
    get_all_territories, get_territory
)
from utils.styles import RiskEmbed, NEON_CYAN, NEON_GREEN, NEON_RED, NEON_BLUE, LINE

# Import the visual map function
try:
    from cogs.territory_visual_map import MapView, generate_map_image, create_text_map, PIL_AVAILABLE
    VISUAL_MAP_AVAILABLE = True
except:
    VISUAL_MAP_AVAILABLE = False
    print("[TERRITORY] Warning: Visual map not available")


def territory_card(t, owner_name):
    e = RiskEmbed(title=f"📍 {t['name']}", color=NEON_CYAN)
    e.description = f"`{t['description']}`\n{LINE}"
    e.add_field(name="Owner", value=owner_name, inline=True)
    e.add_field(name="Income", value=f"`{t['income']:,.0f} ₵/wk`", inline=True)
    e.add_field(name="Defense", value=f"`{t['defense']}/100`", inline=True)
    return e


class Territory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    territory_grp = discord.SlashCommandGroup("territory", "Territory warfare commands")

    # ── /territory map ───────────────────────────────────────
    @territory_grp.command(name="map", description="View visual territory control map")
    async def territory_map(self, ctx: discord.ApplicationContext):
        """Visual map - replaces old text list"""
        player = await get_player(ctx.author.id)
        if not player:
            return await ctx.respond("Register first with `/register`.", ephemeral=True)
        
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
        
        # Ultra fallback - simple list
        territories = await get_all_territories()
        embed = RiskEmbed(title="🗺️ RISK CITY TERRITORIES", color=NEON_BLUE)
        embed.description = "Territory overview\n" + LINE
        for t in territories:
            owner_name = "Unclaimed"
            if t["owner_faction"]:
                fac = await get_faction(t["owner_faction"])
                owner_name = fac["name"] if fac else "Unknown"
            status = "🟢" if t["owner_faction"] == player['faction_id'] else "🔴" if t["owner_faction"] else "⚪"
            embed.add_field(
                name=f"{status} {t['name']}",
                value=f"Owner: **{owner_name}** | Def: `{t['defense']}/100` | `{t['income']:,} ₵/wk`",
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
        if t["owner_faction"]:
            fac = await get_faction(t["owner_faction"])
            owner_name = fac["name"] if fac else "Unknown"
        await ctx.respond(embed=territory_card(t, owner_name))

    # ── /territory attack ────────────────────────────────────
    @territory_grp.command(name="attack", description="Attack a territory to seize it")
    @discord.option("territory_key", description="Territory key")
    async def territory_attack(self, ctx: discord.ApplicationContext, territory_key: str):
        player = await get_player(ctx.author.id)
        if not player or not player["faction_id"]:
            await ctx.respond(content="You must join a faction first!", ephemeral=True)
            return
        t = await get_territory(territory_key.lower())
        if not t:
            await ctx.respond(embed=RiskEmbed(title="❌ Not Found", color=NEON_RED), ephemeral=True)
            return
        if t["owner_faction"] == player["faction_id"]:
            await ctx.respond(embed=RiskEmbed(title="Already Yours", description="Your faction controls this.", color=NEON_CYAN), ephemeral=True)
            return
        
        attack_cost = 500
        if player["credits"] < attack_cost:
            await ctx.respond(embed=RiskEmbed(title="💸 Insufficient Funds", description=f"Attack costs `{attack_cost:,} ₵`", color=NEON_RED), ephemeral=True)
            return
        
        await update_player_credits(player['id'], -attack_cost)
        
        # Combat
        player_power = player["atk"] + player["spd"] + random.randint(1, 100)
        territory_defense = t["defense"] + random.randint(1, 100)
        
        if player_power > territory_defense:
            # Victory
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE territories SET owner_faction = $1 WHERE key = $2",
                    player["faction_id"], territory_key.lower()
                )
            
            await update_player_xp(player['id'], 500)
            
            fac = await get_faction(player["faction_id"])
            embed = RiskEmbed(title="⚔️ VICTORY!", color=NEON_GREEN)
            embed.description = (
                f"**{t['name']}** has been captured!\n\n"
                f"Now controlled by **{fac['name'] if fac else 'your faction'}**.\n{LINE}\n"
                f"**Rewards:**\n"
                f"• Territory claimed\n"
                f"• +500 XP\n"
                f"• Weekly income: `{t['income']:,} ₵`"
            )
        else:
            # Defeat
            damage = random.randint(10, 30)
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE players SET hp = GREATEST(0, hp - $1) WHERE id = $2",
                    damage, player['id']
                )
            
            await update_player_xp(player['id'], 100)
            
            embed = RiskEmbed(title="⚔️ DEFEAT", color=NEON_RED)
            embed.description = (
                f"Your assault on **{t['name']}** was repelled!\n\n"
                f"The defenders held their ground.\n{LINE}\n"
                f"**Losses:**\n"
                f"• -{damage} HP\n"
                f"• -{attack_cost} ₵\n"
                f"• +100 XP (participation)"
            )
        
        await ctx.respond(embed=embed)

    # ── /territory fortify ───────────────────────────────────
    @territory_grp.command(name="fortify", description="Strengthen territory defenses (costs credits)")
    @discord.option("territory_key", description="Territory key")
    async def territory_fortify(self, ctx: discord.ApplicationContext, territory_key: str):
        player = await get_player(ctx.author.id)
        if not player or not player["faction_id"]:
            await ctx.respond(content="You must join a faction first!", ephemeral=True)
            return
        
        t = await get_territory(territory_key.lower())
        if not t:
            await ctx.respond(embed=RiskEmbed(title="❌ Not Found", color=NEON_RED), ephemeral=True)
            return
        
        if t["owner_faction"] != player["faction_id"]:
            await ctx.respond(embed=RiskEmbed(title="❌ Not Yours", description="Can only fortify your faction's territories!", color=NEON_RED), ephemeral=True)
            return
        
        if t["defense"] >= 100:
            await ctx.respond(embed=RiskEmbed(title="Max Defense", description="This territory is already at maximum defense.", color=NEON_YELLOW), ephemeral=True)
            return
        
        fortify_cost = 1000
        if player["credits"] < fortify_cost:
            await ctx.respond(embed=RiskEmbed(title="💸 Insufficient Funds", description=f"Fortifying costs `{fortify_cost:,} ₵`", color=NEON_RED), ephemeral=True)
            return
        
        await update_player_credits(player['id'], -fortify_cost)
        
        new_defense = min(100, t["defense"] + 10)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE territories SET defense = $1 WHERE key = $2",
                new_defense, territory_key.lower()
            )
        
        embed = RiskEmbed(title="🛡️ FORTIFIED", color=NEON_GREEN)
        embed.description = (
            f"**{t['name']}** defenses reinforced!\n\n"
            f"Defense increased: `{t['defense']}` → `{new_defense}`\n"
            f"Cost: `{fortify_cost:,} ₵`"
        )
        
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Territory(bot))
