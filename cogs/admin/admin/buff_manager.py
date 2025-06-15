"""
Buff Management Module
Admin functions for managing global buffs and events.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from utils.db import AsyncDatabase
from .constants import BUFF_TYPES, ERROR_MESSAGES, SUCCESS_MESSAGES

db = AsyncDatabase.get_instance()

class BuffManager:
    """Manages global buffs and events"""
    
    def __init__(self):
        self.active_buffs = {}  # guild_id -> {buff_type: buff_data}
    
    async def activate_buff(self, guild_id: int, buff_type: str, duration_hours: Optional[int] = None) -> Tuple[bool, str]:
        """Activate a global buff for a guild"""
        try:
            if buff_type not in BUFF_TYPES:
                return False, f"Invalid buff type. Available: {', '.join(BUFF_TYPES.keys())}"
            
            buff_config = BUFF_TYPES[buff_type]
            duration = duration_hours or buff_config["duration_hours"]
            
            # Create buff data
            buff_data = {
                "type": buff_type,
                "name": buff_config["name"],
                "description": buff_config["description"],
                "multiplier": buff_config["multiplier"],
                "emoji": buff_config["emoji"],
                "activated_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(hours=duration),
                "duration_hours": duration
            }
            
            # Store in database
            await db.activate_guild_buff(guild_id, buff_data)
            
            # Cache locally
            if guild_id not in self.active_buffs:
                self.active_buffs[guild_id] = {}
            self.active_buffs[guild_id][buff_type] = buff_data
            
            return True, f"{buff_config['emoji']} {buff_config['name']} activated for {duration} hours!"
            
        except Exception as e:
            print(f"Error activating buff: {e}")
            return False, ERROR_MESSAGES["database_error"]
    
    async def deactivate_buff(self, guild_id: int, buff_type: str) -> Tuple[bool, str]:
        """Deactivate a global buff for a guild"""
        try:
            # Remove from database
            await db.deactivate_guild_buff(guild_id, buff_type)
            
            # Remove from cache
            if guild_id in self.active_buffs and buff_type in self.active_buffs[guild_id]:
                del self.active_buffs[guild_id][buff_type]
            
            buff_name = BUFF_TYPES.get(buff_type, {}).get("name", buff_type)
            return True, f"✅ {buff_name} has been deactivated."
            
        except Exception as e:
            print(f"Error deactivating buff: {e}")
            return False, ERROR_MESSAGES["database_error"]
    
    async def get_active_buffs(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all active buffs for a guild"""
        try:
            # Get from database
            buffs = await db.get_guild_active_buffs(guild_id)
            
            # Filter out expired buffs
            active_buffs = []
            now = datetime.now()
            
            for buff in buffs:
                expires_at = buff.get("expires_at")
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                
                if expires_at > now:
                    active_buffs.append(buff)
                else:
                    # Auto-cleanup expired buffs
                    await self.deactivate_buff(guild_id, buff["type"])
            
            return active_buffs
            
        except Exception as e:
            print(f"Error getting active buffs: {e}")
            return []
    
    async def is_buff_active(self, guild_id: int, buff_type: str) -> bool:
        """Check if a specific buff is active"""
        active_buffs = await self.get_active_buffs(guild_id)
        return any(buff["type"] == buff_type for buff in active_buffs)
    
    async def get_buff_multiplier(self, guild_id: int, buff_type: str) -> float:
        """Get the multiplier for a specific buff type if active"""
        active_buffs = await self.get_active_buffs(guild_id)
        
        for buff in active_buffs:
            if buff["type"] == buff_type:
                return buff.get("multiplier", 1.0)
        
        return 1.0  # No buff active
    
    async def extend_buff(self, guild_id: int, buff_type: str, additional_hours: int) -> Tuple[bool, str]:
        """Extend the duration of an active buff"""
        try:
            active_buffs = await self.get_active_buffs(guild_id)
            
            buff_found = None
            for buff in active_buffs:
                if buff["type"] == buff_type:
                    buff_found = buff
                    break
            
            if not buff_found:
                return False, f"No active {buff_type} buff found."
            
            # Calculate new expiration time
            current_expires = buff_found["expires_at"]
            if isinstance(current_expires, str):
                current_expires = datetime.fromisoformat(current_expires)
            
            new_expires = current_expires + timedelta(hours=additional_hours)
            
            # Update in database
            await db.extend_guild_buff(guild_id, buff_type, new_expires)
            
            buff_name = BUFF_TYPES.get(buff_type, {}).get("name", buff_type)
            return True, f"✅ {buff_name} extended by {additional_hours} hours!"
            
        except Exception as e:
            print(f"Error extending buff: {e}")
            return False, ERROR_MESSAGES["database_error"]
    
    async def rotate_global_buff(self) -> str:
        """Randomly select and activate a global buff"""
        try:
            # Get all guilds
            guilds = await db.get_all_guild_ids()
            
            if not guilds:
                return "No guilds found for buff rotation."
            
            # Select random buff type
            buff_type = random.choice(list(BUFF_TYPES.keys()))
            buff_config = BUFF_TYPES[buff_type]
            
            activated_count = 0
            
            # Activate for all guilds
            for guild_id in guilds:
                # Check if this buff type is already active
                if not await self.is_buff_active(guild_id, buff_type):
                    success, _ = await self.activate_buff(guild_id, buff_type)
                    if success:
                        activated_count += 1
                
            return f"{buff_config['emoji']} {buff_config['name']} activated globally for {activated_count} servers!"
            
        except Exception as e:
            print(f"Error rotating global buff: {e}")
            return "Error occurred during buff rotation."
    
    async def schedule_buff(self, guild_id: int, buff_type: str, start_time: datetime, 
                          duration_hours: int) -> Tuple[bool, str]:
        """Schedule a buff to activate at a specific time"""
        try:
            if buff_type not in BUFF_TYPES:
                return False, f"Invalid buff type. Available: {', '.join(BUFF_TYPES.keys())}"
            
            buff_config = BUFF_TYPES[buff_type]
            
            # Create scheduled buff data
            scheduled_buff = {
                "guild_id": guild_id,
                "buff_type": buff_type,
                "buff_name": buff_config["name"],
                "start_time": start_time,
                "duration_hours": duration_hours,
                "scheduled_at": datetime.now(),
                "status": "scheduled"
            }
            
            # Store in database
            await db.schedule_guild_buff(scheduled_buff)
            
            return True, f"✅ {buff_config['name']} scheduled for {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
            
        except Exception as e:
            print(f"Error scheduling buff: {e}")
            return False, ERROR_MESSAGES["database_error"]
    
    async def get_scheduled_buffs(self, guild_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get scheduled buffs for a guild or all guilds"""
        try:
            return await db.get_scheduled_buffs(guild_id)
        except Exception as e:
            print(f"Error getting scheduled buffs: {e}")
            return []
    
    async def cancel_scheduled_buff(self, schedule_id: str) -> Tuple[bool, str]:
        """Cancel a scheduled buff"""
        try:
            success = await db.cancel_scheduled_buff(schedule_id)
            
            if success:
                return True, "✅ Scheduled buff cancelled."
            else:
                return False, "❌ Scheduled buff not found."
                
        except Exception as e:
            print(f"Error cancelling scheduled buff: {e}")
            return False, ERROR_MESSAGES["database_error"]
    
    async def get_buff_history(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get buff activation history for a guild"""
        try:
            return await db.get_guild_buff_history(guild_id, limit)
        except Exception as e:
            print(f"Error getting buff history: {e}")
            return []
    
    async def get_buff_stats(self, guild_id: int) -> Dict[str, Any]:
        """Get buff usage statistics for a guild"""
        try:
            history = await self.get_buff_history(guild_id, 100)  # Get more for stats
            
            if not history:
                return {"total_buffs": 0, "most_used": "None", "total_duration": 0}
            
            buff_counts = {}
            total_duration = 0
            
            for buff in history:
                buff_type = buff.get("type", "unknown")
                duration = buff.get("duration_hours", 0)
                
                buff_counts[buff_type] = buff_counts.get(buff_type, 0) + 1
                total_duration += duration
            
            most_used = max(buff_counts.items(), key=lambda x: x[1])[0] if buff_counts else "None"
            
            return {
                "total_buffs": len(history),
                "most_used": most_used,
                "total_duration": total_duration,
                "buff_breakdown": buff_counts
            }
            
        except Exception as e:
            print(f"Error getting buff stats: {e}")
            return {"total_buffs": 0, "most_used": "None", "total_duration": 0}
    
    def get_available_buff_types(self) -> Dict[str, Dict[str, Any]]:
        """Get all available buff types and their configurations"""
        return BUFF_TYPES
