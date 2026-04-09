"""
Database models for the RPG To-Do Bot.
Following SQLModel pattern from backend/models/
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date


class Player(SQLModel, table=True):
    """Player model representing a Telegram user in the RPG game."""

    __tablename__ = "players"

    user_id: int = Field(primary_key=True)
    username: Optional[str] = Field(default=None)
    level: int = Field(default=1)
    xp: int = Field(default=0)
    hp: int = Field(default=25)
    max_hp: int = Field(default=25)
    od_today: int = Field(default=0)  # Total OD earned today (for daily limit tracking)
    od_current: int = Field(default=0)  # Available OD right now (for spending in fights)
    wins: int = Field(default=0)
    last_reset_date: Optional[date] = Field(default=None)
    guild_id: Optional[int] = Field(default=None, foreign_key="guilds.id")


class Guild(SQLModel, table=True):
    """Guild model representing a group of players."""

    __tablename__ = "guilds"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    owner_id: int = Field(foreign_key="players.user_id")
    created_date: date = Field(default_factory=date.today)
    description: Optional[str] = Field(default=None, max_length=200)


class Task(SQLModel, table=True):
    """Task model representing a to-do item."""

    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="players.user_id")
    name: str
    od: int
    completed: bool = Field(default=False)
    created_date: date = Field(default_factory=date.today)


class Skill(SQLModel, table=True):
    """Skill model representing available combat skills."""

    __tablename__ = "skills"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    od_cost: int
    effect_type: str  # "damage", "defense", "heal"
    effect_value: int
    unlock_condition: str  # JSON string describing unlock condition


class PlayerSkill(SQLModel, table=True):
    """Tracks which skills are unlocked for each player."""

    __tablename__ = "player_skills"

    user_id: int = Field(primary_key=True, foreign_key="players.user_id")
    skill_id: int = Field(primary_key=True, foreign_key="skills.id")
    unlocked_at: date = Field(default_factory=date.today)


class SkillProgress(SQLModel, table=True):
    """Tracks progress towards unlocking skills."""

    __tablename__ = "skill_progress"

    user_id: int = Field(primary_key=True, foreign_key="players.user_id")
    skill_id: int = Field(primary_key=True, foreign_key="skills.id")
    current_step: int = Field(default=0)
    target_steps: int = Field(default=0)


class FightHistory(SQLModel, table=True):
    """Records of completed fights."""

    __tablename__ = "fight_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    player1_id: int = Field(foreign_key="players.user_id")
    player2_id: int = Field(foreign_key="players.user_id")
    winner_id: int = Field(foreign_key="players.user_id")
    player1_od_spent: int = Field(default=0)
    player2_od_spent: int = Field(default=0)
    skills_used_json: str = Field(default="{}")  # JSON string
    fight_date: date = Field(default_factory=date.today)
