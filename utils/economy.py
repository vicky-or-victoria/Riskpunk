# utils/economy.py
# Economy rebalancing and credit sink system

# ═══════════════════════════════════════════════════════════════════════════
# ECONOMY CONSTANTS - REBALANCED
# ═══════════════════════════════════════════════════════════════════════════

# Starting values (reduced from 5000)
STARTING_CREDITS = 1000
STARTING_LEVEL = 1
STARTING_HP = 100

# Credit sinks and costs
DEATH_PENALTY = 500  # Credits lost on death
RESPAWN_COST = 100   # Cost to respawn if broke
HEIST_ENTRY_FEE = 250  # Entry fee to start a heist
TERRITORY_ATTACK_BASE_COST = 500  # Base cost to attack territory
FACTION_WAR_COST = 5000  # Cost to declare faction war
PVP_ENTRY_FEE = 100  # Small entry fee for PvP duels

# Cooldown timers (in seconds)
COOLDOWNS = {
    "pvp": 300,  # 5 minutes between PvP duels
    "heist_create": 1800,  # 30 minutes between creating heists
    "heist_join": 60,  # 1 minute between joining heists
    "territory_attack": 900,  # 15 minutes between territory attacks
    "daily_claim": 86400,  # 24 hours for daily credits
    "faction_war": 604800,  # 7 days between faction wars
}

# Rewards (slightly reduced)
PVP_WIN_REWARD = 300  # Reduced from 500
PVP_WIN_XP = 100  # Reduced from 150
HEIST_BASE_REWARD_MULTIPLIER = 1.5  # Multiplier for heist difficulty
TERRITORY_INCOME_MULTIPLIER = 0.8  # Reduced territory income

# Maintenance costs
IMPLANT_MAINTENANCE_COST = 50  # Per implant per day
TERRITORY_UPKEEP_COST = 100  # Per territory per day

# Daily bonus
DAILY_LOGIN_CREDITS = 200
DAILY_LOGIN_XP = 50


# ═══════════════════════════════════════════════════════════════════════════
# CREDIT SINK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def calculate_territory_attack_cost(territory_defense: int) -> int:
    """Calculate cost to attack a territory based on its defense"""
    return TERRITORY_ATTACK_BASE_COST + (territory_defense * 10)


def calculate_heist_reward(difficulty: int, crew_size: int) -> float:
    """Calculate heist reward based on difficulty and crew"""
    base = difficulty * 1000 * HEIST_BASE_REWARD_MULTIPLIER
    # Reward split among crew
    return base / max(1, crew_size)


def calculate_death_penalty(player_credits: float) -> float:
    """Calculate credits lost on death"""
    # Lose either fixed penalty or 10% of credits, whichever is less
    return min(DEATH_PENALTY, player_credits * 0.1)


def calculate_territory_income(base_income: float, defense: int) -> float:
    """Calculate actual territory income with multiplier"""
    return base_income * TERRITORY_INCOME_MULTIPLIER


def calculate_maintenance_cost(implant_count: int, territory_count: int) -> float:
    """Calculate total daily maintenance cost"""
    return (implant_count * IMPLANT_MAINTENANCE_COST) + (territory_count * TERRITORY_UPKEEP_COST)
