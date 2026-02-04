# cogs/factions.py
import discord
import random
from discord.ext import commands
from utils.database import (
    get_all_factions, get_faction, get_faction_members,
    get_player, set_player_faction, declare_war, get_active_wars, resolve_war,
    get_all_territories, claim_territory, update_player_credits, update_player_xp
)
from utils.game_data import FACTIONS_SEED
from utils.styles import RiskEmbed, NEON_CYAN, NEON_RED, NEON_GREEN, NEON_MAGENTA, LINE, FACTION_COLORS


class FactionsCog(commands.Cog, name="Factions"):
    """Faction membership and corporate warfare."""

    def __init__(self, bot):
        self.bot = bot

    factions_grp = discord.SlashCommandGroup("factions", "Faction operations.")

    # ── /factions list ───────────────────────────────────────
    @factions_grp.command(name="list", description="Browse all factions in the city.")
    async def factions_list(self, ctx: discord.ApplicationContext):
        factions = await get_all_factions()
        if not factions:
            await ctx.respond(content="No factions seeded yet — check bot startup.", ephemeral=True)
            return
        embed = RiskEmbed(title="🏢 FACTIONS — Neo‑Tokyo", color=NEON_MAGENTA)
        embed.description = "`Corporate powers that shape the grid.`\n" + LINE
        for f in factions:
            members = await get_faction_members(f["id"])
            col_int = int(FACTION_COLORS.get(f["key"], "0xFF00FF").replace("#", ""), 16) if isinstance(FACTION_COLORS.get(f["key"]), str) else FACTION_COLORS.get(f["key"], NEON_MAGENTA)
            embed.add_field(
                name=f"🏢 {f['name']}",
                value=(
                    f"{f['description']}\n"
                    f"┆ Members: `{len(members)}`  ┆  Aggression: `{f['aggression']}/100`\n"
                    f"┆ Join: `/factions join {f['key']}`"
                ),
                inline=False
            )
        await ctx.respond(embed=embed)

    # ── /factions join ───────────────────────────────────────
    @factions_grp.command(name="join", description="Pledge your loyalty to a faction.")
    @discord.option("faction_key", description="Faction codename (e.g. omnicorp)")
    async def factions_join(self, ctx: discord.ApplicationContext, faction_key: str):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered. Run `/register`.", ephemeral=True)
            return
        factions = await get_all_factions()
        target = None
        for f in factions:
            if f["key"].lower() == faction_key.lower():
                target = f
                break
        if not target:
            keys = ", ".join(f"`{f['key']}`" for f in factions)
            await ctx.respond(embed=RiskEmbed(title="❌ Unknown Faction", description=f"Valid factions: {keys}", color=NEON_RED), ephemeral=True)
            return
        if player["faction_id"] == target["id"]:
            await ctx.respond(embed=RiskEmbed(title="Already Aligned", description=f"You already belong to **{target['name']}**.", color=NEON_CYAN), ephemeral=True)
            return
        await set_player_faction(ctx.author.id, target["id"])
        embed = RiskEmbed(title="🤝 Faction Joined", color=FACTION_COLORS.get(target["key"], NEON_CYAN))
        embed.description = (
            f"You have pledged your loyalty to **{target['name']}**.\n"
            f"{LINE}\n"
            f"`{target['description']}`"
        )
        await ctx.respond(embed=embed)

    # ── /factions war ────────────────────────────────────────
    @factions_grp.command(name="war", description="Declare war on another faction (faction leader only — simulated).")
    @discord.option("target_faction", description="Enemy faction codename")
    async def factions_war(self, ctx: discord.ApplicationContext, target_faction: str):
        player = await get_player(ctx.author.id)
        if not player or not player["faction_id"]:
            await ctx.respond(content="You must belong to a faction.", ephemeral=True)
            return
        factions = await get_all_factions()
        attacker = await get_faction(player["faction_id"])
        defender = None
        for f in factions:
            if f["key"].lower() == target_faction.lower():
                defender = f
                break
        if not defender:
            await ctx.respond(embed=RiskEmbed(title="❌ Unknown Faction", color=NEON_RED), ephemeral=True)
            return
        if attacker["id"] == defender["id"]:
            await ctx.respond(content="You can't declare war on yourself.", ephemeral=True)
            return
        # Check for existing active war between these two
        active_wars = await get_active_wars()
        for w in active_wars:
            pair = {w["faction_a"], w["faction_b"]}
            if pair == {attacker["id"], defender["id"]}:
                await ctx.respond(embed=RiskEmbed(title="⚠️ War Already Active", description=f"**{attacker['name']}** and **{defender['name']}** are already at war.", color=NEON_RED), ephemeral=True)
                return
        war = await declare_war(attacker["id"], defender["id"])
        # Simulate the war instantly with a dice roll weighted by aggression + random
        atk_power = attacker["aggression"] + random.randint(10, 60)
        def_power = defender["aggression"] + random.randint(10, 60)
        winner_faction = attacker if atk_power >= def_power else defender
        loser_faction  = defender if atk_power >= def_power else attacker
        await resolve_war(war["id"], winner_faction["id"])
        # Winner claims a random unclaimed or enemy territory
        territories = await get_all_territories()
        claimable = [t for t in territories if t["owner_faction"] != winner_faction["id"]]
        if claimable:
            prize = random.choice(claimable)
            await claim_territory(prize["key"], winner_faction["id"])
            prize_text = f"\n🗺️ **{winner_faction['name']}** seized **{prize['name']}**!"
        else:
            prize_text = ""
        # Reward all members of the winning faction
        winners = await get_faction_members(winner_faction["id"])
        for w in winners:
            await update_player_credits(w["discord_id"], 2000)
            await update_player_xp(w["discord_id"], 150)
        embed = RiskEmbed(title="⚔️ WAR RESOLVED", color=NEON_GREEN)
        embed.description = (
            f"{LINE}\n"
            f"**{attacker['name']}** vs **{defender['name']}**\n"
            f"{LINE}\n"
            f"⚡ ATK Power: `{atk_power}`  ┆  DEF Power: `{def_power}`\n"
            f"🏆 **VICTOR: {winner_faction['name']}**\n"
            f"{prize_text}\n"
            f"💰 All {winner_faction['name']} members: `+2,000 ₵` & `+150 XP`\n"
            f"{LINE}"
        )
        await ctx.respond(embed=embed)

    # ── /factions wars ───────────────────────────────────────
    @factions_grp.command(name="wars", description="View currently active wars.")
    async def factions_wars(self, ctx: discord.ApplicationContext):
        wars = await get_active_wars()
        if not wars:
            embed = RiskEmbed(title="⚔️ No Active Wars", description="`The grid is quiet.  For now.`", color=NEON_CYAN)
            await ctx.respond(embed=embed)
            return
        embed = RiskEmbed(title="⚔️ ACTIVE WARS", color=NEON_RED)
        for w in wars:
            fa = await get_faction(w["faction_a"])
            fb = await get_faction(w["faction_b"])
            embed.add_field(
                name=f"War #{w['id']}",
                value=f"**{fa['name']}** vs **{fb['name']}**\n`Started: {w['started_at']}`",
                inline=True
            )
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(FactionsCog(bot))
