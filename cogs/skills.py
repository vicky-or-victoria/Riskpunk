# cogs/skills.py
import discord
from discord.ext import commands
from utils.database import (
    get_player, get_player_skills, get_skill, set_skill, update_player_credits
)
from utils.game_data import SKILL_TREE, SKILL_BRANCHES
from utils.styles import RiskEmbed, NEON_CYAN, NEON_GREEN, NEON_RED, LINE, THIN_LINE


class SkillsCog(commands.Cog, name="Skills"):
    """Skill tree specialisation system."""

    def __init__(self, bot):
        self.bot = bot

    skills_grp = discord.SlashCommandGroup("skills", "Skill tree operations.")

    # ── /skills tree ─────────────────────────────────────────
    @skills_grp.command(name="tree", description="View the full skill tree with unlock status.")
    async def skills_tree(self, ctx: discord.ApplicationContext):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        owned = await get_player_skills(player["id"])
        owned_map = {s["skill_key"]: s["level"] for s in owned}

        embed = RiskEmbed(title="🧬 SKILL TREE", color=NEON_CYAN)
        embed.description = "`Neural pathway mapping.  Upgrade to unlock potential.`\n" + LINE

        for branch in SKILL_BRANCHES:
            branch_skills = [(k, v) for k, v in SKILL_TREE.items() if v["branch"] == branch]
            lines = []
            for key, data in branch_skills:
                lvl = owned_map.get(key, 0)
                status = f"⭐ Lvl {lvl}" if lvl > 0 else "🔒 Locked"
                parent_status = ""
                if data["parent"] and data["parent"] not in owned_map:
                    parent_status = " *(needs `{}`)*".format(data["parent"].replace("_", " ").title())
                bar = "█" * lvl + "░" * (5 - min(lvl, 5))
                lines.append(
                    f"  `{key}` — **{data['name']}**  {status} {bar}\n"
                    f"         ┆ {data['description']}\n"
                    f"         ┆ Cost: `{data['cost']:,} ₵`{parent_status}"
                )
            embed.add_field(
                name=f"🔹 {branch.upper()} Branch",
                value="\n".join(lines),
                inline=False
            )
        embed.add_field(name="💡 Usage", value="`/skills learn <skill_key>`  or  `/skills upgrade <skill_key>`", inline=False)
        await ctx.respond(embed=embed)

    # ── /skills my ───────────────────────────────────────────
    @skills_grp.command(name="my", description="View only your unlocked skills.")
    async def skills_my(self, ctx: discord.ApplicationContext):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        skills = await get_player_skills(player["id"])
        await ctx.respond(embed=skill_tree_embed(player["name"], skills))

    # ── /skills learn ────────────────────────────────────────
    @skills_grp.command(name="learn", description="Learn a new skill (first level).")
    @discord.option("skill_key", description="Skill key from /skills tree")
    async def skills_learn(self, ctx: discord.ApplicationContext, skill_key: str):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        data = SKILL_TREE.get(skill_key.lower())
        if not data:
            await ctx.respond(embed=RiskEmbed(title="❌ Unknown Skill", description=f"`{skill_key}` not found.", color=NEON_RED), ephemeral=True)
            return
        # Check already owned
        existing = await get_skill(player["id"], skill_key.lower())
        if existing:
            await ctx.respond(embed=RiskEmbed(title="Already Learned", description=f"Use `/skills upgrade {skill_key}` to level up.", color=NEON_CYAN), ephemeral=True)
            return
        # Check prerequisite
        if data["parent"]:
            prereq = await get_skill(player["id"], data["parent"])
            if not prereq:
                await ctx.respond(
                    embed=RiskEmbed(
                        title="🔒 Prerequisite Required",
                        description=f"Must learn `{data['parent'].replace('_', ' ').title()}` first.",
                        color=NEON_RED
                    ),
                    ephemeral=True
                )
                return
        # Check cost
        if player["credits"] < data["cost"]:
            await ctx.respond(embed=RiskEmbed(title="💸 Can't Afford", description=f"Costs `{data['cost']:,} ₵`", color=NEON_RED), ephemeral=True)
            return
        await update_player_credits(ctx.author.id, -data["cost"])
        await set_skill(player["id"], skill_key.lower(), 1)
        embed = RiskEmbed(title="🧬 Skill Learned", color=NEON_GREEN)
        embed.description = (
            f"**{data['name']}** — Level 1\n"
            f"{THIN_LINE}\n"
            f"{data['description']}\n"
            f"💵 `{data['cost']:,} ₵` deducted."
        )
        if data["bonus"]:
            bonus_str = ", ".join(f"+{v} {k.upper()}" for k, v in data["bonus"].items())
            embed.add_field(name="⚡ Passive Bonus", value=bonus_str, inline=False)
        await ctx.respond(embed=embed)

    # ── /skills upgrade ──────────────────────────────────────
    @skills_grp.command(name="upgrade", description="Upgrade an existing skill to the next level (max 5).")
    @discord.option("skill_key", description="Skill key")
    async def skills_upgrade(self, ctx: discord.ApplicationContext, skill_key: str):
        player = await get_player(ctx.author.id)
        if not player:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        data = SKILL_TREE.get(skill_key.lower())
        if not data:
            await ctx.respond(embed=RiskEmbed(title="❌ Unknown Skill", color=NEON_RED), ephemeral=True)
            return
        existing = await get_skill(player["id"], skill_key.lower())
        if not existing:
            await ctx.respond(embed=RiskEmbed(title="🔒 Not Learned", description="Use `/skills learn` first.", color=NEON_RED), ephemeral=True)
            return
        if existing["level"] >= 5:
            await ctx.respond(embed=RiskEmbed(title="⭐ Max Level", description="Already at level 5.", color=NEON_CYAN), ephemeral=True)
            return
        # Upgrade cost scales: base × current_level
        upgrade_cost = data["cost"] * existing["level"]
        if player["credits"] < upgrade_cost:
            await ctx.respond(embed=RiskEmbed(title="💸 Can't Afford", description=f"Upgrade costs `{upgrade_cost:,} ₵`", color=NEON_RED), ephemeral=True)
            return
        await update_player_credits(ctx.author.id, -upgrade_cost)
        new_level = existing["level"] + 1
        await set_skill(player["id"], skill_key.lower(), new_level)
        embed = RiskEmbed(title="⬆️ Skill Upgraded", color=NEON_GREEN)
        embed.description = (
            f"**{data['name']}** → Level {new_level}\n"
            f"{THIN_LINE}\n"
            f"💵 `{upgrade_cost:,} ₵` deducted."
        )
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(SkillsCog(bot))
