"""
Trade Offer class and related functionality
"""
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from .constants import TRADE_TIMEOUT, RISK_THRESHOLDS, BALANCE_TOLERANCE

class ModernTradeOffer:
    """Enhanced trade offer with better features and validation"""
    
    def __init__(self, initiator_id: int, target_id: int, guild_id: int):
        self.initiator_id = initiator_id
        self.target_id = target_id
        self.guild_id = guild_id
        
        # Trade contents
        self.initiator_items = []
        self.initiator_currency = 0
        self.target_items = []
        self.target_currency = 0
        
        # Trade metadata
        self.status = "drafting"  # drafting, pending, confirmed, completed, cancelled, expired
        self.created_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(minutes=TRADE_TIMEOUT)
        self.trade_id = self._generate_trade_id()
        
        # Enhanced features
        self.notes = {"initiator": "", "target": ""}  # Trade notes
        self.locked = {"initiator": False, "target": False}  # Lock offer to prevent changes
        self.auto_accept = {"initiator": False, "target": False}  # Auto-accept balanced trades
        self.private = False  # Private trade (not shown in listings)
        
        # Risk assessment
        self.risk_level = "unknown"  # low, medium, high, extreme
        self.warnings = []
        
    def _generate_trade_id(self) -> str:
        """Generate unique trade ID with timestamp"""
        data = f"{self.initiator_id}{self.target_id}{self.created_at.timestamp()}"
        return f"T{hashlib.md5(data.encode()).hexdigest()[:6].upper()}"
    
    def is_expired(self) -> bool:
        """Check if trade has expired"""
        return datetime.now() > self.expires_at
    
    def extend_expiry(self, minutes: int = 15):
        """Extend trade expiry time"""
        self.expires_at = datetime.now() + timedelta(minutes=minutes)
    
    def get_total_value(self, side: str) -> int:
        """Calculate total value with enhanced item evaluation"""
        if side == "initiator":
            item_value = sum(item.get('market_value', item.get('value', 0)) for item in self.initiator_items)
            return item_value + self.initiator_currency
        else:
            item_value = sum(item.get('market_value', item.get('value', 0)) for item in self.target_items)
            return item_value + self.target_currency
    
    def calculate_balance_ratio(self) -> float:
        """Calculate the balance ratio between both sides"""
        initiator_value = self.get_total_value("initiator")
        target_value = self.get_total_value("target")
        
        if initiator_value == 0 and target_value == 0:
            return 1.0
        
        if initiator_value == 0 or target_value == 0:
            return 0.0
        
        return min(initiator_value, target_value) / max(initiator_value, target_value)
    
    def is_balanced(self, tolerance: float = BALANCE_TOLERANCE) -> bool:
        """Check if trade is reasonably balanced"""
        return self.calculate_balance_ratio() >= (1.0 - tolerance)
    
    def assess_risk(self) -> str:
        """Assess trade risk level"""
        balance_ratio = self.calculate_balance_ratio()
        initiator_value = self.get_total_value("initiator")
        target_value = self.get_total_value("target")
        max_value = max(initiator_value, target_value)
        
        # Clear warnings
        self.warnings = []
        
        # Check balance
        if balance_ratio < RISK_THRESHOLDS["extreme"]:
            self.warnings.append("⚠️ Highly unbalanced trade")
            risk = "extreme"
        elif balance_ratio < RISK_THRESHOLDS["high"]:
            self.warnings.append("⚠️ Unbalanced trade")
            risk = "high"
        elif balance_ratio < RISK_THRESHOLDS["medium"]:
            risk = "medium"
        else:
            risk = "low"
        
        # Check for high value trades
        if max_value > 1000000:  # 1M+ value
            if risk == "low":
                risk = "medium"
            elif risk == "medium":
                risk = "high"
            self.warnings.append("💰 High value trade")
        
        # Check for suspicious patterns
        if len(self.initiator_items) + len(self.target_items) > 15:
            self.warnings.append("📦 Many items involved")
        
        self.risk_level = risk
        return risk
    
    def add_item(self, side: str, item: Dict) -> bool:
        """Add item to trade side"""
        if side == "initiator":
            if len(self.initiator_items) >= 20:  # Max items limit
                return False
            self.initiator_items.append(item)
        else:
            if len(self.target_items) >= 20:
                return False
            self.target_items.append(item)
        return True
    
    def remove_item(self, side: str, item_index: int) -> bool:
        """Remove item from trade side"""
        try:
            if side == "initiator":
                self.initiator_items.pop(item_index)
            else:
                self.target_items.pop(item_index)
            return True
        except IndexError:
            return False
    
    def set_currency(self, side: str, amount: int) -> bool:
        """Set currency amount for trade side"""
        if amount < 0:
            return False
        
        if side == "initiator":
            self.initiator_currency = amount
        else:
            self.target_currency = amount
        return True
    
    def lock_side(self, side: str, locked: bool = True):
        """Lock/unlock a side of the trade"""
        self.locked[side] = locked
    
    def is_side_locked(self, side: str) -> bool:
        """Check if a side is locked"""
        return self.locked.get(side, False)
    
    def can_be_confirmed(self) -> Tuple[bool, str]:
        """Check if trade can be confirmed"""
        if self.is_expired():
            return False, "Trade has expired"
        
        if self.status != "pending":
            return False, "Trade is not in pending status"
        
        # Check if both sides have something
        initiator_has_items = len(self.initiator_items) > 0 or self.initiator_currency > 0
        target_has_items = len(self.target_items) > 0 or self.target_currency > 0
        
        if not (initiator_has_items and target_has_items):
            return False, "Both sides must offer something"
        
        return True, "Trade can be confirmed"
    
    def to_dict(self) -> Dict:
        """Convert trade offer to dictionary for storage"""
        return {
            "trade_id": self.trade_id,
            "initiator_id": self.initiator_id,
            "target_id": self.target_id,
            "guild_id": self.guild_id,
            "initiator_items": self.initiator_items,
            "initiator_currency": self.initiator_currency,
            "target_items": self.target_items,
            "target_currency": self.target_currency,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "notes": self.notes,
            "locked": self.locked,
            "auto_accept": self.auto_accept,
            "private": self.private,
            "risk_level": self.risk_level,
            "warnings": self.warnings
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModernTradeOffer':
        """Create trade offer from dictionary"""
        trade = cls(data["initiator_id"], data["target_id"], data["guild_id"])
        trade.trade_id = data["trade_id"]
        trade.initiator_items = data["initiator_items"]
        trade.initiator_currency = data["initiator_currency"]
        trade.target_items = data["target_items"]
        trade.target_currency = data["target_currency"]
        trade.status = data["status"]
        trade.created_at = datetime.fromisoformat(data["created_at"])
        trade.expires_at = datetime.fromisoformat(data["expires_at"])
        trade.notes = data.get("notes", {"initiator": "", "target": ""})
        trade.locked = data.get("locked", {"initiator": False, "target": False})
        trade.auto_accept = data.get("auto_accept", {"initiator": False, "target": False})
        trade.private = data.get("private", False)
        trade.risk_level = data.get("risk_level", "unknown")
        trade.warnings = data.get("warnings", [])
        return trade

class TradeStats:
    """Track trading statistics for users"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.total_trades = 0
        self.successful_trades = 0
        self.cancelled_trades = 0
        self.total_value_traded = 0
        self.reputation_score = 100  # Start at 100
        self.trade_history = []
        
    def add_completed_trade(self, trade_value: int):
        """Add a completed trade to stats"""
        self.total_trades += 1
        self.successful_trades += 1
        self.total_value_traded += trade_value
        self.reputation_score = min(200, self.reputation_score + 1)
        
    def add_cancelled_trade(self):
        """Add a cancelled trade to stats"""
        self.total_trades += 1
        self.cancelled_trades += 1
        self.reputation_score = max(0, self.reputation_score - 2)
        
    def get_success_rate(self) -> float:
        """Get trade success rate as percentage"""
        if self.total_trades == 0:
            return 100.0
        return (self.successful_trades / self.total_trades) * 100
    
    def get_reputation_level(self) -> str:
        """Get reputation level based on score"""
        if self.reputation_score >= 150:
            return "Excellent"
        elif self.reputation_score >= 120:
            return "Good"
        elif self.reputation_score >= 100:
            return "Average"
        elif self.reputation_score >= 80:
            return "Poor"
        else:
            return "Terrible"
