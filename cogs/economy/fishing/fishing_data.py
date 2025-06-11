# Fishing Data Management Module
# Centralizes all fish, rod, and bait data and related utilities

import json
import os
from pathlib import Path

class FishingData:
    """Centralized fishing data management"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self._load_all_data()
    
    def _load_all_data(self):
        """Load all fishing data from files and code"""
        self.rod_data = self._load_all_rod_data()
        self.bait_data = self._load_all_bait_data()
        self.fish_database = self._load_fish_database()
        self.rod_aliases = self._load_rod_aliases()
        self.bait_aliases = self._load_bait_aliases()
    
    def _load_all_rod_data(self):
        """Load and combine rod data from both sources"""
        try:
            # Load from JSON file in the correct location
            json_path = Path(__file__).parent.parent.parent.parent / "data" / "shop" / "rods.json"
            if json_path.exists():
                with open(json_path, 'r') as f:
                    json_rods = json.load(f)
            else:
                json_rods = {}
            
            # Add in-code rod definitions if needed
            code_rods = {
                "basic_rod": {
                    "name": "Basic Rod",
                    "multiplier": 1.0,
                    "durability": 0.95,
                    "power": 1
                }
            }
            
            # Merge data
            all_rods = {**code_rods, **json_rods}
            
            # Convert durability and calculate power for JSON rods
            for rod_id, rod_data in all_rods.items():
                if rod_id in json_rods:
                    rod_data["durability"] = self._convert_durability_improved(
                        rod_data.get("durability", 0.95), 
                        rod_data.get("multiplier", 1.0)
                    )
                    rod_data["power"] = self._calculate_power_from_multiplier(
                        rod_data.get("multiplier", 1.0)
                    )
            
            return all_rods
            
        except Exception as e:
            print(f"Error loading rod data: {e}")
            return {}
    
    def _convert_durability_improved(self, json_durability, multiplier):
        """Convert JSON durability with better scaling for expensive rods"""
        base_durability = json_durability
        multiplier_bonus = min(0.15, (multiplier - 1) * 0.05)
        return min(0.999, base_durability + multiplier_bonus)
    
    def _calculate_power_from_multiplier(self, multiplier):
        """Calculate power level from multiplier"""
        if multiplier >= 50:
            return 10
        elif multiplier >= 20:
            return 8
        elif multiplier >= 10:
            return 6
        elif multiplier >= 5:
            return 4
        elif multiplier >= 2:
            return 2
        else:
            return 1
    
    def _load_all_bait_data(self):
        """Load and combine bait data from both sources"""
        try:
            # Load from JSON file in the correct location
            json_path = Path(__file__).parent.parent.parent.parent / "data" / "shop" / "bait.json"
            if json_path.exists():
                with open(json_path, 'r') as f:
                    json_bait = json.load(f)
            else:
                json_bait = {}
            
            # Add in-code bait definitions if needed
            code_bait = {
                "basic_bait": {
                    "name": "Basic Bait",
                    "description": "Simple earthworms",
                    "rarity": "common",
                    "catch_rates": {
                        "junk": 20.0,
                        "tiny": 15.0,
                        "small": 25.0,
                        "common": 30.0,
                        "uncommon": 8.0,
                        "rare": 2.0
                    }
                }
            }
            
            return {**code_bait, **json_bait}
            
        except Exception as e:
            print(f"Error loading bait data: {e}")
            return {}
    
    def _load_rod_aliases(self):
        """Load rod aliases dynamically from JSON file"""
        try:
            json_path = self.base_path / "data" / "rod_aliases.json"
            if json_path.exists():
                with open(json_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading rod aliases: {e}")
            return {}
    
    def _load_bait_aliases(self):
        """Load bait aliases dynamically from JSON file"""
        try:
            json_path = self.base_path / "data" / "bait_aliases.json"
            if json_path.exists():
                with open(json_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading bait aliases: {e}")
            return {}
    
    def _load_fish_database(self):
        """Load fish database - massive fish collection"""
        return {
            "junk": [
                {"name": "Old Boot", "min_weight": 0.5, "max_weight": 2.0, "base_value": 15, "escape_chance": 0.01},
                {"name": "Tin Can", "min_weight": 0.1, "max_weight": 0.5, "base_value": 20, "escape_chance": 0.02},
                {"name": "Plastic Bottle", "min_weight": 0.05, "max_weight": 0.3, "base_value": 12, "escape_chance": 0.01},
                {"name": "Rusty Spoon", "min_weight": 0.02, "max_weight": 0.1, "base_value": 18, "escape_chance": 0.03},
                {"name": "Broken Phone", "min_weight": 0.15, "max_weight": 0.4, "base_value": 25, "escape_chance": 0.02}
            ],
            "tiny": [
                {"name": "Goldfish", "min_weight": 0.05, "max_weight": 0.3, "base_value": 75, "escape_chance": 0.05},
                {"name": "Anchovy", "min_weight": 0.02, "max_weight": 0.1, "base_value": 50, "escape_chance": 0.08},
                {"name": "Sardine", "min_weight": 0.05, "max_weight": 0.2, "base_value": 65, "escape_chance": 0.06},
                {"name": "Small Perch", "min_weight": 0.1, "max_weight": 0.5, "base_value": 90, "escape_chance": 0.10},
                {"name": "Bluegill", "min_weight": 0.1, "max_weight": 0.4, "base_value": 80, "escape_chance": 0.08},
                {"name": "Sunfish", "min_weight": 0.08, "max_weight": 0.3, "base_value": 78, "escape_chance": 0.07},
                {"name": "Minnow School", "min_weight": 0.2, "max_weight": 0.6, "base_value": 120, "escape_chance": 0.15},
                {"name": "Killifish", "min_weight": 0.03, "max_weight": 0.15, "base_value": 70, "escape_chance": 0.12}
            ],
            "small": [
                {"name": "Bass", "min_weight": 0.3, "max_weight": 3.0, "base_value": 180, "escape_chance": 0.12},
                {"name": "Carp", "min_weight": 0.5, "max_weight": 8.0, "base_value": 165, "escape_chance": 0.15},
                {"name": "Trout", "min_weight": 0.2, "max_weight": 2.5, "base_value": 200, "escape_chance": 0.18},
                {"name": "Catfish", "min_weight": 0.8, "max_weight": 12.0, "base_value": 190, "escape_chance": 0.10},
                {"name": "Perch", "min_weight": 0.2, "max_weight": 1.5, "base_value": 160, "escape_chance": 0.15},
                {"name": "Pike", "min_weight": 1.0, "max_weight": 8.0, "base_value": 220, "escape_chance": 0.20},
                {"name": "Walleye", "min_weight": 0.5, "max_weight": 4.0, "base_value": 185, "escape_chance": 0.14}
            ],
            "common": [
                {"name": "Rainbow Trout", "min_weight": 0.8, "max_weight": 6.0, "base_value": 420, "escape_chance": 0.25},
                {"name": "Salmon", "min_weight": 2.0, "max_weight": 20.0, "base_value": 480, "escape_chance": 0.28},
                {"name": "Large Pike", "min_weight": 5.0, "max_weight": 25.0, "base_value": 570, "escape_chance": 0.32},
                {"name": "Striped Bass", "min_weight": 2.0, "max_weight": 18.0, "base_value": 510, "escape_chance": 0.30},
                {"name": "Muskie", "min_weight": 8.0, "max_weight": 30.0, "base_value": 630, "escape_chance": 0.35},
                {"name": "Red Snapper", "min_weight": 1.5, "max_weight": 8.0, "base_value": 450, "escape_chance": 0.25},
                {"name": "Mackerel", "min_weight": 0.8, "max_weight": 3.5, "base_value": 390, "escape_chance": 0.28},
                {"name": "Cod", "min_weight": 2.0, "max_weight": 12.0, "base_value": 435, "escape_chance": 0.22},
                {"name": "Halibut", "min_weight": 5.0, "max_weight": 40.0, "base_value": 675, "escape_chance": 0.26}
            ],
            "uncommon": [
                {"name": "Marlin", "min_weight": 30.0, "max_weight": 300.0, "base_value": 2400, "escape_chance": 0.52},
                {"name": "Swordfish", "min_weight": 25.0, "max_weight": 250.0, "base_value": 2175, "escape_chance": 0.50},
                {"name": "Tarpon", "min_weight": 40.0, "max_weight": 120.0, "base_value": 1650, "escape_chance": 0.55},
                {"name": "King Salmon", "min_weight": 15.0, "max_weight": 50.0, "base_value": 1380, "escape_chance": 0.42},
                {"name": "Tuna", "min_weight": 20.0, "max_weight": 200.0, "base_value": 1950, "escape_chance": 0.48},
                {"name": "Shark", "min_weight": 50.0, "max_weight": 500.0, "base_value": 3300, "escape_chance": 0.60},
                {"name": "Mahi-Mahi", "min_weight": 5.0, "max_weight": 25.0, "base_value": 1200, "escape_chance": 0.38}
            ],
            "rare": [
                {"name": "Giant Squid", "min_weight": 100.0, "max_weight": 800.0, "base_value": 7500, "escape_chance": 0.70},
                {"name": "Blue Whale", "min_weight": 50000.0, "max_weight": 150000.0, "base_value": 45000, "escape_chance": 0.85},
                {"name": "Colossal Octopus", "min_weight": 200.0, "max_weight": 1000.0, "base_value": 12750, "escape_chance": 0.75},
                {"name": "Megalodon", "min_weight": 5000.0, "max_weight": 15000.0, "base_value": 33000, "escape_chance": 0.80}
            ],
            "epic": [
                {"name": "Leviathan", "min_weight": 1000.0, "max_weight": 5000.0, "base_value": 75000, "escape_chance": 0.90},
                {"name": "Kraken", "min_weight": 2000.0, "max_weight": 8000.0, "base_value": 120000, "escape_chance": 0.92},
                {"name": "Sea Dragon", "min_weight": 500.0, "max_weight": 3000.0, "base_value": 90000, "escape_chance": 0.88}
            ],
            "legendary": [
                {"name": "Ancient Leviathan", "min_weight": 10000.0, "max_weight": 50000.0, "base_value": 500000, "escape_chance": 0.95},
                {"name": "Primordial Kraken", "min_weight": 15000.0, "max_weight": 75000.0, "base_value": 750000, "escape_chance": 0.96}
            ],
            "mythical": [
                {"name": "World Serpent", "min_weight": 100000.0, "max_weight": 500000.0, "base_value": 2500000, "escape_chance": 0.98},
                {"name": "Ocean God", "min_weight": 200000.0, "max_weight": 1000000.0, "base_value": 5000000, "escape_chance": 0.99}
            ],
            "ancient": [
                {"name": "Fossil Megalodon", "min_weight": 25000.0, "max_weight": 100000.0, "base_value": 1500000, "escape_chance": 0.97},
                {"name": "Prehistoric Whale", "min_weight": 80000.0, "max_weight": 200000.0, "base_value": 3000000, "escape_chance": 0.98}
            ],
            "divine": [
                {"name": "Neptune's Trident Bearer", "min_weight": 50000.0, "max_weight": 150000.0, "base_value": 3200000, "escape_chance": 0.992},
                {"name": "Celestial Whale", "min_weight": 300000.0, "max_weight": 800000.0, "base_value": 6000000, "escape_chance": 0.997}
            ],
            "cosmic": [
                {"name": "Stellar Whale", "min_weight": 500000.0, "max_weight": 2000000.0, "base_value": 10000000, "escape_chance": 0.9985},
                {"name": "Galactic Kraken", "min_weight": 1000000.0, "max_weight": 5000000.0, "base_value": 20000000, "escape_chance": 0.9992}
            ],
            "transcendent": [
                {"name": "Reality Bender", "min_weight": 1.0, "max_weight": 10000000.0, "base_value": 40000000, "escape_chance": 0.9997},
                {"name": "Dimension Walker", "min_weight": 0.001, "max_weight": 1000000000.0, "base_value": 100000000, "escape_chance": 0.99995}
            ],
            "void": [
                {"name": "Void Leviathan", "min_weight": 0.0, "max_weight": 1.0, "base_value": 200000000, "escape_chance": 0.99997},
                {"name": "Nothingness Fish", "min_weight": -1.0, "max_weight": 0.0, "base_value": 300000000, "escape_chance": 0.99999}
            ],
            "celestial": [
                {"name": "Moon Fish", "min_weight": 384400.0, "max_weight": 7342000.0, "base_value": 120000000, "escape_chance": 0.9999},
                {"name": "Solar Flare Eel", "min_weight": 1989000000.0, "max_weight": 1989000000000.0, "base_value": 400000000, "escape_chance": 0.99999}
            ],
            "mutated": [
                {"name": "Three-Eyed Bass", "min_weight": 2.0, "max_weight": 15.0, "base_value": 10000, "escape_chance": 0.48},
                {"name": "Radioactive Salmon", "min_weight": 5.0, "max_weight": 30.0, "base_value": 34000, "escape_chance": 0.63},
                {"name": "Chernobyl Catfish", "min_weight": 50.0, "max_weight": 200.0, "base_value": 200000, "escape_chance": 0.83}
            ],
            "crystalline": [
                {"name": "Diamond Fish", "min_weight": 0.5, "max_weight": 5.0, "base_value": 300000, "escape_chance": 0.88},
                {"name": "Crystal Shrimp", "min_weight": 0.1, "max_weight": 1.0, "base_value": 180000, "escape_chance": 0.78},
                {"name": "Sapphire Eel", "min_weight": 10.0, "max_weight": 50.0, "base_value": 480000, "escape_chance": 0.92}
            ],
            "subatomic": [
                {"name": "Quantum Plankton", "min_weight": 0.00000001, "max_weight": 0.000001, "base_value": 2000000, "escape_chance": 0.96},
                {"name": "Electron Fish", "min_weight": 0.0000000000000000000000000000009, "max_weight": 0.000000000000000000000000001, "base_value": 6000000, "escape_chance": 0.985},
                {"name": "Proton Whale", "min_weight": 0.00000000000000000000000000167, "max_weight": 0.0000000000000000000000001, "base_value": 14000000, "escape_chance": 0.992},
                {"name": "Neutron Star Fish", "min_weight": 1000000000000000.0, "max_weight": 2000000000000000.0, "base_value": 40000000, "escape_chance": 0.997}
            ],
            "super": [
                {"name": "Superman Fish", "min_weight": 100.0, "max_weight": 500.0, "base_value": 20000000, "escape_chance": 0.94},
                {"name": "Flash Minnow", "min_weight": 0.01, "max_weight": 0.1, "base_value": 10000000, "escape_chance": 0.992},
                {"name": "Wonder Woman Tuna", "min_weight": 200.0, "max_weight": 800.0, "base_value": 30000000, "escape_chance": 0.96}
            ]
        }
    
    def get_rod_data(self):
        """Get rod data"""
        return self.rod_data
    
    def get_bait_data(self):
        """Get bait data"""
        return self.bait_data
    
    def get_fish_database(self):
        """Get fish database"""
        return self.fish_database
    
    def get_rod_aliases(self):
        """Get rod aliases"""
        return self.rod_aliases
    
    def get_bait_aliases(self):
        """Get bait aliases"""
        return self.bait_aliases
    
    def resolve_rod_alias(self, rod_input: str) -> str:
        """Resolve rod alias to full rod ID"""
        rod_lower = rod_input.lower().strip()
        
        # Check if it's already a direct match
        if rod_lower in self.rod_data:
            return rod_lower
        
        # Check aliases
        for alias, full_id in self.rod_aliases.items():
            if rod_lower == alias.lower():
                return full_id
        
        # Check partial matches in rod names
        for rod_id, rod_data in self.rod_data.items():
            if rod_lower in rod_data.get('name', '').lower():
                return rod_id
        
        return None
    
    def resolve_bait_alias(self, bait_input: str) -> str:
        """Resolve bait alias to full bait ID"""
        bait_lower = bait_input.lower().strip()
        
        # Check if it's already a direct match
        if bait_lower in self.bait_data:
            return bait_lower
        
        # Check aliases
        for alias, full_id in self.bait_aliases.items():
            if bait_lower == alias.lower():
                return full_id
        
        # Check partial matches in bait names
        for bait_id, bait_data in self.bait_data.items():
            if bait_lower in bait_data.get('name', '').lower():
                return bait_id
        
        return None
    
    def apply_rod_multiplier(self, bait_rates, rod_multiplier):
        """Apply rod multiplier to favor higher rarities - Fixed version"""
        if rod_multiplier <= 1.0:
            return bait_rates.copy()
        
        adjusted_rates = {}
        rarity_order = ["junk", "tiny", "small", "common", "uncommon", "rare", "epic", "legendary", "mythical", "ancient", "divine", "cosmic", "transcendent", "void", "celestial", "mutated", "crystalline", "subatomic", "super", "dev"]
        
        for rarity, base_rate in bait_rates.items():
            if base_rate == 0:
                adjusted_rates[rarity] = 0
                continue
                
            if rarity in rarity_order:
                rarity_index = rarity_order.index(rarity)
                # Apply multiplier effect based on rarity tier
                if rarity_index >= 15:  # Ultra rare fish (subatomic, super, etc.)
                    multiplier_effect = 1 + ((rod_multiplier - 1) * 0.8)  # 80% of rod power
                elif rarity_index >= 10:  # High tier fish (divine, cosmic, etc.)
                    multiplier_effect = 1 + ((rod_multiplier - 1) * 1.2)  # 120% of rod power
                elif rarity_index >= 6:  # Mid-high tier (epic, legendary, etc.)
                    multiplier_effect = 1 + ((rod_multiplier - 1) * 1.5)  # 150% of rod power
                elif rarity_index >= 3:  # Mid tier (uncommon, rare)
                    multiplier_effect = 1 + ((rod_multiplier - 1) * 1.0)  # Normal rod power
                else:  # Low tier (junk, tiny, small, common)
                    multiplier_effect = max(0.1, 1 - ((rod_multiplier - 1) * 0.3))  # Reduce low tier
                
                adjusted_rates[rarity] = base_rate * multiplier_effect
            else:
                adjusted_rates[rarity] = base_rate
        
        return adjusted_rates
    
    def calculate_catch_percentages(self, bait_rates, rod_multiplier):
        """Calculate catch percentages with rod multiplier"""
        adjusted_rates = self.apply_rod_multiplier(bait_rates, rod_multiplier)
        total_weight = sum(adjusted_rates.values())
        
        if total_weight == 0:
            return {}
        
        percentages = {}
        for rarity, weight in adjusted_rates.items():
            percentages[rarity] = (weight / total_weight) * 100
        
        return percentages
