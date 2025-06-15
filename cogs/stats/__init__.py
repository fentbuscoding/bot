"""
Stats Module
Modular statistics and monitoring system for Discord bot.
Handles performance tracking, command statistics, and dashboard integration.
"""

# Import main cog
from .stats_cog import Stats

# Import all managers for backwards compatibility
from .stats_manager import StatsManager
from .performance_manager import PerformanceManager
from .task_manager import TaskManager
from .dashboard_manager import DashboardManager
from .guild_manager import GuildManager
from .command_tracker import CommandTracker

# Import constants
from .constants import *

__all__ = [
    'Stats',
    'StatsManager',
    'PerformanceManager', 
    'TaskManager',
    'DashboardManager',
    'GuildManager',
    'CommandTracker'
]
