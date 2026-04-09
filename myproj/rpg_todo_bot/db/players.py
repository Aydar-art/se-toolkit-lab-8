"""
Player data access operations.
Following the pattern from backend/db/learners.py
"""

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Player
from typing import Optional
from datetime import date
import logging

logger = logging.getLogger(__name__)


async def create_player(session: AsyncSession, user_id: int, username: Optional[str] = None) -> Player:
    """Create a new player."""
    player = Player(user_id=user_id, username=username)
    session.add(player)
    await session.commit()
    await session.refresh(player)
    return player


async def get_player(session: AsyncSession, user_id: int) -> Optional[Player]:
    """Get player by user_id."""
    result = await session.execute(select(Player).where(Player.user_id == user_id))
    return result.scalar_one_or_none()


async def update_player(session: AsyncSession, player: Player) -> Player:
    """Update player data."""
    session.add(player)
    await session.commit()
    await session.refresh(player)
    return player


async def reset_daily_od(session: AsyncSession):
    """Reset OD for all players (daily reset)."""
    from sqlalchemy import update as sql_update

    stmt = sql_update(Player).values(od_today=0, od_current=0, last_reset_date=date.today())
    await session.execute(stmt)
    await session.commit()
    logger.info("Daily OD reset completed for all players")
