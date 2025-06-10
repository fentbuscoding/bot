import discord
from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import async_db as db
import json
import datetime
import random
import asyncio
import aiohttp
import os
import traceback
from typing import Optional, List
from cogs.Help import HelpPaginator

logger = CogLogger('Admin')

class Admin(commands.Cog):
    """Admin-only commands for bot management"""
    def __init__(self, bot):
        self.bot = bot
        self.logger = logger
        self.currency = "<:bronkbuk:1377106993495412789>"
        self.db = db
        
        # Set up data file path
        self.data_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'shop.json')

        # Fishing configuration
        self.FISH_TYPES = {
            "normal": {
                "name": "Normal Fish",
                "rarity": 0.7,
                "value_range": (10, 100)
            },
            "rare": {
                "name": "Rare Fish", 
                "rarity": 0.2,
                "value_range": (100, 500)
            },
            "event": {
                "name": "Event Fish",
                "rarity": 0.08,
                "value_range": (500, 2000)
            },
            "mutated": {
                "name": "Mutated Fish",
                "rarity": 0.02,
                "value_range": (2000, 10000)
            }
        }

        # Default items for fishing shops
        self.DEFAULT_FISHING_ITEMS = {
            "bait_shop": {
                "beginner_bait": {
                    "name": "Beginner Bait",
                    "price": 0,  # Free for first 10
                    "amount": 10,
                    "description": "Basic bait for catching fish",
                    "catch_rates": {"normal": 1.0, "rare": 0.1}
                },
                "pro_bait": {
                    "name": "Pro Bait",
                    "price": 50,
                    "amount": 10,
                    "description": "Better chances for rare fish",
                    "catch_rates": {"normal": 1.2, "rare": 0.3, "event": 0.1}
                },
                "mutated_bait": {
                    "name": "Mutated Bait",
                    "price": 200,
                    "amount": 5,
                    "description": "Chance to catch mutated fish",
                    "catch_rates": {"normal": 1.5, "rare": 0.5, "event": 0.2, "mutated": 0.1}
                }
            },
            "rod_shop": {
                "beginner_rod": {
                    "name": "Beginner Rod",
                    "price": 0,  # Free for first one
                    "description": "Basic fishing rod",
                    "multiplier": 1.0
                },
                "pro_rod": {
                    "name": "Pro Rod",
                    "price": 5000,
                    "description": "50% better catch rates",
                    "multiplier": 1.5
                },
                "master_rod": {
                    "name": "Master Rod",
                    "price": 25000,
                    "description": "Double catch rates",
                    "multiplier": 2.0
                }
            }
        }

        self.load_shop_data()
        
        # Buff types for global buff system
        self.buff_types = {
            "economy": {
                "name": "Economy Boost",
                "description": "1.5x multiplier for all economy commands",
                "commands": ["work", "beg", "crime", "rob", "gamble"]
            },
            "fishing": {
                "name": "Fishing Boost", 
                "description": "1.5x catch rates and fish values",
                "commands": ["fish", "cast"]
            },
            "xp": {
                "name": "XP Boost",
                "description": "1.5x experience gain",
                "commands": ["all"]
            }
        }
        
        # Track last global buff to avoid repetition
        self.last_global_buff = None

    def load_shop_data(self) -> None:
        """Load shop data from file"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.shop_data = data.get("global", {
                    "items": {},
                    "potions": {},
                    "buffs": {},
                    "bait_shop": self.DEFAULT_FISHING_ITEMS["bait_shop"].copy(),
                    "rod_shop": self.DEFAULT_FISHING_ITEMS["rod_shop"].copy()
                })
                self.server_shops = data.get("servers", {})
        except FileNotFoundError:
            self.shop_data = {
                "items": {},
                "potions": {},
                "buffs": {},
                "bait_shop": self.DEFAULT_FISHING_ITEMS["bait_shop"].copy(),
                "rod_shop": self.DEFAULT_FISHING_ITEMS["rod_shop"].copy()
            }
            self.server_shops = {}
            self.save_shop_data()

    def save_shop_data(self) -> None:
        """Save shop data to file"""
        with open(self.data_file, 'w') as f:
            json.dump({
                "global": self.shop_data,
                "servers": self.server_shops
            }, f, indent=2)

    def get_server_shop(self, guild_id: int) -> dict:
        """Get server-specific shop data"""
        return self.server_shops.get(str(guild_id), {"items": {}, "potions": {}})

    @commands.group(name="shop_admin", aliases=["sa"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def shop_admin(self, ctx):
        """Shop management commands"""
        embed = discord.Embed(
            title="Shop Management",
            description=(
                "**Available Commands:**\n"
                "`.shop_admin add <shop> <item_data>` - Add item to shop\n"
                "`.shop_admin remove <shop> <item_id>` - Remove item\n"
                "`.shop_admin list <shop>` - List items\n"
                "`.shop_admin edit <shop> <item_id> <field> <value>` - Edit item\n\n"
                "**Available Shops:**\n"
                "🛍️ `item` - General items\n"
                "🧪 `potion` - Buff and boost potions\n"
                "⬆️ `upgrade` - Permanent upgrades\n"
                "🎣 `rod` - Fishing rods\n"
                "🪱 `bait` - Fishing bait"
            ),
            color=0x2b2d31
        )
        await ctx.reply(embed=embed)

    @shop_admin.command(name="add")
    @commands.has_permissions(administrator=True)
    async def shop_add(self, ctx, shop_type: str, *, item_data: str):
        """Add an item to a shop. Format varies by shop type.
        
        Examples:
        Items: .shop_admin add item {"id": "vip", "name": "VIP Role", "price": 10000, "description": "Get VIP status"}
        Potions: .shop_admin add potion {"id": "luck_potion", "name": "Lucky Potion", "price": 1000, "type": "luck", "multiplier": 2.0, "duration": 60}
        Upgrades: .shop_admin add upgrade {"id": "bank_boost", "name": "Bank Boost", "price": 5000, "type": "bank", "amount": 10000}
        Rods: .shop_admin add rod {"id": "pro_rod", "name": "Pro Rod", "price": 5000, "description": "Professional fishing rod", "multiplier": 1.5}
        Bait: .shop_admin add bait {"id": "pro_bait", "name": "Pro Bait", "price": 50, "amount": 10, "description": "Better bait", "catch_rates": {"normal": 1.2, "rare": 0.3}}"""
        
        # Map old shop types to new JSON file types
        shop_type_mapping = {
            "items": "item",
            "potions": "potion", 
            "upgrades": "upgrade",
            "fishing": "rod",  # Legacy support
            "rods": "rod",
            "bait": "bait"
        }
        
        # Convert legacy shop type names
        if shop_type in shop_type_mapping:
            shop_type = shop_type_mapping[shop_type]
            
        # Valid shop types for JSON files
        valid_shop_types = ["item", "potion", "upgrade", "rod", "bait"]
        
        if shop_type not in valid_shop_types:
            return await ctx.reply(f"Invalid shop type! Use one of: {', '.join(valid_shop_types)}")
            
        try:
            # Parse item data
            item = json.loads(item_data)
            
            # Validate required fields
            required_fields = {
                "item": ["id", "name", "price", "description"],
                "potion": ["id", "name", "price", "type", "multiplier", "duration"],
                "upgrade": ["id", "name", "price", "type"],
                "rod": ["id", "name", "price", "description", "multiplier"],
                "bait": ["id", "name", "price", "amount", "description", "catch_rates"]
            }
            
            if not all(field in item for field in required_fields[shop_type]):
                return await ctx.reply(f"Missing required fields: {required_fields[shop_type]}")
                
            # Load existing shop data
            shop_file_path = f"data/shop/{shop_type}s.json"
            try:
                with open(shop_file_path, 'r') as f:
                    shop_data = json.load(f)
            except FileNotFoundError:
                shop_data = {}
            
            # Check if item already exists
            if item["id"] in shop_data:
                return await ctx.reply(f"❌ Item with ID `{item['id']}` already exists!")
            
            # Add the item
            shop_data[item["id"]] = item
            
            # Save back to file
            os.makedirs(os.path.dirname(shop_file_path), exist_ok=True)
            with open(shop_file_path, 'w') as f:
                json.dump(shop_data, f, indent=2)
                
            # Reload shop data in Shop cog if it exists
            shop_cog = self.bot.get_cog("Shop")
            if shop_cog:
                from cogs.economy.Shop import load_shop_data
                shop_cog.shop_data = load_shop_data()
                
            embed = discord.Embed(
                description=f"✨ Added **{item['name']}** to {shop_type} shop!",
                color=0x2b2d31
            )
            await ctx.reply(embed=embed)
                
        except json.JSONDecodeError:
            await ctx.reply("❌ Invalid JSON format! Make sure to use proper JSON syntax.")
        except Exception as e:
            await ctx.reply(f"❌ Error: {str(e)}")
            
    @shop_admin.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def shop_remove(self, ctx, shop_type: str, item_id: str):
        """Remove an item from a shop"""
        # Map old shop types to new JSON file types
        shop_type_mapping = {
            "items": "item",
            "potions": "potion", 
            "upgrades": "upgrade",
            "fishing": "rod",  # Legacy support
            "rods": "rod",
            "bait": "bait"
        }
        
        # Convert legacy shop type names
        if shop_type in shop_type_mapping:
            shop_type = shop_type_mapping[shop_type]
            
        # Valid shop types for JSON files
        valid_shop_types = ["item", "potion", "upgrade", "rod", "bait"]
        
        if shop_type not in valid_shop_types:
            return await ctx.reply(f"Invalid shop type! Use one of: {', '.join(valid_shop_types)}")
            
        try:
            # Load existing shop data
            shop_file_path = f"data/shop/{shop_type}s.json"
            try:
                with open(shop_file_path, 'r') as f:
                    shop_data = json.load(f)
            except FileNotFoundError:
                return await ctx.reply(f"❌ No {shop_type} shop file found!")
            
            # Check if item exists
            if item_id not in shop_data:
                return await ctx.reply(f"❌ Item `{item_id}` not found in {shop_type} shop!")
            
            # Remove the item
            item_name = shop_data[item_id].get("name", item_id)
            del shop_data[item_id]
            
            # Save back to file
            with open(shop_file_path, 'w') as f:
                json.dump(shop_data, f, indent=2)
                
            # Reload shop data in Shop cog if it exists
            shop_cog = self.bot.get_cog("Shop")
            if shop_cog:
                from cogs.economy.Shop import load_shop_data
                shop_cog.shop_data = load_shop_data()
                
            embed = discord.Embed(
                description=f"✨ Removed **{item_name}** from {shop_type} shop!",
                color=0x2b2d31
            )
            await ctx.reply(embed=embed)
            
        except Exception as e:
            await ctx.reply(f"❌ Error: {str(e)}")
            
    @shop_admin.command(name="list")
    @commands.has_permissions(administrator=True)
    async def shop_list(self, ctx, shop_type: str):
        """List all items in a shop"""
        # Map old shop types to new JSON file types
        shop_type_mapping = {
            "items": "item",
            "potions": "potion", 
            "upgrades": "upgrade",
            "fishing": "rod",  # Legacy support
            "rods": "rod",
            "bait": "bait"
        }
        
        # Convert legacy shop type names
        if shop_type in shop_type_mapping:
            shop_type = shop_type_mapping[shop_type]
            
        # Valid shop types for JSON files
        valid_shop_types = ["item", "potion", "upgrade", "rod", "bait"]
        
        if shop_type not in valid_shop_types:
            return await ctx.reply(f"Invalid shop type! Use one of: {', '.join(valid_shop_types)}")
            
        try:
            # Load shop data
            shop_file_path = f"data/shop/{shop_type}s.json"
            try:
                with open(shop_file_path, 'r') as f:
                    shop_data = json.load(f)
            except FileNotFoundError:
                return await ctx.reply(f"❌ No {shop_type} shop file found!")
            
            if not shop_data:
                return await ctx.reply(f"No items found in {shop_type} shop!")
                
            # Convert dict to list format for pagination
            items = []
            for item_id, item_data in shop_data.items():
                item_data['id'] = item_id  # Ensure ID is present
                items.append(item_data)
                
            pages = []
            chunks = [items[i:i+5] for i in range(0, len(items), 5)]
            
            for chunk in chunks:
                embed = discord.Embed(
                    title=f"🛍️ {shop_type.title()} Shop",
                    color=0x2b2d31
                )
                
                for item in chunk:
                    name = f"{item['name']} ({item['price']} {self.currency})"
                    value = []
                    
                    value.append(f"ID: `{item['id']}`")
                    if "description" in item:
                        value.append(item["description"])
                    if "type" in item:
                        value.append(f"Type: {item['type']}")
                    if "multiplier" in item:
                        value.append(f"Multiplier: {item['multiplier']}x")
                    if "duration" in item:
                        value.append(f"Duration: {item['duration']}min")
                    if "amount" in item:
                        value.append(f"Amount: {item['amount']}")
                        
                    embed.add_field(
                        name=name,
                        value="\n".join(value),
                        inline=False
                    )
                    
                pages.append(embed)
                
            if len(pages) > 1:
                view = HelpPaginator(pages, ctx.author)
                view.update_buttons()
                message = await ctx.reply(embed=pages[0], view=view)
                view.message = message
            else:
                await ctx.reply(embed=pages[0])
                
        except Exception as e:
            await ctx.reply(f"❌ Error: {str(e)}")
            
    @shop_admin.command(name="edit")
    @commands.has_permissions(administrator=True)
    async def shop_edit(self, ctx, shop_type: str, item_id: str, field: str, *, value: str):
        """Edit a field of an existing shop item
        
        Example: .shop_admin edit potion luck_potion price 2000"""
        # Map old shop types to new JSON file types
        shop_type_mapping = {
            "items": "item",
            "potions": "potion", 
            "upgrades": "upgrade",
            "fishing": "rod",  # Legacy support
            "rods": "rod",
            "bait": "bait"
        }
        
        # Convert legacy shop type names
        if shop_type in shop_type_mapping:
            shop_type = shop_type_mapping[shop_type]
            
        # Valid shop types for JSON files
        valid_shop_types = ["item", "potion", "upgrade", "rod", "bait"]
        
        if shop_type not in valid_shop_types:
            return await ctx.reply(f"Invalid shop type! Use one of: {', '.join(valid_shop_types)}")
            
        try:
            # Load existing shop data
            shop_file_path = f"data/shop/{shop_type}s.json"
            try:
                with open(shop_file_path, 'r') as f:
                    shop_data = json.load(f)
            except FileNotFoundError:
                return await ctx.reply(f"❌ No {shop_type} shop file found!")
            
            # Check if item exists
            if item_id not in shop_data:
                return await ctx.reply(f"❌ Item `{item_id}` not found in {shop_type} shop!")
            
            # Convert value to appropriate type
            if field in ["price", "duration", "amount"]:
                value = int(value)
            elif field in ["multiplier"]:
                value = float(value)
            elif value.lower() == "null":
                value = None
            elif field == "catch_rates":
                # Handle catch_rates as JSON
                value = json.loads(value)
                
            # Update the item
            shop_data[item_id][field] = value
            
            # Save back to file
            with open(shop_file_path, 'w') as f:
                json.dump(shop_data, f, indent=2)
                
            # Reload shop data in Shop cog if it exists
            shop_cog = self.bot.get_cog("Shop")
            if shop_cog:
                from cogs.economy.Shop import load_shop_data
                shop_cog.shop_data = load_shop_data()
                
            embed = discord.Embed(
                description=f"✨ Updated `{field}` to `{value}` for item `{item_id}`!",
                color=0x2b2d31
            )
            await ctx.reply(embed=embed)
                
        except ValueError:
            await ctx.reply("❌ Invalid value type for this field!")
        except json.JSONDecodeError:
            await ctx.reply("❌ Invalid JSON format for catch_rates field!")
        except Exception as e:
            await ctx.reply(f"❌ Error: {str(e)}")

    async def rotate_global_buff(self):
        """Rotate global buffs every 15 minutes"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                # Select new buff that's different from last one
                available_buffs = list(self.buff_types.keys())
                if self.last_global_buff:
                    available_buffs.remove(self.last_global_buff)
                
                new_buff = random.choice(available_buffs)
                self.last_global_buff = new_buff
                
                # Apply global buff
                expiry = datetime.datetime.now() + datetime.timedelta(minutes=15)
                await db.add_global_buff({
                    "type": new_buff,
                    "multiplier": 1.5,
                    "expires_at": expiry.timestamp()
                })
                
                # Announce in log channel
                channel = self.bot.get_channel(1314685928614264852)
                if channel:
                    buff_info = self.buff_types[new_buff]
                    embed = discord.Embed(
                        description=(
                            f"🌟 **new global buff active**\n"
                            f"**{buff_info['name']}**\n"
                            f"{buff_info['description']}\n"
                            f"Duration: 15 minutes\n"
                            f"Affects: {', '.join(buff_info['commands'])}"
                        ),
                        color=0x2b2d31
                    )
                    await channel.send(embed=embed)
                
                await asyncio.sleep(900)
                
            except Exception as e:
                self.logger.error(f"Error in global buff rotation: {e}")
                await asyncio.sleep(60)

    @commands.command(name="trigger")
    @commands.cooldown(1, 900, commands.BucketType.user)
    async def trigger_buff(self, ctx, buff_type: str = None):
        """Trigger the next global buff (costs 300,000, requires 5M net worth)"""
        is_owner = await self.bot.is_owner(ctx.author)
        
        if not is_owner:
            # Check requirements for non-owners
            wallet = await db.get_wallet_balance(ctx.author.id)
            bank = await db.get_bank_balance(ctx.author.id)
            net_worth = wallet + bank
            
            if net_worth < 5_000_000:
                embed = discord.Embed(description="❌ You need a net worth of 5,000,000 to use this command!", color=0x2b2d31)
                return await ctx.reply(embed=embed)
                
            if wallet < 300_000:
                embed = discord.Embed(description="❌ You need 300,000 in your wallet!", color=0x2b2d31)
                return await ctx.reply(embed=embed)

        if not buff_type:
            embed = discord.Embed(
                description=(
                    "**Available Global Buffs**\n" +
                    ("Cost: Free (Bot Owner)\n" if is_owner else "Cost: 300,000 💰\n") +
                    ("" if is_owner else "Requirement: 5M net worth\n") +
                    "\n**Usage:** `.trigger <buff>`\n\n" +
                    "**Available Buffs:**\n" +
                    "\n".join(f"• **{k}** - {v['description']}\n  *Affects: {', '.join(v['commands'])}*" 
                            for k,v in self.buff_types.items())
                ),
                color=0x2b2d31
            )
            return await ctx.reply(embed=embed)

        if buff_type not in self.buff_types:
            embed = discord.Embed(description="❌ Invalid buff type!", color=0x2b2d31)
            return await ctx.reply(embed=embed)

        if not is_owner:
            await db.update_wallet(ctx.author.id, -300_000)
        
        expiry = datetime.datetime.now() + datetime.timedelta(minutes=15)
        await db.add_global_buff({
            "type": buff_type,
            "multiplier": 1.5,
            "expires_at": expiry.timestamp(),
            "triggered_by": ctx.author.id
        })

        buff_info = self.buff_types[buff_type]
        embed = discord.Embed(
            description=(
                f"✨ **Global Buff Triggered**\n"
                f"**{buff_info['name']}** is now active for 15 minutes!\n"
                f"{buff_info['description']}\n"
                f"Affects: {', '.join(buff_info['commands'])}\n\n"
                f"Triggered by: {ctx.author.mention}"
            ),
            color=0x2b2d31
        )
        await ctx.reply(embed=embed)

    @commands.group(name="server", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def server(self, ctx):
        """Server shop management commands"""
        embed = discord.Embed(
            title="Server Shop Management",
            description=(
                "**Available Commands:**\n"
                "`.server list` - List items in server shop\n"
                "`.server add_potion <name> <price> <type> <multiplier> <duration> [description]` - Add potion to server shop\n\n"
                "**Example:**\n"
                "`.server add_potion \"Lucky Boost\" 1000 economy 1.5 60 \"Boosts economy commands\"`"
            ),
            color=0x2b2d31
        )
        await ctx.reply(embed=embed)

    @server.command(name="list")
    @commands.has_permissions(administrator=True)
    async def server_list_cmd(self, ctx):
        """List items in server shop"""
        await self.server_list(ctx)

    @server.command(name="add_potion")
    @commands.has_permissions(administrator=True)
    async def server_add_potion_cmd(self, ctx, name: str, price: int, type: str, multiplier: float, duration: int, description: str = None):
        """Add a potion to the server shop"""
        await self.server_add_potion(ctx, name, price, type, multiplier, duration, description)

    @commands.command(name="server_list")
    @commands.has_permissions(administrator=True)
    async def server_list(self, ctx):
        """List items in server shop"""
        shop_data = self.get_server_shop(ctx.guild.id)
        
        if not shop_data["items"] and not shop_data["potions"]:
            return await ctx.reply("This server's shop is empty!")

        embed = discord.Embed(title=f"{ctx.guild.name}'s Shop", color=0x2b2d31)
        
        # List items
        if shop_data["items"]:
            items_text = []
            for item_id, item in shop_data["items"].items():
                items_text.append(
                    f"**{item['name']}** - {item['price']} 💰\n"
                    f"{item['description']}"
                )
            if items_text:
                embed.add_field(
                    name="📦 Items",
                    value="\n\n".join(items_text),
                    inline=False
                )
        
        # List potions
        if shop_data["potions"]:
            potions_text = []
            for potion_id, potion in shop_data["potions"].items():
                potions_text.append(
                    f"**{potion['name']}** - {potion['price']} 💰\n"
                    f"{potion['multiplier']}x {potion['type']} buff for {potion['duration']}min"
                )
            if potions_text:
                embed.add_field(
                    name="🧪 Potions",
                    value="\n\n".join(potions_text),
                    inline=False
                )

        await ctx.reply(embed=embed)

    @commands.command(name="server_add_potion")
    @commands.has_permissions(administrator=True)
    async def server_add_potion(self, ctx, name: str, price: int, type: str, multiplier: float, duration: int, description: str = None):
        """Add a potion to the server shop"""
        # Validate inputs
        if not all([name, price, type, multiplier, duration]):
            embed = discord.Embed(description="❌ Missing required arguments", color=0x2b2d31)
            return await ctx.reply(embed=embed)

        if type not in self.buff_types:
            embed = discord.Embed(description="❌ Invalid buff type", color=0x2b2d31)
            return await ctx.reply(embed=embed)

        if price < 0:
            embed = discord.Embed(description="❌ Price cannot be negative", color=0x2b2d31)
            return await ctx.reply(embed=embed)

        if multiplier <= 0:
            embed = discord.Embed(description="❌ Multiplier must be positive", color=0x2b2d31)
            return await ctx.reply(embed=embed)

        if duration <= 0:
            embed = discord.Embed(description="❌ Duration must be positive", color=0x2b2d31)
            return await ctx.reply(embed=embed)

        # Add potion to server shop
        guild_id = str(ctx.guild.id)
        if guild_id not in self.server_shops:
            self.server_shops[guild_id] = {"items": {}, "potions": {}}

        potion_id = name.lower().replace(" ", "_")
        self.server_shops[guild_id]["potions"][potion_id] = {
            "name": name,
            "price": price,
            "type": type,
            "multiplier": multiplier,
            "duration": duration,
            "description": description or self.buff_types[type]["description"]
        }

        self.save_shop_data()
        
        embed = discord.Embed(
            description=f"✨ Added potion **{name}** to server shop\n"
                      f"Type: {type}\n"
                      f"Effect: {multiplier}x for {duration}min\n"
                      f"Price: {price} 💰",
            color=0x2b2d31
        )
        await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        """Cog loaded - print status"""
        self.logger.info(f"{self.__class__.__name__} loaded")

    @commands.command()
    @commands.is_owner()
    async def clearcommands(self, ctx):
        """Clear all slash commands"""
        try:
            # Clear global commands
            self.bot.tree.clear_commands(guild=None)
            await ctx.bot.tree.sync()
            
            # Clear guild-specific commands
            cleared_guilds = 0
            for guild in self.bot.guilds:
                try:
                    self.bot.tree.clear_commands(guild=guild)
                    await ctx.bot.tree.sync(guild=guild)
                    cleared_guilds += 1
                except discord.Forbidden:
                    print(f"Missing permissions in {guild.name} ({guild.id})")
                    continue
                except discord.HTTPException as e:
                    print(f"Error in {guild.name}: {e}")
                    continue
            
            await ctx.send(f"✅ Cleared global commands and {cleared_guilds}/{len(ctx.bot.guilds)} guild commands!")
        
        except Exception as e:
            await ctx.send(f"❌ Error: {type(e).__name__}: {e}")
            raise e

    @commands.command()
    @commands.is_owner()
    async def reset_economy(self, ctx, *, confirmation: Optional[str] = None):
        """Reset everyone's balance, inventory, and economic data (Bot Owner Only)
        Usage: .reset_economy YES I WANT TO RESET EVERYTHING"""
        
        if confirmation != "YES I WANT TO RESET EVERYTHING":
            embed = discord.Embed(
                title="⚠️ Economy Reset",
                description=(
                    "**WARNING:** This will delete ALL economic data including:\n"
                    "- User balances (wallet & bank)\n"
                    "- Inventories\n"
                    "- Fish collections\n"
                    "- Active potions\n"
                    "- Shop data\n\n"
                    "To confirm, use the command:\n"
                    "`.reset_economy YES I WANT TO RESET EVERYTHING`"
                ),
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
            
        try:
            # Delete all user data (balances, inventory, fish collections)
            await self.db.db.users.delete_many({})
            
            # Delete all active potions
            await self.db.db.active_potions.delete_many({})
            
            # Reset shop data to defaults by dropping and recreating collections
            shop_collections = [
                "shop_items",
                "shop_potions",
                "shop_upgrades",
                "shop_fishing",
                "shop_bait",
                "shop_rod"
            ]
            
            for collection in shop_collections:
                await self.db.db[collection].delete_many({})
            
            # Reinitialize default shop items
            await self.db.init_collections()
            
            # Reset local shop data
            self.shop_data = {
                "items": {},
                "potions": {},
                "buffs": {},
                "bait_shop": self.DEFAULT_FISHING_ITEMS["bait_shop"].copy(),
                "rod_shop": self.DEFAULT_FISHING_ITEMS["rod_shop"].copy()
            }
            self.server_shops = {}
            self.save_shop_data()
            
            await ctx.reply("✅ Successfully reset all economic data!")
            
        except Exception as e:
            self.logger.error(f"Failed to reset economy: {e}")
            await ctx.reply("❌ An error occurred while resetting the economy")

    @commands.command()
    @commands.is_owner()
    async def reset(self, ctx, user: discord.Member, new_balance: int = 0):
        """Reset a user's economic data and set their balance to a specified amount
        Usage: .reset @user [new_balance]"""
        
        try:
            # Reset user data completely
            result = await self.db.db.users.delete_one({"_id": str(user.id)})
            
            # Set new balance if specified
            if new_balance > 0:
                await self.db.update_wallet(user.id, new_balance)
            
            # Remove active potions
            await self.db.db.active_potions.delete_many({"user_id": str(user.id)})
            
            embed = discord.Embed(
                title="✅ User Reset Complete",
                description=(
                    f"**User:** {user.mention}\n"
                    f"**Data Reset:** {'✅' if result.deleted_count > 0 else '⚠️ No data found'}\n"
                    f"**New Balance:** {new_balance:,} {self.currency}\n\n"
                    "**Reset Items:**\n"
                    "• Wallet & Bank Balance\n"
                    "• All Inventory Items\n"
                    "• Fishing Rods & Bait\n"
                    "• Fish Collection\n"
                    "• Active Potions\n"
                    "• Upgrades & Multipliers"
                ),
                color=discord.Color.green()
            )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to reset user {user.id}: {e}")
            await ctx.reply(f"❌ Error resetting user: {e}")

    @commands.command(name="rnb", aliases=["rodandbait"], hidden=True)
    @commands.is_owner()
    async def give_all_rods_and_bait(self, ctx, user: discord.Member = None, bait_amount: int = 10, rod_amount: int = 1):
        """Give a user every rod and every bait for testing purposes
        Usage: .rnb @user [bait_amount] [rod_amount]
        Defaults: bait_amount=10, rod_amount=1"""
        
        target_user = user or ctx.author
        
        try:
            # Load all rods from JSON
            import json
            import os
            
            total_rods_given = 0
            total_bait_given = 0
            failed_items = []
            
            # First, ensure the user has proper inventory structure
            user_doc = await db.db.users.find_one({"_id": str(target_user.id)})
            
            # If user doesn't exist or has broken inventory, fix it first
            if not user_doc or not isinstance(user_doc.get("inventory"), dict):
                await db.db.users.update_one(
                    {"_id": str(target_user.id)},
                    {
                        "$set": {
                            "inventory": {
                                "rod": {},
                                "bait": {},
                                "potions": {},
                                "upgrades": {}
                            }
                        },
                        "$setOnInsert": {"wallet": 0}
                    },
                    upsert=True
                )
            elif isinstance(user_doc.get("inventory"), list):
                # Convert old list format to nested dict
                new_inventory = {"rod": {}, "bait": {}, "potions": {}, "upgrades": {}}
                
                # Migrate existing items if any
                for item in user_doc["inventory"]:
                    if isinstance(item, dict) and "type" in item:
                        item_type = item["type"]
                        item_id = item.get("id", item.get("_id", "unknown"))
                        quantity = item.get("quantity", item.get("amount", 1))
                        
                        if item_type in new_inventory:
                            new_inventory[item_type][item_id] = quantity
                
                await db.db.users.update_one(
                    {"_id": str(target_user.id)},
                    {"$set": {"inventory": new_inventory}}
                )
            else:
                # Ensure all required sections exist
                inventory = user_doc.get("inventory", {})
                updates = {}
                
                for section in ["rod", "bait", "potions", "upgrades"]:
                    if section not in inventory:
                        updates[f"inventory.{section}"] = {}
                
                if updates:
                    await db.db.users.update_one(
                        {"_id": str(target_user.id)},
                        {"$set": updates}
                    )
            
            # Give all rods
            rods_file = "data/shop/rods.json"
            if os.path.exists(rods_file):
                with open(rods_file, 'r') as f:
                    rods_data = json.load(f)
                
                for rod_id in rods_data.keys():
                    try:
                        # Use $set instead of $inc to avoid path conflicts
                        # First check current amount, then set the new amount
                        user_doc = await db.db.users.find_one({"_id": str(target_user.id)})
                        current_amount = user_doc.get("inventory", {}).get("rod", {}).get(rod_id, 0)
                        new_amount = current_amount + rod_amount
                        
                        result = await db.db.users.update_one(
                            {"_id": str(target_user.id)},
                            {"$set": {f"inventory.rod.{rod_id}": new_amount}}
                        )
                        if result.modified_count > 0:
                            total_rods_given += 1
                        else:
                            failed_items.append(f"rod: {rod_id}")
                    except Exception as e:
                        failed_items.append(f"rod: {rod_id} (error: {str(e)[:30]})")
            
            # Give all bait
            bait_file = "data/shop/bait.json"
            if os.path.exists(bait_file):
                with open(bait_file, 'r') as f:
                    bait_data = json.load(f)
                
                for bait_id in bait_data.keys():
                    try:
                        # Use $set instead of $inc to avoid path conflicts
                        # First check current amount, then set the new amount
                        user_doc = await db.db.users.find_one({"_id": str(target_user.id)})
                        current_amount = user_doc.get("inventory", {}).get("bait", {}).get(bait_id, 0)
                        new_amount = current_amount + bait_amount
                        
                        result = await db.db.users.update_one(
                            {"_id": str(target_user.id)},
                            {"$set": {f"inventory.bait.{bait_id}": new_amount}}
                        )
                        if result.modified_count > 0:
                            total_bait_given += 1
                        else:
                            failed_items.append(f"bait: {bait_id}")
                    except Exception as e:
                        failed_items.append(f"bait: {bait_id} (error: {str(e)[:30]})")
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Rod & Bait Distribution Complete",
                description=(
                    f"**Target User:** {target_user.mention}\n"
                    f"**Rods Given:** {total_rods_given} types (x{rod_amount} each)\n"
                    f"**Bait Given:** {total_bait_given} types (x{bait_amount} each)\n"
                ),
                color=discord.Color.green()
            )
            
            if failed_items:
                embed.add_field(
                    name="⚠️ Failed Items",
                    value="\n".join(failed_items[:10]) + ("..." if len(failed_items) > 10 else ""),
                    inline=False
                )
            
            embed.add_field(
                name="💡 Next Steps",
                value=(
                    "The user can now:\n"
                    "• Use `.rod` to select a fishing rod\n"
                    "• Use `.bait` to select bait\n"
                    "• Use `.fish` to start fishing\n"
                    "• Use `.fishinv` to view their inventory"
                ),
                inline=False
            )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to give rods and bait to user {target_user.id}: {e}")
            await ctx.reply(f"❌ Error giving rods and bait: {e}")

    @commands.command(name="repair")
    @commands.has_permissions(administrator=True)
    async def repair_user_data(self, ctx, user: discord.Member = None):
        """Repair broken user data in the database
        Usage: .repair [@user]
        If no user specified, repairs the command author's data"""
        
        target_user = user or ctx.author
        
        try:
            # Get current user data
            user_doc = await self.db.db.users.find_one({"_id": str(target_user.id)})
            
            if not user_doc:
                embed = discord.Embed(
                    title="🔧 User Data Repair",
                    description=f"No data found for {target_user.mention}. Creating new user profile...",
                    color=discord.Color.blue()
                )
                
                # Create new user document with proper structure
                await self.db.db.users.update_one(
                    {"_id": str(target_user.id)},
                    {
                        "$setOnInsert": {
                            "wallet": 0,
                            "bank": 0,
                            "inventory": {
                                "rod": {},
                                "bait": {},
                                "potions": {},
                                "upgrades": {},
                                "items": {}
                            },
                            "fishing": {
                                "selected_rod": None,
                                "selected_bait": None,
                                "fish_caught": {}
                            },
                            "active_effects": {},
                            "last_daily": None,
                            "last_work": None
                        }
                    },
                    upsert=True
                )
                
                embed.add_field(
                    name="✅ Created New Profile",
                    value="User profile created with proper structure",
                    inline=False
                )
                
                return await ctx.reply(embed=embed)
            
            # Track what repairs were made
            repairs_made = []
            updates = {}
            
            # Fix wallet/bank if they're missing or invalid
            if "wallet" not in user_doc or not isinstance(user_doc.get("wallet"), (int, float)):
                updates["wallet"] = 0
                repairs_made.append("🔧 Reset wallet to 0")
            
            if "bank" not in user_doc or not isinstance(user_doc.get("bank"), (int, float)):
                updates["bank"] = 0
                repairs_made.append("🔧 Reset bank to 0")
            
            # Fix inventory structure
            inventory = user_doc.get("inventory", [])
            
            # If inventory is a list (old format), convert to proper nested structure
            if isinstance(inventory, list):
                new_inventory = {
                    "rod": {},
                    "bait": {},
                    "potions": {},
                    "upgrades": {}
                }
                
                # Migrate items from old list format
                for item in inventory:
                    if isinstance(item, dict) and "type" in item:
                        item_type = item["type"]
                        item_id = item.get("id", item.get("_id", "unknown"))
                        quantity = item.get("quantity", item.get("amount", 1))
                        
                        if item_type in ["potion"]:
                            new_inventory["potions"][item_id] = quantity
                        elif item_type in ["upgrade"]:
                            new_inventory["upgrades"][item_id] = quantity
                        elif item_type in ["rod"]:
                            new_inventory["rod"][item_id] = quantity
                        elif item_type in ["bait"]:
                            new_inventory["bait"][item_id] = quantity
                
                updates["inventory"] = new_inventory
                repairs_made.append("🔄 Converted inventory from list to nested structure")
            
            # If inventory is dict but missing required sections
            elif isinstance(inventory, dict):
                required_sections = ["rod", "bait", "potions", "upgrades"]
                missing_sections = []
                
                for section in required_sections:
                    if section not in inventory:
                        if "inventory" not in updates:
                            updates["inventory"] = inventory.copy()
                        updates["inventory"][section] = {}
                        missing_sections.append(section)
                
                if missing_sections:
                    repairs_made.append(f"➕ Added missing inventory sections: {', '.join(missing_sections)}")
            
            # Fix fishing data structure
            if "fishing" not in user_doc or not isinstance(user_doc.get("fishing"), dict):
                updates["fishing"] = {
                    "selected_rod": None,
                    "selected_bait": None,
                    "fish_caught": {}
                }
                repairs_made.append("🎣 Fixed fishing data structure")
            else:
                fishing = user_doc["fishing"]
                fishing_updates = {}
                
                if "selected_rod" not in fishing:
                    fishing_updates["selected_rod"] = None
                if "selected_bait" not in fishing:
                    fishing_updates["selected_bait"] = None
                if "fish_caught" not in fishing or not isinstance(fishing.get("fish_caught"), dict):
                    fishing_updates["fish_caught"] = {}
                
                if fishing_updates:
                    updates["fishing"] = {**fishing, **fishing_updates}
                    repairs_made.append("🔧 Fixed missing fishing data fields")
            
            # Fix active effects structure
            if "active_effects" not in user_doc or not isinstance(user_doc.get("active_effects"), dict):
                updates["active_effects"] = {}
                repairs_made.append("✨ Fixed active effects structure")
            
            # Ensure numeric fields are properly typed
            numeric_fields = ["wallet", "bank"]
            for field in numeric_fields:
                if field in user_doc:
                    value = user_doc[field]
                    if not isinstance(value, (int, float)):
                        try:
                            updates[field] = int(float(str(value)))
                            repairs_made.append(f"🔢 Fixed {field} data type")
                        except (ValueError, TypeError):
                            updates[field] = 0
                            repairs_made.append(f"🔢 Reset corrupted {field} to 0")
            
            # Clean up any invalid nested inventory values
            if "inventory" in updates or isinstance(user_doc.get("inventory"), dict):
                current_inv = updates.get("inventory", user_doc.get("inventory", {}))
                cleaned_inv = {}
                
                for section, items in current_inv.items():
                    if isinstance(items, dict):
                        cleaned_section = {}
                        for item_id, quantity in items.items():
                            # Ensure quantities are positive integers
                            try:
                                clean_qty = max(0, int(float(str(quantity))))
                                if clean_qty > 0:  # Only keep items with positive quantities
                                    cleaned_section[item_id] = clean_qty
                            except (ValueError, TypeError):
                                # Skip invalid quantities
                                continue
                        cleaned_inv[section] = cleaned_section
                    else:
                        cleaned_inv[section] = {}
                
                if cleaned_inv != current_inv:
                    updates["inventory"] = cleaned_inv
                    repairs_made.append("🧹 Cleaned invalid inventory quantities")
            
            # Apply all updates if any repairs were needed
            if updates:
                await self.db.db.users.update_one(
                    {"_id": str(target_user.id)},
                    {"$set": updates}
                )
            
            # Create result embed
            embed = discord.Embed(
                title="🔧 User Data Repair Complete",
                description=f"**User:** {target_user.mention}",
                color=discord.Color.green() if repairs_made else discord.Color.blue()
            )
            
            if repairs_made:
                embed.add_field(
                    name="✅ Repairs Made",
                    value="\n".join(repairs_made),
                    inline=False
                )
                embed.add_field(
                    name="💡 What was fixed",
                    value=(
                        "• Inventory structure (list → nested dict)\n"
                        "• Missing wallet/bank fields\n"
                        "• Fishing data structure\n"
                        "• Active effects structure\n"
                        "• Invalid data types\n"
                        "• Negative/invalid quantities"
                    ),
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ No Issues Found",
                    value="User data structure is already correct!",
                    inline=False
                )
            
            # Get final data summary
            final_doc = await self.db.db.users.find_one({"_id": str(target_user.id)})
            if final_doc:
                wallet = final_doc.get("wallet", 0)
                bank = final_doc.get("bank", 0)
                inventory = final_doc.get("inventory", {})
                
                # Count inventory items
                total_items = 0
                for section in inventory.values():
                    if isinstance(section, dict):
                        total_items += sum(section.values())
                
                embed.add_field(
                    name="📊 Current Status",
                    value=(
                        f"💰 Wallet: {wallet:,}\n"
                        f"🏦 Bank: {bank:,}\n"
                        f"📦 Total Items: {total_items}\n"
                        f"🎣 Rods: {len(inventory.get('rod', {}))}\n"
                        f"🪱 Bait Types: {len(inventory.get('bait', {}))}\n"
                        f"🧪 Potions: {len(inventory.get('potions', {}))}\n"
                        f"⬆️ Upgrades: {len(inventory.get('upgrades', {}))}"
                    ),
                    inline=False
                )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to repair user data for {target_user.id}: {e}")
            embed = discord.Embed(
                title="❌ Repair Failed",
                description=f"An error occurred while repairing data for {target_user.mention}:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed)

    @commands.command(name="repair_all")
    @commands.is_owner()
    async def repair_all_users(self, ctx, limit: int = 50):
        """Repair all users with broken data (Bot Owner Only)
        Usage: .repair_all [limit]
        Default limit: 50 users"""
        
        if limit <= 0 or limit > 500:
            return await ctx.reply("❌ Limit must be between 1 and 500!")
        
        try:
            # Get all users
            users_cursor = self.db.db.users.find({}).limit(limit)
            users = await users_cursor.to_list(length=limit)
            
            if not users:
                return await ctx.reply("No users found in database!")
            
            embed = discord.Embed(
                title="🔧 Bulk User Data Repair",
                description=f"Checking {len(users)} users for data issues...",
                color=discord.Color.blue()
            )
            message = await ctx.reply(embed=embed)
            
            repaired_count = 0
            total_repairs = []
            failed_users = []
            
            for user_doc in users:
                user_id = user_doc["_id"]
                
                try:
                    repairs_made = []
                    updates = {}
                    
                    # Same repair logic as single user repair
                    # Fix wallet/bank
                    if "wallet" not in user_doc or not isinstance(user_doc.get("wallet"), (int, float)):
                        updates["wallet"] = 0
                        repairs_made.append("wallet")
                    
                    if "bank" not in user_doc or not isinstance(user_doc.get("bank"), (int, float)):
                        updates["bank"] = 0
                        repairs_made.append("bank")
                    
                    # Fix inventory structure
                    inventory = user_doc.get("inventory", [])
                    
                    if isinstance(inventory, list):
                        new_inventory = {"rod": {}, "bait": {}, "potions": {}, "upgrades": {}}
                        
                        for item in inventory:
                            if isinstance(item, dict) and "type" in item:
                                item_type = item["type"]
                                item_id = item.get("id", item.get("_id", "unknown"))
                                quantity = item.get("quantity", item.get("amount", 1))
                                
                                if item_type == "potion":
                                    new_inventory["potions"][item_id] = quantity
                                elif item_type == "upgrade":
                                    new_inventory["upgrades"][item_id] = quantity
                                elif item_type == "rod":
                                    new_inventory["rod"][item_id] = quantity
                                elif item_type == "bait":
                                    new_inventory["bait"][item_id] = quantity
                        
                        updates["inventory"] = new_inventory
                        repairs_made.append("inventory_structure")
                    
                    elif isinstance(inventory, dict):
                        required_sections = ["rod", "bait", "potions", "upgrades"]
                        missing_sections = []
                        
                        for section in required_sections:
                            if section not in inventory:
                                if "inventory" not in updates:
                                    updates["inventory"] = inventory.copy()
                                updates["inventory"][section] = {}
                                missing_sections.append(section)
                        
                        if missing_sections:
                            repairs_made.append("inventory_sections")
                    
                    # Fix fishing data
                    if "fishing" not in user_doc or not isinstance(user_doc.get("fishing"), dict):
                        updates["fishing"] = {
                            "selected_rod": None,
                            "selected_bait": None,
                            "fish_caught": {}
                        }
                        repairs_made.append("fishing_data")
                    
                    # Fix active effects
                    if "active_effects" not in user_doc or not isinstance(user_doc.get("active_effects"), dict):
                        updates["active_effects"] = {}
                        repairs_made.append("active_effects")
                    
                    # Apply updates if needed
                    if updates:
                        await self.db.db.users.update_one(
                            {"_id": user_id},
                            {"$set": updates}
                        )
                        repaired_count += 1
                        total_repairs.extend(repairs_made)
                
                except Exception as e:
                    failed_users.append(f"{user_id}: {str(e)[:50]}")
            
            # Update embed with results
            embed = discord.Embed(
                title="✅ Bulk Repair Complete",
                description=f"Processed {len(users)} users",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📊 Results",
                value=(
                    f"✅ Users Repaired: {repaired_count}\n"
                    f"⚠️ Failed Repairs: {len(failed_users)}\n"
                    f"🔧 Total Fixes: {len(total_repairs)}"
                ),
                inline=False
            )
            
            if total_repairs:
                repair_counts = {}
                for repair in total_repairs:
                    repair_counts[repair] = repair_counts.get(repair, 0) + 1
                
                repair_summary = "\n".join([f"• {repair}: {count}" for repair, count in repair_counts.items()])
                embed.add_field(
                    name="🔧 Repairs Made",
                    value=repair_summary,
                    inline=False
                )
            
            if failed_users:
                embed.add_field(
                    name="❌ Failed Users",
                    value="\n".join(failed_users[:5]) + ("..." if len(failed_users) > 5 else ""),
                    inline=False
                )
            
            await message.edit(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to repair all users: {e}")
            embed = discord.Embed(
                title="❌ Bulk Repair Failed",
                description=f"An error occurred during bulk repair:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def test(self, ctx):
        """Test command for debugging"""
        await ctx.reply("Admin cog is working!")

async def setup(bot):
    await bot.add_cog(Admin(bot))
