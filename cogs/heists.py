# cogs/heists.py
import discord
import random
from discord.ext import commands
from utils.database import (
    get_player, create_heist, get_heist, get_active_heists,
    join_heist, advance_heist_phase, update_player_credits, update_player_xp,
    get_player_skills, log_event, add_item, get_pool
)
from utils.game_data import HEIST_TARGETS
from utils.styles import (
    RiskEmbed, heist_card, NEON_CYAN, NEON_GREEN, 
    NEON_RED, NEON_ORANGE, NEON_YELLOW, LINE, THIN_LINE
)


class HeistsCog(commands.Cog, name="Heists"):
    """Advanced team-based heist coordination system with dynamic phases."""

    def __init__(self, bot):
        self.bot = bot

    heist_grp = discord.SlashCommandGroup("heist", "Plan and execute high-stakes operations.")

    # ── /heist list ──────────────────────────────────────────
    @heist_grp.command(name="list", description="View all active heists.")
    async def heist_list(self, ctx: discord.ApplicationContext):
        heists = await get_active_heists()
        if not heists:
            embed = RiskEmbed(
                title="🚨 No Active Heists", 
                description="`The streets are quiet. Time to make some noise.`\n\n**Start one with** `/heist create`", 
                color=NEON_CYAN
            )
            await ctx.respond(embed=embed)
            return
        
        embed = RiskEmbed(title="🚨 ACTIVE HEISTS", color=NEON_ORANGE)
        embed.description = f"`Live operations across Risk City`\n{LINE}\n"
        
        for h in heists:
            crew_ids = [x.strip() for x in h["crew"].split(",") if x.strip()]
            status_emoji = {
                "recruiting": "📢",
                "planning": "🗺️",
                "active": "⚡",
                "completed": "✅",
                "failed": "💀"
            }.get(h['status'], "❓")
            
            embed.add_field(
                name=f"{status_emoji} Heist #{h['id']} — {h['target']}",
                value=(
                    f"**Phase:** `{h['phase'].upper()}`  ┆  **Status:** `{h['status'].upper()}`\n"
                    f"**Crew:** `{len(crew_ids)}`  ┆  **Payout:** `{h['reward']:,.0f} ₵`  ┆  **Difficulty:** `{h['difficulty']}/10`\n"
                    f"{THIN_LINE}\n"
                    f"`/heist join {h['id']}`  to enlist  ┆  `/heist info {h['id']}`  for details"
                ),
                inline=False
            )
        await ctx.respond(embed=embed)

    # ── /heist info ──────────────────────────────────────────
    @heist_grp.command(name="info", description="View detailed information about a heist.")
    @discord.option("heist_id", description="Heist ID", type=int)
    async def heist_info(self, ctx: discord.ApplicationContext, heist_id: int):
        heist = await get_heist(heist_id)
        if not heist:
            await ctx.respond(embed=RiskEmbed(title="❌ Heist Not Found", color=NEON_RED), ephemeral=True)
            return
        
        embed = heist_card(heist)
        
        # Add crew list
        crew_ids = [int(x) for x in heist["crew"].split(",") if x.strip()]
        crew_names = []
        pool = await get_pool()
        async with pool.acquire() as conn:
            for cid in crew_ids:
                player = await conn.fetchrow("SELECT name FROM players WHERE id = $1", cid)
                if player:
                    crew_names.append(player['name'])
        
        embed.add_field(
            name="👥 Crew Members",
            value=", ".join([f"`{name}`" for name in crew_names]) if crew_names else "`None yet`",
            inline=False
        )
        
        await ctx.respond(embed=embed)

    # ── /heist targets ───────────────────────────────────────
    @heist_grp.command(name="targets", description="Browse available heist targets.")
    async def heist_targets(self, ctx: discord.ApplicationContext):
        embed = RiskEmbed(title="🎯 Heist Targets", color=NEON_CYAN)
        embed.description = "`High-value objectives across Risk City.`\n" + LINE
        
        for i, t in enumerate(HEIST_TARGETS):
            difficulty_bar = "🟥" * t['difficulty'] + "⬜" * (10 - t['difficulty'])
            
            embed.add_field(
                name=f"{i}. {t['name']}",
                value=(
                    f"💰 **Reward:** `{t['reward']:,} ₵`\n"
                    f"⚙️ **Difficulty:** {difficulty_bar} `{t['difficulty']}/10`\n"
                    f"👥 **Min Crew:** `{t['min_crew']}`"
                ),
                inline=False
            )
        
        embed.add_field(
            name="💡 How to Start", 
            value=(
                "Use `/heist create <target_index>` to plan a job.\n"
                "Recruit crew with `/heist join` before executing."
            ), 
            inline=False
        )
        await ctx.respond(embed=embed)

    # ── /heist create ────────────────────────────────────────
    @heist_grp.command(name="create", description="Plan a new heist.")
    @discord.option("target_index", description="Target index from /heist targets", type=int, min_value=0)
    async def heist_create(self, ctx: discord.ApplicationContext, target_index: int):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="❌ Not registered. Use `/register` first.", ephemeral=True)
            return
        
        if target_index < 0 or target_index >= len(HEIST_TARGETS):
            await ctx.respond(
                embed=RiskEmbed(
                    title="❌ Invalid Target", 
                    description=f"Choose index 0–{len(HEIST_TARGETS)-1}", 
                    color=NEON_RED
                ), 
                ephemeral=True
            )
            return
        
        target = HEIST_TARGETS[target_index]
        
        # Planning fee = 10% of reward
        planning_fee = target["reward"] * 0.1
        if player["credits"] < planning_fee:
            await ctx.respond(
                embed=RiskEmbed(
                    title="💸 Insufficient Credits", 
                    description=f"**Planning Fee Required:** `{planning_fee:,.0f} ₵`\n**Your Balance:** `{player['credits']:,.0f} ₵`", 
                    color=NEON_RED
                ), 
                ephemeral=True
            )
            return
        
        # Deduct planning fee
        await update_player_credits(ctx.author.id, -planning_fee)
        
        # Create heist
        heist = await create_heist(player["id"], target["name"], target["reward"], target["difficulty"])
        
        embed = heist_card(heist)
        embed.add_field(
            name="📋 Next Steps",
            value=(
                f"**1.** Recruit crew with `/heist join {heist['id']}`  (need **{target['min_crew']}** total)\n"
                f"**2.** Execute with `/heist execute {heist['id']}` when ready\n"
                f"**3.** Crew shares the payout equally upon success\n\n"
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
            await ctx.respond(content="❌ Not registered.", ephemeral=True)
            return
        
        heist = await get_heist(heist_id)
        if not heist:
            await ctx.respond(
                embed=RiskEmbed(title="❌ Heist Not Found", color=NEON_RED), 
                ephemeral=True
            )
            return
        
        if heist["status"] != "recruiting":
            await ctx.respond(
                embed=RiskEmbed(
                    title="❌ Not Recruiting", 
                    description=f"Heist is in `{heist['status']}` phase.", 
                    color=NEON_RED
                ), 
                ephemeral=True
            )
            return
        
        success = await join_heist(heist_id, player["id"])
        if not success:
            await ctx.respond(
                embed=RiskEmbed(
                    title="⚠️ Already Enlisted", 
                    description="You're already part of this heist.", 
                    color=NEON_YELLOW
                ), 
                ephemeral=True
            )
            return
        
        # Refresh heist data
        heist = await get_heist(heist_id)
        crew_count = len([x for x in heist["crew"].split(",") if x.strip()])
        
        embed = RiskEmbed(title="✅ Crew Updated", color=NEON_GREEN)
        embed.description = (
            f"You've joined **{heist['target']}**.\n\n"
            f"**Crew Size:** `{crew_count}`\n"
            f"**Potential Payout:** `{heist['reward'] / crew_count:,.0f} ₵` per person"
        )
        await ctx.respond(embed=embed)

    # ── /heist execute ───────────────────────────────────────
    @heist_grp.command(name="execute", description="Execute the heist! (Leader only)")
    @discord.option("heist_id", description="Heist ID", type=int)
    async def heist_execute(self, ctx: discord.ApplicationContext, heist_id: int):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="❌ Not registered.", ephemeral=True)
            return
        
        heist = await get_heist(heist_id)
        if not heist:
            await ctx.respond(
                embed=RiskEmbed(title="❌ Heist Not Found", color=NEON_RED), 
                ephemeral=True
            )
            return
        
        if heist["leader_id"] != player["id"]:
            await ctx.respond(content="❌ Only the heist leader can execute.", ephemeral=True)
            return
        
        if heist["status"] != "recruiting":
            await ctx.respond(
                embed=RiskEmbed(title="❌ Already Executed", color=NEON_RED), 
                ephemeral=True
            )
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
                embed=RiskEmbed(
                    title="👥 Crew Too Small",
                    description=(
                        f"**Required:** `{min_crew}` crew members\n"
                        f"**Current:** `{len(crew_ids)}` members\n\n"
                        "Recruit more with `/heist join`"
                    ),
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        # ── HEIST EXECUTION LOGIC ──────────────────────────────
        await advance_heist_phase(heist_id, "active", "active")
        
        # Success calculation
        base_chance = 50
        crew_bonus = (len(crew_ids) - min_crew) * 5
        
        # Skill bonuses
        leader_skills = await get_player_skills(player["id"])
        tech_bonus = 0
        stealth_bonus = 0
        
        for s in leader_skills:
            if s["skill_key"] in ("hack_basics", "deep_dive", "god_mode"):
                tech_bonus = s["level"] * 5
            if s["skill_key"] in ("shadow_step", "ghost_protocol", "phantom_mode"):
                stealth_bonus = s["level"] * 3
        
        difficulty_penalty = heist["difficulty"] * 7
        
        # Calculate total success chance
        success_pct = max(10, min(95, base_chance + crew_bonus + tech_bonus + stealth_bonus - difficulty_penalty))
        
        # Roll for success
        roll = random.randint(1, 100)
        success = roll <= success_pct
        
        # Build detailed log
        log_lines = [
            f"🎯 **Target:** {heist['target']}",
            f"👥 **Crew:** {len(crew_ids)} runners",
            f"🎲 **Success Chance:** {success_pct}%",
            f"🎲 **Roll:** {roll}",
            "",
            "**Modifiers:**",
            f"  • Base Chance: +{base_chance}%",
            f"  • Extra Crew: +{crew_bonus}%",
            f"  • Tech Skills: +{tech_bonus}%",
            f"  • Stealth Skills: +{stealth_bonus}%",
            f"  • Difficulty: -{difficulty_penalty}%",
            "─" * 40,
        ]
        
        if success:
            await advance_heist_phase(heist_id, "completed", "completed")
            log_lines.append("✅ **HEIST SUCCESSFUL!**")
            log_lines.append("")
            
            # Distribute reward evenly
            per_person = heist["reward"] / len(crew_ids)
            xp_reward = 150 + (heist["difficulty"] * 20)
            
            # Get crew names for display
            pool = await get_pool()
            crew_details = []
            async with pool.acquire() as conn:
                for cid in crew_ids:
                    cp = await conn.fetchrow("SELECT discord_id, name FROM players WHERE id = $1", cid)
                    if cp:
                        await update_player_credits(cp["discord_id"], per_person)
                        await update_player_xp(cp["discord_id"], xp_reward)
                        crew_details.append(cp['name'])
            
            log_lines.append("💰 **Payout Distribution:**")
            for name in crew_details:
                log_lines.append(f"  • {name}: `+{per_person:,.0f} ₵` & `+{xp_reward} XP`")
            
            # Bonus loot chance
            if random.random() < 0.3:  # 30% chance
                bonus_items = ["Hacking Rig", "Stealth Suit", "Data Shard", "EMP Grenade"]
                bonus = random.choice(bonus_items)
                log_lines.append("")
                log_lines.append(f"🎁 **Bonus Loot Found:** {bonus}")
                for cid in crew_ids:
                    await add_item(cid, bonus, 1)
            
            color = NEON_GREEN
            
        else:
            await advance_heist_phase(heist_id, "failed", "failed")
            log_lines.append("💀 **HEIST FAILED!**")
            log_lines.append("Security was tighter than expected.")
            log_lines.append("")
            
            # Penalties
            penalty_pct = 0.10
            pool = await get_pool()
            penalties = []
            async with pool.acquire() as conn:
                for cid in crew_ids:
                    cp = await conn.fetchrow("SELECT discord_id, name, credits FROM players WHERE id = $1", cid)
                    if cp:
                        penalty = cp["credits"] * penalty_pct
                        await update_player_credits(cp["discord_id"], -penalty)
                        penalties.append((cp['name'], penalty))
            
            log_lines.append("💸 **Fines Levied:**")
            for name, penalty in penalties:
                log_lines.append(f"  • {name}: `-{penalty:,.0f} ₵` ({int(penalty_pct*100)}% fine)")
            
            color = NEON_RED
        
        embed = RiskEmbed(title="🚨 HEIST RESULT", color=color)
        embed.description = "\n".join(log_lines)
        await ctx.respond(embed=embed)

    # ── /heist abandon ───────────────────────────────────────
    @heist_grp.command(name="abandon", description="Abandon a heist (Leader only, recruiting phase only)")
    @discord.option("heist_id", description="Heist ID", type=int)
    async def heist_abandon(self, ctx: discord.ApplicationContext, heist_id: int):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="❌ Not registered.", ephemeral=True)
            return
        
        heist = await get_heist(heist_id)
        if not heist:
            await ctx.respond(
                embed=RiskEmbed(title="❌ Heist Not Found", color=NEON_RED), 
                ephemeral=True
            )
            return
        
        if heist["leader_id"] != player["id"]:
            await ctx.respond(content="❌ Only the heist leader can abandon.", ephemeral=True)
            return
        
        if heist["status"] != "recruiting":
            await ctx.respond(
                embed=RiskEmbed(
                    title="❌ Cannot Abandon", 
                    description="Can only abandon during recruiting phase.", 
                    color=NEON_RED
                ), 
                ephemeral=True
            )
            return
        
        # Delete heist
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM heists WHERE id = $1", heist_id)
        
        embed = RiskEmbed(title="🗑️ Heist Abandoned", color=NEON_YELLOW)
        embed.description = f"**{heist['target']}** operation has been called off."
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(HeistsCog(bot))