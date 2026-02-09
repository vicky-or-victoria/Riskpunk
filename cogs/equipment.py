# cogs/equipment.py
# Equipment system - equip items for stat bonuses
import discord
from discord.ext import commands

from utils.database import (
    get_player, get_inventory, get_equipped_items,
    equip_item, unequip_item, add_item
)
from utils.game_data import ITEM_CATALOG
from utils.styles import RiskEmbed, NEON_CYAN, NEON_GREEN, NEON_RED, THIN_LINE


class EquipmentCog(commands.Cog, name="Equipment"):
    """Equip items for combat bonuses"""
    
    def __init__(self, bot):
        self.bot = bot
    
    equip_grp = discord.SlashCommandGroup("equip", "Equipment management")
    
    # ── /equip list ──────────────────────────────────────────
    @equip_grp.command(name="list", description="View your equipped items")
    async def equip_list(self, ctx: discord.ApplicationContext):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond("Not registered.", ephemeral=True)
            return
        
        equipped = await get_equipped_items(player['id'])
        
        embed = RiskEmbed(title="⚙️ EQUIPPED ITEMS", color=NEON_CYAN)
        embed.description = f"{THIN_LINE}\n"
        
        # Calculate total bonuses
        total_atk = 0
        total_def = 0
        total_spd = 0
        
        if not equipped:
            embed.description += "`No items equipped.`\n"
        else:
            for eq in equipped:
                item_data = ITEM_CATALOG.get(eq['item_name'])
                if item_data:
                    bonuses = []
                    if 'atk_bonus' in item_data:
                        bonuses.append(f"+{item_data['atk_bonus']} ATK")
                        total_atk += item_data['atk_bonus']
                    if 'def_bonus' in item_data:
                        bonuses.append(f"+{item_data['def_bonus']} DEF")
                        total_def += item_data['def_bonus']
                    if 'spd_bonus' in item_data:
                        bonuses.append(f"+{item_data['spd_bonus']} SPD")
                        total_spd += item_data['spd_bonus']
                    
                    bonus_str = ", ".join(bonuses) if bonuses else "Cosmetic"
                    embed.add_field(
                        name=f"{eq['slot'].title()}: {eq['item_name']}",
                        value=f"`{bonus_str}`",
                        inline=True
                    )
        
        embed.add_field(
            name="📊 Total Bonuses",
            value=f"ATK: `+{total_atk}` | DEF: `+{total_def}` | SPD: `+{total_spd}`",
            inline=False
        )
        
        await ctx.respond(embed=embed)
    
    # ── /equip item ──────────────────────────────────────────
    @equip_grp.command(name="item", description="Equip an item from your inventory")
    @discord.option("item_name", description="Item to equip")
    async def equip_item_cmd(self, ctx: discord.ApplicationContext, item_name: str):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond("Not registered.", ephemeral=True)
            return
        
        # Check if item exists in catalog
        item_data = None
        for key, data in ITEM_CATALOG.items():
            if key.lower() == item_name.lower():
                item_name = key  # Use proper capitalization
                item_data = data
                break
        
        if not item_data:
            await ctx.respond(
                embed=RiskEmbed(
                    title="❌ Unknown Item",
                    description=f"`{item_name}` not found in catalog.",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        # Check if item can be equipped
        if not item_data.get('slot'):
            await ctx.respond(
                embed=RiskEmbed(
                    title="❌ Cannot Equip",
                    description=f"`{item_name}` is not an equippable item.",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        # Check inventory
        inv = await get_inventory(player['id'])
        has_item = False
        for i in inv:
            if i['item_name'].lower() == item_name.lower():
                has_item = True
                break
        
        if not has_item:
            await ctx.respond(
                embed=RiskEmbed(
                    title="❌ Not in Inventory",
                    description=f"You don't own `{item_name}`.\nPurchase it from `/shop` or `/trade board`.",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        # Equip the item
        slot = item_data['slot']
        await equip_item(player['id'], item_name, slot)
        
        # Build bonus description
        bonuses = []
        if 'atk_bonus' in item_data:
            bonuses.append(f"+{item_data['atk_bonus']} ATK")
        if 'def_bonus' in item_data:
            bonuses.append(f"+{item_data['def_bonus']} DEF")
        if 'spd_bonus' in item_data:
            bonuses.append(f"+{item_data['spd_bonus']} SPD")
        
        bonus_str = ", ".join(bonuses) if bonuses else "No stat bonuses"
        
        embed = RiskEmbed(
            title="✅ Item Equipped",
            description=f"**{item_name}** equipped to `{slot}` slot.\n{THIN_LINE}\n{bonus_str}",
            color=NEON_GREEN
        )
        
        await ctx.respond(embed=embed)
    
    # ── /equip remove ────────────────────────────────────────
    @equip_grp.command(name="remove", description="Unequip an item")
    @discord.option("slot", description="Equipment slot", choices=["weapon", "armor", "accessory"])
    async def equip_remove(self, ctx: discord.ApplicationContext, slot: str):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond("Not registered.", ephemeral=True)
            return
        
        # Check if anything equipped in that slot
        equipped = await get_equipped_items(player['id'])
        item_in_slot = None
        for eq in equipped:
            if eq['slot'] == slot:
                item_in_slot = eq['item_name']
                break
        
        if not item_in_slot:
            await ctx.respond(
                embed=RiskEmbed(
                    title="❌ Slot Empty",
                    description=f"Nothing equipped in `{slot}` slot.",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        # Unequip
        await unequip_item(player['id'], slot)
        
        embed = RiskEmbed(
            title="✅ Item Removed",
            description=f"**{item_in_slot}** unequipped from `{slot}` slot.",
            color=NEON_GREEN
        )
        
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(EquipmentCog(bot))
