"""
Database connection and session management.
Following the pattern from backend/database.py with async support.
"""

import sqlite3
import logging
from sqlmodel import SQLModel, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import OperationalError
from config import settings
from models import Skill


logger = logging.getLogger(__name__)

# Database URL for async SQLite
DATABASE_URL = f"sqlite+aiosqlite:///{settings.db_name}"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Initialize database tables and run migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # Run upgrades
    await upgrade_db()


async def upgrade_db():
    """Upgrade database schema and seed initial data."""
    async with async_session_maker() as session:
        # Add wins column to players if it doesn't exist
        try:
            await session.execute(text("ALTER TABLE players ADD COLUMN wins INTEGER DEFAULT 0"))
            await session.commit()
            logger.info("Added wins column to players table")
        except OperationalError as e:
            if "duplicate column name" in str(e).lower():
                logger.info("wins column already exists")
                await session.rollback()
            else:
                logger.warning(f"Error adding wins column: {e}")
                await session.rollback()

        # Add od_current column to players if it doesn't exist
        try:
            await session.execute(text("ALTER TABLE players ADD COLUMN od_current INTEGER DEFAULT 0"))
            await session.commit()
            logger.info("Added od_current column to players table")
        except OperationalError as e:
            if "duplicate column name" in str(e).lower():
                logger.info("od_current column already exists")
                await session.rollback()
            else:
                logger.warning(f"Error adding od_current column: {e}")
                await session.rollback()

        # Add guild_id column to players if it doesn't exist
        try:
            await session.execute(text("ALTER TABLE players ADD COLUMN guild_id INTEGER"))
            await session.commit()
            logger.info("Added guild_id column to players table")
        except OperationalError as e:
            if "duplicate column name" in str(e).lower():
                logger.info("guild_id column already exists")
                await session.rollback()
            else:
                logger.warning(f"Error adding guild_id column: {e}")
                await session.rollback()

        # Create guilds table if it doesn't exist
        try:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS guilds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    owner_id INTEGER NOT NULL,
                    created_date TEXT NOT NULL,
                    description TEXT,
                    FOREIGN KEY (owner_id) REFERENCES players(user_id)
                )
            """))
            await session.commit()
            logger.info("Created guilds table")
        except OperationalError as e:
            logger.warning(f"Error creating guilds table: {e}")
            await session.rollback()
        
        # Seed default skills if not exists
        default_skills = [
            Skill(
                id=1,
                name="Базовая атака",
                description="Обычная атака",
                od_cost=1,
                effect_type="damage",
                effect_value=5,
                unlock_condition='{"type": "always"}'
            ),
            Skill(
                id=2,
                name="Сильный удар",
                description="Мощная атака, стоит 3 ОД",
                od_cost=3,
                effect_type="damage",
                effect_value=10,
                unlock_condition='{"type": "tasks_completed", "count": 3}'
            ),
            Skill(
                id=3,
                name="Защита",
                description="Снижает следующий получаемый урон на 50%",
                od_cost=2,
                effect_type="defense",
                effect_value=50,
                unlock_condition='{"type": "low_od_tasks", "count": 5}'
            ),
            Skill(
                id=4,
                name="Восстановление",
                description="Восстанавливает 8 HP",
                od_cost=4,
                effect_type="heal",
                effect_value=8,
                unlock_condition='{"type": "high_od_tasks", "count": 3}'
            ),
            # Hard-to-get skills (level and win based)
            Skill(
                id=5,
                name="Критический удар",
                description="Шанс 30% нанести двойной урон (14)",
                od_cost=3,
                effect_type="crit_damage",
                effect_value=14,
                unlock_condition='{"type": "level", "level": 5}'
            ),
            Skill(
                id=6,
                name="Щит титана",
                description="Полностью блокирует следующую атаку",
                od_cost=5,
                effect_type="full_block",
                effect_value=0,
                unlock_condition='{"type": "level", "level": 10}'
            ),
            Skill(
                id=7,
                name="Вампиризм",
                description="Наносит 8 урона и восстанавливает 4 HP",
                od_cost=4,
                effect_type="drain",
                effect_value=8,
                unlock_condition='{"type": "wins", "count": 10}'
            ),
            Skill(
                id=8,
                name="Мегаудар",
                description="Разрушительная атака: 20 урона",
                od_cost=6,
                effect_type="damage",
                effect_value=20,
                unlock_condition='{"type": "level", "level": 20}'
            ),
            Skill(
                id=9,
                name="Ярость берсерка",
                description="Чем меньше HP, тем больше урон (до x3)",
                od_cost=4,
                effect_type="berserk",
                effect_value=10,
                unlock_condition='{"type": "wins", "count": 25}'
            ),
            Skill(
                id=10,
                name="Феникс",
                description="Один раз за бой выживаете с 1 HP при смертельном ударе",
                od_cost=0,
                effect_type="phoenix",
                effect_value=1,
                unlock_condition='{"type": "level", "level": 50}'
            )
        ]
        
        for skill in default_skills:
            result = await session.execute(text(f"SELECT id FROM skills WHERE id = {skill.id}"))
            if not result.scalar_one_or_none():
                session.add(skill)
        
        await session.commit()
        logger.info("Database upgrade completed")


async def get_session():
    """Get database session (for dependency injection pattern)."""
    async with async_session_maker() as session:
        yield session
