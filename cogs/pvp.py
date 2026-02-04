# cogs/pvp.py
import discord
import random
from discord.ext import commands
from utils.database import (
    get_player, get_player_implants, get_player_skills, get_inventory,
    update_player_hp, update_player_xp, update_player_credits, log_pvp
)
from utils.game_data import IMPLANTS, ITEM_CATALOG
from utils.styles import RiskEmbed, NEON_CYAN, NEON_RED, NEON_GREEN, LINE


def _compute_effective_stats(player, implants, skills, inventory):
    """Return dict with effective atk, def, spd, max_hp after all bonuses."""
    stats = {
        "atk":    player["atk"],
        "def":    player["def"],
        "spd":    player["spd"],
        "max_hp": player["max_hp"],
        "hp":     player["hp"],
    }
    # ── Implant bonuses ──────────────────────────────────
    for imp in implants:
        data = IMPLANTS.get(imp["implant_key"], {})
        for stat, val in data.get("bonuses", {}).items():
            if stat in stats:
                stats[stat] += val
    # ── Skill bonuses (combat / stealth branches give stat boosts) ──
    skill_bonus_keys = ["combat_basics", "dual_strike", "killswitch",
                        "shadow_step", "ghost_protocol", "phantom_strike", "god_mode"]
    from utils.game_data import SKILL_TREE
    for s in skills:
        if s["skill_key"] in skill_bonus_keys:
            tree_data = SKILL_TREE.get(s["skill_key"], {})
            for stat, val in tree_data.get("bonus", {}).items():
                if stat in stats:
                    stats[stat] += val * s["level"]
    # ── Item bonuses (equipped items in inventory) ──────
    for inv_item in inventory:
        item_data = ITEM_CATALOG.get(inv_item["item_name"], {})
        for key in ("atk_bonus", "def_bonus", "spd_bonus"):
            stat_name = key.replace("_bonus", "")
            if key in item_data:
                stats[stat_name] += item_data[key]
    # Clamp hp
    stats["hp"] = min(stats["hp"], stats["max_hp"])
    return stats


class PvPCog(commands.Cog, name="PvP"):
    """Player-vs-Player duel system."""

    def __init__(self, bot):
        self.bot = bot

    # ── /pvp ─────────────────────────────────────────────────
    @discord.slash_command(description="Challenge another player to a duel.")
    @discord.option("opponent", description="The runner you want to fight", type=discord.Member)
    async def pvp(self, ctx: discord.ApplicationContext, opponent: discord.Member):
        # Load attacker
        p1 = await get_player(ctx.author.id)
        if not p1:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        # Load defender
        p2 = await get_player(opponent.id)
        if not p2:
            await ctx.respond(embed=RiskEmbed(title="❌ Opponent Not Found", description="They aren't on the grid.", color=NEON_RED), ephemeral=True)
            return
        if p1["id"] == p2["id"]:
            await ctx.respond(content="You can't fight yourself.", ephemeral=True)
            return
        # ── Gather full stats ─────────────────────────────
        p1_implants  = await get_player_implants(p1["id"])
        p1_skills    = await get_player_skills(p1["id"])
        p1_inventory = await get_inventory(p1["id"])
        p2_implants  = await get_player_implants(p2["id"])
        p2_skills    = await get_player_skills(p2["id"])
        p2_inventory = await get_inventory(p2["id"])

        s1 = _compute_effective_stats(p1, p1_implants, p1_skills, p1_inventory)
        s2 = _compute_effective_stats(p2, p2_implants, p2_skills, p2_inventory)

        # ── Simulate turn-based combat ─────────────────────
        hp1 = s1["hp"]
        hp2 = s2["hp"]
        rounds = 0
        max_rounds = 50
        log_lines = []

        # Determine who goes first based on speed
        if s1["spd"] > s2["spd"]:
            first, second = 1, 2
        elif s2["spd"] > s1["spd"]:
            first, second = 2, 1
        else:
            first, second = random.choice([(1, 2), (2, 1)])

        def attacker_data(who):
            if who == 1:
                return p1["name"], s1, "hp1"
            return p2["name"], s2, "hp2"

        while hp1 > 0 and hp2 > 0 and rounds < max_rounds:
            rounds += 1
            for attacker_id in [first, second]:
                if hp1 <= 0 or hp2 <= 0:
                    break
                if attacker_id == 1:
                    a_name, a_stats = p1["name"], s1
                    d_name, d_stats = p2["name"], s2
                    # damage to hp2
                    raw_dmg = a_stats["atk"] + random.randint(0, max(1, a_stats["atk"] // 2))
                    actual_dmg = max(1, raw_dmg - d_stats["def"] + random.randint(-3, 3))
                    hp2 -= actual_dmg
                    log_lines.append(f"Rnd {rounds}: {a_name} → {actual_dmg} dmg  [{d_name} HP: {max(0, hp2)}]")
                else:
                    a_name, a_stats = p2["name"], s2
                    d_name, d_stats = p1["name"], s1
                    raw_dmg = a_stats["atk"] + random.randint(0, max(1, a_stats["atk"] // 2))
                    actual_dmg = max(1, raw_dmg - d_stats["def"] + random.randint(-3, 3))
                    hp1 -= actual_dmg
                    log_lines.append(f"Rnd {rounds}: {a_name} → {actual_dmg} dmg  [{d_name} HP: {max(0, hp1)}]")

        # ── Determine winner ──────────────────────────────
        if hp1 > 0 and hp2 <= 0:
            winner_name = p1["name"]
            winner_discord = p1["discord_id"]
            loser_discord  = p2["discord_id"]
            winner_id      = p1["id"]
        elif hp2 > 0 and hp1 <= 0:
            winner_name = p2["name"]
            winner_discord = p2["discord_id"]
            loser_discord  = p1["discord_id"]
            winner_id      = p2["id"]
        else:
            winner_name = "DRAW"
            winner_discord = None
            loser_discord  = None
            winner_id      = None

        # ── Apply consequences ────────────────────────────
        if winner_discord:
            await update_player_xp(winner_discord, 150)
            await update_player_credits(winner_discord, 500)
            # Winner's HP reduced to what's left (proportional)
            if winner_id == p1["id"]:
                # p1 won, set their HP to hp1
                await _set_hp_absolute(p1["discord_id"], max(1, hp1))
                # p2 goes to 1 HP (beaten, not dead)
                await _set_hp_absolute(p2["discord_id"], 1)
            else:
                await _set_hp_absolute(p2["discord_id"], max(1, hp2))
                await _set_hp_absolute(p1["discord_id"], 1)
            # Loser loses 200 credits
            await update_player_credits(loser_discord, -200)

        # ── Log & respond ─────────────────────────────────
        await log_pvp(p1["id"], p2["id"], winner_id, rounds, "\n".join(log_lines[-30:]))
        embed = pvp_result_embed(p1["name"], p2["name"], winner_name, rounds, "\n".join(log_lines[-25:]))
        if winner_discord:
            embed.add_field(
                name="🏆 Rewards",
                value=f"Winner **{winner_name}**: `+500 ₵` & `+150 XP`\nLoser: `-200 ₵` & set to 1 HP",
                inline=False
            )
        await ctx.respond(embed=embed)


# ── DB helper ────────────────────────────────────────────────────────────────
async def _set_hp_absolute(discord_id: int, hp: int):
    from utils.database import get_db
    async with await get_db() as db:
        await db.execute("UPDATE players SET hp = ? WHERE discord_id = ?", (hp, discord_id))
        await db.commit()


def setup(bot):
    bot.add_cog(PvPCog(bot))
