import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, List, Union
import os
import json
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
        self.supported_types = ["rod", "bait", "pickaxe", "upgrade", "potion"]

    async def get_collection(self, item_type: str):
        """Get the appropriate collection for the item type"""
        if item_type == "rod":
            return self.rods
        elif item_type == "bait":
            return self.bait
        elif item_type == "upgrade":
            return self.upgrades
        elif item_type == "potion":
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
        """Add an item to user's inventory with special handling for baits"""
        try:
            # Special case for bait items
            if item_type == "bait":
                # Check if we should use the object structure (preferred) or array structure
                user = await self.get_user_data(user_id)
                
                if user and 'inventory' in user and 'bait' in user['inventory'] and isinstance(user['inventory']['bait'], dict):
                    # Use the object structure in inventory.bait
                    inventory_field = f"inventory.bait.{item_id}"
                else:
                    # Fallback to array structure (should be migrated eventually)
                    inventory_field = "bait"
                    
                    # Ensure we're pushing to an array
                    await self.db.users.update_one(
                        {"_id": str(user_id)},
                        {"$setOnInsert": {"bait": []}},
                        upsert=True
                    )
            else:
                # Standard handling for other item types
                inventory_field = f"inventory.{item_type}.{item_id}"
            
            # Perform the update
            if item_type == "bait" and inventory_field == "bait":
                # For array structure, we need to find and update or push new item
                user = await self.get_user_data(user_id)
                existing_item = next((item for item in user.get('bait', []) if item.get('_id') == item_id), None)
                
                if existing_item:
                    # Update existing item's amount
                    result = await self.db.users.update_one(
                        {"_id": str(user_id), "bait._id": item_id},
                        {"$inc": {"bait.$.amount": amount}}
                    )
                else:
                    # Push new item to array
                    item_data = await self.get_item(item_id, item_type)
                    if not item_data:
                        return False
                        
                    new_item = {
                        "_id": item_id,
                        "name": item_data.get('name', 'Unknown Bait'),
                        "amount": amount,
                        "description": item_data.get('description', ''),
                        "catch_rates": item_data.get('catch_rates', {})
                    }
                    
                    result = await self.db.users.update_one(
                        {"_id": str(user_id)},
                        {"$push": {"bait": new_item}}
                    )
            else:
                # Standard update for object structure
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

    @commands.command()
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
            await self.display_shop(ctx, shop_type)

    async def display_shop(self, interaction: Union[discord.Interaction, commands.Context], shop_type: str):
        """Display the shop for a specific type"""
        if shop_type not in self.supported_types:
            if isinstance(interaction, discord.Interaction):
                await interaction.response.send_message("Invalid shop type!", ephemeral=True)
            else:
                await interaction.send("Invalid shop type!")
            return
        
        items = await self.get_shop_items(shop_type)
        if not items:
            if isinstance(interaction, discord.Interaction):
                await interaction.response.send_message(f"No items found in the {shop_type} shop!", ephemeral=True)
            else:
                await interaction.send(f"No items found in the {shop_type} shop!")
            return
        
        # Get the user ID correctly for both Interaction and Context objects
        user_id = interaction.user.id if isinstance(interaction, discord.Interaction) else interaction.author.id
        user_balance = await self.get_wallet(user_id)
        
        embed = discord.Embed(
            title=f"{shop_type.capitalize()} Shop",
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
        
        view = ShopView(self, shop_type, items, user_balance, timeout=180)
        
        if isinstance(interaction, discord.Interaction):
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.send(embed=embed, view=view)

    @commands.command()
    async def buy(self, ctx, item_id: str = None, amount: int = 1):
        """Buy an item from the shop"""
        if not item_id:
            await ctx.send(f"Please specify an item ID! Use `{ctx.prefix}shop` to browse items.")
            return
        
        if amount <= 0:
            await ctx.send("Amount must be positive!")
            return
        
        # Determine item type by checking all collections
        item = None
        item_type = None
        for collection_type in self.supported_types:
            collection = await self.get_collection(collection_type)
            if collection is None:  # Skip if collection doesn't exist
                continue
            found_item = await collection.find_one({"_id": item_id})
            if found_item:
                item = found_item
                item_type = collection_type
                break
        
        if not item:
            await ctx.send("Item not found!")
            return
        
        total_price = item['price'] * amount
        user_balance = await self.get_wallet(ctx.author.id)
        
        if user_balance < total_price:
            await ctx.send(f"You don't have enough {self.currency}! You need {total_price}{self.currency} but only have {user_balance}{self.currency}.")
            return
        
        success = await self.process_purchase(ctx.author.id, item_id, amount, item_type)
        if success:
            embed = discord.Embed(
                title="Purchase Successful!",
                description=f"You bought {amount}x **{item['name']}** for {total_price}{self.currency}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("There was an error processing your purchase. Please try again.")

async def setup(bot):
    cog = Shop(bot)
    await bot.add_cog(Shop(bot))