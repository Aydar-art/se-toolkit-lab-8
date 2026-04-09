"""
Skill data access operations.
"""

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Skill, PlayerSkill, SkillProgress
from typing import List, Optional
from datetime import date
import logging

logger = logging.getLogger(__name__)


async def get_all_skills(session: AsyncSession) -> List[Skill]:
    """Get all available skills."""
    result = await session.execute(select(Skill).order_by(Skill.id))
    return result.scalars().all()


async def get_skill(session: AsyncSession, skill_id: int) -> Optional[Skill]:
    """Get skill by ID."""
    result = await session.execute(select(Skill).where(Skill.id == skill_id))
    return result.scalar_one_or_none()


async def get_player_skills(session: AsyncSession, user_id: int) -> List[Skill]:
    """Get all skills unlocked for a player."""
    result = await session.execute(
        select(Skill).join(PlayerSkill, Skill.id == PlayerSkill.skill_id)
        .where(PlayerSkill.user_id == user_id)
        .order_by(Skill.id)
    )
    return result.scalars().all()


async def has_skill(session: AsyncSession, user_id: int, skill_id: int) -> bool:
    """Check if player has a specific skill unlocked."""
    result = await session.execute(
        select(PlayerSkill).where(
            PlayerSkill.user_id == user_id,
            PlayerSkill.skill_id == skill_id
        )
    )
    return result.scalar_one_or_none() is not None


async def unlock_skill(session: AsyncSession, user_id: int, skill_id: int) -> PlayerSkill:
    """Unlock a skill for a player."""
    player_skill = PlayerSkill(user_id=user_id, skill_id=skill_id)
    session.add(player_skill)
    await session.commit()
    await session.refresh(player_skill)
    return player_skill


async def get_skill_progress(session: AsyncSession, user_id: int, skill_id: int) -> Optional[SkillProgress]:
    """Get current progress for a skill."""
    result = await session.execute(
        select(SkillProgress).where(
            SkillProgress.user_id == user_id,
            SkillProgress.skill_id == skill_id
        )
    )
    return result.scalar_one_or_none()


async def update_skill_progress(session: AsyncSession, user_id: int, skill_id: int, 
                                 target_steps: int, increment: int = 1) -> SkillProgress:
    """Update progress for a skill. Creates if doesn't exist."""
    progress = await get_skill_progress(session, user_id, skill_id)
    
    if progress is None:
        progress = SkillProgress(
            user_id=user_id,
            skill_id=skill_id,
            current_step=increment,
            target_steps=target_steps
        )
        session.add(progress)
    else:
        progress.current_step = min(progress.current_step + increment, target_steps)
        session.add(progress)
    
    await session.commit()
    await session.refresh(progress)
    return progress


async def get_all_skill_progress(session: AsyncSession, user_id: int) -> List[SkillProgress]:
    """Get all skill progress for a player."""
    result = await session.execute(
        select(SkillProgress).where(SkillProgress.user_id == user_id)
    )
    return result.scalars().all()
