"""
Guild data access operations.
"""

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Guild, Player
from typing import Optional, List
from datetime import date
import logging

logger = logging.getLogger(__name__)


async def create_guild(session: AsyncSession, name: str, owner_id: int, description: Optional[str] = None) -> Guild:
    """Create a new guild."""
    guild = Guild(name=name, owner_id=owner_id, description=description)
    session.add(guild)
    await session.commit()
    await session.refresh(guild)
    return guild


async def get_guild_by_name(session: AsyncSession, name: str) -> Optional[Guild]:
    """Get guild by name."""
    result = await session.execute(select(Guild).where(Guild.name == name))
    return result.scalar_one_or_none()


async def get_guild_by_id(session: AsyncSession, guild_id: int) -> Optional[Guild]:
    """Get guild by ID."""
    result = await session.execute(select(Guild).where(Guild.id == guild_id))
    return result.scalar_one_or_none()


async def get_guild_members(session: AsyncSession, guild_id: int) -> List[Player]:
    """Get all players in a guild."""
    result = await session.execute(
        select(Player).where(Player.guild_id == guild_id).order_by(Player.level.desc())
    )
    return result.scalars().all()


async def get_guild_member_count(session: AsyncSession, guild_id: int) -> int:
    """Get number of members in a guild."""
    result = await session.execute(
        select(Player.user_id).where(Player.guild_id == guild_id)
    )
    return len(result.scalars().all())


async def join_guild(session: AsyncSession, user_id: int, guild_id: int) -> Player:
    """Add a player to a guild."""
    result = await session.execute(select(Player).where(Player.user_id == user_id))
    player = result.scalar_one()
    player.guild_id = guild_id
    session.add(player)
    await session.commit()
    await session.refresh(player)
    return player


async def leave_guild(session: AsyncSession, user_id: int) -> Player:
    """Remove a player from their guild."""
    result = await session.execute(select(Player).where(Player.user_id == user_id))
    player = result.scalar_one()
    player.guild_id = None
    session.add(player)
    await session.commit()
    await session.refresh(player)
    return player


async def get_player_guild(session: AsyncSession, user_id: int) -> Optional[Guild]:
    """Get the guild a player belongs to."""
    result = await session.execute(select(Player).where(Player.user_id == user_id))
    player = result.scalar_one_or_none()
    if player and player.guild_id:
        return await get_guild_by_id(session, player.guild_id)
    return None


async def get_guild_stats(session: AsyncSession, guild_id: int) -> dict:
    """Get combined statistics for a guild."""
    members = await get_guild_members(session, guild_id)
    if not members:
        return {}

    total_level = sum(m.level for m in members)
    total_xp = sum(m.xp for m in members)
    total_wins = sum(m.wins for m in members)
    avg_level = total_level / len(members)

    return {
        "member_count": len(members),
        "total_level": total_level,
        "total_xp": total_xp,
        "total_wins": total_wins,
        "avg_level": round(avg_level, 1),
        "highest_level_player": max(members, key=lambda m: m.level),
        "most_wins_player": max(members, key=lambda m: m.wins),
    }
