from discord.ext import commands
import discord
import random
import asyncio
import uuid
import datetime
from utils.db import async_db as db
from utils.safe_reply import safe_reply

class AutoFishing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currency = "<:bronkbuk:1377389238290747582>"
        self.BASE_PRICE = 1000
        self.PRICE_MULTIPLIER = 2.5
        self.MAX_AUTOFISHERS = 10
        self.BAIT_COST = 50
        self.CATCH_CHANCE = 0.5
        self.AUTOFISH_INTERVAL = 30  # seconds
        self.autofishing_task = None
        self.last_autofish_time = datetime.datetime.now()
        
        # Bag limit system - based on total deposited amount
        self.BAG_LIMITS = {
            0: 10,        # Default: 10 fish
            1000: 15,     # 1k deposited: 15 fish
            5000: 30,     # 5k deposited: 30 fish
            10000: 50,    # 10k deposited: 50 fish
            20000: 75,    # 20k deposited: 75 fish
            30000: 100,   # 30k deposited: 100 fish
            50000: 150,   # 50k deposited: 150 fish
            100000: 200,  # 100k deposited: 200 fish
            250000: 350,  # 250k deposited: 350 fish
            500000: 500,  # 500k deposited: 500 fish
            1000000: 750, # 1M deposited: 750 fish
            2000000: 1000, # 2M deposited: 1000 fish
            5000000: 2500, # 5M deposited: 2500 fish
            10000000: 5000, # 10M deposited: 5000 fish
            25000000: 10000, # 25M deposited: 10000 fish
            50000000: 25000, # 50M deposited: 25000 fish
            100000000: 50000, # 100M deposited: 50000 fish
            250000000: 100000, # 250M deposited: 100000 fish
            500000000: 250000, # 500M deposited: 250000 fish
            1000000000: 1000000000 # 1B deposited: 1 billion fish limit
        }
        
    async def cog_load(self):
        self.autofishing_task = self.bot.loop.create_task(self.autofishing_loop())

    def cog_unload(self):
        if self.autofishing_task:
            self.autofishing_task.cancel()

    async def autofishing_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                self.last_autofish_time = datetime.datetime.now()
                # Get all users with autofishers
                users = await self.get_all_autofisher_users()
                for user_id in users:
                    try:
                        await self.process_autofishing(user_id)
                    except Exception as e:
                        print(f"Error processing autofishing for {user_id}: {e}")
                await asyncio.sleep(self.AUTOFISH_INTERVAL)  # Run every 30 seconds
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

    def get_bag_limit(self, total_deposited):
        """Calculate bag limit based on total amount deposited"""
        for threshold in sorted(self.BAG_LIMITS.keys(), reverse=True):
            if total_deposited >= threshold:
                return self.BAG_LIMITS[threshold]
        return self.BAG_LIMITS[0]  # Default limit

    async def get_current_fish_count(self, user_id):
        """Get current number of fish from autofisher"""
        try:
            user_data = await db.db.users.find_one({"_id": str(user_id)})
            if not user_data:
                return 0
            
            # Count fish that were auto-caught
            fish_list = user_data.get("fish", [])
            auto_fish_count = sum(1 for fish in fish_list if fish.get("auto_caught", False))
            return auto_fish_count
        except Exception as e:
            print(f"Error getting fish count: {e}")
            return 0

    async def can_catch_fish(self, user_id):
        """Check if user can catch more fish (bag limit check)"""
        try:
            user_data = await db.db.users.find_one({"_id": str(user_id)})
            if not user_data:
                return False
            
            autofisher_data = user_data.get("autofisher", {})
            total_deposited = autofisher_data.get("total_deposited", 0)
            
            current_fish_count = await self.get_current_fish_count(user_id)
            bag_limit = self.get_bag_limit(total_deposited)
            
            return current_fish_count < bag_limit
        except Exception as e:
            print(f"Error checking bag limit: {e}")
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
            active_rod = autofisher_data.get("active_rod", "advanced_rod")
            active_bait = autofisher_data.get("active_bait", "pro_bait")
            caught_fish = []
            
            # Process each autofisher
            for _ in range(autofisher_count):
                # Check bag limit first
                if not await self.can_catch_fish(user_id):
                    break  # Bag is full, stop fishing
                    
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
                    "bait_used": active_bait,
                    "rod_used": active_rod
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
        """Get value range for fish type (increased values)"""
        value_ranges = {
            "normal": (50, 300),      # Was 10-100, now 50-300
            "uncommon": (200, 600),   # Was 50-200, now 200-600
            "rare": (500, 1500),      # Was 100-500, now 500-1500
            "epic": (1000, 3000),     # Was 200-1000, now 1000-3000
            "legendary": (2500, 6000), # Was 500-2000, now 2500-6000
            "mythical": (5000, 15000), # Was 1000-5000, now 5000-15000
        }
        min_val, max_val = value_ranges.get(fish_type, (50, 300))
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
                return await safe_reply(ctx, embed=embed)
                
            count = autofisher_data.get("count", 0)
            balance = autofisher_data.get("balance", 0)
            total_deposited = autofisher_data.get("total_deposited", 0)
            next_cost = int(self.BASE_PRICE * (self.PRICE_MULTIPLIER ** count)) if count < self.MAX_AUTOFISHERS else "MAX"
            
            # Get bag information
            current_fish_count = await self.get_current_fish_count(ctx.author.id)
            bag_limit = self.get_bag_limit(total_deposited)
            
            embed.add_field(name="Autofishers", value=f"{count}/{self.MAX_AUTOFISHERS}", inline=True)
            embed.add_field(name="Balance", value=f"{balance:,} {self.currency}", inline=True)
            embed.add_field(name="Fish Bag", value=f"{current_fish_count}/{bag_limit}", inline=True)
            
            # Show next bag upgrade
            next_upgrade = None
            for threshold in sorted(self.BAG_LIMITS.keys()):
                if threshold > total_deposited:
                    next_upgrade = threshold
                    break
            
            if next_upgrade:
                next_limit = self.BAG_LIMITS[next_upgrade]
                needed = next_upgrade - total_deposited
                embed.add_field(
                    name="Next Bag Upgrade", 
                    value=f"{next_limit} fish (deposit {needed:,} more)", 
                    inline=False
                )
            else:
                embed.add_field(name="Bag Status", value="Maximum bag capacity!", inline=False)
            
            # Calculate time until next autofish
            if hasattr(self, 'last_autofish_time'):
                time_since_last = (datetime.datetime.now() - self.last_autofish_time).total_seconds()
                time_until_next = max(0, self.AUTOFISH_INTERVAL - time_since_last)
                if time_until_next > 0:
                    embed.add_field(name="Next Autofish", value=f"{int(time_until_next)}s", inline=True)
                else:
                    embed.add_field(name="Next Autofish", value="Now!", inline=True)
            
            if count < self.MAX_AUTOFISHERS:
                embed.add_field(name="Next Autofisher Cost", value=f"{next_cost} {self.currency}", inline=False)
            else:
                embed.add_field(name="Status", value="Maximum autofishers reached!", inline=False)
                
            await safe_reply(ctx, embed=embed)
        except Exception as e:
            print(f"Error in auto command: {e}")
            await safe_reply(ctx, "❌ Error retrieving autofisher data!")

    @auto.command(aliases=['buyauto'])
    async def buy(self, ctx):
        """Buy an autofisher"""
        try:
            user_data = await db.db.users.find_one({"_id": str(ctx.author.id)})
            autofisher_data = user_data.get("autofisher", {"count": 0, "balance": 0}) if user_data else {"count": 0, "balance": 0}
            
            current_count = autofisher_data.get("count", 0)
            
            if current_count >= self.MAX_AUTOFISHERS:
                return await safe_reply(ctx, f"You've reached the max of {self.MAX_AUTOFISHERS} autofishers!")
                
            cost = int(self.BASE_PRICE * (self.PRICE_MULTIPLIER ** current_count))
            balance = await db.get_balance(ctx.author.id)
            
            if balance < cost:
                return await safe_reply(ctx, f"Need {cost} {self.currency} (You have {balance})")
                
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
                await safe_reply(ctx, f"✅ Purchased autofisher #{new_count}!")
            else:
                await safe_reply(ctx, "❌ Failed to purchase autofisher!")
        except Exception as e:
            print(f"Error buying autofisher: {e}")
            await safe_reply(ctx, "❌ Error purchasing autofisher!")

    @auto.command()
    async def deposit(self, ctx, amount: int):
        """Deposit money into autofisher balance"""
        if amount <= 0:
            return await safe_reply(ctx, "Amount must be positive!")
            
        try:
            user_data = await db.db.users.find_one({"_id": str(ctx.author.id)})
            if not user_data or not user_data.get("autofisher", {}).get("count", 0):
                return await safe_reply(ctx, "Buy an autofisher first!")
                
            balance = await db.get_balance(ctx.author.id)
            if balance < amount:
                return await safe_reply(ctx, f"You only have {balance} {self.currency}")
                
            if await db.update_balance(ctx.author.id, -amount):
                await db.db.users.update_one(
                    {"_id": str(ctx.author.id)},
                    {"$inc": {
                        "autofisher.balance": amount,
                        "autofisher.total_deposited": amount
                    }}
                )
                await safe_reply(ctx, f"✅ Deposited {amount} {self.currency}!")
            else:
                await safe_reply(ctx, "❌ Failed to deposit money!")
        except Exception as e:
            print(f"Error depositing to autofisher: {e}")
            await safe_reply(ctx, "❌ Error depositing money!")

    @auto.command()
    async def collect(self, ctx):
        """Collect and sell auto-caught fish"""
        try:
            fish = await db.get_fish(ctx.author.id)
            if not fish:
                return await safe_reply(ctx, "No fish in your collection!")
                
            auto_fish = [f for f in fish if f.get("auto_caught")]
            
            if not auto_fish:
                return await safe_reply(ctx, "No auto-caught fish to collect!")
                
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
                    await safe_reply(ctx, embed=embed)
                else:
                    await safe_reply(ctx, "❌ Error updating balance!")
            else:
                await safe_reply(ctx, "❌ No auto-caught fish found!")
                
        except Exception as e:
            print(f"Error collecting auto fish: {e}")
            await safe_reply(ctx, "❌ Error collecting auto-caught fish!")

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
                return await safe_reply(ctx, embed=embed)
            
            count = autofisher_data.get("count", 0)
            balance = autofisher_data.get("balance", 0)
            active_rod = autofisher_data.get("active_rod", "advanced_rod")
            active_bait = autofisher_data.get("active_bait", "pro_bait")
            
            embed.add_field(name="Active Autofishers", value=f"{count}", inline=True)
            embed.add_field(name="Balance", value=f"{balance} {self.currency}", inline=True)
            embed.add_field(name="Pending Fish", value=f"{len(auto_fish)}", inline=True)
            
            # Show active gear
            embed.add_field(
                name="🎣 Active Rod", 
                value=active_rod.replace('_', ' ').title(), 
                inline=True
            )
            embed.add_field(
                name="🪱 Active Bait", 
                value=active_bait.replace('_', ' ').title(), 
                inline=True
            )
            embed.add_field(name="⚙️", value="Use `.auto configure` to change gear", inline=True)
            
            if auto_fish:
                total_value = sum(f["value"] for f in auto_fish)
                embed.add_field(name="Pending Value", value=f"{total_value} {self.currency}", inline=False)
                embed.set_footer(text="Use '.auto collect' to collect your fish!")
            
            await safe_reply(ctx, embed=embed)
            
        except Exception as e:
            print(f"Error checking autofisher status: {e}")
            await safe_reply(ctx, "❌ Error checking autofisher status!")

    @auto.command()
    async def configure(self, ctx, rod_type: str = None, bait_type: str = None):
        """Configure active rod and bait for autofishing"""
        if not rod_type and not bait_type:
            # Show current configuration
            user_data = await db.db.users.find_one({"_id": str(ctx.author.id)})
            autofisher_data = user_data.get("autofisher", {}) if user_data else {}
            
            current_rod = autofisher_data.get("active_rod", "advanced_rod")
            current_bait = autofisher_data.get("active_bait", "pro_bait")
            
            embed = discord.Embed(title="🎣 Autofisher Configuration", color=0x2b2d31)
            embed.add_field(name="Active Rod", value=current_rod.replace('_', ' ').title(), inline=True)
            embed.add_field(name="Active Bait", value=current_bait.replace('_', ' ').title(), inline=True)
            embed.add_field(
                name="Usage", 
                value="`.auto configure <rod_type> <bait_type>`\nExample: `.auto configure advanced_rod pro_bait`", 
                inline=False
            )
            return await safe_reply(ctx, embed=embed)
        
        # Valid rod and bait types
        valid_rods = ["beginner_rod", "advanced_rod", "pro_rod", "master_rod"]
        valid_baits = ["beginner_bait", "pro_bait", "master_bait", "legendary_bait"]
        
        if rod_type and rod_type not in valid_rods:
            return await safe_reply(ctx, f"❌ Invalid rod type! Valid options: {', '.join(valid_rods)}")
        
        if bait_type and bait_type not in valid_baits:
            return await safe_reply(ctx, f"❌ Invalid bait type! Valid options: {', '.join(valid_baits)}")
        
        # Update configuration
        update_data = {}
        if rod_type:
            update_data["autofisher.active_rod"] = rod_type
        if bait_type:
            update_data["autofisher.active_bait"] = bait_type
        
        result = await db.db.users.update_one(
            {"_id": str(ctx.author.id)},
            {"$set": update_data},
            upsert=True
        )
        
        if result.modified_count > 0 or result.upserted_id:
            embed = discord.Embed(title="✅ Configuration Updated", color=0x00ff00)
            if rod_type:
                embed.add_field(name="Active Rod", value=rod_type.replace('_', ' ').title(), inline=True)
            if bait_type:
                embed.add_field(name="Active Bait", value=bait_type.replace('_', ' ').title(), inline=True)
            await safe_reply(ctx, embed=embed)
        else:
            await safe_reply(ctx, "❌ Failed to update configuration!")

    @auto.command(name="test_bag", hidden=True)
    @commands.is_owner()
    async def test_bag_system(self, ctx):
        """Test the bag limit system"""
        try:
            user_data = await db.db.users.find_one({"_id": str(ctx.author.id)})
            autofisher_data = user_data.get("autofisher", {}) if user_data else {}
            
            total_deposited = autofisher_data.get("total_deposited", 0)
            current_fish_count = await self.get_current_fish_count(ctx.author.id)
            bag_limit = self.get_bag_limit(total_deposited)
            can_catch = await self.can_catch_fish(ctx.author.id)
            
            embed = discord.Embed(
                title="🧪 Bag System Test",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Total Deposited", value=f"{total_deposited:,} {self.currency}", inline=True)
            embed.add_field(name="Current Fish Count", value=f"{current_fish_count}", inline=True)
            embed.add_field(name="Bag Limit", value=f"{bag_limit}", inline=True)
            embed.add_field(name="Can Catch More", value="✅ Yes" if can_catch else "❌ No", inline=True)
            
            # Show bag limit tiers
            tiers_text = ""
            for threshold in sorted(self.BAG_LIMITS.keys()):
                limit = self.BAG_LIMITS[threshold]
                status = "✅" if total_deposited >= threshold else "❌"
                tiers_text += f"{status} {threshold:,} {self.currency} → {limit} fish\n"
            
            embed.add_field(name="Bag Limit Tiers", value=tiers_text, inline=False)
            
            await safe_reply(ctx, embed=embed)
            
        except Exception as e:
            await safe_reply(ctx, f"❌ Test failed: {e}")

async def setup(bot):
    await bot.add_cog(AutoFishing(bot))
