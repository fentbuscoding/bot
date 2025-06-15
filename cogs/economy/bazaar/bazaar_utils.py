"""
Bazaar Utilities Module
Helper functions and item management for the bazaar system.
"""

import random
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from utils.db import AsyncDatabase

db = AsyncDatabase.get_instance()

class BazaarItemGenerator:
    """Generate and manage bazaar items"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_items = {}
        self.load_base_items()
    
    def load_base_items(self):
        """Load base item configurations"""
        # This would typically load from a database or config file
        self.base_items = {
            "fishing_rod": {
                "advanced_rod": {"base_price": 500, "rarity": "uncommon", "type": "fishing_rod"},
                "pro_rod": {"base_price": 2000, "rarity": "rare", "type": "fishing_rod"},
                "master_rod": {"base_price": 10000, "rarity": "epic", "type": "fishing_rod"},
            },
            "bait": {
                "pro_bait": {"base_price": 50, "rarity": "common", "type": "bait"},
                "super_bait": {"base_price": 200, "rarity": "uncommon", "type": "bait"},
                "master_bait": {"base_price": 1000, "rarity": "rare", "type": "bait"},
            },
            "potion": {
                "experience_boost": {"base_price": 1000, "rarity": "uncommon", "type": "potion"},
                "luck_potion": {"base_price": 2500, "rarity": "rare", "type": "potion"},
                "treasure_finder": {"base_price": 5000, "rarity": "epic", "type": "potion"},
            },
            "upgrade": {
                "bank_upgrade": {"base_price": 2500, "rarity": "uncommon", "type": "upgrade"},
                "inventory_expansion": {"base_price": 5000, "rarity": "rare", "type": "upgrade"},
                "premium_features": {"base_price": 15000, "rarity": "epic", "type": "upgrade"},
            }
        }
    
    def generate_bazaar_items(self, count: int = 6) -> List[Dict[str, Any]]:
        """Generate random bazaar items with discounts"""
        items = []
        
        # Flatten all available items
        all_items = []
        for category, category_items in self.base_items.items():
            for item_id, item_data in category_items.items():
                all_items.append({
                    "id": item_id,
                    "name": item_id.replace("_", " ").title(),
                    "category": category,
                    **item_data
                })
        
        # Select random items based on rarity weights
        selected_items = self._weighted_selection(all_items, count)
        
        # Apply discounts and finalize
        for item in selected_items:
            discount = random.uniform(
                self.config.get("min_discount", 0.1),
                self.config.get("max_discount", 0.4)
            )
            
            original_price = item["base_price"]
            discounted_price = int(original_price * (1 - discount))
            
            items.append({
                "id": item["id"],
                "name": item["name"],
                "category": item["category"],
                "original_price": original_price,
                "price": discounted_price,
                "discount": discount,
                "rarity": item["rarity"],
                "type": item["type"],
                "stock": random.randint(1, 10),  # Random stock amount
                "description": self._generate_item_description(item)
            })
        
        return items
    
    def _weighted_selection(self, items: List[Dict], count: int) -> List[Dict]:
        """Select items based on rarity weights"""
        rarity_weights = self.config.get("quality_weights", {
            "common": 0.5,
            "uncommon": 0.3,
            "rare": 0.15,
            "epic": 0.04,
            "legendary": 0.01
        })
        
        selected = []
        for _ in range(min(count, len(items))):
            # Calculate weights for remaining items
            weights = [rarity_weights.get(item["rarity"], 0.1) for item in items]
            
            # Select item based on weights
            if weights:
                selected_item = random.choices(items, weights=weights, k=1)[0]
                selected.append(selected_item)
                items.remove(selected_item)  # Avoid duplicates
        
        return selected
    
    def _generate_item_description(self, item: Dict[str, Any]) -> str:
        """Generate a description for an item"""
        descriptions = {
            "fishing_rod": "Perfect for catching rare fish in deep waters.",
            "bait": "High-quality bait that attracts valuable fish.",
            "potion": "Magical brew that enhances your abilities.",
            "upgrade": "Permanent improvement to your capabilities."
        }
        
        base_desc = descriptions.get(item["type"], "A valuable item.")
        rarity_desc = {
            "common": "Standard quality item.",
            "uncommon": "Above average quality.",
            "rare": "High quality with special properties.",
            "epic": "Exceptional item with powerful effects.",
            "legendary": "Ultra-rare item of immense power."
        }
        
        return f"{base_desc} {rarity_desc.get(item['rarity'], '')}"


class BazaarStockManager:
    """Manage bazaar stock prices and investments"""
    
    def __init__(self):
        self.base_stock_price = 100
        self.price_volatility = 0.1  # 10% volatility
        self.dividend_rate = 0.02   # 2% dividend per period
    
    async def get_current_stock_price(self, guild_id: int) -> float:
        """Get current stock price for the guild"""
        try:
            # Get stock data from database
            stock_data = await db.get_bazaar_stock_data(guild_id)
            
            if not stock_data:
                # Initialize stock for new guild
                await self._initialize_guild_stock(guild_id)
                return self.base_stock_price
            
            return stock_data.get('current_price', self.base_stock_price)
            
        except Exception:
            return self.base_stock_price
    
    async def update_stock_price(self, guild_id: int) -> float:
        """Update stock price based on market conditions"""
        try:
            current_price = await self.get_current_stock_price(guild_id)
            
            # Calculate price change based on various factors
            market_sentiment = random.uniform(-1, 1)  # Random market sentiment
            trading_volume = await self._get_trading_volume(guild_id)
            
            # More trading = more volatility
            volatility_factor = min(trading_volume / 100, 2.0)
            price_change = market_sentiment * self.price_volatility * volatility_factor
            
            new_price = max(current_price * (1 + price_change), 10)  # Min price of 10
            
            # Update in database
            await db.update_bazaar_stock_price(guild_id, new_price)
            
            return new_price
            
        except Exception:
            return self.base_stock_price
    
    async def process_dividend_payments(self, guild_id: int):
        """Process dividend payments to stock holders"""
        try:
            stock_holders = await db.get_bazaar_stock_holders(guild_id)
            current_price = await self.get_current_stock_price(guild_id)
            
            for holder in stock_holders:
                user_id = holder['user_id']
                stock_amount = holder['stock_amount']
                
                # Calculate dividend
                dividend = int(stock_amount * current_price * self.dividend_rate)
                
                if dividend > 0:
                    # Pay dividend
                    await db.add_to_wallet(user_id, guild_id, dividend)
                    await db.log_bazaar_dividend(user_id, guild_id, dividend, stock_amount)
            
        except Exception as e:
            print(f"Error processing dividends: {e}")
    
    async def _initialize_guild_stock(self, guild_id: int):
        """Initialize stock data for a new guild"""
        stock_data = {
            'guild_id': guild_id,
            'current_price': self.base_stock_price,
            'total_shares': 0,
            'created_at': datetime.now(),
            'last_updated': datetime.now()
        }
        
        await db.initialize_bazaar_stock(guild_id, stock_data)
    
    async def _get_trading_volume(self, guild_id: int) -> int:
        """Get recent trading volume for volatility calculation"""
        try:
            # Get trades from last 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            trades = await db.get_bazaar_trades_since(guild_id, cutoff_time)
            return len(trades)
        except Exception:
            return 0


class BazaarAnalytics:
    """Analytics and statistics for the bazaar system"""
    
    def __init__(self):
        pass
    
    async def get_popular_items(self, guild_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Get most popular items in the bazaar"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            purchases = await db.get_bazaar_purchases_since(guild_id, cutoff_date)
            
            item_counts = defaultdict(int)
            item_revenue = defaultdict(int)
            
            for purchase in purchases:
                item_name = purchase.get('item_name', 'Unknown')
                amount = purchase.get('amount', 1)
                price = purchase.get('price', 0)
                
                item_counts[item_name] += amount
                item_revenue[item_name] += price
            
            # Create popularity list
            popular_items = []
            for item_name, count in item_counts.items():
                popular_items.append({
                    'name': item_name,
                    'purchases': count,
                    'revenue': item_revenue[item_name],
                    'avg_price': item_revenue[item_name] / count if count > 0 else 0
                })
            
            # Sort by purchase count
            popular_items.sort(key=lambda x: x['purchases'], reverse=True)
            
            return popular_items[:10]  # Top 10
            
        except Exception:
            return []
    
    async def get_user_bazaar_stats(self, user_id: int, guild_id: int) -> Dict[str, Any]:
        """Get comprehensive bazaar statistics for a user"""
        try:
            # Get purchase history
            purchases = await db.get_user_bazaar_purchases(user_id, guild_id)
            
            # Get stock holdings
            stock_holdings = await db.get_user_bazaar_stock(user_id, guild_id)
            
            # Calculate statistics
            total_purchases = len(purchases)
            total_spent = sum(p.get('total_price', 0) for p in purchases)
            unique_items = len(set(p.get('item_name', '') for p in purchases))
            
            # Most purchased item
            item_counts = defaultdict(int)
            for purchase in purchases:
                item_counts[purchase.get('item_name', 'Unknown')] += purchase.get('amount', 1)
            
            most_purchased = max(item_counts.items(), key=lambda x: x[1]) if item_counts else ('None', 0)
            
            return {
                'total_purchases': total_purchases,
                'total_spent': total_spent,
                'unique_items': unique_items,
                'stock_holdings': stock_holdings,
                'most_purchased_item': most_purchased[0],
                'most_purchased_count': most_purchased[1],
                'average_purchase': total_spent / max(total_purchases, 1)
            }
            
        except Exception:
            return {
                'total_purchases': 0,
                'total_spent': 0,
                'unique_items': 0,
                'stock_holdings': 0,
                'most_purchased_item': 'None',
                'most_purchased_count': 0,
                'average_purchase': 0
            }
    
    async def get_guild_bazaar_overview(self, guild_id: int) -> Dict[str, Any]:
        """Get overview statistics for guild's bazaar activity"""
        try:
            # Get recent activity (last 30 days)
            cutoff_date = datetime.now() - timedelta(days=30)
            
            purchases = await db.get_bazaar_purchases_since(guild_id, cutoff_date)
            stock_trades = await db.get_bazaar_stock_trades_since(guild_id, cutoff_date)
            
            total_revenue = sum(p.get('total_price', 0) for p in purchases)
            total_items_sold = sum(p.get('amount', 1) for p in purchases)
            unique_customers = len(set(p.get('user_id') for p in purchases))
            
            return {
                'total_revenue': total_revenue,
                'total_items_sold': total_items_sold,
                'unique_customers': unique_customers,
                'stock_trades': len(stock_trades),
                'average_purchase_value': total_revenue / max(len(purchases), 1)
            }
            
        except Exception:
            return {
                'total_revenue': 0,
                'total_items_sold': 0,
                'unique_customers': 0,
                'stock_trades': 0,
                'average_purchase_value': 0
            }


def calculate_item_rarity_multiplier(rarity: str) -> float:
    """Calculate price multiplier based on item rarity"""
    multipliers = {
        "common": 1.0,
        "uncommon": 1.2,
        "rare": 1.5,
        "epic": 2.0,
        "legendary": 3.0
    }
    return multipliers.get(rarity, 1.0)


def format_currency(amount: int) -> str:
    """Format currency amount with proper separators"""
    return f"{amount:,} <:bronkbuk:1377389238290747582>"


def calculate_discount_savings(original_price: int, discounted_price: int) -> Tuple[int, float]:
    """Calculate savings amount and percentage from discount"""
    savings = original_price - discounted_price
    percentage = (savings / original_price) * 100 if original_price > 0 else 0
    return savings, percentage
