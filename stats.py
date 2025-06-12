# Note: Stats functions are split across two files (stats.py and statFuncs.py) to avoid circular imports(start avoiding circular imports NOW to save future self time)

from imports import *

# Set up logging
logging.basicConfig(level=logging.INFO)

class StatsTracker:
    def __init__(self, bot, dashboard_url):
        self.bot = bot
        self.dashboard_url = dashboard_url.rstrip('/')
        self.start_time = datetime.now()
        self.command_count = 0
        self.daily_commands = 0
        self.command_types = {}
        
    async def send_stats(self):
        """Send comprehensive stats to dashboard"""
        uptime = datetime.now() - self.start_time
        
        stats = {
            "uptime": {
                "days": uptime.days,
                "hours": uptime.seconds // 3600,
                "minutes": (uptime.seconds % 3600) // 60,
                "total_seconds": uptime.total_seconds(),
                "start_time": self.start_time.timestamp()
            },
            "guilds": {
                "count": len(self.bot.guilds),
                "list": [str(guild.id) for guild in self.bot.guilds],
                "detailed": [
                    {
                        "id": str(guild.id),
                        "name": guild.name,
                        "member_count": guild.member_count
                    } for guild in self.bot.guilds
                ]
            },
            "performance": {
                "user_count": sum(guild.member_count for guild in self.bot.guilds if guild.member_count),
                "latency": round(self.bot.latency * 1000, 2),
                "shard_count": self.bot.shard_count or 1
            },
            "commands": {
                "total_executed": self.command_count,
                "daily_count": self.daily_commands,
                "command_types": self.command_types.copy()
            }
        }
        
        try:
            # Use aiohttp for async HTTP requests
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.dashboard_url}/api/stats",
                    json=stats,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        logging.debug("✅ Stats sent to dashboard successfully")
                    else:
                        logging.warning(f"❌ Failed to send stats: {response.status}")
        except Exception as e:
            logging.error(f"❌ Error sending stats: {e}")
    
    async def send_command_update(self, command_name):
        """Send real-time command execution update"""
        self.command_count += 1
        self.daily_commands += 1
        self.command_types[command_name] = self.command_types.get(command_name, 0) + 1
        
        update = {
            "type": "command_executed",
            "command": command_name,
            "total_commands": self.command_count,
            "timestamp": time.time()
        }
        
        try:
            # Use aiohttp for async HTTP requests
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.dashboard_url}/api/stats/realtime",
                    json=update,
                    timeout=5
                ) as response:
                    if response.status != 200:
                        logging.debug(f"Failed to send real-time update: {response.status}")
        except Exception as e:
            logging.debug(f"Failed to send real-time update: {e}")
        