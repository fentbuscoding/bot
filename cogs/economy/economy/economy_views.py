"""
UI Views for the Economy system
"""
import discord
import asyncio
from typing import Dict, Any
from utils.db import db
from .constants import CURRENCY, COLORS
from .economy_utils import format_currency

class PaymentConfirmView(discord.ui.View):
    """Payment confirmation view for the receiving user"""
    
    def __init__(self, sender: discord.Member, receiver: discord.Member, amount: int):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.responded = False
    
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, emoji="✅")
    async def accept_payment(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id:
            return await interaction.response.send_message("❌ Only the payment recipient can respond!", ephemeral=True)
        
        if self.responded:
            return await interaction.response.send_message("❌ This payment has already been responded to!", ephemeral=True)
        
        self.responded = True
        
        # Process the payment
        success = await db.transfer_money(self.sender.id, self.receiver.id, self.amount, interaction.guild.id)
        
        if success:
            embed = discord.Embed(
                title="✅ Payment Accepted!",
                description=f"Successfully transferred **{self.amount:,}** {CURRENCY}",
                color=COLORS["success"]
            )
            embed.add_field(name="From:", value=self.sender.display_name, inline=True)
            embed.add_field(name="To:", value=self.receiver.display_name, inline=True)
            embed.add_field(name="Amount:", value=format_currency(self.amount), inline=True)
            
            # Send a notification to the sender
            try:
                sender_embed = discord.Embed(
                    title="💰 Payment Completed!",
                    description=f"{self.receiver.display_name} accepted your payment of **{self.amount:,}** {CURRENCY}",
                    color=COLORS["success"]
                )
                await self.sender.send(embed=sender_embed)
            except discord.Forbidden:
                pass  # Sender has DMs disabled
        else:
            embed = discord.Embed(
                title="❌ Payment Failed!",
                description=f"The sender ({self.sender.display_name}) has insufficient funds.",
                color=COLORS["error"]
            )
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red, emoji="❌")
    async def decline_payment(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id:
            return await interaction.response.send_message("❌ Only the payment recipient can respond!", ephemeral=True)
        
        if self.responded:
            return await interaction.response.send_message("❌ This payment has already been responded to!", ephemeral=True)
        
        self.responded = True
        
        embed = discord.Embed(
            title="❌ Payment Declined",
            description=f"{self.receiver.display_name} declined the payment of **{self.amount:,}** {CURRENCY}",
            color=COLORS["error"]
        )
        embed.add_field(name="From:", value=self.sender.display_name, inline=True)
        embed.add_field(name="Amount:", value=format_currency(self.amount), inline=True)
        
        # Send a notification to the sender
        try:
            sender_embed = discord.Embed(
                title="❌ Payment Declined",
                description=f"{self.receiver.display_name} declined your payment of **{self.amount:,}** {CURRENCY}",
                color=COLORS["error"]
            )
            await self.sender.send(embed=sender_embed)
        except discord.Forbidden:
            pass  # Sender has DMs disabled
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Called when the view times out"""
        if not self.responded:
            embed = discord.Embed(
                title="⏰ Payment Expired",
                description=f"Payment request from {self.sender.display_name} has expired",
                color=COLORS["warning"]
            )
            embed.add_field(name="Amount:", value=format_currency(self.amount), inline=True)
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            # Try to edit the message (may fail if message was deleted)
            try:
                if hasattr(self, 'message') and self.message:
                    await self.message.edit(embed=embed, view=self)
            except:
                pass  # Message might have been deleted

class LeaderboardPaginationView(discord.ui.View):
    """Pagination view for leaderboard"""
    
    def __init__(self, guild: discord.Guild, leaderboard_data: list, current_page: int = 1):
        super().__init__(timeout=300)
        self.guild = guild
        self.leaderboard_data = leaderboard_data
        self.current_page = current_page
        self.max_pages = max(1, (len(leaderboard_data) + 9) // 10)  # Ceiling division
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.previous_button.disabled = self.current_page <= 1
        self.next_button.disabled = self.current_page >= self.max_pages
        
        # Update labels
        self.previous_button.label = f"← Page {self.current_page - 1}" if self.current_page > 1 else "← Previous"
        self.next_button.label = f"Page {self.current_page + 1} →" if self.current_page < self.max_pages else "Next →"
    
    @discord.ui.button(label="← Previous", style=discord.ButtonStyle.secondary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_buttons()
            
            from .economy_utils import format_leaderboard_embed
            embed = format_leaderboard_embed(self.leaderboard_data, self.guild, self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Refresh leaderboard data
        from .economy_utils import create_leaderboard_data, format_leaderboard_embed
        
        self.leaderboard_data = await create_leaderboard_data(self.guild.id, limit=100)
        self.max_pages = max(1, (len(self.leaderboard_data) + 9) // 10)
        
        # Reset to page 1 if current page is now invalid
        if self.current_page > self.max_pages:
            self.current_page = 1
        
        self.update_buttons()
        embed = format_leaderboard_embed(self.leaderboard_data, self.guild, self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Next →", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.max_pages:
            self.current_page += 1
            self.update_buttons()
            
            from .economy_utils import format_leaderboard_embed
            embed = format_leaderboard_embed(self.leaderboard_data, self.guild, self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)

class InventoryPaginationView(discord.ui.View):
    """Pagination view for inventory display"""
    
    def __init__(self, user: discord.Member, inventory_data: list, current_page: int = 1):
        super().__init__(timeout=300)
        self.user = user
        self.inventory_data = inventory_data
        self.current_page = current_page
        self.items_per_page = 10
        self.max_pages = max(1, (len(inventory_data) + self.items_per_page - 1) // self.items_per_page)
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.previous_button.disabled = self.current_page <= 1
        self.next_button.disabled = self.current_page >= self.max_pages
    
    def create_inventory_embed(self) -> discord.Embed:
        """Create inventory embed for current page"""
        start_index = (self.current_page - 1) * self.items_per_page
        end_index = start_index + self.items_per_page
        page_items = self.inventory_data[start_index:end_index]
        
        embed = discord.Embed(
            title=f"🎒 {self.user.display_name}'s Inventory",
            color=self.user.color
        )
        
        if not page_items:
            embed.description = "This inventory page is empty."
        else:
            description = ""
            for item in page_items:
                item_name = item.get('name', 'Unknown Item')
                quantity = item.get('quantity', 1)
                description += f"• **{item_name}** x{quantity}\n"
            
            embed.description = description
        
        embed.set_footer(text=f"Page {self.current_page}/{self.max_pages} • Total items: {len(self.inventory_data)}")
        return embed
    
    @discord.ui.button(label="← Previous", style=discord.ButtonStyle.secondary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_buttons()
            
            embed = self.create_inventory_embed()
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Refresh inventory data
        self.inventory_data = await db.get_inventory(self.user.id) or []
        self.max_pages = max(1, (len(self.inventory_data) + self.items_per_page - 1) // self.items_per_page)
        
        # Reset to page 1 if current page is now invalid
        if self.current_page > self.max_pages:
            self.current_page = 1
        
        self.update_buttons()
        embed = self.create_inventory_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Next →", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.max_pages:
            self.current_page += 1
            self.update_buttons()
            
            embed = self.create_inventory_embed()
            await interaction.response.edit_message(embed=embed, view=self)
