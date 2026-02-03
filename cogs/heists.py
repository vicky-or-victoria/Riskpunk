# cogs/heists.py
import discord
import random
from discord.ext import commands
from utils.database import (
    get_player, create_heist, get_heist, get_active_heists,
    join_heist, advance_heist_phase, update_player_credits, update_player_xp,
    get_player_skills, log_event, add_item
)
from utils.game_data import HEIST_TARGETS
from utils.styles import heist_card, NeonEmbed, NEON_CYAN, NEON_GREEN, NEON_RED, NEON_ORANGE, LINE, THIN_LINE


class HeistsCog(commands.Cog, name="Heists"):
    """Team-based heist coordination system."""

    def __init__(self, bot):
        self.bot = bot

    heist_grp = discord.SlashCommandGroup("heist", "Heist operations.")

    # ── /heist list ──────────────────────────────────────────
    @heist_grp.command(name="list", description="View all active heists.")
    async def heist_list(self, ctx: discord.ApplicationContext):
        heists = await get_active_heists()
        if not heists:
            embed = NeonEmbed(title="🚨 No Active Heists", description="`The streets are quiet.  Start one with /heist create.`", color=NEON_CYAN)
            await ctx.respond(embed=embed)
            return
        embed = NeonEmbed(title="🚨 ACTIVE HEISTS", color=NEON_ORANGE)
        for h in heists:
            crew_ids = [x.strip() for x in h["crew"].split(",") if x.strip()]
            embed.add_field(
                name=f"Heist #{h['id']}  —  {h['target']}",
                value=(
                    f"Phase: `{h['phase'].upper()}`  ┆  Crew: `{len(crew_ids)}`  ┆  "
                    f"Payout: `{h['reward']:,.0f} ₵`  ┆  Diff: `{h['difficulty']}/10`\n"
                    f"`/heist join {h['id']}`  to enlist."
                ),
                inline=False
            )
        await ctx.respond(embed=embed)

    # ── /heist targets ───────────────────────────────────────
    @heist_grp.command(name="targets", description="Browse available heist targets.")
    async def heist_targets(self, ctx: discord.ApplicationContext):
        embed = NeonEmbed(title="🎯 Heist Targets", color=NEON_CYAN)
        embed.description = "`High-value objectives across Risk City.`\n" + LINE
        for i, t in enumerate(HEIST_TARGETS):
            embed.add_field(
                name=f"{i}. {t['name']}",
                value=(
                    f"💰 Reward: `{t['reward']:,} ₵`  ┆  "
                    f"⚙️ Difficulty: `{t['difficulty']}/10`  ┆  "
                    f"👥 Min Crew: `{t['min_crew']}`"
                ),
                inline=False
            )
        embed.add_field(name="💡 How to Start", value="Use `/heist create <target_index>`", inline=False)
        await ctx.respond(embed=embed)

    # ── /heist create ────────────────────────────────────────
    @heist_grp.command(name="create", description="Plan a new heist.")
    @discord.option("target_index", description="Target index from /heist targets", type=int, min_value=0)
    async def heist_create(self, ctx: discord.ApplicationContext, target_index: int):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        if target_index < 0 or target_index >= len(HEIST_TARGETS):
            await ctx.respond(embed=NeonEmbed(title="❌ Invalid Target", description=f"Choose 0–{len(HEIST_TARGETS)-1}", color=NEON_RED), ephemeral=True)
            return
        target = HEIST_TARGETS[target_index]
        # Check player credits (planning fee = 10% of reward)
        planning_fee = target["reward"] * 0.1
        if player["credits"] < planning_fee:
            await ctx.respond(embed=NeonEmbed(title="💸 Need Planning Fee", description=f"Fee: `{planning_fee:,.0f} ₵`", color=NEON_RED), ephemeral=True)
            return
        await update_player_credits(ctx.author.id, -planning_fee)
        heist = await create_heist(player["id"], target["name"], target["reward"], target["difficulty"])
        embed = heist_card(heist)
        embed.add_field(
            name="📋 Next Steps",
            value=(
                f"1️⃣  Recruit crew with `/heist join {heist['id']}`  (need {target['min_crew']} total)\n"
                f"2️⃣  Execute with `/heist execute {heist['id']}`\n"
                f"💵 Planning fee of `{planning_fee:,.0f} ₵` deducted."
            ),
            inline=False
        )
        await ctx.respond(embed=embed)

    # ── /heist join ──────────────────────────────────────────
    @heist_grp.command(name="join", description="Join an active heist as crew.")
    @discord.option("heist_id", description="Heist ID", type=int)
    async def heist_join(self, ctx: discord.ApplicationContext, heist_id: int):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        heist = await get_heist(heist_id)
        if not heist:
            await ctx.respond(embed=NeonEmbed(title="❌ Heist Not Found", color=NEON_RED), ephemeral=True)
            return
        if heist["status"] != "recruiting":
            await ctx.respond(embed=NeonEmbed(title="❌ Not Recruiting", description=f"Heist is in `{heist['status']}` phase.", color=NEON_RED), ephemeral=True)
            return
        success = await join_heist(heist_id, player["id"])
        if not success:
            await ctx.respond(embed=NeonEmbed(title="Already in Crew", description="You're already part of this heist.", color=NEON_CYAN), ephemeral=True)
            return
        # Refresh heist data
        heist = await get_heist(heist_id)
        crew_count = len([x for x in heist["crew"].split(",") if x.strip()])
        embed = NeonEmbed(title="✅ Crew Updated", color=NEON_GREEN)
        embed.description = f"You've joined **{heist['target']}**.  Crew size: `{crew_count}`"
        await ctx.respond(embed=embed)

    # ── /heist execute ───────────────────────────────────────
    @heist_grp.command(name="execute", description="Execute the heist! (Leader only)")
    @discord.option("heist_id", description="Heist ID", type=int)
    async def heist_execute(self, ctx: discord.ApplicationContext, heist_id: int):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        heist = await get_heist(heist_id)
        if not heist:
            await ctx.respond(embed=NeonEmbed(title="❌ Heist Not Found", color=NEON_RED), ephemeral=True)
            return
        if heist["leader_id"] != player["id"]:
            await ctx.respond(content="Only the heist leader can execute.", ephemeral=True)
            return
        if heist["status"] != "recruiting":
            await ctx.respond(embed=NeonEmbed(title="Already Executed", color=NEON_RED), ephemeral=True)
            return
        crew_ids = [int(x) for x in heist["crew"].split(",") if x.strip()]
        # Find min_crew for this target
        min_crew = 1
        for t in HEIST_TARGETS:
            if t["name"] == heist["target"]:
                min_crew = t["min_crew"]
                break
        if len(crew_ids) < min_crew:
            await ctx.respond(
                embed=NeonEmbed(
                    title="👥 Crew Too Small",
                    description=f"Need at least `{min_crew}` crew members.  You have `{len(crew_ids)}`.",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        # ── EXECUTE LOGIC ──────────────────────────────────
        await advance_heist_phase(heist_id, "active", "active")
        # Success chance: base 50%, +5% per crew member above minimum, -7% per difficulty
        base_chance = 50
        crew_bonus = (len(crew_ids) - min_crew) * 5
        # Tech skill bonus: +10% if leader has hack_basics+
        leader_skills = await get_player_skills(player["id"])
        tech_bonus = 0
        for s in leader_skills:
            if s["skill_key"] in ("hack_basics", "deep_dive", "god_mode"):
                tech_bonus = s["level"] * 5
                break
        difficulty_penalty = heist["difficulty"] * 7
        success_pct = max(10, min(95, base_chance + crew_bonus + tech_bonus - difficulty_penalty))
        roll = random.randint(1, 100)
        success = roll <= success_pct

        # Build log
        log_lines = [
            f"🎯 Target: {heist['target']}",
            f"👥 Crew: {len(crew_ids)} runners",
            f"🎲 Success Chance: {success_pct}%  ┆  Roll: {roll}",
            "─" * 30,
        ]
        if success:
            await advance_heist_phase(heist_id, "completed", "completed")
            log_lines.append("✅ HEIST SUCCESSFUL!")
            # Distribute reward evenly
            per_person = heist["reward"] / len(crew_ids)
            for cid in crew_ids:
                from utils.database import get_player_by_id
                cp = await get_player_by_id(cid)
                if cp:
                    await update_player_credits(cp["discord_id"], per_person)
                    await update_player_xp(cp["discord_id"], 200)
            log_lines.append(f"💰 Each crew member: +{per_person:,.0f} ₵  & +200 XP")
            color = NEON_GREEN
        else:
            await advance_heist_phase(heist_id, "failed", "failed")
            log_lines.append("💀 HEIST FAILED — Security breached!")
            # Crew loses 10% of their credits
            for cid in crew_ids:
                from utils.database import get_player_by_id
                cp = await get_player_by_id(cid)
                if cp:
                    penalty = cp["credits"] * 0.10
                    await update_player_credits(cp["discord_id"], -penalty)
            log_lines.append("💸 All crew fined 10% of current balance.")
            color = NEON_RED

        embed = NeonEmbed(title="🚨 HEIST RESULT", color=color)
        embed.description = "\n".join(log_lines)
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(HeistsCog(bot))
