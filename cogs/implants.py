# cogs/implants.py
import discord
from discord.ext import commands
from utils.database import (
    get_player, get_player_implants, install_implant,
    remove_implant, update_player_credits
)
from utils.game_data import IMPLANTS, IMPLANT_SLOTS
from utils.styles import NeonEmbed, NEON_CYAN, NEON_GREEN, NEON_RED, THIN_LINE, LINE


class ImplantsCog(commands.Cog, name="Implants"):
    """Cybernetic augmentation system."""

    def __init__(self, bot):
        self.bot = bot

    # ── /implants ────────────────────────────────────────────
    implants_grp = discord.SlashCommandGroup("implants", "Manage your cybernetic implants.")

    @implants_grp.command(name="list", description="View your currently installed implants.")
    async def implants_list(self, ctx: discord.ApplicationContext):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered. Run `/register`.", ephemeral=True)
            return
        installed = await get_player_implants(player["id"])
        embed = NeonEmbed(title="🔧 Installed Implants", color=NEON_CYAN)
        if not installed:
            embed.description = "`No augmentations installed.  Visit /implants shop.`"
        else:
            lines = []
            installed_slots = set()
            for imp in installed:
                data = IMPLANTS.get(imp["implant_key"], {})
                bonuses = data.get("bonuses", {})
                bonus_str = ", ".join(f"+{v} {k.upper()}" for k, v in bonuses.items() if v > 0)
                lines.append(
                    f"  `[{imp['slot'].upper():8}]`  **{data.get('name', imp['implant_key'])}**\n"
                    f"         ┆ {data.get('description', '—')}\n"
                    f"         ┆ Bonuses: {bonus_str or '—'}"
                )
                installed_slots.add(imp["slot"])
            embed.description = "\n".join(lines)
            empty_slots = [s for s in IMPLANT_SLOTS if s not in installed_slots]
            if empty_slots:
                embed.add_field(
                    name="🔲 Empty Slots",
                    value=", ".join(f"`{s}`" for s in empty_slots),
                    inline=False
                )
        await ctx.respond(embed=embed)

    # ── /implants shop ───────────────────────────────────────
    @implants_grp.command(name="shop", description="Browse available implants for purchase.")
    async def implants_shop(self, ctx: discord.ApplicationContext):
        embed = NeonEmbed(title="🏪 Implant Shop — Chrome Bazaar", color=NEON_GREEN)
        embed.description = "`Backroom surgery. No questions asked.`\n" + LINE
        # Group by slot
        by_slot = {}
        for key, data in IMPLANTS.items():
            by_slot.setdefault(data["slot"], []).append((key, data))
        for slot in IMPLANT_SLOTS:
            items = by_slot.get(slot, [])
            val = "\n".join(
                f"  `{key}` — **{d['name']}**  ┆  {d['cost']:,} ₵\n"
                f"           {d['description']}"
                for key, d in items
            )
            if val:
                embed.add_field(name=f"📦 {slot.upper()} Slot", value=val, inline=False)
        embed.add_field(
            name="💡 How to Install",
            value="Use `/implants install <implant_key> <slot>`\n"
                  "Installing into an occupied slot **replaces** the existing implant (no refund).",
            inline=False
        )
        await ctx.respond(embed=embed)

    # ── /implants install ────────────────────────────────────
    @implants_grp.command(name="install", description="Install an implant into a slot.")
    @discord.option("implant_key", description="Key from /implants shop")
    @discord.option("slot", description="Body slot", choices=["head", "eyes", "arm", "torso", "legs"])
    async def implants_install(self, ctx: discord.ApplicationContext, implant_key: str, slot: str):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        implant_data = IMPLANTS.get(implant_key)
        if not implant_data:
            await ctx.respond(embed=NeonEmbed(title="❌ Unknown Implant", description=f"`{implant_key}` doesn't exist in our catalogue.", color=NEON_RED), ephemeral=True)
            return
        if implant_data["slot"] != slot:
            await ctx.respond(embed=NeonEmbed(title="❌ Slot Mismatch", description=f"**{implant_data['name']}** must go in the `{implant_data['slot']}` slot.", color=NEON_RED), ephemeral=True)
            return
        cost = implant_data["cost"]
        if player["credits"] < cost:
            await ctx.respond(embed=NeonEmbed(title="💸 Insufficient Funds", description=f"Costs `{cost:,} ₵`. You have `{player['credits']:,.0f} ₵`.", color=NEON_RED), ephemeral=True)
            return
        await update_player_credits(ctx.author.id, -cost)
        await install_implant(player["id"], implant_key, slot)
        bonuses = implant_data.get("bonuses", {})
        bonus_str = ", ".join(f"+{v} {k.upper()}" for k, v in bonuses.items() if v > 0)
        embed = NeonEmbed(title="✅ Implant Installed", color=NEON_GREEN)
        embed.description = (
            f"**{implant_data['name']}** → slot `{slot.upper()}`\n"
            f"{THIN_LINE}\n"
            f"💵 Deducted `{cost:,} ₵`\n"
            f"⚡ Active bonuses: {bonus_str or '—'}"
        )
        await ctx.respond(embed=embed)

    # ── /implants remove ─────────────────────────────────────
    @implants_grp.command(name="remove", description="Remove an implant from a slot (no refund).")
    @discord.option("slot", description="Body slot to clear", choices=["head", "eyes", "arm", "torso", "legs"])
    async def implants_remove(self, ctx: discord.ApplicationContext, slot: str):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        installed = await get_player_implants(player["id"])
        occupied = {imp["slot"]: imp for imp in installed}
        if slot not in occupied:
            await ctx.respond(embed=NeonEmbed(title="🔲 Slot Empty", description=f"`{slot.upper()}` is already vacant.", color=NEON_RED), ephemeral=True)
            return
        imp = occupied[slot]
        data = IMPLANTS.get(imp["implant_key"], {})
        await remove_implant(player["id"], slot)
        embed = NeonEmbed(title="🗑️ Implant Removed", color=NEON_CYAN)
        embed.description = f"**{data.get('name', imp['implant_key'])}** extracted from `{slot.upper()}`. No refund issued."
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(ImplantsCog(bot))
