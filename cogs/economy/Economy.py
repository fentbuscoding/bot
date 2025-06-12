from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import async_db as db
from utils.betting import parse_bet
from utils.amount_parser import parse_amount, get_amount_help_text
from utils.safe_reply import safe_reply
from utils.tos_handler import check_tos_acceptance, prompt_tos_acceptance
import discord
import random
import json
import asyncio
import datetime
from functools import wraps
from discord.ext import commands
from cogs.logging.stats_logger import StatsLogger

with open('data/config.json', 'r') as f:
    data = json.load(f)

def log_command(func):
    """Decorator to log command usage"""
    @wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        if hasattr(self, 'stats_logger'):
            self.stats_logger.log_command_usage(func.__name__)
        return await func(self, ctx, *args, **kwargs)
    return wrapper

def logged_command(*args, **kwargs):
    """Custom command decorator that adds logging"""
    def decorator(func):
        # First apply the command decorator
        cmd = logged_command(*args, **kwargs)(func)
        # Then apply the logging decorator
        return log_command(cmd)
    return decorator

class PaymentConfirmView(discord.ui.View):
    """Payment confirmation view for the receiving user"""
    
    def __init__(self, sender: discord.Member, receiver: discord.Member, amount: int, currency: str):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.currency = currency
        self.responded = False
    
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, emoji="✅")
    async def accept_payment(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id:
            return await interaction.response.send_message("❌ Only the payment recipient can respond!", ephemeral=True)
        
        if self.responded:
            return await interaction.response.send_message("❌ This payment has already been responded to!", ephemeral=True)
        
        self.responded = True
        
        # Process the payment
        success = await db.transfer_money(self.sender.id, self.receiver.id, self.amount, interaction.guild.id)
        
        if success:
            embed = discord.Embed(
                title="✅ Payment Accepted!",
                description=f"Successfully transferred **{self.amount:,}** {self.currency}",
                color=discord.Color.green()
            )
            embed.add_field(name="From:", value=self.sender.display_name, inline=True)
            embed.add_field(name="To:", value=self.receiver.display_name, inline=True)
            embed.add_field(name="Amount:", value=f"{self.amount:,} {self.currency}", inline=True)
            
            # Send a notification to the sender
            try:
                sender_embed = discord.Embed(
                    title="💰 Payment Completed!",
                    description=f"{self.receiver.display_name} accepted your payment of **{self.amount:,}** {self.currency}",
                    color=discord.Color.green()
                )
                await self.sender.send(embed=sender_embed)
            except discord.Forbidden:
                pass  # Sender has DMs disabled
        else:
            embed = discord.Embed(
                title="❌ Payment Failed!",
                description=f"The sender ({self.sender.display_name}) has insufficient funds.",
                color=discord.Color.red()
            )
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red, emoji="❌")
    async def decline_payment(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id:
            return await interaction.response.send_message("❌ Only the payment recipient can respond!", ephemeral=True)
        
        if self.responded:
            return await interaction.response.send_message("❌ This payment has already been responded to!", ephemeral=True)
        
        self.responded = True
        
        embed = discord.Embed(
            title="❌ Payment Declined",
            description=f"{self.receiver.display_name} declined the payment of **{self.amount:,}** {self.currency}",
            color=discord.Color.red()
        )
        embed.add_field(name="From:", value=self.sender.display_name, inline=True)
        embed.add_field(name="Amount:", value=f"{self.amount:,} {self.currency}", inline=True)
        
        # Send a notification to the sender
        try:
            sender_embed = discord.Embed(
                title="❌ Payment Declined",
                description=f"{self.receiver.display_name} declined your payment of **{self.amount:,}** {self.currency}",
                color=discord.Color.red()
            )
            await self.sender.send(embed=sender_embed)
        except discord.Forbidden:
            pass  # Sender has DMs disabled
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Called when the view times out"""
        if not self.responded:
            embed = discord.Embed(
                title="⏰ Payment Expired",
                description=f"Payment request from {self.sender.display_name} has expired",
                color=discord.Color.orange()
            )
            embed.add_field(name="Amount:", value=f"{self.amount:,} {self.currency}", inline=True)
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            # Try to edit the message (may fail if message was deleted)
            try:
                if hasattr(self, 'message') and self.message:
                    await self.message.edit(embed=embed, view=self)
            except:
                pass  # Message might have been deleted

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.currency = "<:bronkbuk:1377389238290747582>"
        self.active_games = set()
        self.stats_logger = StatsLogger()
        self.blocked_channels = [1378156495144751147, 1260347806699491418]
    
    # piece de resistance: cog_check
    async def cog_check(self, ctx):
        """Global check for all commands in this cog"""
        # Check if economy commands are disabled in this channel
        if ctx.channel.id in self.blocked_channels and not ctx.author.guild_permissions.administrator:
            await safe_reply(ctx,
                random.choice([f"❌ Economy commands are disabled in this channel. "
                f"Please use them in another channel.",
                "<#1314685928614264852> is a good place for that."])
            )
            return False
        
        # Check if user has accepted ToS
        if not await check_tos_acceptance(ctx.author.id):
            await prompt_tos_acceptance(ctx)
            return False
            
        return True
    
    @commands.command(aliases=['bal', 'cash', 'bb'])
    async def balance(self, ctx, member: discord.Member = None):
        """Check your balance"""
        member = member or ctx.author
        wallet = await db.get_wallet_balance(member.id, ctx.guild.id)
        bank = await db.get_bank_balance(member.id, ctx.guild.id)
        bank_limit = await db.get_bank_limit(member.id, ctx.guild.id)
        
        badge = await db.get_badge(member.id, ctx.guild.id)
        embed = discord.Embed(
            description=(
                f"💵 Wallet: **{wallet:,}** {self.currency}\n"
                f"🏦 Bank: **{bank:,}**/**{bank_limit:,}** {self.currency}\n"
                f"💰 Net Worth: **{wallet + bank:,}** {self.currency}"
            ),
            color=member.color
        )
        if badge:
            embed.title = f"{badge} | {member.display_name}'s Balance"
        else:
            embed.set_author(name=f"{member.display_name}'s Balance", icon_url=member.display_avatar.url)
        if member != ctx.author:
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        try:
            await safe_reply(ctx, embed=embed)
        except Exception as e:
            self.logger.error(f"Failed to send balance embed in {ctx.channel.name}. User: {ctx.author.id}, Member: {member.id}: {e}")
            await safe_reply(ctx, "An error occurred while displaying the balance.")

    @commands.command(name="deposit", aliases=["dep", 'd'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def deposit(self, ctx, amount: str = None):
        """Deposit money into your bank"""
        try:
            if not amount:
                wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
                bank = await db.get_bank_balance(ctx.author.id, ctx.guild.id)
                limit = await db.get_bank_limit(ctx.author.id, ctx.guild.id)
                space = limit - bank
                if space <= 0:
                    return await safe_reply(ctx, "Your bank is **full**! Upgrade your bank *(`.bu`)* to deposit more.")
                
                embed = discord.Embed(
                    description=(
                        "**BronkBuks Bank Deposit Guide**\n\n"
                        f"Your Wallet: **{wallet:,}** {self.currency}\n"
                        f"Bank Space: **{space:,}** {self.currency}\n\n"
                        "**Usage:**\n"
                        "`.deposit <amount>`\n"
                        "`.deposit 50%` - Deposit 50% of wallet\n"
                        "`.deposit all` - Deposit maximum amount\n"
                        "`.deposit 1k` - Deposit 1,000\n"
                        "`.deposit 1.5m` - Deposit 1,500,000\n"
                        "`.deposit 2b` - Deposit 2,000,000,000\n"
                        "`.deposit 1e3` - Deposit 1,000 (scientific notation)\n"
                        "`.deposit 2.5e5` - Deposit 250,000 (scientific notation)"
                    ),
                    color=0x2b2d31
                )
                return await safe_reply(ctx, embed=embed)

            wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            bank = await db.get_bank_balance(ctx.author.id, ctx.guild.id)
            limit = await db.get_bank_limit(ctx.author.id, ctx.guild.id)
            space = limit - bank

            # Parse amount using the new unified parser
            parsed_amount, error = parse_amount(amount, wallet, max_amount=space, context="wallet")
            
            if error:
                return await safe_reply(ctx, f"❌ {error}")

            if parsed_amount <= 0:
                return await safe_reply(ctx, "Amount must be positive!")
            if parsed_amount > wallet:
                return await safe_reply(ctx, "You don't have that much in your wallet!")
            if parsed_amount > space:
                return await safe_reply(ctx, f"Your bank can only hold {space:,} more coins!")

            if await db.update_wallet(ctx.author.id, -parsed_amount, ctx.guild.id):
                if await db.update_bank(ctx.author.id, parsed_amount, ctx.guild.id):
                    # Log successful deposit
                    self.stats_logger.log_command_usage("deposit")
                    await safe_reply(ctx, f"💰 Deposited **{parsed_amount:,}** {self.currency} into your bank!")
                else:
                    await db.update_wallet(ctx.author.id, parsed_amount, ctx.guild.id)
                    await safe_reply(ctx, "❌ Failed to deposit money! Transaction reverted.")
            else:
                await safe_reply(ctx, "❌ Failed to deposit money!")
                
        except Exception as e:
            self.logger.error(f"Deposit error: {e}")
            await safe_reply(ctx, "An error occurred while processing your deposit.")

    @commands.command(name="withdraw", aliases=["with", 'w'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def withdraw(self, ctx, amount: str = None):
        """Withdraw money from your bank"""
        try:
            if not amount:
                wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
                bank = await db.get_bank_balance(ctx.author.id, ctx.guild.id)
                
                embed = discord.Embed(
                    description=(
                        "**BronkBuks Bank Withdrawal Guide**\n\n"
                        f"Your Bank: **{bank:,}** {self.currency}\n"
                        f"Your Wallet: **{wallet:,}** {self.currency}\n\n"
                        "**Usage:**\n"
                        "`.withdraw <amount>`\n"
                        "`.withdraw 50%` - Withdraw 50% of bank\n"
                        "`.withdraw all` - Withdraw everything\n"
                        "`.withdraw 1k` - Withdraw 1,000\n"
                        "`.withdraw 1.5m` - Withdraw 1,500,000\n"
                        "`.withdraw 2b` - Withdraw 2,000,000,000\n"
                        "`.withdraw 1e3` - Withdraw 1,000 (scientific notation)\n"
                        "`.withdraw 2.5e5` - Withdraw 250,000 (scientific notation)"
                    ),
                    color=0x2b2d31
                )
                return await safe_reply(ctx, embed=embed)

            bank = await db.get_bank_balance(ctx.author.id, ctx.guild.id)

            # Parse amount using the new unified parser
            parsed_amount, error = parse_amount(amount, bank, context="bank")
            
            if error:
                return await safe_reply(ctx, f"❌ {error}")

            if parsed_amount <= 0:
                return await safe_reply(ctx, "Amount must be positive!")
            if parsed_amount > bank:
                return await safe_reply(ctx, "You don't have that much in your bank!")

            if await db.update_bank(ctx.author.id, -parsed_amount, ctx.guild.id):
                if await db.update_wallet(ctx.author.id, parsed_amount, ctx.guild.id):
                    await safe_reply(ctx, f"💸 Withdrew **{parsed_amount:,}** {self.currency} from your bank!")
                else:
                    await db.update_bank(ctx.author.id, parsed_amount, ctx.guild.id)
                    await safe_reply(ctx, "❌ Failed to withdraw money! Transaction reverted.")
            else:
                await safe_reply(ctx, "❌ Failed to withdraw money!")
        except Exception as e:
            self.logger.error(f"Withdraw error: {e}")
            await ctx.reply("An error occurred while processing your withdrawal.")

    @commands.command(name="pay", aliases=["transfer"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def pay(self, ctx, member: discord.Member, amount: str = None):
        """Transfer money to another user"""
        if not amount:
            wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            
            embed = discord.Embed(
                description=(
                    f"**BronkBuks Payment Guide**\n\n"
                    f"Your Wallet: **{wallet:,}** {self.currency}\n\n"
                    f"**Usage:**\n"
                    f"`.pay @user <amount>`\n"
                    f"`.pay @user 50%` - Send 50% of wallet\n"
                    f"`.pay @user all` - Send everything\n"
                    f"`.pay @user half` - Send half of wallet\n"
                    f"`.pay @user 1k` - Send 1,000\n"
                    f"`.pay @user 1.5m` - Send 1,500,000\n"
                    f"`.pay @user 2b` - Send 2,000,000,000\n"
                    f"`.pay @user 1e3` - Send 1,000 (scientific notation)\n"
                    f"`.pay @user 2.5e5` - Send 250,000 (scientific notation)"
                ),
                color=0x2b2d31
            )
            return await safe_reply(ctx, embed=embed)
        
        if member == ctx.author:
            return await ctx.reply("You can't pay yourself!")
        
        # Get sender's wallet balance
        sender_balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        
        # Parse the amount using the new parser
        parsed_amount, error = parse_amount(amount, sender_balance, context="wallet")
        
        if error:
            return await ctx.reply(f"❌ {error}")
        
        if parsed_amount <= 0:
            return await ctx.reply("Amount must be positive!")
        
        if parsed_amount > sender_balance:
            return await ctx.reply("Insufficient funds!")
        
        # Create payment confirmation for receiver
        view = PaymentConfirmView(ctx.author, member, parsed_amount, self.currency)
        
        embed = discord.Embed(
            title="💳 Payment Confirmation Required",
            description=f"{ctx.author.mention} wants to send you **{parsed_amount:,}** {self.currency}",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="From:",
            value=ctx.author.display_name,
            inline=True
        )
        embed.add_field(
            name="Amount:",
            value=f"{parsed_amount:,} {self.currency}",
            inline=True
        )
        embed.add_field(
            name="Action Required:",
            value="Click **Accept** or **Decline** below",
            inline=False
        )
        embed.set_footer(text="This payment request will expire in 5 minutes")
        
        message = await ctx.reply(f"{member.mention}", embed=embed, view=view)
        view.message = message  # Store message reference for timeout handling

    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def daily(self, ctx):
        """Claim your daily reward"""
        amount = random.randint(1000, 5000)
        await db.update_wallet(ctx.author.id, amount, ctx.guild.id)
        await ctx.reply(f"Daily reward claimed! +**{amount}** {self.currency}")

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def beg(self, ctx):
        """Beg for money"""
        amount = random.randint(0, 150)
        await db.update_wallet(ctx.author.id, amount, ctx.guild.id)
        await ctx.reply(f"you got +**{amount}** {self.currency}")

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def rob(self, ctx, victim: discord.Member):
        """Attempt to rob someone"""
        if victim == ctx.author:
            return await ctx.reply("You can't rob yourself!")
        
        author_bal = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        victim_bal = await db.get_wallet_balance(victim.id, ctx.guild.id)
        if victim_bal < 100:
            return await ctx.reply("They're too poor to rob!")
        
        chance = random.random()
        if chance < 0.6:  # 60% chance to fail
            fine = int((random.random() * 0.3 + 0.1) * author_bal)

            await db.update_wallet(ctx.author.id, -fine, ctx.guild.id)
            await db.update_wallet(victim.id, fine, ctx.guild.id)
            return await ctx.reply(f"You got caught and paid **{fine}** {self.currency} in fines!")
        
        stolen = int(victim_bal * random.uniform(0.1, 0.5))
        await db.update_wallet(victim.id, -stolen, ctx.guild.id)
        await db.update_wallet(ctx.author.id, stolen, ctx.guild.id)
        await ctx.reply(f"You stole **{stolen}** {self.currency} from {victim.mention}!")

    @commands.command(aliases=['lb', 'glb'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def leaderboard(self, ctx, scope: str = "server"):
        """View the richest users"""
        if scope.lower() in ["global", "g", "world", "all"]:
            return await self._show_global_leaderboard(ctx)
        else:
            return await self._show_server_leaderboard(ctx)

    async def _show_server_leaderboard(self, ctx):
        """Show server-specific leaderboard"""
        try:
            if not await db.ensure_connected():
                return await ctx.reply(embed=discord.Embed(
                    description="❌ Database connection failed", 
                    color=0xff0000
                ))

            member_ids = [str(member.id) for member in ctx.guild.members if not member.bot]
            
            if not member_ids:
                return await ctx.reply(embed=discord.Embed(
                    description="No users found in this server",
                    color=0x2b2d31
                ))

            cursor = db.db.users.find({
                "_id": {"$in": member_ids},
                "$or": [
                    {"wallet": {"$gt": 0}},
                    {"bank": {"$gt": 0}}
                ]
            })

            users = []
            async for user_doc in cursor:
                member = ctx.guild.get_member(int(user_doc["_id"]))
                if member:
                    total = user_doc.get("wallet", 0) + user_doc.get("bank", 0)
                    users.append({
                        "member": member,
                        "total": round(total)
                    })

            if not users:
                embed = discord.Embed(
                    description="No economy data for this server.", 
                    color=0x2b2d31
                )
                return await ctx.reply(embed=embed)
            
            users.sort(key=lambda x: x["total"], reverse=True)
            users = users[:10]
            
            content = []
            total_wealth = sum(user["total"] for user in users)
            position_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
            
            for i, user in enumerate(users, 1):
                total = user["total"]
                formatted_amount = "{:,}".format(total)
                position = position_emojis.get(i, f"`{i}.`")
                
                # Add percentage for top 3
                percentage_text = ""
                if i <= 3 and total_wealth > 0:
                    percentage = (total / total_wealth) * 100
                    percentage_text = f" ***({percentage:.1f}%)***"
                
                content.append(f"{position} {user['member'].display_name} • **{formatted_amount}** {self.currency} {percentage_text}")
            
            embed = discord.Embed(
                title=f"💰 Richest Users in {ctx.guild.name}",
                description="\n".join(content),
                color=0x2b2d31
            )
            
            formatted_total = "{:,}".format(total_wealth)
            average_wealth = "{:,}".format(total_wealth // len(content)) if content else "0"
            embed.set_footer(text=f"Total Wealth: ${formatted_total} $BB • Average: ${average_wealth} $BB")
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Leaderboard error: {e}")
            return await ctx.reply(embed=discord.Embed(
                description="❌ An error occurred while fetching the leaderboard", 
                color=0xff0000
            ))

    async def _show_global_leaderboard(self, ctx):
        """Show global leaderboard"""
        try:
            if not await db.ensure_connected():
                return await ctx.reply(embed=discord.Embed(
                    description="❌ Database connection failed", 
                    color=0xff0000
                ))
            
            pipeline = [
                {
                    "$group": {
                        "_id": "$_id",
                        "total": {"$sum": {"$add": ["$wallet", "$bank"]}}
                    }
                },
                {"$sort": {"total": -1}},
                {"$limit": 10}
            ]
            
            users = await db.db.users.aggregate(pipeline).to_list(10)
            
            if not users:
                return await ctx.reply(embed=discord.Embed(
                    description="No global economy data found", 
                    color=0x2b2d31
                ))
            
            content = []
            total_wealth = sum(user['total'] for user in users)
            position_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
            
            for i, user in enumerate(users, 1):
                user_id = int(user['_id'])
                total = user['total']
                
                member = ctx.guild.get_member(user_id) or self.bot.get_user(user_id)
                
                if member:
                    position = position_emojis.get(i, f"`{i}.`")
                    display_name = getattr(member, 'display_name', member.name)
                    
                    # Add percentage for top 3
                    percentage_text = ""
                    if i <= 3 and total_wealth > 0:
                        percentage = (total / total_wealth) * 100
                        percentage_text = f" **({percentage:.1f}%)**"
                    
                    content.append(f"{position} {display_name} • **{total:,}**{percentage_text} {self.currency}")
            
            if not content:
                return await ctx.reply(embed=discord.Embed(
                    description="No active users found", 
                    color=0x2b2d31
                ))
            
            embed = discord.Embed(
                title="🌎 Global Economy Leaderboard",
                description="\n".join(content),
                color=0x2b2d31
            )
            
            formatted_total = "{:,}".format(total_wealth)
            average_wealth = "{:,}".format(total_wealth // len(content)) if content else "0"
            embed.set_footer(text=f"Total Wealth: ${formatted_total} • Average: ${average_wealth}")
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Global leaderboard error: {e}")
            return await ctx.reply(embed=discord.Embed(
                description="❌ An error occurred while fetching the global leaderboard", 
                color=0xff0000
            ))

    async def calculate_daily_interest(self, user_id: int, guild_id: int = None) -> float:
        """Calculate and apply daily interest"""
        try:
            wallet = await db.get_wallet_balance(user_id, guild_id)
            bank = await db.get_bank_balance(user_id, guild_id)
            interest_level = await db.get_interest_level(user_id)

            base_rate = 0.0003  # Base rate of 0.03%
            level_bonus = interest_level * 0.0005  # Each level adds 0.05% (0.0005)
            random_bonus = random.randint(0, 100) / 100000  # 0-0.1% random bonus
            total_rate = base_rate + level_bonus + random_bonus
            
            # Calculate interest based on wallet + bank balance
            total_balance = wallet + bank
            interest = total_balance * total_rate
            
            # Apply minimum (1 coin) and maximum (1% of total balance) bounds
            interest = max(1, min(interest, total_balance * 0.01))
            
            # Apply the interest to wallet
            if await db.update_wallet(user_id, int(interest), guild_id):
                return interest
            return 0
        except Exception as e:
            self.logger.error(f"Calculate daily interest error: {e}")
            return 0

    @commands.command(aliases=['interest', 'i'])
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def claim_interest(self, ctx):
        """Claim your daily interest"""
        try:
            interest = await self.calculate_daily_interest(ctx.author.id, ctx.guild.id)
            if interest > 0:
                await safe_reply(ctx, f"💰 You earned **{int(interest):,}** {self.currency} in daily interest!")
            else:
                await safe_reply(ctx, "❌ Failed to claim interest. Try again later.")
        except Exception as e:
            self.logger.error(f"Claim interest error: {e}")
            await safe_reply(ctx, "❌ An error occurred while claiming interest.")

    
    @commands.command(aliases=['interest_info', 'ii'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def interest_status(self, ctx):
        """Check your current interest rate and level"""
        wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
        bank = await db.get_bank_balance(ctx.author.id, ctx.guild.id)
        total_balance = wallet + bank
        level = await db.get_interest_level(ctx.author.id)
        
        # Calculate current rate in percentage
        current_rate_percent = (0.03 + (level * 0.05))  # 0.03% base + 0.05% per level
        next_rate_percent = (0.03 + ((level + 1) * 0.05)) if level < 60 else current_rate_percent
        
        # Calculate estimated earnings (without random bonus for display)
        estimated_interest = total_balance * (current_rate_percent / 100)
        estimated_interest = max(1, min(estimated_interest, total_balance * 0.01))
        
        embed = discord.Embed(
            title="Interest Account Status",
            description=(
                f"**Current Level:** {level}/60\n"
                f"**Daily Interest Rate:** {current_rate_percent:.2f}%\n"
                f"**Wallet Balance:** {wallet:,} {self.currency}\n"
                f"**Bank Balance:** {bank:,} {self.currency}\n"
                f"**Estimated Daily Earnings:** {int(estimated_interest):,} {self.currency}\n"
                f"**Next Level Rate:** {next_rate_percent:.2f}%\n"
                f"*Actual earnings may vary slightly due to random bonus*"
            ),
            color=discord.Color.blue()
        )
        
        if level < 60:
            base_cost = 1000
            cost = base_cost * (level + 1)
            embed.add_field(
                name="Next Upgrade",
                value=f"Cost: **{cost:,}** {self.currency}\n" + 
                    ("*Requires Interest Token*" if level >= 20 else ""),
                inline=False
            )
        
        await ctx.reply(embed=embed)

    @commands.command(aliases=['upgrade_interest', 'iu'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def interest_upgrade(self, ctx):
        """Upgrade your daily interest rate"""
        
        async def create_upgrade_embed(user_id):
            current_level = await db.get_interest_level(user_id)
            if current_level >= 60:
                embed = discord.Embed(
                    title="Interest Rate Upgrade",
                    description="You've reached the maximum interest level!",
                    color=discord.Color.gold()
                )
                return embed, None, True
            
            base_cost = 1000
            cost = base_cost * (current_level + 1)
            item_required = current_level >= 20
            
            # Display rates in percentage form
            current_rate = 0.003 + (current_level * 0.05)
            next_rate = 0.003 + ((current_level + 1) * 0.05)
            
            embed = discord.Embed(
                title="Interest Rate Upgrade",
                description=(
                    f"Current interest level: **{current_level}**\n"
                    f"Next level cost: **{cost:,}** {self.currency}\n"
                    f"Item required: {'Yes' if item_required else 'No'}\n\n"
                    f"Your current daily interest rate: **{current_rate:.3f}%**\n"
                    f"Next level rate: **{next_rate:.3f}%**"
                ),
                color=discord.Color.green()
            )
            
            if item_required:
                embed.add_field(
                    name="Special Item Required",
                    value="You need an **Interest Token** to upgrade beyond level 20!",
                    inline=False
                )
            
            view = discord.ui.View()
            confirm_button = discord.ui.Button(label="Upgrade", style=discord.ButtonStyle.green)
            
            async def confirm_callback(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This isn't your upgrade!", ephemeral=True)
                
                fresh_level = await db.get_interest_level(ctx.author.id)
                fresh_cost = base_cost * (fresh_level + 1)
                fresh_item_required = fresh_level >= 20
                
                success, message = await db.upgrade_interest(ctx.author.id, fresh_cost, fresh_item_required)
                
                if success:
                    new_embed, new_view, max_reached = await create_upgrade_embed(ctx.author.id)
                    if max_reached:
                        await interaction.response.edit_message(embed=new_embed, view=None)
                    else:
                        await interaction.response.edit_message(embed=new_embed, view=new_view)
                else:
                    error_embed = discord.Embed(
                        description=f"❌ {message}",
                        color=discord.Color.red()
                    )
                    await interaction.response.edit_message(embed=error_embed, view=None)
                    await asyncio.sleep(3)
                    original_embed, original_view, _ = await create_upgrade_embed(ctx.author.id)
                    await interaction.edit_original_response(embed=original_embed, view=original_view)
            
            confirm_button.callback = confirm_callback
            view.add_item(confirm_button)
            
            cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.red)
            
            async def cancel_callback(interaction):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("This isn't your upgrade!", ephemeral=True)
                await interaction.response.edit_message(content="Upgrade cancelled.", embed=None, view=None)
            
            cancel_button.callback = cancel_callback
            view.add_item(cancel_button)
            
            return embed, view, False
        
        embed, view, max_reached = await create_upgrade_embed(ctx.author.id)
        await ctx.reply(embed=embed, view=view if not max_reached else None)

    @commands.command(aliases=['upgrade_bank', 'bu'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def bankupgrade(self, ctx):
        """Upgrade your bank capacity with improved options"""
        
        async def create_upgrade_embed(user_id, guild_id):
            # Get current bank stats
            current_limit = await db.get_bank_limit(user_id, guild_id)
            current_balance = await db.get_bank_balance(user_id, guild_id)
            wallet_balance = await db.get_wallet_balance(user_id, guild_id)
            
            # Dynamic pricing formula
            base_cost = 1000
            upgrade_cost = int(current_limit * 0.1) + base_cost
            new_limit = current_limit + 5000
            
            # Check affordability from both sources
            can_afford_bank = current_balance >= upgrade_cost
            can_afford_wallet = wallet_balance >= upgrade_cost
            can_afford_combined = (current_balance + wallet_balance) >= upgrade_cost
            
            # Calculate max upgrades possible
            max_from_bank = current_balance // upgrade_cost if upgrade_cost > 0 else 0
            max_from_wallet = wallet_balance // upgrade_cost if upgrade_cost > 0 else 0
            max_combined = (current_balance + wallet_balance) // upgrade_cost if upgrade_cost > 0 else 0
            
            # Create embed
            embed = discord.Embed(
                title="🏦 Bank Upgrade Center",
                color=0x2ecc71 if can_afford_combined else 0xe74c3c,
                description=(
                    f"**Current Status:**\n"
                    f"🏦 Bank Limit: **{current_limit:,}** {self.currency}\n"
                    f"💰 Bank Balance: **{current_balance:,}** {self.currency}\n"
                    f"💵 Wallet Balance: **{wallet_balance:,}** {self.currency}\n\n"
                    f"**Upgrade Details:**\n"
                    f"💲 Cost per Upgrade: **{upgrade_cost:,}** {self.currency}\n"
                    f"📈 New Limit: **{new_limit:,}** {self.currency} (+5,000)\n"
                    f"🔢 Max Possible: **{max_combined}** upgrades"
                )
            )
            
            if not can_afford_combined:
                needed = upgrade_cost - (current_balance + wallet_balance)
                embed.add_field(
                    name="💸 Insufficient Funds",
                    value=f"You need **{needed:,}** more {self.currency} to upgrade!",
                    inline=False
                )
            else:
                funding_options = []
                if can_afford_bank:
                    funding_options.append(f"🏦 From Bank (Max: {max_from_bank})")
                if can_afford_wallet:
                    funding_options.append(f"💵 From Wallet (Max: {max_from_wallet})")
                if not can_afford_bank and not can_afford_wallet:
                    funding_options.append(f"🔄 Combined Funds")
                
                embed.add_field(
                    name="💳 Payment Options",
                    value="\n".join(funding_options),
                    inline=False
                )
            
            # Create view with improved buttons
            view = discord.ui.View(timeout=180)
            
            if can_afford_combined:
                # Row 0: Single upgrade buttons
                if can_afford_bank:
                    bank_button = discord.ui.Button(
                        label="Upgrade (Bank)", 
                        style=discord.ButtonStyle.primary,
                        emoji="🏦",
                        row=0
                    )
                    bank_button.callback = lambda i: self._handle_upgrade(i, ctx, user_id, guild_id, 1, "bank")
                    view.add_item(bank_button)
                
                if can_afford_wallet:
                    wallet_button = discord.ui.Button(
                        label="Upgrade (Wallet)", 
                        style=discord.ButtonStyle.secondary,
                        emoji="💵",
                        row=0
                    )
                    wallet_button.callback = lambda i: self._handle_upgrade(i, ctx, user_id, guild_id, 1, "wallet")
                    view.add_item(wallet_button)
                
                if not can_afford_bank and not can_afford_wallet and can_afford_combined:
                    combined_button = discord.ui.Button(
                        label="Upgrade (Combined)", 
                        style=discord.ButtonStyle.primary,
                        emoji="🔄",
                        row=0
                    )
                    combined_button.callback = lambda i: self._handle_upgrade(i, ctx, user_id, guild_id, 1, "combined")
                    view.add_item(combined_button)
                
                # Row 1: Max upgrade buttons (if more than 1 possible)
                if max_combined > 1:
                    if max_from_bank > 1 and can_afford_bank:
                        max_bank_button = discord.ui.Button(
                            label=f"Max {max_from_bank} (Bank)", 
                            style=discord.ButtonStyle.success,
                            emoji="🏦",
                            row=1
                        )
                        max_bank_button.callback = lambda i: self._handle_upgrade(i, ctx, user_id, guild_id, max_from_bank, "bank")
                        view.add_item(max_bank_button)
                    
                    if max_from_wallet > 1 and can_afford_wallet:
                        max_wallet_button = discord.ui.Button(
                            label=f"Max {max_from_wallet} (Wallet)", 
                            style=discord.ButtonStyle.success,
                            emoji="💵",
                            row=1
                        )
                        max_wallet_button.callback = lambda i: self._handle_upgrade(i, ctx, user_id, guild_id, max_from_wallet, "wallet")
                        view.add_item(max_wallet_button)
                    
                    if max_combined > max(max_from_bank, max_from_wallet):
                        max_combined_button = discord.ui.Button(
                            label=f"Max {max_combined} (Combined)", 
                            style=discord.ButtonStyle.success,
                            emoji="🔄",
                            row=1
                        )
                        max_combined_button.callback = lambda i: self._handle_upgrade(i, ctx, user_id, guild_id, max_combined, "combined")
                        view.add_item(max_combined_button)
            
            # Row 2: Close button
            close_button = discord.ui.Button(label="Close", style=discord.ButtonStyle.red, emoji="❌", row=2)
            close_button.callback = lambda i: self._handle_close(i, ctx)
            view.add_item(close_button)
            
            return embed, view
        
        embed, view = await create_upgrade_embed(ctx.author.id, ctx.guild.id)
        await ctx.reply(embed=embed, view=view)
    
    async def _handle_upgrade(self, interaction, ctx, user_id, guild_id, count, source):
        """Handle bank upgrade transaction"""
        if interaction.user != ctx.author:
            return await interaction.response.send_message("❌ This isn't your upgrade!", ephemeral=True)
        
        # Get fresh data
        current_limit = await db.get_bank_limit(user_id, guild_id)
        current_balance = await db.get_bank_balance(user_id, guild_id)
        wallet_balance = await db.get_wallet_balance(user_id, guild_id)
        
        base_cost = 1000
        upgrade_cost = int(current_limit * 0.1) + base_cost
        total_cost = upgrade_cost * count
        
        # Verify affordability
        if source == "bank" and current_balance < total_cost:
            return await interaction.response.send_message("❌ Insufficient bank funds!", ephemeral=True)
        elif source == "wallet" and wallet_balance < total_cost:
            return await interaction.response.send_message("❌ Insufficient wallet funds!", ephemeral=True)
        elif source == "combined" and (current_balance + wallet_balance) < total_cost:
            return await interaction.response.send_message("❌ Insufficient combined funds!", ephemeral=True)
        
        # Process payment
        try:
            if source == "bank":
                await db.update_bank(user_id, -total_cost, guild_id)
            elif source == "wallet":
                await db.update_wallet(user_id, -total_cost, guild_id)
            elif source == "combined":
                # Take from bank first, then wallet
                bank_payment = min(current_balance, total_cost)
                wallet_payment = total_cost - bank_payment
                
                if bank_payment > 0:
                    await db.update_bank(user_id, -bank_payment, guild_id)
                if wallet_payment > 0:
                    await db.update_wallet(user_id, -wallet_payment, guild_id)
            
            # Apply upgrades
            limit_increase = 5000 * count
            await db.update_bank_limit(user_id, limit_increase, guild_id)
            
            # Show success and new options
            success_embed = discord.Embed(
                title="✅ Bank Upgrade Successful!",
                description=(
                    f"**Upgraded:** {count} time{'s' if count > 1 else ''}\n"
                    f"**Cost:** {total_cost:,} {self.currency} (from {source})\n"
                    f"**Limit Increased:** +{limit_increase:,} {self.currency}\n"
                    f"**New Limit:** {current_limit + limit_increase:,} {self.currency}"
                ),
                color=discord.Color.green()
            )
            
            # Show new upgrade options
            embed, view = await self._create_upgrade_embed_for_interaction(user_id, guild_id, ctx)
            await interaction.response.edit_message(embeds=[success_embed, embed], view=view)
            
        except Exception as e:
            self.logger.error(f"Bank upgrade error: {e}")
            await interaction.response.send_message("❌ An error occurred during the upgrade!", ephemeral=True)
    
    async def _handle_close(self, interaction, ctx):
        """Handle close button"""
        if interaction.user != ctx.author:
            return await interaction.response.send_message("❌ This isn't your upgrade!", ephemeral=True)
        await interaction.response.edit_message(content="🏦 Bank upgrade center closed.", embed=None, view=None)
    
    async def _create_upgrade_embed_for_interaction(self, user_id, guild_id, ctx):
        """Create upgrade embed for interaction (helper method)"""
        # This is the same logic as create_upgrade_embed but adapted for the interaction context
        current_limit = await db.get_bank_limit(user_id, guild_id)
        current_balance = await db.get_bank_balance(user_id, guild_id)
        wallet_balance = await db.get_wallet_balance(user_id, guild_id)
        
        base_cost = 1000
        upgrade_cost = int(current_limit * 0.1) + base_cost
        new_limit = current_limit + 5000
        
        can_afford_combined = (current_balance + wallet_balance) >= upgrade_cost
        max_combined = (current_balance + wallet_balance) // upgrade_cost if upgrade_cost > 0 else 0
        
        embed = discord.Embed(
            title="🏦 Continue Upgrading?",
            color=0x2ecc71 if can_afford_combined else 0xe74c3c,
            description=(
                f"**Current Status:**\n"
                f"🏦 Bank Limit: **{current_limit:,}** {self.currency}\n"
                f"💰 Bank Balance: **{current_balance:,}** {self.currency}\n"
                f"💵 Wallet Balance: **{wallet_balance:,}** {self.currency}\n\n"
                f"**Next Upgrade:**\n"
                f"💲 Cost: **{upgrade_cost:,}** {self.currency}\n"
                f"📈 New Limit: **{new_limit:,}** {self.currency}\n"
                f"🔢 Max Possible: **{max_combined}** more upgrades"
            )
        )
        
        view = discord.ui.View(timeout=180)
        close_button = discord.ui.Button(label="Done", style=discord.ButtonStyle.red, emoji="✅")
        close_button.callback = lambda i: self._handle_close(i, ctx)
        view.add_item(close_button)
        
        return embed, view

    @commands.command()
    async def voteinfo(self, ctx):
        """Get information about voting rewards"""
        embed = discord.Embed(
            title="Vote Rewards",
            description=(
                f"Vote for our bot on Top.gg every 12 hours to receive rewards!\n\n"
                f"**Reward:** 1,000 {self.currency}\n"
                f"[**Vote Here**](https://top.gg/bot/{self.bot.user.id}/vote)\n\n"
                f"Use `{ctx.prefix}checkvote` to see if you can claim your reward!"
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=['vote', 'votereward'])
    async def checkvote(self, ctx):
        """Check if you've voted and claim your reward"""
        if not data['top_gg']:
            return await ctx.send("Vote rewards are currently disabled in this server.")
        # Check if user has voted in the last 12 hours
        headers = {
            "Authorization": data['top_ggtoken']
        }
        
        try:
            async with self.bot.session.get(
                f"https://top.gg/api/bots/{self.bot.user.id}/check",
                params={"userId": ctx.author.id},
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('voted', 0) == 1:
                        # Check if they've already claimed today
                        last_vote = await db.db.users.find_one({
                            "_id": str(ctx.author.id),
                            "last_vote_reward": {"$gte": datetime.datetime.now() - datetime.timedelta(hours=12)}
                        })
                        
                        if last_vote:
                            return await ctx.send("You've already claimed your vote reward in the last 12 hours!")
                        
                        # Give reward
                        reward_amount = 1000
                        await db.update_wallet(ctx.author.id, reward_amount, ctx.guild.id)
                        await db.db.users.update_one(
                            {"_id": str(ctx.author.id)},
                            {"$set": {"last_vote_reward": datetime.datetime.now()}},
                            upsert=True
                        )
                        
                        return await ctx.send(f"Thanks for voting! You've received {reward_amount} {self.currency}!")
                    else:
                        return await ctx.send(f"You haven't voted yet! Vote here: https://top.gg/bot/{self.bot.user.id}/vote")
                else:
                    return await ctx.send("Couldn't check your vote status. Please try again later.")
        except Exception as e:
            self.logger.error(f"Vote check error: {e}")
            return await ctx.send("An error occurred while checking your vote status.")

    # Item Usage Commands
    @commands.command(aliases=['use', 'consume', 'activate'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def useitem(self, ctx, *, item_name: str = None):
        """Use an item, potion, or upgrade from your inventory"""
        if not item_name:
            return await self._show_inventory_usage_guide(ctx)
        
        try:
            # Get user inventory
            inventory = await db.get_inventory(ctx.author.id, ctx.guild.id)
            if not inventory:
                return await ctx.reply("❌ Your inventory is empty! Buy items from `.shop`")
            
            # Filter inventory to only show usable items (potions and upgrades)
            usable_items = [item for item in inventory if isinstance(item, dict) and 
                          item.get('type') in ['potion', 'upgrade']]
            
            if not usable_items:
                return await ctx.reply("❌ You don't have any usable items! Potions and upgrades can be used with this command.")
            
            # Search for the item in usable items only
            target_item = await self._find_item_in_inventory(usable_items, item_name)
            if not target_item:
                return await self._show_item_not_found(ctx, item_name, usable_items)
            
            # Determine item type and handle usage
            item_type = target_item.get('type', 'item')
            
            if item_type == 'potion':
                await self._use_potion(ctx, target_item)
            elif item_type == 'upgrade':
                await self._use_upgrade(ctx, target_item)
            else:
                # This shouldn't happen now since we filter the inventory
                await ctx.reply("❌ This item cannot be used!")
                
        except Exception as e:
            self.logger.error(f"Use item error: {e}")
            await ctx.reply("❌ An error occurred while using the item!")
    
    async def _show_inventory_usage_guide(self, ctx):
        """Show inventory and usage guide"""
        inventory = await db.get_inventory(ctx.author.id, ctx.guild.id)
        
        embed = discord.Embed(
            title="📦 Item Usage Guide",
            description="Use `.use <item_name>` to consume usable items from your inventory\n\n**Note:** Only potions and upgrades can be used with this command.",
            color=discord.Color.blue()
        )
        
        if inventory:
            # Only show usable items (potions and upgrades)
            potions = [item for item in inventory if isinstance(item, dict) and item.get('type') == 'potion']
            upgrades = [item for item in inventory if isinstance(item, dict) and item.get('type') == 'upgrade']
            
            if potions:
                potion_list = [f"🧪 {item.get('name', 'Unknown')} (x{item.get('quantity', 1)})" for item in potions[:5]]
                embed.add_field(
                    name="🧪 Usable Potions",
                    value="\n".join(potion_list) + ("..." if len(potions) > 5 else ""),
                    inline=True
                )
            
            if upgrades:
                upgrade_list = [f"⬆️ {item.get('name', 'Unknown')} (x{item.get('quantity', 1)})" for item in upgrades[:5]]
                embed.add_field(
                    name="⬆️ Usable Upgrades",
                    value="\n".join(upgrade_list) + ("..." if len(upgrades) > 5 else ""),
                    inline=True
                )
            
            if not potions and not upgrades:
                embed.add_field(
                    name="No Usable Items",
                    value="You don't have any potions or upgrades to use!\nVisit `.shop` to buy some usable items.",
                    inline=False
                )
        else:
            embed.add_field(
                name="Empty Inventory",
                value="You don't have any items! Visit `.shop` to buy some.",
                inline=False
            )
        
        embed.add_field(
            name="💡 Usage Examples",
            value=(
                "`.use luck potion` - Use a luck potion\n"
                "`.use bank boost` - Apply a bank upgrade\n"
                "`.use interest token` - Consume an interest token"
            ),
            inline=False
        )
        
        await ctx.reply(embed=embed)
    
    async def _find_item_in_inventory(self, inventory, item_name):
        """Find an item in inventory by name, partial match, or alias"""
        item_name = item_name.lower().strip()
        
        # Load potion data for alias matching
        try:
            import os
            import json
            potion_file = os.path.join(os.getcwd(), "data", "shop", "potions.json")
            with open(potion_file, 'r') as f:
                potion_data = json.load(f)
        except Exception:
            potion_data = {}
        
        # Exact name match first
        for item in inventory:
            if not isinstance(item, dict):
                continue
            if item.get('name', '').lower() == item_name:
                return item
        
        # Alias match for potions
        for item in inventory:
            if not isinstance(item, dict):
                continue
            item_id = item.get('id', '')
            if item_id in potion_data:
                aliases = potion_data[item_id].get('aliases', [])
                if item_name in [alias.lower() for alias in aliases]:
                    return item
        
        # Partial name match
        for item in inventory:
            if not isinstance(item, dict):
                continue
            if item_name in item.get('name', '').lower():
                return item
        
        # ID match
        for item in inventory:
            if not isinstance(item, dict):
                continue
            if item.get('id', '').lower() == item_name:
                return item
        
        return None
    
    async def _show_item_not_found(self, ctx, item_name, inventory):
        """Show item not found message with suggestions"""
        embed = discord.Embed(
            title="❌ Item Not Found",
            description=f"Couldn't find '{item_name}' in your inventory!",
            color=discord.Color.red()
        )
        
        # Show available items
        if inventory:
            available = [f"`{item.get('name', 'Unknown')}`" for item in inventory[:10] if isinstance(item, dict)]
            embed.add_field(
                name="Available Items",
                value=", ".join(available) + ("..." if len(inventory) > 10 else ""),
                inline=False
            )
        
        embed.add_field(
            name="💡 Tip",
            value="Try using part of the item name or check your spelling!",
            inline=False
        )
        
        await ctx.reply(embed=embed)
    
    async def _use_potion(self, ctx, potion):
        """Handle potion usage"""
        from utils.potion_effects import get_potion_effects
        
        potion_id = potion.get('id') or potion.get('_id')
        potion_name = potion.get('name', 'Unknown Potion')
        
        # Apply potion effect
        potion_effects = get_potion_effects(self.bot)
        success = await potion_effects.apply_potion_effect(ctx.author.id, potion_id)
        
        if success:
            # Remove potion from inventory
            await db.remove_from_inventory(ctx.author.id, ctx.guild.id, potion_id, 1)
            
            # Get potion details for display
            potion_data = potion_effects.potion_data.get(potion_id, {})
            duration = potion_data.get('duration', 600) // 60  # Convert to minutes
            effects = potion_data.get('effects', {})
            
            embed = discord.Embed(
                title="🧪 Potion Consumed!",
                description=f"You drank **{potion_name}**!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="⏱️ Duration",
                value=f"{duration} minutes",
                inline=True
            )
            
            # Show effects
            effect_list = []
            for effect_type, value in effects.items():
                if 'multiplier' in effect_type:
                    effect_list.append(f"• {effect_type.replace('_', ' ').title()}: {value}x")
                elif effect_type == 'cooldown_reduction':
                    effect_list.append(f"• Cooldown Reduction: {value*100:.0f}%")
                else:
                    effect_list.append(f"• {effect_type.replace('_', ' ').title()}: {value}")
            
            if effect_list:
                embed.add_field(
                    name="✨ Effects",
                    value="\n".join(effect_list),
                    inline=False
                )
            
            await ctx.reply(embed=embed)
        else:
            await ctx.reply(f"❌ Failed to consume {potion_name}! It might not be a valid potion.")
    
    async def _use_upgrade(self, ctx, upgrade):
        """Handle upgrade usage"""
        upgrade_id = upgrade.get('id') or upgrade.get('_id')
        upgrade_name = upgrade.get('name', 'Unknown Upgrade')
        upgrade_type = upgrade.get('upgrade_type', 'unknown')
        amount = upgrade.get('amount', 0)
        
        try:
            if upgrade_type == 'bank':
                # Bank limit upgrade
                await db.update_bank_limit(ctx.author.id, amount, ctx.guild.id)
                await db.remove_from_inventory(ctx.author.id, ctx.guild.id, upgrade_id, 1)
                
                embed = discord.Embed(
                    title="🏦 Bank Upgrade Applied!",
                    description=f"Used **{upgrade_name}**",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="📈 Upgrade",
                    value=f"Bank limit increased by **{amount:,}** {self.currency}",
                    inline=False
                )
                
            elif upgrade_type == 'wallet':
                # Wallet upgrade (if implemented)
                # For now, just give money
                await db.update_wallet(ctx.author.id, amount, ctx.guild.id)
                await db.remove_from_inventory(ctx.author.id, ctx.guild.id, upgrade_id, 1)
                
                embed = discord.Embed(
                    title="💵 Wallet Boost Applied!",
                    description=f"Used **{upgrade_name}**",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="💰 Bonus",
                    value=f"Added **{amount:,}** {self.currency} to your wallet",
                    inline=False
                )
                
            elif upgrade_type == 'interest':
                # Interest level upgrade
                current_level = await db.get_interest_level(ctx.author.id)
                if current_level >= 60:
                    return await ctx.reply("❌ You're already at the maximum interest level!")
                
                # Apply the upgrade
                success = await db.upgrade_interest_with_item(ctx.author.id)
                if success:
                    await db.remove_from_inventory(ctx.author.id, ctx.guild.id, upgrade_id, 1)
                    
                    embed = discord.Embed(
                        title="📈 Interest Upgrade Applied!",
                        description=f"Used **{upgrade_name}**",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="🎯 Result",
                        value=f"Interest level increased to **{current_level + 1}**!",
                        inline=False
                    )
                else:
                    return await ctx.reply("❌ Failed to apply interest upgrade!")
                    
            else:
                # Generic upgrade - just give the amount as money
                await db.update_wallet(ctx.author.id, amount, ctx.guild.id)
                await db.remove_from_inventory(ctx.author.id, ctx.guild.id, upgrade_id, 1)
                
                embed = discord.Embed(
                    title="⬆️ Upgrade Applied!",
                    description=f"Used **{upgrade_name}**",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="💰 Benefit",
                    value=f"Received **{amount:,}** {self.currency}",
                    inline=False
                )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Upgrade usage error: {e}")
            await ctx.reply(f"❌ Failed to use {upgrade_name}!")

    @commands.command(aliases=['pot', 'potions', 'effects'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def activeeffects(self, ctx):
        """View your active potion effects"""
        from utils.potion_effects import get_potion_effects
        
        try:
            potion_effects = get_potion_effects(self.bot)
            effects_display = await potion_effects.get_active_effects_display(ctx.author.id)
            
            embed = discord.Embed(
                title="✨ Active Effects",
                description=effects_display,
                color=discord.Color.purple()
            )
            
            # Get user's available potions
            inventory = await db.get_inventory(ctx.author.id, ctx.guild.id)
            potions = [item for item in inventory if isinstance(item, dict) and item.get('type') == 'potion']
            
            if potions:
                available_potions = [f"🧪 {p.get('name', 'Unknown')} (x{p.get('quantity', 1)})" for p in potions[:5]]
                embed.add_field(
                    name="🎒 Available Potions",
                    value="\n".join(available_potions) + ("..." if len(potions) > 5 else ""),
                    inline=False
                )
            
            embed.add_field(
                name="💡 Usage",
                value="Use `.use <potion_name>` to consume a potion",
                inline=False
            )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Active effects error: {e}")
            await ctx.reply("❌ An error occurred while checking your effects!")
    
    @commands.command(aliases=['inv', 'items', 'bag'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def inventory(self, ctx):
        """View your complete inventory with usage options"""
        try:
            inventory = await db.get_inventory(ctx.author.id, ctx.guild.id)
            
            if not inventory:
                embed = discord.Embed(
                    title="📦 Inventory",
                    description="Your inventory is empty! Visit `.shop` to buy items.",
                    color=discord.Color.blue()
                )
                return await ctx.reply(embed=embed)
            
            # Group items by type
            potions = [item for item in inventory if isinstance(item, dict) and item.get('type') == 'potion']
            upgrades = [item for item in inventory if isinstance(item, dict) and item.get('type') == 'upgrade']
            general = [item for item in inventory if isinstance(item, dict) and item.get('type') not in ['potion', 'upgrade']]
            
            # Calculate total value
            total_value = sum(item.get('value', 0) * item.get('quantity', 1) for item in inventory if isinstance(item, dict))
            
            embed = discord.Embed(
                title="📦 Your Inventory",
                description=f"**Total Items:** {len(inventory)} | **Total Value:** {total_value:,} {self.currency}",
                color=discord.Color.blue()
            )
            
            if potions:
                potion_text = []
                for potion in potions[:8]:
                    qty = potion.get('quantity', 1)
                    value = potion.get('value', 0)
                    potion_text.append(f"🧪 **{potion.get('name', 'Unknown')}** (x{qty}) - {value:,} {self.currency}")
                
                embed.add_field(
                    name=f"🧪 Potions ({len(potions)})",
                    value="\n".join(potion_text) + ("..." if len(potions) > 8 else ""),
                    inline=False
                )
            
            if upgrades:
                upgrade_text = []
                for upgrade in upgrades[:8]:
                    qty = upgrade.get('quantity', 1)
                    value = upgrade.get('value', 0)
                    upgrade_text.append(f"⬆️ **{upgrade.get('name', 'Unknown')}** (x{qty}) - {value:,} {self.currency}")
                
                embed.add_field(
                    name=f"⬆️ Upgrades ({len(upgrades)})",
                    value="\n".join(upgrade_text) + ("..." if len(upgrades) > 8 else ""),
                    inline=False
                )
            
            if general:
                general_text = []
                for item in general[:8]:
                    qty = item.get('quantity', 1)
                    value = item.get('value', 0)
                    general_text.append(f"📦 **{item.get('name', 'Unknown')}** (x{qty}) - {value:,} {self.currency}")
                
                embed.add_field(
                    name=f"📦 General Items ({len(general)})",
                    value="\n".join(general_text) + ("..." if len(general) > 8 else ""),
                    inline=False
                )
            
            embed.add_field(
                name="💡 Quick Actions",
                value=(
                    "`.use <item_name>` - Use an item\n"
                    "`.activeeffects` - View active potion effects\n"
                    "`.shop` - Buy more items"
                ),
                inline=False
            )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Inventory error: {e}")
            await ctx.reply("❌ An error occurred while checking your inventory!")

async def setup(bot):
    """Setup function for loading the Economy cog"""
    await bot.add_cog(Economy(bot))
