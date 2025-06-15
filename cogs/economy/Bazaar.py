import discord
from discord.ext import commands, tasks
from typing import Dict, List, Optional
from collections import defaultdict
import random
import asyncio
import math
from cogs.logging.logger import CogLogger
from utils.db import AsyncDatabase
db = AsyncDatabase.get_instance()
from utils.tos_handler import check_tos_acceptance, prompt_tos_acceptance
from datetime import datetime, timedelta
import hashlib

class ItemSelectModal(discord.ui.Modal):
    def __init__(self, cog, items):
        super().__init__(title="Bazaar Purchase", timeout=120)
        self.cog = cog
        self.items = items
        
        # Create a view to hold our select menu
        self.select_view = discord.ui.View(timeout=120)
        
        # Create the select menu
        self.item_select = discord.ui.Select(
            placeholder="Select an item to purchase...",
            options=[
                discord.SelectOption(
                    label=f"{item['name']}",
                    description=f"{item['price']} (Save {int(item['discount']*100)}%)",
                    value=str(idx),
                    emoji="🛒" if idx == 0 else "📦"
                ) for idx, item in enumerate(items)
            ]
        )
        self.select_view.add_item(self.item_select)
        
        # Add amount input
        self.amount = discord.ui.TextInput(
            label="Purchase Amount (1-10)",
            placeholder="Enter how many you want to buy...",
            default="1",
            min_length=1,
            max_length=2,
            required=True
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            item_idx = int(self.item_select.values[0])
            amount = int(self.amount.value)
            
            if amount < 1 or amount > 10:
                await interaction.response.send_message(
                    "❌ Amount must be between 1-10.", 
                    ephemeral=True
                )
                return
                
            selected_item = self.items[item_idx]
            item_id = selected_item.get("_id", selected_item.get("id", selected_item["name"].lower().replace(" ", "_")))
            await self.cog.handle_bazaar_purchase(
                interaction,
                item_id,
                amount
            )
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number between 1-10.",
                ephemeral=True
            )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # This makes sure the select menu gets processed
        if interaction.data.get("custom_id") == self.item_select.custom_id:
            await self.item_select.callback(interaction)
            return False
        return True

class BazaarView(discord.ui.View):
    def __init__(self, cog, timeout=180):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.message = None
        
    @discord.ui.button(label="🛒 Buy Items", style=discord.ButtonStyle.primary)
    async def buy_items(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.cog.current_items:
            await interaction.response.send_message("❌ No items available in the bazaar right now.", ephemeral=True)
            return
        
        modal = ItemSelectModal(self.cog, self.cog.current_items)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="📈 Buy Stock", style=discord.ButtonStyle.secondary)
    async def buy_stock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_stock_purchase(interaction)
        
    @discord.ui.button(label="📉 Sell Stock", style=discord.ButtonStyle.secondary)
    async def sell_stock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_stock_sale(interaction)
        
    @discord.ui.button(label="🗑️ Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass

class Bazaar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.currency = "<:bronkbuk:1377389238290747582>"
        
        # Bazaar configuration
        self.bazaar_reset_interval = 15  # minutes
        self.secret_shop_reset_interval = 60  # minutes
        self.max_discount = 0.9  # 90% max discount
        self.stock_threshold = 500  # Required for secret shop
        
        # Shop category weights (must sum to 100)
        self.category_weights = {
            "items": 93.5,
            "upgrades": 5.0,
            "rods": 1.0,
            "bait": 0.5
        }
        
        # Secret shop weights
        self.secret_weights = {
            "rods": 25,
            "bait": 25,
            "upgrades": 25,
            "items": 25
        }
        
        # Current bazaar items
        self.current_items = []
        self.current_secret_items = []
        self.last_reset = datetime.now()
        self.secret_last_reset = datetime.now()
        
        # Bazaar statistics
        self.visitors = set()
        self.total_spent = 0
        self.stock_base_price = 100  # Base price for stock
        
        # Initialize with empty items
        self.reset_bazaar_items()
        self.reset_secret_shop()
        
        # Start background tasks
        self.reset_bazaar.start()
        self.reset_secret_shop_task.start()
        self.save_stats.start()
        
    def cog_unload(self):
        self.reset_bazaar.cancel()
        self.reset_secret_shop_task.cancel()
        self.save_stats.cancel()
    
    async def get_all_shop_items(self) -> Dict[str, List[dict]]:
        """Get all items from all shop categories"""
        shop_items = defaultdict(list)
        
        try:
            # Get shop cog if available
            shop_cog = self.bot.get_cog("Shop")
            if shop_cog:
                # Get items from JSON files using Shop cog's methods
                shop_items["items"].extend(shop_cog.get_shop_items("item"))  # Fixed: "item" not "items"
                shop_items["upgrades"].extend(shop_cog.get_shop_items("upgrade"))  # Fixed: "upgrade" not "upgrades"
                shop_items["rods"].extend(shop_cog.get_shop_items("rod"))  # Fixed: direct access to "rod"
                shop_items["bait"].extend(shop_cog.get_shop_items("bait"))  # Fixed: direct access to "bait"
            else:
                # Fallback to direct JSON loading if Shop cog isn't loaded
                import json
                import os
                
                json_files = {
                    "items": "data/shop/items.json",
                    "upgrades": "data/shop/upgrades.json", 
                    "rods": "data/shop/rods.json",
                    "bait": "data/shop/bait.json"
                }
                
                for category, file_path in json_files.items():
                    if os.path.exists(file_path):
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            for item_id, item_data in data.items():
                                item_data['_id'] = item_id
                                item_data['type'] = category[:-1] if category.endswith('s') else category  # Remove 's' for consistency
                                shop_items[category].append(item_data)
                
        except Exception as e:
            self.logger.error(f"Error loading shop items: {e}")
        
        return shop_items
    
    def reset_bazaar_items(self):
        """Reset the bazaar items (without database access)"""
        self.current_items = []
        self.last_reset = datetime.now()
    
    def reset_secret_shop(self):
        """Reset the secret shop items (without database access)"""
        self.current_secret_items = []
        self.secret_last_reset = datetime.now()
    
    @tasks.loop(minutes=15)
    async def reset_bazaar(self):
        """Reset the bazaar items every 15 minutes"""
        try:
            all_items = await self.get_all_shop_items()
            
            # Filter out empty categories
            valid_categories = {k: v for k, v in self.category_weights.items() if all_items.get(k)}
            if not valid_categories:
                self.logger.warning("No items found in any category!")
                self.reset_bazaar_items()
                return
                
            # Select categories based on weights
            categories = []
            for category, weight in valid_categories.items():
                categories.extend([category] * int(weight * 10))
            
            selected_category = random.choice(categories)
            category_items = all_items[selected_category]
            
            # Get 3-5 random items from selected category
            num_items = random.randint(3, 5)
            self.current_items = random.sample(category_items, min(num_items, len(category_items)))
            
            # Apply bazaar specific modifications
            for item in self.current_items:
                # Apply random discount (10-30%)
                discount = random.uniform(0.1, 0.3)
                item["original_price"] = item.get("price", 0)
                item["price"] = int(item["price"] * (1 - discount))
                item["discount"] = discount
                item["category"] = selected_category
            
            self.last_reset = datetime.now()
            self.logger.info(f"Bazaar reset with {len(self.current_items)} {selected_category} items")
            
        except Exception as e:
            self.logger.error(f"Error resetting bazaar: {e}")
            self.reset_bazaar_items()
    
    @tasks.loop(minutes=60)
    async def reset_secret_shop_task(self):
        """Reset the secret shop every hour"""
        try:
            all_items = await self.get_all_shop_items()
            
            # Select categories based on secret shop weights
            categories = []
            for category, weight in self.secret_weights.items():
                categories.extend([category] * weight)
            
            # Get 1 item from each category
            self.current_secret_items = []
            for category in set(categories):  # Get unique categories
                category_items = all_items.get(category, [])
                if category_items:
                    item = random.choice(category_items)
                    item["category"] = category
                    self.current_secret_items.append(item)
            
            self.secret_last_reset = datetime.now()
            self.logger.info(f"Secret shop reset with {len(self.current_secret_items)} items")
            
        except Exception as e:
            self.logger.error(f"Error resetting secret shop: {e}")
    
    @tasks.loop(minutes=5)
    async def save_stats(self):
        """Save bazaar statistics periodically"""
        try:
            # Reset visitor count but keep total spent
            self.visitors = set()
        except Exception as e:
            self.logger.error(f"Error saving bazaar stats: {e}")
    
    def calculate_stock_price(self) -> int:
        """Calculate current stock price based on activity"""
        if not self.visitors:
            return self.stock_base_price
        
        # Price increases based on visitor count and money spent
        visitor_factor = len(self.visitors) * 0.5
        spending_factor = math.log10(max(1, self.total_spent)) * 10
        
        price = self.stock_base_price + visitor_factor + spending_factor
        
        # Add some randomness
        price *= random.uniform(0.9, 1.1)
        
        return max(self.stock_base_price, int(price))
    
    async def get_user_stock(self, user_id: int) -> int:
        """Get user's bazaar stock count"""
        try:
            user = await db.db.users.find_one({"_id": str(user_id)})
            if user:
                return user.get("bazaar_stock", 0)
            return 0
        except Exception as e:
            self.logger.error(f"Error getting user stock: {e}")
            return 0
    
    async def add_user_stock(self, user_id: int, amount: int) -> bool:
        """Add bazaar stock to user"""
        try:
            # First get current stock
            current_stock = await self.get_user_stock(user_id)
            
            # Update the user's stock
            result = await db.db.users.update_one(
                {"_id": str(user_id)},
                {"$set": {"bazaar_stock": current_stock + amount}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            self.logger.error(f"Error adding user stock: {e}")
            return False
    
    def calculate_discount(self, stock_count: int) -> float:
        """Calculate discount percentage based on stock owned"""
        # Logarithmic scaling - diminishing returns
        discount = min(self.max_discount, math.log10(stock_count + 1) * 0.2)
        return round(discount, 2)
    
    @commands.command(name="bazaar", aliases=["market"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def bazaar(self, ctx):
        """View the current bazaar offerings"""
        # Track visitor
        self.visitors.add(ctx.author.id)
        
        # Get user's stock count
        user_stock = await self.get_user_stock(ctx.author.id)
        user_discount = self.calculate_discount(user_stock)
        
        # Create embed
        embed = discord.Embed(
            title="🛒 The Wandering Bazaar",
            description=f"*Exotic goods from distant lands*\n\n"
                    f"Your Bazaar Stock: **{user_stock}** (Discount: **{user_discount*100:.0f}%**)\n"
                    f"Current Stock Price: **{self.calculate_stock_price()}** {self.currency}\n"
                    f"Sell Price: **{int(self.calculate_stock_price() * 0.8)}** {self.currency} (80%)",
            color=0x9b59b6
        )
        
        # Add current items
        if not self.current_items:
            embed.add_field(
                name="Current Offerings",
                value="The bazaar is currently being restocked...",
                inline=False
            )
        else:
            category = self.current_items[0]["category"] if self.current_items else "items"
            embed.add_field(
                name=f"Today's Featured: {category.title()}",
                value="*Special discounted prices!*",
                inline=False
            )
            
            for item in self.current_items:
                discount_text = f" (~~{item['original_price']}~~ **{item['price']}** {self.currency}, {item['discount']*100:.0f}% off)"
                item_id = item.get('_id', item.get('id', item['name'].lower().replace(' ', '_')))
                embed.add_field(
                    name=f"🛍️ {item['name']}",
                    value=f"{item.get('description', 'No description')}{discount_text}\n"
                         f"`{ctx.prefix}bazaar buy {item_id}`",
                    inline=False
                )
        
        # Add reset time
        next_reset = self.last_reset + timedelta(minutes=self.bazaar_reset_interval)
        time_left = next_reset - datetime.now()
        minutes_left = max(0, int(time_left.total_seconds() / 60))
        
        embed.set_footer(text=f"Bazaar restocks in {minutes_left} minutes • Buy stock to unlock secret deals!")
        
        # Send with view
        view = BazaarView(self)
        message = await ctx.reply(embed=embed, view=view)
        view.message = message
    
    @commands.command(name="bazaarbuy", aliases=["bbuy"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def bazaar_buy(self, ctx, item_id: str, amount: int = 1):
        """Buy an item from the bazaar"""
        await self.handle_bazaar_purchase(ctx, item_id, amount)
    
    @commands.command(name="bazaarsell", aliases=["bsell"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def bazaar_sell(self, ctx, amount: int = 1):
        """Sell your bazaar stock"""
        await self.handle_stock_sale(ctx, amount)
    
    async def handle_stock_sale(self, interaction_or_ctx, amount: int = 1):
        """Handle stock sale from either interaction or command"""
        is_interaction = isinstance(interaction_or_ctx, discord.Interaction)
        
        if is_interaction:
            interaction = interaction_or_ctx
            user = interaction.user
            guild = interaction.guild
            respond = interaction.response.send_message
        else:
            ctx = interaction_or_ctx
            user = ctx.author
            guild = ctx.guild
            respond = ctx.reply

        if amount <= 0:
            msg = "❌ Amount must be positive."
            if is_interaction:
                await respond(msg, ephemeral=True)
            else:
                await respond(msg)
            return

        # Get user's current stock
        current_stock = await self.get_user_stock(user.id)
        
        if current_stock < amount:
            msg = f"❌ You only have {current_stock} stock to sell!"
            if is_interaction:
                await respond(msg, ephemeral=True)
            else:
                await respond(msg)
            return

        # Calculate sale price (80% of current stock price)
        stock_price = int(self.calculate_stock_price() * 0.8)
        total_gain = stock_price * amount

        # For interactions, defer first
        if is_interaction:
            await interaction.response.defer()

        # Add money to wallet
        if not await db.update_wallet(user.id, total_gain, guild.id if guild else None):
            msg = "❌ Failed to process sale. Please try again."
            if is_interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await respond(msg)
            return

        # Remove stock
        result = await db.db.users.update_one(
            {"_id": str(user.id)},
            {"$set": {"bazaar_stock": current_stock - amount}}
        )
        
        if result.modified_count == 0:
            # Refund if failed
            await db.update_wallet(user.id, -total_gain, guild.id if guild else None)
            msg = "❌ Failed to remove stock. Transaction cancelled."
            if is_interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await respond(msg)
            return

        # Get updated user data
        new_stock = current_stock - amount
        new_discount = self.calculate_discount(new_stock)
        new_balance = await db.get_wallet_balance(user.id, guild.id if guild else None)

        # Create embed
        embed = discord.Embed(
            title="✅ Stock Sale Complete",
            description=f"You sold **{amount}** bazaar stock!",
            color=0x00ff00
        )

        embed.add_field(
            name="Sale Details",
            value=f"Price per Stock: **{stock_price}** {self.currency}\n"
                f"Total Gain: **{total_gain}** {self.currency}",
            inline=False
        )

        embed.add_field(
            name="Your New Holdings",
            value=f"Remaining Stock: **{new_stock}**\n"
                f"Current Discount: **{new_discount*100:.0f}%**\n"
                f"New Balance: **{new_balance}** {self.currency}",
            inline=False
        )

        # Check if they lost secret shop access
        if new_stock < self.stock_threshold and current_stock >= self.stock_threshold:
            embed.add_field(
                name="🔒 Secret Shop Lost",
                value=f"You no longer meet the {self.stock_threshold} stock requirement for secret shop access!",
                inline=False
            )

        try:
            if hasattr(self, 'last_stock_message') and self.last_stock_message:
                # Edit the existing message
                if is_interaction:
                    await self.last_stock_message.edit(embed=embed)
                else:
                    await self.last_stock_message.edit(embed=embed)
            else:
                # Send new message and store reference
                if is_interaction:
                    msg = await interaction.followup.send(embed=embed)
                else:
                    msg = await respond(embed=embed)
                self.last_stock_message = msg
        except Exception as e:
            self.logger.error(f"Error updating stock sale message: {e}")
            # Fallback to sending new message if edit fails
            if is_interaction:
                await interaction.followup.send(embed=embed)
            else:
                await respond(embed=embed)

    async def handle_bazaar_purchase(self, interaction_or_ctx, item_id: str = None, amount: int = 1):
        """Handle bazaar purchase from either interaction or command"""
        is_interaction = isinstance(interaction_or_ctx, discord.Interaction)
        
        # Get context based on input type
        if is_interaction:
            interaction = interaction_or_ctx
            user = interaction.user
            guild = interaction.guild
            respond = interaction.response.send_message
        else:
            ctx = interaction_or_ctx
            user = ctx.author
            guild = ctx.guild
            respond = ctx.reply

        # Find the item
        item = None
        for bazaar_item in self.current_items:
            # Check both _id and name variations for item matching
            item_id_matches = (
                bazaar_item.get("_id") == item_id or 
                bazaar_item.get("id") == item_id or
                bazaar_item["name"].lower().replace(" ", "_") == item_id.lower()
            )
            if item_id_matches:
                item = bazaar_item
                break
        
        if not item:
            msg = f"❌ Item `{item_id}` not found in current bazaar offerings."
            if is_interaction:
                await respond(msg, ephemeral=True)
            else:
                await respond(msg)
            return

        # Validate amount
        if amount <= 0 or amount > 10:
            msg = "❌ Amount must be between 1 and 10."
            if is_interaction:
                await respond(msg, ephemeral=True)
            else:
                await respond(msg)
            return

        # Get user's discount
        user_stock = await self.get_user_stock(user.id)
        user_discount = self.calculate_discount(user_stock)
        
        # Calculate final price with discount
        base_price = item["price"] * amount
        discount_amount = int(base_price * user_discount)
        final_price = base_price - discount_amount
        
        # Check balance
        balance = await db.get_wallet_balance(user.id, guild.id if guild else None)
        if balance < final_price:
            # Calculate max affordable amount
            max_affordable = min(10, balance // (item["price"] * (1 - user_discount)))
            msg = (f"❌ Insufficient funds! You need {final_price} {self.currency} "
                f"but only have {balance}.")
            if max_affordable > 0:
                msg += f"\n💡 You can afford up to {max_affordable} of this item."
            if is_interaction:
                await respond(msg, ephemeral=True)
            else:
                await respond(msg)
            return
        
        # For interactions, defer first
        if is_interaction:
            await interaction.response.defer()
        
        # Deduct money
        if not await db.update_wallet(user.id, -final_price, guild.id if guild else None):
            msg = "❌ Failed to process payment. Please try again."
            if is_interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await respond(msg)
            return
        
        # Add item to inventory
        clean_item = {
            "id": item.get("_id", item.get("id", item["name"].lower().replace(" ", "_"))),
            "name": item["name"],
            "description": item.get("description", ""),
            "price": item["price"],
            "value": item["price"],
            "type": item.get("type", "item"),
            "bazaar_item": True,
            "discounted_price": final_price // amount
        }
        
        success = await db.add_to_inventory(user.id, guild.id if guild else None, clean_item, amount)
        
        if not success:
            # Refund if failed
            await db.update_wallet(user.id, final_price, guild.id if guild else None)
            msg = "❌ Failed to add item to inventory. You have been refunded."
            if is_interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await respond(msg)
            return
        
        # Update bazaar stats
        self.total_spent += final_price
        
        # Create success embed
        embed = discord.Embed(
            title=f"✅ {'Purchase' if amount == 1 else 'Bulk Purchase'} Complete",
            description=f"You bought **{amount}x {item['name']}** from the bazaar!",
            color=0x00ff00
        )
        
        # Price breakdown
        price_text = [
            f"• Base Price: **{item['price'] * amount}** {self.currency}",
            f"• Your Discount ({user_discount*100:.0f}%): **-{discount_amount}** {self.currency}",
            f"• Total Paid: **{final_price}** {self.currency}",
            f"• Price Per Item: **{final_price // amount}** {self.currency}"
        ]
        
        embed.add_field(
            name="💰 Price Breakdown",
            value="\n".join(price_text),
            inline=False
        )
        
        # Add remaining balance
        new_balance = await db.get_wallet_balance(user.id, guild.id if guild else None)
        embed.add_field(
            name="💳 Remaining Balance",
            value=f"**{new_balance}** {self.currency}",
            inline=True
        )
        
        # Add stock info if they have any
        if user_stock > 0:
            embed.add_field(
                name="📈 Your Bazaar Stock",
                value=f"**{user_stock}** (Current discount: {user_discount*100:.0f}%)",
                inline=True
            )
        
        # Add secret shop hint if close to threshold
        if self.stock_threshold - user_stock <= 50 and user_stock < self.stock_threshold:
            embed.add_field(
                name="🔍 Secret Shop Hint",
                value=f"Just {self.stock_threshold - user_stock} more stock needed to unlock!",
                inline=False
            )
        
        # Try to edit previous message if exists
        try:
            if hasattr(self, 'last_purchase_message') and self.last_purchase_message:
                await self.last_purchase_message.edit(embed=embed)
            else:
                if is_interaction:
                    msg = await interaction.followup.send(embed=embed)
                else:
                    msg = await respond(embed=embed)
                self.last_purchase_message = msg
        except Exception as e:
            self.logger.error(f"Error updating purchase message: {e}")
            if is_interaction:
                await interaction.followup.send(embed=embed)
            else:
                await respond(embed=embed)
    
    @commands.command(name="bazaarstock", aliases=["bstock"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def bazaar_stock(self, ctx, amount: int = 1):
        """Buy bazaar stock"""
        await self.handle_stock_purchase(ctx, amount)
    
    @commands.command(name="secret-bazaar", aliases=["secretmarket", "sm"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def secret_bazaar(self, ctx):
        """View the secret bazaar shop (requires 500+ stock)"""
        user_stock = await self.get_user_stock(ctx.author.id)
        
        if user_stock < self.stock_threshold:
            await ctx.reply(f"❌ You need at least {self.stock_threshold} bazaar stock to access the secret shop!")
            return
        
        # Create embed
        embed = discord.Embed(
            title="🔒 Secret Bazaar Shop",
            description=f"*Exclusive items for elite traders*\n\n"
                      f"Your Bazaar Stock: **{user_stock}**",
            color=0x2ecc71
        )
        
        # Add secret items
        if not self.current_secret_items:
            embed.add_field(
                name="Current Offerings",
                value="The secret shop is currently being restocked...",
                inline=False
            )
        else:
            for item in self.current_secret_items:
                embed.add_field(
                    name=f"🔮 {item['name']}",
                    value=f"{item.get('description', 'No description')}\n"
                         f"Price: **{item.get('price', 0)}** {self.currency}\n"
                         f"`{ctx.prefix}secret-buy {item.get('id', item['name'].lower().replace(' ', '_'))}`",
                    inline=False
                )
        
        # Add reset time
        next_reset = self.secret_last_reset + timedelta(minutes=self.secret_shop_reset_interval)
        time_left = next_reset - datetime.now()
        minutes_left = max(0, int(time_left.total_seconds() / 60))
        
        embed.set_footer(text=f"Secret shop restocks in {minutes_left} minutes")
        
        await ctx.reply(embed=embed)
    
    @commands.command(name="secret-buy", aliases=["sbuy"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def secret_buy(self, ctx, item_id: str):
        """Buy an item from the secret bazaar"""
        user_stock = await self.get_user_stock(ctx.author.id)
        
        if user_stock < self.stock_threshold:
            await ctx.reply(f"❌ You need at least {self.stock_threshold} bazaar stock to access the secret shop!")
            return
        
        # Find the item
        item = None
        for secret_item in self.current_secret_items:
            if secret_item.get("id") == item_id or secret_item["name"].lower().replace(" ", "_") == item_id.lower():
                item = secret_item
                break
        
        if not item:
            await ctx.reply(f"❌ Item `{item_id}` not found in current secret shop offerings.")
            return
        
        # Check balance
        price = item["price"]
        balance = await db.get_wallet_balance(ctx.author.id, ctx.guild.id if hasattr(ctx, 'guild') else None)
        if balance < price:
            await ctx.reply(f"❌ Insufficient funds! You need {price} {self.currency} but only have {balance}.")
            return
        
        # Deduct money
        if not await db.update_wallet(ctx.author.id, -price, ctx.guild.id if hasattr(ctx, 'guild') else None):
            await ctx.reply("❌ Failed to process payment. Please try again.")
            return
        
        # Add item to inventory
        clean_item = {
            "id": item.get("id", item["id"] if "id" in item else item["name"].lower().replace(" ", "_")),
            "name": item["name"],
            "description": item.get("description", ""),
            "price": price,
            "value": price,
            "type": item.get("type", "item"),
            "secret_item": True
        }
        
        success = await db.add_to_inventory(ctx.author.id, ctx.guild.id if hasattr(ctx, 'guild') else None, clean_item, 1)
        
        if not success:
            # Refund if failed
            await db.update_wallet(ctx.author.id, price, ctx.guild.id if hasattr(ctx, 'guild') else None)
            await ctx.reply("❌ Failed to add item to inventory. You have been refunded.")
            return
        
        # Update bazaar stats
        self.total_spent += price
        
        # Send success message
        embed = discord.Embed(
            title="✅ Secret Purchase Complete",
            description=f"You bought **{item['name']}** from the secret bazaar!",
            color=0x2ecc71
        )
        
    async def handle_stock_purchase(self, interaction_or_ctx, amount: int = 1):
        """Handle stock purchase from either interaction or command"""
        is_interaction = isinstance(interaction_or_ctx, discord.Interaction)
        
        if is_interaction:
            interaction = interaction_or_ctx
            user = interaction.user
            guild = interaction.guild
            respond = interaction.response.send_message
        else:
            ctx = interaction_or_ctx
            user = ctx.author
            guild = ctx.guild
            respond = ctx.reply

        if amount <= 0:
            msg = "❌ Amount must be positive."
            if is_interaction:
                await respond(msg, ephemeral=True)
            else:
                await respond(msg)
            return

        if amount > 100:
            msg = "❌ Maximum 100 stock per purchase."
            if is_interaction:
                await respond(msg, ephemeral=True)
            else:
                await respond(msg)
            return

        # Calculate price
        stock_price = self.calculate_stock_price()
        total_cost = stock_price * amount

        # Check balance
        balance = await db.get_wallet_balance(user.id, guild.id if guild else None)
        if balance < total_cost:
            msg = f"❌ Insufficient funds! You need {total_cost} {self.currency} but only have {balance}."
            if is_interaction:
                await respond(msg, ephemeral=True)
            else:
                await respond(msg)
            return

        # For interactions, defer first
        if is_interaction:
            await interaction.response.defer()

        # Deduct money
        if not await db.update_wallet(user.id, -total_cost, guild.id if guild else None):
            msg = "❌ Failed to process payment. Please try again."
            if is_interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await respond(msg)
            return

        # Add stock
        if not await self.add_user_stock(user.id, amount):
            # Refund if failed
            await db.update_wallet(user.id, total_cost, guild.id if guild else None)
            msg = "❌ Failed to add stock. You have been refunded."
            if is_interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await respond(msg)
            return

        # Update bazaar stats
        self.total_spent += total_cost

        # Get updated user data
        new_stock = await self.get_user_stock(user.id)
        new_discount = self.calculate_discount(new_stock)
        new_balance = await db.get_wallet_balance(user.id, guild.id if guild else None)

        # Create/update embed
        embed = discord.Embed(
            title="✅ Stock Purchase Complete",
            description=f"You bought **{amount}** more bazaar stock!" if hasattr(self, 'last_stock_message') 
                    else f"You bought **{amount}** bazaar stock!",
            color=0x00ff00
        )

        embed.add_field(
            name="Purchase Details",
            value=f"Price per Stock: **{stock_price}** {self.currency}\n"
                f"Total Cost: **{total_cost}** {self.currency}",
            inline=False
        )

        embed.add_field(
            name="Your New Holdings",
            value=f"Total Stock: **{new_stock}**\n"
                f"Current Discount: **{new_discount*100:.0f}%**\n"
                f"Remaining Balance: **{new_balance}** {self.currency}",
            inline=False
        )

        if new_stock >= self.stock_threshold:
            embed.add_field(
                name="🔓 Secret Shop Unlocked!",
                value=f"You now have access to the secret bazaar shop with {new_stock} stock!",
                inline=False
            )

        try:
            if hasattr(self, 'last_stock_message') and self.last_stock_message:
                # Edit the existing message
                if is_interaction:
                    await self.last_stock_message.edit(embed=embed)
                else:
                    await self.last_stock_message.edit(embed=embed)
            else:
                # Send new message and store reference
                if is_interaction:
                    msg = await interaction.followup.send(embed=embed)
                else:
                    msg = await respond(embed=embed)
                self.last_stock_message = msg
        except Exception as e:
            self.logger.error(f"Error updating stock purchase message: {e}")
            # Fallback to sending new message if edit fails
            if is_interaction:
                await interaction.followup.send(embed=embed)
            else:
                await respond(embed=embed)

    async def cog_check(self, ctx):
        """Global check for all commands in this cog"""
        # Check if user has accepted ToS
        if not await check_tos_acceptance(ctx.author.id):
            await prompt_tos_acceptance(ctx)
            return False
        return True

async def setup(bot):
    await bot.add_cog(Bazaar(bot))