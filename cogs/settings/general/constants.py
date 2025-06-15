"""
General Settings Constants Module
Configuration and constants for the general settings system.
"""

# Permission levels for settings management
PERMISSION_LEVELS = {
    "owner": 5,
    "admin": 4,
    "manager": 3,
    "moderator": 2,
    "trusted": 1,
    "default": 0
}

# Maximum limits for various settings
LIMITS = {
    "max_prefixes": 5,
    "max_prefix_length": 5,
    "max_whitelist_per_command": 50,
    "max_blacklist_per_command": 100,
    "max_ignored_users": 25,
    "max_ignored_roles": 10
}

# Default settings for new guilds
DEFAULT_GUILD_SETTINGS = {
    "prefixes": ["."],
    "permissions": {
        "roles": {},
        "users": {}
    },
    "whitelist": {},
    "blacklist": {},
    "ignored": {
        "users": [],
        "roles": []
    },
    "general_settings": {
        "case_sensitive_commands": False,
        "delete_failed_commands": False,
        "mention_as_prefix": True,
        "allow_dm_commands": True,
        "require_permissions_for_all": False
    }
}

# Setting categories for organization
SETTING_CATEGORIES = {
    "prefixes": {
        "name": "Prefixes",
        "description": "Manage command prefixes for this server",
        "emoji": "📌",
        "permission_required": "manage_guild"
    },
    "permissions": {
        "name": "Permissions",
        "description": "Manage who can edit bot settings",
        "emoji": "🔐",
        "permission_required": "manage_guild"
    },
    "whitelist": {
        "name": "Whitelist",
        "description": "Manage command channel/role whitelists",
        "emoji": "✅",
        "permission_required": "manage_guild"
    },
    "blacklist": {
        "name": "Blacklist",
        "description": "Manage command channel/role/user blacklists",
        "emoji": "❌",
        "permission_required": "manage_guild"
    },
    "ignore": {
        "name": "Ignore",
        "description": "Manage ignored users and roles",
        "emoji": "🔇",
        "permission_required": "manage_guild"
    }
}

# Command validation patterns
COMMAND_PATTERNS = {
    "valid_command_chars": r"^[a-zA-Z0-9_-]+$",
    "reserved_commands": ["help", "ping", "info", "general"],
    "max_command_length": 32
}

# Error messages
ERROR_MESSAGES = {
    "no_permission": "❌ You don't have permission to modify bot settings.",
    "invalid_prefix": "❌ Invalid prefix. Must be 1-5 characters and not contain spaces.",
    "prefix_exists": "❌ That prefix is already configured for this server.",
    "prefix_limit": "❌ Maximum number of prefixes reached (5).",
    "prefix_not_found": "❌ That prefix is not configured for this server.",
    "invalid_command": "❌ Invalid command name. Use only letters, numbers, hyphens, and underscores.",
    "command_not_found": "❌ Command not found.",
    "whitelist_limit": "❌ Maximum whitelist entries reached for this command.",
    "blacklist_limit": "❌ Maximum blacklist entries reached for this command.",
    "already_whitelisted": "❌ Already whitelisted for this command.",
    "already_blacklisted": "❌ Already blacklisted for this command.",
    "not_whitelisted": "❌ Not currently whitelisted for this command.",
    "not_blacklisted": "❌ Not currently blacklisted for this command.",
    "user_not_found": "❌ User not found in this server.",
    "role_not_found": "❌ Role not found in this server.",
    "channel_not_found": "❌ Channel not found in this server.",
    "ignored_limit": "❌ Maximum number of ignored users/roles reached.",
    "already_ignored": "❌ User/role is already being ignored.",
    "not_ignored": "❌ User/role is not currently being ignored.",
    "database_error": "❌ Database error occurred. Please try again later.",
    "invalid_setting": "❌ Invalid setting name.",
    "setting_unchanged": "❌ Setting is already set to that value."
}

# Success messages
SUCCESS_MESSAGES = {
    "prefix_added": "✅ Prefix added successfully.",
    "prefix_removed": "✅ Prefix removed successfully.",
    "permission_added": "✅ Permission granted successfully.",
    "permission_removed": "✅ Permission removed successfully.",
    "whitelist_added": "✅ Added to whitelist successfully.",
    "whitelist_removed": "✅ Removed from whitelist successfully.",
    "blacklist_added": "✅ Added to blacklist successfully.",
    "blacklist_removed": "✅ Removed from blacklist successfully.",
    "ignored_added": "✅ User/role is now being ignored.",
    "ignored_removed": "✅ User/role is no longer being ignored.",
    "settings_reset": "✅ Settings have been reset to defaults.",
    "setting_updated": "✅ Setting updated successfully."
}

# Help text for each category
HELP_TEXT = {
    "general": (
        "**General Settings Help**\n\n"
        "Use the following commands to manage server settings:\n"
        "`general view` - View current settings\n"
        "`general prefix` - Manage prefixes\n"
        "`general permissions` - Manage permissions\n"
        "`general whitelist` - Manage whitelists\n"
        "`general blacklist` - Manage blacklists\n"
        "`general ignore` - Manage ignored users/roles"
    ),
    "prefix": (
        "**Prefix Management**\n\n"
        "`prefix add <prefix>` - Add a new prefix\n"
        "`prefix remove <prefix>` - Remove a prefix\n"
        "`prefix list` - List all current prefixes\n\n"
        "**Notes:**\n"
        "• Maximum 5 prefixes per server\n"
        "• Prefixes can be 1-5 characters long\n"
        "• Cannot contain spaces"
    ),
    "permissions": (
        "**Permission Management**\n\n"
        "`permissions view` - View current permissions\n"
        "`permissions add role <role>` - Grant role settings access\n"
        "`permissions add user <user>` - Grant user settings access\n"
        "`permissions remove role <role>` - Remove role settings access\n"
        "`permissions remove user <user>` - Remove user settings access"
    ),
    "whitelist": (
        "**Whitelist Management**\n\n"
        "`whitelist view` - View current whitelists\n"
        "`whitelist channel <channel> <command>` - Whitelist channel for command\n"
        "`whitelist role <role> <command>` - Whitelist role for command\n"
        "`whitelist remove channel <channel> <command>` - Remove channel whitelist\n"
        "`whitelist remove role <role> <command>` - Remove role whitelist"
    ),
    "blacklist": (
        "**Blacklist Management**\n\n"
        "`blacklist view` - View current blacklists\n"
        "`blacklist channel <channel> <command>` - Blacklist channel for command\n"
        "`blacklist role <role> <command>` - Blacklist role for command\n"
        "`blacklist user <user> <command>` - Blacklist user for command\n"
        "`blacklist remove <type> <target> <command>` - Remove blacklist"
    ),
    "ignore": (
        "**Ignore Management**\n\n"
        "`ignore view` - View currently ignored users/roles\n"
        "`ignore user <user>` - Ignore a user\n"
        "`ignore role <role>` - Ignore a role\n"
        "`ignore remove user <user>` - Stop ignoring user\n"
        "`ignore remove role <role>` - Stop ignoring role"
    )
}

# Settings validation schemas
VALIDATION_SCHEMAS = {
    "prefix": {
        "type": "string",
        "min_length": 1,
        "max_length": 5,
        "pattern": r"^[^\s]+$",  # No spaces
        "reserved": ["@everyone", "@here"]
    },
    "command": {
        "type": "string",
        "min_length": 1,
        "max_length": 32,
        "pattern": r"^[a-zA-Z0-9_-]+$"
    }
}
