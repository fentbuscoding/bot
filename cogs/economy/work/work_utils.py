"""
Utility functions for the Work system
"""
import random
import time
from typing import Dict, Any, Optional, Tuple
from .constants import JOBS, CURRENCY, BOSS_HOSTILE_MAX, BOSS_LOYALTY_MAX
from .constants import HOSTILE_WAGE_PENALTY, LOYALTY_WAGE_BONUS
from utils.db import db

async def get_user_job(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user's current job information"""
    try:
        if not await db.ensure_connected():
            return None
        
        user_data = await db.db.users.find_one({"_id": str(user_id)})
        if user_data and user_data.get('job'):
            return {
                'job_id': user_data['job'],
                'job_info': JOBS.get(user_data['job']),
                'boss_hostile': user_data.get('boss_hostile', 0),
                'boss_loyalty': user_data.get('boss_loyalty', 0),
                'last_work': user_data.get('last_work'),
                'last_raise': user_data.get('last_raise')
            }
        return None
    except Exception as e:
        print(f"Error getting user job for {user_id}: {e}")
        return None

async def set_user_job(user_id: int, job_id: str) -> bool:
    """Set user's job"""
    try:
        if not await db.ensure_connected():
            return False
        
        result = await db.db.users.update_one(
            {"_id": str(user_id)},
            {"$set": {
                "job": job_id,
                "boss_hostile": 0,
                "boss_loyalty": 0
            }},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        print(f"Error setting user job for {user_id}: {e}")
        return False

async def remove_user_job(user_id: int) -> bool:
    """Remove user's job"""
    try:
        if not await db.ensure_connected():
            return False
        
        result = await db.db.users.update_one(
            {"_id": str(user_id)},
            {"$unset": {"job": ""},
             "$set": {
                "boss_hostile": 0,
                "boss_loyalty": 0
             }}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error removing user job for {user_id}: {e}")
        return False

async def update_boss_relationship(user_id: int, hostile_change: int = 0, loyalty_change: int = 0) -> bool:
    """Update boss relationship values"""
    try:
        if not await db.ensure_connected():
            return False
        
        current_data = await get_user_job(user_id)
        if not current_data:
            return False
        
        new_hostile = max(0, min(BOSS_HOSTILE_MAX, current_data['boss_hostile'] + hostile_change))
        new_loyalty = max(0, min(BOSS_LOYALTY_MAX, current_data['boss_loyalty'] + loyalty_change))
        
        result = await db.db.users.update_one(
            {"_id": str(user_id)},
            {"$set": {
                "boss_hostile": new_hostile,
                "boss_loyalty": new_loyalty
            }}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating boss relationship for {user_id}: {e}")
        return False

async def update_work_timestamp(user_id: int) -> bool:
    """Update last work timestamp"""
    try:
        if not await db.ensure_connected():
            return False
        
        result = await db.db.users.update_one(
            {"_id": str(user_id)},
            {"$set": {"last_work": int(time.time())}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        print(f"Error updating work timestamp for {user_id}: {e}")
        return False

async def update_raise_timestamp(user_id: int) -> bool:
    """Update last raise timestamp"""
    try:
        if not await db.ensure_connected():
            return False
        
        result = await db.db.users.update_one(
            {"_id": str(user_id)},
            {"$set": {"last_raise": int(time.time())}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        print(f"Error updating raise timestamp for {user_id}: {e}")
        return False

def calculate_wage(job_info: Dict[str, Any], boss_hostile: int, boss_loyalty: int) -> int:
    """Calculate wage based on job and boss relationship"""
    base_wage = random.randint(job_info['wage']['min'], job_info['wage']['max'])
    
    # Apply boss relationship modifiers
    hostile_penalty = (boss_hostile / BOSS_HOSTILE_MAX) * HOSTILE_WAGE_PENALTY
    loyalty_bonus = (boss_loyalty / BOSS_LOYALTY_MAX) * LOYALTY_WAGE_BONUS
    
    multiplier = 1.0 - hostile_penalty + loyalty_bonus
    final_wage = int(base_wage * multiplier)
    
    return max(1, final_wage)  # Ensure minimum wage of 1

def get_job_display_name(job_id: str) -> str:
    """Get display name for a job"""
    job_info = JOBS.get(job_id)
    if job_info:
        return f"{job_info['emoji']} {job_info['name']}"
    return "Unknown Job"

def get_boss_relationship_status(hostile: int, loyalty: int) -> Tuple[str, str]:
    """Get boss relationship status description and emoji"""
    if hostile > 70:
        return "Absolutely despises you", "😡"
    elif hostile > 40:
        return "Dislikes you", "😠"
    elif hostile > 20:
        return "Annoyed with you", "😒"
    elif loyalty > 70:
        return "Absolutely loves you", "🥰"
    elif loyalty > 40:
        return "Likes you", "😊"
    elif loyalty > 20:
        return "Appreciates you", "🙂"
    else:
        return "Neutral towards you", "😐"

async def get_coworkers(user_id: int, job_id: str, limit: int = 10) -> list:
    """Get list of coworkers with the same job"""
    try:
        if not await db.ensure_connected():
            return []
        
        # Find users with the same job excluding the current user
        cursor = db.db.users.find(
            {"job": job_id, "_id": {"$ne": str(user_id)}}
        ).limit(limit)
        
        coworkers = []
        async for user in cursor:
            coworkers.append({
                "id": user["_id"],
                "username": user.get("username", f"User {user['_id']}")
            })
        
        return coworkers
    except Exception as e:
        print(f"Error getting coworkers for {user_id}: {e}")
        return []

def format_currency(amount: int) -> str:
    """Format currency amount with emoji"""
    return f"{amount:,} {CURRENCY}"

def get_job_list_embed_description() -> str:
    """Get formatted job list for embed description"""
    description = "**Available Jobs:**\n\n"
    for job_id, job_info in JOBS.items():
        wage_range = f"{job_info['wage']['min']:,} - {job_info['wage']['max']:,}"
        description += f"{job_info['emoji']} **{job_info['name']}**\n"
        description += f"💰 Wage: {wage_range} {CURRENCY}\n"
        description += f"📝 {job_info['description']}\n\n"
    return description

def is_valid_job_id(job_id: str) -> bool:
    """Check if job ID is valid"""
    return job_id in JOBS
