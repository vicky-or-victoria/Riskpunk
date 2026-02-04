import discord
from discord.ext import commands
from discord.ui import Button, View
from PIL import Image, ImageDraw, ImageFont
import io
import asyncio

from utils.database import (
    get_pool,
    get_player,
    get_faction,
    update_player_credits,
    update_player_xp
)
from utils.styles import RiskEmbed, NEON_CYAN, NEON_GREEN, NEON_RED, NEON_YELLOW

# Territory positions on the map (x, y, width, height)
TERRITORY_POSITIONS = {
    "industrial_sector": {"x": 50, "y": 50, "w": 200, "h": 150},
    "chrome_district": {"x": 280, "y": 50, "w": 200, "h": 150},
    "downtown_core": {"x": 510, "y": 50, "w": 200, "h": 150},
    "port_authority": {"x": 50, "y": 230, "w": 200, "h": 150},
    "central_plaza": {"x": 280, "y": 230, "w": 200, "h": 150},
    "corp_towers": {"x": 510, "y": 230, "w": 200, "h": 150},
    "undercity": {"x": 50, "y": 410, "w": 200, "h": 150},
    "tech_quarter": {"x": 280, "y": 410, "w": 200, "h": 150},
    "skyline_heights": {"x": 510, "y": 410, "w": 200, "h": 150}
}

# Faction colors for map visualization
FACTION_MAP_COLORS = {
    "omnicorp": (91, 94, 166),      # Purple-blue
    "solarflare": (255, 107, 0),    # Orange
    "netrunners": (0, 255, 255),    # Cyan
    "ironveil": (192, 192, 192),    # Silver
    "phantomcell": (155, 89, 182),  # Purple
    "neutral": (100, 100, 100)      # Gray
}

async def generate_map_image(player_faction_id=None):
    """Generate the actual map image with PIL"""
    # Create dark cyberpunk background
    width, height = 760, 610
    img = Image.new('RGB', (width, height), color=(10, 14, 26))  # Dark navy
    draw = ImageDraw.Draw(img)
    
    # Try to load a font, fallback to default
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Get territory data from database
    pool = await get_pool()
    async with pool.acquire() as conn:
        territories = await conn.fetch("SELECT * FROM territories ORDER BY id")
    
    # Draw grid lines (cyberpunk aesthetic)
    grid_color = (0, 255, 255, 30)  # Cyan with transparency
    for x in range(0, width, 40):
        draw.line([(x, 0), (x, height)], fill=(20, 30, 50), width=1)
    for y in range(0, height, 40):
        draw.line([(0, y), (width, y)], fill=(20, 30, 50), width=1)
    
    # Draw each territory
    for territory in territories:
        pos = TERRITORY_POSITIONS.get(territory['key'])
        if not pos:
            continue
        
        x, y, w, h = pos['x'], pos['y'], pos['w'], pos['h']
        
        # Determine color based on owner
        if territory['owner_faction']:
            faction = await get_faction(territory['owner_faction'])
            if faction:
                color = FACTION_MAP_COLORS.get(faction['key'], FACTION_MAP_COLORS['neutral'])
                is_player_faction = (territory['owner_faction'] == player_faction_id)
            else:
                color = FACTION_MAP_COLORS['neutral']
                is_player_faction = False
        else:
            color = FACTION_MAP_COLORS['neutral']
            is_player_faction = False
        
        # Draw territory background
        alpha = 180 if is_player_faction else 120
        bg_color = (*color, alpha)
        
        # Create semi-transparent overlay
        overlay = Image.new('RGBA', (w-10, h-10), (*color, alpha))
        img.paste(overlay, (x+5, y+5), overlay)
        
        # Draw border
        border_color = (0, 255, 255) if is_player_faction else (color[0]+50, color[1]+50, color[2]+50)
        border_width = 3 if is_player_faction else 2
        draw.rectangle([x, y, x+w, y+h], outline=border_color, width=border_width)
        
        # Draw territory name
        name_lines = territory['name'].split()
        name_y = y + 10
        for line in name_lines:
            draw.text((x + w//2, name_y), line, fill=(255, 255, 255), font=label_font, anchor="mt")
            name_y += 16
        
        # Draw owner info
        owner_text = "NEUTRAL"
        if territory['owner_faction']:
            faction = await get_faction(territory['owner_faction'])
            if faction:
                owner_text = faction['name'].upper()
        
        draw.text((x + w//2, y + h - 40), owner_text, fill=(200, 200, 200), font=small_font, anchor="mt")
        
        # Draw defense bar
        defense = territory['defense']
        bar_width = w - 40
        bar_height = 8
        bar_x = x + 20
        bar_y = y + h - 20
        
        # Background bar
        draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], fill=(50, 50, 50))
        
        # Defense fill
        fill_width = int((defense / 100) * bar_width)
        bar_color = (0, 255, 100) if defense > 70 else (255, 255, 0) if defense > 40 else (255, 100, 100)
        draw.rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], fill=bar_color)
        
        # Defense number
        draw.text((x + w//2, bar_y - 10), f"DEF: {defense}", fill=(150, 150, 150), font=small_font, anchor="mt")
    
    # Add title
    title_text = "RISK CITY - TERRITORY CONTROL"
    draw.text((width//2, 15), title_text, fill=(0, 255, 255), font=title_font, anchor="mt")
    
    # Add legend
    legend_x = 20
    legend_y = height - 30
    draw.text((legend_x, legend_y), "■ Your Faction", fill=(0, 255, 255), font=small_font)
    draw.text((legend_x + 120, legend_y), "■ Enemy", fill=(255, 100, 100), font=small_font)
    draw.text((legend_x + 200, legend_y), "■ Neutral", fill=(100, 100, 100), font=small_font)
    
    # Convert to bytes for Discord
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes


class VisualMapView(View):
    def __init__(self, player_id, player_faction_id):
        super().__init__(timeout=300)
        self.player_id = player_id
        self.player_faction_id = player_faction_id
        self.selected_territory = None
    
    @discord.ui.button(label="Industrial Sector", style=discord.ButtonStyle.secondary, row=0)
    async def industrial_btn(self, button: Button, interaction: discord.Interaction):
        await self.show_territory_detail(interaction, "industrial_sector")
    
    @discord.ui.button(label="Chrome District", style=discord.ButtonStyle.secondary, row=0)
    async def chrome_btn(self, button: Button, interaction: discord.Interaction):
        await self.show_territory_detail(interaction, "chrome_district")
    
    @discord.ui.button(label="Downtown Core", style=discord.ButtonStyle.secondary, row=0)
    async def downtown_btn(self, button: Button, interaction: discord.Interaction):
        await self.show_territory_detail(interaction, "downtown_core")
    
    @discord.ui.button(label="Port Authority", style=discord.ButtonStyle.secondary, row=1)
    async def port_btn(self, button: Button, interaction: discord.Interaction):
        await self.show_territory_detail(interaction, "port_authority")
    
    @discord.ui.button(label="Central Plaza", style=discord.ButtonStyle.secondary, row=1)
    async def plaza_btn(self, button: Button, interaction: discord.Interaction):
        await self.show_territory_detail(interaction, "central_plaza")
    
    @discord.ui.button(label="Corp Towers", style=discord.ButtonStyle.secondary, row=1)
    async def towers_btn(self, button: Button, interaction: discord.Interaction):
        await self.show_territory_detail(interaction, "corp_towers")
    
    @discord.ui.button(label="Undercity", style=discord.ButtonStyle.secondary, row=2)
    async def undercity_btn(self, button: Button, interaction: discord.Interaction):
        await self.show_territory_detail(interaction, "undercity")
    
    @discord.ui.button(label="Tech Quarter", style=discord.ButtonStyle.secondary, row=2)
    async def tech_btn(self, button: Button, interaction: discord.Interaction):
        await self.show_territory_detail(interaction, "tech_quarter")
    
    @discord.ui.button(label="Skyline Heights", style=discord.ButtonStyle.secondary, row=2)
    async def skyline_btn(self, button: Button, interaction: discord.Interaction):
        await self.show_territory_detail(interaction, "skyline_heights")
    
    @discord.ui.button(label="🔄 Refresh Map", style=discord.ButtonStyle.primary, row=3)
    async def refresh_btn(self, button: Button, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Regenerate map image
        map_image = await generate_map_image(self.player_faction_id)
        file = discord.File(map_image, filename="risk_city_map.png")
        
        embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
        embed.description = "Real-time territory control. Click districts below for actions."
        embed.set_image(url="attachment://risk_city_map.png")
        
        await interaction.edit_original_response(embed=embed, file=file, view=self)
    
    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger, row=3)
    async def close_btn(self, button: Button, interaction: discord.Interaction):
        await interaction.response.edit_message(view=None)
        self.stop()
    
    async def show_territory_detail(self, interaction: discord.Interaction, territory_key: str):
        """Show detailed view of a territory"""
        pool = await get_pool()
        async with pool.acquire() as conn:
            territory = await conn.fetchrow(
                "SELECT * FROM territories WHERE key = $1",
                territory_key
            )
        
        if not territory:
            return await interaction.response.send_message("Territory not found!", ephemeral=True)
        
        owner_name = "Neutral"
        owner_color = NEON_CYAN
        if territory['owner_faction']:
            faction = await get_faction(territory['owner_faction'])
            if faction:
                owner_name = faction['name']
                owner_color = int(faction['color'].replace('#', '0x'), 16)
        
        embed = RiskEmbed(title=f"📍 {territory['name']}", color=owner_color)
        embed.description = f"{territory['description']}\n━━━━━━━━━━━━━━━━"
        
        # Defense bar
        defense_bar = "█" * (territory['defense'] // 10) + "░" * (10 - territory['defense'] // 10)
        
        embed.add_field(name="Controller", value=f"`{owner_name}`", inline=True)
        embed.add_field(name="Weekly Income", value=f"`{territory['income']:,.0f} ₵`", inline=True)
        embed.add_field(name="Defense", value=f"{defense_bar} `{territory['defense']}/100`", inline=False)
        
        # Show available actions
        is_player_faction = (territory['owner_faction'] == self.player_faction_id)
        if is_player_faction:
            embed.add_field(
                name="🛡️ Your Territory",
                value="Click **Fortify** to strengthen defenses.",
                inline=False
            )
        else:
            embed.add_field(
                name="⚔️ Enemy/Neutral Territory",
                value="Click **Attack** to attempt capture.",
                inline=False
            )
        
        # Create action view
        action_view = TerritoryActionView(
            self.player_id, 
            self.player_faction_id, 
            territory_key, 
            self
        )
        
        await interaction.response.edit_message(embed=embed, view=action_view)


class TerritoryActionView(View):
    def __init__(self, player_id, player_faction_id, territory_key, parent_view):
        super().__init__(timeout=300)
        self.player_id = player_id
        self.player_faction_id = player_faction_id
        self.territory_key = territory_key
        self.parent_view = parent_view
    
    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.danger)
    async def attack_btn(self, button: Button, interaction: discord.Interaction):
        await self.attack_territory(interaction)
    
    @discord.ui.button(label="🛡️ Fortify", style=discord.ButtonStyle.success)
    async def fortify_btn(self, button: Button, interaction: discord.Interaction):
        await self.fortify_territory(interaction)
    
    @discord.ui.button(label="◀️ Back to Map", style=discord.ButtonStyle.secondary)
    async def back_btn(self, button: Button, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Regenerate map
        map_image = await generate_map_image(self.player_faction_id)
        file = discord.File(map_image, filename="risk_city_map.png")
        
        embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
        embed.description = "Real-time territory control. Click districts below for actions."
        embed.set_image(url="attachment://risk_city_map.png")
        
        await interaction.edit_original_response(embed=embed, file=file, view=self.parent_view)
    
    async def attack_territory(self, interaction: discord.Interaction):
        """Attack logic"""
        player = await get_player(interaction.user.id)
        
        if not self.player_faction_id:
            await interaction.response.send_message("Join a faction first!", ephemeral=True)
            return
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            territory = await conn.fetchrow(
                "SELECT * FROM territories WHERE key = $1",
                self.territory_key
            )
        
        if territory['owner_faction'] == self.player_faction_id:
            await interaction.response.send_message("You already control this!", ephemeral=True)
            return
        
        cost = 500
        if player['credits'] < cost:
            await interaction.response.send_message(f"Attacking costs {cost} ₵!", ephemeral=True)
            return
        
        await update_player_credits(player['id'], -cost)
        
        # Combat
        import random
        player_power = player['atk'] + player['spd'] + random.randint(1, 100)
        territory_defense = territory['defense'] + random.randint(1, 100)
        
        if player_power > territory_defense:
            # Victory
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE territories SET owner_faction = $1 WHERE key = $2",
                    self.player_faction_id, self.territory_key
                )
            
            await update_player_xp(player['id'], 500)
            
            embed = RiskEmbed(title="⚔️ VICTORY!", color=NEON_GREEN)
            embed.description = (
                f"**{territory['name']}** captured!\n\n"
                f"Territory now controlled by your faction.\n"
                f"**Rewards:** Territory claimed, +500 XP"
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
                f"Assault on **{territory['name']}** failed!\n\n"
                f"Defenders held the line.\n"
                f"**Losses:** -{damage} HP, -{cost} ₵, +100 XP"
            )
        
        await interaction.response.edit_message(embed=embed, view=None)
        await asyncio.sleep(5)
        
        # Return to map
        map_image = await generate_map_image(self.player_faction_id)
        file = discord.File(map_image, filename="risk_city_map.png")
        
        map_embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
        map_embed.description = "Real-time territory control. Click districts below for actions."
        map_embed.set_image(url="attachment://risk_city_map.png")
        
        await interaction.edit_original_response(embed=map_embed, file=file, view=self.parent_view)
    
    async def fortify_territory(self, interaction: discord.Interaction):
        """Fortify logic"""
        player = await get_player(interaction.user.id)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            territory = await conn.fetchrow(
                "SELECT * FROM territories WHERE key = $1",
                self.territory_key
            )
        
        if territory['owner_faction'] != self.player_faction_id:
            await interaction.response.send_message("Can only fortify your faction's territories!", ephemeral=True)
            return
        
        if territory['defense'] >= 100:
            await interaction.response.send_message("Already at max defense!", ephemeral=True)
            return
        
        cost = 1000
        if player['credits'] < cost:
            await interaction.response.send_message(f"Fortifying costs {cost} ₵!", ephemeral=True)
            return
        
        await update_player_credits(player['id'], -cost)
        
        new_defense = min(100, territory['defense'] + 10)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE territories SET defense = $1 WHERE key = $2",
                new_defense, self.territory_key
            )
        
        embed = RiskEmbed(title="🛡️ FORTIFIED", color=NEON_GREEN)
        embed.description = (
            f"**{territory['name']}** defenses reinforced!\n\n"
            f"Defense: {territory['defense']} → {new_defense}\n"
            f"Cost: {cost} ₵"
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        await asyncio.sleep(3)
        
        map_image = await generate_map_image(self.player_faction_id)
        file = discord.File(map_image, filename="risk_city_map.png")
        
        map_embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
        map_embed.description = "Real-time territory control. Click districts below for actions."
        map_embed.set_image(url="attachment://risk_city_map.png")
        
        await interaction.edit_original_response(embed=map_embed, file=file, view=self.parent_view)


class VisualTerritoryMap(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.slash_command(name="map", description="View visual territory control map")
    async def open_visual_map(self, ctx: discord.ApplicationContext):
        player = await get_player(ctx.author.id)
        
        if not player:
            return await ctx.respond("Register first with `/register`.", ephemeral=True)
        
        await ctx.defer()
        
        # Generate map image
        map_image = await generate_map_image(player['faction_id'])
        file = discord.File(map_image, filename="risk_city_map.png")
        
        # Create embed with map
        embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
        embed.description = "Real-time territory control map. Click district buttons below to interact."
        embed.set_image(url="attachment://risk_city_map.png")
        
        # Create button view
        view = VisualMapView(player['id'], player['faction_id'])
        
        await ctx.followup.send(embed=embed, file=file, view=view)


def setup(bot):
    bot.add_cog(VisualTerritoryMap(bot))
