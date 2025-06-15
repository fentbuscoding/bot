"""
Stats Constants Module
Configuration and constants for the statistics system.
"""

# Dashboard settings
DASHBOARD_SETTINGS = {
    "update_interval_minutes": 10,
    "performance_update_interval_minutes": 5,
    "daily_reset_hour": 0,  # UTC
    "max_retry_attempts": 3,
    "request_timeout_seconds": 30,
    "batch_size": 100
}

# Statistics categories
STAT_CATEGORIES = {
    "commands": {
        "name": "Command Usage",
        "description": "Track command usage and popularity",
        "fields": ["total_commands", "unique_commands", "command_breakdown", "hourly_usage"]
    },
    "performance": {
        "name": "Bot Performance", 
        "description": "System performance metrics",
        "fields": ["cpu_usage", "memory_usage", "latency", "uptime", "response_times"]
    },
    "guilds": {
        "name": "Guild Statistics",
        "description": "Server and user statistics",
        "fields": ["total_guilds", "total_users", "active_guilds", "guild_sizes"]
    },
    "economy": {
        "name": "Economy Statistics",
        "description": "Economy system usage and transactions",
        "fields": ["total_transactions", "currency_circulation", "popular_items"]
    },
    "engagement": {
        "name": "User Engagement",
        "description": "User activity and interaction metrics", 
        "fields": ["active_users", "command_frequency", "peak_hours"]
    }
}

# Data retention settings
RETENTION_SETTINGS = {
    "daily_stats_days": 30,
    "hourly_stats_hours": 168,  # 7 days
    "command_logs_days": 7,
    "performance_logs_hours": 24,
    "error_logs_days": 14
}

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    "cpu_warning": 70,     # %
    "cpu_critical": 85,    # %
    "memory_warning": 80,  # %
    "memory_critical": 90, # %
    "latency_warning": 200, # ms
    "latency_critical": 500, # ms
    "response_time_warning": 1000, # ms
    "response_time_critical": 3000  # ms
}

# Alert settings
ALERT_SETTINGS = {
    "enable_performance_alerts": True,
    "enable_error_alerts": True,
    "enable_usage_alerts": False,
    "alert_cooldown_minutes": 30,
    "alert_channels": {
        "performance": None,  # Channel ID for performance alerts
        "errors": None,       # Channel ID for error alerts
        "usage": None         # Channel ID for usage alerts
    }
}

# Guild information settings
GUILD_SETTINGS = {
    "max_guilds_per_page": 10,
    "max_members_display": 50,
    "cache_duration_minutes": 15,
    "info_update_interval_hours": 6
}

# Database collection names
COLLECTIONS = {
    "daily_stats": "daily_stats",
    "hourly_stats": "hourly_stats", 
    "command_logs": "command_logs",
    "performance_logs": "performance_logs",
    "guild_stats": "guild_stats",
    "user_stats": "user_stats",
    "error_logs": "error_logs"
}

# API endpoints
API_ENDPOINTS = {
    "stats_update": "/api/stats/update",
    "performance_update": "/api/performance/update", 
    "command_log": "/api/commands/log",
    "guild_update": "/api/guilds/update",
    "health_check": "/api/health"
}

# Default stat structure
DEFAULT_STATS = {
    "total_commands": 0,
    "unique_commands": 0,
    "command_breakdown": {},
    "hourly_usage": [0] * 24,
    "daily_usage": [0] * 7,
    "top_commands": [],
    "top_users": [],
    "top_guilds": [],
    "errors": 0,
    "uptime": 0,
    "last_updated": None
}

# Performance metrics structure
DEFAULT_PERFORMANCE = {
    "cpu_usage": 0.0,
    "memory_usage": 0.0,
    "memory_total": 0.0,
    "latency": 0.0,
    "response_times": [],
    "active_connections": 0,
    "database_latency": 0.0,
    "cache_hit_rate": 0.0,
    "uptime_seconds": 0,
    "last_restart": None
}

# Color scheme for embeds
COLORS = {
    "stats": 0x3498db,
    "performance": 0x2ecc71,
    "warning": 0xf39c12,
    "error": 0xe74c3c,
    "success": 0x27ae60,
    "info": 0x17a2b8
}

# Limits and constraints
LIMITS = {
    "max_command_name_length": 32,
    "max_guild_name_length": 100,
    "max_user_name_length": 32,
    "max_error_message_length": 500,
    "max_performance_samples": 100,
    "max_top_items": 20
}

# Time formats
TIME_FORMATS = {
    "timestamp": "%Y-%m-%d %H:%M:%S UTC",
    "date": "%Y-%m-%d", 
    "time": "%H:%M:%S",
    "iso": "%Y-%m-%dT%H:%M:%S.%fZ"
}

# Chart settings for dashboard
CHART_SETTINGS = {
    "command_usage_chart": {
        "type": "line",
        "time_range": "24h",
        "update_interval": 300  # 5 minutes
    },
    "performance_chart": {
        "type": "area",
        "time_range": "6h", 
        "update_interval": 60   # 1 minute
    },
    "guild_growth_chart": {
        "type": "line",
        "time_range": "30d",
        "update_interval": 3600 # 1 hour
    }
}
