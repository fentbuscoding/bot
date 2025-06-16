"""
Economy System Constants and Configuration
"""

# Currency emoji
CURRENCY = "<:bronkbuk:1377389238290747582>"

# Blocked channels where economy commands are disabled
BLOCKED_CHANNELS = [1378156495144751147, 1260347806699491418]

# Bank upgrade costs and limits
BANK_UPGRADE_LEVELS = {
    1: {"cost": 5000, "limit": 10000},
    2: {"cost": 15000, "limit": 25000},
    3: {"cost": 50000, "limit": 75000},
    4: {"cost": 100000, "limit": 150000},
    5: {"cost": 250000, "limit": 400000},
    6: {"cost": 500000, "limit": 750000},
    7: {"cost": 1000000, "limit": 1500000},
    8: {"cost": 2500000, "limit": 4000000},
    9: {"cost": 5000000, "limit": 8000000},
    10: {"cost": 10000000, "limit": 15000000}
}

# Interest upgrade levels
INTEREST_UPGRADE_LEVELS = {
    1: {"cost": 10000, "rate": 0.02},   # 2% hourly
    2: {"cost": 25000, "rate": 0.025},  # 2.5% hourly
    3: {"cost": 75000, "rate": 0.03},   # 3% hourly
    4: {"cost": 200000, "rate": 0.035}, # 3.5% hourly
    5: {"cost": 500000, "rate": 0.04},  # 4% hourly
    6: {"cost": 1000000, "rate": 0.045}, # 4.5% hourly
    7: {"cost": 2500000, "rate": 0.05},  # 5% hourly
    8: {"cost": 5000000, "rate": 0.055}, # 5.5% hourly
    9: {"cost": 10000000, "rate": 0.06}, # 6% hourly
    10: {"cost": 25000000, "rate": 0.065}, # 6.5% hourly
    11: {"cost": 50000000, "rate": 0.07}, # 7% hourly
    12: {"cost": 100000000, "rate": 0.075}, # 7.5% hourly
    13: {"cost": 200000000, "rate": 0.08}, # 8% hourly
    14: {"cost": 500000000, "rate": 0.085}, # 8.5% hourly
    15: {"cost": 1000000000, "rate": 0.09}, # 9% hourly
    16: {"cost": 2000000000, "rate": 0.095}, # 9.5% hourly
    17: {"cost": 5000000000, "rate": 0.10}, # 10% hourly
    18: {"cost": 10000000000, "rate": 0.105}, # 10.5% hourly
    19: {"cost": 25000000000, "rate": 0.11}, # 11% hourly
    20: {"cost": 50000000000, "rate": 0.115} # 11.5% hourly
}

# Vote rewards
VOTE_REWARDS = {
    "daily": 2500,
    "streak_bonus": 500,  # Per day of streak
    "max_streak_bonus": 5000,  # Maximum streak bonus
    "random_bonus_min": 100,
    "random_bonus_max": 1000
}

# Command cooldowns (in seconds)
COOLDOWNS = {
    "deposit": 3,
    "withdraw": 3,
    "pay": 5,
    "interest": 3600,  # 1 hour
    "vote": 43200,     # 12 hours
}

# Embed colors
COLORS = {
    "success": 0x00ff00,
    "error": 0xff0000,
    "info": 0x0099ff,
    "warning": 0xffaa00,
    "neutral": 0x2b2d31
}

# Help text for amount parsing
AMOUNT_HELP_TEXT = """
**Amount Parsing Examples:**
• `1000` - Exact amount
• `1k` - 1,000
• `1.5m` - 1,500,000
• `2b` - 2,000,000,000
• `50%` - 50% of available
• `all` or `max` - Maximum available
• `1e3` - 1,000 (scientific notation)
• `2.5e5` - 250,000 (scientific notation)
"""
