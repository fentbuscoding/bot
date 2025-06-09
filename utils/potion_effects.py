import asyncio
import datetime
import json
import os
from typing import Dict, Optional, Any
from utils.db import async_db as db

class PotionEffects:
    def __init__(self, bot):
        self.bot = bot
        self.active_effects = {}  # user_id: {effect_name: {expiry, data}}
        self.load_potion_data()
        
    def load_potion_data(self):
        """Load potion data from JSON file"""
        try:
            potion_file = os.path.join(os.getcwd(), "data", "shop", "potions.json")
            with open(potion_file, 'r') as f:
                self.potion_data = json.load(f)
        except Exception as e:
            print(f"Error loading potion data: {e}")
            self.potion_data = {}
            
    async def apply_potion_effect(self, user_id: int, potion_id: str) -> bool:
        """Apply a potion effect to a user"""
        if potion_id not in self.potion_data:
            return False
            
        potion = self.potion_data[potion_id]
        duration = potion.get("duration", 600)  # Default 10 minutes
        effects = potion.get("effects", {})
        
        # Calculate expiry time
        expiry = datetime.datetime.now() + datetime.timedelta(seconds=duration)
        
        # Store effect in memory and database
        if user_id not in self.active_effects:
            self.active_effects[user_id] = {}
            
        effect_data = {
            "potion_id": potion_id,
            "expiry": expiry.isoformat(),
            "effects": effects,
            "potion_name": potion.get("name", potion_id)
        }
        
        self.active_effects[user_id][potion_id] = effect_data
        
        # Save to database
        await db.db.users.update_one(
            {"_id": str(user_id)},
            {"$set": {f"active_effects.{potion_id}": effect_data}},
            upsert=True
        )
        
        return True
        
    async def remove_effect(self, user_id: int, effect_name: str):
        """Remove an effect from a user"""
        if user_id in self.active_effects:
            self.active_effects[user_id].pop(effect_name, None)
            
        await db.db.users.update_one(
            {"_id": str(user_id)},
            {"$unset": {f"active_effects.{effect_name}": ""}}
        )
        
    async def get_user_effects(self, user_id: int) -> Dict[str, Any]:
        """Get all active effects for a user"""
        # Load from database if not in memory
        if user_id not in self.active_effects:
            user_data = await db.db.users.find_one({"_id": str(user_id)})
            if user_data and "active_effects" in user_data:
                self.active_effects[user_id] = user_data["active_effects"]
            else:
                self.active_effects[user_id] = {}
                
        # Clean expired effects
        now = datetime.datetime.now()
        expired_effects = []
        
        for effect_name, effect_data in self.active_effects[user_id].items():
            expiry = datetime.datetime.fromisoformat(effect_data["expiry"])
            if now > expiry:
                expired_effects.append(effect_name)
                
        # Remove expired effects
        for effect_name in expired_effects:
            await self.remove_effect(user_id, effect_name)
            
        return self.active_effects.get(user_id, {})
        
    async def has_effect(self, user_id: int, effect_type: str) -> bool:
        """Check if user has a specific type of effect"""
        effects = await self.get_user_effects(user_id)
        
        for effect_data in effects.values():
            if effect_type in effect_data.get("effects", {}):
                return True
        return False
        
    async def get_effect_multiplier(self, user_id: int, effect_type: str) -> float:
        """Get the multiplier for a specific effect type"""
        effects = await self.get_user_effects(user_id)
        multiplier = 1.0
        
        for effect_data in effects.values():
            effect_value = effect_data.get("effects", {}).get(effect_type)
            if effect_value:
                if isinstance(effect_value, (int, float)):
                    multiplier *= effect_value
                elif effect_value is True:
                    multiplier *= 1.5  # Default boost for boolean effects
                    
        return multiplier
        
    async def get_cooldown_reduction(self, user_id: int) -> float:
        """Get the cooldown reduction percentage (0-1)"""
        effects = await self.get_user_effects(user_id)
        reduction = 0.0
        
        for effect_data in effects.values():
            effect_effects = effect_data.get("effects", {})
            
            # Check for general cooldown reduction
            if "cooldown_reduction" in effect_effects:
                reduction = max(reduction, effect_effects["cooldown_reduction"])
                
            # Check for cooldown removal (100% reduction)
            if effect_effects.get("cooldown_removal"):
                reduction = 1.0
                break
                
        return min(reduction, 0.95)  # Cap at 95% reduction
        
    async def apply_fishing_effects(self, user_id: int, base_value: int) -> int:
        """Apply fishing-related potion effects"""
        multiplier = await self.get_effect_multiplier(user_id, "fishing_value_multiplier")
        rare_multiplier = await self.get_effect_multiplier(user_id, "rare_chance_multiplier")
        
        # Apply general multipliers
        value = int(base_value * multiplier)
        
        return value
        
    async def apply_work_effects(self, user_id: int, base_income: int) -> int:
        """Apply work-related potion effects"""
        work_multiplier = await self.get_effect_multiplier(user_id, "work_income_multiplier")
        reward_multiplier = await self.get_effect_multiplier(user_id, "work_reward_boost")
        all_multiplier = await self.get_effect_multiplier(user_id, "all_rewards_multiplier")
        
        # Apply multipliers
        income = int(base_income * work_multiplier * reward_multiplier * all_multiplier)
        
        return income
        
    async def check_guaranteed_effects(self, user_id: int) -> Dict[str, bool]:
        """Check for guaranteed effects (like guaranteed rare fish)"""
        effects = await self.get_user_effects(user_id)
        guaranteed = {}
        
        for effect_data in effects.values():
            effect_effects = effect_data.get("effects", {})
            
            if effect_effects.get("guaranteed_rare_fish"):
                guaranteed["rare_fish"] = True
            if effect_effects.get("void_mastery"):
                guaranteed["void_mastery"] = True
            if effect_effects.get("cosmic_power"):
                guaranteed["cosmic_power"] = True
                
        return guaranteed
        
    async def get_active_effects_display(self, user_id: int) -> str:
        """Get a formatted string of active effects for display"""
        effects = await self.get_user_effects(user_id)
        
        if not effects:
            return "No active effects"
            
        display_lines = []
        for effect_data in effects.values():
            name = effect_data.get("potion_name", "Unknown")
            expiry = datetime.datetime.fromisoformat(effect_data["expiry"])
            time_left = expiry - datetime.datetime.now()
            
            if time_left.total_seconds() > 0:
                minutes = int(time_left.total_seconds() // 60)
                seconds = int(time_left.total_seconds() % 60)
                time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
                
                emoji = self.potion_data.get(effect_data.get("potion_id", ""), {}).get("emoji", "🧪")
                display_lines.append(f"{emoji} {name} - {time_str}")
                
        return "\n".join(display_lines) if display_lines else "No active effects"

# Global instance to be used across cogs
potion_effects = None

def get_potion_effects(bot):
    """Get or create the global potion effects instance"""
    global potion_effects
    if potion_effects is None:
        potion_effects = PotionEffects(bot)
    return potion_effects
