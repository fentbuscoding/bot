from utils.db import async_db
from discord.ext import commands
from bronxbot import bot

@bot.check
async def blacklist_check(ctx):
    try:
        cmd = ctx.command.name if ctx.command else None
        if not cmd:
            return True  # fallback

        channel_id = str(ctx.channel.id)
        user_id = str(ctx.author.id)

        settings = await async_db.get_guild_settings(ctx.guild.id) or {}
        blacklist = settings.get('command_blacklist', {})
        channel_blacklist = blacklist.get('channels', {})
        user_blacklist = blacklist.get('users', {})
        role_blacklist = blacklist.get('roles', {})

        print(f"[CHECK] Command: {cmd}")
        print(f"[CHECK] Channel ID: {channel_id}")
        print(f"[CHECK] Channel blacklist: {channel_blacklist}")

        if cmd in channel_blacklist.get(channel_id, []) or "all" in channel_blacklist.get(channel_id, []):
            print(f"[BLOCKED] '{cmd}' is blacklisted in channel {channel_id}")
            return False

        if cmd in user_blacklist.get(user_id, []) or "all" in user_blacklist.get(user_id, []):
            print(f"[BLOCKED] '{cmd}' is blacklisted for user {user_id}")
            return False

        for role in ctx.author.roles:
            if cmd in role_blacklist.get(str(role.id), []) or "all" in role_blacklist.get(str(role.id)):
                print(f"[BLOCKED] '{cmd}' is blacklisted for role {role.id}")
                return False

        return True

    except Exception as e:
        print(f"[ERROR] blacklist_check failed: {e}")
        return True 
