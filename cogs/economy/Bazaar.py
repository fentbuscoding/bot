import discord
from discord.ext import commands, tasks
from typing import Dict, List, Optional
from collections import defaultdict
import random
import asyncio
import math
from cogs.logging.logger import CogLogger
from utils.db import async_db as db
from datetime import datetime, timedelta
import hashlib

class BazaarView(discord.ui.View):
    def __init__(self, cog, timeout=180):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.message = None
        
    @discord.ui.button(label="🛒 Buy Items", style=discord.ButtonStyle.primary)
    async def buy_items(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_bazaar_purchase(interaction)
        
    @discord.ui.button(label="📈 Buy Stock", style=discord.ButtonStyle.secondary)
    async def buy_stock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.handle_stock_purchase(interaction)
        
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
        
        # Get items from shop cog if available
        shop_cog = self.bot.get_cog("Shop")
        if shop_cog:
            shop_items["items"].extend(shop_cog.SHOP_ITEMS.values())
            shop_items["rods"].extend([item for item in shop_cog.FISHING_ITEMS.values() if item.get("type") == "rod"])
            shop_items["bait"].extend([item for item in shop_cog.FISHING_ITEMS.values() if item.get("type") == "bait"])
            if hasattr(shop_cog, "UPGRADE_ITEMS"):
                shop_items["upgrades"].extend(shop_cog.UPGRADE_ITEMS.values())
        
        # Get items from database collections
        try:
            # Get shop items from database
            shop_items["items"].extend(await db.get_shop_items("items"))
            shop_items["upgrades"].extend(await db.get_shop_items("upgrades"))
            
            # Get fishing items
            fishing_items = await db.get_shop_items("fishing")
            shop_items["rods"].extend([item for item in fishing_items if item.get("type") == "rod"])
            shop_items["bait"].extend([item for item in fishing_items if item.get("type") == "bait"])
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
            
            # Select categories based on weights
            categories = []
            for category, weight in self.category_weights.items():
                categories.extend([category] * int(weight * 10))
            
            selected_category = random.choice(categories)
            
            # Get 3-5 random items from selected category
            category_items = all_items.get(selected_category, [])
            if not category_items:
                self.logger.warning(f"No items found for category: {selected_category}")
                return
                
            num_items = random.randint(3, 5)
            self.current_items = random.sample(category_items, min(num_items, len(category_items)))
            
            # Apply bazaar-specific modifications
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
                      f"Current Stock Price: **{self.calculate_stock_price()}** {self.currency}",
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
                embed.add_field(
                    name=f"🛍️ {item['name']}",
                    value=f"{item.get('description', 'No description')}{discount_text}\n"
                         f"`{ctx.prefix}bazaar buy {item.get('id', item['name'].lower().replace(' ', '_'))}`",
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
    
    @commands.command(name="bazaar-buy", aliases=["bbuy"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def bazaar_buy(self, ctx, item_id: str, amount: int = 1):
        """Buy an item from the bazaar"""
        await self.handle_bazaar_purchase(ctx, item_id, amount)
    
    async def handle_bazaar_purchase(self, interaction_or_ctx, item_id: str = None, amount: int = 1):
        """Handle bazaar purchase from either interaction or command"""
        is_interaction = isinstance(interaction_or_ctx, discord.Interaction)
        
        if is_interaction:
            # For button interactions, use the interaction directly
            interaction = interaction_or_ctx
            user = interaction.user
            guild = interaction.guild
            respond = interaction.response.send_message
            # For button clicks, we need to get the item_id from a modal or other input method
            # Here we'll just use the first item as an example - you'll need to implement proper item selection
            if not self.current_items:
                await respond("❌ No items available in the bazaar right now.", ephemeral=True)
                return
            item = self.current_items[0]  # Default to first item - implement proper selection logic
        else:
            # For commands, use the normal context
            ctx = interaction_or_ctx
            user = ctx.author
            guild = ctx.guild
            respond = ctx.reply
            
            # Find the item for command-based purchases
            item = None
            for bazaar_item in self.current_items:
                if bazaar_item.get("id") == item_id or bazaar_item["name"].lower().replace(" ", "_") == item_id.lower():
                    item = bazaar_item
                    break
            
            if not item:
                await respond(f"❌ Item `{item_id}` not found in current bazaar offerings.")
                return

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
            msg = f"❌ Insufficient funds! You need {final_price} {self.currency} but only have {balance}."
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
            "id": item["id"],
            "name": item["name"],
            "description": item.get("description", ""),
            "price": item["price"],
            "value": item["price"],
            "type": item.get("type", "item"),
            "bazaar_item": True
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
        
        # Send success message
        embed = discord.Embed(
            title="✅ Purchase Complete",
            description=f"You bought **{amount}x {item['name']}** from the bazaar!",
            color=0x00ff00
        )
        
        price_text = []
        price_text.append(f"Base Price: **{item['price'] * amount}** {self.currency}")
        if user_discount > 0:
            price_text.append(f"Discount ({user_discount*100:.0f}%): **-{discount_amount}** {self.currency}")
        price_text.append(f"Total Paid: **{final_price}** {self.currency}")
        
        embed.add_field(
            name="Price Breakdown",
            value="\n".join(price_text),
            inline=False
        )
        
        new_balance = await db.get_wallet_balance(user.id, guild.id if guild else None)
        embed.add_field(
            name="Remaining Balance",
            value=f"**{new_balance}** {self.currency}",
            inline=True
        )
        
        if is_interaction:
            await interaction.followup.send(embed=embed)
        else:
            await respond(embed=embed)
    
    @commands.command(name="bazaar-stock", aliases=["bstock"])
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
            "id": item["id"],
            "name": item["name"],
            "description": item.get("description", ""),
            "price": price,
            "value": price,
            "type": item.get("type", "item"),
            "secret_item": True
        }
        
        success = await db.add_to_inventory(ctx.author.id, ctx.guild.id if hasattr(ctx, 'guild') else None, clean_item)
        
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

async def setup(bot):
    await bot.add_cog(Bazaar(bot))