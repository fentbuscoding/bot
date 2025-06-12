from bronxbot import *
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
    
    # Track command with stats tracker
    try:
        await stats_tracker.send_command_update(ctx.command.qualified_name)
    except Exception as e:
        logging.debug(f"Error tracking command with stats tracker: {e}")
    
    # Send real-time update to dashboard
    await bot.send_realtime_command_update(
        command_name=ctx.command.qualified_name,
        user_id=ctx.author.id,
        guild_id=ctx.guild.id if ctx.guild else None,
        execution_time=execution_time,
        error=False
    )

@bot.event
async def on_command_error(ctx, error):
    """Track command errors and let Error cog handle the rest"""
    execution_time = time.time() - getattr(ctx, 'command_start_time', time.time())
    command_name = ctx.command.qualified_name if ctx.command else 'unknown'
    usage_tracker.track_command(ctx, command_name, execution_time, error=True)
    
    # Send real-time error update to dashboard
    await bot.send_realtime_command_update(
        command_name=command_name,
        user_id=ctx.author.id,
        guild_id=ctx.guild.id if ctx.guild else None,
        execution_time=execution_time,
        error=True
    )
    
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