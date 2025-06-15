"""
Utility Constants Module
Configuration and constants for the utility system.
"""

# Command categories for organization
COMMAND_CATEGORIES = {
    "system": {
        "name": "🔧 System & Bot Management",
        "commands": ["ping", "uptime", "botinfo", "restart", "restart_force"],
        "description": "Bot system status and management commands"
    },
    "information": {
        "name": "ℹ️ Information & Details", 
        "commands": ["serverinfo", "userinfo", "roleinfo", "avatar", "banner", "emojiinfo", "servericon", "serverbanner"],
        "description": "Get detailed information about users, servers, and Discord entities"
    },
    "utilities": {
        "name": "🛠️ Text & URL Utilities",
        "commands": ["calculate", "hexcolor", "tinyurl", "timestamp", "countdown"],
        "description": "Helpful utility tools for text processing and calculations"
    },
    "interactive": {
        "name": "🎮 Interactive Commands",
        "commands": ["poll", "multipoll", "lottery", "afk"],
        "description": "Interactive and engaging commands for server activity"
    },
    "messages": {
        "name": "💬 Message Management", 
        "commands": ["cleanup", "snipe", "firstmessage"],
        "description": "Commands to manage and interact with messages"
    },
    "emojis": {
        "name": "😀 Emoji Management",
        "commands": ["emojisteal"],
        "description": "Tools for managing server emojis"
    }
}

# Limits and constraints
LIMITS = {
    "cleanup_max": 1000,
    "cleanup_default": 100,
    "poll_max_options": 20,
    "multipoll_max_options": 10,
    "lottery_max_number": 10000,
    "lottery_max_picks": 50,
    "tinyurl_max_length": 2000,
    "hex_color_length": 7,  # Including #
    "afk_max_reason_length": 500,
    "snipe_max_age_hours": 24
}

# Default values
DEFAULTS = {
    "lottery_max_num": 100,
    "lottery_picks": 6,
    "timestamp_style": "f",
    "afk_reason": "AFK",
    "cleanup_limit": 100
}

# Bot restart settings
RESTART_SETTINGS = {
    "max_wait_minutes": 30,
    "check_interval_seconds": 5,
    "critical_activities": [
        "active_gambling",
        "ongoing_trades", 
        "active_work_sessions",
        "pending_reminders",
        "active_giveaways"
    ],
    "blocking_activities": [
        "music_playing",
        "active_modmail",
        "economy_transactions"
    ]
}

# AFK system settings
AFK_SETTINGS = {
    "max_afk_users": 1000,  # Per guild
    "afk_timeout_hours": 72,  # Auto-remove after 3 days
    "mention_response_cooldown": 30  # Seconds between AFK responses
}

# Snipe system settings
SNIPE_SETTINGS = {
    "max_sniped_messages": 10,  # Per channel
    "snipe_expiry_hours": 24,
    "max_content_length": 2000
}

# Emoji settings
EMOJI_SETTINGS = {
    "max_emoji_size_mb": 8,
    "allowed_formats": ["png", "jpg", "jpeg", "gif", "webp"],
    "max_name_length": 32
}

# Color constants
COLORS = {
    "success": 0x2ecc71,
    "error": 0xe74c3c,
    "warning": 0xf39c12,
    "info": 0x3498db,
    "default": 0x95a5a6
}

# Embed limits
EMBED_LIMITS = {
    "title_max": 256,
    "description_max": 4096,
    "field_name_max": 256,
    "field_value_max": 1024,
    "footer_max": 2048,
    "author_name_max": 256,
    "max_fields": 25
}

# Time format styles for timestamp command
TIMESTAMP_STYLES = {
    "t": "Short Time (16:20)",
    "T": "Long Time (16:20:30)",
    "d": "Short Date (20/04/2021)",
    "D": "Long Date (20 April 2021)",
    "f": "Short Date/Time (20 April 2021 16:20)",
    "F": "Long Date/Time (Tuesday, 20 April 2021 16:20)",
    "R": "Relative Time (2 months ago)"
}

# Help text templates
HELP_TEMPLATES = {
    "command_usage": "**Usage:** `{prefix}{command} {usage}`",
    "command_aliases": "**Aliases:** {aliases}",
    "command_description": "{description}",
    "no_permission": "❌ You don't have permission to use this command.",
    "cooldown": "⏰ This command is on cooldown. Try again in {time}.",
    "missing_args": "❌ Missing required arguments. Use `{prefix}help {command}` for usage info."
}
