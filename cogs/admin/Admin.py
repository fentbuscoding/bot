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

    @commands.command(name="servers", aliases=["serverlist", "guilds"])
    @commands.is_owner()
    async def servers(self, ctx):
        """View all servers the bot is in with pagination and remote leave functionality"""
        guilds = list(self.bot.guilds)
        
        if not guilds:
            embed = discord.Embed(
                title="No Servers", 
                description="The bot is not in any servers.",
                color=discord.Color.red()
            )
            return await ctx.reply(embed=embed)
        
        # Sort guilds by member count (descending)
        guilds.sort(key=lambda g: g.member_count, reverse=True)
        
        view = ServerManagerView(guilds, ctx.author, self.bot)
        embed = view.get_server_embed(0)
        
        message = await ctx.reply(embed=embed, view=view)
        view.message = message

class ServerManagerView(discord.ui.View):
    def __init__(self, guilds: List[discord.Guild], author: discord.User, bot):
        super().__init__(timeout=300)
        self.guilds = guilds
        self.author = author
        self.bot = bot
        self.current_page = 0
        self.message = None
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= len(self.guilds) - 1)
        
        # Update page info button
        self.page_info.label = f"{self.current_page + 1}/{len(self.guilds)}"
    
    def get_server_embed(self, page: int) -> discord.Embed:
        """Generate embed for a specific server"""
        if page >= len(self.guilds):
            page = len(self.guilds) - 1
        if page < 0:
            page = 0
            
        guild = self.guilds[page]
        
        # Get member status counts
        online_count = sum(1 for member in guild.members if member.status != discord.Status.offline and not member.bot)
        idle_count = sum(1 for member in guild.members if member.status == discord.Status.idle and not member.bot)
        dnd_count = sum(1 for member in guild.members if member.status == discord.Status.dnd and not member.bot)
        offline_count = sum(1 for member in guild.members if member.status == discord.Status.offline and not member.bot)
        bot_count = sum(1 for member in guild.members if member.bot)
        
        embed = discord.Embed(
            title=f"🔍 Server {page + 1}/{len(self.guilds)}",
            color=0x2b2d31
        )
        
        # Server basic info
        embed.add_field(
            name="📊 Server Info",
            value=(
                f"**Name:** {guild.name}\n"
                f"**ID:** `{guild.id}`\n"
                f"**Owner:** {guild.owner.mention if guild.owner else 'Unknown'} (`{guild.owner.id if guild.owner else 'Unknown'}`)\n"
                f"**Created:** <t:{int(guild.created_at.timestamp())}:R>\n"
                f"**Region:** {guild.preferred_locale or 'Unknown'}"
            ),
            inline=False
        )
        
        # Member statistics
        total_humans = guild.member_count - bot_count
        embed.add_field(
            name="👥 Member Statistics",
            value=(
                f"**Total Members:** {guild.member_count:,}\n"
                f"**Humans:** {total_humans:,} | **Bots:** {bot_count:,}\n\n"
                f"**Status Breakdown (Humans):**\n"
                f"🟢 Online: {online_count:,}\n"
                f"🟡 Idle: {idle_count:,}\n"
                f"🔴 DND: {dnd_count:,}\n"
                f"⚫ Offline: {offline_count:,}"
            ),
            inline=True
        )
        
        # Server features
        features_text = []
        if guild.premium_tier > 0:
            features_text.append(f"💎 Boost Level {guild.premium_tier} ({guild.premium_subscription_count} boosts)")
        if guild.verification_level != discord.VerificationLevel.none:
            features_text.append(f"🛡️ Verification: {guild.verification_level.name.title()}")
        if guild.features:
            notable_features = [f for f in guild.features if f in ['COMMUNITY', 'PARTNERED', 'VERIFIED', 'DISCOVERABLE']]
            if notable_features:
                features_text.extend([f"✨ {f.title()}" for f in notable_features])
        
        embed.add_field(
            name="⚙️ Server Features",
            value=(
                f"**Channels:** {len(guild.channels):,} total\n"
                f"📝 Text: {len(guild.text_channels):,} | 🔊 Voice: {len(guild.voice_channels):,}\n"
                f"**Roles:** {len(guild.roles):,}\n"
                f"**Emojis:** {len(guild.emojis):,}/{guild.emoji_limit}\n\n"
                + ("\n".join(features_text) if features_text else "No special features")
            ),
            inline=True
        )
        
        # Activity indicator
        activity_ratio = (online_count + idle_count + dnd_count) / max(total_humans, 1)
        if activity_ratio > 0.3:
            activity_status = "🟢 Active"
        elif activity_ratio > 0.1:
            activity_status = "🟡 Moderate"
        elif activity_ratio > 0.05:
            activity_status = "🟠 Low Activity"
        else:
            activity_status = "🔴 Dead/Inactive"
            
        embed.add_field(
            name="📈 Activity Status",
            value=(
                f"{activity_status}\n"
                f"**Active Ratio:** {activity_ratio:.1%}\n"
                f"**Last Interaction:** Bot joined <t:{int(guild.me.joined_at.timestamp())}:R>"
            ),
            inline=False
        )
        
        # Set thumbnail
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        # Footer with navigation info
        embed.set_footer(text=f"Use the buttons below to navigate or leave this server")
        
        return embed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only the command author can use these buttons"""
        if interaction.user != self.author:
            await interaction.response.send_message(
                "❌ Only the command author can use these buttons!", 
                ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.secondary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous server"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.get_server_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def page_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Page info button (disabled)"""
        await interaction.response.defer()
    
    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next server"""
        if self.current_page < len(self.guilds) - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.get_server_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🚪 Leave Server", style=discord.ButtonStyle.danger)
    async def leave_server_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Leave the current server"""
        guild = self.guilds[self.current_page]
        
        # Create confirmation view
        confirm_view = LeaveConfirmView(guild, self, self.author)
        
        embed = discord.Embed(
            title="⚠️ Confirm Server Leave",
            description=(
                f"Are you sure you want to leave **{guild.name}**?\n\n"
                f"**Server Info:**\n"
                f"• ID: `{guild.id}`\n"
                f"• Members: {guild.member_count:,}\n"
                f"• Owner: {guild.owner.mention if guild.owner else 'Unknown'}\n\n"
                "**This action cannot be undone!**"
            ),
            color=discord.Color.red()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        await interaction.response.edit_message(embed=embed, view=confirm_view)
    
    @discord.ui.button(label="📊 Summary", style=discord.ButtonStyle.primary)
    async def summary_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show server summary statistics"""
        total_members = sum(guild.member_count for guild in self.guilds)
        total_humans = 0
        total_bots = 0
        active_servers = 0
        dead_servers = 0
        
        for guild in self.guilds:
            bot_count = sum(1 for member in guild.members if member.bot)
            human_count = guild.member_count - bot_count
            total_humans += human_count
            total_bots += bot_count
            
            # Calculate activity
            online_count = sum(1 for member in guild.members if member.status != discord.Status.offline and not member.bot)
            idle_count = sum(1 for member in guild.members if member.status == discord.Status.idle and not member.bot)
            dnd_count = sum(1 for member in guild.members if member.status == discord.Status.dnd and not member.bot)
            
            activity_ratio = (online_count + idle_count + dnd_count) / max(human_count, 1)
            if activity_ratio > 0.05:
                active_servers += 1
            else:
                dead_servers += 1
        
        embed = discord.Embed(
            title="📊 Bot Server Summary",
            color=0x2b2d31
        )
        
        embed.add_field(
            name="🌐 Overview",
            value=(
                f"**Total Servers:** {len(self.guilds):,}\n"
                f"**Total Members:** {total_members:,}\n"
                f"**Average per Server:** {total_members // len(self.guilds):,}\n"
            ),
            inline=True
        )
        
        embed.add_field(
            name="👥 Member Breakdown",
            value=(
                f"**Humans:** {total_humans:,}\n"
                f"**Bots:** {total_bots:,}\n"
                f"**Bot Ratio:** {(total_bots/total_members*100):.1f}%\n"
            ),
            inline=True
        )
        
        embed.add_field(
            name="📈 Activity Analysis",
            value=(
                f"**Active Servers:** {active_servers:,}\n"
                f"**Dead/Inactive:** {dead_servers:,}\n"
                f"**Health Score:** {(active_servers/len(self.guilds)*100):.1f}%\n"
            ),
            inline=True
        )
        
        # Top servers by member count
        top_servers = sorted(self.guilds, key=lambda g: g.member_count, reverse=True)[:5]
        top_list = []
        for i, guild in enumerate(top_servers, 1):
            bot_count = sum(1 for member in guild.members if member.bot)
            human_count = guild.member_count - bot_count
            top_list.append(f"{i}. **{guild.name}** - {guild.member_count:,} ({human_count:,} humans)")
        
        embed.add_field(
            name="🏆 Top 5 Servers by Members",
            value="\n".join(top_list),
            inline=False
        )
        
        # Add button to go back to server browser
        back_view = SummaryBackView(self)
        await interaction.response.edit_message(embed=embed, view=back_view)
    
    async def on_timeout(self):
        """Disable all buttons when view times out"""
        for item in self.children:
            item.disabled = True
        
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass

class LeaveConfirmView(discord.ui.View):
    def __init__(self, guild: discord.Guild, parent_view: ServerManagerView, author: discord.User):
        super().__init__(timeout=60)
        self.guild = guild
        self.parent_view = parent_view
        self.author = author
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only the command author can use these buttons"""
        if interaction.user != self.author:
            await interaction.response.send_message(
                "❌ Only the command author can use these buttons!", 
                ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(label="✅ Yes, Leave", style=discord.ButtonStyle.danger)
    async def confirm_leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm leaving the server"""
        try:
            guild_name = self.guild.name
            guild_id = self.guild.id
            member_count = self.guild.member_count
            
            # Leave the server
            await self.guild.leave()
            
            # Remove from parent view's guild list
            self.parent_view.guilds.remove(self.guild)
            
            # Adjust current page if necessary
            if self.parent_view.current_page >= len(self.parent_view.guilds):
                self.parent_view.current_page = max(0, len(self.parent_view.guilds) - 1)
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Successfully Left Server",
                description=(
                    f"**Left:** {guild_name}\n"
                    f"**ID:** `{guild_id}`\n"
                    f"**Members:** {member_count:,}\n\n"
                    f"Remaining servers: {len(self.parent_view.guilds):,}"
                ),
                color=discord.Color.green()
            )
            
            if len(self.parent_view.guilds) > 0:
                # Update parent view and go back to server browser
                self.parent_view.update_buttons()
                back_view = SummaryBackView(self.parent_view)
                await interaction.response.edit_message(embed=embed, view=back_view)
            else:
                # No servers left
                embed.description += "\n\n🎉 Bot is no longer in any servers!"
                await interaction.response.edit_message(embed=embed, view=None)
            
        except discord.HTTPException as e:
            embed = discord.Embed(
                title="❌ Failed to Leave Server",
                description=f"Error: {e}",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel leaving the server"""
        embed = self.parent_view.get_server_embed(self.parent_view.current_page)
        self.parent_view.update_buttons()
        await interaction.response.edit_message(embed=embed, view=self.parent_view)

class SummaryBackView(discord.ui.View):
    def __init__(self, parent_view: ServerManagerView):
        super().__init__(timeout=300)
        self.parent_view = parent_view
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only the command author can use these buttons"""
        if interaction.user != self.parent_view.author:
            await interaction.response.send_message(
                "❌ Only the command author can use these buttons!", 
                ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(label="🔙 Back to Server Browser", style=discord.ButtonStyle.primary)
    async def back_to_browser(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go back to the server browser"""
        if len(self.parent_view.guilds) > 0:
            embed = self.parent_view.get_server_embed(self.parent_view.current_page)
            self.parent_view.update_buttons()
            await interaction.response.edit_message(embed=embed, view=self.parent_view)
        else:
            embed = discord.Embed(
                title="No Servers Left",
                description="The bot is no longer in any servers.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(Admin(bot))
