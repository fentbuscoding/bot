import discord
import asyncio

class RestartConfirmView(discord.ui.View):
    def __init__(self, utility_cog, ctx, timeout=60):
        super().__init__(timeout=timeout)
        self.utility_cog = utility_cog
        self.ctx = ctx
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only the command author can use these buttons"""
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                "❌ Only the command author can confirm this restart!", 
                ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(label="🔄 Force Restart", style=discord.ButtonStyle.danger)
    async def confirm_restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm the force restart"""
        embed = discord.Embed(
            title="🔄 Force Restarting Bot",
            description="Restarting immediately...",
            color=discord.Color.red()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        await asyncio.sleep(2)
        await self.utility_cog._perform_restart()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the restart"""
        embed = discord.Embed(
            title="❌ Restart Cancelled",
            description="Force restart has been cancelled.",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        
    async def on_timeout(self):
        """Handle timeout"""
        embed = discord.Embed(
            title="⏰ Restart Timeout",
            description="Force restart confirmation timed out.",
            color=discord.Color.gray()
        )
        
        try:
            await self.ctx.edit_last_response(embed=embed, view=None)
        except:
            pass
