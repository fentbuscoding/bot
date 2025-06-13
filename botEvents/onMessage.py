from bronxbot import *

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
