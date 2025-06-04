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
        
        # Get bait - check both possible fields
        bait = user_data.get("bait", []) or user_data.get("fishing_bait", [])
        if not bait:
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
        
        # Use first available bait
        current_bait = bait[0]
        bait_id = current_bait.get("_id", current_bait.get("id"))
        if not bait_id:
            return await ctx.reply("❌ Invalid bait configuration!")
        
        # Remove bait (implemented below)
        if not await self.remove_bait(ctx.author.id, bait_id):
            return await ctx.reply("❌ Failed to use bait!")
        
        # Calculate catch chances
        base_chances = {
            "normal": 0.7 * current_bait.get("catch_rates", {}).get("normal", 0.0),
            "uncommon": 0.5 * current_bait.get("catch_rates", {}).get("uncommon", 0.05),
            "rare": 0.2 * current_bait.get("catch_rates", {}).get("rare", 0.1),
            "epic": 0.1 * current_bait.get("catch_rates", {}).get("epic", 0.05),
            "legendary": 0.05 * current_bait.get("catch_rates", {}).get("legendary", 0.02),
            "mythical": 0.03 * current_bait.get("catch_rates", {}).get("mythical", 0.01),
            "event": 0.08 * current_bait.get("catch_rates", {}).get("event", 0.0),
            "mutated": 0.02 * current_bait.get("catch_rates", {}).get("mutated", 0.0),
            "insane": 0.005 * current_bait.get("catch_rates", {}).get("insane", 0.0),
            "master": 0.0001 * current_bait.get("catch_rates", {}).get("master", 0.0)
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
            
            if caught_type in ["rare", "event", "mutated"]:
                embed.set_footer(text="Wow! That's a special catch!")
                embed.color = discord.Color.gold()
            
            await ctx.reply(embed=embed)
        else:
            await ctx.reply("❌ Failed to store your catch!")

    async def remove_bait(self, user_id: int, bait_id: str) -> bool:
        """Remove bait from user's inventory"""
        try:
            # First check the bait field (new structure)
            result = await db.db.users.update_one(
                {"_id": str(user_id), "bait._id": bait_id},
                {"$inc": {"bait.$.amount": -1}}
            )
            
            if result.modified_count == 0:
                # If not found in bait, check fishing_bait (old structure)
                result = await db.db.users.update_one(
                    {"_id": str(user_id), "fishing_bait.id": bait_id},
                    {"$inc": {"fishing_bait.$.amount": -1}}
                )
            
            # Remove bait items with amount <= 0
            await db.db.users.update_many(
                {"_id": str(user_id)},
                {
                    "$pull": {
                        "bait": {"amount": {"$lte": 0}},
                        "fishing_bait": {"amount": {"$lte": 0}}
                    }
                }
            )
            
            return result.modified_count > 0
        except Exception as e:
            print(f"Error removing bait: {e}")
            return False

    @commands.command(name="fishinv", aliases=["finv", 'fi'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def fish_inventory(self, ctx):
        """View your fishing inventory"""
        fishing_items = await db.get_fishing_items(ctx.author.id)
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
        active_rod = next((r for r in fishing_items["rods"] if r["_id"] == active_gear.get("rod")), None)
        if active_rod:
            active_section += f"**🎣 Active Rod:** {active_rod['name']} ({active_rod['multiplier']}x)\n"
        else:
            active_section += "**🎣 Active Rod:** None\n"
        
        # Show active bait if available
        active_bait = next((b for b in fishing_items["bait"] if b["_id"] == active_gear.get("bait")), None)
        if active_bait:
            active_section += f"**🪱 Active Bait:** {active_bait['name']} (x{active_bait.get('amount', 1)})\n"
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
        for bait in fishing_items["bait"][:3]:
            active_status = " (Active)" if bait["_id"] == active_gear.get("bait") else ""
            bait_text += f"• {bait['name']}{active_status} (x{bait.get('amount', 1)})\n"
        
        if len(fishing_items["bait"]) > 3:
            bait_text += f"\n*+{len(fishing_items['bait']) - 3} more bait...*"
        
        equip_embed.add_field(
            name="🪱 Bait",
            value=bait_text or "No bait",
            inline=True
        )
        
        equip_embed.set_footer(text="Page 1 - Use the buttons below to navigate")
        pages.append(equip_embed)
        
        # Detailed rods page (if more than 3 rods)
        if len(fishing_items["rods"]) > 3:
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
        if len(fishing_items["bait"]) > 3:
            bait_embed = discord.Embed(
                title="🪱 All Bait",
                color=discord.Color.blue()
            )
            
            for bait in fishing_items["bait"]:
                active_status = " (Active)" if bait["_id"] == active_gear.get("bait") else ""
                bait_embed.add_field(
                    name=f"{bait['name']}{active_status} (x{bait.get('amount', 1)})",
                    value=bait.get('description', ''),
                    inline=False
                )
            
            pages.append(bait_embed)
        
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
        fishing_items = await db.get_fishing_items(ctx.author.id)
        
        if not fishing_items["bait"]:
            return await ctx.reply("You don't have any bait! Get some from the shop.")
        
        active_gear = await db.get_active_fishing_gear(ctx.author.id)
        
        if not bait_id:
            # Show list of bait with active one marked
            embed = discord.Embed(
                title="🪱 Your Bait",
                description="Select bait using `.bait <id>`",
                color=discord.Color.blue()
            )
            
            for bait in fishing_items["bait"]:
                status = "✅" if bait["_id"] == active_gear.get("bait") else ""
                embed.add_field(
                    name=f"{status} {bait['name']} (ID: {bait['_id']}) - x{bait.get('amount', 1)}",
                    value=f"{bait.get('description', '')}",
                    inline=False
                )
            
            return await ctx.reply(embed=embed)
        
        # Try to set active bait
        if await db.set_active_bait(ctx.author.id, bait_id):
            bait = next((b for b in fishing_items["bait"] if b["_id"] == bait_id), None)
            if bait:
                await ctx.reply(f"🪱 Successfully set **{bait['name']}** as your active bait!")
        else:
            await ctx.reply("❌ Couldn't find that bait in your inventory!")


    @commands.command(name="migrate", aliases=["migrate_fish"])
    @commands.is_owner()
    async def migrate_fish(self, ctx):
        await db.migrate_to_standard_ids()
        await ctx.reply("Migration complete!")

async def setup(bot):
    await bot.add_cog(Fishing(bot))