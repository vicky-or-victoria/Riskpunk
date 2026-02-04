# cogs/territory.py
import discord
import random
from discord.ext import commands
from utils.database import (
    get_player, get_all_territories, get_territory,
    claim_territory, damage_territory, get_faction,
    get_faction_members, update_player_credits, update_player_xp
)
from utils.styles import RiskEmbed, NEON_CYAN, NEON_GREEN, NEON_RED, NEON_BLUE, LINE


class TerritoryCog(commands.Cog, name="Territory"):
    """Territory control — seize, defend, profit."""

    def __init__(self, bot):
        self.bot = bot

    territory_grp = discord.SlashCommandGroup("territory", "Territory control.")

    # ── /territory map ───────────────────────────────────────
    @territory_grp.command(name="map", description="View all territories on the grid.")
    async def territory_map(self, ctx: discord.ApplicationContext):
        territories = await get_all_territories()
        embed = RiskEmbed(title="🗺️ NEO‑TOKYO TERRITORY MAP", color=NEON_BLUE)
        embed.description = "`Real‑time control overview.`\n" + LINE
        for t in territories:
            owner_name = "Unclaimed"
            if t["owner_faction"]:
                fac = await get_faction(t["owner_faction"])
                owner_name = fac["name"] if fac else "Unknown"
            status_emoji = "🟢" if t["owner_faction"] else "⚪"
            embed.add_field(
                name=f"{status_emoji} {t['name']}",
                value=(
                    f"`{t['description']}`\n"
                    f"🏢 Owner: **{owner_name}**  ┆  "
                    f"🛡️ Def: `{t['defense']}/100`  ┆  "
                    f"💰 `{t['income']:,.0f} ₵/wk`"
                ),
                inline=False
            )
        await ctx.respond(embed=embed)

    # ── /territory info ──────────────────────────────────────
    @territory_grp.command(name="info", description="Detailed info on a single territory.")
    @discord.option("territory_key", description="Territory key (e.g. neon_district)")
    async def territory_info(self, ctx: discord.ApplicationContext, territory_key: str):
        t = await get_territory(territory_key.lower())
        if not t:
            await ctx.respond(embed=RiskEmbed(title="❌ Not Found", description=f"`{territory_key}` is not a valid territory.", color=NEON_RED), ephemeral=True)
            return
        owner_name = "Unclaimed"
        if t["owner_faction"]:
            fac = await get_faction(t["owner_faction"])
            owner_name = fac["name"] if fac else "Unknown"
        await ctx.respond(embed=territory_card(t, owner_name))

    # ── /territory attack ────────────────────────────────────
    @territory_grp.command(name="attack", description="Attack a territory to seize it (costs credits + rolls vs defense).")
    @discord.option("territory_key", description="Territory key")
    async def territory_attack(self, ctx: discord.ApplicationContext, territory_key: str):
        player = await get_player(ctx.author.id)
        if not player or not player["faction_id"]:
            await ctx.respond(content="You must belong to a faction to attack.", ephemeral=True)
            return
        t = await get_territory(territory_key.lower())
        if not t:
            await ctx.respond(embed=RiskEmbed(title="❌ Not Found", color=NEON_RED), ephemeral=True)
            return
        if t["owner_faction"] == player["faction_id"]:
            await ctx.respond(embed=RiskEmbed(title="Already Yours", description="Your faction controls this territory.", color=NEON_CYAN), ephemeral=True)
            return
        # Cost to attack: 10% of territory income × difficulty (defense / 10)
        attack_cost = t["income"] * 0.1 * max(1, t["defense"] / 10)
        if player["credits"] < attack_cost:
            await ctx.respond(embed=RiskEmbed(title="💸 Insufficient Funds", description=f"Attack costs `{attack_cost:,.0f} ₵`", color=NEON_RED), ephemeral=True)
            return
        await update_player_credits(ctx.author.id, -attack_cost)
        # Gather your faction's war power
        your_faction = await get_faction(player["faction_id"])
        your_members = await get_faction_members(player["faction_id"])
        atk_power = your_faction["aggression"] + len(your_members) * 3 + random.randint(5, 40)
        def_power = t["defense"] + random.randint(0, 30)
        log_lines = [
            f"🗺️ **{t['name']}**",
            f"⚔️ ATK Power: `{atk_power}`  (aggression + crew + roll)",
            f"🛡️ DEF Power: `{def_power}`  (base defense + roll)",
            "─" * 30,
        ]
        if atk_power >= def_power:
            # Victory — claim it
            await claim_territory(t["key"], player["faction_id"])
            # Reduce defense to 25 (freshly seized)
            from utils.database import get_db
            async with await get_db() as db:
                await db.execute("UPDATE territories SET defense = 25 WHERE key = ?", (t["key"],))
                await db.commit()
            log_lines.append(f"🏆 **{your_faction['name']} SEIZED {t['name']}!**")
            # Reward all faction members
            for m in your_members:
                await update_player_credits(m["discord_id"], 500)
                await update_player_xp(m["discord_id"], 100)
            log_lines.append(f"💰 All {your_faction['name']} members: +500 ₵ & +100 XP")
            color = NEON_GREEN
        else:
            # Failed attack — defender defense goes up a bit
            await damage_territory(t["key"], -10)  # negative = increase  (we flip logic)
            # Actually increase defense
            from utils.database import get_db
            async with await get_db() as db:
                await db.execute("UPDATE territories SET defense = MIN(100, defense + 10) WHERE key = ?", (t["key"],))
                await db.commit()
            log_lines.append(f"💀 Attack failed.  {t['name']} defense strengthened.")
            color = NEON_RED

        embed = RiskEmbed(title="⚔️ TERRITORY BATTLE", color=color)
        embed.description = "\n".join(log_lines)
        embed.add_field(name="💵 Cost", value=f"`{attack_cost:,.0f} ₵` deducted", inline=True)
        await ctx.respond(embed=embed)

    # ── /territory fortify ───────────────────────────────────
    @territory_grp.command(name="fortify", description="Spend credits to boost a territory's defense.")
    @discord.option("territory_key", description="Territory key")
    @discord.option("amount", description="Defense points to add (50 ₵ each)", type=int, min_value=1, max_value=100)
    async def territory_fortify(self, ctx: discord.ApplicationContext, territory_key: str, amount: int):
        player = await get_player(ctx.author.id)
        if not player or not player["faction_id"]:
            await ctx.respond(content="Must belong to a faction.", ephemeral=True)
            return
        t = await get_territory(territory_key.lower())
        if not t:
            await ctx.respond(embed=RiskEmbed(title="❌ Not Found", color=NEON_RED), ephemeral=True)
            return
        if t["owner_faction"] != player["faction_id"]:
            await ctx.respond(content="You can only fortify your own faction's territory.", ephemeral=True)
            return
        cost = amount * 50
        if player["credits"] < cost:
            await ctx.respond(embed=RiskEmbed(title="💸 Can't Afford", description=f"Costs `{cost:,} ₵`", color=NEON_RED), ephemeral=True)
            return
        # Cap at 100
        actual = min(amount, 100 - t["defense"])
        if actual <= 0:
            await ctx.respond(embed=RiskEmbed(title="Already Maxed", description="Defense is already at 100.", color=NEON_CYAN), ephemeral=True)
            return
        real_cost = actual * 50
        await update_player_credits(ctx.author.id, -real_cost)
        from utils.database import get_db
        async with await get_db() as db:
            await db.execute("UPDATE territories SET defense = defense + ? WHERE key = ?", (actual, t["key"]))
            await db.commit()
        embed = RiskEmbed(title="🏰 Fortified", color=NEON_GREEN)
        embed.description = f"**{t['name']}** defense +{actual}  ┆  Cost: `{real_cost:,} ₵`"
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(TerritoryCog(bot))
