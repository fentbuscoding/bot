import discord
from discord.ext import commands
import aiohttp
import os
import json
from urllib.parse import urlencode

DATA_PATH = "data/lastfm_links.json"

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

    def get_auth_url(self, discord_id):
        params = {
            "api_key": LASTFM_API_KEY,
            # Replace with your actual API endpoint:
            "cb": f"https://yourdomain.com/api/lastfm/callback?discord_id={discord_id}"
        }
        return f"https://www.last.fm/api/auth/?{urlencode(params)}"

    async def get_session_key(self, token):
        url = "http://ws.audioscrobbler.com/2.0/"
        params = {
            "method": "auth.getSession",
            "api_key": LASTFM_API_KEY,
            "token": token,
            "format": "json"
        }
        api_sig = generate_api_sig(params, LASTFM_API_SECRET)
        params["api_sig"] = api_sig
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                return data.get("session", {}).get("key"), data

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

    async def get_lastfm_data(self, method, username, session_key=None, **params):
        url = "http://ws.audioscrobbler.com/2.0/"
        payload = {
            "method": method,
            "user": username,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            **params
        }
        if session_key:
            payload["sk"] = session_key
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=payload) as resp:
                try:
                    return await resp.json()
                except Exception:
                    return {}

    @commands.command()
    async def fmlink(self, ctx):
        """Authenticate your Discord account with Last.fm."""
        if not LASTFM_API_KEY or not LASTFM_API_SECRET:
            embed = discord.Embed(
                title="API Key/Secret Missing",
                description="❌ Last.fm API key/secret not set. Please set them in your config.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        url = self.get_auth_url(ctx.author.id)
        embed = discord.Embed(
            title="Last.fm Authentication",
            description=(
                f"1. [Click here to authorize with Last.fm]({url})\n"
                "2. After authorizing, you'll be redirected and your account will be linked automatically!"
            ),
            color=discord.Color.orange()
        )
        await ctx.reply(embed=embed)

    @commands.command()
    async def fmauth(self, ctx, token: str = None):
        """Finish Last.fm authentication by providing your token (if using manual flow)."""
        if not token:
            return await ctx.reply("Usage: `!fmauth <token>` (see `.fmlink` for instructions)")
        session_key, data = await self.get_session_key(token)
        if not session_key:
            msg = data.get("message", "Failed to get session key. Make sure you authorized the app and used the correct token.")
            embed = discord.Embed(
                title="Authentication Failed",
                description=f"❌ {msg}",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        username = data["session"]["name"]
        self.set_linked_user(ctx.author.id, session_key, username)
        embed = discord.Embed(
            title="Last.fm Linked",
            description=f"✅ Successfully linked to Last.fm user `{username}`.",
            color=discord.Color.green()
        )
        await ctx.reply(embed=embed)

    @commands.command()
    async def fmunlink(self, ctx):
        """Unlink your Last.fm account."""
        username, _ = self.get_linked_user(ctx.author.id)
        if username:
            self.remove_linked_user(ctx.author.id)
            embed = discord.Embed(
                title="Last.fm Unlinked",
                description="❌ Unlinked your Last.fm account.",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed)
        else:
            embed = discord.Embed(
                title="No Link Found",
                description="You don't have a linked Last.fm account.",
                color=discord.Color.orange()
            )
            await ctx.reply(embed=embed)

    @commands.command()
    async def fmwho(self, ctx, user: discord.Member = None):
        """See the Last.fm username linked to a Discord user."""
        user = user or ctx.author
        username, _ = self.get_linked_user(user.id)
        if username:
            embed = discord.Embed(
                title="Last.fm Link",
                description=f"{user.mention} is linked to Last.fm user `{username}`.",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="No Link Found",
                description=f"{user.mention} does not have a linked Last.fm account.",
                color=discord.Color.orange()
            )
        await ctx.reply(embed=embed)

    @commands.command(aliases=["fmnp", "np"])
    async def fm(self, ctx, user: discord.Member = None):
        """Show now playing/last played track for a user."""
        if not LASTFM_API_KEY:
            embed = discord.Embed(
                title="API Key Missing",
                description="❌ Last.fm API key not set.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        if user:
            username, session_key = self.get_linked_user(user.id)
            display_name = user.display_name
            avatar = user.display_avatar.url
        else:
            username, session_key = self.get_linked_user(ctx.author.id)
            display_name = ctx.author.display_name
            avatar = ctx.author.display_avatar.url

        if not username or not session_key:
            embed = discord.Embed(
                title="No Link Found",
                description=f"{display_name} has not linked their Last.fm account. Use `.fmlink` to link.",
                color=discord.Color.orange()
            )
            return await ctx.reply(embed=embed)

        data = await self.get_lastfm_data("user.getrecenttracks", username, session_key, limit=1)
        if not data:
            embed = discord.Embed(
                title="API Error",
                description="❌ Could not contact Last.fm API.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        tracks = data.get("recenttracks", {}).get("track", [])
        if not tracks:
            embed = discord.Embed(
                title="No Tracks Found",
                description="No recent tracks found.",
                color=discord.Color.orange()
            )
            return await ctx.reply(embed=embed)
        track = tracks[0]
        artist = track["artist"]["#text"]
        name = track["name"]
        url = track.get("url", "")
        album = track.get("album", {}).get("#text", "")
        now_playing = track.get("@attr", {}).get("nowplaying", False)
        embed = discord.Embed(
            title=f"{'Now Playing' if now_playing else 'Last Played'}: {name}",
            description=f"by **{artist}**\nAlbum: {album}",
            url=url,
            color=discord.Color.green() if now_playing else discord.Color.blue()
        )
        if track.get("image"):
            embed.set_thumbnail(url=track["image"][-1]["#text"])
        embed.set_author(name=display_name, icon_url=avatar)
        await ctx.reply(embed=embed)

    @commands.command(aliases=["fmartists"])
    async def fmtopartists(self, ctx, user: discord.Member = None, limit: int = 5):
        """Show your (or a user's) top Last.fm artists."""
        if not LASTFM_API_KEY:
            embed = discord.Embed(
                title="API Key Missing",
                description="❌ Last.fm API key not set.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        if user:
            username, session_key = self.get_linked_user(user.id)
            display_name = user.display_name
        else:
            username, session_key = self.get_linked_user(ctx.author.id)
            display_name = ctx.author.display_name

        if not username or not session_key:
            embed = discord.Embed(
                title="No Link Found",
                description=f"{display_name} has not linked their Last.fm account. Use `.fmlink` to link.",
                color=discord.Color.orange()
            )
            return await ctx.reply(embed=embed)

        data = await self.get_lastfm_data("user.gettopartists", username, session_key, limit=limit)
        if not data:
            embed = discord.Embed(
                title="API Error",
                description="❌ Could not contact Last.fm API.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        artists = data.get("topartists", {}).get("artist", [])
        if not artists:
            embed = discord.Embed(
                title="No Artists Found",
                description="No top artists found.",
                color=discord.Color.orange()
            )
            return await ctx.reply(embed=embed)
        msg = "\n".join([f"**{i+1}.** {a['name']} (`{a['playcount']} plays`)" for i, a in enumerate(artists)])
        embed = discord.Embed(
            title=f"Top {limit} artists for {username}",
            description=msg,
            color=discord.Color.purple()
        )
        await ctx.reply(embed=embed)

    @commands.command(aliases=["fmtracks"])
    async def fmtoptracks(self, ctx, user: discord.Member = None, limit: int = 5):
        """Show your (or a user's) top Last.fm tracks."""
        if not LASTFM_API_KEY:
            embed = discord.Embed(
                title="API Key Missing",
                description="❌ Last.fm API key not set.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        if user:
            username, session_key = self.get_linked_user(user.id)
            display_name = user.display_name
        else:
            username, session_key = self.get_linked_user(ctx.author.id)
            display_name = ctx.author.display_name

        if not username or not session_key:
            embed = discord.Embed(
                title="No Link Found",
                description=f"{display_name} has not linked their Last.fm account. Use `.fmlink` to link.",
                color=discord.Color.orange()
            )
            return await ctx.reply(embed=embed)

        data = await self.get_lastfm_data("user.gettoptracks", username, session_key, limit=limit)
        if not data:
            embed = discord.Embed(
                title="API Error",
                description="❌ Could not contact Last.fm API.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        tracks = data.get("toptracks", {}).get("track", [])
        if not tracks:
            embed = discord.Embed(
                title="No Tracks Found",
                description="No top tracks found.",
                color=discord.Color.orange()
            )
            return await ctx.reply(embed=embed)
        msg = "\n".join([f"**{i+1}.** {t['name']} by {t['artist']['name']} (`{t['playcount']} plays`)" for i, t in enumerate(tracks)])
        embed = discord.Embed(
            title=f"Top {limit} tracks for {username}",
            description=msg,
            color=discord.Color.purple()
        )
        await ctx.reply(embed=embed)

    @commands.command()
    async def fminfo(self, ctx, user: discord.Member = None):
        """Show Last.fm profile info and stats."""
        if not LASTFM_API_KEY:
            embed = discord.Embed(
                title="API Key Missing",
                description="❌ Last.fm API key not set.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        if user:
            username, session_key = self.get_linked_user(user.id)
            display_name = user.display_name
            avatar = user.display_avatar.url
        else:
            username, session_key = self.get_linked_user(ctx.author.id)
            display_name = ctx.author.display_name
            avatar = ctx.author.display_avatar.url

        if not username or not session_key:
            embed = discord.Embed(
                title="No Link Found",
                description=f"{display_name} has not linked their Last.fm account. Use `.fmlink` to link.",
                color=discord.Color.orange()
            )
            return await ctx.reply(embed=embed)

        data = await self.get_lastfm_data("user.getinfo", username, session_key)
        if not data:
            embed = discord.Embed(
                title="API Error",
                description="❌ Could not contact Last.fm API.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        userinfo = data.get("user")
        if not userinfo:
            embed = discord.Embed(
                title="Profile Not Found",
                description="Could not fetch Last.fm profile info.",
                color=discord.Color.orange()
            )
            return await ctx.reply(embed=embed)
        embed = discord.Embed(
            title=f"{userinfo['name']}'s Last.fm Profile",
            url=userinfo.get("url", ""),
            color=discord.Color.red(),
            description=f"**Playcount:** {userinfo.get('playcount', 'N/A')}\n"
                        f"**Registered:** {userinfo.get('registered', {}).get('#text', 'N/A')}\n"
                        f"**Country:** {userinfo.get('country', 'N/A')}"
        )
        if userinfo.get("image"):
            embed.set_thumbnail(url=userinfo["image"][-1]["#text"])
        embed.set_author(name=display_name, icon_url=avatar)
        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(LastFM(bot))