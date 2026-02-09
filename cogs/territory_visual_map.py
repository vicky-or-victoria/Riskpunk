import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio

from utils.database import (
    get_pool,
    get_player,
    get_faction,
    update_player_credits,
    update_player_xp
)
from utils.styles import RiskEmbed, NEON_CYAN, NEON_GREEN, NEON_RED, NEON_YELLOW

# Try to import PIL, fallback to text mode if not available
try:
    from PIL import Image, ImageDraw, ImageFont
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[MAP] WARNING: Pillow not installed. Using text-based map.")


# Territory positions for image generation
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

FACTION_MAP_COLORS = {
    "omnicorp": (91, 94, 166),
    "solarflare": (255, 107, 0),
    "netrunners": (0, 255, 255),
    "ironveil": (192, 192, 192),
    "phantomcell": (155, 89, 182),
    "neutral": (100, 100, 100)
}


async def generate_map_image(player_faction_id=None):
    """Generate visual map image if PIL available"""
    if not PIL_AVAILABLE:
        return None
    
    try:
        width, height = 760, 610
        img = Image.new('RGB', (width, height), color=(10, 14, 26))
        draw = ImageDraw.Draw(img)
        
        # Try custom fonts, fallback to default
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except:
            title_font = label_font = small_font = ImageFont.load_default()
        
        # Get territories
        pool = await get_pool()
        async with pool.acquire() as conn:
            territories = await conn.fetch("SELECT * FROM territories")
        
        # Draw grid
        for x in range(0, width, 40):
            draw.line([(x, 0), (x, height)], fill=(20, 30, 50), width=1)
        for y in range(0, height, 40):
            draw.line([(0, y), (width, y)], fill=(20, 30, 50), width=1)
        
        # Draw territories
        for territory in territories:
            pos = TERRITORY_POSITIONS.get(territory['key'])
            if not pos:
                continue
            
            x, y, w, h = pos['x'], pos['y'], pos['w'], pos['h']
            
            # Get color
            if territory['owner_faction']:
                faction = await get_faction(territory['owner_faction'])
                color = FACTION_MAP_COLORS.get(faction['key'] if faction else 'neutral', FACTION_MAP_COLORS['neutral'])
                is_yours = (territory['owner_faction'] == player_faction_id)
                owner = faction['name'].upper() if faction else "NEUTRAL"
            else:
                color = FACTION_MAP_COLORS['neutral']
                is_yours = False
                owner = "NEUTRAL"
            
            # Draw background
            draw.rectangle([x+5, y+5, x+w-5, y+h-5], fill=color)
            
            # Draw border
            border_col = (0, 255, 255) if is_yours else (150, 150, 150)
            draw.rectangle([x, y, x+w, y+h], outline=border_col, width=3 if is_yours else 2)
            
            # Territory name
            name = territory['name']
            draw.text((x+w//2, y+20), name, fill=(255, 255, 255), font=label_font, anchor="mt")
            
            # Owner
            draw.text((x+w//2, y+h-50), owner, fill=(200, 200, 200), font=small_font, anchor="mt")
            
            # Defense bar
            def_val = territory['defense']
            bar_w = w - 40
            bar_h = 8
            bar_x = x + 20
            bar_y = y + h - 25
            
            draw.rectangle([bar_x, bar_y, bar_x+bar_w, bar_y+bar_h], fill=(40, 40, 40))
            fill_w = int((def_val/100) * bar_w)
            if fill_w > 0:
                col = (0, 255, 100) if def_val > 70 else (255, 255, 0) if def_val > 40 else (255, 100, 100)
                draw.rectangle([bar_x, bar_y, bar_x+fill_w, bar_y+bar_h], fill=col)
            
            draw.text((x+w//2, bar_y-10), f"DEF:{def_val}", fill=(180, 180, 180), font=small_font, anchor="mt")
        
        # Title
        draw.text((width//2, 15), "RISK CITY - TERRITORY MAP", fill=(0, 255, 255), font=title_font, anchor="mt")
        
        # Legend
        ly = height - 20
        draw.rectangle([20, ly-4, 40, ly+4], fill=(0, 255, 255))
        draw.text((45, ly), "Your Faction", fill=(200, 200, 200), font=small_font, anchor="lm")
        
        draw.rectangle([170, ly-4, 190, ly+4], fill=(150, 100, 100))
        draw.text((195, ly), "Enemy", fill=(200, 200, 200), font=small_font, anchor="lm")
        
        draw.rectangle([270, ly-4, 290, ly+4], fill=(100, 100, 100))
        draw.text((295, ly), "Neutral", fill=(200, 200, 200), font=small_font, anchor="lm")
        
        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes
        
    except Exception as e:
        print(f"[MAP] Image generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def create_text_map(player_faction_id=None):
    """Create text-based map as fallback"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        territories = await conn.fetch("SELECT * FROM territories ORDER BY id")
    
    # Map layout
    layout = [
        ["industrial_sector", "chrome_district", "downtown_core"],
        ["port_authority", "central_plaza", "corp_towers"],
        ["undercity", "tech_quarter", "skyline_heights"]
    ]
    
    map_lines = ["```"]
    map_lines.append("═" * 50)
    map_lines.append("     RISK CITY - TERRITORY CONTROL MAP")
    map_lines.append("═" * 50)
    map_lines.append("")
    
    # Create visual grid
    for row in layout:
        row_names = []
        row_owners = []
        row_defense = []
        
        for terr_key in row:
            terr = next((t for t in territories if t['key'] == terr_key), None)
            if not terr:
                continue
            
            # Icon based on ownership
            if terr['owner_faction']:
                if terr['owner_faction'] == player_faction_id:
                    icon = "🟢"
                else:
                    icon = "🔴"
            else:
                icon = "⚪"
            
            # Shorten name
            name = terr['name'][:12].ljust(12)
            row_names.append(f"{icon} {name}")
            
            # Owner
            if terr['owner_faction']:
                faction = await get_faction(terr['owner_faction'])
                owner = faction['name'][:10] if faction else "Neutral"
            else:
                owner = "Neutral"
            row_owners.append(owner.ljust(12))
            
            # Defense
            defense = terr['defense']
            bar = "█" * (defense // 20) + "░" * (5 - defense // 20)
            row_defense.append(f"{bar} {defense:3d}")
        
        map_lines.append(" | ".join(row_names))
        map_lines.append(" | ".join(row_owners))
        map_lines.append(" | ".join(row_defense))
        map_lines.append("─" * 50)
    
    map_lines.append("")
    map_lines.append("Legend: 🟢 Your Faction | 🔴 Enemy | ⚪ Neutral")
    map_lines.append("```")
    
    return "\n".join(map_lines)


class MapView(View):
    def __init__(self, player_id, player_faction_id, has_image=False):
        super().__init__(timeout=300)
        self.player_id = player_id
        self.player_faction_id = player_faction_id
        self.has_image = has_image
    
    @discord.ui.button(label="Industrial Sector", style=discord.ButtonStyle.secondary, row=0)
    async def btn1(self, button, interaction):
        await self.show_detail(interaction, "industrial_sector")
    
    @discord.ui.button(label="Chrome District", style=discord.ButtonStyle.secondary, row=0)
    async def btn2(self, button, interaction):
        await self.show_detail(interaction, "chrome_district")
    
    @discord.ui.button(label="Downtown Core", style=discord.ButtonStyle.secondary, row=0)
    async def btn3(self, button, interaction):
        await self.show_detail(interaction, "downtown_core")
    
    @discord.ui.button(label="Port Authority", style=discord.ButtonStyle.secondary, row=1)
    async def btn4(self, button, interaction):
        await self.show_detail(interaction, "port_authority")
    
    @discord.ui.button(label="Central Plaza", style=discord.ButtonStyle.secondary, row=1)
    async def btn5(self, button, interaction):
        await self.show_detail(interaction, "central_plaza")
    
    @discord.ui.button(label="Corp Towers", style=discord.ButtonStyle.secondary, row=1)
    async def btn6(self, button, interaction):
        await self.show_detail(interaction, "corp_towers")
    
    @discord.ui.button(label="Undercity", style=discord.ButtonStyle.secondary, row=2)
    async def btn7(self, button, interaction):
        await self.show_detail(interaction, "undercity")
    
    @discord.ui.button(label="Tech Quarter", style=discord.ButtonStyle.secondary, row=2)
    async def btn8(self, button, interaction):
        await self.show_detail(interaction, "tech_quarter")
    
    @discord.ui.button(label="Skyline Heights", style=discord.ButtonStyle.secondary, row=2)
    async def btn9(self, button, interaction):
        await self.show_detail(interaction, "skyline_heights")
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary, row=3)
    async def refresh_btn(self, button, interaction):
        await interaction.response.defer()
        
        if self.has_image:
            img = await generate_map_image(self.player_faction_id)
            if img:
                file = discord.File(img, filename="map.png")
                embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
                embed.description = "Click districts to interact."
                embed.set_image(url="attachment://map.png")
                await interaction.edit_original_response(embed=embed, attachments=[file], view=self)
                return
        
        # Fallback to text
        text_map = await create_text_map(self.player_faction_id)
        embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
        embed.description = text_map
        await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger, row=3)
    async def close_btn(self, button, interaction):
        await interaction.response.edit_message(view=None)
        self.stop()
    
    async def show_detail(self, interaction, terr_key):
        pool = await get_pool()
        async with pool.acquire() as conn:
            terr = await conn.fetchrow("SELECT * FROM territories WHERE key = $1", terr_key)
        
        if not terr:
            return await interaction.response.send_message("Not found!", ephemeral=True)
        
        owner_name = "Neutral"
        owner_col = NEON_CYAN
        if terr['owner_faction']:
            faction = await get_faction(terr['owner_faction'])
            if faction:
                owner_name = faction['name']
                owner_col = int(faction['color'].replace('#', '0x'), 16)
        
        embed = RiskEmbed(title=f"📍 {terr['name']}", color=owner_col)
        embed.description = terr['description']
        
        def_bar = "█" * (terr['defense'] // 10) + "░" * (10 - terr['defense'] // 10)
        
        embed.add_field(name="Controller", value=f"`{owner_name}`", inline=True)
        embed.add_field(name="Income", value=f"`{terr['income']:,} ₵/week`", inline=True)
        embed.add_field(name="Defense", value=f"{def_bar} `{terr['defense']}/100`", inline=False)
        
        action_view = ActionView(self.player_id, self.player_faction_id, terr_key, self)
        await interaction.response.edit_message(embed=embed, view=action_view)


class ActionView(View):
    def __init__(self, player_id, player_faction_id, terr_key, parent):
        super().__init__(timeout=300)
        self.player_id = player_id
        self.player_faction_id = player_faction_id
        self.terr_key = terr_key
        self.parent = parent
    
    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.danger)
    async def attack(self, button, interaction):
        player = await get_player(interaction.user.id)
        
        if not self.player_faction_id:
            return await interaction.response.send_message("Join a faction first!", ephemeral=True)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            terr = await conn.fetchrow("SELECT * FROM territories WHERE key = $1", self.terr_key)
        
        if terr['owner_faction'] == self.player_faction_id:
            return await interaction.response.send_message("You control this!", ephemeral=True)
        
        if player['credits'] < 500:
            return await interaction.response.send_message("Need 500 ₵!", ephemeral=True)
        
        await update_player_credits(player['id'], -500)
        
        import random
        power = player['atk'] + player['spd'] + random.randint(1, 100)
        defense = terr['defense'] + random.randint(1, 100)
        
        if power > defense:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("UPDATE territories SET owner_faction = $1 WHERE key = $2", 
                                 self.player_faction_id, self.terr_key)
            await update_player_xp(player['id'], 500)
            
            embed = RiskEmbed(title="⚔️ VICTORY!", color=NEON_GREEN)
            embed.description = f"**{terr['name']}** captured! +500 XP"
        else:
            dmg = random.randint(10, 30)
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute("UPDATE players SET hp = GREATEST(0, hp - $1) WHERE id = $2", dmg, player['id'])
            await update_player_xp(player['id'], 100)
            
            embed = RiskEmbed(title="⚔️ DEFEAT", color=NEON_RED)
            embed.description = f"Failed! -{dmg} HP, +100 XP"
        
        await interaction.response.edit_message(embed=embed, view=None)
        await asyncio.sleep(3)
        
        # Back to map
        if self.parent.has_image:
            img = await generate_map_image(self.player_faction_id)
            if img:
                file = discord.File(img, filename="map.png")
                map_embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
                map_embed.set_image(url="attachment://map.png")
                await interaction.edit_original_response(embed=map_embed, attachments=[file], view=self.parent)
                return
        
        text = await create_text_map(self.player_faction_id)
        map_embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
        map_embed.description = text
        await interaction.edit_original_response(embed=map_embed, view=self.parent)
    
    @discord.ui.button(label="🛡️ Fortify", style=discord.ButtonStyle.success)
    async def fortify(self, button, interaction):
        player = await get_player(interaction.user.id)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            terr = await conn.fetchrow("SELECT * FROM territories WHERE key = $1", self.terr_key)
        
        if terr['owner_faction'] != self.player_faction_id:
            return await interaction.response.send_message("Not your faction's territory!", ephemeral=True)
        
        if terr['defense'] >= 100:
            return await interaction.response.send_message("Max defense!", ephemeral=True)
        
        if player['credits'] < 1000:
            return await interaction.response.send_message("Need 1000 ₵!", ephemeral=True)
        
        await update_player_credits(player['id'], -1000)
        new_def = min(100, terr['defense'] + 10)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE territories SET defense = $1 WHERE key = $2", new_def, self.terr_key)
        
        embed = RiskEmbed(title="🛡️ FORTIFIED", color=NEON_GREEN)
        embed.description = f"Defense: {terr['defense']} → {new_def}"
        
        await interaction.response.edit_message(embed=embed, view=None)
        await asyncio.sleep(2)
        
        # Back to map
        if self.parent.has_image:
            img = await generate_map_image(self.player_faction_id)
            if img:
                file = discord.File(img, filename="map.png")
                map_embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
                map_embed.set_image(url="attachment://map.png")
                await interaction.edit_original_response(embed=map_embed, attachments=[file], view=self.parent)
                return
        
        text = await create_text_map(self.player_faction_id)
        map_embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
        map_embed.description = text
        await interaction.edit_original_response(embed=map_embed, view=self.parent)
    
    @discord.ui.button(label="◀️ Back", style=discord.ButtonStyle.secondary)
    async def back(self, button, interaction):
        await interaction.response.defer()
        
        if self.parent.has_image:
            img = await generate_map_image(self.player_faction_id)
            if img:
                file = discord.File(img, filename="map.png")
                embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
                embed.set_image(url="attachment://map.png")
                await interaction.edit_original_response(embed=embed, attachments=[file], view=self.parent)
                return
        
        text = await create_text_map(self.player_faction_id)
        embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
        embed.description = text
        await interaction.edit_original_response(embed=embed, view=self.parent)


class TerritoryMap(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if PIL_AVAILABLE:
            print("[MAP] Image generation ENABLED")
        else:
            print("[MAP] Image generation DISABLED - using text mode")
    
    @commands.slash_command(name="map", description="View territory map")
    async def map_command(self, ctx: discord.ApplicationContext):
        player = await get_player(ctx.author.id)
        if not player:
            return await ctx.respond("Register first!", ephemeral=True)
        
        await ctx.defer()
        
        # Try image first
        has_image = False
        if PIL_AVAILABLE:
            img = await generate_map_image(player['faction_id'])
            if img:
                file = discord.File(img, filename="map.png")
                embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
                embed.description = "Click districts to interact."
                embed.set_image(url="attachment://map.png")
                view = MapView(player['id'], player['faction_id'], has_image=True)
                await ctx.followup.send(embed=embed, file=file, view=view)
                return
        
        # Fallback to text
        text_map = await create_text_map(player['faction_id'])
        embed = RiskEmbed(title="🗺️ RISK CITY MAP", color=NEON_CYAN)
        embed.description = text_map
        view = MapView(player['id'], player['faction_id'], has_image=False)
        await ctx.followup.send(embed=embed, view=view)


def setup(bot):
    bot.add_cog(TerritoryMap(bot))
