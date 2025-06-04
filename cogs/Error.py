import discord
from discord.ext import commands
from cogs.logging.logger import CogLogger
import traceback

logger = CogLogger('Error')

class Error(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Global error handler for all command errors"""
        
        if isinstance(error, commands.CommandNotFound):
            # Ignore command not found errors
            return
            
        # Get command info for logging
        command = ctx.command.qualified_name if ctx.command else "unknown"
        author = f"{ctx.author} ({ctx.author.id})"
        guild = f"{ctx.guild} ({ctx.guild.id})" if ctx.guild else "DM"
        
        # Generate full traceback
        error_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        
        # Log the error
        logger.error(
            f"Command error in {command}:\n"
            f"User: {author}\n" 
            f"Guild: {guild}\n"
            f"Error: {str(error)}\n"
            f"Traceback:\n{error_trace}"
        )

        # Handle specific error types
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ You don't have permission to use this command!")
            
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.reply("❌ I don't have the required permissions for this command!")
            
        elif isinstance(error, commands.BadArgument):
            await ctx.reply(f"❌ Invalid argument provided: {str(error)}")
            
        elif isinstance(error, commands.CommandOnCooldown):
            def format_time(seconds):
                days, seconds = divmod(seconds, 86400)
                hours, seconds = divmod(seconds, 3600)
                minutes, seconds = divmod(seconds, 60)
                time_parts = []
                if days > 0:
                    time_parts.append(f"{int(days)}d")
                if hours > 0:
                    time_parts.append(f"{int(hours)}h")
                if minutes > 0:
                    time_parts.append(f"{int(minutes)}m")
                if seconds > 0:
                    time_parts.append(f"{int(seconds)}s")
                return " ".join(time_parts)
            await ctx.reply(f"⏳ This command is on cooldown for `{format_time(error.retry_after)}`")
            
        elif isinstance(error, commands.DisabledCommand):
            await ctx.reply("❌ This command is currently disabled")
            
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.reply("❌ This command cannot be used in DMs")
            
        elif isinstance(error, commands.CheckFailure):
            await ctx.reply("❌ You don't meet the requirements to use this command")
            
        else:
            # Unhandled error occurred
            error_id = hex(abs(hash(str(error))))[-6:]
            await ctx.reply(
                f"❌ An unexpected error occurred! Error ID: `{error_id}`\n"
                "This has been logged and will be investigated."
            )

async def setup(bot):
    try:
        await bot.add_cog(Error(bot))
        logger.info("Error handling cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Error cog: {e}")
        raise
