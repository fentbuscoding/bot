import discord
from discord.ext import commands
import aiohttp
import os
import json
from urllib.parse import urlencode
from collections import Counter

DATA_PATH = "data/lastfm_links.json"
EMOJI_PATH = "data/lastfm_emojis.json"

def get_lastfm_api_key():
    key = os.getenv("LASTFM_API_KEY")
    if key:
        return key
    for path in ["data/config.json", "config.json"]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("LASTFM_API_KEY") or config.get("lastfm_api_key")
        except Exception:
            continue
    return None

def get_lastfm_api_secret():
    secret = os.getenv("LASTFM_API_SECRET")
    if secret:
        return secret
    for path in ["data/config.json", "config.json"]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("LASTFM_API_SECRET") or config.get("lastfm_api_secret")
        except Exception:
            continue
    return None

LASTFM_API_KEY = get_lastfm_api_key()
LASTFM_API_SECRET = get_lastfm_api_secret()

def load_links():
    if not os.path.exists(DATA_PATH):
        return {}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_links(links):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(links, f, indent=2)

def load_emojis():
    if not os.path.exists(EMOJI_PATH):
        return {}
    try:
        with open(EMOJI_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_emojis(emojis):
    os.makedirs(os.path.dirname(EMOJI_PATH), exist_ok=True)
    with open(EMOJI_PATH, "w", encoding="utf-8") as f:
        json.dump(emojis, f, indent=2)

def generate_api_sig(params, secret):
    items = sorted((k, v) for k, v in params.items() if k != "format")
    sig = "".join(f"{k}{v}" for k, v in items)
    sig += secret
    import hashlib
    return hashlib.md5(sig.encode("utf-8")).hexdigest()

class LastFM(commands.Cog):
    """
    🎵 Last.fm Integration
    Authenticate and link your Discord account to Last.fm, and view your music stats.
    """

    def __init__(self, bot):
        self.bot = bot
        self.links = load_links()
        self.emojis = load_emojis()

    def get_auth_url(self, discord_id):
        params = {
            "api_key": LASTFM_API_KEY,
            # Use localhost with a port for local development/callback
            "cb": f"http://localhost:5000/api/lastfm/callback?discord_id={discord_id}"
        }
        return f"https://www.last.fm/api/auth/?{urlencode(params)}"

    def set_linked_user(self, discord_id, session_key, username):
        self.links[str(discord_id)] = {"session": session_key, "username": username}
        save_links(self.links)

    def remove_linked_user(self, discord_id):
        if str(discord_id) in self.links:
            del self.links[str(discord_id)]
            save_links(self.links)

    def get_linked_user(self, discord_id):
        entry = self.links.get(str(discord_id))
        if isinstance(entry, dict):
            return entry.get("username"), entry.get("session")
        return None, None

    def get_guild_emojis(self, guild_id):
        # Returns a tuple of (emoji1, emoji2) or default if not set
        emojis = self.emojis.get(str(guild_id), ["🎶", "❤️"])
        if isinstance(emojis, list) and len(emojis) == 2:
            return tuple(emojis)
        return ("🎶", "❤️")

    def set_guild_emojis(self, guild_id, emoji1, emoji2):
        self.emojis[str(guild_id)] = [emoji1, emoji2]
        save_emojis(self.emojis)

    async def get_lastfm_data(self, method, username=None, session_key=None, **params):
        url = "http://ws.audioscrobbler.com/2.0/"
        payload = {
            "method": method,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            **params
        }
        if username:
            payload["user"] = username
        if session_key:
            payload["sk"] = session_key
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=payload) as resp:
                try:
                    return await resp.json()
                except Exception:
                    return {}

    # QOL: cooldowns, error handling, simple aliases
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(f"⏳ Slow down! Try again in {error.retry_after:.1f}s.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ You don't have permission to use this command.")
        else:
            await ctx.reply(f"❌ Error: {error}")

    @commands.command(aliases=["link"])
    async def fmlink(self, ctx):
        """Authenticate your Discord account with Last.fm."""
        if not LASTFM_API_KEY or not LASTFM_API_SECRET:
            return await ctx.reply("❌ Last.fm API key/secret not set.")
        url = self.get_auth_url(ctx.author.id)
        embed = discord.Embed(
            title="Last.fm Authentication",
            description=(
                f"**1.** [Click here to authorize with Last.fm]({url})\n"
                "**2.** After authorizing, you'll see a success message in your browser.\n"
                "**3.** You can now use all Last.fm commands in Discord!\n\n"
                "If you have any issues, make sure your bot and API server are running."
            ),
            color=discord.Color.orange()
        )
        embed.set_footer(text="Your account will be linked automatically after you authorize.")
        await ctx.reply(embed=embed)

    @commands.command(aliases=["unlink"])
    async def fmunlink(self, ctx):
        """Unlink your Last.fm account."""
        username, _ = self.get_linked_user(ctx.author.id)
        if username:
            self.remove_linked_user(ctx.author.id)
            await ctx.reply("❌ Your Last.fm account has been unlinked.")
        else:
            await ctx.reply("You don't have a linked Last.fm account.")

    @commands.command(aliases=["who"])
    async def fmwho(self, ctx, user: discord.Member = None):
        """See the Last.fm username linked to a Discord user."""
        user = user or ctx.author
        username, _ = self.get_linked_user(user.id)
        if username:
            await ctx.reply(f"{user.mention} is linked to [`{username}`](https://last.fm/user/{username}).")
        else:
            await ctx.reply(f"{user.mention} does not have a linked Last.fm account.")

    @commands.command(aliases=["np"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def fm(self, ctx, user: discord.Member = None):
        """Show now playing/last played track for a user. Adds two custom emojis as reactions."""
        if not LASTFM_API_KEY:
            return await ctx.reply("❌ Last.fm API key not set.")
        if user:
            username, session_key = self.get_linked_user(user.id)
            display_name = user.display_name
            avatar = user.display_avatar.url
        else:
            username, session_key = self.get_linked_user(ctx.author.id)
            display_name = ctx.author.display_name
            avatar = ctx.author.display_avatar.url

        if not username or not session_key:
            return await ctx.reply(f"{display_name} has not linked their Last.fm account. Use `.fmlink` to link.")

        data = await self.get_lastfm_data("user.getrecenttracks", username, session_key, limit=1)
        tracks = data.get("recenttracks", {}).get("track", [])
        if not tracks:
            return await ctx.reply("No recent tracks found.")
        track = tracks[0]
        artist = track["artist"]["#text"]
        name = track["name"]
        url = track.get("url", "")
        album = track.get("album", {}).get("#text", "")
        now_playing = track.get("@attr", {}).get("nowplaying", False)
        embed = discord.Embed(
            title=f"{'🎵 Now Playing' if now_playing else 'Last Played'}: {name}",
            description=f"**Artist:** {artist}\n**Album:** {album or 'N/A'}",
            url=url,
            color=discord.Color.green() if now_playing else discord.Color.blue()
        )
        if track.get("image"):
            embed.set_thumbnail(url=track["image"][-1]["#text"])
        embed.set_author(name=display_name, icon_url=avatar)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        msg = await ctx.reply(embed=embed)

        # Add two custom emojis as reactions (guild configurable)
        if ctx.guild:
            emoji1, emoji2 = self.get_guild_emojis(ctx.guild.id)
            try:
                await msg.add_reaction(emoji1)
                await msg.add_reaction(emoji2)
            except discord.HTTPException:
                pass

    @commands.command(aliases=["artists"])
    async def fmtopartists(self, ctx, user: discord.Member = None, limit: int = 5):
        """Show top Last.fm artists."""
        if not LASTFM_API_KEY:
            return await ctx.reply("❌ Last.fm API key not set.")
        if user:
            username, session_key = self.get_linked_user(user.id)
            display_name = user.display_name
        else:
            username, session_key = self.get_linked_user(ctx.author.id)
            display_name = ctx.author.display_name

        if not username or not session_key:
            return await ctx.reply(f"{display_name} has not linked their Last.fm account. Use `.fmlink` to link.")

        data = await self.get_lastfm_data("user.gettopartists", username, session_key, limit=limit)
        artists = data.get("topartists", {}).get("artist", [])
        if not artists:
            return await ctx.reply("No top artists found.")
        msg = "\n".join([f"**{i+1}.** [{a['name']}](https://last.fm/music/{a['name'].replace(' ', '+')}) (`{a['playcount']} plays`)" for i, a in enumerate(artists)])
        embed = discord.Embed(
            title=f"Top {limit} artists for {username}",
            description=msg,
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=embed)

    @commands.command(aliases=["tracks"])
    async def fmtoptracks(self, ctx, user: discord.Member = None, limit: int = 5):
        """Show top Last.fm tracks."""
        if not LASTFM_API_KEY:
            return await ctx.reply("❌ Last.fm API key not set.")
        if user:
            username, session_key = self.get_linked_user(user.id)
            display_name = user.display_name
        else:
            username, session_key = self.get_linked_user(ctx.author.id)
            display_name = ctx.author.display_name

        if not username or not session_key:
            return await ctx.reply(f"{display_name} has not linked their Last.fm account. Use `.fmlink` to link.")

        data = await self.get_lastfm_data("user.gettoptracks", username, session_key, limit=limit)
        tracks = data.get("toptracks", {}).get("track", [])
        if not tracks:
            return await ctx.reply("No top tracks found.")
        msg = "\n".join([f"**{i+1}.** [{t['name']}](https://last.fm/music/{t['artist']['name'].replace(' ', '+')}/_/{t['name'].replace(' ', '+')}) by {t['artist']['name']} (`{t['playcount']} plays`)" for i, t in enumerate(tracks)])
        embed = discord.Embed(
            title=f"Top {limit} tracks for {username}",
            description=msg,
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=embed)

    @commands.command(aliases=["album"])
    async def fmalbum(self, ctx, *, album: str):
        """Show info about an album."""
        if not LASTFM_API_KEY:
            return await ctx.reply("❌ Last.fm API key not set.")
        # Try to get artist and album from input
        if " - " in album:
            artist, album_name = album.split(" - ", 1)
        else:
            await ctx.reply("Please use the format: `.fmalbum artist - album`")
            return
        params = {"artist": artist.strip(), "album": album_name.strip()}
        data = await self.get_lastfm_data("album.getinfo", **params)
        albuminfo = data.get("album")
        if not albuminfo:
            return await ctx.reply("Album not found.")
        embed = discord.Embed(
            title=f"{albuminfo.get('name', 'Unknown Album')}",
            url=albuminfo.get("url", ""),
            color=discord.Color.gold(),
            description=f"**Artist:** {albuminfo.get('artist', 'N/A')}\n"
                        f"**Listeners:** `{albuminfo.get('listeners', 'N/A')}`\n"
                        f"**Playcount:** `{albuminfo.get('playcount', 'N/A')}`"
        )
        if albuminfo.get("image"):
            embed.set_thumbnail(url=albuminfo["image"][-1]["#text"])
        await ctx.reply(embed=embed)

    @commands.command(aliases=["artist"])
    async def fmartist(self, ctx, *, artist: str):
        """Show info about an artist."""
        if not LASTFM_API_KEY:
            return await ctx.reply("❌ Last.fm API key not set.")
        data = await self.get_lastfm_data("artist.getinfo", artist=artist)
        artistinfo = data.get("artist")
        if not artistinfo:
            return await ctx.reply("Artist not found.")
        bio = artistinfo.get("bio", {}).get("summary", "")
        embed = discord.Embed(
            title=f"{artistinfo.get('name', 'Unknown Artist')}",
            url=artistinfo.get("url", ""),
            color=discord.Color.gold(),
            description=f"**Listeners:** `{artistinfo.get('stats', {}).get('listeners', 'N/A')}`\n"
                        f"**Playcount:** `{artistinfo.get('stats', {}).get('playcount', 'N/A')}`\n\n"
                        f"{bio[:500]}{'...' if len(bio) > 500 else ''}"
        )
        if artistinfo.get("image"):
            embed.set_thumbnail(url=artistinfo["image"][-1]["#text"])
        await ctx.reply(embed=embed)

    @commands.command(aliases=["recent"])
    async def fmrecent(self, ctx, user: discord.Member = None, count: int = 5):
        """Show the last N tracks a user played."""
        if not LASTFM_API_KEY:
            return await ctx.reply("❌ Last.fm API key not set.")
        if user:
            username, session_key = self.get_linked_user(user.id)
            display_name = user.display_name
        else:
            username, session_key = self.get_linked_user(ctx.author.id)
            display_name = ctx.author.display_name

        if not username or not session_key:
            return await ctx.reply(f"{display_name} has not linked their Last.fm account. Use `.fmlink` to link.")

        data = await self.get_lastfm_data("user.getrecenttracks", username, session_key, limit=count)
        tracks = data.get("recenttracks", {}).get("track", [])
        if not tracks:
            return await ctx.reply("No recent tracks found.")
        msg = "\n".join([f"**{i+1}.** [{t['name']}](https://last.fm/music/{t['artist']['#text'].replace(' ', '+')}/_/{t['name'].replace(' ', '+')}) by {t['artist']['#text']}" for i, t in enumerate(tracks)])
        embed = discord.Embed(
            title=f"Last {count} tracks for {username}",
            description=msg,
            color=discord.Color.blurple()
        )
        await ctx.reply(embed=embed)

    @commands.command(aliases=["servertop"])
    async def fmservertop(self, ctx, limit: int = 5):
        """Show the most played artists among all linked users in the server."""
        if ctx.guild is None:
            return await ctx.reply("This command can only be used in a server.")
        usernames = [self.get_linked_user(m.id)[0] for m in ctx.guild.members if self.get_linked_user(m.id)[0]]
        if not usernames:
            return await ctx.reply("No users in this server have linked their Last.fm accounts.")
        artist_counter = Counter()
        for username in usernames:
            data = await self.get_lastfm_data("user.gettopartists", username, limit=limit)
            artists = data.get("topartists", {}).get("artist", [])
            for a in artists:
                artist_counter[a["name"]] += int(a.get("playcount", 0))
        if not artist_counter:
            return await ctx.reply("No artist data found for this server.")
        top = artist_counter.most_common(limit)
        msg = "\n".join([f"**{i+1}.** {name} (`{plays} plays`)" for i, (name, plays) in enumerate(top)])
        embed = discord.Embed(
            title=f"Server Top {limit} Artists",
            description=msg,
            color=discord.Color.blurple()
        )
        await ctx.reply(embed=embed)

    @commands.command(aliases=["leaderboard", "topscrobblers"])
    async def fmleaderboard(self, ctx):
        """Show the top scrobblers in the server."""
        if ctx.guild is None:
            return await ctx.reply("This command can only be used in a server.")
        leaderboard = []
        for member in ctx.guild.members:
            username, _ = self.get_linked_user(member.id)
            if username:
                data = await self.get_lastfm_data("user.getinfo", username)
                playcount = int(data.get("user", {}).get("playcount", 0))
                leaderboard.append((member.display_name, playcount))
        if not leaderboard:
            return await ctx.reply("No users in this server have linked their Last.fm accounts.")
        leaderboard.sort(key=lambda x: x[1], reverse=True)
        msg = "\n".join([f"**{i+1}.** {name} (`{plays} plays`)" for i, (name, plays) in enumerate(leaderboard[:10])])
        embed = discord.Embed(
            title="Top Scrobblers in This Server",
            description=msg,
            color=discord.Color.blurple()
        )
        await ctx.reply(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def fmsetemojis(self, ctx, emoji1: str, emoji2: str):
        """Set the two emojis used for reactions on .fm command (admin/owner only)."""
        if ctx.guild is None:
            return await ctx.reply("This command can only be used in a server.")
        try:
            await ctx.message.add_reaction(emoji1)
            await ctx.message.add_reaction(emoji2)
        except discord.HTTPException:
            return await ctx.reply("One or both emojis are invalid or I can't use them.")
        self.set_guild_emojis(ctx.guild.id, emoji1, emoji2)
        await ctx.reply(f"Set the .fm reaction emojis to {emoji1} and {emoji2} for this server.")

    @commands.command()
    async def fmemojis(self, ctx):
        """Show the current .fm reaction emojis for this server."""
        if ctx.guild is None:
            return await ctx.reply("This command can only be used in a server.")
        emoji1, emoji2 = self.get_guild_emojis(ctx.guild.id)
        await ctx.reply(f"The current .fm reaction emojis for this server are: {emoji1} {emoji2}")

async def setup(bot):
    await bot.add_cog(LastFM(bot))