"""
Minigame classes for different job types in the Work system
"""
import discord
import random
from utils.db import db
from .constants import CURRENCY, MINIGAME_SUCCESS_MULTIPLIER, MINIGAME_FAILURE_MULTIPLIER
from .work_utils import update_work_timestamp, calculate_wage

class BaseMinigame(discord.ui.View):
    """Base class for all work minigames"""
    def __init__(self, work_cog, user_job, original_user_id):
        super().__init__(timeout=60)
        self.work_cog = work_cog
        self.user_job = user_job
        self.original_user_id = original_user_id
        self.used = False

    async def complete_work(self, interaction, action, multiplier):
        """Complete work with given multiplier"""
        # Update work timestamp to set cooldown
        await update_work_timestamp(interaction.user.id)
        
        # Calculate wage based on job and boss relationship
        base_wage = calculate_wage(
            self.user_job["job_info"], 
            self.user_job["boss_hostile"], 
            self.user_job["boss_loyalty"]
        )
        final_wage = int(base_wage * multiplier)
        
        # Update user's wallet
        await db.update_wallet(interaction.user.id, final_wage, interaction.guild.id)
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        embed = discord.Embed(
            title=f"{self.user_job['job_info']['emoji']} Work Complete",
            description=f"You {action} and earned **{final_wage:,}** {CURRENCY}!",
            color=0x2ecc71
        )
        embed.add_field(name="💰 Earnings", value=f"+{final_wage:,} {CURRENCY}", inline=True)
        await interaction.response.edit_message(embed=embed, view=self)

    async def check_user_permission(self, interaction):
        """Check if user can interact with this minigame"""
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("You can't work someone else's job!", ephemeral=True)
            return False
        if self.used:
            await interaction.response.send_message("You already completed this work session!", ephemeral=True)
            return False
        return True

class ModerationMinigame(BaseMinigame):
    """Minigame for Discord Moderator job"""

    @discord.ui.button(label="Ban Spam Bot", style=discord.ButtonStyle.danger, emoji="🔨")
    async def ban_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "banned a spam bot", 1.2)

    @discord.ui.button(label="Delete NSFW", style=discord.ButtonStyle.secondary, emoji="🗑️")
    async def delete_nsfw(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "deleted inappropriate content", 1.0)

    @discord.ui.button(label="Ignore Report", style=discord.ButtonStyle.success, emoji="😴")
    async def ignore_report(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "ignored a user report", 0.8)

class CryptoMinigame(BaseMinigame):
    """Minigame for Crypto Day Trader job"""

    @discord.ui.button(label="HODL 💎🙌", style=discord.ButtonStyle.primary, emoji="💎")
    async def hodl(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        success = random.choice([True, False])
        multiplier = 2.0 if success else 0.1
        action = "diamond handed to the moon" if success else "paper handed like a noob"
        await self.complete_work(interaction, action, multiplier)

    @discord.ui.button(label="Buy the Dip", style=discord.ButtonStyle.success, emoji="📉")
    async def buy_dip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "bought the dip", 1.3)

    @discord.ui.button(label="Panic Sell", style=discord.ButtonStyle.danger, emoji="📈")
    async def panic_sell(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "panic sold at a loss", 0.5)

class RedditMinigame(BaseMinigame):
    """Minigame for Reddit Admin job"""

    @discord.ui.button(label="Lock Thread", style=discord.ButtonStyle.danger, emoji="🔒")
    async def lock_thread(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "locked a controversial thread", 1.1)

    @discord.ui.button(label="Ban User", style=discord.ButtonStyle.secondary, emoji="🔨")
    async def ban_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "banned a problematic user", 1.3)

    @discord.ui.button(label="Remove Post", style=discord.ButtonStyle.success, emoji="🗑️")
    async def remove_post(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "removed rule-breaking content", 0.9)

class SimpMinigame(BaseMinigame):
    """Minigame for Pokimane Subscriber job"""

    @discord.ui.button(label="Donate $100", style=discord.ButtonStyle.primary, emoji="💸")
    async def donate_big(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        noticed = random.randint(1, 10) == 1  # 10% chance
        if noticed:
            await self.complete_work(interaction, "got noticed by your queen", 2.0)
        else:
            await self.complete_work(interaction, "donated but got ignored", 0.3)

    @discord.ui.button(label="Moderate Chat", style=discord.ButtonStyle.success, emoji="🛡️")
    async def moderate_chat(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "moderated chat for free", 0.8)

    @discord.ui.button(label="Subscribe Tier 3", style=discord.ButtonStyle.danger, emoji="👑")
    async def tier3_sub(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "became a tier 3 sub", 1.5)

class MemeMinigame(BaseMinigame):
    """Minigame for Professional Meme Poster job"""

    @discord.ui.button(label="Create OC", style=discord.ButtonStyle.primary, emoji="✨")
    async def create_oc(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        viral = random.randint(1, 5) == 1  # 20% chance
        if viral:
            await self.complete_work(interaction, "created a viral original meme", 2.0)
        else:
            await self.complete_work(interaction, "created OC that flopped", 0.7)

    @discord.ui.button(label="Repost Classic", style=discord.ButtonStyle.success, emoji="♻️")
    async def repost_classic(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "reposted a classic meme", 1.0)

    @discord.ui.button(label="Make Meta Meme", style=discord.ButtonStyle.secondary, emoji="🤔")
    async def meta_meme(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "made a meta meme about memes", 1.2)

class NFTMinigame(BaseMinigame):
    """Minigame for NFT Trader job"""

    @discord.ui.button(label="Right-Click Save", style=discord.ButtonStyle.danger, emoji="🖱️")
    async def right_click_save(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        caught = random.randint(1, 3) == 1  # 33% chance of getting caught
        if caught:
            await self.complete_work(interaction, "got sued for right-clicking", 0.1)
        else:
            await self.complete_work(interaction, "successfully pirated an NFT", 1.8)

    @discord.ui.button(label="Buy Ugly Ape", style=discord.ButtonStyle.primary, emoji="🐵")
    async def buy_ape(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        success = random.choice([True, False])
        if success:
            await self.complete_work(interaction, "flipped an ape for profit", 3.0)
        else:
            await self.complete_work(interaction, "bought an ape that rugged", 0.05)

    @discord.ui.button(label="Mint New Collection", style=discord.ButtonStyle.success, emoji="⚡")
    async def mint_collection(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "minted a new NFT collection", 1.5)

class TwitterMinigame(BaseMinigame):
    """Minigame for Twitter Social Justice Warrior job"""

    @discord.ui.button(label="Cancel Someone", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_someone(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        successful = random.randint(1, 4) == 1  # 25% chance
        if successful:
            await self.complete_work(interaction, "successfully canceled someone", 1.5)
        else:
            await self.complete_work(interaction, "failed to start a mob", 0.2)

    @discord.ui.button(label="Write Thread", style=discord.ButtonStyle.primary, emoji="🧵")
    async def write_thread(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "wrote a 47-tweet thread", 1.0)

    @discord.ui.button(label="Quote Tweet Dunk", style=discord.ButtonStyle.secondary, emoji="🏀")
    async def quote_tweet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "dunked on someone's tweet", 0.8)

class StreamingMinigame(BaseMinigame):
    """Minigame for Twitch Streamer job"""

    @discord.ui.button(label="Play Meta Game", style=discord.ButtonStyle.primary, emoji="🎮")
    async def play_meta(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        viewers = random.randint(1, 100)
        multiplier = min(2.0, 0.5 + (viewers * 0.015))  # Scale with viewers
        await self.complete_work(interaction, f"streamed to {viewers} viewers", multiplier)

    @discord.ui.button(label="React to Videos", style=discord.ButtonStyle.success, emoji="📺")
    async def react_content(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        dmca = random.randint(1, 10) == 1  # 10% chance of DMCA
        if dmca:
            await self.complete_work(interaction, "got DMCA'd mid-stream", 0.1)
        else:
            await self.complete_work(interaction, "reacted to YouTube videos", 1.2)

    @discord.ui.button(label="Chat with Viewers", style=discord.ButtonStyle.secondary, emoji="💬")
    async def chat_viewers(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "chatted with your 3 viewers", 0.9)

class DefaultMinigame(BaseMinigame):
    """Default minigame for jobs without specific minigames"""

    @discord.ui.button(label="Work Hard", style=discord.ButtonStyle.primary, emoji="💪")
    async def work_hard(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "worked diligently", 1.2)

    @discord.ui.button(label="Take Break", style=discord.ButtonStyle.success, emoji="☕")
    async def take_break(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "took a well-deserved break", 0.8)

    @discord.ui.button(label="Phone It In", style=discord.ButtonStyle.secondary, emoji="📱")
    async def phone_in(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_user_permission(interaction):
            return
        self.used = True
        await self.complete_work(interaction, "did the bare minimum", 0.9)

# Minigame factory function
def get_minigame_class(job_id: str):
    """Get the appropriate minigame class for a job"""
    minigame_map = {
        "discord_mod": ModerationMinigame,
        "reddit_admin": RedditMinigame,
        "pokimane_sub": SimpMinigame,
        "meme_poster": MemeMinigame,
        "nft_trader": NFTMinigame,
        "crypto_investor": CryptoMinigame,
        "twitter_warrior": TwitterMinigame,
        "twitch_streamer": StreamingMinigame
    }
    return minigame_map.get(job_id, DefaultMinigame)
