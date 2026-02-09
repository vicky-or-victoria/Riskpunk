# utils/cooldowns.py
# Cooldown management system to prevent command spam

import time
from typing import Dict, Optional
from .economy import COOLDOWNS

# In-memory cooldown storage (could be moved to database for persistence)
_cooldowns: Dict[str, Dict[int, float]] = {
    "pvp": {},
    "heist_create": {},
    "heist_join": {},
    "territory_attack": {},
    "daily_claim": {},
    "faction_war": {},
}


def get_cooldown_key(action: str, user_id: int) -> Optional[float]:
    """Get the remaining cooldown time for an action"""
    if action not in _cooldowns:
        return None
    
    if user_id not in _cooldowns[action]:
        return 0
    
    last_use = _cooldowns[action][user_id]
    cooldown_duration = COOLDOWNS.get(action, 0)
    elapsed = time.time() - last_use
    remaining = cooldown_duration - elapsed
    
    return max(0, remaining)


def set_cooldown(action: str, user_id: int):
    """Set a cooldown for a user action"""
    if action not in _cooldowns:
        _cooldowns[action] = {}
    
    _cooldowns[action][user_id] = time.time()


def check_cooldown(action: str, user_id: int) -> tuple[bool, float]:
    """
    Check if an action is on cooldown
    Returns: (is_ready: bool, remaining_seconds: float)
    """
    remaining = get_cooldown_key(action, user_id)
    if remaining is None:
        return True, 0
    
    return remaining <= 0, remaining


def format_cooldown_time(seconds: float) -> str:
    """Format cooldown time in human-readable format"""
    if seconds <= 0:
        return "Ready!"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def clear_user_cooldowns(user_id: int):
    """Clear all cooldowns for a user (admin function)"""
    for action in _cooldowns:
        if user_id in _cooldowns[action]:
            del _cooldowns[action][user_id]


def get_all_user_cooldowns(user_id: int) -> Dict[str, float]:
    """Get all active cooldowns for a user"""
    result = {}
    for action in _cooldowns:
        remaining = get_cooldown_key(action, user_id)
        if remaining and remaining > 0:
            result[action] = remaining
    return result
