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
        user_data = await db.execute_fetchone(
            "SELECT job, boss_hostile, boss_loyalty, last_work, last_raise FROM users WHERE id = ?",
            (user_id,)
        )
        if user_data and user_data['job']:
            return {
                'job_id': user_data['job'],
                'job_info': JOBS.get(user_data['job']),
                'boss_hostile': user_data['boss_hostile'] or 0,
                'boss_loyalty': user_data['boss_loyalty'] or 0,
                'last_work': user_data['last_work'],
                'last_raise': user_data['last_raise']
            }
        return None
    except Exception:
        return None

async def set_user_job(user_id: int, job_id: str) -> bool:
    """Set user's job"""
    try:
        await db.execute(
            "UPDATE users SET job = ?, boss_hostile = 0, boss_loyalty = 0 WHERE id = ?",
            (job_id, user_id)
        )
        await db.commit()
        return True
    except Exception:
        return False

async def remove_user_job(user_id: int) -> bool:
    """Remove user's job"""
    try:
        await db.execute(
            "UPDATE users SET job = NULL, boss_hostile = 0, boss_loyalty = 0 WHERE id = ?",
            (user_id,)
        )
        await db.commit()
        return True
    except Exception:
        return False

async def update_boss_relationship(user_id: int, hostile_change: int = 0, loyalty_change: int = 0) -> bool:
    """Update boss relationship values"""
    try:
        current_data = await get_user_job(user_id)
        if not current_data:
            return False
        
        new_hostile = max(0, min(BOSS_HOSTILE_MAX, current_data['boss_hostile'] + hostile_change))
        new_loyalty = max(0, min(BOSS_LOYALTY_MAX, current_data['boss_loyalty'] + loyalty_change))
        
        await db.execute(
            "UPDATE users SET boss_hostile = ?, boss_loyalty = ? WHERE id = ?",
            (new_hostile, new_loyalty, user_id)
        )
        await db.commit()
        return True
    except Exception:
        return False

async def update_work_timestamp(user_id: int) -> bool:
    """Update last work timestamp"""
    try:
        await db.execute(
            "UPDATE users SET last_work = ? WHERE id = ?",
            (int(time.time()), user_id)
        )
        await db.commit()
        return True
    except Exception:
        return False

async def update_raise_timestamp(user_id: int) -> bool:
    """Update last raise timestamp"""
    try:
        await db.execute(
            "UPDATE users SET last_raise = ? WHERE id = ?",
            (int(time.time()), user_id)
        )
        await db.commit()
        return True
    except Exception:
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
        coworkers = await db.execute_fetchall(
            "SELECT id, username FROM users WHERE job = ? AND id != ? ORDER BY RANDOM() LIMIT ?",
            (job_id, user_id, limit)
        )
        return coworkers or []
    except Exception:
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
