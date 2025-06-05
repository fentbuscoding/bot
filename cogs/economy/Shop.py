import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, List, Union
import os
import json
import asyncio
from discord.ui import Button, View, Select, Modal, TextInput

with open('data/config.json', 'r') as f:
    config = json.load(f)

class BuyModal(Modal, title="Purchase Confirmation"):
    def __init__(self, item: Dict, max_amount: int, currency: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item = item
        self.max_amount = max_amount
        self.currency = currency
        
        self.amount = TextInput(
            label=f"Amount (Max: {max_amount})",
            placeholder="Enter amount to purchase...",
            default="1",
            min_length=1,
            max_length=len(str(max_amount)),
        )
        
        self.add_item(self.amount)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            if amount <= 0:
                await interaction.response.send_message("Amount must be positive!", ephemeral=True)
                return
            if amount > self.max_amount:
                await interaction.response.send_message(f"You can't afford that many! Max: {self.max_amount}", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Please enter a valid number!", ephemeral=True)
            return
        
        total_price = self.item['price'] * amount
        embed = discord.Embed(
            title="Purchase Successful!",
            description=f"You bought {amount}x **{self.item['name']}** for {total_price}{self.currency}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()

class ShopItemButton(Button):
    def __init__(self, item: Dict, currency: str, user_balance: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item = item
        self.currency = currency
        self.user_balance = user_balance
        self.label = item['name']
        self.emoji = "🛒" if item['type'] == 'potion' else "💰"
        
    async def callback(self, interaction: discord.Interaction):
        max_amount = self.user_balance // self.item['price'] if self.item['price'] > 0 else 1
        if max_amount <= 0:
            await interaction.response.send_message("You can't afford this item!", ephemeral=True)
            return
            
        modal = BuyModal(
            item=self.item,
            max_amount=max_amount,
            currency=self.currency,
            title=f"Buy {self.item['name']}"
        )
        await interaction.response.send_modal(modal)
        await modal.wait()
        
        # Handle the purchase after modal submission
        if modal.amount.value:
            try:
                amount = int(modal.amount.value)
                await self.view.cog.process_purchase(interaction.user.id, self.item['_id'], amount, self.item['type'])
            except Exception as e:
                print(f"Error processing purchase: {e}")

class ShopTypeSelect(Select):
    def __init__(self, cog, *args, **kwargs):
        options = [
            discord.SelectOption(label="Fishing Rods", value="rod", description="Upgrade your fishing gear"),
            discord.SelectOption(label="Baits", value="bait", description="Better bait for better catches"),
            discord.SelectOption(label="Upgrades", value="upgrade", description="Permanent account upgrades"),
            discord.SelectOption(label="Potions", value="potion", description="Temporary boosts and effects"),
        ]
        super().__init__(placeholder="Select a shop type...", options=options, *args, **kwargs)
        self.cog = cog
    
    async def callback(self, interaction: discord.Interaction):
        await self.cog.display_shop(interaction, self.values[0])

class ShopView(View):
    def __init__(self, cog, shop_type: str, items: List[Dict], user_balance: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cog = cog
        self.shop_type = shop_type
        self.current_page = 0
        self.items = items
        self.user_balance = user_balance
        self.items_per_page = 5
        
        # Add shop type selector
        self.add_item(ShopTypeSelect(cog))
        
        # Add navigation buttons
        self.add_item(Button(style=discord.ButtonStyle.blurple, emoji="⬅️", custom_id="prev_page"))
        self.add_item(Button(style=discord.ButtonStyle.blurple, emoji="➡️", custom_id="next_page"))
        
        # Add item buttons for current page
        self.update_view()

    def get_page_embed(self) -> discord.Embed:
        """Create an embed for the current page"""
        embed = discord.Embed(
            title=f"{self.shop_type.capitalize()} Shop",
            description=f"Your balance: {self.user_balance}{self.cog.currency}\n\nPage {self.current_page + 1}/{(len(self.items) + self.items_per_page - 1) // self.items_per_page}",
            color=discord.Color.blue()
        )
        
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        for item in self.items[start_idx:end_idx]:
            embed.add_field(
                name=f"{item['name']} - {item['price']}{self.cog.currency}",
                value=item.get('description', 'No description available'),
                inline=False
            )
        
        return embed

    def update_view(self):
        """Update both buttons and embed for current page"""
        # Clear existing item buttons (keep first 3 buttons which are nav/select)
        for child in self.children[3:]:
            self.remove_item(child)
        
        # Add buttons for current page items
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        for item in self.items[start_idx:end_idx]:
            self.add_item(ShopItemButton(
                item=item,
                currency=self.cog.currency,
                user_balance=self.user_balance,
                style=discord.ButtonStyle.green
            ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.data.get("custom_id") in ["prev_page", "next_page"]:
            if interaction.data["custom_id"] == "prev_page":
                if self.current_page > 0:
                    self.current_page -= 1
            else:
                if (self.current_page + 1) * self.items_per_page < len(self.items):
                    self.current_page += 1
            
            self.update_view()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
            return False
        return True

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currency = "💰"  # Customize your currency symbol
        
        # Motor MongoDB connection
        self.mongo_uri = config['MONGO_URI']
        self.client = AsyncIOMotorClient(self.mongo_uri)
        self.db = self.client.bronxbot
        self.upgrades = self.db.upgrades
        self.bait = self.db.bait
        self.rods = self.db.rods
        self.potions = self.db.potions
        
        # Define shop types and their aliases
        self.shop_aliases = {
            'rod': ['rods', 'fishingrod', 'fishingrods'],
            'bait': ['baits', 'fishingbait'],
            'upgrade': ['upg', 'upgrades', 'perks'],
            'potion': ['potions', 'boost', 'boosts', 'pot']
        }
        self.supported_types = list(self.shop_aliases.keys())

    def resolve_shop_type(self, input_type: str) -> Optional[str]:
        """Resolve a shop type from its name or aliases"""
        input_type = input_type.lower()
        for main_type, aliases in self.shop_aliases.items():
            if input_type == main_type or input_type in aliases:
                return main_type
        return None

    async def get_collection(self, item_type: str):
        """Get the appropriate collection for the item type"""
        resolved_type = self.resolve_shop_type(item_type)
        if not resolved_type:
            return None
            
        if resolved_type == "rod":
            return self.rods
        elif resolved_type == "bait":
            return self.bait
        elif resolved_type == "upgrade":
            return self.upgrades
        elif resolved_type == "potion":
            return self.potions
        return None

    async def get_item(self, item_id: str, item_type: str) -> Optional[Dict]:
        """Get an item from the appropriate collection"""
        collection = await self.get_collection(item_type)
        if not collection:
            return None
        return await collection.find_one({"_id": item_id})

    async def get_shop_items(self, item_type: str) -> List[Dict]:
        """Get all items of a specific type, sorted by price (cheapest first)"""
        collection = await self.get_collection(item_type)
        if not collection:
            return []
        
        # Sort items by price in ascending order (cheapest first)
        items = await collection.find().sort("price", 1).to_list(None)
        return items

    # Database helper methods
    async def get_user_data(self, user_id: int) -> Dict:
        """Get user's document from database"""
        return await self.db.users.find_one({"_id": str(user_id)})

    async def get_wallet(self, user_id: int) -> int:
        """Get user's wallet balance"""
        user = await self.get_user_data(user_id)
        return user.get('wallet', 0) if user else 0

    async def update_wallet(self, user_id: int, amount: int) -> bool:
        """Update user's wallet balance"""
        result = await self.db.users.update_one(
            {"_id": str(user_id)},
            {"$inc": {"wallet": amount}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
            

    async def add_item_to_inventory(self, user_id: int, item_id: str, item_type: str, amount: int = 1) -> bool:
        """Simplified inventory addition for both rods and bait"""
        try:
            inventory_field = f"inventory.{item_type}.{item_id}"
            result = await self.db.users.update_one(
                {"_id": str(user_id)},
                {"$inc": {inventory_field: amount}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            print(f"Error adding item to inventory: {e}")
            return False

    async def process_purchase(self, user_id: int, item_id: str, amount: int, item_type: str) -> bool:
        """Process a purchase transaction with debug prints"""
        print(f"\n=== Starting purchase process ===")
        print(f"User: {user_id}, Item: {item_id}, Amount: {amount}, Type: {item_type}")
        
        item = await self.get_item(item_id, item_type)
        if not item:
            print("Purchase failed: Item not found")
            return False
        print(f"Item found: {item['name']} (Price: {item['price']})")
        
        total_price = item['price'] * amount
        print(f"Total price: {total_price}")
        
        user_balance = await self.get_wallet(user_id)
        print(f"User balance: {user_balance}")
        
        if user_balance < total_price:
            print("Purchase failed: Insufficient funds")
            return False
        
        # Deduct money
        print("Attempting to deduct money...")
        wallet_updated = await self.update_wallet(user_id, -total_price)
        print(f"Wallet updated: {wallet_updated}")
        
        if not wallet_updated:
            print("Purchase failed: Wallet update failed")
            return False
        
        # Add item to inventory
        print("Attempting to add item to inventory...")
        inventory_updated = await self.add_item_to_inventory(user_id, item_id, item_type, amount)
        print(f"Inventory updated: {inventory_updated}")
        
        if not inventory_updated:
            print("Warning: Inventory update failed, refunding money...")
            await self.update_wallet(user_id, total_price)  # Refund if inventory update failed
            return False
        
        print("=== Purchase successful! ===")
        return True

    @commands.command(aliases=['store'])
    async def shop(self, ctx, shop_type: str = None):
        """Display the shop interface"""
        if not shop_type:
            # Show main shop menu
            embed = discord.Embed(
                title="Shop Menu",
                description=f"Select a shop type from the dropdown below!\n\nYour balance: {await self.get_wallet(ctx.author.id)}{self.currency}",
                color=discord.Color.blue()
            )
            view = View()
            view.add_item(ShopTypeSelect(self))
            await ctx.send(embed=embed, view=view)
        else:
            # Resolve the shop type from aliases
            resolved_type = self.resolve_shop_type(shop_type)
            if not resolved_type:
                await ctx.send("Invalid shop type! Available types: rods, bait, upgrades, potions")
                return
            
            await self.display_shop(ctx, resolved_type)

    async def display_shop(self, interaction: Union[discord.Interaction, commands.Context], shop_type: str):
        """Display the shop for a specific type"""
        resolved_type = self.resolve_shop_type(shop_type)
        if not resolved_type:
            if isinstance(interaction, discord.Interaction):
                await interaction.response.send_message("Invalid shop type!", ephemeral=True)
            else:
                await interaction.send("Invalid shop type!")
            return
        
        items = await self.get_shop_items(resolved_type)
        if not items:
            if isinstance(interaction, discord.Interaction):
                await interaction.response.send_message(f"No items found in the {resolved_type} shop!", ephemeral=True)
            else:
                await interaction.send(f"No items found in the {resolved_type} shop!")
            return
        
        # Get the user ID correctly for both Interaction and Context objects
        user_id = interaction.user.id if isinstance(interaction, discord.Interaction) else interaction.author.id
        user_balance = await self.get_wallet(user_id)
        
        embed = discord.Embed(
            title=f"{resolved_type.capitalize()} Shop",
            description=f"Your balance: {user_balance}{self.currency}\n\nSelect an item to purchase:",
            color=discord.Color.blue()
        )
        
        # Add items to embed (just for display, buttons will handle actual purchasing)
        start_idx = 0
        end_idx = min(5, len(items))
        for item in items[start_idx:end_idx]:
            embed.add_field(
                name=f"{item['name']} - {item['price']}{self.currency}",
                value=item.get('description', 'No description available'),
                inline=False
            )
        
        view = ShopView(self, resolved_type, items, user_balance, timeout=180)
        
        if isinstance(interaction, discord.Interaction):
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.send(embed=embed, view=view)


    # Update the ShopTypeSelect options to use the main types
    class ShopTypeSelect(Select):
        def __init__(self, cog, *args, **kwargs):
            options = [
                discord.SelectOption(label="Fishing Rods", value="rod", description="Upgrade your fishing gear"),
                discord.SelectOption(label="Baits", value="bait", description="Better bait for better catches"),
                discord.SelectOption(label="Upgrades", value="upgrade", description="Permanent account upgrades"),
                discord.SelectOption(label="Potions", value="potion", description="Temporary boosts and effects"),
            ]
            super().__init__(placeholder="Select a shop type...", options=options, *args, **kwargs)
            self.cog = cog
        
        async def callback(self, interaction: discord.Interaction):
            await self.cog.display_shop(interaction, self.values[0])

    @commands.command(name="sell", aliases=['sellitem'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def sell_item(self, ctx, item_id: str, amount: int = 1):
        """Sell items from your inventory back to the shop"""
        if amount <= 0:
            return await ctx.reply("❌ Amount must be positive!")
        
        try:
            # Get user data and inventory
            user_data = await self.get_user_data(ctx.author.id)
            if not user_data:
                return await ctx.reply("❌ User data not found!")
            
            inventory = user_data.get("inventory", {})
            
            # Check all possible item types
            item_type = None
            item_data = None
            
            # Search through all inventory categories
            for category in ['rod', 'bait', 'upgrade', 'potion']:
                if item_id in inventory.get(category, {}):
                    item_type = category
                    current_amount = inventory[category][item_id]
                    break
            
            if not item_type:
                return await ctx.reply("❌ Item not found in your inventory!")
            
            if current_amount < amount:
                return await ctx.reply(f"❌ You only have {current_amount} of this item!")
            
            # Get item data from the appropriate collection
            collection = await self.get_collection(item_type)
            if not collection:
                return await ctx.reply("❌ Invalid item type!")
            
            item_data = await collection.find_one({"_id": item_id})
            if not item_data:
                return await ctx.reply("❌ Item data not found in shop!")
            
            # Check if item has a sell price (default to 50% of purchase price if not)
            sell_price = item_data.get('sell_price', int(item_data.get('price', 0) * 0.5))
            if sell_price <= 0:
                return await ctx.reply("❌ This item cannot be sold!")
            
            total_value = sell_price * amount
            
            # Confirm sale with user
            confirm_embed = discord.Embed(
                title="🛒 Confirm Sale",
                description=f"Sell {amount}x **{item_data['name']}** for {total_value}{self.currency}?",
                color=discord.Color.orange()
            )
            confirm_embed.set_footer(text="React with ✅ to confirm or ❌ to cancel")
            
            confirm_msg = await ctx.reply(embed=confirm_embed)
            await confirm_msg.add_reaction("✅")
            await confirm_msg.add_reaction("❌")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
            
            try:
                reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
                
                if str(reaction.emoji) == "❌":
                    return await confirm_msg.edit(embed=discord.Embed(
                        description="❌ Sale cancelled",
                        color=discord.Color.red()
                    ))
                
                # Process the sale
                # Remove items from inventory
                await self.db.users.update_one(
                    {"_id": str(ctx.author.id)},
                    {"$inc": {f"inventory.{item_type}.{item_id}": -amount}}
                )
                
                # Clean up if amount reaches 0
                if current_amount - amount <= 0:
                    await self.db.users.update_one(
                        {"_id": str(ctx.author.id)},
                        {"$unset": {f"inventory.{item_type}.{item_id}": ""}}
                    )
                
                # Add money to wallet
                await self.update_wallet(ctx.author.id, total_value)
                
                # Send success message
                success_embed = discord.Embed(
                    title="💰 Sale Complete!",
                    description=f"Sold {amount}x **{item_data['name']}** for {total_value}{self.currency}",
                    color=discord.Color.green()
                )
                await confirm_msg.edit(embed=success_embed)
                await confirm_msg.clear_reactions()
                
            except asyncio.TimeoutError:
                await confirm_msg.edit(embed=discord.Embed(
                    description="⌛ Sale timed out",
                    color=discord.Color.red()
                ))
                await confirm_msg.clear_reactions()
        
        except Exception as e:
            print(f"Error in sell command: {e}")
            await ctx.reply("❌ An error occurred while processing your sale!")

    @commands.command(name="inventory", aliases=['inv', 'items'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def show_inventory(self, ctx):
        """View your inventory with all items and quick-sell options"""
        user_data = await self.get_user_data(ctx.author.id)
        if not user_data:
            return await ctx.reply("❌ User data not found!")
        
        inventory = user_data.get("inventory", {})
        
        # Organize items by category
        categories = {
            "🎣 Fishing Rods": ("rod", inventory.get("rod", {})),
            "🪱 Bait": ("bait", inventory.get("bait", {})),
            "⚡ Upgrades": ("upgrade", inventory.get("upgrade", {})),
            "🧪 Potions": ("potion", inventory.get("potion", {})),
        }
        
        # Create pages for each category (only those with items)
        pages = []
        for category_name, (item_type, items) in categories.items():
            if not items:  # Skip empty categories
                continue
                
            embed = discord.Embed(
                title=f"{ctx.author.display_name}'s {category_name}",
                color=discord.Color.blue()
            )
            
            # Get the correct collection
            collection = await self.get_collection(item_type)
            if not collection:
                continue  # Skip if collection doesn't exist
                
            # Add items to embed
            for item_id, amount in items.items():
                item_data = await collection.find_one({"_id": item_id})
                if not item_data:
                    continue
                    
                sell_price = item_data.get('sell_price', int(item_data.get('price', 0)) * 0.5)
                embed.add_field(
                    name=f"{item_data['name']} (x{amount})",
                    value=f"{item_data.get('description', 'No description')}\n"
                        f"Sell Value: {sell_price}{self.currency}",
                    inline=False
                )
            
            if not embed.fields:  # Skip if no valid items were added
                continue
                
            pages.append((embed, item_type))  # Store embed with its item type
        
        if not pages:
            return await ctx.reply("Your inventory is empty!")
        
        class InventoryView(discord.ui.View):
            def __init__(self, cog, pages, author, timeout=60):
                super().__init__(timeout=timeout)
                self.cog = cog
                self.pages = pages
                self.author = author
                self.current_page = 0
                
                # Disable navigation buttons if only one page
                if len(pages) == 1:
                    for item in self.children:
                        if isinstance(item, discord.ui.Button) and item.emoji in ["⬅️", "➡️"]:
                            item.disabled = True
            
            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                return interaction.user == self.author
            
            @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.blurple)
            async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_page > 0:
                    self.current_page -= 1
                    await self.update_ui(interaction)
            
            @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.blurple)
            async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_page < len(self.pages) - 1:
                    self.current_page += 1
                    await self.update_ui(interaction)
            
            async def update_ui(self, interaction: discord.Interaction):
                """Update the UI for the current page"""
                embed, item_type = self.pages[self.current_page]
                
                # Clear existing sell buttons (keep navigation buttons)
                for child in self.children.copy():
                    if isinstance(child, discord.ui.Button) and child.custom_id and child.custom_id.startswith("sell_"):
                        self.remove_item(child)
                
                # Add sell buttons for current page items
                user_data = await self.cog.get_user_data(self.author.id)
                current_items = user_data.get("inventory", {}).get(item_type, {})
                
                for i, field in enumerate(embed.fields):
                    item_name = field.name.split(" (x")[0]
                    item_id = item_name.lower().replace(" ", "_")
                    if item_id in current_items:
                        sell_button = discord.ui.Button(
                            label=f"Sell 1 {item_name}",
                            style=discord.ButtonStyle.red,
                            custom_id=f"sell_{item_id}",
                            row=1
                        )
                        
                        async def sell_callback(interaction: discord.Interaction, item_id=item_id):
                            await self.handle_sell(interaction, item_id, item_type, 1)
                        
                        sell_button.callback = sell_callback
                        self.add_item(sell_button)
                
                await interaction.response.edit_message(embed=embed, view=self)
            
            async def handle_sell(self, interaction: discord.Interaction, item_id: str, item_type: str, amount: int):
                # Get current user data
                user_data = await self.cog.get_user_data(interaction.user.id)
                if not user_data:
                    await interaction.followup.send("❌ User data not found!", ephemeral=True)
                    return
                
                current_amount = user_data.get("inventory", {}).get(item_type, {}).get(item_id, 0)
                if current_amount < amount:
                    await interaction.followup.send(
                        f"❌ You don't have enough {item_id.replace('_', ' ')}!", 
                        ephemeral=True
                    )
                    return
                
                # Get item data
                collection = await self.cog.get_collection(item_type)
                if not collection:
                    await interaction.followup.send("❌ Invalid item type!", ephemeral=True)
                    return
                
                item_data = await collection.find_one({"_id": item_id})
                if not item_data:
                    await interaction.followup.send("❌ Item data not found!", ephemeral=True)
                    return
                
                sell_price = item_data.get('sell_price', int(item_data.get('price', 0)*0.5))
                total_value = sell_price * amount
                
                # Process sale
                await self.cog.db.users.update_one(
                    {"_id": str(interaction.user.id)},
                    {"$inc": {
                        f"inventory.{item_type}.{item_id}": -amount,
                        "wallet": total_value
                    }}
                )
                
                # Clean up if amount reaches 0
                if current_amount - amount <= 0:
                    await self.cog.db.users.update_one(
                        {"_id": str(interaction.user.id)},
                        {"$unset": {f"inventory.{item_type}.{item_id}": ""}}
                    )
                
                # Send success message
                await interaction.followup.send(
                    f"✅ Sold {amount}x {item_data['name']} for {total_value}{self.cog.currency}!",
                    ephemeral=True
                )
                
                # Update the inventory display
                await self.update_ui(interaction)
        
        view = InventoryView(self, pages, ctx.author)

        # Send the initial message
        if pages:
            message = await ctx.reply(embed=pages[0][0], view=view)
            # Trigger initial UI update to add sell buttons
            await view.update_ui(await message.channel.fetch_message(message.id))
        else:
            await ctx.reply("Your inventory is empty!")

async def setup(bot):
    await bot.add_cog(Shop(bot))