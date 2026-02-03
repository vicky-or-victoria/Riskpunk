import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime, timedelta
import random
import asyncio

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Data storage
DATA_FILE = 'neon_city_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        'citizens': {},
        'corporations': {
            'zenith_dynamics': {'influence': 1000, 'credits': 500000, 'reputation': 75},
            'chrome_industries': {'influence': 800, 'credits': 450000, 'reputation': 60},
            'neon_biotech': {'influence': 900, 'credits': 480000, 'reputation': 70},
            'shadow_syndicate': {'influence': 600, 'credits': 300000, 'reputation': 40}
        },
        'market': {
            'data_chips': {'price': 150, 'supply': 1000},
            'chrome_implants': {'price': 3500, 'supply': 200},
            'synth_drugs': {'price': 80, 'supply': 500},
            'weapon_permits': {'price': 1200, 'supply': 150}
        },
        'political_climate': {
            'stability': 65,
            'corporate_control': 80,
            'underground_power': 35,
            'public_unrest': 45
        }
    }

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

data = load_data()

# Color scheme
COLORS = {
    'neon_cyan': 0x00FFFF,
    'neon_pink': 0xFF10F0,
    'neon_green': 0x39FF14,
    'dark_bg': 0x0A0E27,
    'warning': 0xFF6B35,
    'success': 0x4ECDC4
}

# Citizen class and ranks
CITIZEN_RANKS = {
    'street_rat': {'min_credits': 0, 'max_credits': 1000},
    'wage_slave': {'min_credits': 1000, 'max_credits': 5000},
    'corpo_drone': {'min_credits': 5000, 'max_credits': 20000},
    'exec_tier': {'min_credits': 20000, 'max_credits': 100000},
    'elite_class': {'min_credits': 100000, 'max_credits': float('inf')}
}

def get_citizen_rank(credits):
    for rank, bounds in CITIZEN_RANKS.items():
        if bounds['min_credits'] <= credits < bounds['max_credits']:
            return rank.replace('_', ' ').title()
    return 'Elite Class'

def create_citizen(user_id, username):
    return {
        'user_id': user_id,
        'username': username,
        'credits': 500,
        'reputation': 0,
        'faction': None,
        'implants': [],
        'inventory': {},
        'last_work': None,
        'join_date': str(datetime.now()),
        'crimes_committed': 0,
        'deals_completed': 0
    }

@bot.event
async def on_ready():
    print(f'⚡ {bot.user} connected to the Neural Net')
    print(f'⚡ Neon City is ONLINE')
    try:
        synced = await bot.tree.sync()
        print(f'⚡ Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'❌ Error syncing commands: {e}')
    
    market_fluctuation.start()

@tasks.loop(minutes=30)
async def market_fluctuation():
    """Market prices fluctuate based on supply and demand"""
    global data
    for item, details in data['market'].items():
        change = random.uniform(-0.15, 0.15)
        data['market'][item]['price'] = int(details['price'] * (1 + change))
        data['market'][item]['price'] = max(10, data['market'][item]['price'])
    save_data(data)

@bot.tree.command(name='jack_in', description='⚡ Connect to Neon City\'s network')
async def jack_in(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    if user_id in data['citizens']:
        citizen = data['citizens'][user_id]
        
        embed = discord.Embed(
            title='🌃 NEURAL LINK ESTABLISHED',
            description=f'```ansi\n\x1b[36m>> WELCOME BACK, {interaction.user.name.upper()}\n>> IDENTITY VERIFIED\n>> ACCESS GRANTED\x1b[0m\n```',
            color=COLORS['neon_cyan']
        )
        embed.add_field(
            name='💳 CREDIT BALANCE',
            value=f'```css\n¥{citizen["credits"]:,}\n```',
            inline=True
        )
        embed.add_field(
            name='⚡ REPUTATION',
            value=f'```diff\n{"+" if citizen["reputation"] >= 0 else "-"}{abs(citizen["reputation"])}\n```',
            inline=True
        )
        embed.add_field(
            name='🎭 STATUS',
            value=f'```yaml\n{get_citizen_rank(citizen["credits"])}\n```',
            inline=True
        )
        embed.add_field(
            name='🏢 FACTION ALLEGIANCE',
            value=f'```\n{citizen["faction"] or "Independent"}\n```',
            inline=False
        )
        embed.set_footer(text='Use /commands to see available actions')
        
    else:
        data['citizens'][user_id] = create_citizen(user_id, interaction.user.name)
        save_data(data)
        
        embed = discord.Embed(
            title='🌆 NEURAL IMPLANT ACTIVATED',
            description=f'```ansi\n\x1b[35m>> NEW CITIZEN DETECTED\n>> INITIALIZING PROFILE: {interaction.user.name.upper()}\n>> CORPORATE ID ASSIGNED\n>> WELCOME TO NEON CITY\x1b[0m\n```',
            color=COLORS['neon_pink']
        )
        embed.add_field(
            name='💳 STARTING CREDITS',
            value='```css\n¥500\n```',
            inline=True
        )
        embed.add_field(
            name='🎭 CITIZEN CLASS',
            value='```yaml\nStreet Rat\n```',
            inline=True
        )
        embed.add_field(
            name='📡 SURVIVAL TIPS',
            value='```md\n# Get Started:\n- /work to earn credits\n- /market to trade goods\n- /faction to join a corp\n- /crime for risky rewards\n```',
            inline=False
        )
        
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='profile', description='📊 View your citizen profile')
async def profile(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    if user_id not in data['citizens']:
        await interaction.response.send_message('⚠️ Neural link not established. Use `/jack_in` first.', ephemeral=True)
        return
    
    citizen = data['citizens'][user_id]
    rank = get_citizen_rank(citizen['credits'])
    
    embed = discord.Embed(
        title=f'👤 CITIZEN FILE: {interaction.user.name.upper()}',
        color=COLORS['neon_cyan']
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    
    embed.add_field(
        name='💰 FINANCIAL STATUS',
        value=f'```yaml\nCredits: ¥{citizen["credits"]:,}\nClass: {rank}\n```',
        inline=True
    )
    embed.add_field(
        name='⚡ INFLUENCE',
        value=f'```diff\n{"+" if citizen["reputation"] >= 0 else ""}{citizen["reputation"]} REP\n```',
        inline=True
    )
    embed.add_field(
        name='🏢 AFFILIATION',
        value=f'```\n{citizen["faction"] or "None"}\n```',
        inline=True
    )
    
    embed.add_field(
        name='📊 STATISTICS',
        value=f'```css\nDeals: {citizen["deals_completed"]}\nCrimes: {citizen["crimes_committed"]}\nImplants: {len(citizen["implants"])}\n```',
        inline=False
    )
    
    if citizen['inventory']:
        inventory_text = '\n'.join([f'{item}: {qty}' for item, qty in citizen['inventory'].items()])
        embed.add_field(
            name='🎒 INVENTORY',
            value=f'```\n{inventory_text}\n```',
            inline=False
        )
    
    embed.set_footer(text=f'Citizen since {citizen["join_date"][:10]}')
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='work', description='💼 Work for credits (30min cooldown)')
async def work(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    if user_id not in data['citizens']:
        await interaction.response.send_message('⚠️ Neural link not established. Use `/jack_in` first.', ephemeral=True)
        return
    
    citizen = data['citizens'][user_id]
    now = datetime.now()
    
    if citizen['last_work']:
        last_work_time = datetime.fromisoformat(citizen['last_work'])
        cooldown = timedelta(minutes=30)
        if now - last_work_time < cooldown:
            remaining = cooldown - (now - last_work_time)
            minutes = int(remaining.total_seconds() // 60)
            await interaction.response.send_message(
                f'⏰ Neural fatigue detected. Cooldown: {minutes} minutes remaining.',
                ephemeral=True
            )
            return
    
    jobs = [
        {'name': 'Data Mining', 'pay': (50, 150), 'rep': 1},
        {'name': 'Corporate Courier', 'pay': (100, 250), 'rep': 2},
        {'name': 'Black Market Deal', 'pay': (200, 400), 'rep': -1},
        {'name': 'Security Gig', 'pay': (150, 300), 'rep': 3},
        {'name': 'Netrunning Job', 'pay': (300, 500), 'rep': 4}
    ]
    
    job = random.choice(jobs)
    earnings = random.randint(job['pay'][0], job['pay'][1])
    
    citizen['credits'] += earnings
    citizen['reputation'] += job['rep']
    citizen['last_work'] = str(now)
    citizen['deals_completed'] += 1
    save_data(data)
    
    embed = discord.Embed(
        title='💼 JOB COMPLETE',
        description=f'```ansi\n\x1b[32m>> {job["name"].upper()} SUCCESSFUL\x1b[0m\n```',
        color=COLORS['success']
    )
    embed.add_field(name='💰 EARNED', value=f'```diff\n+ ¥{earnings:,}\n```', inline=True)
    embed.add_field(name='⚡ REP CHANGE', value=f'```diff\n{"+" if job["rep"] >= 0 else ""}{job["rep"]}\n```', inline=True)
    embed.add_field(name='💳 NEW BALANCE', value=f'```css\n¥{citizen["credits"]:,}\n```', inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='market', description='🛒 View and trade on the black market')
async def market(interaction: discord.Interaction):
    embed = discord.Embed(
        title='🌃 NEON CITY BLACK MARKET',
        description='```ansi\n\x1b[36m>> ENCRYPTED CONNECTION ESTABLISHED\n>> CONTRABAND AVAILABLE\x1b[0m\n```',
        color=COLORS['neon_pink']
    )
    
    market_display = []
    for item, details in data['market'].items():
        item_name = item.replace('_', ' ').title()
        market_display.append(f'{item_name}\n  Price: ¥{details["price"]:,}\n  Stock: {details["supply"]} units')
    
    embed.add_field(
        name='📦 AVAILABLE GOODS',
        value=f'```yaml\n{chr(10).join(market_display)}\n```',
        inline=False
    )
    embed.add_field(
        name='💡 HOW TO TRADE',
        value='```\nUse /buy <item> <quantity>\nUse /sell <item> <quantity>\n```',
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='buy', description='💳 Purchase items from the market')
@app_commands.describe(item='Item to purchase', quantity='Amount to buy')
async def buy(interaction: discord.Interaction, item: str, quantity: int):
    user_id = str(interaction.user.id)
    
    if user_id not in data['citizens']:
        await interaction.response.send_message('⚠️ Neural link not established. Use `/jack_in` first.', ephemeral=True)
        return
    
    item_key = item.lower().replace(' ', '_')
    
    if item_key not in data['market']:
        await interaction.response.send_message(f'❌ Item `{item}` not found in market.', ephemeral=True)
        return
    
    if quantity <= 0:
        await interaction.response.send_message('❌ Quantity must be positive.', ephemeral=True)
        return
    
    citizen = data['citizens'][user_id]
    market_item = data['market'][item_key]
    total_cost = market_item['price'] * quantity
    
    if citizen['credits'] < total_cost:
        await interaction.response.send_message(
            f'💸 Insufficient credits. Need ¥{total_cost:,}, have ¥{citizen["credits"]:,}',
            ephemeral=True
        )
        return
    
    if market_item['supply'] < quantity:
        await interaction.response.send_message(
            f'📦 Insufficient stock. Only {market_item["supply"]} available.',
            ephemeral=True
        )
        return
    
    citizen['credits'] -= total_cost
    citizen['inventory'][item_key] = citizen['inventory'].get(item_key, 0) + quantity
    data['market'][item_key]['supply'] -= quantity
    save_data(data)
    
    embed = discord.Embed(
        title='✅ TRANSACTION COMPLETE',
        description=f'```ansi\n\x1b[32m>> PURCHASE VERIFIED\x1b[0m\n```',
        color=COLORS['success']
    )
    embed.add_field(name='📦 ITEM', value=f'```{item.title()}```', inline=True)
    embed.add_field(name='🔢 QUANTITY', value=f'```{quantity}```', inline=True)
    embed.add_field(name='💰 TOTAL', value=f'```¥{total_cost:,}```', inline=True)
    embed.add_field(name='💳 REMAINING', value=f'```css\n¥{citizen["credits"]:,}\n```', inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='crime', description='🔫 Commit a crime for high-risk rewards')
async def crime(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    if user_id not in data['citizens']:
        await interaction.response.send_message('⚠️ Neural link not established. Use `/jack_in` first.', ephemeral=True)
        return
    
    citizen = data['citizens'][user_id]
    
    crimes = [
        {'name': 'Data Heist', 'reward': (500, 1500), 'risk': 0.4, 'rep': -5},
        {'name': 'Corporate Sabotage', 'reward': (1000, 3000), 'risk': 0.6, 'rep': -10},
        {'name': 'Blackmail Scheme', 'reward': (300, 800), 'risk': 0.3, 'rep': -3},
        {'name': 'Cyberware Smuggling', 'reward': (2000, 5000), 'risk': 0.7, 'rep': -15}
    ]
    
    crime = random.choice(crimes)
    success = random.random() > crime['risk']
    
    if success:
        reward = random.randint(crime['reward'][0], crime['reward'][1])
        citizen['credits'] += reward
        citizen['reputation'] += crime['rep']
        citizen['crimes_committed'] += 1
        save_data(data)
        
        embed = discord.Embed(
            title='🔥 CRIME SUCCESSFUL',
            description=f'```ansi\n\x1b[31m>> {crime["name"].upper()}\n>> AUTHORITIES EVADED\x1b[0m\n```',
            color=COLORS['warning']
        )
        embed.add_field(name='💰 STOLEN', value=f'```diff\n+ ¥{reward:,}\n```', inline=True)
        embed.add_field(name='⚡ REP HIT', value=f'```diff\n{crime["rep"]}\n```', inline=True)
        embed.add_field(name='💳 BALANCE', value=f'```css\n¥{citizen["credits"]:,}\n```', inline=True)
    else:
        fine = random.randint(200, 1000)
        citizen['credits'] = max(0, citizen['credits'] - fine)
        citizen['reputation'] -= 10
        save_data(data)
        
        embed = discord.Embed(
            title='🚨 CRIME FAILED',
            description=f'```ansi\n\x1b[31m>> {crime["name"].upper()}\n>> AUTHORITIES ALERTED\n>> CAPTURED\x1b[0m\n```',
            color=COLORS['warning']
        )
        embed.add_field(name='💸 FINE', value=f'```diff\n- ¥{fine:,}\n```', inline=True)
        embed.add_field(name='⚡ REP LOSS', value=f'```diff\n-10\n```', inline=True)
        embed.add_field(name='💳 BALANCE', value=f'```css\n¥{citizen["credits"]:,}\n```', inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='faction', description='🏢 Join or view faction information')
async def faction(interaction: discord.Interaction):
    embed = discord.Embed(
        title='🏢 NEON CITY POWER FACTIONS',
        description='```ansi\n\x1b[36m>> CORPORATE DIRECTORY ACCESS\x1b[0m\n```',
        color=COLORS['neon_cyan']
    )
    
    faction_info = {
        'zenith_dynamics': '⚡ High-tech weapons manufacturing\n💰 High pay, strict loyalty',
        'chrome_industries': '🔧 Cybernetic augmentation leader\n🦾 Implant discounts for members',
        'neon_biotech': '🧬 Genetic engineering corporation\n🧪 Access to experimental drugs',
        'shadow_syndicate': '🌑 Underground criminal network\n💀 High risk, high reward operations'
    }
    
    for corp, details in data['corporations'].items():
        corp_name = corp.replace('_', ' ').title()
        embed.add_field(
            name=f'🏛️ {corp_name}',
            value=f'```yaml\nInfluence: {details["influence"]}\nReputation: {details["reputation"]}\n```\n{faction_info[corp]}',
            inline=False
        )
    
    embed.add_field(
        name='📝 JOIN A FACTION',
        value='```\nUse /join_faction <faction_name>\n```',
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='join_faction', description='🤝 Pledge allegiance to a faction')
@app_commands.describe(faction='Name of the faction to join')
async def join_faction(interaction: discord.Interaction, faction: str):
    user_id = str(interaction.user.id)
    
    if user_id not in data['citizens']:
        await interaction.response.send_message('⚠️ Neural link not established. Use `/jack_in` first.', ephemeral=True)
        return
    
    faction_key = faction.lower().replace(' ', '_')
    
    if faction_key not in data['corporations']:
        await interaction.response.send_message(f'❌ Faction `{faction}` not found.', ephemeral=True)
        return
    
    citizen = data['citizens'][user_id]
    
    if citizen['faction']:
        await interaction.response.send_message(
            f'⚠️ Already affiliated with {citizen["faction"]}. Leave first with `/leave_faction`.',
            ephemeral=True
        )
        return
    
    citizen['faction'] = faction_key.replace('_', ' ').title()
    citizen['reputation'] += 10
    save_data(data)
    
    embed = discord.Embed(
        title='🤝 FACTION ALLEGIANCE CONFIRMED',
        description=f'```ansi\n\x1b[35m>> LOYALTY OATH ACCEPTED\n>> WELCOME TO {faction.upper()}\x1b[0m\n```',
        color=COLORS['neon_pink']
    )
    embed.add_field(name='🏢 NEW FACTION', value=f'```{citizen["faction"]}```', inline=True)
    embed.add_field(name='⚡ REP BONUS', value=f'```diff\n+10\n```', inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='city_status', description='🌆 View Neon City\'s current state')
async def city_status(interaction: discord.Interaction):
    climate = data['political_climate']
    
    embed = discord.Embed(
        title='🌃 NEON CITY STATUS REPORT',
        description='```ansi\n\x1b[36m>> LIVE FEED FROM CITY MAINFRAME\x1b[0m\n```',
        color=COLORS['dark_bg']
    )
    
    embed.add_field(
        name='🏛️ POLITICAL CLIMATE',
        value=f'```yaml\nStability: {climate["stability"]}%\nCorp Control: {climate["corporate_control"]}%\nUnderground: {climate["underground_power"]}%\nUnrest: {climate["public_unrest"]}%\n```',
        inline=False
    )
    
    embed.add_field(
        name='🏢 CORPORATE POWER',
        value=f'```css\nActive Factions: {len(data["corporations"])}\nTotal Influence: {sum(c["influence"] for c in data["corporations"].values())}\n```',
        inline=True
    )
    
    embed.add_field(
        name='👥 CITIZEN COUNT',
        value=f'```diff\n+ {len(data["citizens"])} Connected\n```',
        inline=True
    )
    
    embed.set_footer(text='Data refreshes every 30 minutes')
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='commands', description='📋 List all available commands')
async def commands_list(interaction: discord.Interaction):
    embed = discord.Embed(
        title='⚡ NEON CITY COMMAND DATABASE',
        description='```ansi\n\x1b[36m>> SYSTEM COMMANDS AVAILABLE\x1b[0m\n```',
        color=COLORS['neon_green']
    )
    
    embed.add_field(
        name='🔌 CORE SYSTEMS',
        value='```\n/jack_in - Initialize neural link\n/profile - View citizen data\n/city_status - View city state\n```',
        inline=False
    )
    
    embed.add_field(
        name='💼 ECONOMY',
        value='```\n/work - Earn credits (30min CD)\n/market - View black market\n/buy - Purchase items\n/sell - Sell items\n```',
        inline=False
    )
    
    embed.add_field(
        name='🏢 FACTIONS',
        value='```\n/faction - View all factions\n/join_faction - Join a faction\n/leave_faction - Leave faction\n```',
        inline=False
    )
    
    embed.add_field(
        name='🔫 UNDERGROUND',
        value='```\n/crime - Risky criminal activities\n```',
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='sell', description='💰 Sell items from your inventory')
@app_commands.describe(item='Item to sell', quantity='Amount to sell')
async def sell(interaction: discord.Interaction, item: str, quantity: int):
    user_id = str(interaction.user.id)
    
    if user_id not in data['citizens']:
        await interaction.response.send_message('⚠️ Neural link not established. Use `/jack_in` first.', ephemeral=True)
        return
    
    citizen = data['citizens'][user_id]
    item_key = item.lower().replace(' ', '_')
    
    if item_key not in citizen['inventory'] or citizen['inventory'][item_key] < quantity:
        await interaction.response.send_message(f'❌ You don\'t have {quantity} {item} to sell.', ephemeral=True)
        return
    
    if item_key not in data['market']:
        await interaction.response.send_message(f'❌ Item `{item}` cannot be sold.', ephemeral=True)
        return
    
    sell_price = int(data['market'][item_key]['price'] * 0.7)
    total_earnings = sell_price * quantity
    
    citizen['inventory'][item_key] -= quantity
    if citizen['inventory'][item_key] == 0:
        del citizen['inventory'][item_key]
    
    citizen['credits'] += total_earnings
    data['market'][item_key]['supply'] += quantity
    save_data(data)
    
    embed = discord.Embed(
        title='💰 SALE COMPLETE',
        description=f'```ansi\n\x1b[32m>> TRANSACTION PROCESSED\x1b[0m\n```',
        color=COLORS['success']
    )
    embed.add_field(name='📦 SOLD', value=f'```{quantity}x {item.title()}```', inline=True)
    embed.add_field(name='💵 EARNED', value=f'```diff\n+ ¥{total_earnings:,}\n```', inline=True)
    embed.add_field(name='💳 BALANCE', value=f'```css\n¥{citizen["credits"]:,}\n```', inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='leave_faction', description='🚪 Leave your current faction')
async def leave_faction(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    if user_id not in data['citizens']:
        await interaction.response.send_message('⚠️ Neural link not established. Use `/jack_in` first.', ephemeral=True)
        return
    
    citizen = data['citizens'][user_id]
    
    if not citizen['faction']:
        await interaction.response.send_message('❌ You are not affiliated with any faction.', ephemeral=True)
        return
    
    old_faction = citizen['faction']
    citizen['faction'] = None
    citizen['reputation'] -= 15
    save_data(data)
    
    embed = discord.Embed(
        title='🚪 FACTION DEPARTURE',
        description=f'```ansi\n\x1b[31m>> LOYALTY CONTRACT TERMINATED\n>> LEFT {old_faction.upper()}\x1b[0m\n```',
        color=COLORS['warning']
    )
    embed.add_field(name='⚡ REP PENALTY', value=f'```diff\n-15\n```', inline=True)
    embed.add_field(name='🎭 STATUS', value=f'```\nIndependent\n```', inline=True)
    
    await interaction.response.send_message(embed=embed)

# Run the bot
if __name__ == '__main__':
    TOKEN = 'YOUR_BOT_TOKEN_HERE'
    bot.run(TOKEN)
