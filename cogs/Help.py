import discord
import json
from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.error_handler import ErrorHandler
from typing import Optional, List, Dict, Union

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
        logger.info("Help cog initialized")
    
    def _get_command_signature(self, command) -> str:
        """Get a properly formatted command signature"""
        if isinstance(command, commands.Group):
            return f"{command.name} <subcommand>"
        else:
            signature = command.signature
            if signature:
                return f"{command.name} {signature}"
            return command.name
    
    def _format_command_help(self, command, prefix: str = "", show_aliases: bool = True, max_length: int = 80) -> str:
        """Format a command's help text with proper indentation and details"""
        signature = self._get_command_signature(command)
        help_text = command.help or "No description available"
        
        # Truncate long descriptions for overview
        if len(help_text) > max_length:
            help_text = help_text[:max_length-3] + "..."
        
        result = f"`{prefix}{signature}`\n{help_text}"
        
        if show_aliases and command.aliases:
            aliases_text = ", ".join(f"`{alias}`" for alias in command.aliases)
            result += f"\n*Aliases: {aliases_text}*"
        
        return result
    
    def _get_group_commands(self, group: commands.Group) -> List[commands.Command]:
        """Get all commands from a group, including nested groups"""
        commands_list = []
        for command in group.commands:
            if isinstance(command, commands.Group):
                commands_list.append(command)
                commands_list.extend(self._get_group_commands(command))
            else:
                commands_list.append(command)
        return commands_list
    
    def _organize_commands_by_category(self, commands_list: List[commands.Command]) -> Dict[str, List[commands.Command]]:
        """Organize commands by category/module"""
        categories = {
            "Economy": [],
            "Fishing": [],
            "Fun & Games": [],
            "Moderation": [],
            "Settings": [],
            "Utility": [],
            "Music": [],
            "Administration": [],
            "Other": []
        }
        
        for cmd in commands_list:
            if hasattr(cmd, 'cog') and cmd.cog:
                cog_name = cmd.cog.qualified_name.lower()
                
                # Categorize based on cog name/module
                if any(keyword in cog_name for keyword in ['economy', 'shop', 'gambling', 'work', 'trading']):
                    categories["Economy"].append(cmd)
                elif any(keyword in cog_name for keyword in ['fishing', 'rod', 'bait']):
                    categories["Fishing"].append(cmd)
                elif any(keyword in cog_name for keyword in ['fun', 'game', 'misc', 'cypher', 'tictactoe']):
                    categories["Fun & Games"].append(cmd)
                elif any(keyword in cog_name for keyword in ['moderation', 'mod', 'ban', 'kick']):
                    categories["Moderation"].append(cmd)
                elif any(keyword in cog_name for keyword in ['settings', 'config', 'welcome', 'logging']):
                    categories["Settings"].append(cmd)
                elif any(keyword in cog_name for keyword in ['utility', 'reminder', 'help']):
                    categories["Utility"].append(cmd)
                elif any(keyword in cog_name for keyword in ['music', 'audio', 'voice']):
                    categories["Music"].append(cmd)
                elif any(keyword in cog_name for keyword in ['admin', 'owner', 'performance']):
                    categories["Administration"].append(cmd)
                else:
                    categories["Other"].append(cmd)
            else:
                categories["Other"].append(cmd)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    @commands.command(aliases=['support'])
    async def invite(self, ctx):
        """Get the bot's invite link & support server."""
        await self._send_invite(ctx)
    
    @discord.app_commands.command(name="invite", description="Get the bot's invite link and support server")
    async def invite_slash(self, interaction: discord.Interaction):
        """Slash command version of invite"""
        await self._send_invite(interaction)
    
    async def _send_invite(self, ctx_or_interaction):
        """Shared logic for both command types"""
        embed = discord.Embed(
            title="invite bronx",
            url="https://bronxbot.onrender.com/invite",
            description="[invite](https://bronxbot.onrender.com/invite) | [support](https://discord.gg/jvyYWkj3ts) | [help](https://bronxbot.onrender.com)",
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
            return await self._send_specific_help(ctx_or_interaction, command)
        
        # Get all available commands
        all_commands = []
        user_id = ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id
        
        for cog_name, cog in self.bot.cogs.items():
            # Skip certain cogs from help
            if cog_name.lower() in ['help', 'jishaku', 'dev']:
                continue
            
            # Skip admin cogs for non-admins
            if user_id not in BOT_ADMINS and cog_name.lower() in ['admin', 'owner', 'performance']:
                continue
            
            # Get all commands from this cog
            cog_commands = [cmd for cmd in cog.get_commands() if not cmd.hidden]
            
            # Include group subcommands
            for cmd in cog_commands.copy():
                if isinstance(cmd, commands.Group):
                    subcommands = self._get_group_commands(cmd)
                    cog_commands.extend(subcommands)
            
            all_commands.extend(cog_commands)
        
        # Organize commands by category
        categories = self._organize_commands_by_category(all_commands)
        
        # Create pages for each category
        pages = []
        cog_page_map = {}
        
        # Overview page
        total_commands = len(all_commands)
        overview_embed = discord.Embed(
            title="🤖 BronxBot Help",
            description=(
                f"Welcome to BronxBot! Here's what I can do:\n\n"
                f"**📊 Statistics:**\n"
                f"• **{total_commands}** total commands\n"
                f"• **{len(categories)}** categories\n"
                f"• **{len(self.bot.guilds)}** servers\n\n"
                f"**🔍 Navigation:**\n"
                f"• Use the dropdown menu to jump to categories\n"
                f"• Use `.help <command>` for detailed command info\n"
                f"• Use `.help <category>` to see category commands\n\n"
                f"**📚 Quick Start:**\n"
                f"• `.balance` - Check your economy balance\n"
                f"• `.fish` - Start fishing to earn money\n"
                f"• `.help economy` - See all economy commands"
            ),
            color=self._get_color(ctx_or_interaction)
        )
        overview_embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        overview_embed.set_footer(text="💡 Tip: Commands work with both . and / prefixes!")
        pages.append(overview_embed)
        
        # Create category pages with pagination (max 8 commands per page)
        page_index = 1
        for category_name, commands_list in categories.items():
            if not commands_list:
                continue
                
            cog_page_map[category_name] = page_index
            
            # Get category emoji
            category_emojis = {
                "Economy": "💰",
                "Fishing": "🎣",
                "Fun & Games": "🎮",
                "Moderation": "🛡️",
                "Settings": "⚙️",
                "Utility": "🔧",
                "Music": "🎵",
                "Administration": "👑",
                "Other": "📦"
            }
            
            emoji = category_emojis.get(category_name, "📦")
            
            # Group commands by their parent command if they're subcommands
            grouped_commands = {}
            standalone_commands = []
            
            for cmd in sorted(commands_list, key=lambda x: x.qualified_name):
                if '.' in cmd.qualified_name:
                    # This is a subcommand
                    parent_name = cmd.qualified_name.split('.')[0]
                    if parent_name not in grouped_commands:
                        grouped_commands[parent_name] = []
                    grouped_commands[parent_name].append(cmd)
                else:
                    standalone_commands.append(cmd)
            
            # Combine standalone commands and group headers for pagination
            display_items = []
            
            # Add standalone commands first
            for cmd in standalone_commands:
                if isinstance(cmd, commands.Group):
                    # Show group with indication of subcommands
                    subcommand_count = len(list(cmd.walk_commands()))
                    display_items.append({
                        'type': 'group',
                        'command': cmd,
                        'subcommand_count': subcommand_count
                    })
                else:
                    display_items.append({
                        'type': 'command',
                        'command': cmd
                    })
            
            # Add group command summaries
            for parent_name, subcommands in grouped_commands.items():
                if len(subcommands) > 0:
                    display_items.append({
                        'type': 'subcommand_group',
                        'parent_name': parent_name,
                        'subcommands': subcommands[:3]  # Show only first 3 subcommands
                    })
            
            # Split into pages (max 8 items per page)
            items_per_page = 8
            total_pages = (len(display_items) + items_per_page - 1) // items_per_page
            
            for page_num in range(total_pages):
                start_idx = page_num * items_per_page
                end_idx = min(start_idx + items_per_page, len(display_items))
                page_items = display_items[start_idx:end_idx]
                
                title = f"{emoji} {category_name} Commands"
                if total_pages > 1:
                    title += f" (Page {page_num + 1}/{total_pages})"
                
                embed = discord.Embed(
                    title=title,
                    description="",
                    color=self._get_color(ctx_or_interaction)
                )
                
                for item in page_items:
                    if item['type'] == 'group':
                        cmd = item['command']
                        subcommand_count = item['subcommand_count']
                        embed.description += f"**{self._format_command_help(cmd, show_aliases=False, max_length=60)}**\n"
                        embed.description += f"*({subcommand_count} subcommands - use `.help {cmd.name}` for details)*\n\n"
                    elif item['type'] == 'command':
                        cmd = item['command']
                        embed.description += f"{self._format_command_help(cmd, show_aliases=False, max_length=60)}\n\n"
                    elif item['type'] == 'subcommand_group':
                        parent_name = item['parent_name']
                        subcommands = item['subcommands']
                        embed.description += f"**{parent_name} subcommands:**\n"
                        for subcmd in subcommands:
                            help_text = (subcmd.help or 'No description')[:50] + "..." if len(subcmd.help or '') > 50 else (subcmd.help or 'No description')
                            embed.description += f"  • `{subcmd.qualified_name}` - {help_text}\n"
                        embed.description += f"  • *Use `.help {parent_name}` for all subcommands*\n\n"
                
                if total_pages > 1:
                    embed.set_footer(text=f"Page {page_num + 1}/{total_pages} • {len(commands_list)} total commands in {category_name}")
                else:
                    embed.set_footer(text=f"{len(commands_list)} commands in this category")
                
                pages.append(embed)
                if page_num > 0:  # Only update page_index for additional pages
                    page_index += 1
            
            page_index += 1  # Move to next category
        
        # Create and send paginator
        author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        view = HelpPaginator(pages, author)
        
        # Add select menu options
        select = view.select_category
        select.add_option(label="📋 Overview", value="0", description="Main help page with navigation tips")
        
        for category_name, page_num in cog_page_map.items():
            emoji = {"Economy": "💰", "Fishing": "🎣", "Fun & Games": "🎮", "Moderation": "🛡️", 
                    "Settings": "⚙️", "Utility": "🔧", "Music": "🎵", "Administration": "👑", "Other": "📦"}.get(category_name, "📦")
            
            command_count = len(categories[category_name])
            select.add_option(
                label=f"{emoji} {category_name}",
                value=str(page_num),
                description=f"{command_count} commands available"
            )
        
        view.update_buttons()
        message = await self._send_paginated_help(ctx_or_interaction, pages[0], view)
        view.message = message
        view.cog_page_map = cog_page_map
    
    async def _send_specific_help(self, ctx_or_interaction, command_name: str):
        """Send help for a specific command or category"""
        # First check if it's a category
        categories = {
            "economy": "Economy",
            "fishing": "Fishing", 
            "fun": "Fun & Games",
            "games": "Fun & Games",
            "moderation": "Moderation",
            "mod": "Moderation",
            "settings": "Settings",
            "utility": "Utility",
            "util": "Utility",
            "music": "Music",
            "admin": "Administration",
            "administration": "Administration",
            "other": "Other"
        }
        
        category_name = categories.get(command_name.lower())
        if category_name:
            # Send category help
            await self._send_category_help(ctx_or_interaction, category_name)
            return
        
        # Look for specific command
        command = self.bot.get_command(command_name)
        if not command:
            # Try to find by alias
            for cmd in self.bot.walk_commands():
                if command_name.lower() in [alias.lower() for alias in cmd.aliases]:
                    command = cmd
                    break
        
        if not command:
            embed = discord.Embed(
                title="❌ Command Not Found",
                description=f"No command or category named `{command_name}` was found.\n\nUse `.help` to see all available commands.",
                color=0xe74c3c
            )
            await self._respond(ctx_or_interaction, embed)
            return
        
        # Create detailed help for the command
        embed = discord.Embed(
            title=f"📖 Help: {command.qualified_name}",
            color=self._get_color(ctx_or_interaction)
        )
        
        # Command signature
        signature = self._get_command_signature(command)
        embed.add_field(
            name="💬 Usage",
            value=f"`{signature}`",
            inline=False
        )
        
        # Description
        description = command.help or "No description available"
        embed.add_field(
            name="📝 Description", 
            value=description,
            inline=False
        )
        
        # Aliases
        if command.aliases:
            aliases_text = ", ".join(f"`{alias}`" for alias in command.aliases)
            embed.add_field(
                name="🔄 Aliases",
                value=aliases_text,
                inline=False
            )
        
        # Subcommands for groups
        if isinstance(command, commands.Group):
            subcommands = list(command.commands)
            if subcommands:
                subcommand_list = []
                for subcmd in sorted(subcommands, key=lambda x: x.name)[:10]:  # Show max 10
                    subcmd_help = (subcmd.help or 'No description')[:50] + "..." if len(subcmd.help or '') > 50 else (subcmd.help or 'No description')
                    subcommand_list.append(f"`{subcmd.name}` - {subcmd_help}")
                
                embed.add_field(
                    name="📋 Subcommands",
                    value="\n".join(subcommand_list),
                    inline=False
                )
                
                if len(subcommands) > 10:
                    embed.add_field(
                        name="➕ More",
                        value=f"... and {len(subcommands) - 10} more subcommands",
                        inline=False
                    )
        
        # Permissions
        if hasattr(command, 'checks') and command.checks:
            perms = []
            for check in command.checks:
                if hasattr(check, '__qualname__'):
                    if 'has_permissions' in check.__qualname__:
                        perms.append("Requires specific permissions")
                    elif 'is_owner' in check.__qualname__:
                        perms.append("Bot Owner only")
                    elif 'guild_only' in check.__qualname__:
                        perms.append("Server only (no DMs)")
            
            if perms:
                embed.add_field(
                    name="🔒 Requirements",
                    value="\n".join(perms),
                    inline=False
                )
        
        # Category/Cog
        if command.cog:
            embed.add_field(
                name="📁 Category",
                value=command.cog.qualified_name,
                inline=True
            )
        
        embed.set_footer(text="💡 Use .help to see all commands")
        await self._respond(ctx_or_interaction, embed)
    
    async def _send_category_help(self, ctx_or_interaction, category_name: str):
        """Send help for a specific category with better formatting"""
        # Get all commands for this category
        all_commands = []
        user_id = ctx_or_interaction.user.id if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author.id
        
        for cog_name, cog in self.bot.cogs.items():
            if cog_name.lower() in ['help', 'jishaku', 'dev']:
                continue
            if user_id not in BOT_ADMINS and cog_name.lower() in ['admin', 'owner', 'performance']:
                continue
            
            cog_commands = [cmd for cmd in cog.get_commands() if not cmd.hidden]
            for cmd in cog_commands.copy():
                if isinstance(cmd, commands.Group):
                    subcommands = self._get_group_commands(cmd)
                    cog_commands.extend(subcommands)
            all_commands.extend(cog_commands)
        
        # Organize and filter for this category
        categories = self._organize_commands_by_category(all_commands)
        commands_list = categories.get(category_name, [])
        
        if not commands_list:
            embed = discord.Embed(
                title="❌ Category Not Found",
                description=f"No category named `{category_name}` was found.",
                color=0xe74c3c
            )
            await self._respond(ctx_or_interaction, embed)
            return
        
        # Create paginated category help
        category_emojis = {
            "Economy": "💰", "Fishing": "🎣", "Fun & Games": "🎮", "Moderation": "🛡️",
            "Settings": "⚙️", "Utility": "🔧", "Music": "🎵", "Administration": "👑", "Other": "📦"
        }
        emoji = category_emojis.get(category_name, "📦")
        
        # Split commands into pages (6 commands per page for detailed view)
        commands_per_page = 6
        total_pages = (len(commands_list) + commands_per_page - 1) // commands_per_page
        pages = []
        
        for page_num in range(total_pages):
            start_idx = page_num * commands_per_page
            end_idx = min(start_idx + commands_per_page, len(commands_list))
            page_commands = commands_list[start_idx:end_idx]
            
            title = f"{emoji} {category_name} Commands"
            if total_pages > 1:
                title += f" (Page {page_num + 1}/{total_pages})"
                
            embed = discord.Embed(
                title=title,
                description=f"Detailed help for {category_name.lower()} commands:",
                color=self._get_color(ctx_or_interaction)
            )
            
            for cmd in page_commands:
                # More detailed formatting for category help
                signature = self._get_command_signature(cmd)
                help_text = cmd.help or "No description available"
                
                # Limit help text length but allow more than overview
                if len(help_text) > 120:
                    help_text = help_text[:117] + "..."
                
                value = f"`{signature}`\n{help_text}"
                
                if cmd.aliases:
                    aliases_text = ", ".join(f"`{alias}`" for alias in cmd.aliases[:3])
                    if len(cmd.aliases) > 3:
                        aliases_text += f" +{len(cmd.aliases) - 3} more"
                    value += f"\n*Aliases: {aliases_text}*"
                
                embed.add_field(
                    name=f"📌 {cmd.name}",
                    value=value,
                    inline=False
                )
            
            if total_pages > 1:
                embed.set_footer(text=f"Page {page_num + 1}/{total_pages} • {len(commands_list)} total commands • Use .help <command> for details")
            else:
                embed.set_footer(text=f"{len(commands_list)} commands • Use .help <command> for details")
            
            pages.append(embed)
        
        if len(pages) == 1:
            await self._respond(ctx_or_interaction, pages[0])
        else:
            # Use paginator for multiple pages
            author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
            view = HelpPaginator(pages, author)
            view.update_buttons()
            message = await self._send_paginated_help(ctx_or_interaction, pages[0], view)
            view.message = message
    
    async def _send_paginated_help(self, ctx_or_interaction, embed, view):
        """Send paginated help with view components"""
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(embed=embed, view=view)
            return await ctx_or_interaction.original_response()
        else:
            return await ctx_or_interaction.reply(embed=embed, view=view)
    
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