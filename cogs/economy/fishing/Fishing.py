# Advanced Fishing System v2.0
# Completely rebalanced with massive fish database, rod breaking, fish escaping, and suspense mechanics

from discord.ext import commands
from cogs.logging.logger import CogLogger
from utils.db import async_db as db
from utils.safe_reply import safe_reply
import discord
import random
import uuid
import datetime
import asyncio
import math

class Fishing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = CogLogger(self.__class__.__name__)
        self.currency = "<:bronkbuk:1377389238290747582>"
        self.blocked_channels = [1378156495144751147, 1260347806699491418]
        
        # Load rod data from both sources and combine them
        self.rod_data = self._load_all_rod_data()
        
        # Load bait data from both sources
        self.bait_data = self._load_all_bait_data()
        
        # Load aliases dynamically from JSON files
        self.rod_aliases = self._load_rod_aliases()
        self.bait_aliases = self._load_bait_aliases()
        # REBALANCED FISH DATABASE - More reasonable values and better progression
        self.fish_database = {
            "junk": [
                {"name": "Rusty Can", "min_weight": 0.2, "max_weight": 0.5, "base_value": 1, "escape_chance": 0.0},
                {"name": "Old Boot", "min_weight": 0.5, "max_weight": 1.2, "base_value": 2, "escape_chance": 0.0},
                {"name": "Plastic Bottle", "min_weight": 0.05, "max_weight": 0.2, "base_value": 1, "escape_chance": 0.0},
                {"name": "Seaweed Clump", "min_weight": 0.1, "max_weight": 0.3, "base_value": 5, "escape_chance": 0.0},
                {"name": "Broken Net", "min_weight": 0.3, "max_weight": 0.8, "base_value": 8, "escape_chance": 0.0}
            ],
            "tiny": [
                {"name": "Minnow", "min_weight": 0.01, "max_weight": 0.05, "base_value": 15, "escape_chance": 0.02},
                {"name": "Guppy", "min_weight": 0.01, "max_weight": 0.03, "base_value": 18, "escape_chance": 0.02},
                {"name": "Tetra", "min_weight": 0.01, "max_weight": 0.04, "base_value": 22, "escape_chance": 0.03},
                {"name": "Neon Fish", "min_weight": 0.01, "max_weight": 0.03, "base_value": 28, "escape_chance": 0.05},
                {"name": "Baby Goldfish", "min_weight": 0.02, "max_weight": 0.06, "base_value": 35, "escape_chance": 0.03},
                {"name": "Anchovy Fry", "min_weight": 0.005, "max_weight": 0.02, "base_value": 12, "escape_chance": 0.08},
                {"name": "Sardine Fry", "min_weight": 0.008, "max_weight": 0.03, "base_value": 16, "escape_chance": 0.06}
            ],
            "small": [
                {"name": "Goldfish", "min_weight": 0.05, "max_weight": 0.3, "base_value": 45, "escape_chance": 0.05},
                {"name": "Anchovy", "min_weight": 0.02, "max_weight": 0.1, "base_value": 30, "escape_chance": 0.08},
                {"name": "Sardine", "min_weight": 0.05, "max_weight": 0.2, "base_value": 38, "escape_chance": 0.06},
                {"name": "Small Perch", "min_weight": 0.1, "max_weight": 0.5, "base_value": 55, "escape_chance": 0.10},
                {"name": "Bluegill", "min_weight": 0.1, "max_weight": 0.4, "base_value": 50, "escape_chance": 0.08},
                {"name": "Sunfish", "min_weight": 0.08, "max_weight": 0.3, "base_value": 48, "escape_chance": 0.07},
                {"name": "Minnow School", "min_weight": 0.2, "max_weight": 0.6, "base_value": 75, "escape_chance": 0.15},
                {"name": "Killifish", "min_weight": 0.03, "max_weight": 0.15, "base_value": 42, "escape_chance": 0.12}
            ],
            "common": [
                {"name": "Bass", "min_weight": 0.3, "max_weight": 3.0, "base_value": 120, "escape_chance": 0.12},
                {"name": "Carp", "min_weight": 0.5, "max_weight": 8.0, "base_value": 110, "escape_chance": 0.15},
                {"name": "Trout", "min_weight": 0.2, "max_weight": 2.5, "base_value": 135, "escape_chance": 0.18},
                {"name": "Catfish", "min_weight": 0.8, "max_weight": 12.0, "base_value": 125, "escape_chance": 0.10},
                {"name": "Perch", "min_weight": 0.2, "max_weight": 1.5, "base_value": 105, "escape_chance": 0.15},
                {"name": "Pike", "min_weight": 1.0, "max_weight": 15.0, "base_value": 160, "escape_chance": 0.22},
                {"name": "Walleye", "min_weight": 0.5, "max_weight": 4.0, "base_value": 145, "escape_chance": 0.20},
                {"name": "Bream", "min_weight": 0.3, "max_weight": 2.0, "base_value": 95, "escape_chance": 0.12},
                {"name": "Roach", "min_weight": 0.1, "max_weight": 1.0, "base_value": 85, "escape_chance": 0.18},
                {"name": "Chub", "min_weight": 0.5, "max_weight": 3.5, "base_value": 115, "escape_chance": 0.14}
            ],
            "uncommon": [
                {"name": "Rainbow Trout", "min_weight": 0.8, "max_weight": 6.0, "base_value": 280, "escape_chance": 0.25},
                {"name": "Salmon", "min_weight": 2.0, "max_weight": 20.0, "base_value": 320, "escape_chance": 0.28},
                {"name": "Large Pike", "min_weight": 5.0, "max_weight": 25.0, "base_value": 380, "escape_chance": 0.32},
                {"name": "Striped Bass", "min_weight": 2.0, "max_weight": 18.0, "base_value": 340, "escape_chance": 0.30},
                {"name": "Muskie", "min_weight": 8.0, "max_weight": 30.0, "base_value": 420, "escape_chance": 0.35},
                {"name": "Red Snapper", "min_weight": 1.5, "max_weight": 8.0, "base_value": 300, "escape_chance": 0.25},
                {"name": "Mackerel", "min_weight": 0.8, "max_weight": 3.5, "base_value": 260, "escape_chance": 0.28},
                {"name": "Cod", "min_weight": 2.0, "max_weight": 12.0, "base_value": 290, "escape_chance": 0.22},
                {"name": "Halibut", "min_weight": 5.0, "max_weight": 40.0, "base_value": 450, "escape_chance": 0.26},
                {"name": "Flounder", "min_weight": 1.0, "max_weight": 5.0, "base_value": 275, "escape_chance": 0.20}
            ],
            "rare": [
                {"name": "Tuna", "min_weight": 15.0, "max_weight": 120.0, "base_value": 1200, "escape_chance": 0.40},
                {"name": "Mahi-Mahi", "min_weight": 8.0, "max_weight": 35.0, "base_value": 980, "escape_chance": 0.45},
                {"name": "Yellowfin Tuna", "min_weight": 20.0, "max_weight": 150.0, "base_value": 1350, "escape_chance": 0.48},
                {"name": "Marlin", "min_weight": 30.0, "max_weight": 300.0, "base_value": 1600, "escape_chance": 0.52},
                {"name": "Swordfish", "min_weight": 25.0, "max_weight": 250.0, "base_value": 1450, "escape_chance": 0.50},
                {"name": "Tarpon", "min_weight": 40.0, "max_weight": 120.0, "base_value": 1100, "escape_chance": 0.55},
                {"name": "King Salmon", "min_weight": 15.0, "max_weight": 50.0, "base_value": 920, "escape_chance": 0.42},
                {"name": "Sturgeon", "min_weight": 50.0, "max_weight": 400.0, "base_value": 1800, "escape_chance": 0.45},
                {"name": "Giant Grouper", "min_weight": 80.0, "max_weight": 300.0, "base_value": 1650, "escape_chance": 0.43},
                {"name": "Barracuda", "min_weight": 8.0, "max_weight": 45.0, "base_value": 850, "escape_chance": 0.48}
            ],
            "epic": [
                {"name": "Great White Shark", "min_weight": 500.0, "max_weight": 2500.0, "base_value": 8500, "escape_chance": 0.65},
                {"name": "Giant Bluefin Tuna", "min_weight": 200.0, "max_weight": 680.0, "base_value": 7200, "escape_chance": 0.60},
                {"name": "Atlantic Sturgeon", "min_weight": 150.0, "max_weight": 800.0, "base_value": 6800, "escape_chance": 0.55},
                {"name": "Giant Squid", "min_weight": 300.0, "max_weight": 1500.0, "base_value": 9200, "escape_chance": 0.70},
                {"name": "Hammerhead Shark", "min_weight": 200.0, "max_weight": 600.0, "base_value": 5800, "escape_chance": 0.65},
                {"name": "Tiger Shark", "min_weight": 180.0, "max_weight": 900.0, "base_value": 6200, "escape_chance": 0.65},
                {"name": "Bull Shark", "min_weight": 120.0, "max_weight": 400.0, "base_value": 4800, "escape_chance": 0.60},
                {"name": "Mako Shark", "min_weight": 150.0, "max_weight": 650.0, "base_value": 5500, "escape_chance": 0.70},
                {"name": "Giant Octopus", "min_weight": 100.0, "max_weight": 600.0, "base_value": 5200, "escape_chance": 0.65},
                {"name": "Manta Ray", "min_weight": 800.0, "max_weight": 2000.0, "base_value": 7800, "escape_chance": 0.50}
            ],
            "legendary": [
                {"name": "Colossal Squid", "min_weight": 1000.0, "max_weight": 5000.0, "base_value": 25000, "escape_chance": 0.75},
                {"name": "Whale Shark", "min_weight": 8000.0, "max_weight": 25000.0, "base_value": 45000, "escape_chance": 0.68},
                {"name": "Great Barracuda King", "min_weight": 200.0, "max_weight": 800.0, "base_value": 18000, "escape_chance": 0.72},
                {"name": "Emperor Tuna", "min_weight": 800.0, "max_weight": 1200.0, "base_value": 28000, "escape_chance": 0.65},
                {"name": "Ancient Coelacanth", "min_weight": 80.0, "max_weight": 200.0, "base_value": 55000, "escape_chance": 0.80},
                {"name": "Megamouth Shark", "min_weight": 2000.0, "max_weight": 8000.0, "base_value": 35000, "escape_chance": 0.70},
                {"name": "Giant Oarfish", "min_weight": 200.0, "max_weight": 600.0, "base_value": 42000, "escape_chance": 0.78},
                {"name": "Goblin Shark", "min_weight": 150.0, "max_weight": 500.0, "base_value": 32000, "escape_chance": 0.75}
            ],
            "mythical": [
                {"name": "Kraken", "min_weight": 50000.0, "max_weight": 200000.0, "base_value": 8500, "escape_chance": 0.85},
                {"name": "Leviathan", "min_weight": 80000.0, "max_weight": 300000.0, "base_value": 12000, "escape_chance": 0.88},
                {"name": "Ancient Megalodon", "min_weight": 30000.0, "max_weight": 150000.0, "base_value": 9500, "escape_chance": 0.85},
                {"name": "Sea Serpent", "min_weight": 25000.0, "max_weight": 120000.0, "base_value": 7800, "escape_chance": 0.87},
                {"name": "Jörmungandr", "min_weight": 100000.0, "max_weight": 500000.0, "base_value": 15000, "escape_chance": 0.90}
            ],
            "ancient": [
                {"name": "Dunkleosteus", "min_weight": 60000.0, "max_weight": 200000.0, "base_value": 35000, "escape_chance": 0.88},
                {"name": "Leedsichthys", "min_weight": 120000.0, "max_weight": 400000.0, "base_value": 55000, "escape_chance": 0.90},
                {"name": "Helicoprion", "min_weight": 40000.0, "max_weight": 150000.0, "base_value": 42000, "escape_chance": 0.89},
                {"name": "Xiphactinus", "min_weight": 25000.0, "max_weight": 100000.0, "base_value": 32000, "escape_chance": 0.88}
            ],
            "divine": [
                {"name": "Poseidon's Trident Fish", "min_weight": 200000.0, "max_weight": 800000.0, "base_value": 185000, "escape_chance": 0.92},
                {"name": "Neptune's Crown Jewel", "min_weight": 500000.0, "max_weight": 2000000.0, "base_value": 280000, "escape_chance": 0.95},
                {"name": "Oceanic Phoenix", "min_weight": 150000.0, "max_weight": 600000.0, "base_value": 220000, "escape_chance": 0.93}
            ],
            "cosmic": [
                {"name": "Stellar Whale", "min_weight": 1000000.0, "max_weight": 5000000.0, "base_value": 850000, "escape_chance": 0.94},
                {"name": "Void Leviathan", "min_weight": 2000000.0, "max_weight": 10000000.0, "base_value": 1250000, "escape_chance": 0.96},
                {"name": "Cosmic Kraken", "min_weight": 3000000.0, "max_weight": 15000000.0, "base_value": 1800000, "escape_chance": 0.97}
            ],
            "transcendent": [
                {"name": "The First Fish", "min_weight": 10000000.0, "max_weight": 50000000.0, "base_value": 8500000, "escape_chance": 0.96},
                {"name": "Alpha Omega", "min_weight": 25000000.0, "max_weight": 100000000.0, "base_value": 15000000, "escape_chance": 0.98}
            ],
            "mutated": [
                {"name": "Two-Headed Bass", "min_weight": 2.0, "max_weight": 8.0, "base_value": 1800, "escape_chance": 0.30},
                {"name": "Glowing Trout", "min_weight": 1.5, "max_weight": 6.0, "base_value": 2200, "escape_chance": 0.35},
                {"name": "Crystal Carp", "min_weight": 3.0, "max_weight": 12.0, "base_value": 2800, "escape_chance": 0.38},
                {"name": "Electric Eel-fish", "min_weight": 2.5, "max_weight": 10.0, "base_value": 3200, "escape_chance": 0.42},
                {"name": "Phase Salmon", "min_weight": 8.0, "max_weight": 25.0, "base_value": 4500, "escape_chance": 0.50},
                {"name": "Toxic Catfish", "min_weight": 5.0, "max_weight": 20.0, "base_value": 3800, "escape_chance": 0.35},
                {"name": "Neon Shark", "min_weight": 50.0, "max_weight": 200.0, "base_value": 12000, "escape_chance": 0.65}
            ],
            "crystalline": [
                {"name": "Diamond Angelfish", "min_weight": 5.0, "max_weight": 15.0, "base_value": 280, "escape_chance": 0.70},
                {"name": "Ruby Goldfish", "min_weight": 2.0, "max_weight": 8.0, "base_value": 220, "escape_chance": 0.65},
                {"name": "Sapphire Tuna", "min_weight": 80.0, "max_weight": 300.0, "base_value": 650, "escape_chance": 0.75},
                {"name": "Emerald Shark", "min_weight": 200.0, "max_weight": 800.0, "base_value": 1250, "escape_chance": 0.80}
            ],
            "void": [
                {"name": "Shadow Leviathan", "min_weight": 5000.0, "max_weight": 25000.0, "base_value": 8500, "escape_chance": 0.82},
                {"name": "Nightmare Squid", "min_weight": 8000.0, "max_weight": 40000.0, "base_value": 12000, "escape_chance": 0.85},
                {"name": "Abyss Walker", "min_weight": 12000.0, "max_weight": 60000.0, "base_value": 18000, "escape_chance": 0.87}
            ],
            "celestial": [
                {"name": "Starlight Manta", "min_weight": 20000.0, "max_weight": 100000.0, "base_value": 45000, "escape_chance": 0.90},
                {"name": "Moonbeam Whale", "min_weight": 50000.0, "max_weight": 250000.0, "base_value": 85000, "escape_chance": 0.92},
                {"name": "Solar Kraken", "min_weight": 80000.0, "max_weight": 400000.0, "base_value": 150000, "escape_chance": 0.94}
            ],
            "subatomic": [
                {"name": "Quantum Plankton", "min_weight": 0.2, "max_weight": 0.2, "base_value": 7000, "escape_chance": 0.95},
                {"name": "Nano-Bacteriophage", "min_weight": 0.0001, "max_weight": 0.001, "base_value": 5000, "escape_chance": 0.98},
                {"name": "Particle Fish", "min_weight": 0.05, "max_weight": 0.15, "base_value": 4500, "escape_chance": 0.90},
                {"name": "Microscopic Leviathan", "min_weight": 0.1, "max_weight": 0.3, "base_value": 8500, "escape_chance": 0.92},
                {"name": "Atomic Kraken", "min_weight": 0.01, "max_weight": 0.05, "base_value": 12000, "escape_chance": 0.96},
                {"name": "Subatomic Void Fish", "min_weight": 0.001, "max_weight": 0.01, "base_value": 20000, "escape_chance": 0.99},
                {"name": "Proton Swimmer", "min_weight": 0.0005, "max_weight": 0.005, "base_value": 3500, "escape_chance": 0.94},
                {"name": "Neutron Star Fish", "min_weight": 0.02, "max_weight": 0.08, "base_value": 18000, "escape_chance": 0.97}
            ]
        }
    async def cog_check(self, ctx):
        if ctx.channel.id in self.blocked_channels and not ctx.author.guild_permissions.administrator:
            await ctx.reply(
                random.choice([f"❌ Economy commands are disabled in this channel. "
                f"Please use them in another channel.",
                "<#1314685928614264852> is a good place for that."])
            )
            return False
        return True

    def _load_all_rod_data(self):
        """Load and combine rod data from both sources and combine them"""
        # Start with the hardcoded rod data - MUCH better durability for expensive rods
        combined_data = {
            "basic_rod": {
                "name": "Basic Rod", 
                "multiplier": 1.0, 
                "description": "A simple bamboo fishing rod",
                "durability": 0.90,  # 10% break chance
                "power": 1,
                "min_fish_weight": 0.1,
                "max_fish_weight": 5.0
            },
            "advanced_rod": {
                "name": "Advanced Rod", 
                "multiplier": 1.5, 
                "description": "A quality fiberglass rod",
                "durability": 0.95,  # 5% break chance
                "power": 2,
                "min_fish_weight": 0.1,
                "max_fish_weight": 15.0
            },
            "pro_rod": {
                "name": "Pro Rod", 
                "multiplier": 2.0, 
                "description": "Professional carbon fiber rod",
                "durability": 0.97,  # 3% break chance
                "power": 3,
                "min_fish_weight": 0.1,
                "max_fish_weight": 100.0  # Much higher weight limit
            },
            "expert_rod": {
                "name": "Expert Rod", 
                "multiplier": 1.8, 
                "description": "Precision-engineered rod with enhanced sensitivity",
                "durability": 0.975,  # 2.5% break chance
                "power": 3,
                "min_fish_weight": 0.1,
                "max_fish_weight": 200.0
            },
            "master_rod": {
                "name": "Master Rod", 
                "multiplier": 3.0, 
                "description": "Master craftsman's titanium rod",
                "durability": 0.985,  # 1.5% break chance
                "power": 4,
                "min_fish_weight": 0.1,
                "max_fish_weight": 500.0  # Even higher weight limit
            },
            "titanium_rod": {
                "name": "Titanium Rod", 
                "multiplier": 2.3, 
                "description": "Aerospace-grade titanium rod",
                "durability": 0.988,  # 1.2% break chance
                "power": 4,
                "min_fish_weight": 0.1,
                "max_fish_weight": 800.0
            },
            "enchanted_rod": {
                "name": "Enchanted Rod", 
                "multiplier": 2.5, 
                "description": "Mystical rod blessed by lunar magic",
                "durability": 0.990,  # 1.0% break chance
                "power": 4,
                "min_fish_weight": 0.1,
                "max_fish_weight": 1200.0
            },
            "legendary_rod": {
                "name": "Legendary Rod", 
                "multiplier": 4.0, 
                "description": "Forged from ancient materials",
                "durability": 0.993,  # 0.7% break chance
                "power": 5,
                "min_fish_weight": 0.1,
                "max_fish_weight": 2000.0  # Can handle large legendary fish
            },
            "dragon_rod": {
                "name": "Dragon Rod", 
                "multiplier": 2.8, 
                "description": "Forged from ancient dragon scales",
                "durability": 0.9925,  # 0.75% break chance
                "power": 5,
                "min_fish_weight": 0.1,
                "max_fish_weight": 3000.0
            },
            "phoenix_rod": {
                "name": "Phoenix Rod", 
                "multiplier": 3.2, 
                "description": "Crafted with phoenix feathers",
                "durability": 0.994,  # 0.6% break chance
                "power": 5,
                "min_fish_weight": 0.1,
                "max_fish_weight": 4000.0
            },
            "crystal_rod": {
                "name": "Crystal Rod", 
                "multiplier": 3.5, 
                "description": "Made from resonating crystals",
                "durability": 0.995,  # 0.5% break chance
                "power": 5,
                "min_fish_weight": 0.1,
                "max_fish_weight": 5000.0
            },
            "leviathan_rod": {
                "name": "Leviathan Rod", 
                "multiplier": 3.8, 
                "description": "Carved from ancient sea beast bones",
                "durability": 0.996,  # 0.4% break chance
                "power": 6,
                "min_fish_weight": 0.1,
                "max_fish_weight": 7500.0
            },
            "mythical_rod": {
                "name": "Mythical Rod", 
                "multiplier": 6.0, 
                "description": "Blessed by sea gods",
                "durability": 0.997,  # 0.3% break chance
                "power": 6,
                "min_fish_weight": 0.1,
                "max_fish_weight": 10000.0  # Can handle mythical fish
            },
            "cosmic_rod": {
                "name": "Cosmic Rod", 
                "multiplier": 10.0, 
                "description": "Forged in the heart of dying stars",
                "durability": 0.9992,  # 0.08% break chance
                "power": 8,
                "min_fish_weight": 0.1,
                "max_fish_weight": 100000000.0  # Can handle any fish
            },
            "nebula_rod": {
                "name": "Nebula Rod", 
                "multiplier": 4.5, 
                "description": "Woven from the fabric of space itself",
                "durability": 0.9985,  # 0.15% break chance
                "power": 7,
                "min_fish_weight": 0.1,
                "max_fish_weight": 25000000.0
            },
            "quantum_rod": {
                "name": "Quantum Rod", 
                "multiplier": 5.0, 
                "description": "Exists in multiple dimensions simultaneously",
                "durability": 0.9988,  # 0.12% break chance
                "power": 7,
                "min_fish_weight": 0.1,
                "max_fish_weight": 50000000.0
            },
            "astral_rod": {
                "name": "Astral Rod", 
                "multiplier": 5.5, 
                "description": "Transcends physical limitations",
                "durability": 0.9990,  # 0.10% break chance
                "power": 8,
                "min_fish_weight": 0.1,
                "max_fish_weight": 75000000.0
            },
            "void_rod": {
                "name": "Void Rod", 
                "multiplier": 6.0, 
                "description": "Fishes in the spaces between reality",
                "durability": 0.9993,  # 0.07% break chance
                "power": 8,
                "min_fish_weight": 0.1,
                "max_fish_weight": 100000000.0
            },
            "infinity_rod": {
                "name": "Infinity Rod", 
                "multiplier": 7.5, 
                "description": "Contains infinite potential within finite form",
                "durability": 0.9995,  # 0.05% break chance
                "power": 9,
                "min_fish_weight": 0.1,
                "max_fish_weight": 250000000.0
            },
            "genesis_rod": {
                "name": "Genesis Rod", 
                "multiplier": 10.0, 
                "description": "The first and final rod, existing at beginning and end",
                "durability": 0.9998,  # 0.02% break chance
                "power": 10,
                "min_fish_weight": 0.1,
                "max_fish_weight": 1000000000.0
            }
        }
        
        # Load JSON rod data and merge
        try:
            import json
            with open("data/shop/rods.json", "r") as f:
                json_rods = json.load(f)
                
            for rod_id, rod_data in json_rods.items():
                # Convert JSON format to internal format with much better durability scaling
                multiplier = rod_data.get("multiplier", 1.0)
                price = rod_data.get("price", 0)
                durability = self._convert_durability_improved(rod_data.get("durability", 100), multiplier)
                
                # Calculate weight limits based on price and multiplier
                if price >= 200000:  # Ultra expensive rods
                    max_weight = 100000000.0
                elif price >= 75000:  # Very expensive rods
                    max_weight = 10000.0
                elif price >= 25000:  # Expensive rods  
                    max_weight = 2000.0
                elif price >= 7500:   # Mid-tier rods
                    max_weight = 500.0
                elif price >= 2500:  # Entry premium rods
                    max_weight = 100.0
                else:  # Basic rods
                    max_weight = multiplier * 15.0
                
                combined_data[rod_id] = {
                    "name": rod_data.get("name", rod_id.replace("_", " ").title()),
                    "multiplier": multiplier,
                    "description": rod_data.get("description", ""),
                    "durability": durability,
                    "power": self._calculate_power_from_multiplier(multiplier),
                    "min_fish_weight": 0.1,
                    "max_fish_weight": max_weight,
                    "price": price
                }
                
        except Exception as e:
            self.logger.warning(f"Could not load JSON rod data: {e}")
            
        return combined_data

    def _convert_durability_improved(self, json_durability, multiplier):
        """Convert JSON durability with much better scaling for expensive rods"""
        # Base durability from JSON value
        if json_durability <= 100:
            base_durability = 0.90
        elif json_durability <= 150:
            base_durability = 0.95
        elif json_durability <= 200:
            base_durability = 0.97
        elif json_durability <= 300:
            base_durability = 0.985
        elif json_durability <= 500:
            base_durability = 0.993
        elif json_durability <= 1000:
            base_durability = 0.997
        elif json_durability <= 2000:
            base_durability = 0.9985
        else:
            base_durability = 0.9992
        
        # Apply multiplier bonus - higher multiplier = much better durability
        multiplier_bonus = min((multiplier - 1.0) * 0.001, 0.0008)  # Up to 0.08% bonus
        final_durability = min(base_durability + multiplier_bonus, 0.9998)
        
        return final_durability

    def _calculate_power_from_multiplier(self, multiplier):
        """Calculate power level from multiplier"""
        if multiplier <= 1.0:
            return 1
        elif multiplier <= 1.5:
            return 2
        elif multiplier <= 2.0:
            return 3
        elif multiplier <= 3.0:
            return 4
        elif multiplier <= 4.0:
            return 5
        elif multiplier <= 6.0:
            return 6
        elif multiplier <= 8.0:
            return 8
        else:
            return 10

    def _load_all_bait_data(self):
        """Load and combine bait data from both in-code and JSON sources"""
        # Start with UPDATED and more balanced bait data - EXPANDED to include all bait types
        combined_data = {
            "beginner_bait": {
                "name": "Beginner Bait", 
                "description": "Basic worms for small fish",
                "catch_rates": {
                    "junk": 0.08, "tiny": 0.30, "small": 0.35, "common": 0.20, "uncommon": 0.06,
                    "rare": 0.01, "epic": 0.0, "legendary": 0.0, "mythical": 0.0, 
                    "ancient": 0.0, "divine": 0.0, "cosmic": 0.0, "transcendent": 0.0,
                    "mutated": 0.0, "crystalline": 0.0, "void": 0.0, "celestial": 0.0
                }
            },
            "pro_bait": {
                "name": "Pro Bait",
                "description": "Professional grade bait",
                "catch_rates": {
                    "junk": 0.05, "tiny": 0.20, "small": 0.30, "common": 0.25, "uncommon": 0.15,
                    "rare": 0.04, "epic": 0.01, "legendary": 0.0, "mythical": 0.0, 
                    "ancient": 0.0, "divine": 0.0, "cosmic": 0.0, "transcendent": 0.0,
                    "mutated": 0.0, "crystalline": 0.0, "void": 0.0, "celestial": 0.0
                }
            },
            "premium_bait": {
                "name": "Premium Bait",
                "description": "High-quality bait for rare fish",
                "catch_rates": {
                    "junk": 0.02, "tiny": 0.10, "small": 0.20, "common": 0.30, "uncommon": 0.25,
                    "rare": 0.10, "epic": 0.02, "legendary": 0.01, "mythical": 0.0, 
                    "ancient": 0.0, "divine": 0.0, "cosmic": 0.0, "transcendent": 0.0,
                    "mutated": 0.0, "crystalline": 0.0, "void": 0.0, "celestial": 0.0
                }
            },
            "legendary_bait": {
                "name": "Legendary Bait",
                "description": "Legendary bait that attracts rare fish",
                "catch_rates": {
                    "junk": 0.01, "tiny": 0.05, "small": 0.10, "common": 0.20, "uncommon": 0.25,
                    "rare": 0.20, "epic": 0.10, "legendary": 0.05, "mythical": 0.03, 
                    "ancient": 0.01, "divine": 0.0, "cosmic": 0.0, "transcendent": 0.0,
                    "mutated": 0.0, "crystalline": 0.0, "void": 0.0, "celestial": 0.0
                }
            },
            "mythical_bait": {
                "name": "Mythical Bait",
                "description": "Mythical bait that can attract ancient creatures",
                "catch_rates": {
                    "junk": 0.0, "tiny": 0.02, "small": 0.05, "common": 0.10, "uncommon": 0.15,
                    "rare": 0.25, "epic": 0.20, "legendary": 0.15, "mythical": 0.05, 
                    "ancient": 0.02, "divine": 0.01, "cosmic": 0.0, "transcendent": 0.0,
                    "mutated": 0.0, "crystalline": 0.0, "void": 0.0, "celestial": 0.0
                }
            },
            "divine_bait": {
                "name": "Divine Bait",
                "description": "Divine bait blessed by sea gods",
                "catch_rates": {
                    "junk": 0.0, "tiny": 0.0, "small": 0.02, "common": 0.05, "uncommon": 0.08,
                    "rare": 0.15, "epic": 0.25, "legendary": 0.20, "mythical": 0.15, 
                    "ancient": 0.05, "divine": 0.03, "cosmic": 0.01, "transcendent": 0.01,
                    "mutated": 0.0, "crystalline": 0.0, "void": 0.0, "celestial": 0.0
                }
            },
            "cosmic_bait": {
                "name": "Cosmic Bait",
                "description": "Bait infused with cosmic energy",
                "catch_rates": {
                    "junk": 0.0, "tiny": 0.0, "small": 0.0, "common": 0.02, "uncommon": 0.03,
                    "rare": 0.10, "epic": 0.15, "legendary": 0.25, "mythical": 0.20, 
                    "ancient": 0.10, "divine": 0.08, "cosmic": 0.05, "transcendent": 0.02,
                    "mutated": 0.0, "crystalline": 0.0, "void": 0.0, "celestial": 0.0
                }
            },
            "quantum_bait": {
                "name": "Quantum Bait",
                "description": "Bait that exists in multiple dimensions simultaneously",
                "catch_rates": {
                    "junk": 0.0, "tiny": 0.0, "small": 0.0, "common": 0.0, "uncommon": 0.01,
                    "rare": 0.05, "epic": 0.10, "legendary": 0.15, "mythical": 0.25, 
                    "ancient": 0.15, "divine": 0.12, "cosmic": 0.10, "transcendent": 0.05,
                    "mutated": 0.01, "crystalline": 0.01, "void": 0.0, "celestial": 0.0
                }
            },
            "void_bait": {
                "name": "Void Bait",
                "description": "Dark bait that attracts creatures from the abyss",
                "catch_rates": {
                    "junk": 0.0, "tiny": 0.0, "small": 0.0, "common": 0.0, "uncommon": 0.0,
                    "rare": 0.02, "epic": 0.05, "legendary": 0.10, "mythical": 0.15, 
                    "ancient": 0.20, "divine": 0.15, "cosmic": 0.12, "transcendent": 0.08,
                    "mutated": 0.03, "crystalline": 0.0, "void": 0.10, "celestial": 0.0
                }
            },
            "crystalline_bait": {
                "name": "Crystalline Bait",
                "description": "Crystalline bait that attracts gem-fish",
                "catch_rates": {
                    "junk": 0.0, "tiny": 0.0, "small": 0.05, "common": 0.10, "uncommon": 0.15,
                    "rare": 0.20, "epic": 0.15, "legendary": 0.10, "mythical": 0.05, 
                    "ancient": 0.02, "divine": 0.01, "cosmic": 0.0, "transcendent": 0.0,
                    "mutated": 0.02, "crystalline": 0.15, "void": 0.0, "celestial": 0.0
                }
            },
            "celestial_bait": {
                "name": "Celestial Bait",
                "description": "Starlight-infused bait from the heavens",
                "catch_rates": {
                    "junk": 0.0, "tiny": 0.0, "small": 0.0, "common": 0.0, "uncommon": 0.0,
                    "rare": 0.01, "epic": 0.02, "legendary": 0.05, "mythical": 0.10, 
                    "ancient": 0.15, "divine": 0.20, "cosmic": 0.25, "transcendent": 0.15,
                    "mutated": 0.0, "crystalline": 0.02, "void": 0.0, "celestial": 0.05
                }
            }
        }
        
        # Load JSON bait data and merge/override - IMPROVED error handling
        try:
            import json
            import os
            
            json_path = "data/shop/bait.json"
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    json_baits = json.load(f)
                    
                for bait_id, bait_data in json_baits.items():
                    # Ensure catch_rates exist and are valid
                    catch_rates = bait_data.get("catch_rates", {})
                    if not catch_rates:
                        # If no catch_rates, use default based on bait name/id
                        if "quantum" in bait_id.lower():
                            catch_rates = combined_data["quantum_bait"]["catch_rates"]
                        elif "dimensional" in bait_id.lower():
                            catch_rates = combined_data["quantum_bait"]["catch_rates"]  # Use quantum as fallback for high-tier
                        elif "reality" in bait_id.lower():
                            catch_rates = combined_data["quantum_bait"]["catch_rates"]
                        elif "primordial" in bait_id.lower():
                            catch_rates = combined_data["celestial_bait"]["catch_rates"]
                        elif "temporal" in bait_id.lower():
                            catch_rates = combined_data["crystalline_bait"]["catch_rates"]
                        elif "void" in bait_id.lower():
                            catch_rates = combined_data["void_bait"]["catch_rates"]
                        elif "celestial" in bait_id.lower():
                            catch_rates = combined_data["celestial_bait"]["catch_rates"]
                        elif "crystalline" in bait_id.lower():
                            catch_rates = combined_data["crystalline_bait"]["catch_rates"]
                        elif "cosmic" in bait_id.lower():
                            catch_rates = combined_data["cosmic_bait"]["catch_rates"]
                        elif "mystic" in bait_id.lower():
                            catch_rates = combined_data["cosmic_bait"]["catch_rates"]
                        elif "divine" in bait_id.lower():
                            catch_rates = combined_data["divine_bait"]["catch_rates"]
                        elif "mythical" in bait_id.lower():
                            catch_rates = combined_data["mythical_bait"]["catch_rates"]
                        elif "legendary" in bait_id.lower():
                            catch_rates = combined_data["legendary_bait"]["catch_rates"]
                        elif "premium" in bait_id.lower():
                            catch_rates = combined_data["premium_bait"]["catch_rates"]
                        elif "pro" in bait_id.lower():
                            catch_rates = combined_data["pro_bait"]["catch_rates"]
                        else:
                            catch_rates = combined_data["beginner_bait"]["catch_rates"]
                    
                    # Use JSON data to override or add new baits
                    combined_data[bait_id] = {
                        "name": bait_data.get("name", bait_id.replace("_", " ").title()),
                        "description": bait_data.get("description", "Fishing bait"),
                        "catch_rates": catch_rates
                    }
                    
                self.logger.info(f"Loaded {len(json_baits)} bait types from JSON")
            else:
                self.logger.warning(f"Bait JSON file not found at {json_path}")
                
        except Exception as e:
            self.logger.warning(f"Could not load JSON bait data: {e}")
            
        self.logger.info(f"Total bait types loaded: {len(combined_data)}")
        return combined_data

    def _load_rod_aliases(self):
        """Load rod aliases dynamically from JSON file"""
        try:
            import json
            import os
            
            aliases = {}
            json_path = "data/shop/rods.json"
            
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    rods_data = json.load(f)
                
                # Build aliases dictionary from JSON data
                for rod_id, rod_data in rods_data.items():
                    if "aliases" in rod_data:
                        for alias in rod_data["aliases"]:
                            aliases[alias.lower()] = rod_id
                
                print(f"Loaded {len(aliases)} rod aliases from JSON")
            else:
                print(f"Rod JSON file not found at {json_path}")
                
            return aliases
        except Exception as e:
            print(f"Could not load rod aliases from JSON: {e}")
            return {}

    def _load_bait_aliases(self):
        """Load bait aliases dynamically from JSON file"""
        try:
            import json
            import os
            
            aliases = {}
            json_path = "data/shop/bait.json"
            
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    baits_data = json.load(f)
                
                # Build aliases dictionary from JSON data
                for bait_id, bait_data in baits_data.items():
                    if "aliases" in bait_data:
                        for alias in bait_data["aliases"]:
                            aliases[alias.lower()] = bait_id
                
                print(f"Loaded {len(aliases)} bait aliases from JSON")
            else:
                print(f"Bait JSON file not found at {json_path}")
                
            return aliases
        except Exception as e:
            print(f"Could not load bait aliases from JSON: {e}")
            return {}

    def _resolve_rod_alias(self, rod_input: str) -> str:
        """Resolve rod alias to full rod ID"""
        if not rod_input:
            return None
        
        rod_input = rod_input.lower().strip()
        
        # Check if it's already a valid rod ID
        if rod_input in self.rod_data:
            return rod_input
        
        # Check aliases
        if rod_input in self.rod_aliases:
            return self.rod_aliases[rod_input]
        
        # Check partial matches (e.g., "quantum_r" -> "quantum_rod")
        for rod_id in self.rod_data.keys():
            if rod_id.startswith(rod_input):
                return rod_id
        
        return None

    def _resolve_bait_alias(self, bait_input: str) -> str:
        """Resolve bait alias to full bait ID"""
        if not bait_input:
            return None
        
        bait_input = bait_input.lower().strip()
        
        # Check if it's already a valid bait ID
        if bait_input in self.bait_data:
            self.logger.info(f"Bait alias '{bait_input}' resolved to existing bait ID: {bait_input}")
            return bait_input
        
        # Check aliases
        if bait_input in self.bait_aliases:
            resolved = self.bait_aliases[bait_input]
            self.logger.info(f"Bait alias '{bait_input}' resolved to: {resolved}")
            return resolved
        
        # Check partial matches (e.g., "quantum_b" -> "quantum_bait")
        for bait_id in self.bait_data.keys():
            if bait_id.startswith(bait_input):
                self.logger.info(f"Bait alias '{bait_input}' partially matched to: {bait_id}")
                return bait_id
        
        self.logger.info(f"Bait alias '{bait_input}' could not be resolved")
        return None

    def _apply_rod_multiplier_properly(self, bait_rates, rod_multiplier):
        """Properly apply rod multiplier to favor higher rarities - More generous for expensive rods"""
        adjusted_rates = {}
        
        # Define rarity tiers with value thresholds
        rarity_values = {
            "junk": 5, "tiny": 25, "small": 60, "common": 140, "uncommon": 350,
            "rare": 1200, "epic": 6500, "legendary": 35000, "mythical": 900000, "ancient": 4000000,
            "divine": 20000000, "cosmic": 100000000, "transcendent": 1000000000,
            "mutated": 3000, "crystalline": 50000, "void": 1400000, "celestial": 10000000
        }
        
        for rarity, base_rate in bait_rates.items():
            if base_rate == 0:
                adjusted_rates[rarity] = 0
                continue
                
            rarity_value = rarity_values.get(rarity, 0)
            
            # MUCH more generous scaling for expensive rods (2.0+ multiplier = 5k+ cost)
            if rarity_value >= 100000:  # Ultra-rare fish (100k+ value)
                if rod_multiplier < 1.5:
                    # Still hard with basic rods
                    multiplier_effect = 0.05
                elif rod_multiplier < 2.0:
                    # Better with mid-tier rods
                    multiplier_effect = 0.2
                elif rod_multiplier < 4.0:
                    # Much better with expensive rods (5k-75k cost)
                    multiplier_effect = 0.6 + (rod_multiplier - 2.0) * 0.3
                else:
                    # Very good with ultra-expensive rods (75k+ cost)
                    multiplier_effect = 1.2 + (rod_multiplier - 4.0) * 0.4
                    
            elif rarity_value >= 10000:  # High-value fish (10k-100k)
                if rod_multiplier < 1.5:
                    multiplier_effect = 0.4
                elif rod_multiplier < 2.0:
                    multiplier_effect = 0.7
                elif rod_multiplier < 4.0:
                    # Great scaling for expensive rods
                    multiplier_effect = 1.0 + (rod_multiplier - 2.0) * 0.5
                else:
                    # Excellent for ultra-expensive rods
                    multiplier_effect = 2.0 + (rod_multiplier - 4.0) * 0.3
                    
            elif rarity_value >= 1000:  # Mid-value fish (1k-10k)
                if rod_multiplier < 2.0:
                    multiplier_effect = 0.8 + (rod_multiplier - 1.0) * 0.3
                else:
                    # Very good scaling for expensive rods
                    multiplier_effect = 1.1 + (rod_multiplier - 2.0) * 0.4
                    
            else:  # Low-value fish (under 1k)
                # Better rods are actually worse for catching junk (as intended)
                if rarity in ["junk", "tiny"]:
                    multiplier_effect = max(0.2, 1.0 - (rod_multiplier - 1.0) * 0.15)
                else:
                    multiplier_effect = 1.0 + (rod_multiplier - 1.0) * 0.1
            
            adjusted_rates[rarity] = base_rate * multiplier_effect
        
        return adjusted_rates

    async def display_catch_percentages_fixed(self, bait_rates, rod_multiplier):
        """Display catch percentages using the fixed calculation"""
        adjusted_rates = self._apply_rod_multiplier_properly(bait_rates, rod_multiplier)
        total_weight = sum(adjusted_rates.values())
        
        percentages = {}
        for rarity, weight in adjusted_rates.items():
            if total_weight > 0:
                percentage = (weight / total_weight) * 100
                if percentage > 0:
                    percentages[rarity] = percentage
        
        return percentages

    async def get_user_inventory(self, user_id: int):
        """Get user's inventory from database"""
        try:
            user_data = await db.db.users.find_one({"_id": str(user_id)})
            if not user_data:
                return None
            return user_data.get("inventory", {})
        except Exception as e:
            self.logger.error(f"Error getting user inventory: {e}")
            return None

    async def get_user_rods(self, user_id: int):
        """Get user's rods with full data"""
        inventory = await self.get_user_inventory(user_id)
        if not inventory:
            return []
        
        rod_inventory = inventory.get("rod", {})
        rods = []
        
        for rod_id, quantity in rod_inventory.items():
            if quantity > 0 and rod_id in self.rod_data:
                rod_info = self.rod_data[rod_id].copy()
                rod_info["_id"] = rod_id
                rod_info["quantity"] = quantity
                rods.append(rod_info)
        
        return rods

    async def get_user_bait(self, user_id: int):
        """Get user's bait with full data - IMPROVED to handle missing bait data"""
        inventory = await self.get_user_inventory(user_id)
        if not inventory:
            return []
        
        bait_inventory = inventory.get("bait", {})
        bait = []
        
        for bait_id, quantity in bait_inventory.items():
            if quantity > 0:
                if bait_id in self.bait_data:
                    bait_info = self.bait_data[bait_id].copy()
                    bait_info["_id"] = bait_id
                    bait_info["amount"] = quantity
                    bait.append(bait_info)
                else:
                    # Handle missing bait data by creating default entry
                    self.logger.warning(f"Missing bait data for {bait_id}, creating default")
                    default_bait = {
                        "name": bait_id.replace("_", " ").title(),
                        "description": "Unknown bait type",
                        "catch_rates": self.bait_data["beginner_bait"]["catch_rates"],
                        "_id": bait_id,
                        "amount": quantity
                    }
                    bait.append(default_bait)
        
        return bait

    async def remove_bait(self, user_id: int, bait_id: str) -> bool:
        """Remove one bait from user's inventory - Fixed to work with new structure"""
        try:
            # First check if user has this bait in the new inventory structure
            result = await db.db.users.update_one(
                {"_id": str(user_id), f"inventory.bait.{bait_id}": {"$gt": 0}},
                {"$inc": {f"inventory.bait.{bait_id}": -1}}
            )
            
            if result.modified_count > 0:
                return True
                
            # If that didn't work, try the old structure for backwards compatibility
            user = await db.db.users.find_one({"_id": str(user_id)})
            if not user:
                return False
                
            # Check old bait structure
            old_bait = user.get("bait", [])
            for i, bait in enumerate(old_bait):
                if bait.get("_id") == bait_id or bait.get("id") == bait_id:
                    # Remove this bait item
                    result = await db.db.users.update_one(
                        {"_id": str(user_id)},
                        {"$unset": {f"bait.{i}": ""}}
                    )
                    # Clean up the array
                    await db.db.users.update_one(
                        {"_id": str(user_id)},
                        {"$pull": {"bait": None}}
                    )
                    return result.modified_count > 0
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error removing bait: {e}")
            return False

    async def set_active_rod_manual(self, user_id: int, rod_id: str) -> bool:
        """Set user's active fishing rod manually"""
        try:
            result = await db.db.users.update_one(
                {"_id": str(user_id)},
                {"$set": {"active_fishing.rod": rod_id}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            self.logger.error(f"Error setting active rod: {e}")
            return False

    async def check_rod_durability(self, durability: float) -> bool:
        """Check if rod survives this fishing attempt"""
        return random.random() < durability

    async def select_fish_from_rarity(self, rarity: str):
        """Select a random fish from the given rarity category"""
        if rarity not in self.fish_database:
            return None
        
        fish_list = self.fish_database[rarity]
        if not fish_list:
            return None
            
        return random.choice(fish_list)

    async def check_fish_escape(self, fish_template, rod_power: int):
        """Check if fish escapes - Much more generous for expensive rods and reduced overall escape rates"""
        # Generate fish weight
        fish_weight = random.uniform(fish_template["min_weight"], fish_template["max_weight"])
        
        # Fish under 50kg cannot escape (increased from 10kg)
        if fish_weight < 50.0:
            return False, fish_weight
        
        # For fish 50kg and above, check escape chance with much more generous rod power scaling
        base_escape_chance = fish_template.get("escape_chance", 0.0)
        
        # DRAMATICALLY reduced escape chances - expensive rods should almost never lose fish
        if rod_power >= 8:  # Cosmic+ rods (200k+ cost) - practically no escapes
            power_reduction = min(rod_power * 0.12, 0.95)  # Up to 95% reduction
        elif rod_power >= 6:  # Mythical+ rods (75k+ cost) - very rare escapes
            power_reduction = min(rod_power * 0.10, 0.85)  # Up to 85% reduction
        elif rod_power >= 4:  # Master+ rods (25k+ cost) - rare escapes
            power_reduction = min(rod_power * 0.08, 0.70)  # Up to 70% reduction
        elif rod_power >= 3:  # Pro+ rods (7.5k+ cost) - occasional escapes
            power_reduction = min(rod_power * 0.06, 0.50)  # Up to 50% reduction
        elif rod_power >= 2:  # Advanced rods - moderate escapes
            power_reduction = min(rod_power * 0.04, 0.35)  # Up to 35% reduction
        else:  # Basic rods - still significant escapes
            power_reduction = min(rod_power * 0.02, 0.20)  # Max 20% reduction
        
        # Apply additional weight-based reduction for very heavy fish
        if fish_weight >= 10000.0:  # 10+ ton fish get additional protection
            weight_reduction = min(fish_weight / 50000.0, 0.40)  # Up to 40% more reduction
        elif fish_weight >= 1000.0:  # 1+ ton fish get some protection
            weight_reduction = min(fish_weight / 10000.0, 0.20)  # Up to 20% more reduction
        else:
            weight_reduction = 0
        
        total_reduction = power_reduction + weight_reduction
        final_escape_chance = max(0.001, base_escape_chance - total_reduction)  # Minimum 0.1% escape chance
        
        # Cap maximum escape chance at 15% even for basic rods on huge fish
        final_escape_chance = min(final_escape_chance, 0.15)
        
        escaped = random.random() < final_escape_chance
        return escaped, fish_weight

    @commands.command(name="fish", aliases=["fishing", 'fs'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def fish(self, ctx):
        """Go fishing with advanced mechanics including rod breaking and fish escaping"""
        try:
            rods = await self.get_user_rods(ctx.author.id)
            bait = await self.get_user_bait(ctx.author.id)
            
            if not rods:
                embed = discord.Embed(
                    title="🎣 First Time Fishing",
                    description="You need a fishing rod to start! Buy one from `.shop rod`",
                    color=discord.Color.blue()
                )
                return await ctx.reply(embed=embed)
            
            if not bait:
                return await ctx.reply("❌ You need bait to go fishing! Buy some from `.shop bait`")
            
            # Get active gear
            active_gear = await db.get_active_fishing_gear(ctx.author.id)
            active_rod_id = active_gear.get("rod") if active_gear else None
            active_bait_id = active_gear.get("bait") if active_gear else None
            
            if active_rod_id:
                rod = next((r for r in rods if r.get("_id") == active_rod_id), None)
            else:
                rod = rods[0]
                active_rod_id = rod.get("_id")
                await self.set_active_rod_manual(ctx.author.id, active_rod_id)
            
            if not rod:
                return await ctx.reply("❌ Your active rod is no longer available!")
            
            # Use active bait or first available bait
            current_bait = None
            bait_id = None
            
            # First try to use the active bait if it exists and user has it
            if active_bait_id:
                current_bait = next((b for b in bait if b.get("_id") == active_bait_id), None)
                if current_bait and current_bait.get("amount", 0) > 0:
                    bait_id = active_bait_id
                else:
                    # Active bait not available, clear it from active gear
                    await db.set_active_bait(ctx.author.id, None)
                    current_bait = None
            
            # If no active bait or active bait unavailable, use first available
            if not current_bait:
                current_bait = bait[0]
                bait_id = current_bait.get("_id")
                # Set this as the new active bait
                await db.set_active_bait(ctx.author.id, bait_id)
            
            # Debug logging to track what bait is being used
            self.logger.info(f"User {ctx.author.id} fishing with bait: {current_bait.get('name')} (ID: {bait_id})")
            
            # Remove bait
            if not await self.remove_bait(ctx.author.id, bait_id):
                return await ctx.reply("❌ Failed to use bait or you're out of bait!")
            
            # Get rod stats
            rod_multiplier = rod.get("multiplier", 1.0)
            rod_durability = rod.get("durability", 0.95)
            rod_power = rod.get("power", 1)
            bait_rates = current_bait.get("catch_rates", {})
            
            # Display suspense message
            suspense_embed = discord.Embed(
                title="🎣 Casting your line...",
                description=f"Using **{rod['name']}** with **{current_bait['name']}**",
                color=discord.Color.blue()
            )
            
            # Calculate catch percentages for debugging (hidden from users)
            percentages = await self.display_catch_percentages_fixed(bait_rates, rod_multiplier)
            if percentages:
                # Debug logging - print ALL odds to console for debugging
                sorted_percentages = sorted(percentages.items(), key=lambda x: x[1], reverse=True)
                debug_text = f"[FISHING DEBUG] {ctx.author.name} ({ctx.author.id}) - Rod: {rod['name']} (x{rod_multiplier}) - Bait: {current_bait['name']}\n"
                for rarity, chance in sorted_percentages:
                    if chance >= 0.001:
                        debug_text += f"  {rarity.title()}: {chance:.3f}%\n"
                print(debug_text)
                self.logger.debug(debug_text)
            
            suspense_embed.set_footer(text="🌊 Waiting for a bite...")
            message = await ctx.reply(embed=suspense_embed)
            
            # Suspense delay
            await asyncio.sleep(random.uniform(2.5, 4.5))
            
            # Check rod durability first
            if not await self.check_rod_durability(rod_durability):
                # Rod breaks!
                break_embed = discord.Embed(
                    title="💥 Rod Broke!",
                    description=f"Your **{rod['name']}** snapped under pressure!",
                    color=discord.Color.red()
                )
                break_embed.add_field(
                    name="⚠️ Rod Removed",
                    value="The broken rod has been removed from your inventory.",
                    inline=False
                )
                break_embed.add_field(
                    name="🛡️ Durability Info",
                    value=f"This rod had a {((1-rod_durability)*100):.2f}% break chance per use.",
                    inline=False
                )
                
                # Remove rod from inventory
                await db.db.users.update_one(
                    {"_id": str(ctx.author.id)},
                    {"$inc": {f"inventory.rod.{active_rod_id}": -1}}
                )
                
                await message.edit(embed=break_embed)
                return
            
            # FIXED: Determine what fish is hooked with proper rod multiplier application
            # Apply rod multiplier to higher rarity chances specifically
            adjusted_rates = self._apply_rod_multiplier_properly(bait_rates, rod_multiplier)
            
            total_weight = sum(adjusted_rates.values())
            if total_weight == 0:
                await message.edit(embed=discord.Embed(
                    title="🎣 No Bite",
                    description="Nothing seems interested in your bait...",
                    color=discord.Color.gray()
                ))
                return
            
            # Roll for fish rarity using adjusted rates
            roll = random.random() * total_weight
            cumulative = 0
            caught_rarity = "junk"
            
            for rarity, weight in adjusted_rates.items():
                cumulative += weight
                if roll <= cumulative:
                    caught_rarity = rarity
                    break
            
            # Select specific fish
            fish_template = await self.select_fish_from_rarity(caught_rarity)
            if not fish_template:
                caught_rarity = "junk"
                fish_template = await self.select_fish_from_rarity(caught_rarity)
            
            # Check if fish escapes
            escaped, fish_weight = await self.check_fish_escape(fish_template, rod_power)
            
            if escaped:
                # Fish escaped!
                escape_embed = discord.Embed(
                    title="🐟 The one that got away...",
                    description=f"A **{fish_template['name']}** ({fish_weight:.2f}kg) broke free!",
                    color=discord.Color.orange()
                )
                escape_embed.add_field(
                    name="💰 Potential Value",
                    value=f"You could have earned **{fish_template['base_value']:,}** {self.currency}",
                    inline=True
                )
                escape_embed.add_field(
                    name="🎣 Tip",
                    value="Try using a stronger rod for big fish!",
                    inline=True
                )
                
                await message.edit(embed=escape_embed)
                return
            
            # Successfully caught!
            final_value = random.randint(
                int(fish_template["base_value"] * 0.8),
                int(fish_template["base_value"] * 1.2)
            )
            
            fish = {
                "id": str(uuid.uuid4()),
                "type": caught_rarity,
                "name": fish_template["name"],
                "value": final_value,
                "weight": fish_weight,
                "caught_at": datetime.datetime.now().isoformat(),
                "bait_used": bait_id,
                "rod_used": active_rod_id
            }
            
            if await db.add_fish(ctx.author.id, fish):
                # Success embed with rarity-based colors
                rarity_colors = {
                    "junk": discord.Color.light_gray(),
                    "tiny": discord.Color.light_gray(),
                    "small": discord.Color.blue(),
                    "common": discord.Color.green(),
                    "uncommon": discord.Color.dark_green(),
                    "rare": discord.Color.blue(),
                    "epic": discord.Color.purple(),
                    "legendary": discord.Color.orange(),
                    "mythical": discord.Color.red(),
                    "ancient": discord.Color.red(),
                    "divine": discord.Color.red(),
                    "cosmic": discord.Color.red(),
                    "transcendent": discord.Color.red(),
                    "void": discord.Color.red(),
                    "celestial": discord.Color.red(),
                    "subatomic": discord.Color.magenta(),
                    "dev": discord.Color.gold()
                }
                
                success_embed = discord.Embed(
                    title="🎣 Fish Caught!",
                    description=f"You caught a **{fish['name']}**!",
                    color=rarity_colors.get(caught_rarity, discord.Color.blue())
                )
                
                success_embed.add_field(
                    name="💰 Value",
                    value=f"**{final_value:,}** {self.currency}",
                    inline=True
                )
                
                success_embed.add_field(
                    name="⚖️ Weight",
                    value=f"{fish_weight:.2f} kg",
                    inline=True
                )
                
                success_embed.add_field(
                    name="🏷️ Rarity",
                    value=caught_rarity.title(),
                    inline=True
                )
                
                # Add special message for rare fish
                if caught_rarity == "subatomic":
                    success_embed.set_footer(text="⚛️ LEGENDARY SUBATOMIC CATCH! You've caught microscopic life worth a fortune!")
                elif caught_rarity in ["legendary", "mythical", "ancient", "divine", "cosmic", "transcendent", "void", "celestial"]:
                    success_embed.set_footer(text="🌟 Incredible catch! This is extremely rare!")
                elif caught_rarity in ["epic", "rare"]:
                    success_embed.set_footer(text="✨ Nice catch! This is quite rare!")
                
                await message.edit(embed=success_embed)
            else:
                await message.edit(embed=discord.Embed(
                    title="❌ Storage Error",
                    description="Failed to store your catch!",
                    color=discord.Color.red()
                ))
                
        except Exception as e:
            self.logger.error(f"Fishing error: {e}")
            await ctx.reply("❌ An error occurred while fishing!")

    @commands.command(name="sellfish", aliases=["sf"])
    async def sell_fish(self, ctx, fish_id: str = None):
        """Sell a specific fish or all fish"""
        try:
            user_fish = await db.get_fish(ctx.author.id)
            if not user_fish:
                return await ctx.reply("❌ You haven't caught any fish yet!")
            
            if fish_id:
                # Sell specific fish
                fish = next((f for f in user_fish if f.get("id") == fish_id), None)
                if not fish:
                    return await ctx.reply("❌ Fish not found in your inventory!")
                
                if await db.remove_fish(ctx.author.id, fish_id):
                    await db.add_currency(ctx.author.id, fish["value"])
                    embed = discord.Embed(
                        title="🐟 Fish Sold!",
                        description=f"Sold **{fish['name']}** for **{fish['value']:,}** {self.currency}",
                        color=discord.Color.green()
                    )
                    await ctx.reply(embed=embed)
                else:
                    await ctx.reply("❌ Failed to sell fish!")
            else:
                # Sell all fish
                total_value = sum(fish.get("value", 0) for fish in user_fish)
                fish_count = len(user_fish)
                
                if await db.clear_fish(ctx.author.id):
                    await db.add_currency(ctx.author.id, total_value)
                    embed = discord.Embed(
                        title="🐟 All Fish Sold!",
                        description=f"Sold **{fish_count:,}** fish for **{total_value:,}** {self.currency}",
                        color=discord.Color.green()
                    )
                    await ctx.reply(embed=embed)
                else:
                    await ctx.reply("❌ Failed to sell fish!")
                    
        except Exception as e:
            self.logger.error(f"Sell fish error: {e}")
            await ctx.reply("❌ An error occurred while selling fish!")

    @commands.command(name="fishinv", aliases=["fi", "fishbag"])
    async def fish_inventory(self, ctx, page: int = 1):
        """View your fish inventory with pagination - first page shows gear, rest show fish"""
        try:
            user_fish = await db.get_fish(ctx.author.id)
            
            # Page 1: Show active gear and summary
            if page == 1:
                # Get active gear
                active_gear = await db.get_active_fishing_gear(ctx.author.id)
                
                # Get total fish stats
                total_fish = len(user_fish)
                total_value = sum(fish.get("value", 0) for fish in user_fish) if user_fish else 0
                
                embed = discord.Embed(
                    title="🎣 Fishing Overview",
                    description=f"**Total Fish:** {total_fish:,} | **Total Value:** {total_value:,} {self.currency}",
                    color=discord.Color.blue()
                )
                
                # Show equipped rod
                if active_gear.get("rod"):
                    rod_id = active_gear["rod"]
                    if rod_id in self.rod_data:
                        rod = self.rod_data[rod_id]
                        embed.add_field(
                            name="🎣 Equipped Rod",
                            value=f"**{rod['name']}**\n"
                                  f"Multiplier: {rod.get('multiplier', 1.0)}x\n"
                                  f"Power: {rod.get('power', 1)}\n"
                                  f"Durability: {(rod.get('durability', 0.95)*100):.1f}%",
                            inline=True
                        )
                    else:
                        embed.add_field(
                            name="🎣 Equipped Rod",
                            value="❌ Rod data not found",
                            inline=True
                        )
                else:
                    embed.add_field(
                        name="🎣 Equipped Rod",
                        value="❌ No rod equipped\nUse `.rod` to equip one",
                        inline=True
                    )
                
                # Show equipped bait
                if active_gear.get("bait"):
                    bait_id = active_gear["bait"]
                    user_bait = await self.get_user_bait(ctx.author.id)
                    equipped_bait = next((b for b in user_bait if b.get("_id") == bait_id), None)
                    
                    if equipped_bait:
                        embed.add_field(
                            name="🪱 Equipped Bait",
                            value=f"**{equipped_bait['name']}**\n"
                                  f"Amount: {equipped_bait.get('amount', 1)}\n"
                                  f"Type: {equipped_bait.get('rarity', 'Common').title()}",
                            inline=True
                        )
                    else:
                        embed.add_field(
                            name="🪱 Equipped Bait",
                            value="❌ Bait data not found",
                            inline=True
                        )
                else:
                    embed.add_field(
                        name="🪱 Equipped Bait",
                        value="❌ No bait equipped\nUse `.bait` to equip some",
                        inline=True
                    )
                
                # Add quick stats if user has fish
                if user_fish:
                    # Sort by value and get top catches
                    sorted_fish = sorted(user_fish, key=lambda x: x.get("value", 0), reverse=True)
                    top_fish = sorted_fish[:3]
                    
                    top_catches = []
                    for i, fish in enumerate(top_fish, 1):
                        top_catches.append(f"{i}. **{fish.get('name', 'Unknown')}** - {fish.get('value', 0):,} {self.currency}")
                    
                    embed.add_field(
                        name="🏆 Top Catches",
                        value="\n".join(top_catches),
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="🐟 Fish Collection",
                        value="No fish caught yet! Use `.fish` to start fishing.",
                        inline=False
                    )
                
                # Calculate total pages (gear page + fish pages)
                fish_pages = math.ceil(len(user_fish) / 5) if user_fish else 0
                total_pages = 1 + fish_pages
                
                embed.set_footer(text=f"Page 1/{total_pages} • Use buttons to view your fish collection")
                
                # Create pagination view
                view = FishInventoryPaginator(ctx.author.id, user_fish, 1, total_pages, self.currency, self.rod_data, self.bait_data, self.get_user_bait)
                message = await ctx.reply(embed=embed, view=view)
                view.message = message
                return
            
            # Pages 2+: Show fish
            if not user_fish:
                return await ctx.reply("❌ You haven't caught any fish yet!")
            
            # Sort by value (highest first)
            user_fish.sort(key=lambda x: x.get("value", 0), reverse=True)
            
            items_per_page = 5
            fish_pages = math.ceil(len(user_fish) / items_per_page)
            total_pages = 1 + fish_pages
            
            # Adjust page number for fish display (page 2 becomes fish page 1)
            fish_page = page - 1
            
            if fish_page > fish_pages:
                fish_page = fish_pages
                page = total_pages
            
            start_idx = (fish_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_fish = user_fish[start_idx:end_idx]
            
            # Create fish display embed
            total_value = sum(fish.get("value", 0) for fish in user_fish)
            embed = discord.Embed(
                title="🐟 Your Fish Collection",
                description=f"**Total Fish:** {len(user_fish):,} | **Total Value:** {total_value:,} {self.currency}",
                color=discord.Color.blue()
            )
            
            # Add fish to embed
            for i, fish in enumerate(page_fish, start=start_idx + 1):
                fish_info = (
                    f"**#{i}** • **{fish.get('value', 0):,}** {self.currency}\n"
                    f"**Weight:** {fish.get('weight', 0):.2f} kg\n"
                    f"**Rarity:** {fish.get('type', 'unknown').title()}\n"
                    f"**ID:** `{fish.get('id', 'unknown')[:8]}...`"
                )
                
                embed.add_field(
                    name=f"🐟 {fish.get('name', 'Unknown Fish')}",
                    value=fish_info,
                    inline=False
                )
            
            embed.set_footer(text=f"Page {page}/{total_pages} • Use buttons to navigate")
            
            # Create pagination view
            view = FishInventoryPaginator(ctx.author.id, user_fish, page, total_pages, self.currency, self.rod_data, self.bait_data, self.get_user_bait)
            message = await ctx.reply(embed=embed, view=view)
            view.message = message
            
        except Exception as e:
            self.logger.error(f"Fish inventory error: {e}")
            await ctx.reply("❌ An error occurred while viewing your fish inventory!")

    @commands.command(name="topfish", aliases=["gf", "globalfish", "flb", "fishleaderboard"])
    async def global_fish_leaderboard(self, ctx, page: int = 1):
        """Global fish leaderboard showing all catches"""
        try:
            all_fish = await db.get_all_fish_global()
            if not all_fish:
                return await ctx.reply("❌ No fish have been caught yet!")
            
            # Sort by value (highest first)
            all_fish.sort(key=lambda x: x.get("value", 0), reverse=True)
            
            items_per_page = 2  # 2 fish per page as requested
            total_pages = math.ceil(len(all_fish) / items_per_page)
            page = max(1, min(page, total_pages))
            
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_fish = all_fish[start_idx:end_idx]
            
            embed = discord.Embed(
                title="🌍 Global Fish Leaderboard",
                description="Top catches from all players",
                color=discord.Color.gold()
            )
            
            for i, fish in enumerate(page_fish, start=start_idx + 1):
                user_id = fish.get("user_id", "Unknown")
                try:
                    user = self.bot.get_user(int(user_id))
                    username = user.display_name if user else f"User {user_id}"
                except:
                    username = f"User {user_id}"
                
                caught_time = fish.get("caught_at", "Unknown")
                if caught_time != "Unknown":
                    try:
                        dt = datetime.datetime.fromisoformat(caught_time)
                        caught_time = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        caught_time = "Unknown"
                
                fish_info = f"**#{i} • Caught by:** {username}\n"
                fish_info += f"**Value:** {fish.get('value', 0):,} {self.currency}\n"
                fish_info += f"**Weight:** {fish.get('weight', 0):.2f} kg\n"
                fish_info += f"**Rarity:** {fish.get('type', 'unknown').title()}\n"
                fish_info += f"**Rod Used:** {fish.get('rod_used', 'Unknown')}\n"
                fish_info += f"**Bait Used:** {fish.get('bait_used', 'Unknown')}\n"
                fish_info += f"**Caught:** {caught_time}"
                
                embed.add_field(
                    name=f"🐟 {fish.get('name', 'Unknown Fish')}",
                    value=fish_info,
                    inline=False
                )
            
            embed.set_footer(text=f"Page {page}/{total_pages} • {len(all_fish)} total catches")
            
            # Create pagination view
            view = GlobalFishPaginator(all_fish, page, total_pages, self.currency, self.bot)
            message = await ctx.reply(embed=embed, view=view)
            view.message = message
            
        except Exception as e:
            self.logger.error(f"Global fish leaderboard error: {e}")
            await ctx.reply("❌ An error occurred while loading the fish leaderboard!")

    @commands.command(name="fishstats", aliases=["fs_stats"])
    async def fish_stats(self, ctx, user: discord.Member = None):
        """View fishing statistics for yourself or another user"""
        try:
            target_user = user or ctx.author
            user_fish = await db.get_fish(target_user.id)
            
            if not user_fish:
                pronoun = "You haven't" if target_user == ctx.author else f"{target_user.display_name} hasn't"
                return await ctx.reply(f"❌ {pronoun} caught any fish yet!")
            
            # Calculate statistics
            total_fish = len(user_fish)
            total_value = sum(fish.get("value", 0) for fish in user_fish)
            total_weight = sum(fish.get("weight", 0) for fish in user_fish)
            avg_value = total_value / total_fish if total_fish > 0 else 0
            
            # Find rarest fish
            rarity_order = ["junk", "tiny", "small", "common", "uncommon", "rare", "epic", 
                           "legendary", "mythical", "ancient", "divine", "cosmic", "transcendent",
                           "mutated", "crystalline", "void", "celestial", "subatomic", "dev"]
            
            rarest_fish = None
            for rarity in reversed(rarity_order):
                rarest_fish = next((f for f in user_fish if f.get("type") == rarity), None)
                if rarest_fish:
                    break
            
            # Count by rarity
            rarity_counts = {}
            for fish in user_fish:
                rarity = fish.get("type", "unknown")
                rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
            
            embed = discord.Embed(
                title=f"📊 {target_user.display_name}'s Fishing Stats",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="🎣 Total Catches",
                value=f"**{total_fish}** fish",
                inline=True
            )
            
            embed.add_field(
                name="💰 Total Value",
                value=f"**{total_value:,}** {self.currency}",
                inline=True
            )
            
            embed.add_field(
                name="⚖️ Total Weight",
                value=f"**{total_weight:.2f}** kg",
                inline=True
            )
            
            embed.add_field(
                name="📈 Average Value",
                value=f"**{avg_value:.0f}** {self.currency}",
                inline=True
            )
            
            if rarest_fish:
                embed.add_field(
                    name="✨ Rarest Catch",
                    value=f"**{rarest_fish['name']}** ({rarest_fish['type'].title()})",
                    inline=True
                )
            
            # Show top rarities caught
            if rarity_counts:
                top_rarities = sorted(rarity_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                rarity_text = "\n".join([f"**{rarity.title()}:** {count}" for rarity, count in top_rarities])
                embed.add_field(
                    name="🏷️ Catches by Rarity",
                    value=rarity_text,
                    inline=False
                )
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Fish stats error: {e}")
            await ctx.reply("❌ An error occurred while loading fishing stats!")

    @commands.command(name="rod", aliases=["erod", 'equiprod', "equip_rod"])
    async def rod(self, ctx, *, rod_name: str = None):
        """Equip a fishing rod from your inventory"""
        try:
            if not rod_name:
                # Show available rods
                user_rods = await self.get_user_rods(ctx.author.id)
                if not user_rods:
                    return await ctx.reply("❌ You don't have any fishing rods! Buy one from `.shop rod`")
                
                embed = discord.Embed(
                    title="🎣 Your Fishing Rods",
                    description="Use `.rod <rod_name>` to equip a rod\n💡 **Aliases:** quantum, cosmic, void, divine, basic, pro, etc.",
                    color=discord.Color.blue()
                )
                
                for rod in user_rods[:10]:  # Show first 10 rods
                    embed.add_field(
                        name=f"🎣 {rod['name']}",
                        value=f"**Multiplier:** {rod.get('multiplier', 1.0)}x\n**Quantity:** {rod.get('quantity', 1)}",
                        inline=True
                    )
                
                return await ctx.reply(embed=embed)
            
            # Find rod by name, ID, or alias
            user_rods = await self.get_user_rods(ctx.author.id)
            target_rod = None
            
            # First try to resolve alias
            resolved_rod_id = self._resolve_rod_alias(rod_name)
            
            for rod in user_rods:
                rod_id = rod.get('_id', '').lower()
                rod_full_name = rod['name'].lower()
                
                # Match by exact ID, resolved alias, or name contains
                if (rod_name.lower() == rod_id or 
                    (resolved_rod_id and resolved_rod_id == rod_id) or
                    rod_name.lower() in rod_full_name):
                    target_rod = rod
                    break
            
            if not target_rod:
                embed = discord.Embed(
                    title="❌ Rod Not Found",
                    description=f"Rod '{rod_name}' not found in your inventory!",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="💡 Try using aliases",
                    value="quantum, cosmic, void, divine, basic, pro, etc.",
                    inline=False
                )
                return await ctx.reply(embed=embed)
            
            # Equip the rod
            if await self.set_active_rod_manual(ctx.author.id, target_rod['_id']):
                embed = discord.Embed(
                    title="🎣 Rod Equipped!",
                    description=f"You equipped **{target_rod['name']}**",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="💪 Multiplier",
                    value=f"{target_rod.get('multiplier', 1.0)}x",
                    inline=True
                )
                embed.add_field(
                    name="🛡️ Durability",
                    value=f"{((target_rod.get('durability', 0.95))*100):.1f}%",
                    inline=True
                )
                embed.add_field(
                    name="⚡ Power Level",
                    value=f"{target_rod.get('power', 1)}",
                    inline=True
                )
                await ctx.reply(embed=embed)
            else:
                await ctx.reply("❌ Failed to equip rod!")
                
        except Exception as e:
            self.logger.error(f"Equip rod error: {e}")
            await ctx.reply("❌ An error occurred while equipping the rod!")

    @commands.command(name="bait", aliases=["ebait", 'equipbait', "equip_bait"])
    async def bait(self, ctx, *, bait_name: str = None):
        """Equip bait from your inventory"""
        try:
            if not bait_name:
                # Show available bait
                user_bait = await self.get_user_bait(ctx.author.id)
                if not user_bait:
                    return await ctx.reply("❌ You don't have any bait! Buy some from `.shop bait`")
                
                # Debug logging
                self.logger.info(f"User {ctx.author.id} bait inventory for listing:")
                for bait in user_bait:
                    self.logger.info(f"  - ID: '{bait.get('_id', 'unknown')}', Name: '{bait.get('name', 'unknown')}', Amount: {bait.get('amount', 0)}")
                
                embed = discord.Embed(
                    title="🪱 Your Bait Collection",
                    description="Use `.bait <bait_name>` to equip bait\n💡 **Aliases:** quantum, void, crystal, divine, basic, pro, etc.",
                    color=discord.Color.green()
                )
                
                for bait in user_bait[:10]:  # Show first 10 bait types
                    embed.add_field(
                        name=f"🪱 {bait['name']}",
                        value=f"**Amount:** {bait.get('amount', 1)}\n**ID:** `{bait.get('_id', 'unknown')}`\n**Description:** {bait.get('description', 'N/A')[:30]}...",
                        inline=True
                    )
                
                return await ctx.reply(embed=embed)
            
            # Find bait by name, ID, or alias - IMPROVED matching with aliases
            user_bait = await self.get_user_bait(ctx.author.id)
            target_bait = None
            
            # First try to resolve alias
            resolved_bait_id = self._resolve_bait_alias(bait_name)
            
            # Try exact matches first (highest priority)
            for bait in user_bait:
                bait_id = bait.get('_id', '').lower()
                bait_full_name = bait['name'].lower()
                
                # Exact ID match
                if bait_name.lower() == bait_id:
                    target_bait = bait
                    break
                    
                # Exact resolved alias match
                if resolved_bait_id and resolved_bait_id == bait_id:
                    target_bait = bait
                    break
            
            # If no exact match found, try partial name matches (lower priority)
            if not target_bait:
                for bait in user_bait:
                    bait_full_name = bait['name'].lower()
                    
                    # Only match if the input is a significant part of the name (not just a substring)
                    if (len(bait_name) >= 3 and 
                        bait_name.lower() in bait_full_name and
                        len(bait_name) / len(bait_full_name) > 0.3):  # At least 30% of the name
                        target_bait = bait
                        break
            
            if not target_bait:
                # Debug logging
                self.logger.info(f"User {ctx.author.id} failed to find bait '{bait_name}'. Available baits:")
                for bait in user_bait:
                    self.logger.info(f"  - ID: '{bait.get('_id', 'unknown')}', Name: '{bait.get('name', 'unknown')}'")
                
                available_bait = [f"`{b.get('_id', 'unknown')}`" for b in user_bait[:5]]
                embed = discord.Embed(
                    title="❌ Bait Not Found",
                    description=f"Bait '{bait_name}' not found in your inventory!",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="💡 Try using aliases",
                    value="quantum, void, crystal, divine, basic, pro, etc.",
                    inline=False
                )
                if available_bait:
                    embed.add_field(
                        name="Available bait IDs",
                        value=", ".join(available_bait),
                        inline=False
                    )
                
                # Also show names for easier identification
                if user_bait:
                    available_names = [f"`{b.get('name', 'unknown')}`" for b in user_bait[:5]]
                    embed.add_field(
                        name="Available bait names",
                        value=", ".join(available_names),
                        inline=False
                    )
                
                return await ctx.reply(embed=embed)
            
            # Equip the bait - IMPROVED error handling
            bait_id = target_bait.get('_id')
            if not bait_id:
                return await ctx.reply("❌ Invalid bait ID!")
            
            # Debug logging
            self.logger.info(f"User {ctx.author.id} attempting to equip bait: '{bait_name}' -> resolved to ID: '{bait_id}' (name: '{target_bait['name']}')")
                
            if await db.set_active_bait(ctx.author.id, bait_id):
                embed = discord.Embed(
                    title="🪱 Bait Equipped!",
                    description=f"You equipped **{target_bait['name']}**",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="📦 Amount Available",
                    value=f"{target_bait.get('amount', 1)}",
                    inline=True
                )
                embed.add_field(
                    name="🆔 Bait ID",
                    value=f"`{bait_id}`",
                    inline=True
                )
                embed.add_field(
                    name="📝 Description",
                    value=target_bait.get('description', 'No description available'),
                    inline=False
                )
                
                # Show some catch rate info
                catch_rates = target_bait.get('catch_rates', {})
                if catch_rates:
                    high_rate_rarities = []
                    for rarity, rate in catch_rates.items():
                        if rate > 0.05:  # 5% or higher
                            high_rate_rarities.append(f"{rarity.title()}: {rate*100:.1f}%")
                    
                    if high_rate_rarities:
                        embed.add_field(
                            name="🎯 Best For",
                            value="\n".join(high_rate_rarities[:5]),
                            inline=False
                        )
                
                await ctx.reply(embed=embed)
            else:
                self.logger.error(f"Failed to equip bait '{bait_id}' for user {ctx.author.id}")
                await ctx.reply("❌ Failed to equip bait! Database operation failed. Please try again or contact support if the issue persists.")
                
        except Exception as e:
            self.logger.error(f"Equip bait error: {e}")
            await ctx.reply("❌ An error occurred while equipping the bait!")

    @commands.command(name="fishgear", aliases=["gear", "equipped"])
    async def fish_gear(self, ctx):
        """View your currently equipped fishing gear"""
        try:
            active_gear = await db.get_active_fishing_gear(ctx.author.id)
            
            embed = discord.Embed(
                title="🎣 Your Fishing Gear",
                color=discord.Color.blue()
            )
            
            # Show equipped rod
            if active_gear.get("rod"):
                rod_id = active_gear["rod"]
                if rod_id in self.rod_data:
                    rod = self.rod_data[rod_id]
                    embed.add_field(
                        name="🎣 Equipped Rod",
                        value=f"**{rod['name']}**\n"
                              f"Multiplier: {rod.get('multiplier', 1.0)}x\n"
                              f"Power: {rod.get('power', 1)}\n"
                              f"Durability: {(rod.get('durability', 0.95)*100):.1f}%",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="🎣 Equipped Rod",
                        value="❌ Rod data not found",
                        inline=True
                    )
            else:
                embed.add_field(
                    name="🎣 Equipped Rod",
                    value="❌ No rod equipped",
                    inline=True
                )
            
            # Show equipped bait
            if active_gear.get("bait"):
                bait_id = active_gear["bait"]
                user_bait = await self.get_user_bait(ctx.author.id)
                equipped_bait = next((b for b in user_bait if b.get("_id") == bait_id), None)
                
                if equipped_bait:
                    embed.add_field(
                        name="🪱 Equipped Bait",
                        value=f"**{equipped_bait['name']}**\n"
                              f"Amount: {equipped_bait.get('amount', 1)}\n"
                              f"Description: {equipped_bait.get('description', 'N/A')[:50]}...",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="🪱 Equipped Bait",
                        value="❌ Bait data not found",
                        inline=True
                    )
            else:
                embed.add_field(
                    name="🪱 Equipped Bait",
                    value="❌ No bait equipped",
                    inline=True
                )
            
            embed.set_footer(text="Use .equiprod and .equipbait to change your gear")
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Fish gear error: {e}")
            await ctx.reply("❌ An error occurred while viewing your gear!")

    @commands.command(name="fishrates", aliases=["rates", "catchrates"])
    async def fish_rates(self, ctx):
        """Show all fishing catch rates with your current gear"""
        try:
            # Get user's active gear
            active_gear = await db.get_active_fishing_gear(ctx.author.id)
            if not active_gear:
                return await ctx.reply("❌ You need fishing gear first! Use `.shop rod` and `.shop bait`")
            
            active_rod_id = active_gear.get("rod")
            active_bait_id = active_gear.get("bait")
            
            if not active_rod_id or not active_bait_id:
                return await ctx.reply("❌ You need both a rod and bait equipped!")
            
            # Get rod data
            user_rods = await self.get_user_rods(ctx.author.id)
            rod = next((r for r in user_rods if r.get("_id") == active_rod_id), None)
            
            if not rod:
                return await ctx.reply("❌ Your equipped rod is no longer available!")
            
            # Get bait data
            user_bait = await self.get_user_bait(ctx.author.id)
            current_bait = next((b for b in user_bait if b.get("_id") == active_bait_id), None)
            
            if not current_bait:
                return await ctx.reply("❌ Your equipped bait is no longer available!")
            
            # Calculate catch rates
            rod_multiplier = rod.get("multiplier", 1.0)
            bait_rates = current_bait.get("catch_rates", {})
            
            percentages = await self.display_catch_percentages_fixed(bait_rates, rod_multiplier)
            
            if not percentages:
                return await ctx.reply("❌ Unable to calculate catch rates!")
            
            # Create embed with all catch rates
            embed = discord.Embed(
                title="🎯 Fishing Catch Rates",
                description=f"**Rod:** {rod['name']} (x{rod_multiplier} multiplier)\n**Bait:** {current_bait['name']}",
                color=discord.Color.blue()
            )
            
            # Sort by catch rate (highest first)
            sorted_percentages = sorted(percentages.items(), key=lambda x: x[1], reverse=True)
            
            # Split into two columns for better display
            left_column = []
            right_column = []
            
            for i, (rarity, chance) in enumerate(sorted_percentages):
                if chance >= 0.001:  # Only show if at least 0.001%
                    rate_text = f"**{rarity.title()}:** {chance:.3f}%"
                    if i % 2 == 0:
                        left_column.append(rate_text)
                    else:
                        right_column.append(rate_text)
            
            if left_column:
                embed.add_field(
                    name="📊 Catch Rates (Part 1)",
                    value="\n".join(left_column),
                    inline=True
                )
            
            if right_column:
                embed.add_field(
                    name="📊 Catch Rates (Part 2)",
                    value="\n".join(right_column),
                    inline=True
                )
            
            # Add summary stats
            total_rate = sum(percentages.values())
            embed.add_field(
                name="📈 Summary",
                value=f"**Total Rate:** {total_rate:.2f}%\n"
                      f"**Rarities:** {len([r for r, c in percentages.items() if c >= 0.001])}\n"
                      f"**Best Chance:** {sorted_percentages[0][0].title()} ({sorted_percentages[0][1]:.3f}%)",
                inline=False
            )
            
            embed.set_footer(text="Rates are calculated with your current rod multiplier and bait")
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Fish rates error: {e}")
            await ctx.reply("❌ An error occurred while calculating catch rates!")

    @commands.command(name="devrod", aliases=["givedevrod", "adminrod"], hidden=True)
    @commands.is_owner()
    async def give_dev_rod(self, ctx, *users: discord.Member):
        """Admin command to give dev rods to specified users - Bot owner only"""
        try:
            
            if not users:
                return await ctx.reply("❌ Please specify at least one user to give the dev rod to!\n"
                                     "Usage: `.devrod @user1 @user2 @user3`")
            
            # Validate that dev_rod exists in our rod data
            if "dev_rod" not in self.rod_data:
                return await ctx.reply("❌ Dev rod not found in rod database!")
            
            successful_gives = []
            failed_gives = []
            
            for user in users:
                try:
                    # Get user's current rods
                    user_rods = await self.get_user_rods(user.id)
                    
                    # Check if user already has a dev rod
                    has_dev_rod = any(rod.get("rod_type") == "dev_rod" for rod in user_rods)
                    
                    if has_dev_rod:
                        failed_gives.append(f"{user.display_name} (already has dev rod)")
                        continue
                    
                    # Create the dev rod with maximum durability and unique ID
                    dev_rod = {
                        "_id": str(uuid.uuid4()),
                        "rod_type": "dev_rod",
                        "name": "Developer's Omnipotent Rod",
                        "description": "A legendary rod wielded only by the creators themselves, bending reality to their will",
                        "multiplier": 1000.0,
                        "durability": 999999,
                        "max_durability": 999999,
                        "rarity": "dev",
                        "special_effects": ["faster_catch", "rare_fish_boost", "legendary_chance", "mythical_attraction", 
                                          "cosmic_fishing", "void_fishing", "quantum_manipulation", "subatomic_detection", 
                                          "reality_control", "dev_powers"],
                        "created_at": datetime.datetime.utcnow().isoformat(),
                        "given_by": ctx.author.id
                    }
                    
                    # Add dev rod to user's collection
                    user_rods.append(dev_rod)
                    
                    # Save updated rods
                    await db.update_user_data(user.id, "fishing_rods", user_rods)
                    
                    successful_gives.append(user.display_name)
                    
                except Exception as e:
                    self.logger.error(f"Error giving dev rod to {user.id}: {e}")
                    failed_gives.append(f"{user.display_name} (error occurred)")
            
            # Create response embed
            embed = discord.Embed(
                title="🛠️ Dev Rod Distribution",
                color=discord.Color.gold()
            )
            
            if successful_gives:
                embed.add_field(
                    name="✅ Successfully Given",
                    value="\n".join([f"• {name}" for name in successful_gives]),
                    inline=False
                )
            
            if failed_gives:
                embed.add_field(
                    name="❌ Failed",
                    value="\n".join([f"• {name}" for name in failed_gives]),
                    inline=False
                )
            
            embed.add_field(
                name="📊 Summary",
                value=f"**Success:** {len(successful_gives)}\n**Failed:** {len(failed_gives)}",
                inline=False
            )
            
            embed.set_footer(text=f"Command executed by {ctx.author.display_name}")
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Dev rod command error: {e}")
            await ctx.reply("❌ An error occurred while giving dev rods!")

# ...existing code...
async def setup(bot):
    await bot.add_cog(Fishing(bot))

class FishInventoryPaginator(discord.ui.View):
    def __init__(self, user_id: int, fish_list: list, current_page: int, total_pages: int, currency: str, rod_data: dict, bait_data: dict, get_user_bait_func):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.fish_list = fish_list
        self.current_page = current_page
        self.total_pages = total_pages
        self.currency = currency
        self.rod_data = rod_data
        self.bait_data = bait_data
        self.get_user_bait = get_user_bait_func
        self.message = None
        self.items_per_page = 5
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        # First page button
        self.children[0].disabled = self.current_page <= 1
        # Previous page button  
        self.children[1].disabled = self.current_page <= 1
        # Next page button
        self.children[2].disabled = self.current_page >= self.total_pages
        # Last page button
        self.children[3].disabled = self.current_page >= self.total_pages
    
    async def create_embed(self):
        """Create embed for current page"""
        if self.current_page == 1:
            # Page 1: Show gear overview
            from utils.db import async_db as db
            
            active_gear = await db.get_active_fishing_gear(self.user_id)
            total_fish = len(self.fish_list)
            total_value = sum(fish.get("value", 0) for fish in self.fish_list)
            
            embed = discord.Embed(
                title="🎣 Fishing Overview",
                description=f"**Total Fish:** {total_fish:,} | **Total Value:** {total_value:,} {self.currency}",
                color=discord.Color.blue()
            )
            
            # Show equipped rod
            if active_gear.get("rod"):
                rod_id = active_gear["rod"]
                if rod_id in self.rod_data:
                    rod = self.rod_data[rod_id]
                    embed.add_field(
                        name="🎣 Equipped Rod",
                        value=f"**{rod['name']}**\n"
                              f"Multiplier: {rod.get('multiplier', 1.0)}x\n"
                              f"Power: {rod.get('power', 1)}\n"
                              f"Durability: {(rod.get('durability', 0.95)*100):.1f}%",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="🎣 Equipped Rod",
                        value="❌ Rod data not found",
                        inline=True
                    )
            else:
                embed.add_field(
                    name="🎣 Equipped Rod",
                    value="❌ No rod equipped\nUse `.rod` to equip one",
                    inline=True
                )
            
            # Show equipped bait
            if active_gear.get("bait"):
                bait_id = active_gear["bait"]
                user_bait = await self.get_user_bait(self.user_id)
                equipped_bait = next((b for b in user_bait if b.get("_id") == bait_id), None)
                
                if equipped_bait:
                    embed.add_field(
                        name="🪱 Equipped Bait",
                        value=f"**{equipped_bait['name']}**\n"
                              f"Amount: {equipped_bait.get('amount', 1)}\n"
                              f"Type: {equipped_bait.get('rarity', 'Common').title()}",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="🪱 Equipped Bait",
                        value="❌ Bait data not found",
                        inline=True
                    )
            else:
                embed.add_field(
                    name="🪱 Equipped Bait",
                    value="❌ No bait equipped\nUse `.bait` to equip some",
                    inline=True
                )
            
            # Add top catches if user has fish
            if self.fish_list:
                sorted_fish = sorted(self.fish_list, key=lambda x: x.get("value", 0), reverse=True)
                top_fish = sorted_fish[:3]
                
                top_catches = []
                for i, fish in enumerate(top_fish, 1):
                    top_catches.append(f"{i}. **{fish.get('name', 'Unknown')}** - {fish.get('value', 0):,} {self.currency}")
                
                embed.add_field(
                    name="🏆 Top Catches",
                    value="\n".join(top_catches),
                    inline=False
                )
            else:
                embed.add_field(
                    name="🐟 Fish Collection",
                    value="No fish caught yet! Use `.fish` to start fishing.",
                    inline=False
                )
            
            embed.set_footer(text=f"Page 1/{self.total_pages} • Use buttons to view your fish collection")
            return embed
        
        else:
            # Pages 2+: Show fish
            fish_page = self.current_page - 1
            start_idx = (fish_page - 1) * self.items_per_page
            end_idx = start_idx + self.items_per_page
            page_fish = self.fish_list[start_idx:end_idx]
            
            total_value = sum(fish.get("value", 0) for fish in self.fish_list)
            embed = discord.Embed(
                title="🐟 Your Fish Collection",
                description=f"**Total Fish:** {len(self.fish_list):,} | **Total Value:** {total_value:,} {self.currency}",
                color=discord.Color.blue()
            )
            
            # Add fish to embed
            for i, fish in enumerate(page_fish, start=start_idx + 1):
                fish_info = (
                    f"**#{i}** • **{fish.get('value', 0):,}** {self.currency}\n"
                    f"**Weight:** {fish.get('weight', 0):.2f} kg\n"
                    f"**Rarity:** {fish.get('type', 'unknown').title()}\n"
                    f"**ID:** `{fish.get('id', 'unknown')[:8]}...`"
                )
                
                embed.add_field(
                    name=f"🐟 {fish.get('name', 'Unknown Fish')}",
                    value=fish_info,
                    inline=False
                )
            
            embed.set_footer(text=f"Page {self.current_page}/{self.total_pages} • Use buttons to navigate")
            return embed
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the command author to use the buttons"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You can't use these buttons!", ephemeral=True)
            return False
        return True
    
    @discord.ui.button(label="⏪", style=discord.ButtonStyle.gray)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to first page"""
        self.current_page = 1
        self.update_buttons()
        embed = await self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page"""
        self.current_page = max(1, self.current_page - 1)
        self.update_buttons()
        embed = await self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page"""
        self.current_page = min(self.total_pages, self.current_page + 1)
        self.update_buttons()
        embed = await self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="⏩", style=discord.ButtonStyle.gray)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to last page"""
        self.current_page = self.total_pages
        self.update_buttons()
        embed = await self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🗑️", style=discord.ButtonStyle.red)
    async def delete_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Delete the paginator message"""
        await interaction.response.edit_message(content="Fish inventory closed.", embed=None, view=None)
    
    async def on_timeout(self):
        """Called when the view times out"""
        if self.message:
            try:
                # Disable all buttons
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass  # Message might be deleted

class GlobalFishPaginator(discord.ui.View):
    def __init__(self, fish_list: list, current_page: int, total_pages: int, currency: str, bot):
        super().__init__(timeout=300)  # 5 minute timeout
        self.fish_list = fish_list
        self.current_page = current_page
        self.total_pages = total_pages
        self.currency = currency
        self.bot = bot
        self.message = None
        self.items_per_page = 2
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        # First page button
        self.children[0].disabled = self.current_page <= 1
        # Previous page button  
        self.children[1].disabled = self.current_page <= 1
        # Next page button
        self.children[2].disabled = self.current_page >= self.total_pages
        # Last page button
        self.children[3].disabled = self.current_page >= self.total_pages
    
    async def create_embed(self):
        """Create embed for current page"""
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_fish = self.fish_list[start_idx:end_idx]
        
        embed = discord.Embed(
            title="🌍 Global Fish Leaderboard",
            description="Top catches from all players",
            color=discord.Color.gold()
        )
        
        for i, fish in enumerate(page_fish, start=start_idx + 1):
            user_id = fish.get("user_id", "Unknown")
            try:
                user = self.bot.get_user(int(user_id))
                username = user.display_name if user else f"User {user_id}"
            except:
                username = f"User {user_id}"
            
            caught_time = fish.get("caught_at", "Unknown")
            if caught_time != "Unknown":
                try:
                    dt = datetime.datetime.fromisoformat(caught_time)
                    caught_time = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    caught_time = "Unknown"
            
            fish_info = f"**#{i} • Caught by:** {username}\n"
            fish_info += f"**Value:** {fish.get('value', 0):,} {self.currency}\n"
            fish_info += f"**Weight:** {fish.get('weight', 0):.2f} kg\n"
            fish_info += f"**Rarity:** {fish.get('type', 'unknown').title()}\n"
            fish_info += f"**Rod Used:** {fish.get('rod_used', 'Unknown')}\n"
            fish_info += f"**Bait Used:** {fish.get('bait_used', 'Unknown')}\n"
            fish_info += f"**Caught:** {caught_time}"
            
            embed.add_field(
                name=f"🐟 {fish.get('name', 'Unknown Fish')}",
                value=fish_info,
                inline=False
            )
        
        embed.set_footer(text=f"Page {self.current_page}/{self.total_pages} • {len(self.fish_list)} total catches")
        return embed
    
    @discord.ui.button(label="⏪", style=discord.ButtonStyle.gray)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to first page"""
        self.current_page = 1
        self.update_buttons()
        embed = await self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page"""
        self.current_page = max(1, self.current_page - 1)
        self.update_buttons()
        embed = await self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page"""
        self.current_page = min(self.total_pages, self.current_page + 1)
        self.update_buttons()
        embed = await self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="⏩", style=discord.ButtonStyle.gray)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to last page"""
        self.current_page = self.total_pages
        self.update_buttons()
        embed = await self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🗑️", style=discord.ButtonStyle.red)
    async def delete_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Delete the paginator message"""
        await interaction.response.edit_message(content="Global fish leaderboard closed.", embed=None, view=None)
    
    async def on_timeout(self):
        """Called when the view times out"""
        if self.message:
            try:
                # Disable all buttons
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass  # Message might be deleted
