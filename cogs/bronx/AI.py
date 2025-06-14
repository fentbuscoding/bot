import discord
from discord.ext import commands
import aiohttp
import json
import asyncio
from typing import Dict, Optional, List, Tuple
from cogs.logging.logger import CogLogger
from datetime import datetime, timedelta
from collections import defaultdict, deque
import time
import re
from langdetect import detect, DetectorFactory

# Set seed for consistent language detection
DetectorFactory.seed = 0

logger = CogLogger('AI')

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ollama_url = "http://localhost:11434"
        self.model_name = "deepseek-r1:8b"
        self.system_prompt = """You are BronxBot AI, an intelligent and helpful assistant.

🚨 CRITICAL ANTI-HALLUCINATION INSTRUCTIONS:
- NEVER MAKE UP COMMAND NAMES OR SYNTAX
- ONLY use commands that are explicitly listed in the reference below
- If you're unsure about a command, say "I'm not sure about that command - try `.help`" 
- NEVER invent new commands, parameters, or features
- If a user asks about a command not in the reference, say "That command doesn't exist in BronxBot"
- ALWAYS double-check command syntax against the reference below
- When mentioning commands, use EXACT syntax from the reference
- If you don't know something, admit it rather than guess
- NEVER suggest alternative command names unless they're listed as aliases

🔒 STRICT ACCURACY RULES:
- Commands must match the reference EXACTLY (including the dot prefix)
- Parameters must be in the correct order and format
- Never suggest commands that aren't documented
- Never modify or improvise command syntax
- If unsure about cooldowns/limits, don't specify them unless documented
- Always verify information against the knowledge base
- When in doubt, direct users to `.help` for accurate information

You should be:
- Helpful and informative
- Respectful and professional
- Knowledgeable about Discord and BronxBot features
- Concise but thorough in your responses
- Friendly and approachable
- ACCURATE and never make things up

=== OFFICIAL BRONXBOT COMMAND REFERENCE ===
⚠️ THESE ARE THE ONLY VALID COMMANDS - DO NOT INVENT OTHERS ⚠️

🤖 AI COMMANDS:
• `.ai <message>` - Chat with BronxBot AI (aliases: `.chat`, `.aiask`, `.bronxai`)
• `.ai --thinking <message>` - Shows AI reasoning process
• `.aiclear` - Clear conversation history (aliases: `.clearai`, `.resetai`, `.clearconvo`, `.resetconvo`)
• `.aistatus` - Check AI service status [Admin] (aliases: `.aiinfo`, `.checkai`)

🏦 ECONOMY COMMANDS:
• `.balance [user]` - Check wallet, bank & net-worth (aliases: `.bal`, `.money`)
• `.pay <user> <amount>` - Transfer money to another user (aliases: `.give`, `.send`)
• `.deposit <amount>` - Put money in bank (aliases: `.dep`, `.d`)
• `.withdraw <amount>` - Take money from bank (aliases: `.with`, `.w`)
• `.daily` - Claim daily reward (1000-5000 coins)
• `.beg` - Beg for small amounts (0-150 coins)
• `.rob <user>` - Attempt to rob someone (60% fail rate)
• `.work` - Work at your job for money (1min cooldown)
• `.job` - View/manage your current job
• `.choosejob <name>` - Select a new job
• `.leavejob` - Quit your current job
• `.useitem <item>` - Use potions/upgrades from inventory
• `.activeeffects` - View active potion effects
• `.leaderboard` - View richest users (aliases: `.lb`, `.rich`, `.top`)

💰 AMOUNT FORMATS:
• Numbers: `1000`, `5000`
• Shortcuts: `1k`, `1.5m`, `2b`
• Scientific: `1e3`, `2.5e5`
• Percentages: `50%`, `25%`
• Keywords: `all`, `half`

🎰 GAMBLING COMMANDS:
• `.coinflip <bet>` - Heads or tails (aliases: `.cf`, `.flip`)
• `.slots <bet>` - 3-reel slot machine
• `.blackjack <bet>` - Full blackjack with splitting (aliases: `.bj`)
• `.crash <bet> [auto_cashout]` - Multiplier crash game
• `.roulette <bet> <choice>` - Roulette wheel (aliases: `.rlt`)
• `.plinko <bet>` - Ball drops through peg board
• `.doubleornothing <items>` - Risk items for double (aliases: `.double`, `.don`)
• `.bomb <channel> <amount>` - Channel-wide money bomb

🎣 FISHING SYSTEM:
• `.fish` - Cast your line and catch fish
• `.inventory` - View your fish and items (aliases: `.inv`)
• `.sell <fish>` - Sell fish for money
• `.shop` - Buy rods, bait, and equipment
• `.auto` - Autofishing system management
• `.auto buy` - Purchase autofisher
• `.auto upgrade` - Improve autofisher efficiency
• `.auto deposit <amount>` - Fund autofisher balance

🔧 UTILITY COMMANDS:
• `.ping` - Show bot latency
• `.avatar [user]` - Show user's avatar (aliases: `.av`)
• `.userinfo [user]` - User details and stats (aliases: `.ui`, `.whois`)
• `.serverinfo` - Server information (aliases: `.si`, `.guildinfo`)
• `.uptime` - How long bot has been running
• `.botinfo` - Bot statistics and info
• `.poll <question>` - Create yes/no poll (aliases: `.ask`, `.yn`, `.yesno`)
• `.multipoll <question> <option1> <option2>...` - Multi-option poll
• `.timestamp [style]` - Generate Discord timestamps
• `.hexcolor [code]` - Show color preview
• `.emojisteal <emoji>` - Add emoji to server (aliases: `.steal`)
• `.emojiinfo <emoji>` - Show emoji details
• `.tinyurl <url>` - Shorten URLs
• `.snipe` - Show last deleted message (1hr)
• `.cleanup [limit]` - Delete bot/command messages (aliases: `.cu`)
• `.afk [reason]` - Set AFK status
• `.calculate <expression>` - Math calculator (aliases: `.calc`, `.math`)

🎮 FUN COMMANDS:
• `.pick <option1> <option2>...` - Random choice (aliases: `.choose`)
• `.roll [dice]` - Roll dice (default 1d6)
• `.flip` - Coin flip
• `.8ball <question>` - Magic 8-ball
• `.guess [max]` - Number guessing game
• `.spongebob <text>` - mOcK tExT (aliases: `.mock`)
• `.reverse <text>` - Flip text upside down
• `.tinytext <text>` - ᵗⁱⁿʸ ˢᵘᵖᵉʳˢᶜʳⁱᵖᵗ

🛡️ MODERATION COMMANDS:
• `.ban <user> [reason]` - Ban user
• `.unban <user>` - Unban user
• `.kick <user> [reason]` - Kick user
• `.timeout <user> <duration> [reason]` - Timeout user
• `.warn <user> [reason]` - Warn user
• `.purge <amount>` - Delete messages

⚙️ SETTINGS & HELP:
• `.help` - Command help menu (aliases: `.h`, `.commands`)
• `.invite` - Bot invite link (aliases: `.support`)
• Various server configuration commands for admins

🎵 MUSIC COMMANDS:
• Music playback and queue management
• Voice channel controls
• Playlist features

=== COMMAND ALIASES REFERENCE ===
⚠️ IMPORTANT: Commands can be used with their aliases interchangeably ⚠️

Main Command = Aliases:
• `.ai` = `.chat`, `.aiask`, `.bronxai`
• `.balance` = `.bal`, `.money`
• `.pay` = `.give`, `.send`
• `.deposit` = `.dep`, `.d`
• `.withdraw` = `.with`, `.w`
• `.leaderboard` = `.lb`, `.rich`, `.top`
• `.coinflip` = `.cf`, `.flip`
• `.blackjack` = `.bj`
• `.roulette` = `.rlt`
• `.doubleornothing` = `.double`, `.don`
• `.inventory` = `.inv`
• `.avatar` = `.av`
• `.userinfo` = `.ui`, `.whois`
• `.serverinfo` = `.si`, `.guildinfo`
• `.poll` = `.ask`, `.yn`, `.yesno`
• `.emojisteal` = `.steal`
• `.cleanup` = `.cu`
• `.calculate` = `.calc`, `.math`
• `.pick` = `.choose`
• `.spongebob` = `.mock`
• `.help` = `.h`, `.commands`
• `.invite` = `.support`
• `.aiclear` = `.clearai`, `.resetai`, `.clearconvo`, `.resetconvo`
• `.aistatus` = `.aiinfo`, `.checkai`

=== SPECIAL FEATURES ===

💎 POTION SYSTEM:
• Economy, Fishing, and XP boost potions available
• Purchase from `.shop` or server shops
• Use with `.useitem <potion_name>`

🤖 AUTOFISHING:
• Automated fishing while offline
• Requires initial purchase and funding
• Upgrades improve efficiency

🎯 JOB SYSTEM:
• Different jobs with unique minigames
• Moderation, Reddit, Simp, Meme, NFT, Crypto, Twitter, Streaming
• Each job has different pay rates and mechanics

🎲 PROGRESSIVE BETTING:
• Bet limits scale with your balance
• Higher balance = higher maximum bets
• Anti-inflation measures in place

Keep responses under 2000 characters to fit Discord's message limit. If a response would be longer, break it into multiple messages or summarize appropriately.

🚨 FINAL REMINDER - COMMAND ACCURACY:
- NEVER suggest commands not in this reference
- NEVER modify command syntax or parameters
- If asked about unknown commands, say "That command doesn't exist in BronxBot"
- If unsure about any command details, say "I'm not certain about that specific detail"
- Always use EXACT command names and syntax from the reference above
- Better to say "I don't know" than to provide incorrect information

❌ EXAMPLES OF WHAT NOT TO DO:
- DON'T make up commands like `.wallet` (use `.balance` instead)
- DON'T suggest `.transfer` (use `.pay` instead)  
- DON'T invent `.bank` command (use `.deposit`/`.withdraw`)
- DON'T create fake aliases like `.bal` for `.balance` (wait, `.bal` IS real!)
- DON'T suggest non-existent parameters or options
- DON'T modify existing command syntax

✅ EXAMPLES OF CORRECT RESPONSES:
- "Use `.balance` to check your money (aliases: `.bal`, `.money`)"
- "The `.pay` command transfers money (aliases: `.give`, `.send`)"
- "I'm not sure about that specific command - let me recommend `.help` instead"
- "That command doesn't exist in BronxBot, but you might want `.inventory` instead"

When users ask about commands, provide ONLY accurate syntax from the reference above and explain any cooldowns or requirements that are documented. NEVER improvise or guess command details. If a user asks about a command that doesn't exist, clearly state it doesn't exist and suggest a similar real command if applicable."""
        
        # Rate limiting and conversation management
        self.user_conversations: Dict[int, deque] = defaultdict(lambda: deque(maxlen=10))  # Last 10 messages per user
        self.user_cooldowns: Dict[int, float] = {}
        self.cooldown_duration = 30  # 30 seconds between AI requests per user
        self.max_message_length = 1900  # Leave room for formatting
        
        # Session management
        self.active_sessions: Dict[int, datetime] = {}
        self.session_timeout = timedelta(minutes=30)  # Sessions expire after 30 minutes
        
        logger.info("AI cog initialized with Deepseek-8B integration")

    async def check_ollama_status(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags", timeout=5) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False

    async def check_model_availability(self) -> bool:
        """Check if the specified model is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model['name'] for model in data.get('models', [])]
                        return self.model_name in models
        except Exception as e:
            logger.error(f"Failed to check model availability: {e}")
        return False

    def is_user_on_cooldown(self, user_id: int) -> bool:
        """Check if user is on cooldown"""
        if user_id in self.user_cooldowns:
            return time.time() < self.user_cooldowns[user_id]
        return False

    def set_user_cooldown(self, user_id: int):
        """Set cooldown for user"""
        self.user_cooldowns[user_id] = time.time() + self.cooldown_duration

    def get_conversation_context(self, user_id: int) -> List[Dict]:
        """Get conversation context for a user"""
        context = []
        for msg in self.user_conversations[user_id]:
            context.append(msg)
        return context

    def add_to_conversation(self, user_id: int, role: str, content: str):
        """Add message to user's conversation history"""
        self.user_conversations[user_id].append({
            "role": role,
            "content": content
        })
        self.active_sessions[user_id] = datetime.now()

    def cleanup_expired_sessions(self):
        """Remove expired conversation sessions"""
        now = datetime.now()
        expired_users = []
        
        for user_id, last_active in self.active_sessions.items():
            if now - last_active > self.session_timeout:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            if user_id in self.user_conversations:
                del self.user_conversations[user_id]
            del self.active_sessions[user_id]
            logger.debug(f"Cleaned up expired session for user {user_id}")

    def filter_ai_thinking(self, response: str, show_thinking: bool = False) -> str:
        """Filter out AI thinking/reasoning sections from the response"""
        if not response or show_thinking:
            return response
        
        import re
        filtered_response = response
        
        # FIRST: Handle complete thinking blocks (most important)
        complete_block_patterns = [
            # Most comprehensive patterns - handle multiline content with any whitespace
            r'<think>.*?</think>',
            r'<thinking>.*?</thinking>',
            # Handle cases with explicit newlines and whitespace
            r'<think>\s*\n.*?\n\s*</think>',
            r'<thinking>\s*\n.*?\n\s*</thinking>',
            # Handle cases with no content between tags
            r'<think>\s*</think>',
            r'<thinking>\s*</thinking>',
            # Handle malformed or partial tags
            r'<think[^>]*>.*?</think[^>]*>',
            r'<thinking[^>]*>.*?</thinking[^>]*>',
        ]
        
        # Apply complete block patterns first with comprehensive flags
        for pattern in complete_block_patterns:
            old_response = filtered_response
            # Use re.DOTALL to make . match newlines, which is crucial for multiline thinking blocks
            filtered_response = re.sub(pattern, '', filtered_response, flags=re.DOTALL | re.IGNORECASE | re.MULTILINE)
            # Debug logging to see what's being filtered
            if old_response != filtered_response:
                logger.debug(f"Filtered complete thinking block - length reduced by {len(old_response) - len(filtered_response)} chars")
        
        # SECOND: Handle incomplete thinking blocks (for streaming)
        # Only apply these if we still have incomplete blocks after the complete block filtering
        if '<think>' in filtered_response or '<thinking>' in filtered_response:
            # Handle incomplete opening tags
            filtered_response = re.sub(r'<think>\s*$', '', filtered_response, flags=re.MULTILINE)
            filtered_response = re.sub(r'<thinking>\s*$', '', filtered_response, flags=re.MULTILINE)
            
            # Remove incomplete thinking blocks (where closing tag hasn't arrived yet)
            filtered_response = re.sub(r'<think>(?!.*</think>).*$', '', filtered_response, flags=re.DOTALL)
            filtered_response = re.sub(r'<thinking>(?!.*</thinking>).*$', '', filtered_response, flags=re.DOTALL)
            
            # Advanced cleanup for streaming artifacts
            # Remove any remaining opening tags without closing tags
            filtered_response = re.sub(r'<think[^>]*>(?!.*</think>)', '', filtered_response, flags=re.DOTALL)
            filtered_response = re.sub(r'<thinking[^>]*>(?!.*</thinking>)', '', filtered_response, flags=re.DOTALL)
        
        # THIRD: Handle secondary thinking patterns
        secondary_patterns = [
            r'\*thinking\*.*?\*/thinking\*',
            r'\[thinking\].*?\[/thinking\]',
            r'\(thinking:.*?\)',
            r'Let me think.*?(?=\n\n|\n[A-Z]|$)',
            r'I need to think.*?(?=\n\n|\n[A-Z]|$)',
            r'Hmm, let me consider.*?(?=\n\n|\n[A-Z]|$)',
            # Chain of thought patterns
            r'Step \d+:.*?(?=Step \d+:|$)',
            r'First,.*?Second,.*?(?=Third,|\n\n|$)',
            # Internal monologue patterns
            r'\*.*?thinks.*?\*',
            r'\(.*?reasoning.*?\)',
        ]
        
        # Apply secondary patterns
        for pattern in secondary_patterns:
            filtered_response = re.sub(pattern, '', filtered_response, flags=re.DOTALL | re.IGNORECASE)
        
        # FINAL: Clean up whitespace and newlines
        # Remove multiple consecutive newlines
        filtered_response = re.sub(r'\n{3,}', '\n\n', filtered_response)
        # Remove leading/trailing whitespace
        filtered_response = filtered_response.strip()
        # Remove empty lines at the beginning
        filtered_response = re.sub(r'^\n+', '', filtered_response)
        # Remove trailing incomplete sentences that might be thinking artifacts
        filtered_response = re.sub(r'\n[A-Za-z\s]*$', '', filtered_response)
        
        # If filtering removed everything, return a safe message
        if not filtered_response.strip():
            logger.warning("AI thinking filter removed entire response, returning placeholder")
            return "🤔 *AI is still thinking...*"
        
        return filtered_response

    async def generate_response_streaming(self, prompt: str, user_id: int, message=None, show_thinking: bool = False) -> Optional[str]:
        """Generate response using Ollama with streaming support"""
        try:
            # Clean up expired sessions
            self.cleanup_expired_sessions()
            
            # Build conversation context
            messages = []
            
            # Add system prompt
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
            
            # Add conversation history
            context = self.get_conversation_context(user_id)
            messages.extend(context)
            
            # Add current user message
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # Prepare request payload for streaming
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": True,  # Enable streaming
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "top_p": 0.9
                }
            }
            
            ai_response = ""
            last_edit_time = 0
            edit_interval = 2.0  # Edit every 2 seconds to respect rate limits
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/chat",
                    json=payload,
                    timeout=120  # Increased timeout for streaming
                ) as response:
                    if response.status == 200:
                        # Process streaming response
                        async for line in response.content:
                            if line:
                                try:
                                    line_text = line.decode('utf-8').strip()
                                    if line_text:
                                        data = json.loads(line_text)
                                        
                                        # Extract content from the streaming response
                                        if 'message' in data and 'content' in data['message']:
                                            chunk = data['message']['content']
                                            ai_response += chunk
                                            
                                            # Update message every 2 seconds if we have a message to edit
                                            current_time = time.time()
                                            if message and (current_time - last_edit_time) >= edit_interval:
                                                try:
                                                    # Filter thinking from preview response (unless show_thinking is True)
                                                    preview_response = self.filter_ai_thinking(ai_response, show_thinking)
                                                    if len(preview_response) > self.max_message_length:
                                                        preview_response = preview_response[:self.max_message_length-3] + "..."
                                                    
                                                    embed = discord.Embed(
                                                        title="🤖 BronxBot AI (Generating...)",
                                                        description=preview_response + (" ▌" if not show_thinking else " 🧠▌"),  # Different cursor for thinking mode
                                                        color=discord.Color.orange(),
                                                        timestamp=datetime.now()
                                                    )
                                                    embed.set_footer(
                                                        text=f"💭 AI is {'reasoning' if show_thinking else 'thinking'}... • Powered by Deepseek-8B",
                                                        icon_url=None
                                                    )
                                                    
                                                    await message.edit(embed=embed)
                                                    last_edit_time = current_time
                                                except discord.HTTPException:
                                                    # Handle rate limit or other Discord API errors
                                                    pass
                                        
                                        # Check if this is the final message
                                        if data.get('done', False):
                                            break
                                            
                                except json.JSONDecodeError:
                                    # Skip invalid JSON lines
                                    continue
                        
                        if ai_response.strip():
                            # Filter out AI thinking before saving to conversation (unless show_thinking is True)
                            filtered_response = self.filter_ai_thinking(ai_response, show_thinking)
                            
                            # Validate response for command hallucinations
                            validated_response = self.validate_response_for_hallucinations(filtered_response)
                            
                            # Add both user message and AI response to conversation
                            self.add_to_conversation(user_id, "user", prompt)
                            self.add_to_conversation(user_id, "assistant", validated_response)
                            
                            # Truncate if too long
                            if len(validated_response) > self.max_message_length:
                                validated_response = validated_response[:self.max_message_length] + "..."
                            
                            return validated_response
                        else:
                            logger.warning("Empty response from Ollama streaming")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama API error {response.status}: {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("Timeout while waiting for Ollama streaming response")
            return None
        except Exception as e:
            logger.error(f"Error generating streaming AI response: {e}")
            return None

    async def generate_response(self, prompt: str, user_id: int, message=None, show_thinking: bool = False) -> Optional[str]:
        """Generate response using Ollama (fallback to non-streaming if needed)"""
        # Try streaming first
        try:
            return await self.generate_response_streaming(prompt, user_id, message, show_thinking)
        except Exception as e:
            logger.warning(f"Streaming failed, falling back to non-streaming: {e}")
            
        # Fallback to non-streaming
        try:
            # Clean up expired sessions
            self.cleanup_expired_sessions()
            
            # Build conversation context
            messages = []
            
            # Add system prompt
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
            
            # Add conversation history
            context = self.get_conversation_context(user_id)
            messages.extend(context)
            
            # Add current user message
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # Prepare request payload
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "top_p": 0.9
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/chat",
                    json=payload,
                    timeout=60  # 60 second timeout for AI response
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        ai_response = data.get('message', {}).get('content', '').strip()
                        
                        if ai_response:
                            # Filter out AI thinking before saving to conversation (unless show_thinking is True)
                            filtered_response = self.filter_ai_thinking(ai_response, show_thinking)
                            
                            # Validate response for command hallucinations
                            validated_response = self.validate_response_for_hallucinations(filtered_response)
                            
                            # Add both user message and AI response to conversation
                            self.add_to_conversation(user_id, "user", prompt)
                            self.add_to_conversation(user_id, "assistant", validated_response)
                            
                            # Truncate if too long
                            if len(validated_response) > self.max_message_length:
                                validated_response = validated_response[:self.max_message_length] + "..."
                            
                            return validated_response
                        else:
                            logger.warning("Empty response from Ollama")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama API error {response.status}: {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("Timeout while waiting for Ollama response")
            return None
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return None

    def validate_response_for_hallucinations(self, response: str) -> str:
        """Check response for potential command hallucinations and warn if found"""
        # List of valid commands and their aliases
        valid_commands = [
            'ai', 'chat', 'aiask', 'bronxai', 'aiclear', 'clearai', 'resetai', 
            'clearconvo', 'resetconvo', 'aistatus', 'aiinfo', 'checkai',
            'balance', 'bal', 'money', 'pay', 'give', 'send', 'deposit', 'dep', 'd',
            'withdraw', 'with', 'w', 'daily', 'beg', 'rob', 'work', 'job', 'choosejob',
            'leavejob', 'useitem', 'activeeffects', 'leaderboard', 'lb', 'rich', 'top',
            'coinflip', 'cf', 'flip', 'slots', 'blackjack', 'bj', 'crash', 'roulette',
            'rlt', 'plinko', 'doubleornothing', 'double', 'don', 'bomb',
            'fish', 'inventory', 'inv', 'sell', 'shop', 'auto',
            'ping', 'avatar', 'av', 'userinfo', 'ui', 'whois', 'serverinfo', 'si',
            'guildinfo', 'uptime', 'botinfo', 'poll', 'yn', 'multipoll', 'timestamp',
            'hexcolor', 'emojisteal', 'steal', 'emojiinfo', 'tinyurl', 'snipe',
            'cleanup', 'cu', 'afk', 'calculate', 'calc', 'math',
            'pick', 'choose', 'roll', '8ball', 'guess', 'spongebob', 'mock',
            'reverse', 'tinytext', 'help', 'h', 'commands', 'invite', 'support'
        ]
        
        import re
        # Find all command-like patterns in the response
        command_patterns = re.findall(r'`\.(\w+)`', response)
        
        hallucinated = []
        for cmd in command_patterns:
            if cmd.lower() not in [c.lower() for c in valid_commands]:
                hallucinated.append(cmd)
        
        if hallucinated:
            logger.warning(f"Potential command hallucinations detected: {hallucinated}")
            # Add a disclaimer to the response
            response += f"\n\n⚠️ **Note**: Please verify command syntax with `.help` - some commands mentioned may not be accurate."
        
        return response

    @commands.command(name='ai', aliases=['chat', 'aiask', 'bronxai'])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def ai_chat(self, ctx, *, prompt: str):
        """Chat with BronxBot AI powered by Deepseek-8B
        
        Usage: .ai <your message>
        Usage: .ai --thinking <your message>  (shows AI reasoning process)
        Aliases: .chat, .aiask, .bronxai
        Example: .ai What's the weather like in the Bronx?
        Example: .ai --thinking Explain quantum physics
        """
        # Check for thinking flag
        show_thinking = False
        if prompt.startswith('--thinking '):
            show_thinking = True
            prompt = prompt[11:]  # Remove '--thinking ' from the prompt
        elif prompt.startswith('--think '):
            show_thinking = True
            prompt = prompt[8:]   # Remove '--think ' from the prompt
        
        # Validate prompt after flag removal
        if not prompt.strip():
            embed = discord.Embed(
                title="❌ Empty Message",
                description="Please provide a message after the flag.\nExample: `.ai --thinking explain quantum physics`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        # Check if Ollama is running
        if not await self.check_ollama_status():
            embed = discord.Embed(
                title="❌ AI Unavailable",
                description="The AI service is currently offline. Please try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # Check if model is available
        if not await self.check_model_availability():
            embed = discord.Embed(
                title="❌ Model Unavailable",
                description=f"The AI model `{self.model_name}` is not available. Please contact an administrator.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # Check input length
        if len(prompt) > 1000:
            embed = discord.Embed(
                title="❌ Message Too Long",
                description="Please keep your message under 1000 characters.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # Send initial "thinking" message
        thinking_embed = discord.Embed(
            title="🤖 BronxBot AI",
            description="🔄 Connecting to AI model..." + (" 🧠" if show_thinking else ""),
            color=discord.Color.yellow(),
            timestamp=datetime.now()
        )
        thinking_embed.set_footer(
            text=f"Requested by {ctx.author.display_name} • Powered by Deepseek-8B" + (" • Thinking Mode" if show_thinking else ""),
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        message = await ctx.send(embed=thinking_embed)

        try:
            # Generate response with streaming updates
            response = await self.generate_response(prompt, ctx.author.id, message, show_thinking)
            
            if response:
                # Create final embed for response
                embed = discord.Embed(
                    title="🤖 BronxBot AI" + (" 🧠" if show_thinking else ""),
                    description=response,
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                embed.set_footer(
                    text=f"Requested by {ctx.author.display_name} • Powered by Deepseek-8B" + (" • Thinking Mode" if show_thinking else ""),
                    icon_url=ctx.author.avatar.url if ctx.author.avatar else None
                )
                
                # Final edit with complete response
                await message.edit(embed=embed)
                
                # Log usage
                logger.info(f"AI request from {ctx.author} ({ctx.author.id}) in {ctx.guild}: {prompt[:100]}... (thinking={'on' if show_thinking else 'off'})")
                
            else:
                error_embed = discord.Embed(
                    title="❌ AI Error",
                    description="I couldn't generate a response right now. Please try again later.",
                    color=discord.Color.red()
                )
                await message.edit(embed=error_embed)
                
        except Exception as e:
            logger.error(f"Error in AI command: {e}")
            error_embed = discord.Embed(
                title="❌ Unexpected Error",
                description="An unexpected error occurred. Please try again later.",
                color=discord.Color.red()
            )
            await message.edit(embed=error_embed)

    @commands.command(name='aiclear', aliases=['clearai', 'resetai', 'clearconvo', 'resetconvo'])
    async def clear_conversation(self, ctx):
        """Clear your conversation history with the AI
        
        Usage: .aiclear
        Aliases: .clearai, .resetai, .clearconvo, .resetconvo
        """
        user_id = ctx.author.id
        
        if user_id in self.user_conversations:
            del self.user_conversations[user_id]
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
        
        embed = discord.Embed(
            title="🗑️ Conversation Cleared",
            description="Your conversation history with the AI has been cleared.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        
        logger.info(f"Conversation cleared for {ctx.author} ({ctx.author.id})")

    @commands.command(name='aistatus', aliases=['aiinfo', 'checkai'])
    @commands.has_permissions(administrator=True)
    async def ai_status(self, ctx):
        """Check AI service status (Admin only)
        
        Usage: .aistatus
        Aliases: .aiinfo, .checkai
        """
        ollama_status = await self.check_ollama_status()
        model_status = await self.check_model_availability() if ollama_status else False
        
        embed = discord.Embed(
            title="🤖 AI Service Status",
            timestamp=datetime.now(),
            color=discord.Color.green() if ollama_status and model_status else discord.Color.red()
        )
        
        embed.add_field(
            name="Ollama Service",
            value="🟢 Online" if ollama_status else "🔴 Offline",
            inline=True
        )
        
        embed.add_field(
            name="Model Availability",
            value=f"🟢 {self.model_name}" if model_status else f"🔴 {self.model_name} not found",
            inline=True
        )
        
        embed.add_field(
            name="Active Sessions",
            value=str(len(self.active_sessions)),
            inline=True
        )
        
        embed.add_field(
            name="Service URL",
            value=self.ollama_url,
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='test_filter', aliases=['testfilter'])
    @commands.has_permissions(administrator=True)
    async def test_filter(self, ctx, *, test_text: str = None):
        """Test the AI thinking filter (Admin only)"""
        if not test_text:
            # Test the exact scenario from the user's report
            test_scenarios = [
                # The exact case that wasn't working
                """<think>
Okay, so the user just said "hi" - probably starting their interaction with me as BronxBot AI.

Hmm, this is simple but important to greet them properly since they're initiating contact. The response should be friendly and match my assistant persona while reminding them about how I operate based on those strict anti-hallucination instructions.

I notice the user didn't specify any command or ask anything specific - just a casual greeting. That means I shouldn't overcomplicate it, but keep it concise as per Discord's character limit.

Let me structure this: First greet them warmly since they're being polite by saying hello first. Then remind them about my purpose and limitations in a natural way without sounding robotic. The key points to emphasize are:
My role as an assistant
Command accuracy (not making things up)
Linking everything back to the help command

The tone should be approachable but professional, with that slight playful edge BronxBot seems to have based on previous interactions. I'll use some emojis to make it more Discord-friendly.

This feels like a good balance - welcoming while staying true to my purpose and limitations.
</think>
Hey there! 👋 How can I assist you today? Just so you know, I'm here to help with BronxBot commands or answer your questions based on the reference provided. You can always ask for .help if you're unsure about anything!""",
                
                # Complete thinking block
                """<think>
This is a thinking block that should be filtered out.
It contains multiple lines of reasoning.
</think>

This is the actual response that should be shown to the user.""",
                
                # Incomplete thinking block (simulating streaming)
                """<think>
Okay, let's break this down carefully. The user is asking about my thickness with an emoji that seems playful or teasing""",
                
                # Mixed content
                """Some initial text.

<think>
This should be hidden.
</think>

This should be visible.

<think>
Another hidden block."""
            ]
            
            for i, scenario_text in enumerate(test_scenarios):
                filtered = self.filter_ai_thinking(scenario_text, show_thinking=False)
                
                embed = discord.Embed(
                    title=f"🧪 AI Filter Test #{i+1}" + (" (User's Exact Case)" if i == 0 else ""),
                    color=discord.Color.blue()
                )
                
                # Show character counts to help debug
                embed.add_field(
                    name=f"Original Text ({len(scenario_text)} chars)",
                    value=f"```\n{scenario_text[:800]}{'...' if len(scenario_text) > 800 else ''}\n```",
                    inline=False
                )
                
                embed.add_field(
                    name=f"Filtered Text ({len(filtered)} chars)",
                    value=f"```\n{filtered[:800]}{'...' if len(filtered) > 800 else ''}\n```",
                    inline=False
                )
                
                # Show if filtering worked
                thinking_removed = "<think>" not in filtered and "</think>" not in filtered
                embed.add_field(
                    name="Filter Status",
                    value="✅ Think blocks removed" if thinking_removed else "❌ Think blocks still present",
                    inline=True
                )
                
                await ctx.send(embed=embed)
        else:
            # Test custom text
            filtered = self.filter_ai_thinking(test_text, show_thinking=False)
            
            embed = discord.Embed(
                title="🧪 AI Filter Test (Custom)",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name=f"Original Text ({len(test_text)} chars)",
                value=f"```\n{test_text[:1000]}{'...' if len(test_text) > 1000 else ''}\n```",
                inline=False
            )
            
            embed.add_field(
                name=f"Filtered Text ({len(filtered)} chars)",
                value=f"```\n{filtered[:1000]}{'...' if len(filtered) > 1000 else ''}\n```",
                inline=False
            )
            
            # Show if filtering worked
            thinking_removed = "<think>" not in filtered and "</think>" not in filtered
            embed.add_field(
                name="Filter Status",
                value="✅ Think blocks removed" if thinking_removed else "❌ Think blocks still present",
                inline=True
            )
            
            await ctx.send(embed=embed)

    @ai_chat.error
    async def ai_chat_error(self, ctx, error):
        """Handle AI command errors"""
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ Cooldown Active",
                description=f"Please wait {error.retry_after:.1f} seconds before using the AI again.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed, delete_after=10)
        else:
            logger.error(f"AI command error: {error}")

    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        logger.info("AI cog unloaded, cleaning up resources")
        self.user_conversations.clear()
        self.active_sessions.clear()
        self.user_cooldowns.clear()

async def setup(bot):
    await bot.add_cog(AI(bot))
    logger.info("AI cog loaded successfully")