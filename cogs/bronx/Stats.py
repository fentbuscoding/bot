import discord
from discord.ext import commands
from cogs.logging.logger import CogLogger
from cogs.logging.stats_logger import StatsLogger
from utils.db import db

logger = CogLogger('Stats')
guilds = [1259717095382319215, 1299747094449623111, 1142088882222022786]

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.main_guilds = self.bot.MAIN_GUILD_IDS
        self.stats_logger = StatsLogger()

    async def cog_check(self, ctx):
        """Check if the guild has permission to use this cog's commands"""
        return ctx.guild.id in self.main_guilds

    @commands.command(name="stats", aliases=["st"])
    @commands.is_owner()
    async def stats(self, ctx):
        stats = db.get_stats(ctx.guild.id)
        
        embed = discord.Embed(
            description=f"""
            `messages {stats.get('messages', 0)}`
            `members gained {stats.get('gained', 0)}`
            `members lost {stats.get('lost', 0)}`
            `total g/l {stats.get('gained', 0) - stats.get('lost', 0)}`
            """,
            color=discord.Color.random()
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        await ctx.reply(embed=embed)

    @commands.command(name="resetstats", aliases=["rst"])
    @commands.is_owner()
    async def resetstats(self, ctx):
        if db.reset_stats(ctx.guild.id):
            await ctx.reply("Stats have been reset for this guild!")
        else:
            await ctx.reply("Failed to reset stats!")

    @commands.command(name="commandstats", aliases=["cmdstats"])
    async def command_stats(self, ctx):
        """Show command usage statistics"""
        top_commands = self.stats_logger.get_top_commands()
        least_commands = self.stats_logger.get_least_used_commands()
        biggest_wins = self.stats_logger.get_biggest_wins()
        biggest_losses = self.stats_logger.get_biggest_losses()
        
        embed = discord.Embed(
            title="📊 Command Statistics",
            color=0x3498db
        )
        
        # Top commands
        top_cmd_text = "\n".join(
            f"`{i+1}.` {cmd['command']}: **{cmd['count']}** uses"
            for i, cmd in enumerate(top_commands)
        )
        embed.add_field(
            name="🏆 Top Commands",
            value=top_cmd_text or "No data",
            inline=False
        )
        
        # Least used commands
        least_cmd_text = "\n".join(
            f"`{i+1}.` {cmd['command']}: **{cmd['count']}** uses"
            for i, cmd in enumerate(least_commands)
        )
        embed.add_field(
            name="📉 Least Used Commands",
            value=least_cmd_text or "No data",
            inline=False
        )
        
        # Biggest wins
        if biggest_wins:
            win_text = "\n".join(
                f"`{i+1}.` <@{win['user_id']}>: **{win['amount']:,}** (via {win['command']})"
                for i, win in enumerate(biggest_wins[:5]))
            embed.add_field(
                name="💰 Biggest Wins",
                value=win_text,
                inline=True
            )
        
        # Biggest losses
        if biggest_losses:
            loss_text = "\n".join(
                f"`{i+1}.` <@{loss['user_id']}>: **{loss['amount']:,}** (via {loss['command']})"
                for i, loss in enumerate(biggest_losses[:5]))
            embed.add_field(
                name="💸 Biggest Losses",
                value=loss_text,
                inline=True
            )
        
        await ctx.reply(embed=embed)

async def setup(bot):
    try:
        await bot.add_cog(Stats(bot))
    except Exception as e:
        logger.error(f"Failed to load Stats cog: {e}")
        raise e
