# Chance Games Module
# Contains pure chance gambling games like slots, coinflip, double or nothing

from discord.ext import commands
from cogs.logging.logger import CogLogger
from cogs.logging.stats_logger import StatsLogger
from utils.db import AsyncDatabase
db = AsyncDatabase.get_instance()
from utils.safe_reply import safe_reply
from utils.tos_handler import check_tos_acceptance, prompt_tos_acceptance
import discord
import random
import asyncio
import functools
from typing import Optional, List

def requires_tos():
    """Decorator to ensure user has accepted ToS before using gambling commands"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            if not await check_tos_acceptance(ctx.author.id):
                await prompt_tos_acceptance(ctx)
                return
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator

class ChanceGames(commands.Cog):
    """Pure chance gambling games"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.currency = "<:bronkbuk:1377389238290747582>"
        self.active_games = set()
        self.stats_logger = StatsLogger()
        
        # Progressive bet limits based on user balance (ANTI-INFLATION)
        self.BET_LIMITS = {
            0: 10000,           # 0-99k balance: max 10k bet
            100000: 25000,      # 100k-499k: max 25k bet
            500000: 50000,      # 500k-999k: max 50k bet
            1000000: 100000,    # 1M-4.9M: max 100k bet
            5000000: 200000,    # 5M-9.9M: max 200k bet
            10000000: 500000,   # 10M+: max 500k bet (hard cap)
        }
        
        # HEAVILY NERFED slot machine symbols and weights to combat inflation
        self.slot_symbols = [
            ("💎", 1),     # Diamond - Ultra rare (3x multiplier - NERFED from 100x)
            ("7️⃣", 3),     # Lucky 7 - Very rare (2.5x multiplier - NERFED from 20x)
            ("🔔", 8),     # Bell - Rare (2x multiplier - NERFED from 10x)
            ("🍒", 15),    # Cherry - Uncommon (1.8x multiplier - NERFED from 5x)
            ("🍋", 15),    # Lemon - Uncommon (1.8x multiplier - NERFED from 5x)
            ("🍊", 15),    # Orange - Uncommon (1.8x multiplier - NERFED from 5x)
            ("🍇", 15),    # Grape - Uncommon (1.8x multiplier - NERFED from 5x)
            ("⭐", 20),    # Star - Common (1.5x multiplier - NERFED from 5x)
            ("🎯", 25),    # Target - Common (1.5x multiplier - NERFED from 5x)
            ("💫", 30),    # Dizzy - Very common (1.2x multiplier - NERFED from 5x)
        ]
        
        self.blocked_channels = [1378156495144751147, 1260347806699491418]
        self.logger.info("Chance games module initialized with anti-inflation measures")
    
    async def cog_check(self, ctx):
        """Global check for gambling commands"""
        if ctx.channel.id in self.blocked_channels:
            await ctx.reply("❌ Gambling commands are not allowed in this channel!")
            return False
        return True
    
    def _get_max_bet_for_balance(self, balance: int) -> int:
        """Get maximum bet allowed based on user balance (progressive limits)"""
        for min_balance in sorted(self.BET_LIMITS.keys(), reverse=True):
            if balance >= min_balance:
                return self.BET_LIMITS[min_balance]
        return self.BET_LIMITS[0]
    
    async def _parse_bet(self, bet_str: str, wallet: int) -> int:
        """Parse bet string (all, half, percentage, or number)"""
        bet_str = bet_str.lower().strip()
        
        if bet_str in ['all', 'max']:
            return wallet
        elif bet_str in ['half', '50%']:
            return wallet // 2
        elif bet_str.endswith('%'):
            try:
                percentage = float(bet_str[:-1])
                if 0 <= percentage <= 100:
                    return int(wallet * (percentage / 100))
            except ValueError:
                pass
        else:
            try:
                return int(bet_str.replace(',', ''))
            except ValueError:
                pass
        
        return None

    @commands.command(aliases=['cf', 'flip'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    @requires_tos()
    async def coinflip(self, ctx, bet: str, choice: str = None):
        """Flip a coin - heads or tails (HEAVILY NERFED PAYOUTS)
        
        Usage: `.coinflip <bet> <heads/tails>`
        Examples: `.coinflip 1000 heads`, `.coinflip all tails`
        
        Payout: 0.9x bet (NERFED from 1x) - House edge increased to combat inflation
        """
        try:
            # Parse bet amount
            wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            parsed_bet = await self._parse_bet(bet, wallet)
            
            if not parsed_bet:
                return await ctx.reply("❌ Invalid bet amount!")
                
            if parsed_bet <= 0:
                return await ctx.reply("❌ Bet amount must be greater than 0!")

            if parsed_bet > wallet:
                return await ctx.reply("❌ You don't have enough money for that bet!")
                
            # Check bet limits (ANTI-INFLATION)
            max_bet = self._get_max_bet_for_balance(wallet)
            if parsed_bet > max_bet:
                return await ctx.reply(f"❌ Maximum bet for your balance is **{max_bet:,}** {self.currency}!\n"
                                     f"💡 This limit helps prevent extreme inflation in the economy.")
                
            # Validate choice
            if not choice:
                embed = discord.Embed(
                    title="🪙 Coin Flip",
                    description=f"Bet: **{parsed_bet:,}** {self.currency}\n\n"
                               f"Choose heads or tails:\n"
                               f"`{ctx.prefix}coinflip {bet} heads`\n"
                               f"`{ctx.prefix}coinflip {bet} tails`\n\n"
                               f"⚠️ **New payout: 0.9x bet** (house edge increased)",
                    color=0xf1c40f
                )
                return await ctx.reply(embed=embed)
                
            choice = choice.lower()
            if choice not in ["heads", "tails", "h", "t"]:
                return await ctx.reply("❌ Invalid choice! Must be 'heads' or 'tails'")
                
            # Convert shorthand
            if choice == "h":
                choice = "heads"
            elif choice == "t":
                choice = "tails"
                
            # Flip coin
            result = random.choice(["heads", "tails"])
            win = choice == result
            
            # Calculate winnings (NERFED - 0.9x payout instead of 1x)
            if win:
                winnings = int(parsed_bet * 0.9)  # HEAVY NERF: 0.9x instead of 1x
                outcome = f"**You won {winnings:,}** {self.currency}! (0.9x payout)"
                self.stats_logger.log_economy_transaction(ctx.author.id, "coinflip", winnings, True)
            else:
                winnings = -parsed_bet
                outcome = f"**You lost {parsed_bet:,}** {self.currency}!"
                self.stats_logger.log_economy_transaction(ctx.author.id, "coinflip", parsed_bet, False)
                
            # Update balance
            await db.update_wallet(ctx.author.id, winnings, ctx.guild.id)
            self.stats_logger.log_command_usage("coinflip")
            
            # Send result
            embed = discord.Embed(
                title=f"🪙 {'You win!' if win else 'You lose!'}",
                description=f"Your choice: **{choice.title()}**\n"
                          f"Result: **{result.title()}**\n\n"
                          f"{outcome}",
                color=0x2ecc71 if win else 0xe74c3c
            )
            
            embed.add_field(
                name="New Balance",
                value=f"**{wallet + winnings:,}** {self.currency}",
                inline=True
            )
            
            if win:
                embed.add_field(
                    name="⚠️ Economy Rebalance",
                    value="Payouts reduced to combat inflation",
                    inline=True
                )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Coinflip error: {e}")
            await ctx.reply("❌ An error occurred while processing your bet.")

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    @requires_tos()
    async def slots(self, ctx, bet: str):
        """Play the slot machine (HEAVILY NERFED PAYOUTS)
        
        Usage: `.slots <bet>`
        Examples: `.slots 1000`, `.slots all`, `.slots 25%`
        
        NEW Payouts (HEAVILY NERFED):
        💎💎💎 = 3x bet (was 100x - MASSIVE NERF!)
        7️⃣7️⃣7️⃣ = 2.5x bet (was 20x - MASSIVE NERF!)
        🔔🔔🔔 = 2x bet (was 10x - MASSIVE NERF!)
        Any other triple = 1.8x bet (was 5x - MASSIVE NERF!)
        Any double = 1.2x bet (was 2x - NERF!)
        """
        try:
            # Parse bet amount
            wallet = await db.get_wallet_balance(ctx.author.id, ctx.guild.id)
            parsed_bet = await self._parse_bet(bet, wallet)
            
            if not parsed_bet:
                return await ctx.reply("❌ Invalid bet amount!")
            
            if parsed_bet <= 0:
                return await ctx.reply("❌ Bet amount must be greater than 0!")
        
            if parsed_bet > wallet:
                return await ctx.reply("❌ You don't have enough money for that bet!")
                
            # Check bet limits (ANTI-INFLATION)
            max_bet = self._get_max_bet_for_balance(wallet)
            if parsed_bet > max_bet:
                return await ctx.reply(f"❌ Maximum bet for your balance is **{max_bet:,}** {self.currency}!\n"
                                     f"💡 This limit helps prevent extreme inflation in the economy.")
                
            # Deduct bet
            await db.update_wallet(ctx.author.id, -parsed_bet, ctx.guild.id)
            self.stats_logger.log_command_usage("slots")
            
            # Spin the slots
            reels = []
            total_weight = sum(weight for _, weight in self.slot_symbols)
            
            for _ in range(3):
                rand = random.uniform(0, total_weight)
                current = 0
                for symbol, weight in self.slot_symbols:
                    current += weight
                    if rand <= current:
                        reels.append(symbol)
                        break
            
            # Calculate winnings (HEAVILY NERFED MULTIPLIERS)
            winnings = 0
            outcome = "You lost!"
            
            # Check for wins
            if reels[0] == reels[1] == reels[2]:
                if reels[0] == "💎":
                    multiplier = 3.0  # MASSIVE NERF: was 100x
                    outcome = "JACKPOT! 💎💎💎 (NERFED: was 100x, now 3x)"
                elif reels[0] == "7️⃣":
                    multiplier = 2.5  # MASSIVE NERF: was 20x
                    outcome = "TRIPLE 7s! 🎰 (NERFED: was 20x, now 2.5x)"
                elif reels[0] == "🔔":
                    multiplier = 2.0  # MASSIVE NERF: was 10x
                    outcome = "TRIPLE BELLS! 🔔 (NERFED: was 10x, now 2x)"
                else:
                    multiplier = 1.8  # MASSIVE NERF: was 5x
                    outcome = "TRIPLE MATCH! (NERFED: was 5x, now 1.8x)"
                    
                winnings = int(parsed_bet * multiplier)
            elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
                multiplier = 1.2  # NERF: was 2x
                winnings = int(parsed_bet * multiplier)
                outcome = "DOUBLE MATCH! (NERFED: was 2x, now 1.2x)"
                
            # Update balance if won
            if winnings > 0:
                await db.update_wallet(ctx.author.id, winnings, ctx.guild.id)
                self.stats_logger.log_economy_transaction(ctx.author.id, "slots", winnings, True)
            else:
                self.stats_logger.log_economy_transaction(ctx.author.id, "slots", parsed_bet, False)
                
            # Create slot display
            slot_display = " | ".join(reels)
            
            embed = discord.Embed(
                title="🎰 Slot Machine (REBALANCED)",
                description=f"**{slot_display}**\n\n"
                          f"**{outcome}**\n"
                          f"Bet: **{parsed_bet:,}** {self.currency}\n"
                          f"Won: **{winnings:,}** {self.currency}",
                color=0x9b59b6
            )
            
            embed.add_field(
                name="New Balance",
                value=f"**{wallet - parsed_bet + winnings:,}** {self.currency}",
                inline=True
            )
            
            if winnings > 0:
                embed.add_field(
                    name="⚠️ Economy Rebalance",
                    value="All payouts heavily reduced to combat inflation",
                    inline=True
                )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Slots error: {e}")
            await ctx.reply("❌ An error occurred while spinning the slots.")

    @commands.command(aliases=['double', 'don', 'dbl'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @requires_tos()
    async def doubleornothing(self, ctx, *, items: str = None):
        """Double your items or lose them all
        
        Usage: `.doubleornothing <item1> [item2] ... [item20]`
        Example: `.doubleornothing fish rod bait`
        
        50% chance to double all items, 50% chance to lose them all!
        """
        if ctx.author.id in self.active_games:
            return await ctx.reply("❌ You already have an active game!")
            
        if not items:
            return await ctx.reply(f"Usage: `{ctx.prefix}doubleornothing <item1> [item2] ... [item20]`")
            
        try:
            # Get user inventory
            inventory = await db.get_inventory(ctx.author.id, ctx.guild.id)
            if not inventory:
                return await ctx.reply("❌ Your inventory is empty!")
                
            # Parse requested items
            requested_items = items.split()
            if len(requested_items) > 20:
                return await ctx.reply("❌ You can only bet up to 20 items at a time!")
                
            # Find matching items in inventory
            items_to_bet = []
            for item_name in requested_items:
                found = False
                for item in inventory:
                    if not isinstance(item, dict):
                        continue
                    if (item.get("id", "").lower() == item_name.lower() or 
                        item.get("name", "").lower() == item_name.lower()):
                        items_to_bet.append(item)
                        found = True
                        break
                        
                if not found:
                    return await ctx.reply(f"❌ You don't have '{item_name}' in your inventory!")
                    
            # Create confirmation view
            view = discord.ui.View(timeout=30.0)
            
            async def confirm_callback(interaction):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
                    
                # Flip coin (50% chance)
                win = random.choice([True, False])
                
                if win:
                    # Double the items
                    for item in items_to_bet:
                        await db.add_to_inventory(
                            ctx.author.id, 
                            ctx.guild.id, 
                            item, 
                            item.get("quantity", 1)
                        )
                        
                    outcome = f"**You won!** All items doubled!"
                    self.stats_logger.log_economy_transaction(
                        ctx.author.id, 
                        "doubleornothing", 
                        sum(item.get("value", 0) for item in items_to_bet), 
                        True
                    )
                else:
                    # Remove the items
                    for item in items_to_bet:
                        await db.remove_from_inventory(
                            ctx.author.id, 
                            ctx.guild.id, 
                            item.get("id", item.get("name")), 
                            item.get("quantity", 1)
                        )
                        
                    outcome = "**You lost!** All items are gone!"
                    self.stats_logger.log_economy_transaction(
                        ctx.author.id, 
                        "doubleornothing", 
                        sum(item.get("value", 0) for item in items_to_bet), 
                        False
                    )
                    
                # Log command usage
                self.stats_logger.log_command_usage("doubleornothing")
                
                # Create result embed
                item_names = ", ".join([item.get("name", "Unknown") for item in items_to_bet])
                
                embed = discord.Embed(
                    title="🎲 Double or Nothing",
                    description=f"You bet: **{item_names}**\n\n"
                            f"{outcome}",
                    color=0x2ecc71 if win else 0xe74c3c
                )
                
                await interaction.response.edit_message(embed=embed, view=None)
                self.active_games.remove(ctx.author.id)
                
            async def cancel_callback(interaction):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
                    
                await interaction.response.edit_message(content="❌ Game cancelled.", embed=None, view=None)
                self.active_games.remove(ctx.author.id)
                
            confirm_button = discord.ui.Button(label="Confirm", style=discord.ButtonStyle.green)
            confirm_button.callback = confirm_callback
            view.add_item(confirm_button)
            
            cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.red)
            cancel_button.callback = cancel_callback
            view.add_item(cancel_button)
            
            # Create confirmation message
            item_names = ", ".join([item.get("name", "Unknown") for item in items_to_bet])
            
            embed = discord.Embed(
                title="🎲 Double or Nothing",
                description=f"You're about to bet:\n**{item_names}**\n\n"
                        f"50% chance to double them, 50% chance to lose them all!",
                color=0xf39c12
            )
            
            self.active_games.add(ctx.author.id)
            await ctx.reply(embed=embed, view=view)
            
        except Exception as e:
            self.logger.error(f"Double or nothing error: {e}")
            if ctx.author.id in self.active_games:
                self.active_games.remove(ctx.author.id)
            await ctx.reply("❌ An error occurred while setting up the game.")

async def setup(bot):
    await bot.add_cog(ChanceGames(bot))
