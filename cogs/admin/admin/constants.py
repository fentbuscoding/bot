"""
Admin Constants Module
Configuration and constants for the admin system.
"""

# Currency emoji
CURRENCY_EMOJI = "<:bronkbuk:1377106993495412789>"

# Admin permission levels
ADMIN_PERMISSIONS = {
    "owner": ["*"],  # All permissions
    "super_admin": [
        "economy.reset", "economy.manage_users", "shop.manage",
        "system.clear_commands", "system.repair_data", "buffs.manage"
    ],
    "admin": [
        "shop.manage", "economy.manage_users", "buffs.trigger"
    ],
    "moderator": [
        "economy.view", "shop.view"
    ]
}

# Fishing configuration
FISH_TYPES = {
    "normal": {
        "name": "Normal Fish",
        "rarity": 0.7,
        "value_range": (10, 100)
    },
    "rare": {
        "name": "Rare Fish", 
        "rarity": 0.2,
        "value_range": (100, 500)
    },
    "event": {
        "name": "Event Fish",
        "rarity": 0.08,
        "value_range": (500, 2000)
    },
    "mutated": {
        "name": "Mutated Fish",
        "rarity": 0.02,
        "value_range": (2000, 10000)
    }
}

# Default fishing items
DEFAULT_FISHING_ITEMS = {
    "bait_shop": {
        "beginner_bait": {
            "name": "Beginner Bait",
            "price": 0,  # Free for first 10
            "amount": 10,
            "description": "Basic bait for catching fish",
            "catch_rates": {"normal": 1.0, "rare": 0.1}
        },
        "pro_bait": {
            "name": "Pro Bait",
            "price": 50,
            "amount": 10,
            "description": "Better chances for rare fish",
            "catch_rates": {"normal": 1.2, "rare": 0.3, "event": 0.1}
        },
        "mutated_bait": {
            "name": "Mutated Bait",
            "price": 200,
            "amount": 5,
            "description": "Chance to catch mutated fish",
            "catch_rates": {"normal": 1.5, "rare": 0.5, "event": 0.2, "mutated": 0.1}
        }
    },
    "rod_shop": {
        "beginner_rod": {
            "name": "Beginner Rod",
            "price": 0,  # Free for first one
            "description": "Basic fishing rod",
            "multiplier": 1.0
        },
        "pro_rod": {
            "name": "Pro Rod",
            "price": 5000,
            "description": "50% better catch rates",
            "multiplier": 1.5
        },
        "master_rod": {
            "name": "Master Rod",
            "price": 25000,
            "description": "Double catch rates",
            "multiplier": 2.0
        }
    }
}

# Buff types and configurations
BUFF_TYPES = {
    "experience": {
        "name": "Experience Boost",
        "description": "Double experience from all activities",
        "multiplier": 2.0,
        "duration_hours": 24,
        "emoji": "💫"
    },
    "currency": {
        "name": "Currency Boost",
        "description": "50% bonus currency from work and fishing",
        "multiplier": 1.5,
        "duration_hours": 12,
        "emoji": "💰"
    },
    "fishing": {
        "name": "Fishing Boost",
        "description": "Double fish catch rates and value",
        "multiplier": 2.0,
        "duration_hours": 8,
        "emoji": "🎣"
    },
    "trading": {
        "name": "Trading Boost",
        "description": "Reduced trading fees and better rates",
        "multiplier": 0.5,  # Reduced fees
        "duration_hours": 6,
        "emoji": "🤝"
    }
}

# Shop categories
SHOP_CATEGORIES = {
    "items": {
        "name": "Items",
        "description": "General items and consumables",
        "emoji": "📦"
    },
    "upgrades": {
        "name": "Upgrades",
        "description": "Permanent upgrades and enhancements",
        "emoji": "⬆️"
    },
    "rods": {
        "name": "Fishing Rods",
        "description": "Fishing equipment and tools",
        "emoji": "🎣"
    },
    "bait": {
        "name": "Bait",
        "description": "Fishing bait and lures",
        "emoji": "🪱"
    },
    "potions": {
        "name": "Potions",
        "description": "Temporary boost potions",
        "emoji": "🧪"
    }
}

# Admin command categories
ADMIN_CATEGORIES = {
    "shop": {
        "name": "Shop Management",
        "description": "Manage shop items and categories",
        "emoji": "🏪"
    },
    "economy": {
        "name": "Economy Administration",
        "description": "Manage user balances and economy",
        "emoji": "💰"
    },
    "system": {
        "name": "System Administration",
        "description": "System maintenance and repair",
        "emoji": "🔧"
    },
    "buffs": {
        "name": "Buff Management",
        "description": "Manage global buffs and events",
        "emoji": "✨"
    }
}

# Error messages
ERROR_MESSAGES = {
    "no_permission": "❌ You don't have permission to use this command.",
    "invalid_shop_type": "❌ Invalid shop type. Valid types: items, upgrades, rods, bait, potions",
    "item_not_found": "❌ Item not found in the specified shop category.",
    "invalid_json": "❌ Invalid JSON format. Please check your syntax.",
    "file_not_found": "❌ Shop data file not found.",
    "database_error": "❌ Database error occurred. Please try again later.",
    "user_not_found": "❌ User not found or not in the database.",
    "insufficient_balance": "❌ User has insufficient balance for this operation.",
    "confirmation_required": "❌ Please provide confirmation by typing 'CONFIRM' to proceed."
}

# Success messages
SUCCESS_MESSAGES = {
    "item_added": "✅ Item successfully added to the shop.",
    "item_removed": "✅ Item successfully removed from the shop.",
    "item_updated": "✅ Item successfully updated.",
    "shop_reset": "✅ Shop has been reset successfully.",
    "user_balance_updated": "✅ User balance has been updated.",
    "economy_reset": "✅ Economy has been reset successfully.",
    "data_repaired": "✅ User data has been repaired.",
    "buff_activated": "✅ Global buff has been activated.",
    "commands_cleared": "✅ Application commands have been cleared."
}

# Confirmation phrases
CONFIRMATION_PHRASES = [
    "CONFIRM",
    "YES I AM SURE",
    "PROCEED",
    "I UNDERSTAND THE CONSEQUENCES"
]
