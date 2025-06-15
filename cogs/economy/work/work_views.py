"""
UI Views for the Work system
"""
import discord
import asyncio
from typing import Dict, Any
from .constants import JOBS, BOSS_GIFTS, CURRENCY
from .work_utils import (
    get_user_job, set_user_job, remove_user_job, update_boss_relationship,
    get_boss_relationship_status, format_currency, get_coworkers
)
from utils.db import db

class JobManagementView(discord.ui.View):
    """Main job management interface"""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="Choose Job", style=discord.ButtonStyle.primary, emoji="💼")
    async def choose_job(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your job menu!", ephemeral=True)
            return

        # Check if user already has a job
        current_job = await get_user_job(self.user_id)
        if current_job:
            embed = discord.Embed(
                title="❌ Already Employed",
                description=f"You already work as a **{current_job['job_info']['name']}**!\nUse `/leavejob` first if you want to change jobs.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        view = JobSelectionView(self.user_id)
        embed = discord.Embed(
            title="💼 Choose Your Career",
            description="Select a job that matches your skills and ambitions:",
            color=0x0099ff
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Job Status", style=discord.ButtonStyle.secondary, emoji="📊")
    async def job_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your job menu!", ephemeral=True)
            return

        user_job = await get_user_job(self.user_id)
        if not user_job:
            embed = discord.Embed(
                title="❌ Unemployed",
                description="You don't have a job! Use the **Choose Job** button to get started.",
                color=0xff0000
            )
        else:
            job_info = user_job['job_info']
            status_text, status_emoji = get_boss_relationship_status(
                user_job['boss_hostile'], user_job['boss_loyalty']
            )
            
            embed = discord.Embed(
                title=f"{job_info['emoji']} Your Job Status",
                description=f"**Position:** {job_info['name']}\n**Description:** {job_info['description']}",
                color=0x00ff00
            )
            embed.add_field(
                name="💰 Wage Range",
                value=f"{job_info['wage']['min']:,} - {job_info['wage']['max']:,} {CURRENCY}",
                inline=True
            )
            embed.add_field(
                name=f"{status_emoji} Boss Relationship",
                value=status_text,
                inline=True
            )
            embed.add_field(
                name="📈 Boss Stats",
                value=f"Hostility: {user_job['boss_hostile']}/100\nLoyalty: {user_job['boss_loyalty']}/100",
                inline=True
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Boss Relations", style=discord.ButtonStyle.success, emoji="🤝")
    async def boss_relations(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your job menu!", ephemeral=True)
            return

        user_job = await get_user_job(self.user_id)
        if not user_job:
            embed = discord.Embed(
                title="❌ No Job",
                description="You need a job to manage boss relationships!",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        view = BossRelationsView(self.user_id, user_job)
        embed = discord.Embed(
            title="🤝 Boss Relationship Management",
            description="Improve your relationship with your boss through gifts:",
            color=0x0099ff
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class JobSelectionView(discord.ui.View):
    """Job selection interface"""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.create_job_buttons()

    def create_job_buttons(self):
        """Create buttons for each job"""
        for job_id, job_info in list(JOBS.items())[:20]:  # Limit to first 20 jobs
            button = discord.ui.Button(
                label=job_info['name'][:80],  # Truncate if too long
                emoji=job_info['emoji'],
                style=discord.ButtonStyle.secondary,
                custom_id=f"job_select_{job_id}"
            )
            button.callback = self.create_job_callback(job_id)
            self.add_item(button)

    def create_job_callback(self, job_id: str):
        """Create callback for job selection"""
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("This isn't your job selection!", ephemeral=True)
                return

            success = await set_user_job(self.user_id, job_id)
            if success:
                job_info = JOBS[job_id]
                embed = discord.Embed(
                    title="🎉 Job Acquired!",
                    description=f"Congratulations! You're now employed as a **{job_info['name']}**!",
                    color=0x00ff00
                )
                embed.add_field(
                    name="💼 Job Details",
                    value=f"**Description:** {job_info['description']}\n**Wage:** {job_info['wage']['min']:,} - {job_info['wage']['max']:,} {CURRENCY}",
                    inline=False
                )
                embed.add_field(
                    name="🚀 Getting Started",
                    value="Use `/work` to start earning money!",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to assign job. Please try again.",
                    color=0xff0000
                )

            await interaction.response.edit_message(embed=embed, view=None)
        
        return callback

class BossRelationsView(discord.ui.View):
    """Boss relationship management interface"""
    
    def __init__(self, user_id: int, user_job: Dict[str, Any]):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.user_job = user_job

    @discord.ui.button(label="View Gifts", style=discord.ButtonStyle.primary, emoji="🎁")
    async def view_gifts(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your boss menu!", ephemeral=True)
            return

        view = GiftSelectionView(self.user_id)
        embed = discord.Embed(
            title="🎁 Boss Gifts",
            description="Choose a gift to improve your relationship with your boss:",
            color=0x0099ff
        )
        
        gift_list = ""
        for gift_id, gift_info in BOSS_GIFTS.items():
            gift_list += f"{gift_info['emoji']} **{gift_info['name']}** - {gift_info['cost']:,} {CURRENCY}\n"
            gift_list += f"   Loyalty: +{gift_info['loyalty']}, Hostility: {gift_info['hostile']}\n\n"
        
        embed.add_field(name="Available Gifts", value=gift_list, inline=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Current Status", style=discord.ButtonStyle.secondary, emoji="📊")
    async def current_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your boss menu!", ephemeral=True)
            return

        status_text, status_emoji = get_boss_relationship_status(
            self.user_job['boss_hostile'], self.user_job['boss_loyalty']
        )
        
        embed = discord.Embed(
            title=f"{status_emoji} Boss Relationship Status",
            description=f"Your boss {status_text.lower()}",
            color=0x0099ff
        )
        embed.add_field(
            name="📊 Detailed Stats",
            value=f"**Hostility:** {self.user_job['boss_hostile']}/100\n**Loyalty:** {self.user_job['boss_loyalty']}/100",
            inline=True
        )
        embed.add_field(
            name="💡 Tips",
            value="• Higher loyalty = better wages\n• Lower hostility = less problems\n• Give gifts to improve relationship",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class GiftSelectionView(discord.ui.View):
    """Gift selection interface"""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.create_gift_buttons()

    def create_gift_buttons(self):
        """Create buttons for each gift"""
        for gift_id, gift_info in BOSS_GIFTS.items():
            button = discord.ui.Button(
                label=f"{gift_info['name']} ({gift_info['cost']:,})",
                emoji=gift_info['emoji'],
                style=discord.ButtonStyle.secondary,
                custom_id=f"gift_{gift_id}"
            )
            button.callback = self.create_gift_callback(gift_id)
            self.add_item(button)

    def create_gift_callback(self, gift_id: str):
        """Create callback for gift selection"""
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("You can't buy gifts for someone else's boss!", ephemeral=True)
                return

            gift_info = BOSS_GIFTS[gift_id]
            
            # Check if user has enough money
            user_data = await db.execute_fetchone(
                "SELECT wallet FROM users WHERE id = ?", (self.user_id,)
            )
            
            if not user_data or user_data['wallet'] < gift_info['cost']:
                embed = discord.Embed(
                    title="❌ Insufficient Funds",
                    description=f"You need {gift_info['cost']:,} {CURRENCY} to buy {gift_info['name']}!",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Deduct cost and update boss relationship
            await db.update_wallet(self.user_id, -gift_info['cost'], interaction.guild_id)
            await update_boss_relationship(
                self.user_id, 
                hostile_change=gift_info['hostile'],
                loyalty_change=gift_info['loyalty']
            )

            embed = discord.Embed(
                title="🎁 Gift Given!",
                description=f"You gave your boss {gift_info['emoji']} **{gift_info['name']}**!",
                color=0x00ff00
            )
            embed.add_field(
                name="💰 Cost",
                value=f"-{gift_info['cost']:,} {CURRENCY}",
                inline=True
            )
            embed.add_field(
                name="📈 Relationship Change",
                value=f"Loyalty: +{gift_info['loyalty']}\nHostility: {gift_info['hostile']}",
                inline=True
            )

            await interaction.response.edit_message(embed=embed, view=None)
        
        return callback

class CoworkersView(discord.ui.View):
    """View for displaying coworkers"""
    
    def __init__(self, user_id: int, job_id: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.job_id = job_id

    @discord.ui.button(label="Refresh List", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh_coworkers(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your coworkers list!", ephemeral=True)
            return

        coworkers = await get_coworkers(self.user_id, self.job_id)
        job_info = JOBS.get(self.job_id)
        
        if not coworkers:
            embed = discord.Embed(
                title="👥 No Coworkers",
                description=f"You're the only {job_info['name']} currently employed!",
                color=0x0099ff
            )
        else:
            coworker_list = []
            for i, coworker in enumerate(coworkers, 1):
                username = coworker['username'] or f"User {coworker['id']}"
                coworker_list.append(f"{i}. {username}")
            
            embed = discord.Embed(
                title=f"👥 Your {job_info['name']} Coworkers",
                description="\n".join(coworker_list),
                color=0x0099ff
            )
            embed.set_footer(text=f"Total coworkers: {len(coworkers)}")

        await interaction.response.edit_message(embed=embed, view=self)
