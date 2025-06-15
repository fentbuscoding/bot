"""
Trading System Constants and Configuration
"""

# Currency emoji
CURRENCY = "<:bronkbuk:1377389238290747582>"

# Trade expiration times (in minutes)
TRADE_TIMEOUT = 15
QUICK_TRADE_TIMEOUT = 5

# Balance tolerance for fair trades
BALANCE_TOLERANCE = 0.25
STRICT_BALANCE_TOLERANCE = 0.15

# Risk assessment thresholds
RISK_THRESHOLDS = {
    "extreme": 0.5,   # Below 50% balance ratio
    "high": 0.7,      # Below 70% balance ratio
    "medium": 0.85,   # Below 85% balance ratio
    "low": 1.0        # Above 85% balance ratio
}

# Trade limits
MAX_ITEMS_PER_TRADE = 20
MAX_CURRENCY_PER_TRADE = 1000000000  # 1 billion
MIN_TRADE_VALUE = 1

# Status constants
TRADE_STATUS = {
    "DRAFTING": "drafting",
    "PENDING": "pending", 
    "CONFIRMED": "confirmed",
    "COMPLETED": "completed",
    "CANCELLED": "cancelled",
    "EXPIRED": "expired"
}

# Colors for embeds
COLORS = {
    "success": 0x00ff00,
    "error": 0xff0000,
    "warning": 0xffaa00,
    "info": 0x0099ff,
    "neutral": 0x2b2d31,
    "risk_low": 0x00ff00,
    "risk_medium": 0xffaa00,
    "risk_high": 0xff6600,
    "risk_extreme": 0xff0000
}

# Risk level emojis
RISK_EMOJIS = {
    "low": "🟢",
    "medium": "🟡", 
    "high": "🟠",
    "extreme": "🔴"
}

# Trade action emojis
EMOJIS = {
    "currency": "💰",
    "items": "📦",
    "add": "➕",
    "remove": "➖",
    "lock": "🔒",
    "unlock": "🔓",
    "confirm": "✅",
    "cancel": "❌",
    "private": "🔒",
    "public": "🔓",
    "warning": "⚠️",
    "success": "✅",
    "error": "❌"
}

# Default trade notes
DEFAULT_NOTES = {
    "fair_trade": "Looking for a fair trade!",
    "quick_sale": "Quick sale - accepting reasonable offers",
    "collection": "Collecting this item - willing to overpay",
    "investment": "Investment opportunity",
    "bulk_discount": "Bulk trade discount available"
}
