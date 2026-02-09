import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
import random
from datetime import datetime, timedelta

from utils.database import (
    get_pool, 
    get_player,
    update_player_credits
)
from utils.styles import RiskEmbed, NEON_CYAN, NEON_GREEN, NEON_RED, NEON_YELLOW, NEON_MAGENTA, LINE, THIN_LINE

COMPANY_TYPES = {
    # STARTER TIER - Low cost, low profit, good for beginners
    "street_vendor": {
        "name": "Street Vendor Cart",
        "tier": "Starter",
        "desc": "Sell counterfeit goods and stolen merchandise to passersby.",
        "cost": 5000,
        "income_per_min": 8,
        "risk": 0.12
    },
    "data_mule": {
        "name": "Data Mule Service",
        "tier": "Starter",
        "desc": "Transport encrypted packages between fixers for a fee.",
        "cost": 7500,
        "income_per_min": 12,
        "risk": 0.10
    },
    "scrap_yard": {
        "name": "Scrap Yard",
        "tier": "Starter",
        "desc": "Buy junked tech, strip parts, flip for profit.",
        "cost": 10000,
        "income_per_min": 15,
        "risk": 0.08
    },
    
    # STREET TIER - Medium-low investment, steady income
    "chop_shop": {
        "name": "Chop Shop",
        "tier": "Street",
        "desc": "Strip stolen vehicles and sell parts on the black market.",
        "cost": 20000,
        "income_per_min": 28,
        "risk": 0.15
    },
    "underground_clinic": {
        "name": "Underground Clinic",
        "tier": "Street",
        "desc": "Patch up runners who can't afford real hospitals.",
        "cost": 25000,
        "income_per_min": 35,
        "risk": 0.08
    },
    "pirate_radio": {
        "name": "Pirate Radio Station",
        "tier": "Street",
        "desc": "Broadcast unlicensed content and sell ad slots to shady clients.",
        "cost": 18000,
        "income_per_min": 22,
        "risk": 0.10
    },
    "tattoo_parlor": {
        "name": "Tattoo Parlor",
        "tier": "Street",
        "desc": "Ink and identity modification. Some clients prefer to disappear.",
        "cost": 15000,
        "income_per_min": 20,
        "risk": 0.06
    },
    
    # CORPORATE TIER - Good investment, professional operations
    "data_broker": {
        "name": "Data Brokerage",
        "tier": "Corporate",
        "desc": "Buy and sell corporate intel to the highest bidder.",
        "cost": 40000,
        "income_per_min": 55,
        "risk": 0.12
    },
    "nightclub": {
        "name": "Underground Club",
        "tier": "Corporate",
        "desc": "Legitimate front with some less legitimate backroom deals.",
        "cost": 50000,
        "income_per_min": 68,
        "risk": 0.08
    },
    "private_security": {
        "name": "Private Security Firm",
        "tier": "Corporate",
        "desc": "Protection services for those who can afford discretion.",
        "cost": 45000,
        "income_per_min": 62,
        "risk": 0.14
    },
    "gambling_den": {
        "name": "Gambling Den",
        "tier": "Corporate",
        "desc": "Cards, dice, and rigged games. House always wins.",
        "cost": 38000,
        "income_per_min": 50,
        "risk": 0.16
    },
    
    # SYNDICATE TIER - High investment, high returns
    "synth_lab": {
        "name": "Synth Lab",
        "tier": "Syndicate",
        "desc": "Cook designer drugs for the city's elite.",
        "cost": 70000,
        "income_per_min": 95,
        "risk": 0.20
    },
    "hack_collective": {
        "name": "Hacker Collective",
        "tier": "Syndicate",
        "desc": "Penetration testing and corporate espionage as a service.",
        "cost": 80000,
        "income_per_min": 110,
        "risk": 0.18
    },
    "smuggling_ring": {
        "name": "Smuggling Ring",
        "tier": "Syndicate",
        "desc": "Move contraband across district borders and take a cut.",
        "cost": 85000,
        "income_per_min": 115,
        "risk": 0.22
    },
    "organ_trade": {
        "name": "Organ Trade Network",
        "tier": "Syndicate",
        "desc": "Supply fresh bio-ware to clinics with no questions asked.",
        "cost": 75000,
        "income_per_min": 102,
        "risk": 0.25
    },
    
    # MEGACORP TIER - Massive investment, massive profits
    "arms_dealer": {
        "name": "Arms Dealership",
        "tier": "Megacorp",
        "desc": "Move weapons between factions and take a cut.",
        "cost": 120000,
        "income_per_min": 165,
        "risk": 0.25
    },
    "cybernetics_factory": {
        "name": "Cybernetics Factory",
        "tier": "Megacorp",
        "desc": "Manufacture and distribute chrome to the masses.",
        "cost": 150000,
        "income_per_min": 200,
        "risk": 0.15
    },
    "money_laundering": {
        "name": "Money Laundering Front",
        "tier": "Megacorp",
        "desc": "Clean dirty credits through a network of shell companies.",
        "cost": 100000,
        "income_per_min": 140,
        "risk": 0.28
    },
    "biotech_lab": {
        "name": "Biotech Research Lab",
        "tier": "Megacorp",
        "desc": "Develop experimental augments and sell to the highest bidder.",
        "cost": 140000,
        "income_per_min": 185,
        "risk": 0.18
    },
    
    # EMPIRE TIER - Endgame businesses, extreme profits
    "ai_development": {
        "name": "AI Development Corp",
        "tier": "Empire",
        "desc": "Build and lease corporate AI systems. Cutting edge tech.",
        "cost": 250000,
        "income_per_min": 320,
        "risk": 0.12
    },
    "satellite_network": {
        "name": "Satellite Network",
        "tier": "Empire",
        "desc": "Control orbital infrastructure and sell bandwidth worldwide.",
        "cost": 300000,
        "income_per_min": 380,
        "risk": 0.10
    },
    "megacorp_subsidiary": {
        "name": "Megacorp Subsidiary",
        "tier": "Empire",
        "desc": "Own a piece of the corporations that run the city.",
        "cost": 350000,
        "income_per_min": 450,
        "risk": 0.08
    },
    "black_market_cartel": {
        "name": "Black Market Cartel",
        "tier": "Empire",
        "desc": "Control entire supply chains of illegal goods across Risk City.",
        "cost": 280000,
        "income_per_min": 360,
        "risk": 0.22
    }
}

TIER_COLORS = {
    "Starter": NEON_GREEN,
    "Street": NEON_CYAN,
    "Corporate": NEON_YELLOW,
    "Syndicate": NEON_MAGENTA,
    "Megacorp": NEON_RED,
    "Empire": 0x9B59B6
}

# Default company limit
DEFAULT_COMPANY_LIMIT = 3


class Companies(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    company = SlashCommandGroup("company", "Manage your business empire")
    
    async def _get_company_limit(self, guild_id: int) -> int:
        """Get the company limit for a guild (default: 3)"""
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT company_limit FROM guild_settings WHERE guild_id = $1",
                guild_id
            )
            return result['company_limit'] if result else DEFAULT_COMPANY_LIMIT
    
    async def _has_admin_perms(self, ctx: discord.ApplicationContext) -> bool:
        """Check if user has admin permissions, bot owner, or trusted role"""
        # Check if user is bot owner
        app_info = await self.bot.application_info()
        if ctx.author.id == app_info.owner.id:
            return True
        
        # Check if user is guild owner
        if ctx.guild and ctx.author.id == ctx.guild.owner_id:
            return True
        
        # Check if user has administrator permission
        if ctx.author.guild_permissions.administrator:
            return True
        
        # Check for trusted role (must be named exactly "Trusted")
        if ctx.guild:
            trusted_role = discord.utils.get(ctx.guild.roles, name="Trusted")
            if trusted_role and trusted_role in ctx.author.roles:
                return True
        
        return False
    
    @company.command(name="setlimit", description="[ADMIN] Set the max company limit for this server")
    @discord.option("limit", description="Maximum companies per player (1-20)", type=int, min_value=1, max_value=20)
    async def set_company_limit(
        self,
        ctx: discord.ApplicationContext,
        limit: int
    ):
        if not await self._has_admin_perms(ctx):
            return await ctx.respond(
                "❌ You need Administrator permissions, bot owner status, guild owner status, or the `Trusted` role to use this command.",
                ephemeral=True
            )
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO guild_settings (guild_id, company_limit)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET company_limit = $2
                """,
                ctx.guild_id, limit
            )
        
        embed = RiskEmbed(title="⚙️ Company Limit Updated", color=NEON_GREEN)
        embed.description = (
            f"Company limit for this server set to **{limit}** companies per player.\n\n"
            f"All players can now own up to {limit} businesses."
        )
        
        await ctx.respond(embed=embed)
    
    @company.command(name="limit", description="View the current company limit for this server")
    async def view_company_limit(self, ctx: discord.ApplicationContext):
        limit = await self._get_company_limit(ctx.guild_id)
        
        embed = RiskEmbed(title="📊 Company Limit", color=NEON_CYAN)
        embed.description = (
            f"**Current Limit:** `{limit}` companies per player\n\n"
            f"Admins can adjust this with `/company setlimit`"
        )
        
        await ctx.respond(embed=embed, ephemeral=True)
    
    @company.command(name="list", description="Browse available businesses by tier")
    async def list_companies(
        self, 
        ctx: discord.ApplicationContext,
        tier: discord.Option(
            str, 
            "Filter by tier",
            choices=["All", "Starter", "Street", "Corporate", "Syndicate", "Megacorp", "Empire"],
            default="All"
        )
    ):
        embed = RiskEmbed(title="🏢 Available Businesses", color=NEON_CYAN)
        embed.description = f"`Build your criminal empire across Risk City`\n{LINE}\n"
        
        filtered_types = {
            k: v for k, v in COMPANY_TYPES.items()
            if tier == "All" or v['tier'] == tier
        }
        
        if not filtered_types:
            return await ctx.respond("No businesses in that tier.", ephemeral=True)
        
        for key, data in filtered_types.items():
            hourly = data['income_per_min'] * 60
            daily = hourly * 24
            
            embed.add_field(
                name=f"{data['name']} ({data['tier']})",
                value=(
                    f"{data['desc']}\n"
                    f"**Cost:** `{data['cost']:,} ₵`  ┆  **Risk:** `{int(data['risk']*100)}%`\n"
                    f"**Hourly:** `{hourly:,} ₵`  ┆  **Daily:** `{daily:,} ₵`\n"
                    f"`/company start {key}`"
                ),
                inline=False
            )
        
        await ctx.respond(embed=embed)
    
    @company.command(name="start", description="Start a new business")
    async def start_company(
        self,
        ctx: discord.ApplicationContext,
        company_type: discord.Option(
            str,
            "Business type to start",
            autocomplete=discord.utils.basic_autocomplete(lambda ctx: list(COMPANY_TYPES.keys()))
        ),
        name: discord.Option(str, "Custom name for your business", required=False)
    ):
        player = await get_player(ctx.author.id)
        if not player:
            return await ctx.respond("Register first with `/register`.", ephemeral=True)
        
        if company_type not in COMPANY_TYPES:
            return await ctx.respond("Invalid business type.", ephemeral=True)
        
        # Check company limit
        company_limit = await self._get_company_limit(ctx.guild_id)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            current_count = await conn.fetchval(
                "SELECT COUNT(*) FROM companies WHERE owner_id = $1",
                player['id']
            )
        
        if current_count >= company_limit:
            return await ctx.respond(
                embed=RiskEmbed(
                    title="🚫 Company Limit Reached",
                    description=(
                        f"You already own **{current_count}** businesses.\n"
                        f"**Server Limit:** `{company_limit}` companies per player\n\n"
                        f"Close a business with `/company close` to start a new one, "
                        f"or ask an admin to increase the limit with `/company setlimit`"
                    ),
                    color=NEON_RED
                ),
                ephemeral=True
            )
        
        data = COMPANY_TYPES[company_type]
        
        if player['credits'] < data['cost']:
            return await ctx.respond(
                f"You need `{data['cost']:,} ₵` to start this business. You have `{player['credits']:,.0f} ₵`.",
                ephemeral=True
            )
        
        business_name = name if name else data['name']
        
        await update_player_credits(player['id'], -data['cost'])
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            company = await conn.fetchrow(
                """
                INSERT INTO companies (owner_id, company_type, name, last_collect)
                VALUES ($1, $2, $3, NOW())
                RETURNING *
                """,
                player['id'], company_type, business_name
            )
        
        embed = RiskEmbed(title="✅ Business Established", color=NEON_GREEN)
        embed.description = f"**{business_name}**\n`{data['desc']}`\n{LINE}"
        
        hourly = data['income_per_min'] * 60
        daily = hourly * 24
        
        embed.add_field(name="💰 Setup Cost", value=f"`{data['cost']:,} ₵`", inline=True)
        embed.add_field(name="⚠️ Risk Level", value=f"`{int(data['risk']*100)}%`", inline=True)
        embed.add_field(name="🆔 Company ID", value=f"`{company['id']}`", inline=True)
        
        embed.add_field(
            name="📊 Income Projections",
            value=(
                f"**Per Hour:** `{hourly:,} ₵`\n"
                f"**Per Day:** `{daily:,} ₵`\n"
                f"**Per Week:** `{daily * 7:,} ₵`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📋 Next Steps",
            value=(
                f"• Collect earnings with `/company collect`\n"
                f"• Invest for passive income with `/company invest`\n"
                f"• View all businesses with `/company status`\n"
                f"• Current Portfolio: `{current_count + 1}/{company_limit}` companies"
            ),
            inline=False
        )
        
        await ctx.respond(embed=embed)
    
    @company.command(name="status", description="View all your businesses")
    async def company_status(self, ctx: discord.ApplicationContext):
        player = await get_player(ctx.author.id)
        if not player:
            return await ctx.respond("Register first with `/register`.", ephemeral=True)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            companies = await conn.fetch(
                "SELECT * FROM companies WHERE owner_id = $1 ORDER BY id",
                player['id']
            )
        
        if not companies:
            return await ctx.respond(
                "You don't own any businesses yet. Start one with `/company start`.",
                ephemeral=True
            )
        
        company_limit = await self._get_company_limit(ctx.guild_id)
        
        embed = RiskEmbed(title="🏢 Your Business Empire", color=NEON_CYAN)
        embed.description = (
            f"`Portfolio: {len(companies)}/{company_limit} companies`\n{LINE}\n"
        )
        
        total_value = 0
        total_hourly = 0
        
        for comp in companies:
            comp_data = COMPANY_TYPES[comp['company_type']]
            
            minutes_passed = (datetime.now() - comp['last_collect']).total_seconds() / 60
            active_earnings = int(minutes_passed * comp_data['income_per_min'])
            stockpiled_earnings = int(comp['stockpiled_minutes'] * comp_data['income_per_min'])
            total_pending = active_earnings + stockpiled_earnings
            
            hourly = comp_data['income_per_min'] * 60
            total_hourly += hourly
            total_value += comp_data['cost'] + comp['total_invested']
            
            status_emoji = "🟢" if total_pending > 0 else "🟡"
            
            embed.add_field(
                name=f"{status_emoji} {comp['name']} (ID: {comp['id']})",
                value=(
                    f"**Type:** `{comp_data['tier']}`  ┆  **Risk:** `{int(comp_data['risk']*100)}%`\n"
                    f"**Pending:** `{total_pending:,} ₵`  ┆  **Hourly:** `{hourly:,} ₵`\n"
                    f"**Lifetime Earned:** `{comp['total_earned']:,.0f} ₵`"
                ),
                inline=False
            )
        
        embed.add_field(
            name="💼 Portfolio Summary",
            value=(
                f"**Total Value:** `{total_value:,} ₵`\n"
                f"**Combined Hourly:** `{total_hourly:,} ₵`\n"
                f"**Daily Projection:** `{total_hourly * 24:,} ₵`"
            ),
            inline=False
        )
        
        await ctx.respond(embed=embed)
    
    @company.command(name="collect", description="Collect earnings from all businesses")
    async def collect_earnings(self, ctx: discord.ApplicationContext):
        player = await get_player(ctx.author.id)
        if not player:
            return await ctx.respond("Register first with `/register`.", ephemeral=True)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            companies = await conn.fetch(
                "SELECT * FROM companies WHERE owner_id = $1",
                player['id']
            )
        
        if not companies:
            return await ctx.respond(
                "You don't own any businesses yet.",
                ephemeral=True
            )
        
        total_earned = 0
        results = []
        
        for comp in companies:
            comp_data = COMPANY_TYPES[comp['company_type']]
            
            minutes_passed = (datetime.now() - comp['last_collect']).total_seconds() / 60
            active_earnings = int(minutes_passed * comp_data['income_per_min'])
            stockpiled_earnings = int(comp['stockpiled_minutes'] * comp_data['income_per_min'])
            total_collect = active_earnings + stockpiled_earnings
            
            if total_collect <= 0:
                continue
            
            if random.random() < comp_data['risk']:
                event_type = random.choice(['raid', 'bust', 'crash', 'sabotage'])
                events = {
                    'raid': f"🚨 Raided by corpo security",
                    'bust': f"👮 Busted by law enforcement",
                    'crash': f"📉 Market crash hit hard",
                    'sabotage': f"💣 Sabotaged by competitors"
                }
                results.append({
                    'name': comp['name'],
                    'profit': 0,
                    'event': events[event_type]
                })
                total_collect = 0
            else:
                total_earned += total_collect
                results.append({
                    'name': comp['name'],
                    'profit': total_collect,
                    'event': None
                })
            
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE companies SET last_collect = NOW(), stockpiled_minutes = 0, total_earned = total_earned + $1 WHERE id = $2",
                    total_collect, comp['id']
                )
        
        if total_earned == 0 and not results:
            return await ctx.respond("Nothing to collect yet. Come back later!", ephemeral=True)
        
        await update_player_credits(player['id'], total_earned)
        
        embed = RiskEmbed(
            title="💰 COLLECTION COMPLETE",
            color=NEON_GREEN if total_earned > 0 else NEON_YELLOW
        )
        embed.description = f"`Collected from {len(results)} businesses`\n{LINE}\n"
        
        for result in results:
            profit_str = f"`+{result['profit']:,} ₵`" if result['profit'] > 0 else "`0 ₵`"
            value = f"**Earned:** {profit_str}"
            if result['event']:
                value += f"\n{result['event']}"
            embed.add_field(name=result['name'], value=value, inline=True)
        
        embed.add_field(
            name="🔹 Total Collected",
            value=f"**+{total_earned:,} ₵** added to your balance",
            inline=False
        )
        
        await ctx.respond(embed=embed)
    
    @company.command(name="invest", description="Stockpile hours of earnings")
    async def invest_in_company(
        self,
        ctx: discord.ApplicationContext,
        company_id: discord.Option(int, "Company ID from /company status"),
        amount: discord.Option(int, "Amount to invest (buys earning hours)")
    ):
        player = await get_player(ctx.author.id)
        if not player:
            return await ctx.respond("Register first with `/register`.", ephemeral=True)
        
        if amount < 100:
            return await ctx.respond("Minimum investment is 100 ₵.", ephemeral=True)
        
        if player['credits'] < amount:
            return await ctx.respond(
                f"You only have `{player['credits']:,.0f} ₵`.",
                ephemeral=True
            )
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            company = await conn.fetchrow(
                "SELECT * FROM companies WHERE id = $1 AND owner_id = $2",
                company_id, player['id']
            )
        
        if not company:
            return await ctx.respond("You don't own that company.", ephemeral=True)
        
        comp_data = COMPANY_TYPES[company['company_type']]
        
        hourly_rate = comp_data['income_per_min'] * 60
        hours_bought = amount / hourly_rate
        minutes_bought = hours_bought * 60
        
        await update_player_credits(player['id'], -amount)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE companies SET stockpiled_minutes = stockpiled_minutes + $1, total_invested = total_invested + $2 WHERE id = $3",
                minutes_bought, amount, company_id
            )
        
        embed = RiskEmbed(title="📈 Investment Processed", color=NEON_GREEN)
        embed.description = (
            f"Invested `{amount:,} ₵` into **{company['name']}**.\n{LINE}\n"
            f"**Stockpiled:** `{hours_bought:.2f} hours` of future earnings\n"
            f"**Value:** `{int(hours_bought * hourly_rate):,} ₵`\n\n"
            f"This will be available immediately on your next `/company collect`."
        )
        
        await ctx.respond(embed=embed)
    
    @company.command(name="close", description="Shut down a business")
    async def close_company(
        self,
        ctx: discord.ApplicationContext,
        company_id: discord.Option(int, "Company ID from /company status")
    ):
        player = await get_player(ctx.author.id)
        if not player:
            return await ctx.respond("Register first with `/register`.", ephemeral=True)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            company = await conn.fetchrow(
                "SELECT * FROM companies WHERE id = $1 AND owner_id = $2",
                company_id, player['id']
            )
        
        if not company:
            return await ctx.respond("You don't own that company.", ephemeral=True)
        
        comp_data = COMPANY_TYPES[company['company_type']]
        
        minutes_passed = (datetime.now() - company['last_collect']).total_seconds() / 60
        uncollected = int(minutes_passed * comp_data['income_per_min'])
        stockpiled = int(company['stockpiled_minutes'] * comp_data['income_per_min'])
        final_payout = uncollected + stockpiled
        
        total_investment = comp_data['cost'] + company['total_invested']
        salvage_value = int(total_investment * 0.6)
        total_return = salvage_value + final_payout
        
        await update_player_credits(player['id'], total_return)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM companies WHERE id = $1", company_id)
        
        embed = RiskEmbed(title="🗑️ Business Closed", color=NEON_YELLOW)
        embed.description = f"Shut down **{company['name']}**.\n{LINE}"
        embed.add_field(name="Salvage Value", value=f"`{salvage_value:,} ₵` (60% of investment)", inline=True)
        embed.add_field(name="Final Payout", value=f"`{final_payout:,} ₵`", inline=True)
        embed.add_field(name="Total Return", value=f"`{total_return:,} ₵`", inline=True)
        embed.add_field(
            name="Lifetime Stats",
            value=f"**Total Earned:** `{company['total_earned']:,.0f} ₵`",
            inline=False
        )
        
        await ctx.respond(embed=embed)
    
    @company.command(name="info", description="Detailed info on a specific business type")
    async def company_info(
        self,
        ctx: discord.ApplicationContext,
        company_type: discord.Option(
            str,
            "Business type to view",
            autocomplete=discord.utils.basic_autocomplete(lambda ctx: list(COMPANY_TYPES.keys()))
        )
    ):
        if company_type not in COMPANY_TYPES:
            return await ctx.respond("Invalid business type.", ephemeral=True)
        
        data = COMPANY_TYPES[company_type]
        
        hourly = data['income_per_min'] * 60
        daily = hourly * 24
        weekly = daily * 7
        monthly = daily * 30
        
        embed = RiskEmbed(title=data['name'], color=TIER_COLORS[data['tier']])
        embed.description = f"**{data['tier']} Tier**\n\n{data['desc']}\n{LINE}"
        
        embed.add_field(
            name="💰 Setup Cost",
            value=f"`{data['cost']:,} ₵`",
            inline=True
        )
        embed.add_field(
            name="⚠️ Risk Level",
            value=f"`{int(data['risk']*100)}%`",
            inline=True
        )
        embed.add_field(
            name="⚡ Per Minute",
            value=f"`{data['income_per_min']:,} ₵`",
            inline=True
        )
        
        embed.add_field(
            name="📊 Income Breakdown",
            value=(
                f"**Hourly:** `{hourly:,} ₵`\n"
                f"**Daily:** `{daily:,} ₵`\n"
                f"**Weekly:** `{weekly:,} ₵`\n"
                f"**Monthly:** `{monthly:,} ₵`"
            ),
            inline=False
        )
        
        roi_days = data['cost'] / daily
        embed.add_field(
            name="💹 Return on Investment",
            value=f"Pays for itself in **`{roi_days:.1f} days`** of active earnings",
            inline=False
        )
        
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Companies(bot))