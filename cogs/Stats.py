import discord
import aiohttp
import logging
import time
import json
import psutil
import os
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
        self.send_performance_update_task.start()
        self.reset_daily_stats_task.start()
        self.load_stats_task.start()
        
        logging.info("Stats cog initialized")

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.send_stats_task.cancel()
        self.send_performance_update_task.cancel()
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
                
                # Load uptime start if available, otherwise use current time
                if "uptime_start" in stats_doc:
                    self.start_time = datetime.fromtimestamp(stats_doc["uptime_start"])
                
                logging.info(f"Loaded stats from MongoDB: {self.command_count} commands, {len(self.command_types)} unique commands")
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
            # Get system performance metrics
            try:
                process = psutil.Process(os.getpid())
                memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                cpu_usage = process.cpu_percent()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                memory_usage = 0
                cpu_usage = 0
            
            # Calculate total user count
            total_users = sum(guild.member_count or 0 for guild in self.bot.guilds)
            
            # Get detailed guild information
            guild_details = []
            guild_basic_list = []
            for guild in self.bot.guilds:
                try:
                    basic_info = {
                        "id": str(guild.id),
                        "name": guild.name,
                        "member_count": guild.member_count or 0
                    }
                    guild_basic_list.append(basic_info)
                    
                    detailed_info = {
                        "id": str(guild.id),
                        "name": guild.name,
                        "member_count": guild.member_count or 0,
                        "owner_id": str(guild.owner_id) if guild.owner_id else None,
                        "created_at": guild.created_at.isoformat() if guild.created_at else None,
                        "features": list(guild.features) if guild.features else [],
                        "verification_level": str(guild.verification_level) if guild.verification_level else "none",
                        "premium_tier": guild.premium_tier if hasattr(guild, 'premium_tier') else 0,
                        "premium_subscription_count": guild.premium_subscription_count if hasattr(guild, 'premium_subscription_count') else 0,
                        "large": guild.large if hasattr(guild, 'large') else False,
                        "icon": guild.icon.url if guild.icon else None,
                        "banner": guild.banner.url if guild.banner else None,
                        "description": guild.description,
                        "region": str(guild.preferred_locale) if hasattr(guild, 'preferred_locale') else None,
                        "channels_count": len(guild.channels) if guild.channels else 0,
                        "roles_count": len(guild.roles) if guild.roles else 0,
                        "emojis_count": len(guild.emojis) if guild.emojis else 0,
                        "joined_at": guild.me.joined_at.isoformat() if guild.me and guild.me.joined_at else None,
                        "permissions": guild.me.guild_permissions.value if guild.me else 0,
                        "last_updated": datetime.now().isoformat()
                    }
                    guild_details.append(detailed_info)
                except Exception as e:
                    logging.warning(f"Error getting details for guild {guild.id}: {e}")
                    basic_info = {
                        "id": str(guild.id),
                        "name": getattr(guild, 'name', 'Unknown'),
                        "member_count": getattr(guild, 'member_count', 0) or 0
                    }
                    guild_basic_list.append(basic_info)
                    guild_details.append(basic_info)
            
            # Prepare comprehensive stats document
            stats_doc = {
                "command_count": self.command_count,
                "daily_commands": self.daily_commands,
                "command_types": self.command_types,
                "last_update": time.time(),
                "updated_at": datetime.now(),
                
                # Performance metrics
                "user_count": total_users,
                "latency": round(self.bot.latency * 1000, 2),
                "shard_count": self.bot.shard_count or 1,
                "memory_usage": round(memory_usage, 2),
                "cpu_usage": round(cpu_usage, 2),
                "cached_users": len(self.bot.users),
                
                # Guild information - comprehensive
                "guild_count": len(self.bot.guilds),
                "guild_list": [str(guild.id) for guild in self.bot.guilds],
                "guild_details": guild_details,  # Full detailed information
                "guild_basic": guild_basic_list,  # Basic information for quick access
                
                # Guild statistics
                "largest_guild": max(guild_details, key=lambda g: g.get('member_count', 0)) if guild_details else None,
                "total_channels": sum(g.get('channels_count', 0) for g in guild_details),
                "total_roles": sum(g.get('roles_count', 0) for g in guild_details),
                "total_emojis": sum(g.get('emojis_count', 0) for g in guild_details),
                "premium_guilds": len([g for g in guild_details if g.get('premium_tier', 0) > 0]),
                "large_guilds": len([g for g in guild_details if g.get('large', False)]),
                
                # Uptime information
                "uptime_start": self.start_time.timestamp(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                
                # System information
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
                "discord_py_version": discord.__version__,
                "platform": os.name,
                "process_id": os.getpid()
            }
            
            # Update or insert the global stats document
            result = await self.db.db.bot_stats.update_one(
                {"_id": "global_stats"},
                {"$set": stats_doc},
                upsert=True
            )
            
            # Also save individual guild documents for detailed tracking
            try:
                for guild_info in guild_details:
                    await self.db.db.guild_cache.update_one(
                        {"_id": guild_info["id"]},
                        {"$set": {
                            **guild_info,
                            "bot_joined_at": guild_info.get("joined_at"),
                            "last_seen": datetime.now().isoformat(),
                            "is_active": True
                        }},
                        upsert=True
                    )
                
                # Mark guilds we're no longer in as inactive
                current_guild_ids = [g["id"] for g in guild_details]
                await self.db.db.guild_cache.update_many(
                    {"_id": {"$nin": current_guild_ids}, "is_active": True},
                    {"$set": {
                        "is_active": False,
                        "left_at": datetime.now().isoformat()
                    }}
                )
                
                logging.debug(f"Updated {len(guild_details)} guild cache entries")
            except Exception as e:
                logging.error(f"Error updating guild cache: {e}")
            
            success = result.modified_count > 0 or result.upserted_id is not None
            if success:
                logging.debug("Stats and guild data saved to MongoDB successfully")
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

    @tasks.loop(minutes=1)
    async def send_performance_update_task(self):
        """Send performance metrics update every minute for real-time monitoring"""
        try:
            await self.send_performance_update()
        except Exception as e:
            logging.debug(f"Error in performance update task: {e}")

    @send_performance_update_task.before_loop
    async def before_send_performance_update_task(self):
        """Wait until the bot is ready before starting the performance update loop"""
        await self.bot.wait_until_ready()

    async def send_performance_update(self):
        """Send lightweight performance update to dashboard"""
        try:
            process = psutil.Process(os.getpid())
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            cpu_usage = process.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            memory_usage = 0
            cpu_usage = 0
        
        performance_data = {
            "type": "performance_update",
            "latency": round(self.bot.latency * 1000, 2),
            "memory_usage": round(memory_usage, 2),
            "cpu_usage": round(cpu_usage, 2),
            "guild_count": len(self.bot.guilds),
            "user_count": sum(guild.member_count or 0 for guild in self.bot.guilds),
            "cached_users": len(self.bot.users),
            "timestamp": time.time()
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.dashboard_url}/api/stats/performance",
                    json=performance_data,
                    timeout=5
                ) as response:
                    if response.status == 200:
                        logging.debug("✅ Performance update sent successfully")
                    else:
                        logging.debug(f"❌ Failed to send performance update: {response.status}")
        except Exception as e:
            logging.debug(f"❌ Error sending performance update: {e}")

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
        
        # Get system performance metrics
        try:
            process = psutil.Process(os.getpid())
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            cpu_usage = process.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            memory_usage = 0
            cpu_usage = 0
        
        # Calculate total user count across all guilds
        total_users = sum(guild.member_count or 0 for guild in self.bot.guilds)
        
        # Get detailed guild information
        guild_details = []
        for guild in self.bot.guilds:
            try:
                guild_details.append({
                    "id": str(guild.id),
                    "name": guild.name,
                    "member_count": guild.member_count or 0,
                    "owner_id": str(guild.owner_id) if guild.owner_id else None,
                    "created_at": guild.created_at.isoformat() if guild.created_at else None,
                    "features": list(guild.features) if guild.features else [],
                    "verification_level": str(guild.verification_level) if guild.verification_level else "none",
                    "premium_tier": guild.premium_tier if hasattr(guild, 'premium_tier') else 0
                })
            except Exception as e:
                logging.warning(f"Error getting details for guild {guild.id}: {e}")
                guild_details.append({
                    "id": str(guild.id),
                    "name": getattr(guild, 'name', 'Unknown'),
                    "member_count": getattr(guild, 'member_count', 0) or 0
                })
        
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
                "detailed": guild_details
            },
            "performance": {
                "user_count": total_users,
                "latency": round(self.bot.latency * 1000, 2),  # Convert to milliseconds
                "shard_count": self.bot.shard_count or 1,
                "memory_usage": round(memory_usage, 2),
                "cpu_usage": round(cpu_usage, 2),
                "cached_users": len(self.bot.users),
                "cached_messages": getattr(self.bot, '_connection', {}).get('_messages', {}) and len(getattr(self.bot._connection, '_messages', {})) or 0
            },
            "commands": {
                "total_executed": self.command_count,
                "daily_count": self.daily_commands,
                "command_types": self.command_types.copy()
            },
            "system": {
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
                "discord_py_version": discord.__version__,
                "platform": os.name,
                "process_id": os.getpid()
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
                        
                        # Also save to MongoDB after successful dashboard update
                        await self.save_stats_to_mongodb()
                    else:
                        response_text = await response.text()
                        logging.warning(f"❌ Failed to send comprehensive stats: {response.status} - {response_text}")
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
        
        # Get system metrics
        try:
            process = psutil.Process(os.getpid())
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            cpu_usage = process.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            memory_usage = 0
            cpu_usage = 0
        
        total_users = sum(guild.member_count or 0 for guild in self.bot.guilds)
        
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
            name="🌐 Bot Performance",
            value=f"**Guilds:** {len(self.bot.guilds):,}\n"
                  f"**Users:** {total_users:,}\n"
                  f"**Latency:** {round(self.bot.latency * 1000, 2)}ms",
            inline=True
        )
        
        embed.add_field(
            name="💻 System Performance",
            value=f"**Memory Usage:** {memory_usage:.1f} MB\n"
                  f"**CPU Usage:** {cpu_usage:.1f}%\n"
                  f"**Shards:** {self.bot.shard_count or 1}",
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
            inline=True
        )
        
        embed.add_field(
            name="📋 System Info",
            value=f"**Python:** {os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}\n"
                  f"**Discord.py:** {discord.__version__}\n"
                  f"**Platform:** {os.name}",
            inline=True
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
            # Update dashboard with comprehensive stats
            await self.send_comprehensive_stats()
            # Send performance update as well
            await self.send_performance_update()
            # Save to MongoDB
            mongo_success = await self.save_stats_to_mongodb()
            
            if mongo_success:
                await ctx.send("✅ Stats update sent to dashboard and saved to MongoDB successfully!")
            else:
                await ctx.send("⚠️ Stats update sent to dashboard but MongoDB save failed.")
        except Exception as e:
            await ctx.send(f"❌ Failed to send stats update: {e}")

    @commands.command(name='testperformance', aliases=['perftest'])
    @commands.is_owner()
    async def test_performance_update(self, ctx):
        """Test performance metrics update"""
        await ctx.send("🔄 Testing performance update...")
        
        try:
            await self.send_performance_update()
            await ctx.send("✅ Performance update sent successfully!")
        except Exception as e:
            await ctx.send(f"❌ Failed to send performance update: {e}")

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

    @commands.command(name='guildstats', aliases=['serverstats'])
    @commands.is_owner()
    async def guild_stats(self, ctx):
        """Show comprehensive guild statistics"""
        guild_count = len(self.bot.guilds)
        total_users = sum(guild.member_count or 0 for guild in self.bot.guilds)
        
        # Calculate guild statistics
        large_guilds = len([g for g in self.bot.guilds if getattr(g, 'large', False)])
        premium_guilds = len([g for g in self.bot.guilds if getattr(g, 'premium_tier', 0) > 0])
        
        # Find largest and smallest guilds
        guilds_with_members = [(g.name, g.member_count or 0) for g in self.bot.guilds if g.member_count]
        largest_guild = max(guilds_with_members, key=lambda x: x[1]) if guilds_with_members else ("None", 0)
        smallest_guild = min(guilds_with_members, key=lambda x: x[1]) if guilds_with_members else ("None", 0)
        
        embed = discord.Embed(
            title="🏰 Guild Statistics",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="📊 Overview",
            value=f"**Total Guilds:** {guild_count:,}\n"
                  f"**Total Users:** {total_users:,}\n"
                  f"**Average Users/Guild:** {total_users // guild_count if guild_count > 0 else 0:,}",
            inline=True
        )
        
        embed.add_field(
            name="🏆 Guild Types",
            value=f"**Large Guilds:** {large_guilds:,}\n"
                  f"**Premium Guilds:** {premium_guilds:,}\n"
                  f"**Regular Guilds:** {guild_count - large_guilds - premium_guilds:,}",
            inline=True
        )
        
        embed.add_field(
            name="📈 Size Range",
            value=f"**Largest:** {largest_guild[0][:20]}{'...' if len(largest_guild[0]) > 20 else ''} ({largest_guild[1]:,})\n"
                  f"**Smallest:** {smallest_guild[0][:20]}{'...' if len(smallest_guild[0]) > 20 else ''} ({smallest_guild[1]:,})",
            inline=False
        )
        
        # Guild distribution by size
        size_ranges = {
            "Tiny (1-50)": len([g for g in self.bot.guilds if 1 <= (g.member_count or 0) <= 50]),
            "Small (51-200)": len([g for g in self.bot.guilds if 51 <= (g.member_count or 0) <= 200]),
            "Medium (201-1000)": len([g for g in self.bot.guilds if 201 <= (g.member_count or 0) <= 1000]),
            "Large (1001+)": len([g for g in self.bot.guilds if (g.member_count or 0) > 1000])
        }
        
        size_distribution = "\n".join([f"**{size}:** {count}" for size, count in size_ranges.items() if count > 0])
        embed.add_field(
            name="📏 Size Distribution",
            value=size_distribution or "No data available",
            inline=False
        )
        
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)

    @commands.command(name='guildlist', aliases=['serverlist'])
    @commands.is_owner()
    async def guild_list(self, ctx, page: int = 1):
        """Show paginated list of guilds with details"""
        guilds_per_page = 10
        guild_list = sorted(self.bot.guilds, key=lambda g: g.member_count or 0, reverse=True)
        total_pages = (len(guild_list) + guilds_per_page - 1) // guilds_per_page
        
        if page < 1 or page > total_pages:
            await ctx.send(f"❌ Invalid page number. Pages available: 1-{total_pages}")
            return
        
        start_idx = (page - 1) * guilds_per_page
        end_idx = start_idx + guilds_per_page
        page_guilds = guild_list[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"🏰 Guild List (Page {page}/{total_pages})",
            color=discord.Color.blue()
        )
        
        for i, guild in enumerate(page_guilds, start=start_idx + 1):
            premium_indicator = "👑" if getattr(guild, 'premium_tier', 0) > 0 else ""
            large_indicator = "🏢" if getattr(guild, 'large', False) else ""
            
            embed.add_field(
                name=f"{i}. {guild.name} {premium_indicator}{large_indicator}",
                value=f"**ID:** `{guild.id}`\n"
                      f"**Members:** {guild.member_count or 0:,}\n"
                      f"**Owner:** <@{guild.owner_id}>" if guild.owner_id else "Unknown",
                inline=True
            )
        
        embed.set_footer(text=f"Total: {len(guild_list)} guilds • Use .guildlist <page> to navigate")
        await ctx.send(embed=embed)

    @commands.command(name='guildinfo', aliases=['server'])
    @commands.is_owner()
    async def guild_info(self, ctx, *, guild_query: str):
        """Get detailed information about a specific guild"""
        # Try to find guild by ID first, then by name
        guild = None
        if guild_query.isdigit():
            guild = self.bot.get_guild(int(guild_query))
        
        if not guild:
            # Search by name (case insensitive)
            guild = discord.utils.find(
                lambda g: guild_query.lower() in g.name.lower(),
                self.bot.guilds
            )
        
        if not guild:
            await ctx.send(f"❌ Guild not found: `{guild_query}`")
            return
        
        embed = discord.Embed(
            title=f"{guild.name}",
            color=discord.Color.green()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(
            name="Basic Info",
            value=f"**ID:** `{guild.id}`\n"
                  f"**Owner:** <@{guild.owner_id}>\n"
                  f"**Created:** <t:{int(guild.created_at.timestamp())}:R>\n"
                  f"**Joined:** <t:{int(guild.me.joined_at.timestamp())}:R>" if guild.me.joined_at else "Unknown",
            inline=True
        )
        
        embed.add_field(
            name="Members & Channels",
            value=f"**Members:** {guild.member_count or 0:,}\n"
                  f"**Channels:** {len(guild.channels):,}\n"
                  f"**Roles:** {len(guild.roles):,}\n"
                  f"**Emojis:** {len(guild.emojis):,}",
            inline=True
        )
        
        embed.add_field(
            name="Features",
            value=f"**Verification:** {guild.verification_level}\n"
                  f"**Premium Tier:** {guild.premium_tier if hasattr(guild, 'premium_tier') else 0}\n"
                  f"**Large Guild:** {'Yes' if getattr(guild, 'large', False) else 'No'}\n"
                  f"**Features:** {len(guild.features)} special",
            inline=True
        )
        
        if guild.description:
            embed.add_field(
                name="Description",
                value=guild.description[:500] + ("..." if len(guild.description) > 500 else ""),
                inline=False
            )
        
        if guild.features:
            features_str = ", ".join(guild.features[:10])
            if len(guild.features) > 10:
                features_str += f" (+{len(guild.features) - 10} more)"
            embed.add_field(
                name="Special Features",
                value=f"`{features_str}`",
                inline=False
            )
        
        # Bot permissions in the guild
        if guild.me:
            perms = guild.me.guild_permissions
            important_perms = []
            if perms.administrator:
                important_perms.append("Administrator")
            if perms.manage_guild:
                important_perms.append("Manage Server")
            if perms.manage_channels:
                important_perms.append("Manage Channels")
            if perms.kick_members:
                important_perms.append("Kick Members")
            if perms.ban_members:
                important_perms.append("Ban Members")
            
            embed.add_field(
                name="🔐 Bot Permissions",
                value=", ".join(important_perms[:5]) if important_perms else "Basic permissions",
                inline=False
            )
        
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)

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
