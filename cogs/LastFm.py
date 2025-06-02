import discord
from discord.ext import commands
import aiohttp
import os
import json
from utils.db import async_db as db

DATA_PATH = "data/lastfm_links.json"

def get_lastfm_api_key():
    key = os.getenv("LASTFM_API_KEY")
    if key:
        return key
    config_paths = [
        "data/config.json",
        "config.json",
        "./data/config.json",
        "./config.json",
    ]
    for path in config_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
                if "LASTFM_API_KEY" in config:
                    return config["LASTFM_API_KEY"]
                if "lastfm_api_key" in config:
                    return config["lastfm_api_key"]
        except Exception:
            continue
    return None

LASTFM_API_KEY = get_lastfm_api_key()

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

class LastFM(commands.Cog, name="LastFM"):
    """
    🎵 Last.fm Integration
    Commands to link your Discord account to Last.fm and view your music stats.
    """

    def __init__(self, bot):
        self.bot = bot
        self.links = load_links()
        self.db_available = True

    async def cog_load(self):
        # Test DB connection on cog load
        try:
            await db.db.command("ping")
        except Exception:
            self.db_available = False

    async def get_lastfm_data(self, method, user, **params):
        if not LASTFM_API_KEY:
            return None
        url = "http://ws.audioscrobbler.com/2.0/"
        payload = {
            "method": method,
            "user": user,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            **params
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=payload) as resp:
                try:
                    return await resp.json()
                except Exception:
                    return {}

    async def get_linked_user(self, discord_id):
        if self.db_available:
            try:
                user = await db.db.users.find_one({"_id": str(discord_id)})
                return user.get("lastfm") if user and "lastfm" in user else None
            except Exception:
                self.db_available = False
        # fallback to file
        return self.links.get(str(discord_id))

    async def set_linked_user(self, discord_id, lastfm_username):
        if self.db_available:
            try:
                await db.db.users.update_one(
                    {"_id": str(discord_id)},
                    {"$set": {"lastfm": lastfm_username}},
                    upsert=True
                )
                return
            except Exception:
                self.db_available = False
        # fallback to file
        self.links[str(discord_id)] = lastfm_username
        save_links(self.links)

    async def remove_linked_user(self, discord_id):
        if self.db_available:
            try:
                await db.db.users.update_one(
                    {"_id": str(discord_id)},
                    {"$unset": {"lastfm": ""}}
                )
                return
            except Exception:
                self.db_available = False
        # fallback to file
        if str(discord_id) in self.links:
            del self.links[str(discord_id)]
            save_links(self.links)

    @commands.command()
    async def fmlink(self, ctx, lastfm_username: str = None):
        """Link your Discord account to your Last.fm username."""
        if not lastfm_username:
            embed = discord.Embed(
                title="Last.fm Link",
                description="Usage: `.fmlink <your_lastfm_username>`",
                color=discord.Color.orange()
            )
            return await ctx.reply(embed=embed)
        await self.set_linked_user(ctx.author.id, lastfm_username)
        embed = discord.Embed(
            title="Last.fm Linked",
            description=f"✅ Linked your Discord to Last.fm user `{lastfm_username}`.",
            color=discord.Color.green()
        )
        await ctx.reply(embed=embed)

    @commands.command()
    async def fmunlink(self, ctx):
        """Unlink your Last.fm account."""
        linked = await self.get_linked_user(ctx.author.id)
        if linked:
            await self.remove_linked_user(ctx.author.id)
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
        linked = await self.get_linked_user(user.id)
        if linked:
            embed = discord.Embed(
                title="Last.fm Link",
                description=f"{user.mention} is linked to Last.fm user `{linked}`.",
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
    async def fm(self, ctx, user: discord.Member = None, lastfm_username: str = None):
        """Show now playing/last played track for a user or Last.fm username."""
        if not LASTFM_API_KEY:
            embed = discord.Embed(
                title="API Key Missing",
                description="❌ Last.fm API key not set. Please set it in your .env or config.json.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        if user:
            lastfm_user = await self.get_linked_user(user.id)
            display_name = user.display_name
            avatar = user.display_avatar.url
        elif lastfm_username:
            lastfm_user = lastfm_username
            display_name = lastfm_username
            avatar = ctx.author.display_avatar.url
        else:
            lastfm_user = await self.get_linked_user(ctx.author.id)
            display_name = ctx.author.display_name
            avatar = ctx.author.display_avatar.url

        if not lastfm_user:
            embed = discord.Embed(
                title="No Link Found",
                description=f"{display_name} has not linked their Last.fm account. Use `.fmlink <username>` to link, or provide a username.",
                color=discord.Color.orange()
            )
            return await ctx.reply(embed=embed)

        data = await self.get_lastfm_data("user.getrecenttracks", lastfm_user, limit=1)
        if not data:
            embed = discord.Embed(
                title="API Error",
                description="❌ Could not contact Last.fm API. Check your API key.",
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
    async def fmtopartists(self, ctx, user: discord.Member = None, limit: int = 5, lastfm_username: str = None):
        """Show your (or a user's) top Last.fm artists."""
        if not LASTFM_API_KEY:
            embed = discord.Embed(
                title="API Key Missing",
                description="❌ Last.fm API key not set. Please set it in your .env or config.json.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        if user:
            lastfm_user = await self.get_linked_user(user.id)
            display_name = user.display_name
        elif lastfm_username:
            lastfm_user = lastfm_username
            display_name = lastfm_username
        else:
            lastfm_user = await self.get_linked_user(ctx.author.id)
            display_name = ctx.author.display_name

        if not lastfm_user:
            embed = discord.Embed(
                title="No Link Found",
                description=f"{display_name} has not linked their Last.fm account. Use `.fmlink <username>` to link, or provide a username.",
                color=discord.Color.orange()
            )
            return await ctx.reply(embed=embed)

        data = await self.get_lastfm_data("user.gettopartists", lastfm_user, limit=limit)
        if not data:
            embed = discord.Embed(
                title="API Error",
                description="❌ Could not contact Last.fm API. Check your API key.",
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
            title=f"Top {limit} artists for {lastfm_user}",
            description=msg,
            color=discord.Color.purple()
        )
        await ctx.reply(embed=embed)

    @commands.command(aliases=["fmtracks"])
    async def fmtoptracks(self, ctx, user: discord.Member = None, limit: int = 5, lastfm_username: str = None):
        """Show your (or a user's) top Last.fm tracks."""
        if not LASTFM_API_KEY:
            embed = discord.Embed(
                title="API Key Missing",
                description="❌ Last.fm API key not set. Please set it in your .env or config.json.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        if user:
            lastfm_user = await self.get_linked_user(user.id)
            display_name = user.display_name
        elif lastfm_username:
            lastfm_user = lastfm_username
            display_name = lastfm_username
        else:
            lastfm_user = await self.get_linked_user(ctx.author.id)
            display_name = ctx.author.display_name

        if not lastfm_user:
            embed = discord.Embed(
                title="No Link Found",
                description=f"{display_name} has not linked their Last.fm account. Use `.fmlink <username>` to link, or provide a username.",
                color=discord.Color.orange()
            )
            return await ctx.reply(embed=embed)

        data = await self.get_lastfm_data("user.gettoptracks", lastfm_user, limit=limit)
        if not data:
            embed = discord.Embed(
                title="API Error",
                description="❌ Could not contact Last.fm API. Check your API key.",
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
            title=f"Top {limit} tracks for {lastfm_user}",
            description=msg,
            color=discord.Color.purple()
        )
        await ctx.reply(embed=embed)

    @commands.command()
    async def fminfo(self, ctx, user: discord.Member = None, lastfm_username: str = None):
        """Show Last.fm profile info and stats."""
        if not LASTFM_API_KEY:
            embed = discord.Embed(
                title="API Key Missing",
                description="❌ Last.fm API key not set. Please set it in your .env or config.json.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        if user:
            lastfm_user = await self.get_linked_user(user.id)
            display_name = user.display_name
            avatar = user.display_avatar.url
        elif lastfm_username:
            lastfm_user = lastfm_username
            display_name = lastfm_username
            avatar = ctx.author.display_avatar.url
        else:
            lastfm_user = await self.get_linked_user(ctx.author.id)
            display_name = ctx.author.display_name
            avatar = ctx.author.display_avatar.url

        if not lastfm_user:
            embed = discord.Embed(
                title="No Link Found",
                description=f"{display_name} has not linked their Last.fm account. Use `.fmlink <username>` to link, or provide a username.",
                color=discord.Color.orange()
            )
            return await ctx.reply(embed=embed)

        data = await self.get_lastfm_data("user.getinfo", lastfm_user)
        if not data:
            embed = discord.Embed(
                title="API Error",
                description="❌ Could not contact Last.fm API. Check your API key.",
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