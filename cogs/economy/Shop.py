import discord
from discord.ext import commands
from utils.db import async_db as db
from typing import Optional, Dict, List, Union
import os
import json
from discord.ui import Button, View, Select, Modal, TextInput

# Load shop data from JSON files
def load_shop_data():
    shop_data = {}
    shop_files = {
        'rod': 'data/shop/rods.json',
        'bait': 'data/shop/bait.json', 
        'upgrade': 'data/shop/upgrades.json',
        'potion': 'data/shop/potions.json',
        'item': 'data/shop/items.json'
    }
    
    for shop_type, file_path in shop_files.items():
        try:
            with open(file_path, 'r') as f:
                shop_data[shop_type] = json.load(f)
        except FileNotFoundError:
            shop_data[shop_type] = {}
    
    return shop_data

# Load shop data at module level
SHOP_DATA = load_shop_data()

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
            discord.SelectOption(label="Fishing Rods", value="rod", description="Upgrade your fishing gear", emoji="🎣"),
            discord.SelectOption(label="Baits", value="bait", description="Better bait for better catches", emoji="🪱"),
            discord.SelectOption(label="Items", value="item", description="Various useful items", emoji="📦"),
            discord.SelectOption(label="Upgrades", value="upgrade", description="Permanent account upgrades", emoji="⬆️"),
            discord.SelectOption(label="Potions", value="potion", description="Temporary boosts and effects", emoji="🧪"),
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
            rarity_emoji = {
                "common": "⚪",
                "uncommon": "🟢", 
                "rare": "🔵",
                "epic": "🟣",
                "legendary": "🟠",
                "mythical": "🔴"
            }.get(item.get('rarity', 'common'), "⚪")
            
            embed.add_field(
                name=f"{rarity_emoji} {item['name']} - {item['price']}{self.cog.currency}",
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
        self.currency = "<:bronkbuk:1377389238290747582>"  # Use the same currency as other cogs
        self.supported_types = ["rod", "bait", "upgrade", "potion", "item"]
        
        # Load shop data from JSON files
        self.shop_data = SHOP_DATA

    def get_shop_items(self, item_type: str) -> List[Dict]:
        """Get all items of a specific type, sorted by price (cheapest first)"""
        if item_type not in self.shop_data:
            return []
        
        items = []
        for item_id, item_data in self.shop_data[item_type].items():
            item_data['_id'] = item_id  # Add the ID to the item data
            item_data['type'] = item_type  # Add the type for consistency
            items.append(item_data)
        
        # Sort items by price in ascending order (cheapest first)
        items.sort(key=lambda x: x.get('price', 0))
        return items

    def get_item(self, item_id: str, item_type: str) -> Optional[Dict]:
        """Get an item from the JSON data"""
        if item_type not in self.shop_data:
            return None
        
        item_data = self.shop_data[item_type].get(item_id)
        if item_data:
            item_data['_id'] = item_id
            item_data['type'] = item_type
        return item_data

    # Database helper methods
    async def get_wallet(self, user_id: int) -> int:
        """Get user's wallet balance"""
        user_data = await db.db.users.find_one({"_id": str(user_id)})
        return user_data.get('wallet', 0) if user_data else 0

    async def update_wallet(self, user_id: int, amount: int) -> bool:
        """Update user's wallet balance"""
        result = await db.db.users.update_one(
            {"_id": str(user_id)},
            {"$inc": {"wallet": amount}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None

    async def add_item_to_inventory(self, user_id: int, item_id: str, item_type: str, amount: int = 1) -> bool:
        """Add an item to user's inventory"""
        if item_type in ["rod", "bait"]:
            # For fishing items, use the inventory structure
            inventory_field = f"inventory.{item_type}.{item_id}"
            result = await db.db.users.update_one(
                {"_id": str(user_id)},
                {"$inc": {inventory_field: amount}},
                upsert=True
            )
        elif item_type == "potion":
            # For potions, add to potions array
            potion_data = {
                "_id": item_id,
                "amount": amount,
                "expires_at": None  # Set when consumed
            }
            result = await db.db.users.update_one(
                {"_id": str(user_id)},
                {"$push": {"potions": potion_data}},
                upsert=True
            )
        else:
            # For other items, use general inventory
            inventory_field = f"inventory.{item_type}.{item_id}"
            result = await db.db.users.update_one(
                {"_id": str(user_id)},
                {"$inc": {inventory_field: amount}},
                upsert=True
            )
        
        return result.modified_count > 0 or result.upserted_id is not None

    async def process_purchase(self, user_id: int, item_id: str, amount: int, item_type: str) -> bool:
        """Process a purchase transaction"""
        item = self.get_item(item_id, item_type)
        if not item:
            return False
        
        total_price = item['price'] * amount
        user_balance = await self.get_wallet(user_id)
        
        if user_balance < total_price:
            return False
        
        # Deduct money
        wallet_updated = await self.update_wallet(user_id, -total_price)
        if not wallet_updated:
            return False
        
        # Add item to inventory
        inventory_updated = await self.add_item_to_inventory(user_id, item_id, item_type, amount)
        return wallet_updated and inventory_updated

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
        
        items = self.get_shop_items(shop_type)
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
            rarity_emoji = {
                "common": "⚪",
                "uncommon": "🟢", 
                "rare": "🔵",
                "epic": "🟣",
                "legendary": "🟠",
                "mythical": "🔴"
            }.get(item.get('rarity', 'common'), "⚪")
            
            embed.add_field(
                name=f"{rarity_emoji} {item['name']} - {item['price']}{self.currency}",
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
        """Buy an item from the shop with better error handling"""
        if not item_id:
            embed = discord.Embed(
                title="Purchase Error",
                description=f"Please specify an item ID! Use `{ctx.prefix}shop` to browse items.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        try:
            amount = int(amount)
            if amount <= 0:
                await ctx.send("Amount must be positive!")
                return
            
            # Determine item type by searching all shop types
            item = None
            item_type = None
            for collection_type in self.supported_types:
                found_item = self.get_item(item_id, collection_type)
                if found_item:
                    item = found_item
                    item_type = collection_type
                    break
            
            if not item:
                embed = discord.Embed(
                    title="Item Not Found",
                    description=f"Could not find item with ID `{item_id}`",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            
            total_price = item['price'] * amount
            user_balance = await self.get_wallet(ctx.author.id)
            
            if user_balance < total_price:
                embed = discord.Embed(
                    title="Insufficient Funds",
                    description=(
                        f"You need {total_price}{self.currency} but only have {user_balance}{self.currency}.\n"
                        f"Use `{ctx.prefix}daily` to get some free coins!"
                    ),
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            
            success = await self.process_purchase(ctx.author.id, item_id, amount, item_type)
            if success:
                rarity_emoji = {
                    "common": "⚪",
                    "uncommon": "🟢", 
                    "rare": "🔵",
                    "epic": "🟣",
                    "legendary": "🟠",
                    "mythical": "🔴"
                }.get(item.get('rarity', 'common'), "⚪")
                
                embed = discord.Embed(
                    title="Purchase Successful!",
                    description=f"You bought {amount}x {rarity_emoji} **{item['name']}** for {total_price}{self.currency}",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="Purchase Failed",
                    description="There was an error processing your purchase. Please try again.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                
        except ValueError:
            embed = discord.Embed(
                title="Invalid Amount",
                description="Please enter a valid number for the amount.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"Error in buy command: {e}")
            embed = discord.Embed(
                title="Unexpected Error",
                description="An unexpected error occurred. Please try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
async def setup(bot):
    await bot.add_cog(Shop(bot))
