import discord
import aiohttp
import logging
import time
import json
from datetime import datetime
from discord.ext import commands, tasks
from typing import Dict, List, Optional
from utils.command_tracker import usage_tracker
from utils.db import AsyncDatabase


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dashboard_url = "https://bronxbot.onrender.com" if not getattr(bot, 'dev_mode', False) else "http://localhost:5000"
        self.dashboard_url = self.dashboard_url.rstrip('/')
        
        # Setup database connection
        self.db = AsyncDatabase.get_instance()
        
        # Stats tracking
        self.start_time = datetime.now()
        self.command_count = 0
        self.daily_commands = 0
        self.command_types = {}
        self.last_stats_update = 0
        
        # Start background tasks
        self.send_stats_task.start()
        self.reset_daily_stats_task.start()
        self.load_stats_task.start()
        
        logging.info("Stats cog initialized")

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.send_stats_task.cancel()
        self.reset_daily_stats_task.cancel()
        self.load_stats_task.cancel()
        # Save stats before unloading
        self.bot.loop.create_task(self.save_stats_to_mongodb())
        logging.info("Stats cog unloaded")
        
    @tasks.loop(hours=1)
    async def load_stats_task(self):
        """Load stats from MongoDB periodically to ensure data consistency"""
        try:
            await self.load_stats_from_mongodb()
            logging.debug("Stats loaded from MongoDB successfully")
        except Exception as e:
            logging.error(f"Error loading stats from MongoDB: {e}")
    
    @load_stats_task.before_loop
    async def before_load_stats_task(self):
        """Wait until the bot is ready before loading stats"""
        await self.bot.wait_until_ready()
        # Initial load of stats
        await self.load_stats_from_mongodb()

    async def load_stats_from_mongodb(self):
        """Load stats from MongoDB"""
        if not await self.db.ensure_connected():
            logging.error("Failed to connect to MongoDB for stats loading")
            return
            
        try:
            # Load global stats document
            stats_doc = await self.db.db.bot_stats.find_one({"_id": "global_stats"})
            if stats_doc:
                self.command_count = stats_doc.get("command_count", 0)
                self.daily_commands = stats_doc.get("daily_commands", 0)
                self.command_types = stats_doc.get("command_types", {})
                self.last_stats_update = stats_doc.get("last_update", 0)
                logging.info(f"Loaded stats from MongoDB: {self.command_count} commands")
            else:
                logging.info("No stats found in MongoDB, using default values")
        except Exception as e:
            logging.error(f"Error loading stats from MongoDB: {e}")
            
    async def save_stats_to_mongodb(self):
        """Save stats to MongoDB"""
        if not await self.db.ensure_connected():
            logging.error("Failed to connect to MongoDB for stats saving")
            return False
            
        try:
            # Prepare stats document
            stats_doc = {
                "command_count": self.command_count,
                "daily_commands": self.daily_commands,
                "command_types": self.command_types,
                "last_update": time.time(),
                "updated_at": datetime.now()
            }
            
            # Update or insert the global stats document
            result = await self.db.db.bot_stats.update_one(
                {"_id": "global_stats"},
                {"$set": stats_doc},
                upsert=True
            )
            
            success = result.modified_count > 0 or result.upserted_id is not None
            if success:
                logging.debug("Stats saved to MongoDB successfully")
            else:
                logging.warning("Failed to save stats to MongoDB")
                
            return success
        except Exception as e:
            logging.error(f"Error saving stats to MongoDB: {e}")
            return False

    @tasks.loop(minutes=5)
    async def send_stats_task(self):
        """Send comprehensive stats to dashboard every 5 minutes"""
        try:
            await self.send_comprehensive_stats()
            # Save stats to MongoDB after sending to dashboard
            await self.save_stats_to_mongodb()
        except Exception as e:
            logging.error(f"Error in stats update task: {e}")

    @send_stats_task.before_loop
    async def before_send_stats_task(self):
        """Wait until the bot is ready before starting the stats update loop"""
        await self.bot.wait_until_ready()

    @tasks.loop(hours=24)
    async def reset_daily_stats_task(self):
        """Reset daily command count at midnight"""
        try:
            self.daily_commands = 0
            await self.save_stats_to_mongodb()
            logging.info("Daily stats reset completed")
        except Exception as e:
            logging.error(f"Error resetting daily stats: {e}")

    @reset_daily_stats_task.before_loop
    async def before_reset_daily_stats_task(self):
        """Wait until the bot is ready before starting the daily reset loop"""
        await self.bot.wait_until_ready()

    async def send_comprehensive_stats(self):
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
                        "member_count": guild.member_count or 0
                    } for guild in self.bot.guilds
                ]
            },
            "performance": {
                "user_count": sum(guild.member_count or 0 for guild in self.bot.guilds),
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
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.dashboard_url}/api/stats",
                    json=stats,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        logging.debug("✅ Comprehensive stats sent to dashboard successfully")
                        self.last_stats_update = time.time()
                    else:
                        logging.warning(f"❌ Failed to send comprehensive stats: {response.status}")
        except Exception as e:
            logging.error(f"❌ Error sending comprehensive stats: {e}")

    async def send_realtime_command_update(self, command_name: str, user_id: int, guild_id: Optional[int] = None, 
                                         execution_time: float = 0, error: bool = False):
        """Send real-time command execution update to dashboard"""
        # Update internal counters
        self.command_count += 1
        self.daily_commands += 1
        self.command_types[command_name] = self.command_types.get(command_name, 0) + 1
        
        # Save stats to MongoDB periodically (not on every command to avoid excessive DB writes)
        # Using a threshold of every 10 commands or when specific commands are used
        if self.command_count % 10 == 0 or command_name in ['help', 'stats', 'invite']:
            await self.save_stats_to_mongodb()
        
        # Prepare update data
        update_data = {
            'type': 'command_update',
            'command': command_name,
            'user_id': str(user_id),
            'guild_id': str(guild_id) if guild_id else None,
            'execution_time': execution_time,
            'error': error,
            'timestamp': time.time(),
            'total_commands': self.command_count
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.dashboard_url}/api/stats/realtime",
                    json=update_data,
                    timeout=5
                ) as response:
                    if response.status == 200:
                        logging.debug("✅ Real-time command update sent successfully")
                    else:
                        logging.debug(f"❌ Failed to send real-time update: {response.status}")
        except Exception as e:
            logging.debug(f"❌ Error sending real-time command update: {e}")

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        """Handle successful command completion"""
        execution_time = time.time() - getattr(ctx, 'command_start_time', time.time())
        command_name = ctx.command.qualified_name
        
        # Track with usage tracker (existing system)
        usage_tracker.track_command(ctx, command_name, execution_time, error=False)
        
        # Send real-time update to dashboard
        await self.send_realtime_command_update(
            command_name=command_name,
            user_id=ctx.author.id,
            guild_id=ctx.guild.id if ctx.guild else None,
            execution_time=execution_time,
            error=False
        )

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle command errors for stats tracking"""
        execution_time = time.time() - getattr(ctx, 'command_start_time', time.time())
        command_name = ctx.command.qualified_name if ctx.command else 'unknown'
        
        # Track with usage tracker (existing system)
        usage_tracker.track_command(ctx, command_name, execution_time, error=True)
        
        # Send real-time error update to dashboard
        await self.send_realtime_command_update(
            command_name=command_name,
            user_id=ctx.author.id,
            guild_id=ctx.guild.id if ctx.guild else None,
            execution_time=execution_time,
            error=True
        )

    @commands.command(name='statstatus', aliases=['statsinfo'])
    @commands.is_owner()
    async def stats_status(self, ctx):
        """Show current stats status and information"""
        uptime = datetime.now() - self.start_time
        last_update_ago = time.time() - self.last_stats_update if self.last_stats_update else None
        
        embed = discord.Embed(
            title="📊 Stats Cog Status",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📈 Current Stats",
            value=f"**Commands Executed:** {self.command_count:,}\n"
                  f"**Daily Commands:** {self.daily_commands:,}\n"
                  f"**Unique Commands:** {len(self.command_types)}",
            inline=True
        )
        
        embed.add_field(
            name="⏱️ Timing",
            value=f"**Uptime:** {uptime.days}d {uptime.seconds//3600}h {(uptime.seconds%3600)//60}m\n"
                  f"**Last Update:** {f'{last_update_ago:.1f}s ago' if last_update_ago else 'Never'}",
            inline=True
        )
        
        embed.add_field(
            name="🔧 Configuration",
            value=f"**Dashboard URL:** {self.dashboard_url}\n"
                  f"**Update Interval:** 5 minutes\n"
                  f"**MongoDB Storage:** Enabled\n"
                  f"**Tasks Running:** {self.send_stats_task.is_running()}",
            inline=False
        )
        
        # Top 5 commands
        if self.command_types:
            top_commands = sorted(self.command_types.items(), key=lambda x: x[1], reverse=True)[:5]
            top_commands_str = "\n".join([f"`{cmd}`: {count}" for cmd, count in top_commands])
            embed.add_field(
                name="🏆 Top Commands",
                value=top_commands_str,
                inline=False
            )
        
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)

    @commands.command(name='forcestatsupdate', aliases=['updatestats'])
    @commands.is_owner()
    async def force_stats_update(self, ctx):
        """Force an immediate stats update to dashboard"""
        await ctx.send("🔄 Sending stats update...")
        
        try:
            # Update dashboard
            await self.send_comprehensive_stats()
            # Save to MongoDB
            mongo_success = await self.save_stats_to_mongodb()
            
            if mongo_success:
                await ctx.send("✅ Stats update sent to dashboard and saved to MongoDB successfully!")
            else:
                await ctx.send("⚠️ Stats update sent to dashboard but MongoDB save failed.")
        except Exception as e:
            await ctx.send(f"❌ Failed to send stats update: {e}")

    @commands.command(name='resetstats')
    @commands.is_owner()
    async def reset_stats(self, ctx):
        """Reset internal stats counters (use with caution)"""
        confirm_msg = await ctx.send("⚠️ This will reset all internal stats counters. React with ✅ to confirm.")
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "✅":
                self.command_count = 0
                self.daily_commands = 0
                self.command_types = {}
                self.start_time = datetime.now()
                
                # Save reset stats to MongoDB
                await self.save_stats_to_mongodb()
                await ctx.send("✅ Stats counters have been reset and saved to MongoDB.")
            else:
                await ctx.send("❌ Stats reset cancelled.")
                
        except TimeoutError:
            await ctx.send("⏰ Stats reset timed out.")

    def get_stats_summary(self) -> Dict:
        """Get a summary of current stats"""
        uptime = datetime.now() - self.start_time
        
        return {
            "command_count": self.command_count,
            "daily_commands": self.daily_commands,
            "unique_commands": len(self.command_types),
            "uptime_seconds": uptime.total_seconds(),
            "top_commands": dict(sorted(self.command_types.items(), key=lambda x: x[1], reverse=True)[:10]),
            "last_update": self.last_stats_update
        }


async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(Stats(bot))
    logging.info("Stats cog loaded successfully")
