from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import async_db as db
import discord
import random
import uuid
import datetime
import asyncio
import math

class AutoFishing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.currency = "<:bronkbuk:1377389238290747582>"
        
        # Autofisher configurations
        self.BASE_AUTOFISHER_PRICE = 1000
        self.AUTOFISHER_PRICE_MULTIPLIER = 2.5  # Gets expensive FAST
        self.BASE_EFFICIENCY_UPGRADE_PRICE = 500
        self.EFFICIENCY_PRICE_MULTIPLIER = 1.8
        self.BASE_FISHING_INTERVAL = 300  # 5 minutes base
        self.MAX_EFFICIENCY_LEVEL = 20
        self.MAX_AUTOFISHERS = 10
        
        # Start the autofishing loop
        self.autofishing_task = self.bot.loop.create_task(self.autofishing_loop())

    def cog_unload(self):
        """Cancel the autofishing task when cog is unloaded"""
        if hasattr(self, 'autofishing_task'):
            self.autofishing_task.cancel()

    async def autofishing_loop(self):
        """Main autofishing loop that runs continuously"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                # Get all users with autofishers
                users_with_autofishers = await db.get_all_autofisher_users()
                
                for user_id in users_with_autofishers:
                    try:
                        await self.process_user_autofishing(user_id)
                    except Exception as e:
                        self.logger.error(f"Error processing autofishing for user {user_id}: {e}")
                
                # Wait 30 seconds before next cycle
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Error in autofishing loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def process_user_autofishing(self, user_id):
        """Process autofishing for a single user"""
        autofisher_data = await db.get_autofisher_data(user_id)
        if not autofisher_data or autofisher_data["count"] == 0:
            return
            
        fishing_items = await db.get_fishing_items(user_id)
        if not fishing_items["rods"]:
            return  # No rods, can't autofish
            
        current_time = datetime.datetime.utcnow()
        last_fish_time = datetime.datetime.fromisoformat(autofisher_data.get("last_fish_time", "2000-01-01T00:00:00"))
        
        # Calculate fishing interval based on efficiency level
        efficiency_level = autofisher_data.get("efficiency_level", 1)
        fishing_interval = self.BASE_FISHING_INTERVAL * (0.85 ** (efficiency_level - 1))  # 15% faster per level
        
        # Check if enough time has passed to fish
        if (current_time - last_fish_time).total_seconds() < fishing_interval:
            return
            
        # Process fishing for each autofisher
        autofisher_count = autofisher_data["count"]
        autofisher_balance = autofisher_data.get("balance", 0)
        
        for _ in range(autofisher_count):
            # Check for bait
            if not fishing_items["bait"]:
                # Try to buy bait if autofisher has balance
                bait_cost = 50  # Pro bait cost
                if autofisher_balance >= bait_cost:
                    # Buy pro bait
                    bait = {
                        "id": str(uuid.uuid4()),
                        "name": "Pro Bait",
                        "amount": 10,
                        "description": "Better chances for rare fish",
                        "catch_rates": {"normal": 1.2, "rare": 0.3, "event": 0.1}
                    }
                    await db.add_bait(user_id, bait)
                    autofisher_balance -= bait_cost
                    fishing_items["bait"] = [bait]  # Update local copy
                else:
                    break  # No money for bait, stop autofishing
            
            # Use bait and fish
            bait = fishing_items["bait"][0]
            rod = fishing_items["rods"][0]  # Use first rod
            
            # Remove bait
            if not await db.remove_bait(user_id, bait["id"]):
                break
                
            # Update local bait count
            bait["amount"] -= 1
            if bait["amount"] <= 0:
                fishing_items["bait"] = []
            
            # Calculate catch chances (same as manual fishing)
            base_chances = {
                "normal": 0.7 * bait.get("catch_rates", {}).get("normal", 1.0),
                "rare": 0.2 * bait.get("catch_rates", {}).get("rare", 0.1),
                "event": 0.08 * bait.get("catch_rates", {}).get("event", 0.0),
                "mutated": 0.02 * bait.get("catch_rates", {}).get("mutated", 0.0)
            }
            
            rod_mult = rod.get("multiplier", 1.0)
            chances = {k: v * rod_mult for k, v in base_chances.items()}
            
            roll = random.random()
            cumulative = 0
            caught_type = "normal"
            
            for fish_type, chance in chances.items():
                cumulative += chance
                if roll <= cumulative:
                    caught_type = fish_type
                    break
            
            # Generate fish value
            value_range = {
                "normal": (10, 100),
                "rare": (100, 500),
                "event": (500, 2000),
                "mutated": (2000, 10000)
            }[caught_type]
            
            fish = {
                "id": str(uuid.uuid4()),
                "type": caught_type,
                "name": f"{caught_type.title()} Fish",
                "value": random.randint(*value_range),
                "caught_at": current_time.isoformat(),
                "bait_used": bait["id"],
                "rod_used": rod["id"],
                "auto_caught": True
            }
            
            # Add fish to collection
            await db.add_fish(user_id, fish)
        
        # Update last fish time and autofisher balance
        await db.update_autofisher_data(user_id, {
            "last_fish_time": current_time.isoformat(),
            "balance": autofisher_balance
        })

    @commands.group(name="auto", aliases=["af", "autofisher"], invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def auto(self, ctx):
        """View your autofisher status with interactive controls"""
        autofisher_data = await db.get_autofisher_data(ctx.author.id)
        
        if not autofisher_data:
            embed = discord.Embed(
                title="🤖 Autofisher System",
                description="You don't have any autofishers yet!\nUse `.auto buy` to purchase your first autofisher.",
                color=0x2b2d31
            )
            embed.add_field(
                name="💰 First Autofisher Cost",
                value=f"{self.BASE_AUTOFISHER_PRICE}",
                inline=False
            )
            
            # Add buy button for first autofisher
            view = discord.ui.View()
            buy_button = discord.ui.Button(
                label=f"Buy First Autofisher ({self.BASE_AUTOFISHER_PRICE})",
                style=discord.ButtonStyle.green,
                emoji="🤖"
            )
            
            async def buy_callback(interaction):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("❌ This is not your autofisher!", ephemeral=True)
                await self.handle_autofisher_purchase(ctx)
                view.stop()
            
            buy_button.callback = buy_callback
            view.add_item(buy_button)
            return await ctx.reply(embed=embed, view=view)
        
        # Calculate next fishing time
        last_fish_time = datetime.datetime.fromisoformat(autofisher_data.get("last_fish_time", "2000-01-01T00:00:00"))
        efficiency_level = autofisher_data.get("efficiency_level", 1)
        fishing_interval = self.BASE_FISHING_INTERVAL * (0.85 ** (efficiency_level - 1))
        next_fish_time = last_fish_time + datetime.timedelta(seconds=fishing_interval)
        time_until_next = (next_fish_time - datetime.datetime.utcnow()).total_seconds()
        
        embed = discord.Embed(
            title="🤖 Your Autofisher Status",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📊 Statistics",
            value=f"**Autofishers:** {autofisher_data['count']}/{self.MAX_AUTOFISHERS}\n"
                f"**Efficiency Level:** {efficiency_level}/{self.MAX_EFFICIENCY_LEVEL}\n"
                f"**Autofisher Balance:** {autofisher_data.get('balance', 0)} {self.currency}",
            inline=False
        )
        
        embed.add_field(
            name="⏰ Timing",
            value=f"**Fishing Interval:** {fishing_interval/60:.1f} minutes\n"
                f"**Next Fish:** {'Now!' if time_until_next <= 0 else f'{time_until_next/60:.1f} minutes'}",
            inline=False
        )
        
        # Calculate upgrade costs
        next_autofisher_cost = int(self.BASE_AUTOFISHER_PRICE * (self.AUTOFISHER_PRICE_MULTIPLIER ** autofisher_data['count']))
        next_efficiency_cost = int(self.BASE_EFFICIENCY_UPGRADE_PRICE * (self.EFFICIENCY_PRICE_MULTIPLIER ** (efficiency_level - 1)))
        
        embed.add_field(
            name="💸 Upgrade Costs",
            value=f"**Next Autofisher:** {next_autofisher_cost} {self.currency}\n"
                f"**Efficiency Upgrade:** {next_efficiency_cost} {self.currency}",
            inline=False
        )
        
        # Create view with buttons
        view = discord.ui.View(timeout=120)
        
        # Add autofisher purchase button if not at max
        if autofisher_data["count"] < self.MAX_AUTOFISHERS:
            buy_button = discord.ui.Button(
                label=f"Buy Autofisher ({next_autofisher_cost})",
                style=discord.ButtonStyle.green,
                emoji="🤖",
                row=0
            )
            
            async def buy_callback(interaction):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("❌ This is not your autofisher!", ephemeral=True)
                await self.handle_autofisher_purchase(ctx)
                view.stop()
            
            buy_button.callback = buy_callback
            view.add_item(buy_button)
        
        # Add efficiency upgrade button if not at max
        if efficiency_level < self.MAX_EFFICIENCY_LEVEL:
            upgrade_button = discord.ui.Button(
                label=f"Upgrade Efficiency ({next_efficiency_cost})",
                style=discord.ButtonStyle.blurple,
                emoji="⚡",
                row=0
            )
            
            async def upgrade_callback(interaction):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("❌ This is not your autofisher!", ephemeral=True)
                await self.handle_efficiency_upgrade(ctx)
                view.stop()
            
            upgrade_button.callback = upgrade_callback
            view.add_item(upgrade_button)
        
        # Add balance management buttons
        current_balance = autofisher_data.get("balance", 0)
        deposit_amount = 100
        
        # Deposit button row
        deposit_row = discord.ui.View(timeout=120)
        
        # Decrease button
        decrease_button = discord.ui.Button(
            label="◀",
            style=discord.ButtonStyle.gray,
            row=1
        )
        
        async def decrease_callback(interaction):
            nonlocal deposit_amount
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message("❌ This is not your autofisher!", ephemeral=True)
            
            deposit_amount = max(100, deposit_amount - 100)
            await interaction.response.edit_message(view=create_balance_buttons())
        
        decrease_button.callback = decrease_callback
        deposit_row.add_item(decrease_button)
        
        # Deposit amount button
        deposit_display = discord.ui.Button(
            label=f"Deposit {deposit_amount}",
            style=discord.ButtonStyle.green,
            row=1
        )
        
        async def deposit_callback(interaction):
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message("❌ This is not your autofisher!", ephemeral=True)
            
            balance = await db.get_balance(ctx.author.id)
            if balance < deposit_amount:
                return await interaction.response.send_message(
                    f"❌ You don't have enough money! (Need {deposit_amount} {self.currency})",
                    ephemeral=True
                )
            
            if await db.update_balance(ctx.author.id, -deposit_amount):
                autofisher_data["balance"] = autofisher_data.get("balance", 0) + deposit_amount
                await db.set_autofisher_data(ctx.author.id, autofisher_data)
                
                embed = discord.Embed(
                    title="💰 Deposit Successful!",
                    description=f"Deposited **{deposit_amount}** {self.currency} into autofisher balance\n"
                            f"New autofisher balance: **{autofisher_data['balance']}** {self.currency}",
                    color=discord.Color.green()
                )
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.response.send_message("❌ Failed to deposit money!", ephemeral=True)
        
        deposit_display.callback = deposit_callback
        deposit_row.add_item(deposit_display)
        
        # Increase button
        increase_button = discord.ui.Button(
            label="▶",
            style=discord.ButtonStyle.gray,
            row=1
        )
        
        async def increase_callback(interaction):
            nonlocal deposit_amount
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message("❌ This is not your autofisher!", ephemeral=True)
            
            deposit_amount += 100
            await interaction.response.edit_message(view=create_balance_buttons())
        
        increase_button.callback = increase_callback
        deposit_row.add_item(increase_button)
        
        def create_balance_buttons():
            """Helper function to recreate buttons with updated amount"""
            new_view = discord.ui.View(timeout=120)
            
            # Copy existing buttons
            for item in view.children:
                if isinstance(item, discord.ui.Button) and item.row == 0:
                    new_view.add_item(item)
            
            # Update deposit row
            deposit_row = discord.ui.View(timeout=120)
            
            # Decrease button
            decrease_button = discord.ui.Button(
                label="◀",
                style=discord.ButtonStyle.gray,
                row=1
            )
            decrease_button.callback = decrease_callback
            deposit_row.add_item(decrease_button)
            
            # Updated deposit button
            updated_deposit = discord.ui.Button(
                label=f"Deposit {deposit_amount}",
                style=discord.ButtonStyle.green,
                row=1
            )
            updated_deposit.callback = deposit_callback
            deposit_row.add_item(updated_deposit)
            
            # Increase button
            increase_button = discord.ui.Button(
                label="▶",
                style=discord.ButtonStyle.gray,
                row=1
            )
            increase_button.callback = increase_callback
            deposit_row.add_item(increase_button)
            
            # Add deposit row to main view
            for item in deposit_row.children:
                new_view.add_item(item)
            
            return new_view
        
        # Add the deposit buttons to the main view
        for item in deposit_row.children:
            view.add_item(item)
        
        await ctx.reply(embed=embed, view=view)

    @auto.command(name="buy", aliases=["purchase"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def auto_buy(self, ctx):
        """Buy an additional autofisher"""
        await self.handle_autofisher_purchase(ctx, is_initial=True)

    async def handle_autofisher_purchase(self, ctx, is_initial=False):
        balance = await db.get_balance(ctx.author.id)
        autofisher_data = await db.get_autofisher_data(ctx.author.id) or {"count": 0, "efficiency_level": 1, "balance": 0}
        
        if autofisher_data["count"] >= self.MAX_AUTOFISHERS:
            return await ctx.reply(f"❌ You've reached the maximum number of autofishers ({self.MAX_AUTOFISHERS})!")
        
        cost = int(self.BASE_AUTOFISHER_PRICE * (self.AUTOFISHER_PRICE_MULTIPLIER ** autofisher_data["count"]))
        
        if balance < cost:
            return await ctx.reply(f"❌ You need {cost} {self.currency} to buy an autofisher! (You have {balance})")
        
        # Create embed
        embed = discord.Embed(
            title="🤖 Autofisher Purchase",
            description=f"Current autofishers: **{autofisher_data['count']}**\n"
                    f"Purchase cost: **{cost} {self.currency}**\n"
                    f"Your balance: **{balance} {self.currency}**\n\n"
                    f"New total will be: **{autofisher_data['count'] + 1}**",
            color=discord.Color.blue()
        )
        
        # Add next purchase info if not max
        if autofisher_data["count"] + 1 < self.MAX_AUTOFISHERS:
            next_cost = int(self.BASE_AUTOFISHER_PRICE * (self.AUTOFISHER_PRICE_MULTIPLIER ** (autofisher_data["count"] + 1)))
            embed.add_field(
                name="Next Purchase",
                value=f"Autofisher #{autofisher_data['count'] + 2} will cost {next_cost} {self.currency}",
                inline=False
            )
        
        # Create view with buttons
        view = discord.ui.View()
        
        # Purchase button
        purchase_button = discord.ui.Button(
            label=f"Buy Autofisher #{autofisher_data['count'] + 1}",
            style=discord.ButtonStyle.green,
            emoji="🤖"
        )
        
        async def purchase_callback(interaction):
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message("❌ This is not your purchase!", ephemeral=True)
            
            # Verify balance again in case it changed
            current_balance = await db.get_balance(ctx.author.id)
            if current_balance < cost:
                return await interaction.response.send_message(
                    f"❌ You no longer have enough money! (Need {cost} {self.currency})",
                    ephemeral=True
                )
            
            # Process purchase
            if await db.update_balance(ctx.author.id, -cost):
                autofisher_data["count"] += 1
                autofisher_data["last_fish_time"] = datetime.datetime.utcnow().isoformat()
                await db.set_autofisher_data(ctx.author.id, autofisher_data)
                
                success_embed = discord.Embed(
                    title="🤖 Autofisher Purchased!",
                    description=f"You now have **{autofisher_data['count']}** autofisher{'s' if autofisher_data['count'] > 1 else ''}!",
                    color=discord.Color.green()
                )
                
                # Disable the purchase button after successful purchase
                purchase_button.disabled = True
                view.stop()
                
                await interaction.response.edit_message(embed=success_embed, view=view)
                
                # If not at max, offer another purchase
                if autofisher_data["count"] < self.MAX_AUTOFISHERS:
                    await self.handle_autofisher_purchase(ctx)
            else:
                await interaction.response.send_message("❌ Failed to purchase autofisher!", ephemeral=True)
        
        purchase_button.callback = purchase_callback
        view.add_item(purchase_button)
        
        # Cancel button
        cancel_button = discord.ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.red,
            emoji="❌"
        )
        
        async def cancel_callback(interaction):
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message("❌ This is not your purchase!", ephemeral=True)
            
            embed = discord.Embed(
                description="❌ Autofisher purchase cancelled.",
                color=discord.Color.red()
            )
            view.stop()
            await interaction.response.edit_message(embed=embed, view=view)
        
        cancel_button.callback = cancel_callback
        view.add_item(cancel_button)
        
        if is_initial:
            await ctx.reply(embed=embed, view=view)
        else:
            await ctx.send(embed=embed, view=view)

    @auto.command(name="upgrade", aliases=["eff", "efficiency"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def auto_upgrade(self, ctx):
        """Upgrade autofisher efficiency (faster fishing)"""
        await self.handle_efficiency_upgrade(ctx, is_initial=True)

    async def handle_efficiency_upgrade(self, ctx, is_initial=False):
        balance = await db.get_balance(ctx.author.id)
        autofisher_data = await db.get_autofisher_data(ctx.author.id)
        
        if not autofisher_data or autofisher_data["count"] == 0:
            return await ctx.reply("❌ You need at least one autofisher before upgrading efficiency!")
        
        efficiency_level = autofisher_data.get("efficiency_level", 1)
        if efficiency_level >= self.MAX_EFFICIENCY_LEVEL:
            return await ctx.reply(f"❌ Your autofishers are at maximum efficiency ({self.MAX_EFFICIENCY_LEVEL})!")
        
        cost = int(self.BASE_EFFICIENCY_UPGRADE_PRICE * (self.EFFICIENCY_PRICE_MULTIPLIER ** (efficiency_level - 1)))
        
        if balance < cost:
            return await ctx.reply(f"❌ You need {cost} {self.currency} to upgrade efficiency! (You have {balance})")
        
        # Create embed
        embed = discord.Embed(
            title="⚡ Efficiency Upgrade",
            description=f"Current level: **{efficiency_level}**\n"
                    f"Upgrade cost: **{cost} {self.currency}**\n"
                    f"Your balance: **{balance} {self.currency}**\n\n"
                    f"New level will be: **{efficiency_level + 1}**",
            color=discord.Color.blue()
        )
        
        # Add next level info if not max
        if efficiency_level + 1 < self.MAX_EFFICIENCY_LEVEL:
            next_cost = int(self.BASE_EFFICIENCY_UPGRADE_PRICE * (self.EFFICIENCY_PRICE_MULTIPLIER ** efficiency_level))
            embed.add_field(
                name="Next Upgrade",
                value=f"Level {efficiency_level + 2} will cost {next_cost} {self.currency}",
                inline=False
            )
        
        # Create view with buttons
        view = discord.ui.View()
        
        # Upgrade button
        upgrade_button = discord.ui.Button(
            label=f"Upgrade to Level {efficiency_level + 1}",
            style=discord.ButtonStyle.green,
            emoji="⚡"
        )
        
        async def upgrade_callback(interaction):
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message("❌ This is not your upgrade!", ephemeral=True)
            
            # Verify balance again in case it changed
            current_balance = await db.get_balance(ctx.author.id)
            if current_balance < cost:
                return await interaction.response.send_message(
                    f"❌ You no longer have enough money! (Need {cost} {self.currency})",
                    ephemeral=True
                )
            
            # Process upgrade
            if await db.update_balance(ctx.author.id, -cost):
                autofisher_data["efficiency_level"] = efficiency_level + 1
                await db.set_autofisher_data(ctx.author.id, autofisher_data)
                
                new_interval = self.BASE_FISHING_INTERVAL * (0.85 ** (efficiency_level))
                
                success_embed = discord.Embed(
                    title="⚡ Efficiency Upgraded!",
                    description=f"New efficiency level: **{efficiency_level + 1}**\n"
                            f"New fishing interval: **{new_interval/60:.1f} minutes**",
                    color=discord.Color.green()
                )
                
                # Disable the upgrade button after successful upgrade
                upgrade_button.disabled = True
                view.stop()
                
                await interaction.response.edit_message(embed=success_embed, view=view)
                
                # If not at max level, offer another upgrade
                if efficiency_level + 1 < self.MAX_EFFICIENCY_LEVEL:
                    await self.handle_efficiency_upgrade(ctx)
            else:
                await interaction.response.send_message("❌ Failed to upgrade efficiency!", ephemeral=True)
        
        upgrade_button.callback = upgrade_callback
        view.add_item(upgrade_button)
        
        # Cancel button
        cancel_button = discord.ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.red,
            emoji="❌"
        )
        
        async def cancel_callback(interaction):
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message("❌ This is not your upgrade!", ephemeral=True)
            
            embed = discord.Embed(
                description="❌ Efficiency upgrade cancelled.",
                color=discord.Color.red()
            )
            view.stop()
            await interaction.response.edit_message(embed=embed, view=view)
        
        cancel_button.callback = cancel_callback
        view.add_item(cancel_button)
        
        if is_initial:
            await ctx.reply(embed=embed, view=view)
        else:
            await ctx.send(embed=embed, view=view)

    @auto.command(name="deposit", aliases=["add", "fund"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def auto_deposit(self, ctx, amount: int):
        """Deposit money into your autofisher balance for buying bait"""
        if amount <= 0:
            return await ctx.reply("❌ Amount must be positive!")
        
        balance = await db.get_balance(ctx.author.id)
        if balance < amount:
            return await ctx.reply(f"❌ You don't have enough money! (You have {balance} {self.currency})")
        
        autofisher_data = await db.get_autofisher_data(ctx.author.id)
        if not autofisher_data or autofisher_data["count"] == 0:
            return await ctx.reply("❌ You need at least one autofisher before depositing!")
        
        if await db.update_balance(ctx.author.id, -amount):
            autofisher_data["balance"] = autofisher_data.get("balance", 0) + amount
            await db.set_autofisher_data(ctx.author.id, autofisher_data)
            
            embed = discord.Embed(
                title="💰 Deposit Successful!",
                description=f"Deposited **{amount}** {self.currency} into autofisher balance\n"
                           f"New autofisher balance: **{autofisher_data['balance']}** {self.currency}",
                color=discord.Color.green()
            )
            await ctx.reply(embed=embed)
        else:
            await ctx.reply("❌ Failed to deposit money!")

    @auto.command(name="withdraw", aliases=["take"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def auto_withdraw(self, ctx, amount: int):
        """Withdraw money from your autofisher balance"""
        if amount <= 0:
            return await ctx.reply("❌ Amount must be positive!")
            
        autofisher_data = await db.get_autofisher_data(ctx.author.id)
        if not autofisher_data or autofisher_data["count"] == 0:
            return await ctx.reply("❌ You don't have any autofishers!")
            
        autofisher_balance = autofisher_data.get("balance", 0)
        if autofisher_balance < amount:
            return await ctx.reply(f"❌ Your autofisher balance is only {autofisher_balance} {self.currency}!")
        
        if await db.update_balance(ctx.author.id, amount):
            autofisher_data["balance"] = autofisher_balance - amount
            await db.set_autofisher_data(ctx.author.id, autofisher_data)
            
            embed = discord.Embed(
                title="💸 Withdrawal Successful!",
                description=f"Withdrew **{amount}** {self.currency} from autofisher balance\n"
                           f"Remaining autofisher balance: **{autofisher_data['balance']}** {self.currency}",
                color=discord.Color.green()
            )
            await ctx.reply(embed=embed)
        else:
            await ctx.reply("❌ Failed to withdraw money!")

    @auto.command(name="collect", aliases=["sell", "cash"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def auto_collect(self, ctx):
        """Collect and sell all auto-caught fish"""
        fish = await db.get_fish(ctx.author.id)
        auto_fish = [f for f in fish if f.get("auto_caught", False)]
        
        if not auto_fish:
            return await ctx.reply("❌ You don't have any auto-caught fish to collect!")
        
        total_value = sum(f["value"] for f in auto_fish)
        
        # Remove auto-caught fish and add money
        for fish_item in auto_fish:
            await db.remove_fish(ctx.author.id, fish_item["id"])
        
        if await db.update_balance(ctx.author.id, total_value):
            embed = discord.Embed(
                title="🤖 Auto-Fish Collected!",
                description=f"Sold **{len(auto_fish)}** auto-caught fish for **{total_value}** {self.currency}!",
                color=discord.Color.green()
            )
            
            # Show breakdown by type
            fish_by_type = {}
            for f in auto_fish:
                fish_by_type.setdefault(f["type"], []).append(f)
            
            breakdown = []
            for fish_type, fish_list in fish_by_type.items():
                type_value = sum(f["value"] for f in fish_list)
                breakdown.append(f"**{fish_type.title()}:** {len(fish_list)} fish ({type_value} {self.currency})")
            
            if breakdown:
                embed.add_field(
                    name="📊 Breakdown",
                    value="\n".join(breakdown),
                    inline=False
                )
            
            await ctx.reply(embed=embed)
        else:
            await ctx.reply("❌ Failed to collect fish!")

async def setup(bot):
    await bot.add_cog(AutoFishing(bot))