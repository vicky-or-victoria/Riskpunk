# cogs/leaderboard.py
import discord
from discord.ext import commands
from utils.database import get_leaderboard
from utils.styles import RiskEmbed, NEON_YELLOW


class LeaderboardCog(commands.Cog, name="Leaderboard"):
    """City-wide leaderboard rankings."""

    def __init__(self, bot):
        self.bot = bot

    leaderboard_grp = discord.SlashCommandGroup("leaderboard", "City rankings.")

    # ── /leaderboard credits ─────────────────────────────────
    @leaderboard_grp.command(name="credits", description="Top 10 richest citizens.")
    async def lb_credits(self, ctx: discord.ApplicationContext):
        players = await get_leaderboard("credits", 10)
        if not players:
            await ctx.respond(embed=RiskEmbed(title="🏆 No Data", description="No registered players yet.", color=NEON_YELLOW))
            return
        await ctx.respond(embed=leaderboard_embed(players, "Credits"))

    # ── /leaderboard level ───────────────────────────────────
    @leaderboard_grp.command(name="level", description="Top 10 by character level.")
    async def lb_level(self, ctx: discord.ApplicationContext):
        players = await get_leaderboard("level", 10)
        if not players:
            await ctx.respond(embed=RiskEmbed(title="🏆 No Data", description="No data.", color=NEON_YELLOW))
            return
        await ctx.respond(embed=leaderboard_embed(players, "Level"))

    # ── /leaderboard rep ─────────────────────────────────────
    @leaderboard_grp.command(name="rep", description="Top 10 by street reputation.")
    async def lb_rep(self, ctx: discord.ApplicationContext):
        players = await get_leaderboard("rep", 10)
        if not players:
            await ctx.respond(embed=RiskEmbed(title="🏆 No Data", description="No data.", color=NEON_YELLOW))
            return
        await ctx.respond(embed=leaderboard_embed(players, "Rep"))


def setup(bot):
    bot.add_cog(LeaderboardCog(bot))
