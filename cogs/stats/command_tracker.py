"""
Command Tracker
Handles command usage tracking and analysis.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional

from utils.db import db
from utils.command_tracker import usage_tracker
from cogs.logging.logger import CogLogger
from .constants import (
    COLLECTIONS, RETENTION_SETTINGS, LIMITS
)

logger = CogLogger('CommandTracker')

class CommandTracker:
    """Tracks and analyzes command usage"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = db
        
        # Command tracking data
        self.command_times = {}
        self.recent_commands = []
        
    async def track_command_completion(self, ctx):
        """Track successful command completion"""
        try:
            command_name = ctx.command.qualified_name if ctx.command else "unknown"
            user_id = ctx.author.id
            guild_id = ctx.guild.id if ctx.guild else None
            
            # Calculate execution time if available
            execution_time = 0.0
            if hasattr(ctx, 'command_start_time'):
                execution_time = time.time() - ctx.command_start_time
            
            # Update local stats
            await self._update_command_stats(command_name, user_id, guild_id, execution_time, True)
            
            # Log to database
            await self._log_command_usage(command_name, user_id, guild_id, execution_time, True)
            
            # Send real-time update to dashboard
            stats_cog = self.bot.get_cog('Stats')
            if stats_cog and hasattr(stats_cog, 'dashboard_manager'):
                await stats_cog.dashboard_manager.send_realtime_command_update(
                    command_name, user_id, guild_id, execution_time, True
                )
            
            logger.debug(f"Tracked command completion: {command_name} by {user_id}")
            
        except Exception as e:
            logger.error(f"Error tracking command completion: {e}")

    async def track_command_error(self, ctx, error):
        """Track command errors"""
        try:
            command_name = ctx.command.qualified_name if ctx.command else "unknown"
            user_id = ctx.author.id
            guild_id = ctx.guild.id if ctx.guild else None
            
            # Calculate execution time if available
            execution_time = 0.0
            if hasattr(ctx, 'command_start_time'):
                execution_time = time.time() - ctx.command_start_time
            
            # Update local stats
            await self._update_command_stats(command_name, user_id, guild_id, execution_time, False)
            
            # Log error to database
            await self._log_command_error(command_name, user_id, guild_id, error, execution_time)
            
            # Send real-time update to dashboard
            stats_cog = self.bot.get_cog('Stats')
            if stats_cog and hasattr(stats_cog, 'dashboard_manager'):
                await stats_cog.dashboard_manager.send_realtime_command_update(
                    command_name, user_id, guild_id, execution_time, False
                )
            
            logger.debug(f"Tracked command error: {command_name} by {user_id} - {type(error).__name__}")
            
        except Exception as e:
            logger.error(f"Error tracking command error: {e}")

    async def _update_command_stats(self, command_name: str, user_id: int, 
                                  guild_id: Optional[int], execution_time: float, 
                                  success: bool):
        """Update local command statistics"""
        try:
            # Get stats manager
            stats_cog = self.bot.get_cog('Stats')
            if stats_cog and hasattr(stats_cog, 'stats_manager'):
                await stats_cog.stats_manager.update_command_stats(
                    command_name, user_id, guild_id, execution_time, success
                )
            
            # Update command timing data
            if command_name not in self.command_times:
                self.command_times[command_name] = []
            
            self.command_times[command_name].append(execution_time)
            
            # Keep only recent times (limit memory usage)
            if len(self.command_times[command_name]) > 100:
                self.command_times[command_name] = self.command_times[command_name][-100:]
            
            # Update recent commands list
            self.recent_commands.append({
                'command': command_name,
                'user_id': user_id,
                'guild_id': guild_id,
                'execution_time': execution_time,
                'success': success,
                'timestamp': datetime.now()
            })
            
            # Limit recent commands list
            if len(self.recent_commands) > 1000:
                self.recent_commands = self.recent_commands[-1000:]
                
        except Exception as e:
            logger.error(f"Error updating command stats: {e}")

    async def _log_command_usage(self, command_name: str, user_id: int, 
                               guild_id: Optional[int], execution_time: float, 
                               success: bool):
        """Log command usage to database"""
        try:
            collection = self.db.db[COLLECTIONS['command_logs']]
            
            log_entry = {
                'command_name': command_name,
                'user_id': str(user_id),
                'guild_id': str(guild_id) if guild_id else None,
                'execution_time': execution_time,
                'success': success,
                'timestamp': datetime.now(),
                'bot_id': str(self.bot.user.id) if self.bot.user else None
            }
            
            await collection.insert_one(log_entry)
            
            # Clean up old logs periodically
            await self._cleanup_old_command_logs()
            
        except Exception as e:
            logger.error(f"Error logging command usage: {e}")

    async def _log_command_error(self, command_name: str, user_id: int, 
                               guild_id: Optional[int], error: Exception, 
                               execution_time: float):
        """Log command error to database"""
        try:
            collection = self.db.db[COLLECTIONS['error_logs']]
            
            error_entry = {
                'command_name': command_name,
                'user_id': str(user_id),
                'guild_id': str(guild_id) if guild_id else None,
                'error_type': type(error).__name__,
                'error_message': str(error)[:LIMITS['max_error_message_length']],
                'execution_time': execution_time,
                'timestamp': datetime.now(),
                'bot_id': str(self.bot.user.id) if self.bot.user else None
            }
            
            await collection.insert_one(error_entry)
            
        except Exception as e:
            logger.error(f"Error logging command error: {e}")

    async def _cleanup_old_command_logs(self):
        """Clean up old command logs based on retention settings"""
        try:
            # Only run cleanup occasionally to avoid performance impact
            if not hasattr(self, '_last_cleanup'):
                self._last_cleanup = 0
            
            current_time = time.time()
            if current_time - self._last_cleanup < 3600:  # Only cleanup once per hour
                return
            
            from datetime import timedelta
            
            # Clean up command logs
            command_cutoff = datetime.now() - timedelta(days=RETENTION_SETTINGS['command_logs_days'])
            command_collection = self.db.db[COLLECTIONS['command_logs']]
            result1 = await command_collection.delete_many({
                'timestamp': {'$lt': command_cutoff}
            })
            
            # Clean up error logs
            error_cutoff = datetime.now() - timedelta(days=RETENTION_SETTINGS['error_logs_days'])
            error_collection = self.db.db[COLLECTIONS['error_logs']]
            result2 = await error_collection.delete_many({
                'timestamp': {'$lt': error_cutoff}
            })
            
            if result1.deleted_count > 0 or result2.deleted_count > 0:
                logger.info(f"Cleaned up {result1.deleted_count} command logs and {result2.deleted_count} error logs")
            
            self._last_cleanup = current_time
            
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")

    def get_command_statistics(self) -> Dict:
        """Get command usage statistics"""
        try:
            # Calculate average execution times
            avg_times = {}
            for command, times in self.command_times.items():
                if times:
                    avg_times[command] = sum(times) / len(times)
            
            # Get recent command counts
            recent_counts = {}
            for cmd_entry in self.recent_commands:
                cmd = cmd_entry['command']
                recent_counts[cmd] = recent_counts.get(cmd, 0) + 1
            
            return {
                'total_tracked': len(self.recent_commands),
                'unique_commands': len(self.command_times),
                'average_execution_times': avg_times,
                'recent_command_counts': recent_counts,
                'top_commands': sorted(recent_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            }
            
        except Exception as e:
            logger.error(f"Error getting command statistics: {e}")
            return {}

    def get_recent_commands(self, limit: int = 50) -> List[Dict]:
        """Get recent command usage"""
        try:
            return self.recent_commands[-limit:] if limit > 0 else self.recent_commands
        except Exception as e:
            logger.error(f"Error getting recent commands: {e}")
            return []

    async def get_top_commands(self, days: int = 7, limit: int = 10) -> List[tuple]:
        """Get top commands from database for specified time period"""
        try:
            from datetime import timedelta
            
            collection = self.db.db[COLLECTIONS['command_logs']]
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Aggregate command usage
            pipeline = [
                {'$match': {'timestamp': {'$gte': cutoff_date}}},
                {'$group': {
                    '_id': '$command_name',
                    'count': {'$sum': 1},
                    'avg_time': {'$avg': '$execution_time'},
                    'success_rate': {
                        '$avg': {'$cond': ['$success', 1, 0]}
                    }
                }},
                {'$sort': {'count': -1}},
                {'$limit': limit}
            ]
            
            results = []
            async for doc in collection.aggregate(pipeline):
                results.append((
                    doc['_id'],
                    doc['count'],
                    round(doc['avg_time'], 3),
                    round(doc['success_rate'], 3)
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting top commands: {e}")
            return []

    async def get_command_analytics(self, command_name: str, days: int = 30) -> Dict:
        """Get detailed analytics for a specific command"""
        try:
            from datetime import timedelta
            
            collection = self.db.db[COLLECTIONS['command_logs']]
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get command usage data
            cursor = collection.find({
                'command_name': command_name,
                'timestamp': {'$gte': cutoff_date}
            })
            
            usage_data = []
            total_executions = 0
            successful_executions = 0
            total_time = 0
            
            async for doc in cursor:
                usage_data.append(doc)
                total_executions += 1
                if doc.get('success', True):
                    successful_executions += 1
                total_time += doc.get('execution_time', 0)
            
            return {
                'command_name': command_name,
                'total_executions': total_executions,
                'successful_executions': successful_executions,
                'success_rate': successful_executions / total_executions if total_executions > 0 else 0,
                'average_execution_time': total_time / total_executions if total_executions > 0 else 0,
                'unique_users': len(set(doc.get('user_id') for doc in usage_data)),
                'unique_guilds': len(set(doc.get('guild_id') for doc in usage_data if doc.get('guild_id'))),
                'time_period_days': days
            }
            
        except Exception as e:
            logger.error(f"Error getting command analytics: {e}")
            return {}
