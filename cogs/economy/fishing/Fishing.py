

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
from utils.db import AsyncDatabase
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
        self.db = AsyncDatabase.get_instance()
    
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

    async def migrate_rods_and_bait(self):
        """Migration method to clean up rod and bait IDs"""
        try:
            print("[MIGRATION] Starting rod and bait ID migration...")
            
            # Process rods collection
            rods_collection = self.db.db.rods
            rods_cursor = rods_collection.find({})
            rods_updated = 0
            
            async for rod in rods_cursor:
                if 'id' not in rod:
                    continue
                    
                new_id = rod['id']
                if not new_id:
                    continue
                    
                # Check if document with new _id already exists
                existing = await rods_collection.find_one({"_id": new_id})
                if existing:
                    print(f"[MIGRATION] Skipping rod {new_id} - already exists with new ID")
                    continue
                    
                # Create new document with correct _id
                new_rod = {
                    "_id": new_id,
                    "name": rod.get("name", ""),
                    "price": rod.get("price", 0),
                    "description": rod.get("description", ""),
                    "multiplier": rod.get("multiplier", 1),
                    "type": rod.get("type", "rod")
                }
                
                # Insert new document
                await rods_collection.insert_one(new_rod)
                
                # Remove old document
                await rods_collection.delete_one({"_id": rod["_id"]})
                rods_updated += 1
                print(f"[MIGRATION] Updated rod: {rod['_id']} -> {new_id}")
            
            # Process bait collection
            bait_collection = self.db.db.bait
            bait_cursor = bait_collection.find({})
            bait_updated = 0
            
            async for bait in bait_cursor:
                if 'id' not in bait:
                    continue
                    
                new_id = bait['id']
                if not new_id:
                    continue
                    
                # Check if document with new _id already exists
                existing = await bait_collection.find_one({"_id": new_id})
                if existing:
                    print(f"[MIGRATION] Skipping bait {new_id} - already exists with new ID")
                    continue
                    
                # Create new document with correct _id
                new_bait = {
                    "_id": new_id,
                    "name": bait.get("name", ""),
                    "price": bait.get("price", 0),
                    "description": bait.get("description", ""),
                    "catch_rates": bait.get("catch_rates", {}),
                    "type": bait.get("type", "bait")
                }
                
                # Insert new document
                await bait_collection.insert_one(new_bait)
                
                # Remove old document
                await bait_collection.delete_one({"_id": bait["_id"]})
                bait_updated += 1
                print(f"[MIGRATION] Updated bait: {bait['_id']} -> {new_id}")
            
            print(f"[MIGRATION] Completed! Updated {rods_updated} rods and {bait_updated} bait items.")
            return {
                "rods_updated": rods_updated,
                "bait_updated": bait_updated
            }
            
        except Exception as e:
            print(f"[MIGRATION ERROR] {str(e)}")
            raise

    def get_default_catch_rates(self, bait_name):
        """Return default catch rates for determine_fish_catchdifferent bait types"""
        rates = {
            "beginner_bait": {"normal": 1.5},
            "pro_bait": {"normal": 1.2, "rare": 1.1},
            "advanced_bait": {"normal": 1.1, "rare": 1.3, "epic": 1.1},
            "insane_bait": {"normal": 0.8, "rare": 1.5, "epic": 1.3, "legendary": 1.2}
        }
        return rates.get(bait_name, {"normal": 1.0})

    @commands.command(name="fish", aliases=["fishing", 'fs'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def fish(self, ctx):
        """Go fishing using your active rod and bait"""
        try:
            user_data = await self.db.db.users.find_one({"_id": str(ctx.author.id)})
            if not user_data:
                return await ctx.reply("❌ User data not found!")

            # Check rods in inventory.rod
            rods = user_data.get("inventory", {}).get("rod", {})
            if not rods:
                return await ctx.reply("❌ You need a fishing rod! Buy one from `.shop rod`")

            # Get active rod
            active_rod = user_data.get("active_rod")
            if not active_rod or active_rod not in rods:
                active_rod = next(iter(rods.keys()), None)
                if active_rod:
                    await self.db.db.users.update_one(
                        {"_id": str(ctx.author.id)},
                        {"$set": {"active_rod": active_rod}}
                    )
                else:
                    return await ctx.reply("❌ No valid rods available!")

            # Get bait inventory
            bait_inventory = user_data.get("inventory", {}).get("bait", {})
            if not bait_inventory:
                return await ctx.reply("❌ You need bait! Buy some from `.shop bait`")

            # Get active bait
            active_bait = user_data.get("active_bait")
            if not active_bait or active_bait not in bait_inventory:
                active_bait = next(iter(bait_inventory.keys()), None)
                if active_bait:
                    await self.db.db.users.update_one(
                        {"_id": str(ctx.author.id)},
                        {"$set": {"active_bait": active_bait}}
                    )
                else:
                    return await ctx.reply("❌ No valid bait available!")

            # Verify bait amount
            if bait_inventory.get(active_bait, 0) <= 0:
                return await ctx.reply(f"❌ You're out of {active_bait.replace('_', ' ')}!")

            # Remove 1 bait
            await self.db.db.users.update_one(
                {"_id": str(ctx.author.id)},
                {"$inc": {f"inventory.bait.{active_bait}": -1}}
            )

            # Fishing logic
            caught_type = (await self.determine_fish_catch(active_bait))
            fish_value = self.calculate_fish_value(caught_type)
            
            fish = {
                "type": caught_type,
                "name": f"{caught_type.title()} Fish",
                "value": fish_value,
                "caught_at": datetime.datetime.now().isoformat(),
                "bait_used": active_bait,
                "rod_used": active_rod
            }

            if await self.db.add_fish(ctx.author.id, fish):
                embed = discord.Embed(
                    title=f"🎣 Caught a {caught_type.title()} Fish!",
                    description=f"**Value:** {fish_value} {self.currency}",
                    color=self.get_rarity_color(caught_type)
                )
                embed.add_field(name="🪱 Bait Used", value=active_bait.replace('_', ' '), inline=True)
                embed.add_field(name="🎣 Rod Used", value=active_rod.replace('_', ' '), inline=True)
                await ctx.reply(embed=embed)
            else:
                await ctx.reply("❌ Failed to store your catch!")

        except Exception as e:
            print(f"[FISHING ERROR] {type(e).__name__}: {str(e)}")
            await ctx.reply("❌ An error occurred while fishing. Please try again later.")

    @commands.command(name="rod", aliases=["selectrod", "changerod"])
    async def select_rod(self, ctx, rod_name: str = None):
        """Select or view your active fishing rod"""
        try:
            user_data = await self.db.db.users.find_one({"_id": str(ctx.author.id)})
            if not user_data:
                return await ctx.reply("❌ User data not found!")
            
            rods = user_data.get("inventory", {}).get("rod", {})
            if not rods:
                return await ctx.reply("You don't have any fishing rods! Get one from the shop.")
            
            active_gear = await self.db.get_active_fishing_gear(ctx.author.id)
            
            if not rod_name:
                embed = discord.Embed(
                    title="🎣 Your Fishing Rods",
                    description="Select a rod using `.rod <name>`",
                    color=discord.Color.blue()
                )
                
                for rod_id in rods:
                    rod_name_display = rod_id.replace("_", " ").title()
                    status = "✅" if rod_id == active_gear.get("rod") else ""
                    embed.add_field(
                        name=f"{status} {rod_name_display}",
                        value=f"Currently owned: {rods[rod_id]}",
                        inline=False
                    )
                
                return await ctx.reply(embed=embed)
            
            rod_name_clean = rod_name.lower().strip().replace(" ", "_")
            if rod_name_clean in rods:
                await self.db.db.users.update_one(
                    {"_id": str(ctx.author.id)},
                    {"$set": {"active_rod": rod_name_clean}}
                )
                await ctx.reply(f"🎣 Successfully set **{rod_name_clean.replace('_', ' ')}** as your active fishing rod!")
            else:
                await ctx.reply("❌ Couldn't find that fishing rod in your inventory!")
                
        except Exception as e:
            print(f"[ROD COMMAND ERROR] {type(e).__name__}: {str(e)}")
            await ctx.reply("❌ An error occurred while processing your request.")

    async def determine_fish_catch(self, bait_type):
        """Determine fish catch based on bait's catch rates"""
        try:
            # Get the bait's configuration from database
            bait_config = await self.db.db.bait.find_one({"_id": bait_type})
            if not bait_config:
                return "normal"  # Fallback if bait not found
            if 'insane' in bait_type.lower:
                return "insane"
            # Get the catch rates from the bait config
            catch_rates = bait_config.get("catch_rates", {})
            if not catch_rates:
                return "normal"  # Fallback if no catch rates defined
            
            # Special handling for insane_bait
            if bait_type == "insane_bait":
                # Insane bait should only catch mutated or insane fish
                roll = random.random()
                if roll < 0.9:  # 90% chance for mutated
                    return "mutated"
                else:  # 10% chance for insane
                    return "insane"
            
            # For other baits, use their configured catch rates
            total = sum(catch_rates.values())
            if total <= 0:
                return "normal"  # Fallback if all rates are zero
                
            # Normalize probabilities
            normalized = {k: v/total for k, v in catch_rates.items()}
            
            # Determine catch
            roll = random.random()
            cumulative = 0
            for fish_type, prob in normalized.items():
                cumulative += prob
                if roll <= cumulative:
                    return fish_type
                    
            return "normal"  # Fallback if something went wrong
            
        except Exception as e:
            print(f"[FISH CATCH ERROR] {str(e)}")
            return "normal"

    def calculate_fish_value(self, fish_type):
        """Calculate fish value based on type"""
        value_ranges = {
            "normal": (10, 100),
            "uncommon": (50, 200),
            "rare": (100, 500),
            "epic": (200, 1000),
            "legendary": (500, 2000),
            "mutated": (1000, 5000),
            "insane": (5000, 20000),
            "master": (100000, 5000000)
        }
        return random.randint(*value_ranges.get(fish_type, (10, 100)))

    def get_rarity_color(self, rarity):
        """Get embed color based on fish rarity"""
        colors = {
            "normal": discord.Color.blue(),
            "uncommon": discord.Color.green(),
            "rare": discord.Color.teal(),
            "epic": discord.Color.purple(),
            "legendary": discord.Color.gold(),
            "mutated": discord.Color.dark_purple(),
            "insane": discord.Color.dark_red()
        }
        return colors.get(rarity, discord.Color.blue())

    async def remove_bait_improved(self, user_id: int, bait_id: str) -> bool:
        """Improved bait removal that handles all data structures"""
        try:
            user_data = await self.db.db.users.find_one({"_id": str(user_id)})
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
                        result = await self.db.db.users.update_one(
                            {"_id": str(user_id)},
                            {"$set": {inventory_path: {"$numberInt": str(amount - 1)}}}
                        )
                    else:
                        # Remove completely
                        result = await self.db.db.users.update_one(
                            {"_id": str(user_id)},
                            {"$unset": {inventory_path: ""}}
                        )
                    return result.modified_count > 0
            
            # Try to remove from fishing_bait array
            result = await self.db.db.users.update_one(
                {"_id": str(user_id), "fishing_bait.id": bait_id},
                {"$inc": {"fishing_bait.$.amount": -1}}
            )
            
            if result.modified_count > 0:
                # Remove bait items with amount <= 0
                await self.db.db.users.update_one(
                    {"_id": str(user_id)},
                    {"$pull": {"fishing_bait": {"amount": {"$lte": 0}}}}
                )
                return True
            
            # Try to remove from bait array (if it exists)
            result = await self.db.db.users.update_one(
                {"_id": str(user_id), "bait._id": bait_id},
                {"$inc": {"bait.$.amount": -1}}
            )
            
            if result.modified_count > 0:
                # Remove bait items with amount <= 0
                await self.db.db.users.update_one(
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
        user_data = await self.db.db.users.find_one({"_id": str(ctx.author.id)})
        if not user_data:
            return await ctx.reply("❌ User data not found!")
        
        fishing_items = await self.db.get_fishing_items(ctx.author.id)
        fish = await self.db.get_fish(ctx.author.id)
        active_gear = await self.db.get_active_fishing_gear(ctx.author.id)
        
        # Get all bait
        all_bait = await self.get_all_bait(user_data)
        
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
        
        # Show active bait if available - simplified without original_id
        active_bait_id = active_gear.get("bait")
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
        
        # List all rods (simplified display)
        rods_text = ""
        for rod in fishing_items["rods"][:3]:  # Show first 3 rods
            active_status = " (Active)" if rod["_id"] == active_gear.get("rod") else ""
            rods_text += f"• {rod['name']}{active_status} ({rod['multiplier']}x)\n"
        
        if len(fishing_items["rods"]) > 3:
            rods_text += f"\n*+{len(fishing_items['rods']) - 3} more rods...*"
        
        equip_embed.add_field(
            name="🎣 Fishing Rods",
            value=rods_text or "No rods",
            inline=True
        )
        
        # List all bait (simplified display)
        bait_text = ""
        for bait in all_bait[:3]:  # Show first 3 baits
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
        print("[DEBUG] Added equipment page")
        
        # Detailed rods page (if more than 3 rods)
        if len(fishing_items["rods"]) > 3:
            print(f"[DEBUG] Creating detailed rods page with {len(fishing_items['rods'])} rods")
            rods_embed = discord.Embed(
                title="🎣 All Fishing Rods",
                color=discord.Color.blue()
            )
            
            for rod in fishing_items["rods"]:
                active_status = " (Active)" if rod["_id"] == active_gear.get("rod") else ""
                rods_embed.add_field(
                    name=f"{rod['name']}{active_status}",
                    value=f"Multiplier: {rod['multiplier']}x\n{rod.get('description', '')}",
                    inline=False
                )
            
            pages.append(rods_embed)
        
        # Detailed bait page (if more than 3 bait)
        if len(all_bait) > 3:
            print(f"[DEBUG] Creating detailed bait page with {len(all_bait)} bait types")
            bait_embed = discord.Embed(
                title="🪱 All Bait",
                color=discord.Color.blue()
            )
            
            for bait in all_bait:
                active_status = " (Active)" if bait["_id"] == active_bait_id else ""
                bait_embed.add_field(
                    name=f"{bait['name']}{active_status} (x{bait['amount']})",
                    value=bait.get('description', 'No description available'),
                    inline=False
                )
            
            pages.append(bait_embed)
        
        # Fish collection pages
        if fish:
            print(f"[DEBUG] Raw fish data: {fish}")  # Add this debug line
            fish_by_type = {}
            for f in fish:
                print(f"[DEBUG] Processing fish item: {f}")  # Debug each fish item
                if not isinstance(f, dict):
                    print(f"[WARNING] Invalid fish item (not a dict): {f}")
                    continue
                    
                fish_type = f.get("type", "unknown")
                fish_by_type.setdefault(fish_type, []).append(f)
                
            for fish_type, fish_list in fish_by_type.items():
                print(f"[DEBUG] Creating page for fish type: {fish_type}")
                embed = discord.Embed(
                    title=f"🐟 {fish_type.title()} Collection",
                    color=discord.Color.blue()
                )
                
                total_value = sum(f.get("value", 0) for f in fish_list)
                embed.description = f"Total Value: **{total_value}** {self.currency}\nAmount: {len(fish_list)}"
                
                for fish_item in sorted(fish_list, key=lambda x: x.get("value", 0), reverse=True)[:10]:
                    # Safely get all fields with defaults
                    fish_id = fish_item.get("_id", "Unknown Fish")
                    fish_value = fish_item.get("value", 0)
                    caught_date = fish_item.get("caught_at", "Unknown date")
                    if isinstance(caught_date, str) and "T" in caught_date:
                        caught_date = caught_date.split("T")[0]
                    
                    embed.add_field(
                        name=f"{fish_id} ({fish_value} {self.currency})",
                        value=f"Caught: {caught_date}",
                        inline=True
                    )
                    
                pages.append(embed)
        else:
            print("[DEBUG] No fish found, creating empty collection page")
            pages.append(discord.Embed(
                title="🐟 Fish Collection",
                description="You haven't caught any fish yet!\nUse `.fish` to start fishing.",
                color=discord.Color.blue()
            ))
        
        print(f"[DEBUG] Total pages created: {len(pages)}")
        
        class InventoryView(discord.ui.View):
            def __init__(self, pages, author, timeout=60):
                super().__init__(timeout=timeout)
                self.pages = pages
                self.author = author
                self.current_page = 0
                print(f"[DEBUG] InventoryView initialized with {len(pages)} pages")
                self.update_buttons()
                
            def update_buttons(self):
                self.clear_items()
                
                # Navigation buttons
                if len(self.pages) > 1:
                    first_button = discord.ui.Button(emoji="⏮️", style=discord.ButtonStyle.secondary, disabled=self.current_page == 0)
                    first_button.callback = self.first_page
                    self.add_item(first_button)
                    
                    prev_button = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.primary, disabled=self.current_page == 0)
                    prev_button.callback = self.prev_page
                    self.add_item(prev_button)
                    
                    self.add_item(discord.ui.Button(
                        label=f"Page {self.current_page + 1}/{len(self.pages)}",
                        style=discord.ButtonStyle.gray,
                        disabled=True
                    ))
                    
                    next_button = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.primary, disabled=self.current_page == len(self.pages) - 1)
                    next_button.callback = self.next_page
                    self.add_item(next_button)
                    
                    last_button = discord.ui.Button(emoji="⏭️", style=discord.ButtonStyle.secondary, disabled=self.current_page == len(self.pages) - 1)
                    last_button.callback = self.last_page
                    self.add_item(last_button)
            
            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                if interaction.user != self.author:
                    print(f"[DEBUG] Blocked inventory access by {interaction.user} (not owner)")
                    await interaction.response.send_message("This isn't your inventory!", ephemeral=True)
                    return False
                return True
                    
            async def navigate(self, interaction: discord.Interaction, action: str):
                print(f"[DEBUG] Navigation action: {action}")
                if action == "first":
                    self.current_page = 0
                elif action == "prev":
                    self.current_page -= 1
                elif action == "next":
                    self.current_page += 1
                elif action == "last":
                    self.current_page = len(self.pages) - 1
                
                print(f"[DEBUG] New page index: {self.current_page}")
                self.update_buttons()
                await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
            
            async def first_page(self, interaction: discord.Interaction):
                await self.navigate(interaction, "first")
            
            async def prev_page(self, interaction: discord.Interaction):
                await self.navigate(interaction, "prev")
            
            async def next_page(self, interaction: discord.Interaction):
                await self.navigate(interaction, "next")
            
            async def last_page(self, interaction: discord.Interaction):
                await self.navigate(interaction, "last")
        
        view = InventoryView(pages, ctx.author)
        print("[DEBUG] Sending inventory message...")
        await ctx.reply(embed=pages[0], view=view)
        print("[DEBUG] Inventory message sent")

    @commands.command(name="sellfish", aliases=["sellf", 'sell_fish', 'sf'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def sellfish(self, ctx, fish_id: str = "all"):
        """Sell fish from your inventory"""
        fish = await self.db.get_fish(ctx.author.id)
        if not fish:
            return await ctx.reply("You don't have any fish to sell!")
            
        if fish_id.lower() == "all":
            total_value = sum(f["value"] for f in fish)
            if await self.db.update_balance(ctx.author.id, total_value):
                await self.db.clear_fish(ctx.author.id)
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
                
            if await self.db.update_balance(ctx.author.id, fish_to_sell["value"]):
                await self.db.remove_fish(ctx.author.id, fish_id)
                embed = discord.Embed(
                    title="🐟 Fish Sold!",
                    description=f"Sold {fish_to_sell['name']} for **{fish_to_sell['value']}** {self.currency}",
                    color=discord.Color.green()
                )
                return await ctx.reply(embed=embed)
            await ctx.reply("❌ Failed to sell fish!")

    async def get_all_bait(self, user_data):
        """Get all bait with proper names"""
        bait = []
        if "inventory" in user_data and "bait" in user_data["inventory"]:
            for bait_id, amount in user_data["inventory"]["bait"].items():
                # Get bait details from database
                bait_item = await self.db.db.bait.find_one({"_id": bait_id})
                if bait_item:
                    bait.append({
                        "_id": bait_id,
                        "name": bait_item.get("name", bait_id.replace("_", " ").title()),
                        "amount": amount,
                        "description": bait_item.get("description", "")
                    })
        return sorted(bait, key=lambda x: x["name"])  # Sort alphabetically

    @commands.command(name="bait", aliases=["selectbait", "changebait"])
    async def select_bait(self, ctx, bait_name: str = None):
        """Select or view your active bait"""
        user_data = await self.db.db.users.find_one({"_id": str(ctx.author.id)})
        if not user_data:
            return await ctx.reply("❌ User data not found!")
        
        all_bait = await self.get_all_bait(user_data)
        
        if not all_bait:
            return await ctx.reply("You don't have any bait! Get some from the shop.")

        if not bait_name:
            # Show list of bait with active one marked
            embed = discord.Embed(
                title="🪱 Your Bait",
                description="Select bait using `.bait <name>`",
                color=discord.Color.blue()
            )
            
            active_bait_id = user_data.get("active_bait")
            for bait in all_bait:
                status = "✅" if bait["_id"] == active_bait_id else ""
                embed.add_field(
                    name=f"{status} {bait['name']} - x{bait['amount']}",
                    value=f"{bait.get('description', 'No description available')}",
                    inline=False
                )
            
            return await ctx.reply(embed=embed)
        
        # Fixed the unterminated string here - added missing quote after underscore
        bait_name_clean = bait_name.lower().replace("_", " ").strip()
        bait_to_set = None
        
        for bait in all_bait:
            bait_name_in_db = bait['name'].lower().replace("_", " ").strip()
            if bait_name_clean == bait_name_in_db:
                bait_to_set = bait
                break
        
        if bait_to_set:
            await self.db.db.users.update_one(
                {"_id": str(ctx.author.id)},
                {"$set": {"active_bait": bait_to_set["_id"]}}
            )
            await ctx.reply(f"🪱 Successfully set **{bait_to_set['name']}** as your active bait!")
        else:
            suggestions = []
            for bait in all_bait:
                if bait_name_clean in bait['name'].lower().replace("_", " "):
                    suggestions.append(f"`{bait['name']}`")
            
            if suggestions:
                await ctx.reply(f"❌ No exact match found. Did you mean: {', '.join(suggestions)}?")
            else:
                await ctx.reply("❌ Couldn't find that bait in your inventory!")

async def setup(bot):
    await bot.add_cog(Fishing(bot))

