import json
import os
import logging
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List

class StatsLogger:
    def __init__(self):
        self.logger = logging.getLogger('StatsLogger')
        self.stats_file = 'data/stats.json'
        self._ensure_data_directory()
        self._initialize_stats_file()
        
    def _ensure_data_directory(self):
        """Ensure the data directory exists"""
        os.makedirs('data', exist_ok=True)
        
    def _initialize_stats_file(self):
        """Initialize the stats file with default structure if it doesn't exist"""
        if not os.path.exists(self.stats_file):
            default_stats = {
                "command_usage": {},
                "economy_stats": {
                    "biggest_wins": [],
                    "biggest_losses": []
                },
                "last_updated": None
            }
            self._save_stats(default_stats)
    
    def _load_stats(self) -> Dict[str, Any]:
        """Load stats from the JSON file"""
        try:
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.logger.warning("Stats file corrupted or missing, recreating...")
            self._initialize_stats_file()
            return self._load_stats()
    
    def _save_stats(self, stats: Dict[str, Any]):
        """Save stats to the JSON file"""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(stats, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save stats: {e}")
    
    def log_command_usage(self, command_name: str):
        """Log that a command was used"""
        stats = self._load_stats()
        
        # Initialize command count if not exists
        if "command_usage" not in stats:
            stats["command_usage"] = {}
            
        if command_name not in stats["command_usage"]:
            stats["command_usage"][command_name] = 0
            
        stats["command_usage"][command_name] += 1
        stats["last_updated"] = datetime.now().isoformat()
        
        self._save_stats(stats)
    
    def log_economy_transaction(self, user_id: int, command_name: str, amount: int, is_win: bool):
        """Log an economy transaction (win or loss)"""
        if amount == 0:
            return
            
        stats = self._load_stats()
        
        # Initialize economy stats if not exists
        if "economy_stats" not in stats:
            stats["economy_stats"] = {
                "biggest_wins": [],
                "biggest_losses": []
            }
            
        transaction = {
            "user_id": str(user_id),
            "command": command_name,
            "amount": amount,
            "timestamp": datetime.now().isoformat()
        }
        
        key = "biggest_wins" if is_win else "biggest_losses"
        stats["economy_stats"][key].append(transaction)
        
        # Keep only top 10 wins/losses
        stats["economy_stats"][key].sort(
            key=lambda x: x["amount"], 
            reverse=is_win
        )
        stats["economy_stats"][key] = stats["economy_stats"][key][:10]
        
        stats["last_updated"] = datetime.now().isoformat()
        self._save_stats(stats)
    
    def get_command_usage_stats(self) -> Dict[str, int]:
        """Get command usage statistics"""
        stats = self._load_stats()
        return stats.get("command_usage", {})
    
    def get_top_commands(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top used commands"""
        usage = self.get_command_usage_stats()
        sorted_commands = sorted(usage.items(), key=lambda x: x[1], reverse=True)
        return [{"command": cmd, "count": count} for cmd, count in sorted_commands[:limit]]
    
    def get_least_used_commands(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get least used commands"""
        usage = self.get_command_usage_stats()
        sorted_commands = sorted(usage.items(), key=lambda x: x[1])
        return [{"command": cmd, "count": count} for cmd, count in sorted_commands[:limit]]
    
    def get_biggest_wins(self) -> List[Dict[str, Any]]:
        """Get biggest economy wins"""
        stats = self._load_stats()
        return stats.get("economy_stats", {}).get("biggest_wins", [])
    
    def get_biggest_losses(self) -> List[Dict[str, Any]]:
        """Get biggest economy losses"""
        stats = self._load_stats()
        return stats.get("economy_stats", {}).get("biggest_losses", [])