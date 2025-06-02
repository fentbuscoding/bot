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


    @commands.command(name="work", aliases=["wrk", "earn"])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def work(self, ctx):
        """Work for some money"""
        amount = random.randint(100, 1800)
        await db.update_wallet(ctx.author.id, amount, ctx.guild.id)
        responses = [
            f"You worked hard and earned **{amount}** {self.currency}!",
            f"Great effort! You just made **{amount}** {self.currency}.",
            f"Your dedication paid off! You received **{amount}** {self.currency}.",
            f"Well done! You've earned **{amount}** {self.currency}.",
            f"Awesome work! You've collected **{amount}** {self.currency}.",
            f"Success! You gained **{amount}** {self.currency} from your work.",
            f"Keep it up! You earned **{amount}** {self.currency}.",
            f"Fantastic job! You made **{amount}** {self.currency}.",
            f"Your hard work has been rewarded with **{amount}** {self.currency}.",
            f"You put in the effort and earned **{amount}** {self.currency}.",
            f"Your labor was fruitful! You received **{amount}** {self.currency}.",
            f"You've been productive! You earned **{amount}** {self.currency}.",
            f"Your work ethic is impressive! You made **{amount}** {self.currency}.",
            f"You've shown great diligence! You earned **{amount}** {self.currency}.",
            f"Your commitment to work has paid off! You received **{amount}** {self.currency}.",
            f"You've been industrious! You earned **{amount}** {self.currency}.",
            f"Your efforts have been fruitful! You made **{amount}** {self.currency}.",
            f"You've been a hard worker! You earned **{amount}** {self.currency}.",
            f"You've shown great perseverance! You received **{amount}** {self.currency}.",
            f"You've been diligent! You earned **{amount}** {self.currency}.",
            f"You've been a model employee! You made **{amount}** {self.currency}.",
            f"You've been a star worker! You earned **{amount}** {self.currency}.",
            f"You've been a top performer! You received **{amount}** {self.currency}.",
            f"You've been a valuable asset! You earned **{amount}** {self.currency}.",
            f"You've been a key contributor! You made **{amount}** {self.currency}.",
        ]
        await ctx.reply(random.choice(responses))


async def setup(bot):
    await bot.add_cog(Work(bot))