import discord
from discord.ext import commands
import logging
import json
import os
import asyncio
from typing import Dict, Optional, Any
from utils.error_handler import ErrorHandler

try:
    import aiofiles
except ImportError:
    aiofiles = None

CONFIG_PATH = "data/config.json"
MODMAIL_DATA_PATH = "data/modmail.json"
STATS_PATH = "data/stats.json"

def atomic_write(path: str, data: Any):
    """Write JSON data atomically to avoid corruption."""
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)

class ModMail(commands.Cog, ErrorHandler):
    """A Discord ModMail system for user-staff communication."""
    def __init__(self, bot: commands.Bot):
        ErrorHandler.__init__(self)
        self.bot = bot

        # Load config
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        self.staff_channel_id = config.get("modmail_staff_channel", 1259717946947670099)
        self.allowed_guilds = config.get("modmail_allowed_guilds", [
            1259717095382319215, 1299747094449623111, 1142088882222022786
        ])

        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)

        # Logger setup
        self.logger = logging.getLogger("ModMail")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # Load active tickets
        self.active_tickets: Dict[str, int] = asyncio.run(self.load_data())
        self.logger.info("ModMail cog initialized")

    async def load_data(self) -> Dict[str, int]:
        """Load active tickets from JSON file."""
        if not os.path.exists(MODMAIL_DATA_PATH):
            return {}
        try:
            if aiofiles:
                async with aiofiles.open(MODMAIL_DATA_PATH, "r") as f:
                    data = json.loads(await f.read())
            else:
                with open(MODMAIL_DATA_PATH, "r") as f:
                    data = json.load(f)
            return {k: int(v) for k, v in data.items()}
        except Exception as e:
            self.logger.error(f"Failed to load modmail data: {e}")
            return {}

    async def save_data(self):
        """Save active tickets to JSON file."""
        try:
            if aiofiles:
                async with aiofiles.open(MODMAIL_DATA_PATH, "w") as f:
                    await f.write(json.dumps(self.active_tickets, indent=2))
            else:
                atomic_write(MODMAIL_DATA_PATH, self.active_tickets)
        except Exception as e:
            self.logger.error(f"Failed to save modmail data: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info(f"ModMail cog ready. Logged in as {self.bot.user}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.author == self.bot.user:
            return

        # DM: User contacting ModMail
        if isinstance(message.channel, discord.DMChannel):
            if str(message.author.id) not in self.active_tickets:
                if message.content.lower().strip() == "help":
                    await self.send_help_message(message.author)
                else:
                    await self.create_new_modmail(message)
            else:
                await self.forward_to_thread(message)
            return

        # Staff reply in thread
        if (isinstance(message.channel, discord.Thread) and
            message.channel.parent_id == self.staff_channel_id and
            not message.author.bot and
            not message.content.startswith(".")):
            await self.handle_staff_reply(message)
            return

        # Message stats for allowed guilds
        if message.guild and message.guild.id in self.allowed_guilds:
            await self.update_message_stats(message)

    async def send_help_message(self, user: discord.User):
        """Send a help message to the user."""
        if not await self.can_use_modmail(user):
            embed = discord.Embed(
                description="Sorry, ModMail is only available to members of our servers.",
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                description="To create a modmail ticket, send a message containing your issue.\nExample: `I need help with...`",
                color=discord.Color.blue()
            )
        await user.send(embed=embed)

    async def can_use_modmail(self, user: discord.User | discord.Member) -> bool:
        """Check if user is in any of the allowed guilds."""
        for guild_id in self.allowed_guilds:
            guild = self.bot.get_guild(guild_id)
            if guild and guild.get_member(user.id):
                return True
        return False

    async def create_new_modmail(self, user_message: discord.Message):
        """Create a new modmail thread for a user's DM."""
        try:
            if not await self.can_use_modmail(user_message.author):
                embed = discord.Embed(
                    title="Access Denied",
                    description="You must be a member of one of our servers to use ModMail.",
                    color=discord.Color.red()
                )
                await user_message.author.send(embed=embed)
                return

            staff_channel = self.bot.get_channel(self.staff_channel_id)
            if not staff_channel:
                self.logger.error(f"Staff channel {self.staff_channel_id} not found!")
                return

            if str(user_message.author.id) in self.active_tickets:
                return

            embed = discord.Embed(
                title=f"New ModMail from {user_message.author}",
                description=user_message.content,
                color=discord.Color.green()
            )
            if user_message.author.avatar:
                embed.set_thumbnail(url=user_message.author.avatar.url)
            embed.add_field(name="User ID", value=str(user_message.author.id), inline=False)
            embed.add_field(name="Account Created", value=user_message.author.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)

            staff_msg = await staff_channel.send(embed=embed)
            thread = await staff_msg.create_thread(
                name=f"ModMail {user_message.author}",
                auto_archive_duration=1440
            )

            self.active_tickets[str(user_message.author.id)] = thread.id
            await self.save_data()

            user_embed = discord.Embed(
                title="ModMail Received",
                description="Your message has been received by our staff team. "
                            "Please wait for a response. You can send additional "
                            "messages in this DM and they will be forwarded.",
                color=discord.Color.green()
            )
            await user_message.author.send(embed=user_embed)
            self.logger.info(f"Created new modmail for {user_message.author}")

        except Exception as e:
            self.logger.error(f"Failed to create modmail: {e}")
            try:
                await user_message.author.send("Failed to create your modmail ticket. Please try again later.")
            except Exception:
                pass

    async def forward_to_thread(self, user_message: discord.Message):
        """Forward subsequent DMs to the existing thread."""
        thread_id = self.active_tickets.get(str(user_message.author.id))
        if not thread_id:
            self.logger.error(f"No thread ID found for user {user_message.author.id}")
            return

        try:
            thread = await self.bot.fetch_channel(thread_id)
            if not thread:
                self.logger.error(f"Thread {thread_id} not found!")
                del self.active_tickets[str(user_message.author.id)]
                await self.save_data()
                return

            embed = discord.Embed(
                description=user_message.content,
                color=discord.Color.blurple(),
                timestamp=user_message.created_at
            )
            avatar_url = user_message.author.avatar.url if user_message.author.avatar else discord.Embed.Empty
            embed.set_author(name=str(user_message.author), icon_url=avatar_url)

            if user_message.attachments:
                attachment_urls = [f"[a.filename](a.url)" for a in user_message.attachments]
                embed.add_field(name="Attachments", value="\n".join(attachment_urls), inline=False)

            msg = await thread.send(embed=embed)
            await msg.add_reaction("✅")

        except discord.NotFound:
            self.logger.error(f"Thread {thread_id} not found (404)")
            del self.active_tickets[str(user_message.author.id)]
            await self.save_data()
            try:
                await user_message.author.send("Your previous modmail thread was not found. A new one will be created if you send another message.")
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"Failed to forward message: {e}")
            try:
                await user_message.author.send("Failed to forward your message to staff. Please try again later.")
            except Exception:
                pass

    async def handle_staff_reply(self, staff_message: discord.Message):
        """Handle staff replies in modmail threads."""
        try:
            if staff_message.content.startswith("!"):
                return

            staffroles = {
                "owner": 1281553341100457995,
                "co-owner": 1262995584231669770,
                "admin": 1292612655261155428,
                "head mod": 1259718732163321906,
                "mod": 1266510089683079330,
                "trial mod": 1259718795556028446,
                "helper": 1362671155730972733,
                "staff": 1259728436377817100
            }
            staffrank = None
            author_role_ids = {role.id for role in getattr(staff_message.author, "roles", [])}
            for role_name, role_id in staffroles.items():
                if role_id in author_role_ids:
                    staffrank = role_name
                    break
            if not staffrank:
                return

            user_id = next((int(uid) for uid, tid in self.active_tickets.items() if tid == staff_message.channel.id), None)
            if not user_id:
                return
            user = self.bot.get_user(user_id)
            if not user:
                return

            embed = discord.Embed(
                description=staff_message.content,
                color=discord.Color.blurple(),
                timestamp=staff_message.created_at
            )
            avatar_url = staff_message.author.avatar.url if staff_message.author.avatar else discord.Embed.Empty
            embed.set_author(
                name=f"{staff_message.author} ({staffrank.capitalize()})",
                icon_url=avatar_url
            )
            if staff_message.attachments:
                attachment_urls = [f"[a.filename](a.url)" for a in staff_message.attachments]
                embed.add_field(name="Attachments", value="\n".join(attachment_urls), inline=False)

            await user.send(embed=embed)
            await staff_message.add_reaction("✅")

        except discord.Forbidden:
            await staff_message.add_reaction("❌")
            await staff_message.channel.send("Failed to send message to user (user has DMs disabled)")
        except Exception as e:
            self.logger.error(f"Failed to handle staff reply: {e}")
            await staff_message.add_reaction("❌")
            await staff_message.channel.send(f"Failed to send message to user: {str(e)}")

    async def update_message_stats(self, message: discord.Message):
        """Update message statistics for allowed guilds."""
        try:
            os.makedirs("data", exist_ok=True)
            if aiofiles:
                if os.path.exists(STATS_PATH):
                    async with aiofiles.open(STATS_PATH, "r") as f:
                        data = json.loads(await f.read())
                else:
                    data = {}
            else:
                if os.path.exists(STATS_PATH):
                    with open(STATS_PATH, "r") as f:
                        data = json.load(f)
                else:
                    data = {}

            if "stats" not in data:
                data["stats"] = {}
            if "guilds" not in data:
                data["guilds"] = []

            guild_id = str(message.guild.id)
            if guild_id not in data["stats"]:
                data["stats"][guild_id] = {
                    "messages": 0,
                    "name": message.guild.name,
                    "last_message": discord.utils.utcnow().isoformat()
                }
            data["stats"][guild_id]["messages"] += 1
            data["stats"][guild_id]["last_message"] = discord.utils.utcnow().isoformat()
            if guild_id not in data["guilds"]:
                data["guilds"].append(guild_id)

            if aiofiles:
                async with aiofiles.open(STATS_PATH, "w") as f:
                    await f.write(json.dumps(data, indent=2))
            else:
                atomic_write(STATS_PATH, data)
        except Exception as e:
            self.logger.error(f"Failed to update stats for guild {message.guild.id}: {e}")

    @commands.command(name="open", aliases=["openmail", "openmodmail", "omm", "mods"])
    async def open_modmail(self, ctx: commands.Context, *, message: Optional[str] = None):
        """Open a new modmail thread."""
        if not await self.can_use_modmail(ctx.author):
            await ctx.reply("You must be a member of one of our servers to use ModMail.")
            return

        if not message or len(message) < 15:
            await ctx.reply("Please give a reason to open a new modmail thread. Don't spam it please.")
            return

        if str(ctx.author.id) in self.active_tickets:
            try:
                thread = await self.bot.fetch_channel(self.active_tickets[str(ctx.author.id)])
                await ctx.reply(f"You already have an active ticket! {thread.jump_url}")
                return
            except Exception:
                del self.active_tickets[str(ctx.author.id)]
                await self.save_data()

        class MockMessage:
            def __init__(self, author, content):
                self.author = author
                self.content = content
                self.created_at = discord.utils.utcnow()
        mock_message = MockMessage(ctx.author, message)
        await self.create_new_modmail(mock_message)
        await ctx.message.add_reaction("✅")

    @commands.command(name="close", aliases=["closemail", "closemodmail", "cmm"])
    @commands.has_permissions(manage_messages=True)
    async def close_modmail(self, ctx: commands.Context):
        """Close the current modmail thread."""
        try:
            if not isinstance(ctx.channel, discord.Thread):
                await ctx.send("This command can only be used in modmail threads")
                return

            user_id = next((uid for uid, tid in self.active_tickets.items() if tid == ctx.channel.id), None)
            if user_id:
                user = self.bot.get_user(int(user_id))
                if user:
                    try:
                        embed = discord.Embed(
                            title="ModMail Closed",
                            description="This modmail ticket has been closed by staff. "
                                        "If you have further questions, please open a new one.",
                            color=discord.Color.red()
                        )
                        await user.send(embed=embed)
                    except discord.HTTPException:
                        pass
                del self.active_tickets[user_id]
                await self.save_data()

            await ctx.send("Closing this modmail ticket...")
            await ctx.channel.edit(archived=True, locked=True)

        except Exception as e:
            self.logger.error(f"Failed to close modmail: {e}")
            await ctx.send(f"Failed to close modmail: {e}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if ctx.command and ctx.command.cog_name == self.__class__.__name__:
            await self.handle_error(ctx, error)

async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    try:
        await bot.add_cog(ModMail(bot))
    except Exception as e:
        print(f"Failed to load ModMail cog: {e}")
        raise