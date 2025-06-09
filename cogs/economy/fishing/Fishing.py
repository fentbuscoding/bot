# hey! if you see this, it means the code is being loaded correctly!
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
        
        # Define rod and bait data (this should eventually come from your database)
        self.rod_data = {
            "basic_rod": {"name": "Basic Rod", "multiplier": 1.0, "description": "A simple fishing rod"},
            "pro_rod": {"name": "Pro Rod", "multiplier": 1.5, "description": "A professional fishing rod"},
            "master_rod": {"name": "Master Rod", "multiplier": 2.0, "description": "A master craftsman's rod"},
            # Add more rods as needed
        }
        
        self.bait_data = {
            "beginner_bait": {
                "name": "Beginner Bait", 
                "description": "Basic worms for catching fish",
                "catch_rates": {
                    "normal": 0.7, "uncommon": 0.2, "rare": 0.08, "epic": 0.02,
                    "legendary": 0.0, "mythical": 0.0, "event": 0.0, "mutated": 0.0,
                    "insane": 0.0, "master": 0.0
                }
            },
            "pro_bait": {  # Added this missing bait type
                "name": "Pro Bait",
                "description": "Professional grade bait for better catches",
                "catch_rates": {
                    "normal": 0.4, "uncommon": 0.3, "rare": 0.2, "epic": 0.08,
                    "legendary": 0.02, "mythical": 0.0, "event": 0.0, "mutated": 0.0,
                    "insane": 0.0, "master": 0.0
                }
            },
            "advanced_bait": {
                "name": "Advanced Bait",
                "description": "Better bait for better catches",
                "catch_rates": {
                    "normal": 0.5, "uncommon": 0.3, "rare": 0.15, "epic": 0.05,
                    "legendary": 0.0, "mythical": 0.0, "event": 0.0, "mutated": 0.0,
                    "insane": 0.0, "master": 0.0
                }
            },
            "master_bait": {
                "name": "Master Bait",
                "description": "The finest bait for legendary catches",
                "catch_rates": {
                    "normal": 0.3, "uncommon": 0.25, "rare": 0.2, "epic": 0.15,
                    "legendary": 0.08, "mythical": 0.02, "event": 0.0, "mutated": 0.0,
                    "insane": 0.0, "master": 0.0
                }
            },
            # Add more bait types as needed
        }
    async def cog_check(self, ctx):
        if ctx.channel.id in self.blocked_channels and not ctx.author.guild_permissions.administrator:
            await ctx.reply(
                random.choice([f"❌ Economy commands are disabled in this channel. "
                f"Please use them in another channel.",
                "<#1314685928614264852> is a good place for that."])
            )
            return False
        return True

    async def get_user_inventory(self, user_id: int):
        """Get user's inventory from database"""
        try:
            user_data = await db.db.users.find_one({"_id": str(user_id)})
            if not user_data:
                return None
            return user_data.get("inventory", {})
        except Exception as e:
            self.logger.error(f"Error getting user inventory: {e}")
            return None

    async def get_user_rods(self, user_id: int):
        """Get user's rods with full data"""
        inventory = await self.get_user_inventory(user_id)
        if not inventory:
            return []
        
        rod_inventory = inventory.get("rod", {})
        rods = []
        
        for rod_id, quantity in rod_inventory.items():
            if quantity > 0 and rod_id in self.rod_data:
                rod_info = self.rod_data[rod_id].copy()
                rod_info["_id"] = rod_id
                rod_info["quantity"] = quantity
                rods.append(rod_info)
        
        return rods

    async def get_user_bait(self, user_id: int):
        """Get user's bait with full data"""
        inventory = await self.get_user_inventory(user_id)
        if not inventory:
            return []
        
        bait_inventory = inventory.get("bait", {})
        bait = []
        
        for bait_id, quantity in bait_inventory.items():
            if quantity > 0 and bait_id in self.bait_data:
                bait_info = self.bait_data[bait_id].copy()
                bait_info["_id"] = bait_id
                bait_info["amount"] = quantity
                bait.append(bait_info)
        
        return bait

    async def remove_bait(self, user_id: int, bait_id: str) -> bool:
        """Remove one bait from user's inventory"""
        try:
            result = await db.db.users.update_one(
                {"_id": str(user_id), f"inventory.bait.{bait_id}": {"$gt": 0}},
                {"$inc": {f"inventory.bait.{bait_id}": -1}}
            )
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"Error removing bait: {e}")
            return False

    @commands.command(name="fish", aliases=["fishing", 'fs'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def fish(self, ctx):
        """Go fishing using your active rod and bait"""
        try:
            rods = await self.get_user_rods(ctx.author.id)
            bait = await self.get_user_bait(ctx.author.id)
            
            if not rods:
                embed = discord.Embed(
                    title="🎣 First Time Fishing",
                    description="You need a fishing rod to start! Buy one from `.shop rod`",
                    color=discord.Color.blue()
                )
                return await ctx.reply(embed=embed)
            
            if not bait:
                return await ctx.reply("❌ You need bait to go fishing! Buy some from `.shop bait`")
            
            # Get active rod or use first available
            active_gear = await db.get_active_fishing_gear(ctx.author.id)
            active_rod_id = active_gear.get("rod") if active_gear else None
            
            if active_rod_id:
                rod = next((r for r in rods if r.get("_id") == active_rod_id), None)
            else:
                rod = rods[0]
                active_rod_id = rod.get("_id")
                await self.set_active_rod_manual(ctx.author.id, active_rod_id)
            
            if not rod:
                return await ctx.reply("❌ Your active rod is no longer available!")
            
            # Use first available bait
            current_bait = bait[0]
            bait_id = current_bait.get("_id")
            
            # Remove bait
            if not await self.remove_bait(ctx.author.id, bait_id):
                return await ctx.reply("❌ Failed to use bait or you're out of bait!")
            
            # Calculate catch chances
            bait_rates = current_bait.get("catch_rates", {})
            base_chances = {
                "normal": bait_rates.get("normal", 0.7),
                "uncommon": bait_rates.get("uncommon", 0.05),
                "rare": bait_rates.get("rare", 0.1),
                "epic": bait_rates.get("epic", 0.05),
                "legendary": bait_rates.get("legendary", 0.02),
                "mythical": bait_rates.get("mythical", 0.01),
                "event": bait_rates.get("event", 0.0),
                "mutated": bait_rates.get("mutated", 0.0),
                "insane": bait_rates.get("insane", 0.0),
                "master": bait_rates.get("master", 0.0)
            }
            
            rod_mult = rod.get("multiplier", 1.0)
            chances = {k: v * rod_mult for k, v in base_chances.items()}
            
            # Normalize chances
            total = sum(chances.values())
            if total > 0:
                chances = {k: v/total for k, v in chances.items()}
            
            # Determine catch
            roll = random.random()
            cumulative = 0
            caught_type = "normal"
            
            for fish_type, chance in chances.items():
                cumulative += chance
                if roll <= cumulative:
                    caught_type = fish_type
                    break
                    
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
            }.get(caught_type, (10, 100))
            
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
                
                if caught_type in ["rare", "epic", "legendary", "mythical", "event", "mutated", "insane", "master"]:
                    embed.set_footer(text="Wow! That's a special catch!")
                    embed.color = discord.Color.gold()
                
                await ctx.reply(embed=embed)
            else:
                await ctx.reply("❌ Failed to store your catch!")
                
        except Exception as e:
            self.logger.error(f"Fishing error: {e}")
            await ctx.reply("❌ An error occurred while fishing!")

    @commands.command(name="fishinv", aliases=["finv", 'fi'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def fish_inventory(self, ctx):
        """View your fishing inventory"""
        rods = await self.get_user_rods(ctx.author.id)
        bait = await self.get_user_bait(ctx.author.id)
        fish = await db.get_fish(ctx.author.id)
        active_gear = await db.get_active_fishing_gear(ctx.author.id)
        
        pages = []
        
        # Equipment page with active gear
        equip_embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Fishing Inventory",
            color=discord.Color.blue()
        )
        
        # Active gear section
        active_section = ""
        
        # Show active rod if available
        active_rod = next((r for r in rods if r["_id"] == active_gear.get("rod")), None)
        if active_rod:
            active_section += f"**🎣 Active Rod:** {active_rod['name']} ({active_rod['multiplier']}x)\n"
        else:
            active_section += "**🎣 Active Rod:** None\n"
        
        # Show active bait if available
        active_bait = next((b for b in bait if b["_id"] == active_gear.get("bait")), None)
        if active_bait:
            active_section += f"**🪱 Active Bait:** {active_bait['name']} (x{active_bait.get('amount', 1)})\n"
        else:
            active_section += "**🪱 Active Bait:** None\n"
        
        equip_embed.add_field(
            name="⚡ Active Gear",
            value=active_section,
            inline=False
        )
        
        # List all rods
        rods_text = ""
        for rod in rods:
            active_status = " (Active)" if rod["_id"] == active_gear.get("rod") else ""
            rods_text += f"• {rod['name']}{active_status} ({rod['multiplier']}x)\n"
        
        equip_embed.add_field(
            name="🎣 Fishing Rods",
            value=rods_text or "No rods",
            inline=True
        )
        
        # List all bait
        bait_text = ""
        for b in bait:
            active_status = " (Active)" if b["_id"] == active_gear.get("bait") else ""
            bait_text += f"• {b['name']}{active_status} (x{b.get('amount', 1)})\n"
        
        equip_embed.add_field(
            name="🪱 Bait",
            value=bait_text or "No bait",
            inline=True
        )
        
        equip_embed.set_footer(text="Page 1 - Use the buttons below to navigate")
        pages.append(equip_embed)
        
        # Fish collection pages
        if fish:
            fish_by_type = {}
            for f in fish:
                fish_by_type.setdefault(f["type"], []).append(f)
                
            for fish_type, fish_list in fish_by_type.items():
                embed = discord.Embed(
                    title=f"🐟 {fish_type.title()} Collection",
                    color=discord.Color.blue()
                )
                
                total_value = sum(f["value"] for f in fish_list)
                embed.description = f"Total Value: **{total_value}** {self.currency}\nAmount: {len(fish_list)}"
                
                for fish in sorted(fish_list, key=lambda x: x["value"], reverse=True)[:10]:
                    embed.add_field(
                        name=f"{fish['name']} ({fish['value']} {self.currency})",
                        value=f"Caught: {fish['caught_at'].split('T')[0]}",
                        inline=True
                    )
                    
                pages.append(embed)
        else:
            pages.append(discord.Embed(
                title="🐟 Fish Collection",
                description="You haven't caught any fish yet!\nUse `.fish` to start fishing.",
                color=discord.Color.blue()
            ))
        
        class InventoryView(discord.ui.View):
            def __init__(self, pages, author, timeout=60):
                super().__init__(timeout=timeout)
                self.pages = pages
                self.author = author
                self.current_page = 0
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
                    await interaction.response.send_message("This isn't your inventory!", ephemeral=True)
                    return False
                return True
                    
            async def navigate(self, interaction: discord.Interaction, action: str):
                if action == "first":
                    self.current_page = 0
                elif action == "prev":
                    self.current_page -= 1
                elif action == "next":
                    self.current_page += 1
                elif action == "last":
                    self.current_page = len(self.pages) - 1
                
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
        await ctx.reply(embed=pages[0], view=view)

    @commands.command(hidden=True, description="Debugging command to make sure that rods and bait work correctly, please ignore this command if your baits and rod are working correctly.")
    async def fishing_debug(self, ctx):
        """Debug fishing gear"""
        rods = await self.get_user_rods(ctx.author.id)
        bait = await self.get_user_bait(ctx.author.id)
        embed = discord.Embed(title="Fishing Debug", color=0x00ff00)
        embed.add_field(name="Rods", value=str(rods), inline=False)
        embed.add_field(name="Bait", value=str(bait), inline=False)
        await ctx.send(embed=embed)

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

    async def set_active_rod_manual(self, user_id: int, rod_id: str) -> bool:
        """Manually set active rod in database"""
        try:
            result = await db.db.users.update_one(
                {"_id": str(user_id)},
                {"$set": {"active_fishing_gear.rod": rod_id}},
                upsert=True
            )
            return True
        except Exception as e:
            self.logger.error(f"Error setting active rod: {e}")
            return False

    async def set_active_bait_manual(self, user_id: int, bait_id: str) -> bool:
        """Manually set active bait in database"""
        try:
            result = await db.db.users.update_one(
                {"_id": str(user_id)},
                {"$set": {"active_fishing_gear.bait": bait_id}},
                upsert=True
            )
            return True
        except Exception as e:
            self.logger.error(f"Error setting active bait: {e}")
            return False

    @commands.command(name="rod", aliases=["selectrod", "changerod"])
    async def select_rod(self, ctx, rod_id: str = None):
        """Select or view your active fishing rod"""
        rods = await self.get_user_rods(ctx.author.id)
        
        if not rods:
            return await ctx.reply("You don't have any fishing rods! Get one from the shop.")
        
        active_gear = await db.get_active_fishing_gear(ctx.author.id)
        
        if not rod_id:
            # Show list of rods with active one marked
            embed = discord.Embed(
                title="🎣 Your Fishing Rods",
                description="Select a rod using `.rod <id>`",
                color=discord.Color.blue()
            )
            
            for rod in rods:
                status = "✅" if rod["_id"] == active_gear.get("rod") else ""
                embed.add_field(
                    name=f"{status} {rod['name']} (ID: {rod['_id']})",
                    value=f"Multiplier: {rod['multiplier']}x\n{rod.get('description', '')}",
                    inline=False
                )
            
            return await ctx.reply(embed=embed)
        
        # Try to set active rod
        rod = next((r for r in rods if r["_id"] == rod_id), None)
        if rod:
            if await self.set_active_rod_manual(ctx.author.id, rod_id):
                await ctx.reply(f"🎣 Successfully set **{rod['name']}** as your active fishing rod!")
            else:
                await ctx.reply("❌ Failed to set active rod!")
        else:
            await ctx.reply("❌ Couldn't find that fishing rod in your inventory!")

    @commands.command(name="bait", aliases=["selectbait", "changebait"])
    async def select_bait(self, ctx, bait_id: str = None):
        """Select or view your active bait"""
        bait = await self.get_user_bait(ctx.author.id)
        
        if not bait:
            return await ctx.reply("You don't have any bait! Get some from the shop.")
        
        active_gear = await db.get_active_fishing_gear(ctx.author.id)
        
        if not bait_id:
            # Show list of bait with active one marked
            embed = discord.Embed(
                title="🪱 Your Bait",
                description="Select bait using `.bait <id>`",
                color=discord.Color.blue()
            )
            
            for b in bait:
                status = "✅" if b["_id"] == active_gear.get("bait") else ""
                embed.add_field(
                    name=f"{status} {b['name']} (ID: {b['_id']}) - x{b.get('amount', 1)}",
                    value=f"{b.get('description', '')}",
                    inline=False
                )
            
            return await ctx.reply(embed=embed)
        
        # Try to set active bait
        selected_bait = next((b for b in bait if b["_id"] == bait_id), None)
        if selected_bait:
            if await self.set_active_bait_manual(ctx.author.id, bait_id):
                await ctx.reply(f"🪱 Successfully set **{selected_bait['name']}** as your active bait!")
            else:
                await ctx.reply("❌ Failed to set active bait!")
        else:
            await ctx.reply("❌ Couldn't find that bait in your inventory!")

    @commands.command(name="migrate", aliases=["migrate_fish"])
    @commands.is_owner()
    async def migrate_fish(self, ctx):
        await db.migrate_to_standard_ids()
        await ctx.reply("Migration complete!")

async def setup(bot):
    await bot.add_cog(Fishing(bot))
