from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import async_db as db
from utils.betting import parse_bet
import discord
import random
import asyncio
from functools import wraps
from discord.ext import commands
from cogs.logging.stats_logger import StatsLogger

class Work(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.currency = "<:bronkbuk:1377389238290747582>"


    @commands.command(name="work", aliases=["w"])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def work(self, ctx):
        """Work for some money"""
        amount = random.randint(50, 200)
        await db.update_wallet(ctx.author.id, amount, ctx.guild.id)
        await ctx.reply(f"You worked and earned **{amount}** {self.currency}")


async def setup(bot):
    await bot.add_cog(Work(bot))