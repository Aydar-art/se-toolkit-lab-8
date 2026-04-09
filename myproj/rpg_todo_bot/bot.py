"""
Main entry point for the RPG To-Do Telegram Bot.
Following the pattern from backend/main.py and backend/run.py
"""

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import MenuButtonDefault, BotCommand

from config import settings
from database import init_db, async_session_maker
from db import reset_daily_od

# Import handlers
from handlers import start, profile, tasks, fight, guild

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def daily_reset():
    """Background task to reset daily OD at midnight UTC."""
    while True:
        now = datetime.utcnow()
        midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        seconds_to_sleep = (midnight - now).total_seconds()
        
        logger.info(f"Next daily OD reset in {seconds_to_sleep/3600:.2f} hours")
        await asyncio.sleep(seconds_to_sleep)
        
        try:
            async with async_session_maker() as session:
                await reset_daily_od(session)
                logger.info("Daily OD reset completed")
        except Exception as e:
            logger.error(f"Error during daily reset: {e}")


async def main():
    """Main function to start the bot."""
    logger.info("Starting RPG To-Do Bot...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Create bot and dispatcher
    bot = Bot(token=settings.bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Set up bot menu commands
    commands = [
        BotCommand(command="start", description="🎮 Регистрация / Начало"),
        BotCommand(command="profile", description="👤 Профиль и статистика"),
        BotCommand(command="add_task", description="➕ Добавить задачу"),
        BotCommand(command="tasks", description="📋 Мои задачи"),
        BotCommand(command="complete", description="✅ Выполнить задачу"),
        BotCommand(command="skills", description="🎯 Навыки и прогресс"),
        BotCommand(command="fight", description="⚔️ Вызвать на дуэль"),
        BotCommand(command="accept", description="🤝 Принять вызов"),
        BotCommand(command="history", description="📜 История боёв"),
        BotCommand(command="rating", description="🏆 Таблица лидеров"),
        BotCommand(command="create_guild", description="🏰 Создать гильдию"),
        BotCommand(command="join_guild", description="🤝 Вступить в гильдию"),
        BotCommand(command="guild", description="📊 Информация о гильдии"),
        BotCommand(command="guild_stats", description="🏆 Статистика гильдии"),
        BotCommand(command="leave_guild", description="👋 Покинуть гильдию"),
        BotCommand(command="help", description="📜 Помощь"),
    ]
    await bot.set_my_commands(commands)

    # Register routers (following backend router pattern)
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(tasks.router)
    dp.include_router(fight.router)
    dp.include_router(guild.router)
    
    # Start daily reset background task
    asyncio.create_task(daily_reset())
    
    # Start polling
    logger.info("Bot started and polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot stopped: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
