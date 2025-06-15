"""
Bazaar Constants Module
Configuration and constants for the bazaar system.
"""

# Default item types and their base configurations
DEFAULT_ITEM_TYPES = [
    "fishing_rod", "bait", "potion", "color", "upgrade", "tool"
]

# Bazaar shop configuration
BAZAAR_CONFIG = {
    "refresh_hours": 12,
    "max_items": 6,
    "min_discount": 0.1,  # 10%
    "max_discount": 0.4,  # 40%
    "quality_weights": {
        "common": 0.5,
        "uncommon": 0.3,
        "rare": 0.15,
        "epic": 0.04,
        "legendary": 0.01
    }
}

# Item quality colors for embeds
QUALITY_COLORS = {
    "common": 0x9d9d9d,      # Gray
    "uncommon": 0x1eff00,    # Green
    "rare": 0x0070dd,       # Blue
    "epic": 0xa335ee,       # Purple
    "legendary": 0xff8000   # Orange
}

# Emojis for the bazaar
BAZAAR_EMOJIS = {
    "bazaar": "🏪",
    "coin": "<:bronkbuk:1377389238290747582>",
    "refresh": "🔄",
    "purchase": "🛒",
    "discount": "💰",
    "quality": {
        "common": "⚪",
        "uncommon": "🟢", 
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟠"
    }
}

# Purchase limits
PURCHASE_LIMITS = {
    "min_amount": 1,
    "max_amount": 10,
    "max_daily_purchases": 50
}

# Bazaar messages
BAZAAR_MESSAGES = {
    "welcome": "Welcome to the Traveling Bazaar! 🏪\nDiscover rare items at discounted prices!",
    "no_items": "The bazaar is currently empty. Check back later!",
    "refresh_success": "✅ The bazaar has been refreshed with new items!",
    "purchase_success": "✅ Purchase successful! Items added to your inventory.",
    "insufficient_funds": "❌ You don't have enough currency for this purchase.",
    "invalid_amount": "❌ Please enter a valid amount (1-10).",
    "purchase_limit": "❌ You've reached your daily purchase limit.",
    "item_out_of_stock": "❌ This item is no longer available."
}
