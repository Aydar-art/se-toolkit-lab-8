"""
Handlers for /start, /help commands.
Following the router pattern from backend/routers/
"""

from aiogram import Router, types
from aiogram.filters import Command
from database import async_session_maker
from db import create_player, get_player
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handle /start command - register player if not exists."""
    user_id = message.from_user.id
    username = message.from_user.username
    
    async with async_session_maker() as session:
        # Try to register the player
        player = await get_player(session, user_id)
        if player is None:
            player = await create_player(session, user_id, username)
            await message.answer(
                f"🎮 Добро пожаловать в RPG To-Do Bot, {message.from_user.first_name}!\n\n"
                f"Вы зарегистрированы как новый игрок.\n"
                f"Уровень: {player.level} | XP: {player.xp} | HP: {player.hp}\n\n"
                f"Используйте /help чтобы узнать доступные команды."
            )
            logger.info(f"New player registered: {user_id}")
        else:
            await message.answer(
                f"👋 С возвращением, {message.from_user.first_name}!\n\n"
                f"Уровень: {player.level} | XP: {player.xp} | HP: {player.hp}\n"
                f"Используйте /help чтобы узнать доступные команды."
            )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Handle /help command - show available commands."""
    help_text = """
📜 **Доступные команды:**

/start - Начать работу / Регистрация
/profile - Просмотр профиля и статистики
/tasks - Список ваших задач
/add_task - Добавить новую задачу
/complete - Выполнить задачу
/skills - Просмотр навыков и прогресса
/fight @username - Вызвать игрока на PvP дуэль
/accept - Принять вызов (для тестирования)
/history - История последних 5 боёв
/rating - Таблица лидеров (топ-10)
/help - Показать это сообщение

**Как играть:**
1. Добавляйте задачи через /add_task
2. Выполняйте их через /complete чтобы получать XP
3. Накапливайте ОД (очки действий) за выполнение задач
4. Открывайте новые навыки, выполняя задачи
5. Сражайтесь с другими игроками в /fight!

**Навыки:**
• Выполняйте задачи чтобы открывать новые навыки
• /skills покажет ваши открытые навыки и прогресс
• Перед боем вы выбираете до 3 навыков

**Бой:**
• Используйте inline-кнопки для выбора действий
• ⚔️ Атака (1 ОД) - базовая атака
• 💥 Навыки - специальные умения
• 🛡️ Защита (0 ОД) - снижает урон на 50%
"""
    await message.answer(help_text)
