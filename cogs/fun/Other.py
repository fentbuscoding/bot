import discord
from discord.ext import commands
import aiohttp
import os
import json

TIMEZONE_FILE = "user_timezones.json"

def load_timezones():
    if os.path.exists(TIMEZONE_FILE):
        with open(TIMEZONE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_timezones(timezones):
    with open(TIMEZONE_FILE, "w", encoding="utf-8") as f:
        json.dump(timezones, f)

class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timezones = load_timezones()

    def set_timezone(self, user_id, tz):
        self.timezones[str(user_id)] = tz
        save_timezones(self.timezones)

    def remove_timezone(self, user_id):
        if str(user_id) in self.timezones:
            del self.timezones[str(user_id)]
            save_timezones(self.timezones)

    def get_timezone(self, user_id):
        return self.timezones.get(str(user_id))

    @commands.command()
    async def settimezone(self, ctx, tz: str):
        """Set your timezone (e.g. UTC, UTC+2, UTC-5, EST, PST)"""
        self.set_timezone(ctx.author.id, tz)
        await ctx.reply(f"🕒 Your timezone has been set to `{tz}`.")

    @commands.command()
    async def removetimezone(self, ctx):
        """Remove your saved timezone."""
        self.remove_timezone(ctx.author.id)
        await ctx.reply("🗑️ Your timezone has been removed.")

    @commands.command()
    async def timezone(self, ctx, user: discord.Member = None):
        """Check a user's timezone (or your own)"""
        user = user or ctx.author
        tz = self.get_timezone(user.id)
        if tz:
            await ctx.reply(f"🕒 {user.display_name}'s timezone: `{tz}`")
        else:
            await ctx.reply(f"Timezone not set for {user.display_name}. They can set it with `.settimezone <zone>`.")

    @commands.command()
    async def listtimezones(self, ctx):
        """List all users with a set timezone in this server."""
        members = [m for m in ctx.guild.members if self.get_timezone(m.id)]
        if not members:
            return await ctx.reply("No one in this server has set a timezone yet.")
        desc = "\n".join(f"• **{m.display_name}**: `{self.get_timezone(m.id)}`" for m in members)
        embed = discord.Embed(title="Server Timezones", description=desc, color=discord.Color.blue())
        await ctx.reply(embed=embed)

    @commands.command()
    async def weather(self, ctx, *, city: str):
        """Check the weather for a city (uses wttr.in, no API key needed)"""
        url = f"https://wttr.in/{city}?format=j1"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await ctx.reply("Could not fetch weather. Check the city name.")
                data = await resp.json()
        try:
            area = data["nearest_area"][0]["areaName"][0]["value"]
            region = data["nearest_area"][0]["region"][0]["value"]
            country = data["nearest_area"][0]["country"][0]["value"]
            current = data["current_condition"][0]
            temp_c = current["temp_C"]
            feels_c = current["FeelsLikeC"]
            weather_desc = current["weatherDesc"][0]["value"]
            humidity = current["humidity"]
            wind = current["windspeedKmph"]
            icon_url = current["weatherIconUrl"][0]["value"]

            embed = discord.Embed(
                title=f"Weather in {area}, {region}, {country}",
                description=f"**{weather_desc}**",
                color=discord.Color.blue()
            )
            embed.add_field(name="Temperature", value=f"{temp_c}°C (feels like {feels_c}°C)")
            embed.add_field(name="Humidity", value=f"{humidity}%")
            embed.add_field(name="Wind", value=f"{wind} km/h")
            embed.set_thumbnail(url=icon_url)
            await ctx.reply(embed=embed)
        except Exception:
            await ctx.reply("Could not parse weather data. Try a different city.")

async def setup(bot):
    await bot.add_cog(Other(bot))