"""
Fight history data access operations.
"""

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from models import FightHistory, Player
from typing import List, Optional, Tuple
from datetime import date
import logging

logger = logging.getLogger(__name__)


async def save_fight_history(
    session: AsyncSession,
    player1_id: int,
    player2_id: int,
    winner_id: int,
    player1_od_spent: int = 0,
    player2_od_spent: int = 0,
    skills_used_json: str = "{}"
) -> FightHistory:
    """Save a completed fight to history."""
    fight = FightHistory(
        player1_id=player1_id,
        player2_id=player2_id,
        winner_id=winner_id,
        player1_od_spent=player1_od_spent,
        player2_od_spent=player2_od_spent,
        skills_used_json=skills_used_json
    )
    session.add(fight)
    await session.commit()
    await session.refresh(fight)
    return fight


async def get_player_history(session: AsyncSession, user_id: int, limit: int = 5) -> List[FightHistory]:
    """Get last N fights for a player."""
    result = await session.execute(
        select(FightHistory).where(
            (FightHistory.player1_id == user_id) | (FightHistory.player2_id == user_id)
        ).order_by(FightHistory.id.desc()).limit(limit)
    )
    return result.scalars().all()


async def get_rating(session: AsyncSession, limit: int = 10) -> List[Tuple[Player, int]]:
    """Get top players by wins."""
    result = await session.execute(
        select(Player).order_by(Player.wins.desc()).limit(limit)
    )
    players = result.scalars().all()
    return [(player, player.wins) for player in players]
