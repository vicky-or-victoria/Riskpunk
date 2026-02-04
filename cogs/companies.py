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


class Companies(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    company = SlashCommandGroup("company", "Manage your business empire")
    
    @company.command(name="list", description="Browse available businesses by tier")
    async def list_companies(
        self, 
        ctx: discord.ApplicationContext,
        tier: discord.Option(
            str, 
            "Filter by tier", 
            choices=["All", "Starter", "Street", "Corporate", "Syndicate", "Megacorp", "Empire"],
            required=False,
            default="All"
        )
    ):
        player = await get_player(ctx.author.id)
        if not player:
            return await ctx.respond("Register first with `/register`.", ephemeral=True)
        
        embed = RiskEmbed(title="BUSINESS OPPORTUNITIES", color=NEON_CYAN)
        embed.description = f"Businesses generate profit every minute. Invest to stockpile hours of earnings.\n{LINE}"
        
        for key, data in COMPANY_TYPES.items():
            if tier != "All" and data["tier"] != tier:
                continue
            
            hourly_rate = data["income_per_min"] * 60
            daily_rate = hourly_rate * 24
            
            field_value = (
                f"{data['desc']}\n\n"
                f"**Setup:** `{data['cost']:,} ₵`\n"
                f"**Income:** `{data['income_per_min']:,} ₵/min` (`{hourly_rate:,} ₵/hr`)\n"
                f"**Daily Potential:** `{daily_rate:,} ₵`\n"
                f"**Risk:** {'🔴' * int(data['risk'] * 20)}"
            )
            embed.add_field(
                name=f"{data['tier']} | {data['name']}", 
                value=field_value, 
                inline=False
            )
        
        if tier == "All":
            embed.add_field(
                name="Investment System",
                value=(
                    "Use `/company invest` to stockpile earnings hours.\n"
                    "Example: Invest 5000 ₵ = buy hours based on hourly income.\n"
                    "Collect anytime with `/company collect`."
                ),
                inline=False
            )
        
        await ctx.respond(embed=embed)
    
    @company.command(name="start", description="Launch a new business")
    async def start_company(
        self, 
        ctx: discord.ApplicationContext,
        company_type: discord.Option(
            str, 
            "Type of business",
            autocomplete=discord.utils.basic_autocomplete(lambda ctx: list(COMPANY_TYPES.keys()))
        )
    ):
        player = await get_player(ctx.author.id)
        if not player:
            return await ctx.respond("Register first with `/register`.", ephemeral=True)
        
        if company_type not in COMPANY_TYPES:
            return await ctx.respond("Invalid business type.", ephemeral=True)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT * FROM companies WHERE owner_id = $1 AND company_type = $2",
                player['id'], company_type
            )
            
            if existing:
                return await ctx.respond(
                    f"You already own a {COMPANY_TYPES[company_type]['name']}.",
                    ephemeral=True
                )
            
            total_companies = await conn.fetchval(
                "SELECT COUNT(*) FROM companies WHERE owner_id = $1",
                player['id']
            )
            
            if total_companies >= 5:
                return await ctx.respond(
                    "Max 5 companies per player. Close one with `/company close`.",
                    ephemeral=True
                )
        
        company_data = COMPANY_TYPES[company_type]
        
        if player['credits'] < company_data['cost']:
            embed = RiskEmbed(title="Insufficient Funds", color=NEON_RED)
            embed.description = (
                f"Starting a {company_data['name']} costs `{company_data['cost']:,} ₵`.\n"
                f"You only have `{player['credits']:,.0f} ₵`."
            )
            return await ctx.respond(embed=embed, ephemeral=True)
        
        await update_player_credits(player['id'], -company_data['cost'])
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            company = await conn.fetchrow("""
                INSERT INTO companies (owner_id, company_type, name, last_collect, stockpiled_minutes)
                VALUES ($1, $2, $3, NOW(), 0)
                RETURNING *
            """, player['id'], company_type, company_data['name'])
        
        hourly = company_data['income_per_min'] * 60
        
        embed = RiskEmbed(title="Business Established", color=TIER_COLORS[company_data['tier']])
        embed.description = (
            f"**{company_data['name']}** is now operational.\n\n"
            f"{company_data['desc']}\n{THIN_LINE}"
        )
        embed.add_field(
            name="Income",
            value=f"`{company_data['income_per_min']:,} ₵/min` | `{hourly:,} ₵/hr`",
            inline=True
        )
        embed.add_field(
            name="Tier",
            value=f"`{company_data['tier']}`",
            inline=True
        )
        embed.add_field(
            name="Risk Level",
            value=f"`{int(company_data['risk']*100)}%`",
            inline=True
        )
        embed.add_field(
            name="Next Steps",
            value=(
                "• Wait for profits to accumulate\n"
                "• Use `/company invest` to stockpile hours\n"
                "• Use `/company collect` to claim earnings"
            ),
            inline=False
        )
        
        await ctx.respond(embed=embed)
    
    @company.command(name="status", description="View your businesses")
    async def company_status(self, ctx: discord.ApplicationContext):
        player = await get_player(ctx.author.id)
        if not player:
            return await ctx.respond("Register first with `/register`.", ephemeral=True)
        
        pool = await get_pool()
        async with pool.acquire() as conn:
            companies = await conn.fetch(
                "SELECT * FROM companies WHERE owner_id = $1 ORDER BY created_at",
                player['id']
            )
        
        if not companies:
            embed = RiskEmbed(title="No Businesses", color=NEON_YELLOW)
            embed.description = "You don't own any companies. Check `/company list` to start one."
            return await ctx.respond(embed=embed)
        
        embed = RiskEmbed(title="YOUR BUSINESS EMPIRE", color=NEON_CYAN)
        embed.description = f"Operating {len(companies)}/5 businesses.\n{LINE}"
        
        total_value = 0
        total_hourly = 0
        
        for comp in companies:
            comp_data = COMPANY_TYPES[comp['company_type']]
            
            minutes_passed = (datetime.now() - comp['last_collect']).total_seconds() / 60
            accumulated = int(minutes_passed * comp_data['income_per_min'])
            stockpiled = int(comp['stockpiled_minutes'] * comp_data['income_per_min'])
            total_ready = accumulated + stockpiled
            
            hourly = comp_data['income_per_min'] * 60
            total_value += comp_data['cost'] + comp['total_invested']
            total_hourly += hourly
            
            stockpile_hours = comp['stockpiled_minutes'] / 60
            
            field_value = (
                f"**Ready:** `{total_ready:,} ₵` ({int(minutes_passed)}m active + {stockpile_hours:.1f}h stocked)\n"
                f"**Rate:** `{comp_data['income_per_min']:,} ₵/min` | `{hourly:,} ₵/hr`\n"
                f"**Lifetime:** `{comp['total_earned']:,.0f} ₵`\n"
                f"**ID:** `{comp['id']}`"
            )
            
            embed.add_field(
                name=f"{comp_data['tier']} | {comp['name']}",
                value=field_value,
                inline=False
            )
        
        embed.add_field(
            name="Empire Stats",
            value=(
                f"**Total Invested:** `{total_value:,} ₵`\n"
                f"**Combined Income:** `{total_hourly:,} ₵/hr`\n"
                f"**Daily Potential:** `{total_hourly * 24:,} ₵`"
            ),
            inline=False
        )
        
        await ctx.respond(embed=embed)
    
    @company.command(name="collect", description="Collect accumulated profits")
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
            return await ctx.respond("You don't own any companies.", ephemeral=True)
        
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
                    'raid': f"🚨 Raided",
                    'bust': f"👮 Busted",
                    'crash': f"📉 Crashed",
                    'sabotage': f"💣 Sabotaged"
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
            return await ctx.respond("Nothing to collect yet.", ephemeral=True)
        
        await update_player_credits(player['id'], total_earned)
        
        embed = RiskEmbed(
            title="COLLECTION COMPLETE",
            color=NEON_GREEN if total_earned > 0 else NEON_YELLOW
        )
        embed.description = f"Collected from {len(results)} businesses.\n{LINE}"
        
        for result in results:
            profit_str = f"`+{result['profit']:,} ₵`" if result['profit'] > 0 else "`0 ₵`"
            value = f"**Earned:** {profit_str}"
            if result['event']:
                value += f"\n{result['event']}"
            embed.add_field(name=result['name'], value=value, inline=True)
        
        embed.add_field(
            name="Total Collected",
            value=f"**+{total_earned:,} ₵**",
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
        
        embed = RiskEmbed(title="Investment Processed", color=NEON_GREEN)
        embed.description = (
            f"Invested `{amount:,} ₵` into **{company['name']}**.\n\n"
            f"**Stockpiled:** `{hours_bought:.2f} hours` of earnings\n"
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
        
        embed = RiskEmbed(title="Business Closed", color=NEON_YELLOW)
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
            name="Setup Cost",
            value=f"`{data['cost']:,} ₵`",
            inline=True
        )
        embed.add_field(
            name="Risk Level",
            value=f"`{int(data['risk']*100)}%`",
            inline=True
        )
        embed.add_field(
            name="Per Minute",
            value=f"`{data['income_per_min']:,} ₵`",
            inline=True
        )
        
        embed.add_field(
            name="Income Breakdown",
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
            name="Return on Investment",
            value=f"Pays for itself in `{roi_days:.1f} days` of active earnings",
            inline=False
        )
        
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Companies(bot))
