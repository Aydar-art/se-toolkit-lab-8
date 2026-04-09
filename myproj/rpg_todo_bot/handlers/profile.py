"""
Handler for /profile command.
Following the router pattern from backend/routers/
"""

from aiogram import Router, types
from aiogram.filters import Command
from database import async_session_maker
from db import get_player
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Handle /profile command - show player statistics."""
    user_id = message.from_user.id

    async with async_session_maker() as session:
        player = await get_player(session, user_id)

        if player is None:
            await message.answer(
                "❌ Вы ещё не зарегистрированы. Используйте /start для регистрации."
            )
            return

        # Calculate XP needed for next level
        xp_for_next_level = player.level * 100
        xp_progress = min(player.xp / xp_for_next_level, 1.0) if xp_for_next_level > 0 else 0

        # Visual progress bar (10 blocks)
        filled = int(xp_progress * 10)
        empty = 10 - filled
        bar = "█" * filled + "░" * empty
        pct = int(xp_progress * 100)

        profile_text = f"""
🎭 **Профиль игрока**

👤 **Имя:** {message.from_user.first_name}
🏆 **Уровень:** {player.level}
⭐ **XP:** {player.xp}/{xp_for_next_level}
❤️ **HP:** {player.hp}/{player.max_hp}
⚡ **ОД сейчас:** {player.od_current}
📊 **ОД заработано сегодня:** {player.od_today}/{50}
🥇 **Побед:** {player.wins}

**Прогресс до ур. {player.level + 1}:** {bar} {pct}%
"""
        await message.answer(profile_text)
