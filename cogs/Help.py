import discord
import json
from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.error_handler import ErrorHandler
from typing import Dict, List, Union

logger = CogLogger('Help')
with open('data/config.json', 'r') as f:
    data = json.load(f)
BOT_ADMINS = data['OWNER_IDS']

class HelpPaginator(discord.ui.View):
    def __init__(self, pages, author, timeout=180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.author = author
        self.current_page = 0
        self.message = None
        self.cog_page_map = {}  # Maps cog names to page indices
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.prev_button.disabled = len(self.pages) <= 1
        self.next_button.disabled = len(self.pages) <= 1
        
        # Update labels to show page numbers
        if len(self.pages) > 1:
            self.page_info.label = f"{self.current_page + 1}/{len(self.pages)}"
    
    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("This isn't your help menu!", ephemeral=True)
        
        self.current_page = (self.current_page - 1) % len(self.pages)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    @discord.ui.button(label="1/1", style=discord.ButtonStyle.primary, custom_id="page_info", disabled=True)
    async def page_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass  # This button is just for display
    
    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("This isn't your help menu!", ephemeral=True)
        
        self.current_page = (self.current_page + 1) % len(self.pages)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    @discord.ui.button(label="🗑️", style=discord.ButtonStyle.danger, custom_id="delete")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("Only the command author can delete this!", ephemeral=True)
        
        await interaction.response.defer()
        if self.message:
            await self.message.delete()
    
    @discord.ui.select(
        placeholder="Jump to category...",
        custom_id="category_select",
        row=1
    )
    async def select_category(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user != self.author:
            return await interaction.response.send_message("This isn't your help menu!", ephemeral=True)
        
        self.current_page = int(select.values[0])
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    async def on_timeout(self):
        """Disable all buttons when the view times out"""
        for item in self.children:
            item.disabled = True
        
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass  # Message was already deleted


class Help(commands.Cog, ErrorHandler):
    def __init__(self, bot):
        ErrorHandler.__init__(self)
        self.bot = bot
        
        # Define category mappings and emojis
        self.category_info = {
            'Economy': {'emoji': '💰', 'description': 'Money, work, fishing, gambling'},
            'Fun': {'emoji': '🎮', 'description': 'Games, entertainment, random fun'},
            'Utility': {'emoji': '🔧', 'description': 'Server info, user tools, utilities'},
            'Moderation': {'emoji': '🛡️', 'description': 'Admin tools, server management'},
            'Music': {'emoji': '🎵', 'description': 'Music playback and queue'},
            'Settings': {'emoji': '⚙️', 'description': 'Bot configuration and preferences'},
            'Admin': {'emoji': '👑', 'description': 'Bot owner and admin commands'},
            'Fishing': {'emoji': '🎣', 'description': 'Fishing system and related commands'},
            'AutoFishing': {'emoji': '🤖', 'description': 'Automated fishing features'},
            'Other': {'emoji': '📦', 'description': 'Miscellaneous commands'}
        }
        
        # Define cog to category mappings
        self.cog_categories = {
            'Economy': ['Economy', 'Work', 'Gambling', 'Giveaway', 'Trading', 'Shop', 'Bazaar'],
            'Fun': ['Fun', 'Text', 'Multiplayer', 'TicTacToe', 'Cypher', 'MathRace'],
            'Utility': ['Utility', 'Reminders', 'Status'],
            'Moderation': ['Moderation', 'VoteBans', 'Welcoming', 'Admin'],
            'Music': ['MusicCore', 'MusicControls', 'MusicQueue', 'MusicPlayer'],
            'Settings': ['GeneralSettings', 'ModerationSettings', 'EconomySettings', 'MusicSettings', 'WelcomeSettings', 'LoggingSettings'],
            'Fishing': ['FishingCore', 'FishingInventory', 'FishingSelling', 'FishingStats'],
            'AutoFishing': ['AutoFishing']
        }
        
        logger.info("Help cog initialized")
    
    def _get_command_signature(self, command: Union[commands.Command, commands.Group]) -> str:
        """Get a formatted command signature"""
        if isinstance(command, commands.Group):
            return f"{command.name} <subcommand>"
        else:
            return f"{command.name} {command.signature}".strip()
    
    def _format_command_help(self, command: Union[commands.Command, commands.Group]) -> str:
        """Format command help text with proper truncation"""
        if isinstance(command, commands.Group):
            subcommands = [sub.name for sub in command.commands if not sub.hidden]
            help_text = command.help or "Group command"
            if subcommands:
                help_text += f"\n**Subcommands:** {', '.join(subcommands[:5])}"
                if len(subcommands) > 5:
                    help_text += f" (+{len(subcommands) - 5} more)"
        else:
            help_text = command.help or "No description available"
        
        # Truncate if too long
        if len(help_text) > 100:
            help_text = help_text[:97] + "..."
        
        return help_text
    
    def _categorize_cog(self, cog_name: str) -> str:
        """Determine which category a cog belongs to"""
        for category, cogs in self.cog_categories.items():
            if cog_name in cogs or cog_name.lower() in [c.lower() for c in cogs]:
                return category
        return 'Other'
    
    def _should_show_cog(self, cog_name: str, user_id: int) -> bool:
        """Determine if a cog should be shown to the user"""
        # Hidden cogs
        hidden_cogs = ['help', 'jishaku', 'dev', 'performance', 'fishingmain', 'error']
        if cog_name.lower() in hidden_cogs:
            return False
        
        # Admin-only cogs
        admin_cogs = ['admin']
        if cog_name.lower() in admin_cogs and user_id not in BOT_ADMINS:
            return False
        
        return True
    
    @commands.command(aliases=['support'])
    async def invite(self, ctx):
        """Get the bot's invite link & support server."""
        await self._send_invite(ctx)
    
    @discord.app_commands.command(name="invite", description="Get the bot's invite link and support server")
    async def invite_slash(self, interaction: discord.Interaction):
        """Get the bot's invite link & support server."""
        await self._send_invite(interaction)
    
    async def _send_invite(self, ctx_or_interaction):
        """Send invite information"""
        embed = discord.Embed(
            title="🔗 Invite & Support",
            description=(
                f"**[Add {self.bot.user.name} to your server]"
                f"(https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands)**\n\n"
                "**[Join Support Server](https://discord.gg/jvyYWkj3ts)**\n"
                "**[Source Code](https://github.com/bronxbot/bot)**\n\n"
                "*Need help? Join our support server for assistance!*"
            ),
            color=self._get_color(ctx_or_interaction)
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await self._respond(ctx_or_interaction, embed)
    
    async def _send_invite(self, ctx_or_interaction):
        """Shared logic for both command types"""
        embed = discord.Embed(
            title="invite bronx",
            url="https://bronxbot.onrender.com/invite",
            description="[invite](https://bronxbot.onrender.com/invite) | [support](https://discord.gg/jvyYWkj3ts) | [website](https://bronxbot.onrender.com)",
            color=0x2b2d31
        )
        embed.set_footer(text="thanks for using bronx bot!")
        
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.reply(embed=embed)

    @commands.command(name="help", aliases=["h", "commands"])
    async def help(self, ctx, *, command=None):
        """Show help information for commands"""
        await self._send_help(ctx, command)
    
    @discord.app_commands.command(name="help", description="Show help information for commands")
    @discord.app_commands.describe(command="The command or category to get help for")
    async def help_slash(self, interaction: discord.Interaction, command: str = None):
        """Slash command version of help"""
        await self._send_help(interaction, command)
    
    async def _send_help(self, ctx_or_interaction, command=None):
        """Shared logic for both command types"""
        if command:
            # Check if it's a cog first
            cog = self.bot.get_cog(command)
            if cog:
                # Help for a cog
                commands_list = cog.get_commands()
                if not commands_list:
                    embed = discord.Embed(
                        description=f"no commands found in `{cog.qualified_name}`",
                        color=discord.Color.red()
                    )
                    return await self._respond(ctx_or_interaction, embed)
                
                embed = discord.Embed(
                    title=f"{cog.qualified_name} commands",
                    description="\n".join(
                        f"`/{cmd.name} {cmd.signature}` - {cmd.help or 'no description'}"
                        for cmd in sorted(commands_list, key=lambda x: x.name)
                    ),
                    color=self._get_color(ctx_or_interaction)
                )
                embed.set_footer(text=f"{len(commands_list)} commands")
                return await self._respond(ctx_or_interaction, embed)

            # Help for specific command
            cmd = self.bot.get_command(command.lower())
            if not cmd:
                embed = discord.Embed(
                    description=f"couldn't find command `{command}`",
                    color=discord.Color.red()
                )
                return await self._respond(ctx_or_interaction, embed)
            
            embed = discord.Embed(
                description=(
                    f"`/{cmd.name} {cmd.signature}`\n"
                    f"{cmd.help or 'no description'}\n"
                    + (f"\n**aliases:** {', '.join([f'`{a}`' for a in cmd.aliases])}" if cmd.aliases else "")
                ),
                color=self._get_color(ctx_or_interaction)
            )
            return await self._respond(ctx_or_interaction, embed)
        
        # Paginated help menu
        pages = []
        total_commands = 0
        cog_page_map = {}
        page_index = 1  # Start at 1 because overview is at 0
        
        # Group fishing-related cogs
        fishing_commands = []
        autofishing_commands = []
        
        for cog_name, cog in sorted(self.bot.cogs.items(), key=lambda x: x[0].lower()):
            if cog_name.lower() in ['help', 'jishaku', 'dev', 'moderation', 'votebans', 'stats', 'welcoming', 'performance', 'fishingmain']:
                continue

            if isinstance(ctx_or_interaction, (discord.Interaction, commands.Context)):
                user_id = ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id
                if user_id not in BOT_ADMINS and cog_name.lower() in ['admin', 'owner']:
                    continue
            
            commands_list = [cmd for cmd in cog.get_commands() if not cmd.hidden]
            if not commands_list:
                continue

            # Handle fishing modules specially
            if cog_name.lower() == 'autofishing':
                autofishing_commands.extend(commands_list)
                continue
            elif cog_name.lower() in ['fishingcore', 'fishinginventory', 'fishingselling', 'fishingstats'] or (hasattr(cog, '__module__') and 'fishing' in cog.__module__ and cog_name.lower() != 'autofishing'):
                fishing_commands.extend(commands_list)
                continue

            # Regular cog processing
            cog_page_map[cog_name] = page_index
            page_index += 1

            embed = discord.Embed(
                description=f"**{cog_name.lower()}**\n\n",
                color=self._get_color(ctx_or_interaction)
            )
            
            for cmd in sorted(commands_list, key=lambda x: x.name):
                usage = f"/{cmd.name} {cmd.signature}".strip()
                description = cmd.help or "no description"
                if len(description) > 80:
                    description = description[:77] + "..."
                embed.description += f"`{usage}`\n{description}\n\n"
                total_commands += 1
            
            embed.set_footer(text=f"{len(commands_list)} commands")
            pages.append(embed)
        
        # Create Fishing page if we have fishing commands
        if fishing_commands:
            cog_page_map["Fishing"] = page_index
            page_index += 1
            
            embed = discord.Embed(
                description=f"**fishing**\n\n",
                color=self._get_color(ctx_or_interaction)
            )
            
            for cmd in sorted(fishing_commands, key=lambda x: x.name):
                usage = f"/{cmd.name} {cmd.signature}".strip()
                description = cmd.help or "no description"
                if len(description) > 80:
                    description = description[:77] + "..."
                embed.description += f"`{usage}`\n{description}\n\n"
                total_commands += 1
            
            embed.set_footer(text=f"{len(fishing_commands)} commands")
            pages.append(embed)
        
        # Create AutoFishing page if we have autofishing commands
        if autofishing_commands:
            cog_page_map["AutoFishing"] = page_index
            page_index += 1
            
            embed = discord.Embed(
                description=f"**autofishing**\n\n",
                color=self._get_color(ctx_or_interaction)
            )
            
            for cmd in sorted(autofishing_commands, key=lambda x: x.name):
                usage = f"/{cmd.name} {cmd.signature}".strip()
                description = cmd.help or "no description"
                if len(description) > 80:
                    description = description[:77] + "..."
                embed.description += f"`{usage}`\n{description}\n\n"
                total_commands += 1
            
            embed.set_footer(text=f"{len(autofishing_commands)} commands")
            pages.append(embed)

        # Overview page
        overview_embed = discord.Embed(
            description=(
                f"`/help <command>` for details\n\n"
                f"**commands:** {total_commands}\n"
                f"**categories:** {len(pages)}"
            ),
            color=self._get_color(ctx_or_interaction)
        )
        pages.insert(0, overview_embed)
        
        # Create and send paginator
        author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        view = HelpPaginator(pages, author)
        
        # Add select menu options
        select = view.select_category
        select.add_option(label="Overview", value="0", description="View all categories")
        for cog_name, page_num in cog_page_map.items():
            select.add_option(
                label=cog_name,
                value=str(page_num),
                description=f"View {cog_name.lower()} commands"
            )
        
        view.update_buttons()
        if isinstance(ctx_or_interaction, discord.Interaction):
            message = await ctx_or_interaction.response.send_message(embed=pages[0], view=view)
            if isinstance(message, discord.InteractionResponse):
                # Need to fetch the message if it's an interaction response
                message = await ctx_or_interaction.original_response()
        else:
            message = await ctx_or_interaction.reply(embed=pages[0], view=view)
        
        view.message = message
        view.cog_page_map = cog_page_map
    
    def _get_color(self, ctx_or_interaction):
        """Get the color based on context or interaction"""
        if isinstance(ctx_or_interaction, discord.Interaction):
            return ctx_or_interaction.user.accent_color or discord.Color.blue()
        else:
            return ctx_or_interaction.author.accent_color or discord.Color.blue()
    
    async def _respond(self, ctx_or_interaction, embed):
        """Respond to either context or interaction"""
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.reply(embed=embed)

    @help.error
    async def help_error(self, ctx, error):
        """Handle help command errors"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.reply("❌ Command not found!")
        else:
            await self.handle_error(ctx, error, "help")
    
    @help_slash.error
    async def help_slash_error(self, interaction: discord.Interaction, error):
        logger.error(f"Help slash command error: {error}")
        await interaction.response.send_message("An error occurred with the help command.", ephemeral=True)

    @invite_slash.error
    async def invite_slash_error(self, interaction: discord.Interaction, error):
        logger.error(f"Invite slash command error: {error}")
        await interaction.response.send_message("An error occurred with the invite command.", ephemeral=True)


async def setup(bot):
    try:
        await bot.add_cog(Help(bot))
        # Sync commands
        await bot.tree.sync()
        logger.info("Help cog loaded and commands synced")
    except Exception as e:
        logger.error(f"Failed to load Help cog: {e}")
        raise e