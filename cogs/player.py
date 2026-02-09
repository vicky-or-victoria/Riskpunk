# cogs/player.py
import discord
from discord.ext import commands
from utils.database import ensure_player, get_player, get_player_implants, update_player_hp, get_faction
from utils.styles import RiskEmbed, NEON_CYAN, NEON_GREEN, THIN_LINE, player_card


class PlayerCog(commands.Cog, name="Player"):
    """Core player registration and profile commands."""

    def __init__(self, bot):
        self.bot = bot

    # ── /register ────────────────────────────────────────────
    @commands.slash_command(description="Register yourself in the Risk City grid.")
    async def register(self, ctx: discord.ApplicationContext, name: str = discord.Option(str, "Your street name", default="Drifter")):
        existing = await get_player(ctx.author.id)
        if existing:
            await ctx.respond(
                embed=RiskEmbed(
                    title="Already Registered",
                    description=f"You are already on the grid as **{existing['name']}**.\nUse `/profile` to view your status.",
                    color=NEON_CYAN
                ),
                ephemeral=True
            )
            return
        player = await ensure_player(ctx.author.id, name)
        implants = await get_player_implants(player["id"])
        await ctx.respond(
            embed=player_card(player, implants, "Independent"),
            content="✅ **Identity registered.** Welcome to the grid, runner."
        )

    # ── /profile ─────────────────────────────────────────────
    @commands.slash_command(description="View your (or another runner's) full profile.")
    async def profile(self, ctx: discord.ApplicationContext, target: discord.Member = None):
        target_member = target or ctx.author
        player = await get_player(target_member.id)
        if not player:
            await ctx.respond(
                embed=RiskEmbed(title="Not Found", description="`That runner isn't on the grid yet.`", color=0xFF073A),
                ephemeral=True
            )
            return
        implants = await get_player_implants(player["id"])
        faction_name = "Independent"
        if player["faction_id"]:
            fac = await get_faction(player["faction_id"])
            faction_name = fac["name"] if fac else "Unknown"
        await ctx.respond(embed=player_card(player, implants, faction_name))

    # ── /balance ─────────────────────────────────────────────
    @commands.slash_command(description="Check your current credit balance.")
    async def balance(self, ctx: discord.ApplicationContext):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="You aren't registered yet.  Run `/register` first.", ephemeral=True)
            return
        embed = RiskEmbed(title="💰 Credit Balance", color=NEON_GREEN)
        embed.description = (
            f"{THIN_LINE}\n"
            f"💵  **{player['credits']:,.2f} ₵**\n"
            f"{THIN_LINE}\n"
            f"`Synced with the city financial mesh.`"
        )
        await ctx.respond(embed=embed)

    # ── /heal ────────────────────────────────────────────────
    @commands.slash_command(description="Spend credits to heal HP at a street clinic.")
    async def heal(self, ctx: discord.ApplicationContext, amount: discord.Option(int, "HP to heal (costs 50 ₵ per HP)", min_value=1)):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered. Run `/register`.", ephemeral=True)
            return
        cost = amount * 50
        if player["credits"] < cost:
            await ctx.respond(
                embed=RiskEmbed(title="💸 Insufficient Funds", description=f"Healing {amount} HP costs `{cost:,.0f} ₵`. You only have `{player['credits']:,.0f} ₵`.", color=0xFF073A),
                ephemeral=True
            )
            return
        heal_actual = min(amount, player["max_hp"] - player["hp"])
        if heal_actual <= 0:
            await ctx.respond(embed=RiskEmbed(title="Already at Full HP", description="Nano-mesh is green across the board.", color=NEON_CYAN), ephemeral=True)
            return
        from utils.database import update_player_credits
        await update_player_credits(ctx.author.id, -cost)
        await update_player_hp(ctx.author.id, heal_actual)
        embed = RiskEmbed(title="🏥 Street Clinic", description=f"Healed **{heal_actual} HP** for `{cost:,.0f} ₵`.", color=NEON_GREEN)
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(PlayerCog(bot))