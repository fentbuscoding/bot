import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os

class CommandUsageTracker:
    """Global command usage tracking with analytics"""
    
    def __init__(self):
        self.usage_stats = defaultdict(lambda: {
            'total_uses': 0,
            'last_used': None,
            'users': set(),
            'guilds': set(),
            'hourly_usage': deque(maxlen=24),  # Last 24 hours
            'daily_usage': deque(maxlen=30),   # Last 30 days
            'errors': 0,
            'avg_execution_time': 0,
            'execution_times': deque(maxlen=100)
        })
        
        self.user_stats = defaultdict(lambda: {
            'total_commands': 0,
            'commands_used': defaultdict(int),
            'first_command': None,
            'last_command': None,
            'favorite_command': None
        })
        
        self.guild_stats = defaultdict(lambda: {
            'total_commands': 0,
            'unique_users': set(),
            'popular_commands': defaultdict(int),
            'peak_usage_hour': 0
        })
        
        self.rate_limits = defaultdict(lambda: deque(maxlen=100))
        self.current_hour = datetime.now().hour
        self.current_day = datetime.now().day
        
        # Load existing data
        self.load_stats()
        
        # Auto-save task (will be started later)
        self._auto_save_task = None
    
    def start_auto_save(self):
        """Start the auto-save loop (call this when event loop is running)"""
        if self._auto_save_task is None:
            try:
                self._auto_save_task = asyncio.create_task(self._auto_save_loop())
            except RuntimeError:
                # No event loop running, will try again later
                pass
    
    def track_command(self, ctx, command_name: str, execution_time: float = 0, error: bool = False):
        """Track command usage"""
        now = datetime.now()
        
        # Update command stats
        cmd_stats = self.usage_stats[command_name]
        cmd_stats['total_uses'] += 1
        cmd_stats['last_used'] = now.isoformat()
        cmd_stats['users'].add(str(ctx.author.id))
        cmd_stats['guilds'].add(str(ctx.guild.id) if ctx.guild else 'DM')
        
        if error:
            cmd_stats['errors'] += 1
        
        if execution_time > 0:
            cmd_stats['execution_times'].append(execution_time)
            # Update average
            times = list(cmd_stats['execution_times'])
            cmd_stats['avg_execution_time'] = sum(times) / len(times)
        
        # Update hourly tracking
        if now.hour != self.current_hour:
            # New hour, rotate
            cmd_stats['hourly_usage'].append({'hour': self.current_hour, 'count': 0})
            self.current_hour = now.hour
        
        if cmd_stats['hourly_usage']:
            cmd_stats['hourly_usage'][-1]['count'] += 1
        else:
            cmd_stats['hourly_usage'].append({'hour': now.hour, 'count': 1})
        
        # Update daily tracking
        if now.day != self.current_day:
            cmd_stats['daily_usage'].append({'day': self.current_day, 'count': 0})
            self.current_day = now.day
        
        if cmd_stats['daily_usage']:
            cmd_stats['daily_usage'][-1]['count'] += 1
        else:
            cmd_stats['daily_usage'].append({'day': now.day, 'count': 1})
        
        # Update user stats
        user_stats = self.user_stats[str(ctx.author.id)]
        user_stats['total_commands'] += 1
        user_stats['commands_used'][command_name] += 1
        user_stats['last_command'] = now.isoformat()
        
        if not user_stats['first_command']:
            user_stats['first_command'] = now.isoformat()
        
        # Update favorite command
        most_used = max(user_stats['commands_used'].items(), key=lambda x: x[1])
        user_stats['favorite_command'] = most_used[0]
        
        # Update guild stats
        if ctx.guild:
            guild_stats = self.guild_stats[str(ctx.guild.id)]
            guild_stats['total_commands'] += 1
            guild_stats['unique_users'].add(str(ctx.author.id))
            guild_stats['popular_commands'][command_name] += 1
    
    def track_rate_limit(self, endpoint: str, retry_after: float):
        """Track rate limit hits"""
        self.rate_limits[endpoint].append({
            'timestamp': datetime.now().isoformat(),
            'retry_after': retry_after
        })
    
    def get_command_stats(self, command_name: str) -> Dict:
        """Get statistics for a specific command"""
        stats = dict(self.usage_stats[command_name])
        # Convert sets to lists for JSON serialization
        stats['users'] = list(stats['users'])
        stats['guilds'] = list(stats['guilds'])
        stats['hourly_usage'] = list(stats['hourly_usage'])
        stats['daily_usage'] = list(stats['daily_usage'])
        stats['execution_times'] = list(stats['execution_times'])
        return stats
    
    def get_top_commands(self, limit: int = 10) -> List[Dict]:
        """Get most used commands"""
        commands = []
        for cmd, stats in self.usage_stats.items():
            commands.append({
                'command': cmd,
                'uses': stats['total_uses'],
                'unique_users': len(stats['users']),
                'unique_guilds': len(stats['guilds']),
                'error_rate': stats['errors'] / max(stats['total_uses'], 1),
                'avg_execution_time': stats['avg_execution_time']
            })
        
        return sorted(commands, key=lambda x: x['uses'], reverse=True)[:limit]
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Get statistics for a specific user"""
        stats = dict(self.user_stats[user_id])
        stats['commands_used'] = dict(stats['commands_used'])
        return stats
    
    def get_guild_stats(self, guild_id: str) -> Dict:
        """Get statistics for a specific guild"""
        stats = dict(self.guild_stats[guild_id])
        stats['unique_users'] = list(stats['unique_users'])
        stats['popular_commands'] = dict(stats['popular_commands'])
        return stats
    
    def get_rate_limit_stats(self) -> Dict:
        """Get rate limiting statistics"""
        stats = {}
        for endpoint, limits in self.rate_limits.items():
            recent_limits = [l for l in limits if 
                           datetime.fromisoformat(l['timestamp']) > datetime.now() - timedelta(hours=24)]
            
            stats[endpoint] = {
                'total_hits': len(limits),
                'recent_hits': len(recent_limits),
                'avg_retry_after': sum(l['retry_after'] for l in recent_limits) / max(len(recent_limits), 1)
            }
        
        return stats
    
    def save_stats(self):
        """Save statistics to file"""
        try:
            os.makedirs('data/analytics', exist_ok=True)
            
            # Convert sets to lists for JSON serialization
            save_data = {
                'usage_stats': {},
                'user_stats': {},
                'guild_stats': {},
                'rate_limits': dict(self.rate_limits)
            }
            
            # Process usage stats
            for cmd, stats in self.usage_stats.items():
                save_data['usage_stats'][cmd] = {
                    'total_uses': stats['total_uses'],
                    'last_used': stats['last_used'],
                    'users': list(stats['users']),
                    'guilds': list(stats['guilds']),
                    'hourly_usage': list(stats['hourly_usage']),
                    'daily_usage': list(stats['daily_usage']),
                    'errors': stats['errors'],
                    'avg_execution_time': stats['avg_execution_time'],
                    'execution_times': list(stats['execution_times'])
                }
            
            # Process user stats
            for user_id, stats in self.user_stats.items():
                save_data['user_stats'][user_id] = {
                    'total_commands': stats['total_commands'],
                    'commands_used': dict(stats['commands_used']),
                    'first_command': stats['first_command'],
                    'last_command': stats['last_command'],
                    'favorite_command': stats['favorite_command']
                }
            
            # Process guild stats
            for guild_id, stats in self.guild_stats.items():
                save_data['guild_stats'][guild_id] = {
                    'total_commands': stats['total_commands'],
                    'unique_users': list(stats['unique_users']),
                    'popular_commands': dict(stats['popular_commands']),
                    'peak_usage_hour': stats['peak_usage_hour']
                }
            
            with open('data/analytics/command_usage.json', 'w') as f:
                json.dump(save_data, f, indent=2)
            
        except Exception as e:
            print(f"Error saving command usage stats: {e}")
    
    def load_stats(self):
        """Load statistics from file"""
        try:
            if not os.path.exists('data/analytics/command_usage.json'):
                return
            
            with open('data/analytics/command_usage.json', 'r') as f:
                data = json.load(f)
            
            # Load usage stats
            for cmd, stats in data.get('usage_stats', {}).items():
                self.usage_stats[cmd].update({
                    'total_uses': stats['total_uses'],
                    'last_used': stats['last_used'],
                    'users': set(stats['users']),
                    'guilds': set(stats['guilds']),
                    'hourly_usage': deque(stats['hourly_usage'], maxlen=24),
                    'daily_usage': deque(stats['daily_usage'], maxlen=30),
                    'errors': stats['errors'],
                    'avg_execution_time': stats['avg_execution_time'],
                    'execution_times': deque(stats['execution_times'], maxlen=100)
                })
            
            # Load user stats
            for user_id, stats in data.get('user_stats', {}).items():
                self.user_stats[user_id].update({
                    'total_commands': stats['total_commands'],
                    'commands_used': defaultdict(int, stats['commands_used']),
                    'first_command': stats['first_command'],
                    'last_command': stats['last_command'],
                    'favorite_command': stats['favorite_command']
                })
            
            # Load guild stats
            for guild_id, stats in data.get('guild_stats', {}).items():
                self.guild_stats[guild_id].update({
                    'total_commands': stats['total_commands'],
                    'unique_users': set(stats['unique_users']),
                    'popular_commands': defaultdict(int, stats['popular_commands']),
                    'peak_usage_hour': stats['peak_usage_hour']
                })
            
            # Load rate limits
            for endpoint, limits in data.get('rate_limits', {}).items():
                self.rate_limits[endpoint] = deque(limits, maxlen=100)
            
        except Exception as e:
            print(f"Error loading command usage stats: {e}")
    
    async def _auto_save_loop(self):
        """Auto-save statistics every 5 minutes"""
        while True:
            await asyncio.sleep(300)  # 5 minutes
            self.save_stats()
    
    def cleanup(self):
        """Cleanup resources and save final stats"""
        if self._auto_save_task:
            self._auto_save_task.cancel()
            self._auto_save_task = None
        self.save_stats()

# Global instance
usage_tracker = CommandUsageTracker()
