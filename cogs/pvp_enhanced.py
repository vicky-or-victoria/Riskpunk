# cogs/pvp_enhanced.py
# Enhanced PvP system with ranking, achievements, and combat stances

import discord
import random
from discord.ext import commands
from utils.database import (
    get_player, get_player_implants, get_player_skills, get_equipped_items,
    update_player_hp, update_player_xp, update_player_credits, log_pvp,
    set_hp_absolute, get_pool
)
from utils.game_data import IMPLANTS, ITEM_CATALOG
from utils.styles import RiskEmbed, NEON_CYAN, NEON_RED, NEON_GREEN, NEON_YELLOW, LINE
from utils.economy import PVP_WIN_REWARD, PVP_WIN_XP, PVP_ENTRY_FEE
from utils.cooldowns import check_cooldown, set_cooldown, format_cooldown_time


# Combat stances
COMBAT_STANCES = {
    "aggressive": {
        "name": "Aggressive",
        "desc": "High damage, low defense",
        "atk_mult": 1.3,
        "def_mult": 0.7,
        "emoji": "⚔️"
    },
    "defensive": {
        "name": "Defensive", 
        "desc": "Low damage, high defense",
        "atk_mult": 0.7,
        "def_mult": 1.3,
        "emoji": "🛡️"
    },
    "balanced": {
        "name": "Balanced",
        "desc": "Normal damage and defense",
        "atk_mult": 1.0,
        "def_mult": 1.0,
        "emoji": "⚖️"
    },
    "tactical": {
        "name": "Tactical",
        "desc": "Bonus to speed, normal damage/def",
        "atk_mult": 1.0,
        "def_mult": 1.0,
        "spd_mult": 1.2,
        "emoji": "🎯"
    }
}


def _compute_effective_stats(player, implants, skills, equipped_items, stance="balanced"):
    """Return dict with effective atk, def, spd, max_hp after all bonuses + stance."""
    stats = {
        "atk":    player["atk"],
        "def":    player["def"],
        "spd":    player["spd"],
        "max_hp": player["max_hp"],
        "hp":     player["hp"],
    }
    
    # Apply implant bonuses
    for imp in implants:
        data = IMPLANTS.get(imp["implant_key"], {})
        for stat, val in data.get("bonuses", {}).items():
            if stat in stats:
                stats[stat] += val
    
    # Apply skill bonuses
    skill_bonus_keys = ["combat_basics", "dual_strike", "killswitch",
                        "shadow_step", "ghost_protocol", "phantom_strike", "god_mode"]
    from utils.game_data import SKILL_TREE
    for s in skills:
        if s["skill_key"] in skill_bonus_keys:
            tree_data = SKILL_TREE.get(s["skill_key"], {})
            for stat, val in tree_data.get("bonus", {}).items():
                if stat in stats:
                    stats[stat] += val * s["level"]
    
    # Apply equipment bonuses
    for eq_item in equipped_items:
        item_data = ITEM_CATALOG.get(eq_item["item_name"], {})
        if 'atk_bonus' in item_data:
            stats["atk"] += item_data['atk_bonus']
        if 'def_bonus' in item_data:
            stats["def"] += item_data['def_bonus']
        if 'spd_bonus' in item_data:
            stats["spd"] += item_data['spd_bonus']
    
    # Apply stance modifiers
    stance_data = COMBAT_STANCES.get(stance, COMBAT_STANCES["balanced"])
    stats["atk"] = int(stats["atk"] * stance_data["atk_mult"])
    stats["def"] = int(stats["def"] * stance_data["def_mult"])
    stats["spd"] = int(stats["spd"] * stance_data.get("spd_mult", 1.0))
    
    # Clamp hp
    stats["hp"] = min(stats["hp"], stats["max_hp"])
    return stats


class PvPEnhancedCog(commands.Cog, name="PvP Enhanced"):
    """Enhanced PvP with ranking, stances, and betting."""

    def __init__(self, bot):
        self.bot = bot

    pvp_grp = discord.SlashCommandGroup("pvp", "PvP combat system")

    # ── /pvp duel ─────────────────────────────────────────────────
    @pvp_grp.command(name="duel", description="Challenge another player to a ranked duel.")
    @discord.option("opponent", description="The runner you want to fight", type=discord.Member)
    @discord.option("stance", description="Combat stance", choices=list(COMBAT_STANCES.keys()), default="balanced")
    async def pvp_duel(self, ctx: discord.ApplicationContext, opponent: discord.Member, stance: str):
        # Check cooldown
        is_ready, remaining = check_cooldown("pvp", ctx.author.id)
        if not is_ready:
            await ctx.respond(
                embed=RiskEmbed(
                    title="⏱️ Cooldown Active",
                    description=f"You can duel again in `{format_cooldown_time(remaining)}`",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        # Load players
        p1 = await get_player(ctx.author.id)
        if not p1:
            await ctx.respond(content="Not registered.", ephemeral=True)
            return
        
        p2 = await get_player(opponent.id)
        if not p2:
            await ctx.respond(
                embed=RiskEmbed(
                    title="❌ Opponent Not Found",
                    description="They aren't on the grid.",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        if p1["id"] == p2["id"]:
            await ctx.respond(content="You can't fight yourself.", ephemeral=True)
            return
        
        # Check entry fee
        if p1["credits"] < PVP_ENTRY_FEE:
            await ctx.respond(
                embed=RiskEmbed(
                    title="💸 Insufficient Credits",
                    description=f"PvP entry fee: `{PVP_ENTRY_FEE} ₵`",
                    color=NEON_RED
                ),
                ephemeral=True
            )
            return
        
        # Deduct entry fee
        await update_player_credits(ctx.author.id, -PVP_ENTRY_FEE)
        
        # Gather full stats
        p1_implants  = await get_player_implants(p1["id"])
        p1_skills    = await get_player_skills(p1["id"])
        p1_equipped  = await get_equipped_items(p1["id"])
        p2_implants  = await get_player_implants(p2["id"])
        p2_skills    = await get_player_skills(p2["id"])
        p2_equipped  = await get_equipped_items(p2["id"])

        # Opponent uses balanced stance by default
        s1 = _compute_effective_stats(p1, p1_implants, p1_skills, p1_equipped, stance)
        s2 = _compute_effective_stats(p2, p2_implants, p2_skills, p2_equipped, "balanced")

        # Simulate combat
        hp1 = s1["hp"]
        hp2 = s2["hp"]
        rounds = 0
        max_rounds = 50
        log_lines = []

        # Determine who goes first
        if s1["spd"] > s2["spd"]:
            first, second = 1, 2
        elif s2["spd"] > s1["spd"]:
            first, second = 2, 1
        else:
            first, second = random.choice([(1, 2), (2, 1)])

        while hp1 > 0 and hp2 > 0 and rounds < max_rounds:
            rounds += 1
            for attacker_id in [first, second]:
                if hp1 <= 0 or hp2 <= 0:
                    break
                if attacker_id == 1:
                    a_name, a_stats = p1["name"], s1
                    d_name, d_stats = p2["name"], s2
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

        # Determine winner
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

        # Apply consequences
        if winner_discord:
            await update_player_xp(winner_discord, PVP_WIN_XP)
            await update_player_credits(winner_discord, PVP_WIN_REWARD)
            
            # Update HP
            if winner_id == p1["id"]:
                await set_hp_absolute(p1["discord_id"], max(1, hp1))
                await set_hp_absolute(p2["discord_id"], 1)
            else:
                await set_hp_absolute(p2["discord_id"], max(1, hp2))
                await set_hp_absolute(p1["discord_id"], 1)
            
            # Loser loses entry fee
            await update_player_credits(loser_discord, -PVP_ENTRY_FEE)
            
            # Update PvP stats
            await _update_pvp_stats(winner_id, True)
            await _update_pvp_stats(p1["id"] if winner_id == p2["id"] else p2["id"], False)

        # Set cooldown
        set_cooldown("pvp", ctx.author.id)
        
        # Log & respond
        await log_pvp(p1["id"], p2["id"], winner_id, rounds, "\n".join(log_lines[-30:]))
        
        embed = RiskEmbed(title="⚔️ PvP DUEL COMPLETE", color=NEON_GREEN if winner_name else NEON_RED)
        stance_emoji = COMBAT_STANCES[stance]["emoji"]
        embed.description = (
            f"`{p1['name']}` {stance_emoji} vs `{p2['name']}`\n"
            f"{LINE}\n"
            f"🏆 Winner: **{winner_name or 'DRAW'}** after `{rounds}` rounds\n"
            f"{LINE}"
        )
        if log_lines:
            embed.add_field(name="📜 Battle Log", value=f"```{chr(10).join(log_lines[-25:][:1500])}```", inline=False)
        
        if winner_discord:
            embed.add_field(
                name="🏆 Rewards",
                value=f"Winner **{winner_name}**: `+{PVP_WIN_REWARD} ₵` & `+{PVP_WIN_XP} XP`\nLoser: `-{PVP_ENTRY_FEE} ₵` & set to 1 HP",
                inline=False
            )
        
        await ctx.respond(embed=embed)

    # ── /pvp rank ─────────────────────────────────────────────────
    @pvp_grp.command(name="rank", description="View PvP rankings.")
    async def pvp_rank(self, ctx: discord.ApplicationContext):
        pool = await get_pool()
        async with pool.acquire() as conn:
            rankings = await conn.fetch(
                """SELECT p.name, ps.wins, ps.losses, ps.elo 
                   FROM pvp_stats ps
                   JOIN players p ON ps.player_id = p.id
                   ORDER BY ps.elo DESC
                   LIMIT 10"""
            )
        
        embed = RiskEmbed(title="🏆 PvP RANKINGS", color=NEON_YELLOW)
        embed.description = "`Top combatants on the grid.`\n" + LINE
        
        if not rankings:
            embed.add_field(name="No Rankings Yet", value="Be the first to duel!", inline=False)
        else:
            lines = []
            medals = ["🥇", "🥈", "🥉"]
            for i, r in enumerate(rankings):
                medal = medals[i] if i < 3 else f"`#{i+1}`"
                win_rate = (r['wins'] / max(1, r['wins'] + r['losses'])) * 100
                lines.append(
                    f"{medal} **{r['name']}** | "
                    f"ELO: `{r['elo']}` | "
                    f"W/L: `{r['wins']}/{r['losses']}` ({win_rate:.1f}%)"
                )
            embed.add_field(name="", value="\n".join(lines), inline=False)
        
        await ctx.respond(embed=embed)


async def _update_pvp_stats(player_id: int, won: bool):
    """Update PvP statistics for a player"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if stats exist
        stats = await conn.fetchrow("SELECT * FROM pvp_stats WHERE player_id = $1", player_id)
        
        if stats:
            # Update existing stats
            new_wins = stats['wins'] + (1 if won else 0)
            new_losses = stats['losses'] + (0 if won else 1)
            elo_change = 25 if won else -15
            new_elo = max(0, stats['elo'] + elo_change)
            
            await conn.execute(
                """UPDATE pvp_stats 
                   SET wins = $1, losses = $2, elo = $3
                   WHERE player_id = $4""",
                new_wins, new_losses, new_elo, player_id
            )
        else:
            # Create new stats
            await conn.execute(
                """INSERT INTO pvp_stats (player_id, wins, losses, elo)
                   VALUES ($1, $2, $3, $4)""",
                player_id, 1 if won else 0, 0 if won else 1, 1000
            )


def setup(bot):
    bot.add_cog(PvPEnhancedCog(bot))
