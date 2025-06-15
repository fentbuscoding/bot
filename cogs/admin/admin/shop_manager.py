"""
Shop Management Module
Admin functions for managing shop items and categories.
"""

import json
import os
from typing import Dict, List, Optional, Any
from utils.db import AsyncDatabase
from .constants import SHOP_CATEGORIES, DEFAULT_FISHING_ITEMS, ERROR_MESSAGES, SUCCESS_MESSAGES

db = AsyncDatabase.get_instance()

class ShopManager:
    """Manages shop items and data"""
    
    def __init__(self):
        self.data_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'shop.json')
        self.shop_data = {}
        self.load_shop_data()
    
    def load_shop_data(self) -> None:
        """Load shop data from JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.shop_data = data.get('shops', {})
            else:
                # Initialize with default data
                self.shop_data = {
                    "bait_shop": DEFAULT_FISHING_ITEMS["bait_shop"],
                    "rod_shop": DEFAULT_FISHING_ITEMS["rod_shop"],
                    "items": {},
                    "upgrades": {},
                    "potions": {}
                }
                self.save_shop_data()
        except Exception as e:
            print(f"Error loading shop data: {e}")
            self.shop_data = {}
    
    def save_shop_data(self) -> None:
        """Save shop data to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w') as f:
                json.dump({"shops": self.shop_data}, f, indent=2)
        except Exception as e:
            print(f"Error saving shop data: {e}")
    
    def get_server_shop(self, guild_id: int) -> dict:
        """Get server-specific shop data"""
        return self.shop_data.get(str(guild_id), {})
    
    def validate_shop_type(self, shop_type: str) -> bool:
        """Validate if shop type is valid"""
        valid_types = ["items", "upgrades", "rods", "bait", "potions", "bait_shop", "rod_shop"]
        return shop_type.lower() in valid_types
    
    def add_item_to_shop(self, shop_type: str, item_id: str, item_data: Dict[str, Any]) -> bool:
        """Add an item to the specified shop"""
        try:
            if not self.validate_shop_type(shop_type):
                return False
            
            if shop_type not in self.shop_data:
                self.shop_data[shop_type] = {}
            
            self.shop_data[shop_type][item_id] = item_data
            self.save_shop_data()
            return True
            
        except Exception as e:
            print(f"Error adding item to shop: {e}")
            return False
    
    def remove_item_from_shop(self, shop_type: str, item_id: str) -> bool:
        """Remove an item from the specified shop"""
        try:
            if shop_type not in self.shop_data:
                return False
            
            if item_id not in self.shop_data[shop_type]:
                return False
            
            del self.shop_data[shop_type][item_id]
            self.save_shop_data()
            return True
            
        except Exception as e:
            print(f"Error removing item from shop: {e}")
            return False
    
    def update_item_in_shop(self, shop_type: str, item_id: str, field: str, value: Any) -> bool:
        """Update a specific field of an item in the shop"""
        try:
            if shop_type not in self.shop_data:
                return False
            
            if item_id not in self.shop_data[shop_type]:
                return False
            
            # Convert value to appropriate type
            if field == "price" or field == "amount":
                value = int(value)
            elif field == "multiplier":
                value = float(value)
            
            self.shop_data[shop_type][item_id][field] = value
            self.save_shop_data()
            return True
            
        except Exception as e:
            print(f"Error updating item in shop: {e}")
            return False
    
    def get_shop_items(self, shop_type: str) -> Dict[str, Any]:
        """Get all items from a specific shop"""
        return self.shop_data.get(shop_type, {})
    
    def get_all_shops(self) -> Dict[str, Dict[str, Any]]:
        """Get all shop data"""
        return self.shop_data
    
    def search_items(self, query: str) -> List[Dict[str, Any]]:
        """Search for items across all shops"""
        results = []
        
        for shop_type, items in self.shop_data.items():
            for item_id, item_data in items.items():
                item_name = item_data.get("name", item_id)
                if query.lower() in item_name.lower() or query.lower() in item_id.lower():
                    results.append({
                        "shop_type": shop_type,
                        "item_id": item_id,
                        "item_data": item_data
                    })
        
        return results
    
    def validate_item_data(self, item_data_str: str) -> Optional[Dict[str, Any]]:
        """Validate and parse item data JSON string"""
        try:
            item_data = json.loads(item_data_str)
            
            # Required fields
            required_fields = ["name", "price"]
            for field in required_fields:
                if field not in item_data:
                    return None
            
            # Validate field types
            if not isinstance(item_data["price"], (int, float)) or item_data["price"] < 0:
                return None
            
            return item_data
            
        except json.JSONDecodeError:
            return None
    
    def get_shop_stats(self) -> Dict[str, Any]:
        """Get statistics about all shops"""
        stats = {
            "total_shops": len(self.shop_data),
            "total_items": 0,
            "shop_breakdown": {}
        }
        
        for shop_type, items in self.shop_data.items():
            item_count = len(items)
            stats["total_items"] += item_count
            stats["shop_breakdown"][shop_type] = {
                "items": item_count,
                "total_value": sum(item.get("price", 0) for item in items.values())
            }
        
        return stats
    
    def export_shop_data(self, shop_type: Optional[str] = None) -> Dict[str, Any]:
        """Export shop data for backup or transfer"""
        if shop_type:
            return {shop_type: self.shop_data.get(shop_type, {})}
        return self.shop_data
    
    def import_shop_data(self, data: Dict[str, Any], merge: bool = False) -> bool:
        """Import shop data from backup or external source"""
        try:
            if merge:
                # Merge with existing data
                for shop_type, items in data.items():
                    if shop_type not in self.shop_data:
                        self.shop_data[shop_type] = {}
                    self.shop_data[shop_type].update(items)
            else:
                # Replace existing data
                self.shop_data = data
            
            self.save_shop_data()
            return True
            
        except Exception as e:
            print(f"Error importing shop data: {e}")
            return False


class ServerShopManager:
    """Manages server-specific shops and potions"""
    
    def __init__(self):
        pass
    
    async def get_server_potions(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get server-specific potions"""
        try:
            potions = await db.get_server_potions(guild_id)
            return potions or []
        except Exception as e:
            print(f"Error getting server potions: {e}")
            return []
    
    async def add_server_potion(self, guild_id: int, potion_data: Dict[str, Any]) -> bool:
        """Add a potion to server shop"""
        try:
            await db.add_server_potion(guild_id, potion_data)
            return True
        except Exception as e:
            print(f"Error adding server potion: {e}")
            return False
    
    async def remove_server_potion(self, guild_id: int, potion_id: str) -> bool:
        """Remove a potion from server shop"""
        try:
            await db.remove_server_potion(guild_id, potion_id)
            return True
        except Exception as e:
            print(f"Error removing server potion: {e}")
            return False
    
    async def update_server_potion(self, guild_id: int, potion_id: str, updates: Dict[str, Any]) -> bool:
        """Update a server potion"""
        try:
            await db.update_server_potion(guild_id, potion_id, updates)
            return True
        except Exception as e:
            print(f"Error updating server potion: {e}")
            return False
    
    async def validate_potion_data(self, name: str, price: int, potion_type: str, 
                                 multiplier: float, duration: int, description: str = None) -> Optional[Dict[str, Any]]:
        """Validate potion data"""
        try:
            # Validate price
            if price < 0:
                return None
            
            # Validate type
            valid_types = ["experience", "currency", "fishing", "work", "trading", "luck"]
            if potion_type not in valid_types:
                return None
            
            # Validate multiplier
            if multiplier <= 0:
                return None
            
            # Validate duration
            if duration <= 0:
                return None
            
            return {
                "name": name,
                "price": price,
                "type": potion_type,
                "multiplier": multiplier,
                "duration": duration,
                "description": description or f"{potion_type.title()} boost potion"
            }
            
        except Exception:
            return None
