import discord 
from discord.ext import commands
import aiohttp
import os
import json
import asyncio
from urllib.parse import urlencode
from collections import Counter
from typing import Optional, Tuple

DATA_PATH = "data/lastfm_links.json"
EMOJI_PATH = "data/lastfm_emojis.json"

def get_lastfm_api_key() -> Optional[str]:
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

def get_lastfm_api_secret() -> Optional[str]:
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
with open("data/config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

LASTFM_API_KEY = get_lastfm_api_key()
LASTFM_API_SECRET = get_lastfm_api_secret()
#TODO: Migrate this to mongo

def load_links() -> dict:
    if not os.path.exists(DATA_PATH):
        return {}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_links(links: dict):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(links, f, indent=2)

def load_emojis() -> dict:
    if not os.path.exists(EMOJI_PATH):
        return {}
    try:
        with open(EMOJI_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_emojis(emojis: dict):
    os.makedirs(os.path.dirname(EMOJI_PATH), exist_ok=True)
    with open(EMOJI_PATH, "w", encoding="utf-8") as f:
        json.dump(emojis, f, indent=2)

def generate_api_sig(params, secret):
    items = sorted((k, v) for k, v in params.items() if k != "format")
    sig = "".join(f"{k}{v}" for k, v in items)
    sig += secret
    import hashlib
    return hashlib.md5(sig.encode("utf-8")).hexdigest()

def create_embed(
    title: str,
    description: str,
    color: discord.Color = discord.Color.blurple(),
    url: Optional[str] = None,
    thumbnail: Optional[str] = None,
    author: Optional[Tuple[str, str]] = None,
    footer: Optional[Tuple[str, str]] = None
) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color, url=url)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if author:
        embed.set_author(name=author[0], icon_url=author[1])
    if footer:
        embed.set_footer(text=footer[0], icon_url=footer[1])
    return embed

class LastFM(commands.Cog):
    """
    🎵 Last.fm Integration — link your Discord and view music stats.
    """

    def __init__(self, bot):
        self.bot = bot
        self.links = load_links()
        self.emojis = load_emojis()

    def get_auth_url(self, discord_id: int) -> str:
        params = {
            "api_key": LASTFM_API_KEY,
            "cb": f"https://bronxbot.onrender.com/api/lastfm/callback?discord_id={discord_id}"
        }
        print(f"Generated auth URL with params: {params}")  # Debug logging
        return f"https://www.last.fm/api/auth/?{urlencode(params)}"

    #TODO: Migrate this to mongo asap

    def set_linked_user(self, discord_id: int, session_key: str, username: str):
        if not session_key or not username:
            raise ValueError("Invalid session key or username")
        self.links[str(discord_id)] = {"session": session_key, "username": username}
        save_links(self.links)

    def remove_linked_user(self, discord_id: int):
        if str(discord_id) in self.links:
            del self.links[str(discord_id)]
            save_links(self.links)

    def get_linked_user(self, discord_id: int) -> Tuple[Optional[str], Optional[str]]:
        entry = self.links.get(str(discord_id))
        if isinstance(entry, dict):
            return entry.get("username"), entry.get("session")
        return None, None

    def get_guild_emojis(self, guild_id: int) -> Tuple[str, str]:
        emojis = self.emojis.get(str(guild_id), ["🎶", "❤️"])
        if isinstance(emojis, list) and len(emojis) == 2:
            return tuple(emojis)
        return ("🎶", "❤️")

    def set_guild_emojis(self, guild_id: int, emoji1: str, emoji2: str):
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
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=payload) as resp:
                    try:
                        data = await resp.json()
                        # Last.fm API sometimes returns error in JSON
                        if "error" in data:
                            return {"error": data.get("message", "Unknown Last.fm error")}
                        return data
                    except Exception as e:
                        return {"error": f"Failed to decode response: {e}"}
        except Exception as e:
            return {"error": f"Request failed: {e}"}

    # QOL: cooldowns, error handling, simple aliases
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply("⏳ Slow down! Try again soon.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.UserInputError):
            await ctx.reply("❌ Invalid input. Please check your command usage.")
        elif isinstance(error, aiohttp.ClientError):
            await ctx.reply("❌ Network error while contacting Last.fm.")
        else:
            await ctx.reply(f"❌ Error: {error}")

    async def get_user_and_session(self, ctx, user: Optional[discord.Member]) -> Tuple[Optional[str], Optional[str], str, str]:
        if user:
            username, session_key = self.get_linked_user(user.id)
            display_name = user.display_name
            avatar = user.display_avatar.url
        else:
            username, session_key = self.get_linked_user(ctx.author.id)
            display_name = ctx.author.display_name
            avatar = ctx.author.display_avatar.url
        return username, session_key, display_name, avatar

    async def fmlink(self, ctx):
    """Link your Discord to Last.fm."""
    if not LASTFM_API_KEY or not LASTFM_API_SECRET:
        return await ctx.reply("❌ Last.fm API key/secret not set.")
    
    try:
        url = self.get_auth_url(ctx.author.id)
        # Add verification that URL is properly formed
        if not url.startswith("https://www.last.fm/api/auth/"):
            raise ValueError("Invalid auth URL generated")
            
        embed = create_embed(
            "Last.fm Authentication",
            f"**1.** [Click here to authorize with Last.fm]({url})\n"
            "**2.** After authorizing, you'll see a success message in your browser.\n"
            "**3.** You can now use all Last.fm commands in Discord!\n\n"
            "If you have any issues, make sure your bot and API server are running.",
            color=discord.Color.orange(),
            footer=("Your account will be linked automatically after you authorize.", ctx.author.display_avatar.url)
        )
        await ctx.reply(embed=embed)
    except Exception as e:
        await ctx.reply(f"❌ Error generating auth link: {e}")
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
    async def fmwho(self, ctx, user: Optional[discord.Member] = None):
        """See the Last.fm username linked to a Discord user."""
        user = user or ctx.author
        username, _ = self.get_linked_user(user.id)
        if username:
            await ctx.reply(f"{user.mention} is linked to [`{username}`](https://last.fm/user/{username}).")
        else:
            await ctx.reply(f"{user.mention} does not have a linked Last.fm account.")

    @commands.command(aliases=["np"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def fm(self, ctx, user: Optional[discord.Member] = None):
        """Show now playing/last played track for a user."""
        try:
            username, session_key, display_name, avatar = await self.get_user_and_session(ctx, user)
            if not username or not session_key:
                return await ctx.reply(f"{display_name} has not linked their Last.fm account. Use `.fmlink` to link.")

            data = await self.get_lastfm_data("user.getrecenttracks", username, session_key, limit=1)
            if "error" in data:
                return await ctx.reply(f"❌ Last.fm error: {data['error']}")
            recenttracks = data.get("recenttracks", {})
            if isinstance(recenttracks, dict):
                tracks = recenttracks.get("track", [])
            else:
                tracks = []
            if not tracks:
                return await ctx.reply("No recent tracks found.")
            track = tracks[0]
            artist = track["artist"]["#text"]
            name = track["name"]
            url = track.get("url", "")
            album = track.get("album", {}).get("#text", "")
            now_playing = track.get("@attr", {}).get("nowplaying", False)
            embed = create_embed(
                f"{'🎵 Now Playing' if now_playing else 'Last Played'}: {name}",
                f"**Artist:** {artist}\n**Album:** {album or 'N/A'}",
                color=discord.Color.green() if now_playing else discord.Color.blue(),
                url=url,
                thumbnail=track["image"][-1]["#text"] if track.get("image") else None,
                author=(display_name, avatar),
                footer=(f"Requested by {ctx.author}", ctx.author.display_avatar.url)
            )
            msg = await ctx.reply(embed=embed)
            if ctx.guild:
                emoji1, emoji2 = self.get_guild_emojis(ctx.guild.id)
                try:
                    await msg.add_reaction(emoji1)
                    await msg.add_reaction(emoji2)
                except discord.HTTPException:
                    pass
        except Exception as e:
            await ctx.reply(f"❌ Unexpected error: {e}")

    @commands.command(aliases=["artists"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def fmtopartists(self, ctx, user: Optional[discord.Member] = None, limit: int = 5):
        """Show top artists."""
        try:
            username, session_key, display_name, _ = await self.get_user_and_session(ctx, user)
            if not username or not session_key:
                return await ctx.reply(f"{display_name} has not linked their Last.fm account. Use `.fmlink` to link.")
            data = await self.get_lastfm_data("user.gettopartists", username, session_key, limit=limit)
            if "error" in data:
                return await ctx.reply(f"❌ Last.fm error: {data['error']}")
            artists = data.get("topartists", {}).get("artist", []) if not artists:
                return await ctx.reply("No top artists found.")
            msg = "\n".join([f"**{i+1}.** [{a['name']}](https://last.fm/music/{a['name'].replace(' ', '+')}) (`{a['playcount']} plays`)" for i, a in enumerate(artists)])
            embed = create_embed(
                f"Top {limit} artists for {username}",
                msg,
                color=discord.Color.purple(),
                footer=(f"Requested by {ctx.author}", ctx.author.display_avatar.url)
            )
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ Unexpected error: {e}")

    @commands.command(aliases=["tracks"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def fmtoptracks(self, ctx, user: discord.Member = None, limit: int = 5):
        """Show top tracks."""
        try:
            username, session_key, display_name, _ = await self.get_user_and_session(ctx, user)
            if not username or not session_key:
                return await ctx.reply(f"{display_name} has not linked their Last.fm account. Use `.fmlink` to link.")
            data = await self.get_lastfm_data("user.gettoptracks", username, session_key, limit=limit)
            if "error" in data:
                return await ctx.reply(f"❌ Last.fm error: {data['error']}")
            tracks = data.get("toptracks", {}).get("track", [])
            if not tracks:
                return await ctx.reply("No top tracks found.")
            msg = "\n".join([f"**{i+1}.** [{t['name']}](https://last.fm/music/{t['artist']['name'].replace(' ', '+')}/_/{t['name'].replace(' ', '+')}) by {t['artist']['name']} (`{t['playcount']} plays`)" for i, t in enumerate(tracks)])
            embed = create_embed(
                f"Top {limit} tracks for {username}",
                msg,
                color=discord.Color.purple(),
                footer=(f"Requested by {ctx.author}", ctx.author.display_avatar.url)
            )
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ Unexpected error: {e}")

    @commands.command(aliases=["album"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def fmalbum(self, ctx, *, album: str):
        """Show album info."""
        try:
            if not LASTFM_API_KEY:
                return await ctx.reply("❌ Last.fm API key not set.")
            if " - " in album:
                artist, album_name = album.split(" - ", 1)
            else:
                return await ctx.reply("Please use the format: `.fmalbum artist - album`")
            params = {"artist": artist.strip(), "album": album_name.strip()}
            data = await self.get_lastfm_data("album.getinfo", **params)
            if "error" in data:
                return await ctx.reply(f"❌ Last.fm error: {data['error']}")
            albuminfo = data.get("album")
            if not albuminfo:
                return await ctx.reply("Album not found.")
            embed = create_embed(
                albuminfo.get('name', 'Unknown Album'),
                f"**Artist:** {albuminfo.get('artist', 'N/A')}\n"
                f"**Listeners:** `{albuminfo.get('listeners', 'N/A')}`\n"
                f"**Playcount:** `{albuminfo.get('playcount', 'N/A')}`",
                color=discord.Color.gold(),
                url=albuminfo.get("url", ""),
                thumbnail=albuminfo.get("image", [{}])[-1].get("#text") if albuminfo.get("image") else None
            )
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ Unexpected error: {e}")

    @commands.command(aliases=["artist"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def fmartist(self, ctx, *, artist: str):
        """Show artist info."""
        try:
            if not LASTFM_API_KEY:
                return await ctx.reply("❌ Last.fm API key not set.")
            data = await self.get_lastfm_data("artist.getinfo", artist=artist)
            if "error" in data:
                return await ctx.reply(f"❌ Last.fm error: {data['error']}")
            artistinfo = data.get("artist")
            if not artistinfo:
                return await ctx.reply("Artist not found.")
            bio = artistinfo.get("bio", {}).get("summary", "")
            embed = create_embed(
                artistinfo.get('name', 'Unknown Artist'),
                f"**Listeners:** `{artistinfo.get('stats', {}).get('listeners', 'N/A')}`\n"
                f"**Playcount:** `{artistinfo.get('stats', {}).get('playcount', 'N/A')}`\n\n"
                f"{bio[:500]}{'...' if len(bio) > 500 else ''}",
                color=discord.Color.gold(),
                url=artistinfo.get("url", ""),
                thumbnail=artistinfo.get("image", [{}])[-1].get("#text") if artistinfo.get("image") else None
            )
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ Unexpected error: {e}")

    @commands.command(aliases=["recent"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def fmrecent(self, ctx, user: Optional[discord.Member] = None, count: int = 5):
        """Show recent tracks."""
        try:
            username, session_key, display_name, _ = await self.get_user_and_session(ctx, user)
            if not username or not session_key:
                return await ctx.reply(f"{display_name} has not linked their Last.fm account. Use `.fmlink` to link.")
            data = await self.get_lastfm_data("user.getrecenttracks", username, session_key, limit=count)
            if "error" in data:
                return await ctx.reply(f"❌ Last.fm error: {data['error']}")
            tracks = data.get("recenttracks", {}).get("track", [])
            if not tracks:
                return await ctx.reply("No recent tracks found.")
            msg = "\n".join([f"**{i+1}.** [{t['name']}](https://last.fm/music/{t['artist']['#text'].replace(' ', '+')}/_/{t['name'].replace(' ', '+')}) by {t['artist']['#text']}" for i, t in enumerate(tracks)])
            embed = create_embed(
                f"Last {count} tracks for {username}",
                msg,
                color=discord.Color.blurple()
            )
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ Unexpected error: {e}")

    @commands.command(aliases=["servertop"])
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def fmservertop(self, ctx, limit: int = 5):
        """Show server's most played artists."""
        try:
            if ctx.guild is None:
                return await ctx.reply("This command can only be used in a server.")
            usernames = [self.get_linked_user(m.id)[0] for m in ctx.guild.members if self.get_linked_user(m.id)[0]]
            if not usernames:
                return await ctx.reply("No users in this server have linked their Last.fm accounts.")

            async def fetch_artists(username):
                await asyncio.sleep(0.1)  New chat
Today
Last.fm Authentication Error Fix Guide
Code Analysis and Security Improvements Suggested
Add Stock Selling Feature to Bazaar
Yesterday
Fixing Discord Modal Interaction Error
Split Text Manipulation Commands into Cog
Discord Economy Bot Features and Analysis
Correcting Discord Bot Widget Markdown Syntax
New Update Release with Discord Integration
New chat# small delay to avoid rate limits
                data = await self.get_lastfm_data("user.gettopartists", username, limit=limit)
                if "error" in data:
                    return []
                return data.get("topartists", {}).get("artist", [])

            async with ctx.typing():
                all_artists_lists = await asyncio.gather(*(fetch_artists(u) for u in usernames))
                artist_counter = Counter()
                for artists in all_artists_lists:
                    for a in artists:
                        artist_counter[a["name"]] += int(a.get("playcount", 0))
                if not artist_counter:
                    return await ctx.reply("No artist data found for this server.")
                top = artist_counter.most_common(limit)
                msg = "\n".join([f"**{i+1}.** {name} (`{plays} plays`)" for i, (name, plays) in enumerate(top)])
                embed = create_embed(
                    f"Server Top {limit} Artists",
                    msg,
                    color=discord.Color.blurple()
                )
                await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ Unexpected error: {e}")

    @commands.command(aliases=["topscrobblers"])
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def fmleaderboard(self, ctx):
        """Show top scrobblers in the server."""
        try:
            if ctx.guild is None:
                return await ctx.reply("This command can only be used in a server.")
            members = [m for m in ctx.guild.members if self.get_linked_user(m.id)[0]]
            if not members:
                return await ctx.reply("No users in this server have linked their Last.fm accounts.")

            async def fetch_playcount(member):
                await asyncio.sleep(0.1)  # small delay to avoid rate limits
                username, _ = self.get_linked_user(member.id)
                data = await self.get_lastfm_data("user.getinfo", username)
                if "error" in data:
                    return (member.display_name, 0)
                playcount = int(data.get("user", {}).get("playcount", 0))
                return (member.display_name, playcount)

            async with ctx.typing():
                leaderboard = await asyncio.gather(*(fetch_playcount(m) for m in members))
                leaderboard = [entry for entry in leaderboard if entry[1] > 0]
                if not leaderboard:
                    return await ctx.reply("No users in this server have linked their Last.fm accounts.")
                leaderboard.sort(key=lambda x: x[1], reverse=True)
                msg = "\n".join([f"**{i+1}.** {name} (`{plays} plays`)" for i, (name, plays) in enumerate(leaderboard[:10])])
                embed = create_embed(
                    "Top Scrobblers in This Server",
                    msg,
                    color=discord.Color.blurple()
                )
                await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ Unexpected error: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def fmsetemojis(self, ctx, emoji1: str, emoji2: str):
        """Set the two emojis used for .fm reactions (admin only)."""
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

    @commands.command()
    async def fmhelp(self, ctx):
        """Show all Last.fm commands."""
        embed = discord.Embed(
            title="🎵 Last.fm Commands",
            description=(
                "**.fm [user]** — Now playing/last played track\n"
                "**.fmtopartists [user] [limit]** — Top artists\n"
                "**.fmtoptracks [user] [limit]** — Top tracks\n"
                "**.fmalbum artist - album** — Album info\n"
                "**.fmartist artist** — Artist info\n"
                "**.fmrecent [user] [count]** — Recent tracks\n"
                "**.fmservertop [limit]** — Server's top artists\n"
                "**.fmleaderboard** — Server's top scrobblers\n"
                "**.fmsetemojis emoji1 emoji2** — Set .fm emojis (admin)\n"
                "**.fmemojis** — Show current .fm emojis\n"
                "**.fmlink / .fmunlink** — Link/unlink your account\n"
                "**.fmwho [user]** — See who is linked\n"
            ),
            color=discord.Color.blurple()
        )
        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(LastFM(bot))
