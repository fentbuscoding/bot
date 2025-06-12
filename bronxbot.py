import discord
import json
import random
import time
import sys
import os
import asyncio
import aiohttp
import traceback
import signal
import atexit
from discord.ext import commands, tasks
from typing import Dict, List, Tuple
from os import system
import logging
from utils.command_tracker import usage_tracker
from utils.tos_handler import check_tos_acceptance, prompt_tos_acceptance
from utils.scalability import initialize_scalability

# Set up logging
logging.basicConfig(level=logging.INFO)

def cleanup_resources():
    """Cleanup resources on shutdown"""
    try:
        if hasattr(bot, 'scalability_manager') and bot.scalability_manager:
            asyncio.create_task(bot.scalability_manager.cleanup())
            logging.info("Scalability manager cleanup initiated")
    except:
        pass
    
    try:
        usage_tracker.cleanup()
        logging.info("Command tracker cleanup completed")
    except:
        pass
    
    logging.info("Resource cleanup completed")

# Register cleanup handler
atexit.register(cleanup_resources)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logging.info(f"Received signal {signum}, shutting down gracefully...")
    cleanup_resources()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# config
with open("data/config.json", "r") as f:
    config = json.load(f)

dev = config.get('DEV', False)  # Check if running in development mode

# List of guilds that have access to all features
MAIN_GUILD_IDS = [
    1259717095382319215,  # Main server
    1299747094449623111,  # South Bronx
    1142088882222022786   # Long Island
]

# setup
intents = discord.Intents.all()
intents.message_content = True  # Enable message content intent

class BronxBot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        self.boot_metrics = {
            'start_time': time.time(),
            'config_load_time': 0,
            'cog_load_times': {},
            'total_cog_load_time': 0,
            'guild_cache_time': 0,
            'total_boot_time': 0,
            'ready_time': 0
        }
        
        config_start = time.time()
        super().__init__(*args, **kwargs)
        self.boot_metrics['config_load_time'] = time.time() - config_start
        
        self.start_time = time.time()
        self.cog_load_times = {}
        self.restart_channel = None
        self.restart_message = None
        self.MAIN_GUILD_IDS = MAIN_GUILD_IDS
        self.guild_list = []  # Add this line to store guild IDs

    async def load_cog_with_timing(self, cog_name: str) -> Tuple[bool, float]:
        """Load a cog and measure its loading time"""
        start_time = time.time()
        try:
            await self.load_extension(cog_name)
            load_time = time.time() - start_time
            self.cog_load_times[cog_name] = load_time
            return True, load_time
        except Exception as e:
            load_time = time.time() - start_time
            self.cog_load_times[cog_name] = load_time
            return False, load_time

    @tasks.loop(seconds=10)  # More frequent updates for better real-time feel
    async def update_stats(self):
        """Update bot stats and send to dashboard"""
        try:
            # Calculate uptime
            current_time = time.time()
            uptime_seconds = int(current_time - self.start_time)
            uptime_days = uptime_seconds // 86400
            uptime_hours = (uptime_seconds % 86400) // 3600
            uptime_minutes = (uptime_seconds % 3600) // 60
            
            # Get command metrics from tracker if available
            command_stats = {}
            daily_commands = 0
            total_commands = 0
            session_stats = {}
            
            try:
                # Try to get command stats from tracker
                if hasattr(usage_tracker, 'get_daily_stats'):
                    daily_commands = usage_tracker.get_daily_stats()
                if hasattr(usage_tracker, 'get_total_commands'):
                    total_commands = usage_tracker.get_total_commands()
                if hasattr(usage_tracker, 'get_command_breakdown'):
                    command_stats = usage_tracker.get_command_breakdown()
                if hasattr(usage_tracker, 'get_session_stats'):
                    session_stats = usage_tracker.get_session_stats()
            except:
                pass
            
            stats = {
                'uptime': {
                    'days': uptime_days,
                    'hours': uptime_hours,
                    'minutes': uptime_minutes,
                    'total_seconds': uptime_seconds,
                    'start_time': self.start_time
                },
                'guilds': {
                    'count': len(self.guilds),
                    'list': [str(g.id) for g in self.guilds],
                    'detailed': [
                        {
                            'id': str(g.id),
                            'name': g.name,
                            'member_count': g.member_count or 0
                        } for g in self.guilds
                    ]
                },
                'commands': {
                    'daily_count': daily_commands,
                    'total_executed': total_commands,
                    'command_types': command_stats,
                    'session': session_stats
                },
                'performance': {
                    'latency': round(self.latency * 1000, 2),
                    'user_count': sum((g.member_count or 0) for g in self.guilds),
                    'shard_count': self.shard_count or 1
                },
                'timestamp': current_time
            }
            
            # Store stats based on environment
            if dev:
                # Development: Store in JSON file
                with open('data/stats.json', 'w') as f:
                    json.dump(stats, f, indent=2)
                logging.debug("Stats saved to local JSON file")
            else:
                # Production: Send to database via dashboard API
                async with aiohttp.ClientSession() as session:
                    dashboard_urls = ['https://bronxbot.onrender.com/api/stats/update']
                    
                    for url in dashboard_urls:
                        try:
                            async with session.post(url, json=stats, timeout=10) as resp:
                                if resp.status == 200:
                                    result = await resp.json()
                                    logging.debug(f"Stats updated successfully to {url}")
                                else:
                                    error_text = await resp.text()
                                    logging.warning(f"Failed to update stats to {url}: {resp.status} - {error_text}")
                                    
                        except asyncio.TimeoutError:
                            logging.warning(f"Timeout updating stats to {url}")
                        except Exception as e:
                            logging.error(f"Error updating stats to {url}: {e}")
            
            # Always try to update localhost if available (for development testing)
            if dev:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post('http://localhost:5000/api/stats/update', 
                                              json=stats, timeout=5) as resp:
                            if resp.status == 200:
                                logging.debug("Stats updated to localhost dashboard")
                except:
                    pass  # Localhost might not be running
                        
        except Exception as e:
            logging.error(f"Error in update_stats loop: {e}")
            import traceback
            traceback.print_exc()

    @update_stats.before_loop
    async def before_update_stats(self):
        """Wait until the bot is ready before starting the stats update loop"""
        await self.wait_until_ready()

    @tasks.loop(minutes=5)  # Check every 5 minutes, no need to do it as frequently as stats
    async def update_guilds(self):
        """Update guild list for the web interface"""
        try:
            self.guild_list = [str(g.id) for g in self.guilds]
            
            async with aiohttp.ClientSession() as session:
                async with session.post('https://bronxbot.onrender.com/api/stats', 
                                      json={'guilds': self.guild_list}) as resp:
                    if resp.status != 200:
                        print(f"Failed to update guild list: {resp.status}")
        except Exception as e:
            print(f"Error updating guild list: {e}")

    @update_guilds.before_loop
    async def before_update_guilds(self):
        await self.wait_until_ready()

    async def close(self):
        """Gracefully close bot connections"""
        logging.info("Shutting down bot...")
        
        # Stop background tasks
        if hasattr(self, 'update_stats') and self.update_stats.is_running():
            self.update_stats.stop()
            logging.info("Stopped stats update loop")
        
        if hasattr(self, 'update_guilds') and self.update_guilds.is_running():
            self.update_guilds.stop()
            logging.info("Stopped guild update loop")
        
        # Shutdown scalability manager
        if hasattr(self, 'scalability_manager') and self.scalability_manager:
            await self.scalability_manager.shutdown()
            logging.info("Scalability manager shutdown complete")
        
        # Close database connections (only if db module exists)
        try:
            from utils.db import async_db
            if hasattr(async_db, '_client') and async_db._client:
                async_db._client.close()
                logging.info("Closed database connections")
        except ImportError:
            logging.debug("Database module not available, skipping cleanup")
        except Exception as e:
            logging.error(f"Error closing database: {e}")
        
        # Close aiohttp sessions and other resources
        await super().close()
        logging.info("Bot shutdown complete")


bot = BronxBot(
    command_prefix='.',
    intents=intents,
    shard_count=round(config['GUILD_COUNT']/20),  # a shard for every 20 servers
    case_insensitive=True,
    application_id=config["CLIENT_ID"]  # <-- Add this line
)
bot.remove_command('help')

# loading config
COG_DATA = {
    "cogs": {
        "cogs.admin.Admin": "warning",
        "cogs.admin.Performance": "warning",  # Add performance monitoring
        "cogs.misc.Cypher": "cog", 
        "cogs.misc.MathRace": "cog", 
        "cogs.misc.TicTacToe": "cog",
        "cogs.bronx.Stats": "other", 
        "cogs.bronx.VoteBans": "other", 
        "cogs.bronx.Welcoming": "other",
        "cogs.unique.Multiplayer": "fun", 
        "cogs.fun.Fun": "fun",
        "cogs.fun.Text": "fun",
        "cogs.unique.SyncRoles": "success", 
        "cogs.Help": "success", 
        "cogs.ModMail": "success", 
        "cogs.Reminders": "success",
        "cogs.Utility": "cog",
        "cogs.Reminders": "success",
        "cogs.economy.Economy": "success",
        "cogs.economy.fishing": "success",
        "cogs.economy.fishing.AutoFishing": "success",
        "cogs.economy.Shop": "success",
        "cogs.economy.Giveaway": "success",
        "cogs.economy.Trading": "success",
        "cogs.economy.Gambling": "success",
        "cogs.economy.Work": "success",
        "cogs.economy.Bazaar": "success",
        "cogs.settings.general": "success",
        "cogs.settings.moderation": "success", 
        "cogs.settings.economy": "success",
        "cogs.settings.music": "success",
        "cogs.settings.welcome": "success",
        "cogs.settings.logging": "success",
        "cogs.Error": "success",
        "cogs.music": "fun",
        #"cogs.Security": "success", disabled for now
        #"cogs.LastFm": "disabled",  disabled for now
    },
    "colors": {
        "error": "\033[31m",      # Red
        "success": "\033[32m",    # Green
        "warning": "\033[33m",    # Yellow
        "info": "\033[34m",       # Blue
        "default": "\033[37m",    # White
        "disabled": "\033[90m",   # Bright Black (Gray)
        "fun": "\033[35m",        # Magenta
        "cog": "\033[36m",        # Cyan
        "other": "\033[94m"       # Bright Blue
    }
}

class CogLoader:
    @staticmethod
    def get_color_escape(color_name: str) -> str:
        return COG_DATA['colors'].get(color_name, COG_DATA['colors']['default'])

    @classmethod
    async def load_extension_safe(cls, bot: BronxBot, cog: str) -> Tuple[bool, str, float]:
        """Safely load an extension and return status, error (if any), and load time"""
        start = time.time()
        try:
            await bot.load_extension(cog)
            return True, "", time.time() - start
        except Exception as e:
            tb = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            return False, tb, time.time() - start

    @classmethod
    async def load_all_cogs(cls, bot: BronxBot) -> Tuple[int, int]:
        """Load all cogs and display results grouped by type"""
        results = []
        errors = []

        print(f"{cls.get_color_escape('info')}=== COG LOADING STATUS ===\033[0m".center(100))
        
        cog_groups = {}
        for cog, cog_type in COG_DATA["cogs"].items():
            if cog_type not in cog_groups:
                cog_groups[cog_type] = []
            cog_groups[cog_type].append(cog)

        for cog_type in sorted(cog_groups.keys()):
            cog_results = []
            
            for cog in cog_groups[cog_type]:
                success, error, load_time = await cls.load_extension_safe(bot, cog)
                
                status = "LOADED" if success else "ERROR"
                color = cls.get_color_escape('success' if success else 'error')
                cog_color = cls.get_color_escape(cog_type)
                
                line = f"[bronxbot] {cog_color}{cog:<24}\033[0m : {color}{status}\033[0m ({load_time:.2f}s)"
                cog_results.append(line)
                
                if not success:
                    errors.append((cog, error))
            
            print('\n'.join(cog_results))
            print()

        # summary
        success_count = len(COG_DATA["cogs"]) - len(errors)
        total = len(COG_DATA["cogs"])
        
        print(f"{cls.get_color_escape('success' if not errors else 'warning')}[SUMMARY] Loaded {success_count}/{total} cogs ({len(errors)} errors)\033[0m")
        
        # detailed error report if needed
        if errors:
            print("\nDetailed error report:")
            for cog, error in errors:
                print(f"\n{cls.get_color_escape('error')}[ERROR] {cog}:\033[0m")
                print(f"{error.strip()}")
        
        return success_count, len(errors)

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    logging.info(f"Bot ready as {bot.user.name} ({bot.user.id})")
    
    # Load all cogs using CogLoader
    try:
        logging.info("Loading cogs...")
        success_count, error_count = await CogLoader.load_all_cogs(bot)
        logging.info(f"Loaded {success_count} cogs with {error_count} errors")
    except Exception as e:
        logging.error(f"Error during cog loading: {e}")
        traceback.print_exc()
    
    # Start the stats update loop after cogs are loaded
    if not hasattr(bot, 'update_stats'):
        logging.error("update_stats task not found")
        return
    if not bot.update_stats.is_running():
        bot.update_stats.start()
        logging.info("Started stats update loop")

    # Start command usage tracker auto-save
    try:
        usage_tracker.start_auto_save()
        logging.info("Started command usage tracker auto-save")
    except Exception as e:
        logging.error(f"Failed to start command usage tracker: {e}")

    # Initialize scalability manager
    try:
        bot.scalability_manager = await initialize_scalability(bot)
        logging.info("Scalability manager initialized successfully")
    except Exception as e:
        logging.warning(f"Scalability manager initialization failed: {e}")
        bot.scalability_manager = None

    # Load additional cogs manually
    try:
        # Load TOS handler
        await bot.load_extension('utils.tos_handler')
        logging.info("TOS handler loaded successfully")
        
        # Load Setup wizard
        await bot.load_extension('cogs.setup.SetupWizard') 
        logging.info("Setup wizard loaded successfully")
    except Exception as e:
        logging.error(f"Failed to load additional cogs: {e}")

    # Initialize database and clean up corrupted inventory data
    try:
        from utils.db import async_db
        await async_db.ensure_connected()
        logging.info("Database connection established")
        
        # Run inventory cleanup on startup to remove corrupted data
        cleaned_count = await async_db.cleanup_corrupted_inventory()
        if cleaned_count > 0:
            logging.info(f"Cleaned up {cleaned_count} corrupted inventory items on startup")
        else:
            logging.info("No corrupted inventory items found during startup cleanup")
    except ImportError:
        logging.warning("Database module not available, skipping database initialization")
    except Exception as e:
        logging.error(f"Failed to initialize database or cleanup inventory: {e}")

    guild_cache_start = time.time()
    # Build guild cache
    for guild in bot.guilds:
        await guild.chunk()
    bot.boot_metrics['guild_cache_time'] = time.time() - guild_cache_start
    
    # Update presence
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name=f"with {len(bot.guilds)} servers | .help"
        )
    )
    
    if bot.restart_channel and bot.restart_message:
        try:
            channel = await bot.fetch_channel(bot.restart_channel)
            message = await channel.fetch_message(bot.restart_message)
            
            bot.boot_metrics['total_boot_time'] = time.time() - bot.boot_metrics['start_time']
            bot.boot_metrics['ready_time'] = time.time() - bot.start_time
            bot.boot_metrics['total_cog_load_time'] = sum(bot.cog_load_times.values())
            
            boot_info = (
                f"✅ Boot completed in `{bot.boot_metrics['total_boot_time']:.2f}s`\n\n"
                f"**Boot Metrics:**\n"
                f"• Config Load: `{bot.boot_metrics['config_load_time']:.2f}s`\n"
                f"• Guild Cache: `{bot.boot_metrics['guild_cache_time']:.2f}s`\n"
                f"• Total Cog Load: `{bot.boot_metrics['total_cog_load_time']:.2f}s`\n"
                f"• Ready Time: `{bot.boot_metrics['ready_time']:.2f}s`\n\n"
                f"**Individual Cog Load Times:**\n" + 
                "\n".join([f"• `{cog.split('.')[-1]}: {time:.2f}s`" 
                          for cog, time in sorted(bot.cog_load_times.items())])
            )
            
            embed = discord.Embed(
                description=boot_info,
                color=discord.Color.green()
            )
            await message.edit(embed=embed)
        except Exception as e:
            print(f"Failed to update restart message: {e}")

    """success, errors = await CogLoader.load_all_cogs(bot)
    status_msg = (
        f"[?] Logged in as {bot.user.name} (ID: {bot.user.id})\n"
        f"[!] Shards: {bot.shard_count}, Latency: {round(bot.latency * 1000, 2)}ms\n"
        f"[+] Cogs: {success} loaded, {errors} errors"
    )
    print(status_msg)"""
    
    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name=f"with {len(bot.guilds)} servers | .help"
    )
    await bot.change_presence(activity=activity)

@bot.event
async def on_guild_join(guild):
    """Send welcome message when bot joins a new guild"""
    # Find first available channel
    channel = None
    for ch in guild.text_channels:
        try:
            if ch.permissions_for(guild.me).send_messages:
                channel = ch
                break
        except discord.HTTPException:
            continue
    
    if not channel:
        return

    embed = discord.Embed(
        description=(
            f"Thanks for adding me! 👋\n\n"
            "**What I can do:**\n"
            "• Customizable welcome messages\n"
            "• Economy & *Fake* Gambling\n"
            "• Basic utility commands (.help)\n"
            "• Fun commands and games\n"
            "• Moderation tools\n\n"
            "*The bot is still in [active development](https://github.com/bronxbot/bot) *which is open source btw*, so feel free to [suggest](https://github.com/bronxbot/bot) new features!*\n\n"
           
            "• Use .help to see available commands\n"
            "• Use .help <command> for detailed info\n"
            "• Join the [support server](https://discord.gg/jvyYWkj3ts)\n\n"
            "Have fun! 🎉"
        ),
        color=discord.Color.blue()
    )
    
    embed.set_thumbnail(url=bot.user.avatar.url)
    embed.set_footer(text="made with 💜 by ks.net", icon_url=bot.user.avatar.url)
    
    try:
        await channel.send(embed=embed)
    except discord.HTTPException as e:
        print(f"Failed to send welcome message in {guild.name}: {e}")

@bot.event
async def on_command(ctx):
    """Track command usage and check TOS acceptance"""
    start_time = time.time()
    ctx.command_start_time = start_time
    
    # Skip TOS check for essential commands that users need access to
    exempt_commands = [
        'tos', 'terms', 'termsofservice', 'tosinfo', 'tosdetails',  # TOS related
        'help', 'h', 'commands',  # Help command and aliases
        'support', 'invite',  # Support commands
        'ping', 'pong',  # Basic utility
        'balance', 'bal', 'cash', 'bb'  # Balance commands - don't require ToS
    ]
    
    if ctx.command.name not in exempt_commands:
        # Check TOS acceptance for all other commands
        accepted = await check_tos_acceptance(ctx.author.id)
        if not accepted:
            await prompt_tos_acceptance(ctx)
            raise commands.CommandError("TOS not accepted")

@bot.event 
async def on_command_completion(ctx):
    """Track successful command completion"""
    execution_time = time.time() - getattr(ctx, 'command_start_time', time.time())
    usage_tracker.track_command(ctx, ctx.command.qualified_name, execution_time, error=False)

@bot.event
async def on_command_error(ctx, error):
    """Track command errors and let Error cog handle the rest"""
    execution_time = time.time() - getattr(ctx, 'command_start_time', time.time())
    usage_tracker.track_command(ctx, ctx.command.qualified_name if ctx.command else 'unknown', execution_time, error=True)
    
    # Let the Error cog handle most errors first
    if hasattr(bot, 'get_cog') and bot.get_cog('Error'):
        return  # Let the Error cog handle it
    
    # Fallback error handling if Error cog is not loaded
    if isinstance(error, commands.CommandNotFound):
        return
    else:
        print(f"Fallback error handler: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

@bot.command()
@commands.is_owner()
async def syncslash(ctx):
    """Sync slash commands globally"""
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands globally")
    except Exception as e:
        await ctx.send(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    """Handle messages"""
    if message.author.bot:
        return
    if message.content.startswith(bot.command_prefix):
        if message.guild in bot.MAIN_GUILD_IDS:
            if message.channel.id in [1378156495144751147, 1260347806699491418]:
                return await message.reply("<#1314685928614264852>")
    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    """Handle message edits and re-process commands if edited"""
    # Ignore bot messages
    if after.author.bot:
        return
    
    # Ignore if message content didn't change (e.g., embed updates)
    if before.content == after.content:
        return
    
    # Only process if the edited message starts with a command prefix
    if not after.content.startswith(bot.command_prefix):
        return
    
    # Add rate limiting to prevent spam processing
    current_time = time.time()
    user_id = after.author.id
    
    # Check if user has processed a command edit recently (within 2 seconds)
    if not hasattr(bot, 'last_edit_times'):
        bot.last_edit_times = {}
    
    if user_id in bot.last_edit_times:
        if current_time - bot.last_edit_times[user_id] < 2.0:
            return  # Skip if too recent
    
    bot.last_edit_times[user_id] = current_time
    
    # Check if the message is in a main guild and restricted channel
    if after.guild and after.guild.id in bot.MAIN_GUILD_IDS:
        if after.channel.id in [1378156495144751147, 1260347806699491418]:
            return await after.reply("<#1314685928614264852>")
    
    try:
        # Re-process the edited message as a command
        await bot.process_commands(after)
        
        # Log the command edit for debugging
        command_name = after.content.split()[0][1:] if after.content.split() else "unknown"
        logging.info(f"Command edited and re-processed: {command_name} by {after.author} ({after.author.id}) in {after.guild.name if after.guild else 'DM'}")
        
    except Exception as e:
        # Log any errors but don't crash
        logging.error(f"Error processing edited command: {e}")
        # Optionally, you could add a small reaction or reply to indicate the edit was processed
        try:
            await after.add_reaction("🔄")  # Indicate command was re-processed
        except:
            pass  # Ignore if we can't add reactions

if os.path.exists("data/restart_info.json"):
    try:
        with open("data/restart_info.json", "r") as f:
            restart_info = json.load(f)
            bot.restart_channel = restart_info["channel_id"]
            bot.restart_message = restart_info["message_id"]
        os.remove("data/restart_info.json")
    except Exception as e:
        print(f"Failed to load restart info: {e}")

if __name__ == "__main__":
    import platform
    
    # Print startup info
    logging.info(f"Python version: {platform.python_version()}")
    logging.info(f"Discord.py version: {discord.__version__}")
    logging.info(f"Starting BronxBot with {bot.shard_count} shards")
    
    # Run the Discord bot
    if dev:
        logging.info("Running in development mode")
        system("clear" if os.name == "posix" else "cls")
        if os.name == "posix":
            sys.stdout.write("\x1b]2;BronxBot (DEV)\x07")
        bot.run(config['DEV_TOKEN'], log_handler=None)  # Disable default discord.py logging
    else:
        try:
            system("clear" if os.name == "posix" else "cls")
            if os.name == "posix":
                sys.stdout.write("\x1b]2;BronxBot\x07")
            bot.run(config['TOKEN'], log_handler=None)  # Disable default discord.py logging
        except Exception as e:
            logging.error(f"Failed to start the bot: {e}")
            traceback.print_exc()