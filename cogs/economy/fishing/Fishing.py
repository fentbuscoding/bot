# Fixed Fishing.py - Focus on bait handling fixes
# This file is part of the Bronk Discord Bot project.

# template for adding bait that uses every possible value
{
  "_id": "insane_bait",
  "name": "INSANE BAIT",
  "type": "bait",
  "price": { "$numberInt": "50000" },
  "description": "For the worthy.",
  "catch_rates": {
    "normal":0.0,
    "uncommon":0.0,
    "rare": 0.0,
    "epic": 0.0,
    "legendary": 0.0,
    "mythical": 0.0,
    "event": 0.0,
    "mutated": 0.1,
    "insane": 100000.0,
    "master": 0.0
  }
}

from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import async_db as db
import discord
import random
import uuid
import datetime
import asyncio

class Fishing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.currency = "<:bronkbuk:1377389238290747582>"
        self.blocked_channels = [1378156495144751147, 1260347806699491418]
    
    # piece de resistance: cog_check
    async def cog_check(self, ctx):
        """Global check for all commands in this cog"""
        if ctx.channel.id in self.blocked_channels and not ctx.author.guild_permissions.administrator:
            await ctx.reply(
                random.choice([f"❌ Economy commands are disabled in this channel. "
                f"Please use them in another channel.",
                "<#1314685928614264852> is a good place for that."])
            )
            return False
        return True

    def get_all_bait(self, user_data):
        """Get all bait from both inventory and fishing_bait arrays"""
        all_bait = []
        
        # Get bait from inventory.bait (newer structure)
        inventory_bait = user_data.get("inventory", {}).get("bait", {})
        for bait_key, bait_data in inventory_bait.items():
            if isinstance(bait_data, dict) and bait_data.get("$numberInt"):
                # Handle MongoDB number format
                amount = int(bait_data["$numberInt"])
                if amount > 0:
                    all_bait.append({
                        "_id": bait_key,
                        "name": bait_key.replace("_", " ").title(),
                        "amount": amount,
                        "source": "inventory"
                    })
        
        # Get bait from fishing_bait array (older structure)
        fishing_bait = user_data.get("fishing_bait", [])
        for bait in fishing_bait:
            amount = bait.get("amount", 0)
            if isinstance(amount, dict) and amount.get("$numberInt"):
                amount = int(amount["$numberInt"])
            if amount > 0:
                all_bait.append({
                    "_id": bait.get("id", bait.get("_id")),
                    "name": bait.get("name", "Unknown Bait"),
                    "amount": amount,
                    "catch_rates": bait.get("catch_rates", {}),
                    "description": bait.get("description", ""),
                    "source": "fishing_bait"
                })
        
        # Also get from user_data.bait (another possible structure)
        direct_bait = user_data.get("bait", [])
        for bait in direct_bait:
            amount = bait.get("amount", 0)
            if isinstance(amount, dict) and amount.get("$numberInt"):
                amount = int(amount["$numberInt"])
            if amount > 0:
                all_bait.append({
                    "_id": bait.get("_id", bait.get("id")),
                    "name": bait.get("name", "Unknown Bait"),
                    "amount": amount,
                    "catch_rates": bait.get("catch_rates", {}),
                    "description": bait.get("description", ""),
                    "source": "bait"
                })
        
        return all_bait

    def get_bait_catch_rates(self, bait_id):
        """Get catch rates for specific bait types"""
        bait_rates = {
            "insane_bait": {
                "normal": 0.0,
                "uncommon": 0.0,
                "rare": 0.0,
                "epic": 0.0,
                "legendary": 0.0,
                "mythical": 0.0,
                "event": 0.0,
                "mutated": 0.1,
                "insane": 100000.0,
                "master": 0.0
            },
            "pro_bait": {
                "normal": 1.2,
                "uncommon": 0.1,
                "rare": 0.3,
                "epic": 0.05,
                "legendary": 0.02,
                "mythical": 0.01,
                "event": 0.1,
                "mutated": 0.0,
                "insane": 0.0,
                "master": 0.0
            },
            # Default rates for unknown bait
            "default": {
                "normal": 1.0,
                "uncommon": 0.05,
                "rare": 0.1,
                "epic": 0.05,
                "legendary": 0.02,
                "mythical": 0.01,
                "event": 0.0,
                "mutated": 0.0,
                "insane": 0.0,
                "master": 0.0
            }
        }
        
        return bait_rates.get(bait_id, bait_rates["default"])

    @commands.command(name="fish", aliases=["fishing", 'fs'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def fish(self, ctx):
        """Go fishing using your active rod and bait"""
        # Get user data
        user_data = await db.db.users.find_one({"_id": str(ctx.author.id)})
        
        if not user_data:
            return await ctx.reply("❌ User data not found!")
        
        # Get rods - check both possible fields
        rods = user_data.get("rods", []) or user_data.get("fishing_rods", [])
        if not rods:
            embed = discord.Embed(
                title="🎣 First Time Fishing",
                description="You need a fishing rod to start! Buy one from `.shop rod`",
                color=discord.Color.blue()
            )
            return await ctx.reply(embed=embed)
        
        # Get all available bait
        all_bait = self.get_all_bait(user_data)
        if not all_bait:
            return await ctx.reply("❌ You need bait to go fishing! Buy some from `.shop bait`")
        
        # Get active rod or default to first rod
        active_rod_id = user_data.get("active_rod")
        if active_rod_id:
            rod = next((r for r in rods if r.get("_id") == active_rod_id), None)
        else:
            rod = rods[0]
            active_rod_id = rod.get("_id")
            await db.db.users.update_one(
                {"_id": str(ctx.author.id)},
                {"$set": {"active_rod": active_rod_id}}
            )
        
        if not rod:
            return await ctx.reply("❌ Your active rod is no longer available!")
        
        # Get active bait or use first available
        active_bait_id = user_data.get("active_bait")
        current_bait = None
        
        if active_bait_id:
            current_bait = next((b for b in all_bait if b["_id"] == active_bait_id), None)
        
        if not current_bait:
            current_bait = all_bait[0]  # Use first available bait
        
        bait_id = current_bait["_id"]
        if not bait_id:
            return await ctx.reply("❌ Invalid bait configuration!")
        
        # Remove bait
        if not await self.remove_bait_improved(ctx.author.id, bait_id):
            return await ctx.reply("❌ Failed to use bait!")
        
        # Get catch rates for this bait
        bait_catch_rates = current_bait.get("catch_rates", {})
        if not bait_catch_rates:
            bait_catch_rates = self.get_bait_catch_rates(bait_id)
        
        # Calculate catch chances
        base_chances = {
            "normal": 0.7 * bait_catch_rates.get("normal", 1.0),
            "uncommon": 0.5 * bait_catch_rates.get("uncommon", 0.05),
            "rare": 0.3 * bait_catch_rates.get("rare", 0.1),
            "epic": 0.15 * bait_catch_rates.get("epic", 0.05),
            "legendary": 0.08 * bait_catch_rates.get("legendary", 0.02),
            "mythical": 0.05 * bait_catch_rates.get("mythical", 0.01),
            "event": 0.1 * bait_catch_rates.get("event", 0.0),
            "mutated": 0.03 * bait_catch_rates.get("mutated", 0.0),
            "insane": 0.005 * bait_catch_rates.get("insane", 0.0),
            "master": 0.001 * bait_catch_rates.get("master", 0.0)
        }
        
        # Apply rod multiplier
        rod_mult = rod.get("multiplier", 1.0)
        if isinstance(rod_mult, dict) and rod_mult.get("$numberInt"):
            rod_mult = int(rod_mult["$numberInt"])
        
        chances = {k: v * rod_mult for k, v in base_chances.items()}
        
        # Normalize chances if total > 1
        total = sum(chances.values())
        if total > 1.0:
            chances = {k: v/total for k, v in chances.items()}
        
        # Add base chance for normal fish if no other fish would be caught
        if total < 0.5:
            chances["normal"] = max(chances["normal"], 0.5)
        
        # Determine catch
        roll = random.random()
        cumulative = 0
        caught_type = "normal"
        
        # Sort by rarity (rarest first) for proper probability distribution
        rarity_order = ["master", "insane", "mythical", "legendary", "epic", "rare", "event", "mutated", "uncommon", "normal"]
        
        for fish_type in rarity_order:
            if fish_type in chances:
                cumulative += chances[fish_type]
                if roll <= cumulative:
                    caught_type = fish_type
                    break
        
        # Value ranges for different fish types
        value_range = {
            "normal": (10, 100),
            "uncommon": (50, 200),
            "rare": (100, 500),
            "epic": (200, 1000),
            "legendary": (500, 2000),
            "mythical": (1000, 5000),
            "event": (500, 10000),
            "mutated": (2000, 10000),
            "insane": (5000, 200000),
            "master": (100000, 10000000)
        }[caught_type]
        
        fish = {
            "id": str(uuid.uuid4()),
            "type": caught_type,
            "name": f"{caught_type.title()} Fish",
            "value": random.randint(*value_range),
            "caught_at": datetime.datetime.now().isoformat(),
            "bait_used": bait_id,
            "rod_used": active_rod_id
        }
        
        if await db.add_fish(ctx.author.id, fish):
            embed = discord.Embed(
                title="🎣 Caught a Fish!",
                description=f"You caught a **{fish['name']}**!\nValue: **{fish['value']}** {self.currency}",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="🪱 Bait Used",
                value=current_bait["name"],
                inline=True
            )
            
            embed.add_field(
                name="🎣 Rod Used", 
                value=rod["name"],
                inline=True
            )
            
            if caught_type in ["rare", "epic", "legendary", "mythical", "event", "mutated", "insane", "master"]:
                embed.set_footer(text="Wow! That's a special catch!")
                embed.color = discord.Color.gold()
            
            await ctx.reply(embed=embed)
        else:
            await ctx.reply("❌ Failed to store your catch!")

    async def remove_bait_improved(self, user_id: int, bait_id: str) -> bool:
        """Improved bait removal that handles all data structures"""
        try:
            user_data = await db.db.users.find_one({"_id": str(user_id)})
            if not user_data:
                return False
            
            # Try to remove from inventory.bait structure
            inventory_path = f"inventory.bait.{bait_id}"
            if user_data.get("inventory", {}).get("bait", {}).get(bait_id):
                current_amount = user_data["inventory"]["bait"][bait_id]
                if isinstance(current_amount, dict) and current_amount.get("$numberInt"):
                    amount = int(current_amount["$numberInt"])
                    if amount > 1:
                        # Decrease amount
                        result = await db.db.users.update_one(
                            {"_id": str(user_id)},
                            {"$set": {inventory_path: {"$numberInt": str(amount - 1)}}}
                        )
                    else:
                        # Remove completely
                        result = await db.db.users.update_one(
                            {"_id": str(user_id)},
                            {"$unset": {inventory_path: ""}}
                        )
                    return result.modified_count > 0
            
            # Try to remove from fishing_bait array
            result = await db.db.users.update_one(
                {"_id": str(user_id), "fishing_bait.id": bait_id},
                {"$inc": {"fishing_bait.$.amount": -1}}
            )
            
            if result.modified_count > 0:
                # Remove bait items with amount <= 0
                await db.db.users.update_one(
                    {"_id": str(user_id)},
                    {"$pull": {"fishing_bait": {"amount": {"$lte": 0}}}}
                )
                return True
            
            # Try to remove from bait array (if it exists)
            result = await db.db.users.update_one(
                {"_id": str(user_id), "bait._id": bait_id},
                {"$inc": {"bait.$.amount": -1}}
            )
            
            if result.modified_count > 0:
                # Remove bait items with amount <= 0
                await db.db.users.update_one(
                    {"_id": str(user_id)},
                    {"$pull": {"bait": {"amount": {"$lte": 0}}}}
                )
                return True
            
            return False
            
        except Exception as e:
            print(f"Error removing bait: {e}")
            return False

    @commands.command(name="fishinv", aliases=["finv", 'fi'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def fish_inventory(self, ctx):
        """View your fishing inventory"""
        user_data = await db.db.users.find_one({"_id": str(ctx.author.id)})
        if not user_data:
            return await ctx.reply("❌ User data not found!")
        
        fishing_items = await db.get_fishing_items(ctx.author.id)
        fish = await db.get_fish(ctx.author.id)
        active_gear = await db.get_active_fishing_gear(ctx.author.id)
        
        # Get all bait using improved method
        all_bait = self.get_all_bait(user_data)
        
        pages = []
        
        # Equipment page with active gear
        equip_embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Fishing Inventory",
            color=discord.Color.blue()
        )
        
        # Active gear section
        active_section = ""
        
        # Show active rod if available
        active_rod = next((r for r in fishing_items["rods"] if r["_id"] == active_gear.get("rod")), None)
        if active_rod:
            active_section += f"**🎣 Active Rod:** {active_rod['name']} ({active_rod['multiplier']}x)\n"
        else:
            active_section += "**🎣 Active Rod:** None\n"
        
        # Show active bait if available
        active_bait_id = user_data.get("active_bait")
        active_bait = next((b for b in all_bait if b["_id"] == active_bait_id), None) if active_bait_id else None
        if active_bait:
            active_section += f"**🪱 Active Bait:** {active_bait['name']} (x{active_bait['amount']})\n"
        elif all_bait:
            active_section += f"**🪱 Active Bait:** {all_bait[0]['name']} (x{all_bait[0]['amount']}) [Auto-selected]\n"
        else:
            active_section += "**🪱 Active Bait:** None\n"
        
        equip_embed.add_field(
            name="⚡ Active Gear",
            value=active_section,
            inline=False
        )
        
        # List all rods (limited to 3 on first page)
        rods_text = ""
        for rod in fishing_items["rods"][:3]:
            active_status = " (Active)" if rod["_id"] == active_gear.get("rod") else ""
            rods_text += f"• {rod['name']}{active_status} ({rod['multiplier']}x)\n"
        
        if len(fishing_items["rods"]) > 3:
            rods_text += f"\n*+{len(fishing_items['rods']) - 3} more rods...*"
        
        equip_embed.add_field(
            name="🎣 Fishing Rods",
            value=rods_text or "No rods",
            inline=True
        )
        
        # List all bait (limited to 3 on first page)
        bait_text = ""
        for bait in all_bait[:3]:
            active_status = " (Active)" if bait["_id"] == active_bait_id else ""
            bait_text += f"• {bait['name']}{active_status} (x{bait['amount']})\n"
        
        if len(all_bait) > 3:
            bait_text += f"\n*+{len(all_bait) - 3} more bait...*"
        
        equip_embed.add_field(
            name="🪱 Bait",
            value=bait_text or "No bait",
            inline=True
        )
        
        equip_embed.set_footer(text="Page 1 - Use the buttons below to navigate")
        pages.append(equip_embed)
        
        # Rest of the inventory pages (fish, detailed views, etc.)
        # ... (keeping the rest of the original fishinv code)
        
        class InventoryView(discord.ui.View):
            def __init__(self, pages, author, timeout=60):
                super().__init__(timeout=timeout)
                self.pages = pages
                self.author = author
                self.current_page = 0
        
        view = InventoryView(pages, ctx.author)
        await ctx.reply(embed=pages[0], view=view)

    @commands.command(name="sellfish", aliases=["sellf", 'sell_fish', 'sf'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def sellfish(self, ctx, fish_id: str = "all"):
        """Sell fish from your inventory"""
        fish = await db.get_fish(ctx.author.id)
        if not fish:
            return await ctx.reply("You don't have any fish to sell!")
            
        if fish_id.lower() == "all":
            total_value = sum(f["value"] for f in fish)
            if await db.update_balance(ctx.author.id, total_value):
                await db.clear_fish(ctx.author.id)
                embed = discord.Embed(
                    title="🐟 Fish Sold!",
                    description=f"Sold {len(fish)} fish for **{total_value}** {self.currency}",
                    color=discord.Color.green()
                )
                return await ctx.reply(embed=embed)
            await ctx.reply("❌ Failed to sell fish!")
        else:
            fish_to_sell = next((f for f in fish if f["id"] == fish_id), None)
            if not fish_to_sell:
                return await ctx.reply("❌ Fish not found in your inventory!")
                
            if await db.update_balance(ctx.author.id, fish_to_sell["value"]):
                await db.remove_fish(ctx.author.id, fish_id)
                embed = discord.Embed(
                    title="🐟 Fish Sold!",
                    description=f"Sold {fish_to_sell['name']} for **{fish_to_sell['value']}** {self.currency}",
                    color=discord.Color.green()
                )
                return await ctx.reply(embed=embed)
            await ctx.reply("❌ Failed to sell fish!")

    @commands.command(name="rod", aliases=["selectrod", "changerod"])
    async def select_rod(self, ctx, rod_id: str = None):
        """Select or view your active fishing rod"""
        fishing_items = await db.get_fishing_items(ctx.author.id)
        
        if not fishing_items["rods"]:
            return await ctx.reply("You don't have any fishing rods! Get one from the shop.")
        
        active_gear = await db.get_active_fishing_gear(ctx.author.id)
        
        if not rod_id:
            # Show list of rods with active one marked
            embed = discord.Embed(
                title="🎣 Your Fishing Rods",
                description="Select a rod using `.rod <id>`",
                color=discord.Color.blue()
            )
            
            for rod in fishing_items["rods"]:
                status = "✅" if rod["_id"] == active_gear.get("rod") else ""
                embed.add_field(
                    name=f"{status} {rod['name']} (ID: {rod['_id']})",
                    value=f"Multiplier: {rod['multiplier']}x\n{rod.get('description', '')}",
                    inline=False
                )
            
            return await ctx.reply(embed=embed)
        
        # Try to set active rod
        if await db.set_active_rod(ctx.author.id, rod_id):
            rod = next((r for r in fishing_items["rods"] if r["_id"] == rod_id), None)
            if rod:
                await ctx.reply(f"🎣 Successfully set **{rod['name']}** as your active fishing rod!")
        else:
            await ctx.reply("❌ Couldn't find that fishing rod in your inventory!")

    @commands.command(name="bait", aliases=["selectbait", "changebait"])
    async def select_bait(self, ctx, bait_id: str = None):
        """Select or view your active bait"""
        user_data = await db.db.users.find_one({"_id": str(ctx.author.id)})
        if not user_data:
            return await ctx.reply("❌ User data not found!")
        
        all_bait = self.get_all_bait(user_data)
        
        if not all_bait:
            return await ctx.reply("You don't have any bait! Get some from the shop.")
        
        active_bait_id = user_data.get("active_bait")
        
        if not bait_id:
            # Show list of bait with active one marked
            embed = discord.Embed(
                title="🪱 Your Bait",
                description="Select bait using `.bait <id>`",
                color=discord.Color.blue()
            )
            
            for bait in all_bait:
                status = "✅" if bait["_id"] == active_bait_id else ""
                embed.add_field(
                    name=f"{status} {bait['name']} (ID: {bait['_id']}) - x{bait['amount']}",
                    value=f"{bait.get('description', 'No description available')}",
                    inline=False
                )
            
            return await ctx.reply(embed=embed)
        
        # Try to set active bait
        bait_to_set = next((b for b in all_bait if b["_id"] == bait_id), None)
        if bait_to_set:
            await db.db.users.update_one(
                {"_id": str(ctx.author.id)},
                {"$set": {"active_bait": bait_id}}
            )
            await ctx.reply(f"🪱 Successfully set **{bait_to_set['name']}** as your active bait!")
        else:
            await ctx.reply("❌ Couldn't find that bait in your inventory!")

    @commands.command(name="migrate", aliases=["migrate_fish"])
    @commands.is_owner()
    async def migrate_fish(self, ctx):
        await db.migrate_to_standard_ids()
        await ctx.reply("Migration complete!")

async def setup(bot):
    await bot.add_cog(Fishing(bot))