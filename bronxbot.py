from imports import *
from stats import StatsTracker
import math
# Note: bronxbot.py has most necessary imports for main & related files, so import bronxbot.py if you're too lazy to import everything

# Need to import specific functions for some odd reason

# Put BronxBot in a separate class, modularization and ease of use

# List of guilds that have access to all features
MAIN_GUILD_IDS = [
    1259717095382319215,  # Main server
    1299747094449623111,  # South Bronx
    1142088882222022786   # Long Island
]

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
        self.guild_list = []
        self.stats_tracker = None  # Will be initialized later

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

    async def send_realtime_command_update(self, command_name: str, user_id: int, guild_id: int = None, execution_time: float = 0, error: bool = False):
        """Send real-time command update to dashboard"""
        try:
            update_data = {
                'type': 'command_update',
                'command': command_name,
                'user_id': str(user_id),
                'guild_id': str(guild_id) if guild_id else None,
                'execution_time': execution_time,
                'error': error,
                'timestamp': time.time()
            }
            
            dashboard_urls = ['https://bronxbot.onrender.com/api/realtime'] if not dev else ['http://localhost:5000/api/realtime']
            
            async with aiohttp.ClientSession() as session:
                for url in dashboard_urls:
                    try:
                        async with session.post(url, json=update_data, timeout=5) as resp:
                            if resp.status == 200:
                                logging.debug("Real-time command update sent successfully")
                                break
                    except Exception as e:
                        logging.debug(f"Failed to send real-time update to {url}: {e}")
        except Exception as e:
            logging.debug(f"Error sending real-time command update: {e}")

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
        
        # Stop additional stats tasks
        try:
            if additional_stats_update.is_running():
                additional_stats_update.stop()
                logging.info("Stopped additional stats update loop")
        except:
            pass
            
        try:
            if reset_daily_stats.is_running():
                reset_daily_stats.stop()
                logging.info("Stopped daily stats reset loop")
        except:
            pass
        
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

# setup
intents = discord.Intents.all()
intents.message_content = True

with open("data/config.json", "r") as f:
    config = json.load(f)

dev = config.get('DEV', False)

bot = BronxBot(
    command_prefix='.',
    intents=intents,
    shard_count=math.ceil(config["GUILD_COUNT"]/20),
    case_insensitive=True,
    application_id=config["CLIENT_ID"]
)
bot.remove_command('help')

# Stats tracking now handled by the Stats cog

# loading config
COG_DATA = {
    "cogs": {
        "cogs.admin.Admin": "warning",
        "cogs.admin.Performance": "warning",  # Add performance monitoring
        "cogs.misc.Cypher": "cog", 
        "cogs.misc.MathRace": "cog", 
        "cogs.misc.TicTacToe": "cog",
        "cogs.Stats": "other", 
        "cogs.bronx.VoteBans": "other", 
        "cogs.bronx.Welcoming": "other",
        "cogs.bronx.AI": "other",  # AI integration with Ollama
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
        logging.error(f"Error in additional stats update: {e}")

@tasks.loop(hours=24)
async def reset_daily_stats():
    try:
        bot.stats_tracker.daily_commands = 0
        logging.info("Daily stats reset completed")
    except Exception as e:
        logging.error(f"Error resetting daily stats: {e}")

# Export objects needed by main.py
additional_stats_update = additional_stats_update
reset_daily_stats = reset_daily_stats
stats_tracker = bot.stats_tracker