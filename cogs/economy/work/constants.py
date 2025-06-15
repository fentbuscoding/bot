"""
Constants and configuration for the Work system
"""

# Job definitions with all properties
JOBS = {
    "discord_mod": {
        "name": "Discord Moderator",
        "wage": {"min": 200, "max": 800},
        "boss": {"hostile": 5, "loyalty": 0},
        "emoji": "🔨",
        "description": "Delete messages and ban users for the greater good",
        "minigame": "moderation"
    },
    "reddit_admin": {
        "name": "Reddit Admin", 
        "wage": {"min": 500, "max": 1500},
        "boss": {"hostile": 10, "loyalty": 0},
        "emoji": "🤓",
        "description": "Control the narrative and moderate subreddits",
        "minigame": "reddit"
    },
    "pokimane_sub": {
        "name": "Pokimane Subscriber",
        "wage": {"min": 50, "max": 300},
        "boss": {"hostile": 0, "loyalty": 10},
        "emoji": "💸",
        "description": "Donate your life savings for a chance at a shoutout",
        "minigame": "simp"
    },
    "meme_poster": {
        "name": "Professional Meme Poster",
        "wage": {"min": 100, "max": 600},
        "boss": {"hostile": 3, "loyalty": 5},
        "emoji": "🗿",
        "description": "Create dank memes for internet points",
        "minigame": "meme"
    },
    "nft_trader": {
        "name": "NFT Trader",
        "wage": {"min": 0, "max": 5000},
        "boss": {"hostile": 20, "loyalty": 0},
        "emoji": "🖼️",
        "description": "Right-click save forbidden JPEGs",
        "minigame": "nft"
    },
    "crypto_investor": {
        "name": "Crypto Day Trader",
        "wage": {"min": 50, "max": 3000},
        "boss": {"hostile": 15, "loyalty": 0},
        "emoji": "📈",
        "description": "Lose money with diamond hands",
        "minigame": "crypto"
    },
    "twitter_warrior": {
        "name": "Twitter Social Justice Warrior",
        "wage": {"min": 0, "max": 400},
        "boss": {"hostile": 25, "loyalty": 0},
        "emoji": "🐦",
        "description": "Get offended professionally",
        "minigame": "twitter"
    },
    "twitch_streamer": {
        "name": "Twitch Streamer",
        "wage": {"min": 20, "max": 2000},
        "boss": {"hostile": 5, "loyalty": 15},
        "emoji": "🎮",
        "description": "Entertain 3 viewers including your mom",
        "minigame": "streaming"
    }
}

# Currency emoji
CURRENCY = "<:bronkbuk:1377389238290747582>"

# Work cooldown settings
WORK_COOLDOWN = 3600  # 1 hour in seconds
RAISE_COOLDOWN = 86400  # 24 hours in seconds

# Boss relationship ranges
BOSS_HOSTILE_MAX = 100
BOSS_LOYALTY_MAX = 100

# Wage multipliers based on boss relationship
HOSTILE_WAGE_PENALTY = 0.5  # 50% penalty at max hostility
LOYALTY_WAGE_BONUS = 1.5    # 50% bonus at max loyalty

# Gift costs and effects
BOSS_GIFTS = {
    "coffee": {"cost": 50, "loyalty": 5, "hostile": -2, "emoji": "☕", "name": "Coffee"},
    "donut": {"cost": 100, "loyalty": 8, "hostile": -3, "emoji": "🍩", "name": "Donut"},
    "pizza": {"cost": 200, "loyalty": 15, "hostile": -5, "emoji": "🍕", "name": "Pizza"},
    "flowers": {"cost": 500, "loyalty": 25, "hostile": -10, "emoji": "💐", "name": "Flowers"},
    "watch": {"cost": 1000, "loyalty": 40, "hostile": -15, "emoji": "⌚", "name": "Watch"},
    "car": {"cost": 5000, "loyalty": 80, "hostile": -30, "emoji": "🚗", "name": "Car"}
}

# Minigame reward multipliers
MINIGAME_SUCCESS_MULTIPLIER = 1.5
MINIGAME_FAILURE_MULTIPLIER = 0.7

# Colors for embeds
WORK_EMBED_COLOR = 0x00ff00
ERROR_EMBED_COLOR = 0xff0000
INFO_EMBED_COLOR = 0x0099ff
