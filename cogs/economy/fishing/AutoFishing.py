from discord.ext import commands
import discord
import random
import asyncio
import uuid
import datetime
from utils.db import async_db as db

class AutoFishing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currency = "<:bronkbuk:1377389238290747582>"
        self.BASE_PRICE = 1000
        self.PRICE_MULTIPLIER = 2.5
        self.MAX_AUTOFISHERS = 10
        self.BAIT_COST = 50
        self.CATCH_CHANCE = 0.5
        self.autofishing_task = None
        
    async def cog_load(self):
        self.autofishing_task = self.bot.loop.create_task(self.autofishing_loop())

    def cog_unload(self):
        if self.autofishing_task:
            self.autofishing_task.cancel()

    async def autofishing_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                # Get all users with autofishers
                users = await self.get_all_autofisher_users()
                for user_id in users:
                    try:
                        await self.process_autofishing(user_id)
                    except Exception as e:
                        print(f"Error processing autofishing for {user_id}: {e}")
                await asyncio.sleep(30)  # Run every 30 seconds
            except Exception as e:
                print(f"Error in autofishing loop: {e}")
                await asyncio.sleep(60)

    async def get_all_autofisher_users(self):
        """Get all users who have autofishers"""
        try:
            cursor = db.db.users.find({"autofisher.count": {"$gt": 0}})
            users = []
            async for user in cursor:
                users.append(int(user["_id"]))
            return users
        except Exception as e:
            print(f"Error getting autofisher users: {e}")
            return []

    async def get_user_inventory(self, user_id: int):
        """Get user's inventory from database"""
        try:
            user_data = await db.db.users.find_one({"_id": str(user_id)})
            if not user_data:
                return None
            return user_data.get("inventory", {})
        except Exception as e:
            print(f"Error getting user inventory: {e}")
            return None

    async def has_bait(self, user_id: int):
        """Check if user has any bait"""
        inventory = await self.get_user_inventory(user_id)
        if not inventory:
            return False
        
        bait_inventory = inventory.get("bait", {})
        for bait_id, quantity in bait_inventory.items():
            if quantity > 0:
                return True
        return False

    async def remove_any_bait(self, user_id: int):
        """Remove one bait of any type from user's inventory"""
        try:
            inventory = await self.get_user_inventory(user_id)
            if not inventory:
                return False
            
            bait_inventory = inventory.get("bait", {})
            for bait_id, quantity in bait_inventory.items():
                if quantity > 0:
                    result = await db.db.users.update_one(
                        {"_id": str(user_id), f"inventory.bait.{bait_id}": {"$gt": 0}},
                        {"$inc": {f"inventory.bait.{bait_id}": -1}}
                    )
                    return result.modified_count > 0
            return False
        except Exception as e:
            print(f"Error removing bait: {e}")
            return False

    async def buy_bait_for_autofisher(self, user_id: int, cost: int):
        """Buy bait using autofisher balance"""
        try:
            # Remove cost from autofisher balance and add bait
            result = await db.db.users.update_one(
                {"_id": str(user_id), "autofisher.balance": {"$gte": cost}},
                {
                    "$inc": {
                        "autofisher.balance": -cost,
                        "inventory.bait.pro_bait": 10
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error buying bait for autofisher: {e}")
            return False

    async def process_autofishing(self, user_id):
        try:
            # Get autofisher data
            user_data = await db.db.users.find_one({"_id": str(user_id)})
            if not user_data:
                return
                
            autofisher_data = user_data.get("autofisher", {})
            if not autofisher_data or not autofisher_data.get("count", 0):
                return
            
            # Check if user has any rods
            inventory = user_data.get("inventory", {})
            rod_inventory = inventory.get("rod", {})
            has_rods = any(quantity > 0 for quantity in rod_inventory.values())
            
            if not has_rods:
                return  # Can't fish without rods
                
            autofisher_count = autofisher_data.get("count", 0)
            autofisher_balance = autofisher_data.get("balance", 0)
            caught_fish = []
            
            # Process each autofisher
            for _ in range(autofisher_count):
                # Random chance to catch something
                if random.random() > self.CATCH_CHANCE:
                    continue
                    
                # Check if has bait, if not try to buy some
                if not await self.has_bait(user_id):
                    if autofisher_balance >= self.BAIT_COST:
                        if await self.buy_bait_for_autofisher(user_id, self.BAIT_COST):
                            autofisher_balance -= self.BAIT_COST
                        else:
                            continue  # Failed to buy bait
                    else:
                        continue  # Not enough balance for bait
                        
                # Remove bait
                if not await self.remove_any_bait(user_id):
                    continue  # No bait available
                    
                # Generate fish (simpler catches for autofisher)
                fish_type = self.determine_auto_fish_type()
                fish_value = self.get_fish_value(fish_type)
                
                fish = {
                    "id": str(uuid.uuid4()),
                    "type": fish_type,
                    "name": f"{fish_type.title()} Fish",
                    "value": fish_value,
                    "caught_at": datetime.datetime.now().isoformat(),
                    "auto_caught": True,
                    "bait_used": "auto_bait",
                    "rod_used": "auto_rod"
                }
                caught_fish.append(fish)
                
            # Add caught fish to database
            if caught_fish:
                await self.add_fish_batch(user_id, caught_fish)
                
            # Update autofisher balance if it changed
            if autofisher_balance != autofisher_data.get("balance", 0):
                await db.db.users.update_one(
                    {"_id": str(user_id)},
                    {"$set": {"autofisher.balance": autofisher_balance}}
                )
                
        except Exception as e:
            print(f"Error processing autofishing for {user_id}: {e}")

    def determine_auto_fish_type(self):
        """Determine what type of fish to catch (autofishers catch mostly normal fish)"""
        rand = random.random()
        if rand < 0.7:
            return "normal"
        elif rand < 0.85:
            return "uncommon"
        elif rand < 0.95:
            return "rare"
        else:
            return "epic"

    def get_fish_value(self, fish_type):
        """Get value range for fish type"""
        value_ranges = {
            "normal": (10, 100),
            "uncommon": (50, 200),
            "rare": (100, 500),
            "epic": (200, 1000),
            "legendary": (500, 2000),
            "mythical": (1000, 5000),
        }
        min_val, max_val = value_ranges.get(fish_type, (10, 100))
        return random.randint(min_val, max_val)

    async def add_fish_batch(self, user_id: int, fish_list):
        """Add multiple fish to user's collection"""
        try:
            result = await db.db.users.update_one(
                {"_id": str(user_id)},
                {"$push": {"fish": {"$each": fish_list}}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            print(f"Error adding fish batch: {e}")
            return False

    @commands.group(aliases=['af', 'afish'], invoke_without_command=True)
    async def auto(self, ctx):
        """Autofisher management system"""
        try:
            user_data = await db.db.users.find_one({"_id": str(ctx.author.id)})
            autofisher_data = user_data.get("autofisher", {}) if user_data else {}
            
            embed = discord.Embed(title="🤖 Autofisher System", color=0x2b2d31)
            
            if not autofisher_data or not autofisher_data.get("count", 0):
                embed.description = "You don't have any autofishers yet!"
                embed.add_field(name="First Autofisher Cost", 
                               value=f"{self.BASE_PRICE} {self.currency}")
                return await ctx.send(embed=embed)
                
            count = autofisher_data.get("count", 0)
            balance = autofisher_data.get("balance", 0)
            next_cost = int(self.BASE_PRICE * (self.PRICE_MULTIPLIER ** count)) if count < self.MAX_AUTOFISHERS else "MAX"
            
            embed.add_field(name="Autofishers", value=f"{count}/{self.MAX_AUTOFISHERS}", inline=False)
            embed.add_field(name="Balance", value=f"{balance} {self.currency}", inline=False)
            
            if count < self.MAX_AUTOFISHERS:
                embed.add_field(name="Next Autofisher Cost", value=f"{next_cost} {self.currency}", inline=False)
            else:
                embed.add_field(name="Status", value="Maximum autofishers reached!", inline=False)
                
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"Error in auto command: {e}")
            await ctx.send("❌ Error retrieving autofisher data!")

    @auto.command(aliases=['buyauto'])
    async def buy(self, ctx):
        """Buy an autofisher"""
        try:
            user_data = await db.db.users.find_one({"_id": str(ctx.author.id)})
            autofisher_data = user_data.get("autofisher", {"count": 0, "balance": 0}) if user_data else {"count": 0, "balance": 0}
            
            current_count = autofisher_data.get("count", 0)
            
            if current_count >= self.MAX_AUTOFISHERS:
                return await ctx.send(f"You've reached the max of {self.MAX_AUTOFISHERS} autofishers!")
                
            cost = int(self.BASE_PRICE * (self.PRICE_MULTIPLIER ** current_count))
            balance = await db.get_balance(ctx.author.id)
            
            if balance < cost:
                return await ctx.send(f"Need {cost} {self.currency} (You have {balance})")
                
            if await db.update_balance(ctx.author.id, -cost):
                new_count = current_count + 1
                await db.db.users.update_one(
                    {"_id": str(ctx.author.id)},
                    {"$set": {
                        "autofisher.count": new_count,
                        "autofisher.balance": autofisher_data.get("balance", 0)
                    }},
                    upsert=True
                )
                await ctx.send(f"✅ Purchased autofisher #{new_count}!")
            else:
                await ctx.send("❌ Failed to purchase autofisher!")
        except Exception as e:
            print(f"Error buying autofisher: {e}")
            await ctx.send("❌ Error purchasing autofisher!")

    @auto.command()
    async def deposit(self, ctx, amount: int):
        """Deposit money into autofisher balance"""
        if amount <= 0:
            return await ctx.send("Amount must be positive!")
            
        try:
            user_data = await db.db.users.find_one({"_id": str(ctx.author.id)})
            if not user_data or not user_data.get("autofisher", {}).get("count", 0):
                return await ctx.send("Buy an autofisher first!")
                
            balance = await db.get_balance(ctx.author.id)
            if balance < amount:
                return await ctx.send(f"You only have {balance} {self.currency}")
                
            if await db.update_balance(ctx.author.id, -amount):
                await db.db.users.update_one(
                    {"_id": str(ctx.author.id)},
                    {"$inc": {"autofisher.balance": amount}}
                )
                await ctx.send(f"✅ Deposited {amount} {self.currency}!")
            else:
                await ctx.send("❌ Failed to deposit money!")
        except Exception as e:
            print(f"Error depositing to autofisher: {e}")
            await ctx.send("❌ Error depositing money!")

    @auto.command()
    async def collect(self, ctx):
        """Collect and sell auto-caught fish"""
        try:
            fish = await db.get_fish(ctx.author.id)
            if not fish:
                return await ctx.send("No fish in your collection!")
                
            auto_fish = [f for f in fish if f.get("auto_caught")]
            
            if not auto_fish:
                return await ctx.send("No auto-caught fish to collect!")
                
            total_value = sum(f["value"] for f in auto_fish)
            
            # Remove auto-caught fish and add money
            auto_fish_ids = [f["id"] for f in auto_fish]
            
            result = await db.db.users.update_one(
                {"_id": str(ctx.author.id)},
                {"$pull": {"fish": {"id": {"$in": auto_fish_ids}}}}
            )
            
            if result.modified_count > 0:
                if await db.update_balance(ctx.author.id, total_value):
                    embed = discord.Embed(
                        title="🤖 Auto-Fish Collection",
                        description=f"Sold {len(auto_fish)} auto-caught fish for **{total_value}** {self.currency}",
                        color=discord.Color.green()
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Error updating balance!")
            else:
                await ctx.send("❌ No auto-caught fish found!")
                
        except Exception as e:
            print(f"Error collecting auto fish: {e}")
            await ctx.send("❌ Error collecting auto-caught fish!")

    @auto.command()
    async def status(self, ctx):
        """Check autofisher status and recent catches"""
        try:
            fish = await db.get_fish(ctx.author.id)
            auto_fish = [f for f in fish if f.get("auto_caught")] if fish else []
            
            user_data = await db.db.users.find_one({"_id": str(ctx.author.id)})
            autofisher_data = user_data.get("autofisher", {}) if user_data else {}
            
            embed = discord.Embed(title="🤖 Autofisher Status", color=0x2b2d31)
            
            if not autofisher_data or not autofisher_data.get("count", 0):
                embed.description = "You don't have any autofishers!"
                return await ctx.send(embed=embed)
            
            count = autofisher_data.get("count", 0)
            balance = autofisher_data.get("balance", 0)
            
            embed.add_field(name="Active Autofishers", value=f"{count}", inline=True)
            embed.add_field(name="Balance", value=f"{balance} {self.currency}", inline=True)
            embed.add_field(name="Pending Fish", value=f"{len(auto_fish)}", inline=True)
            
            if auto_fish:
                total_value = sum(f["value"] for f in auto_fish)
                embed.add_field(name="Pending Value", value=f"{total_value} {self.currency}", inline=False)
                embed.set_footer(text="Use '.auto collect' to collect your fish!")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Error checking autofisher status: {e}")
            await ctx.send("❌ Error checking autofisher status!")

async def setup(bot):
    await bot.add_cog(AutoFishing(bot))
