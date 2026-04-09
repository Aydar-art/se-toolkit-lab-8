"""
Handlers for guild system.
"""

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import async_session_maker
from db import (
    get_player, update_player,
    create_guild, get_guild_by_name, get_guild_by_id,
    get_guild_members, get_guild_member_count,
    join_guild, leave_guild, get_player_guild, get_guild_stats
)
import logging

logger = logging.getLogger(__name__)

router = Router()


class GuildStates(StatesGroup):
    """States for guild operations."""
    waiting_for_guild_name = State()
    waiting_for_guild_description = State()
    waiting_for_join_guild_name = State()


@router.message(Command("create_guild"))
async def cmd_create_guild(message: types.Message, state: FSMContext):
    """Start creating a new guild."""
    user_id = message.from_user.id

    async with async_session_maker() as session:
        player = await get_player(session, user_id)
        if player is None:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        if player.guild_id:
            guild = await get_guild_by_id(session, player.guild_id)
            if guild:
                await message.answer(f"❌ Вы уже состоите в гильдии **{guild.name}**!\nСначала покиньте её через /leave_guild")
                return

    await message.answer("🏰 Введите название гильдии:")
    await state.set_state(GuildStates.waiting_for_guild_name)


@router.message(GuildStates.waiting_for_guild_name)
async def process_guild_name(message: types.Message, state: FSMContext):
    """Process guild name."""
    guild_name = message.text.strip()

    if len(guild_name) < 3 or len(guild_name) > 30:
        await message.answer("❌ Название должно быть от 3 до 30 символов:")
        return

    async with async_session_maker() as session:
        existing = await get_guild_by_name(session, guild_name)
        if existing:
            await message.answer(f"❌ Гильдия с названием **{guild_name}** уже существует! Введите другое:")
            return

    await state.update_data(guild_name=guild_name)
    await message.answer("📝 Введите описание гильдии (или '-' чтобы пропустить):")
    await state.set_state(GuildStates.waiting_for_guild_description)


@router.message(GuildStates.waiting_for_guild_description)
async def process_guild_description(message: types.Message, state: FSMContext):
    """Process guild description and create guild."""
    description = message.text.strip()
    if description == "-":
        description = None

    data = await state.get_data()
    guild_name = data.get("guild_name")
    user_id = message.from_user.id

    async with async_session_maker() as session:
        # Create guild
        guild = await create_guild(session, guild_name, user_id, description)

        # Add owner to guild
        await join_guild(session, user_id, guild.id)

    await message.answer(
        f"🏰 Гильдия **{guild_name}** создана!\n"
        f"Вы стали её лидером.\n\n"
        f"Используйте /guild чтобы посмотреть информацию о гильдии.\n"
        f"Другие игроки могут вступить через /join_guild {guild_name}"
    )
    await state.clear()


@router.message(Command("join_guild"))
async def cmd_join_guild(message: types.Message, state: FSMContext):
    """Start joining an existing guild."""
    user_id = message.from_user.id

    async with async_session_maker() as session:
        player = await get_player(session, user_id)
        if player is None:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        if player.guild_id:
            guild = await get_guild_by_id(session, player.guild_id)
            if guild:
                await message.answer(f"❌ Вы уже состоите в гильдии **{guild.name}**!\nСначала покиньте её через /leave_guild")
                return

    await message.answer("🤝 Введите название гильдии для вступления:")
    await state.set_state(GuildStates.waiting_for_join_guild_name)


@router.message(GuildStates.waiting_for_join_guild_name)
async def process_join_guild(message: types.Message, state: FSMContext):
    """Process guild name and join."""
    guild_name = message.text.strip()
    user_id = message.from_user.id

    async with async_session_maker() as session:
        guild = await get_guild_by_name(session, guild_name)
        if guild is None:
            await message.answer(f"❌ Гильдия **{guild_name}** не найдена!\nПроверьте название и попробуйте снова:")
            return

        # Double-check player isn't already in a guild
        player = await get_player(session, user_id)
        if player and player.guild_id:
            await message.answer(f"❌ Вы уже состоите в гильдии **{guild.name}**!")
            await state.clear()
            return

        # Join guild
        await join_guild(session, user_id, guild.id)
        member_count = await get_guild_member_count(session, guild.id)

        # Get owner name
        owner = await get_player(session, guild.owner_id)
        owner_name = owner.username if owner and owner.username else f"user{guild.owner_id}"

    await message.answer(
        f"✅ Вы вступили в гильдию **{guild.name}**!\n"
        f"👑 Лидер: {owner_name}\n"
        f"👥 Участников: {member_count}\n\n"
        f"Используйте /guild чтобы посмотреть информацию о гильдии."
    )
    await state.clear()


@router.message(Command("leave_guild"))
async def cmd_leave_guild(message: types.Message):
    """Leave current guild."""
    user_id = message.from_user.id

    async with async_session_maker() as session:
        player = await get_player(session, user_id)
        if player is None:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        if not player.guild_id:
            await message.answer("❌ Вы не состоите ни в одной гильдии!")
            return

        guild = await get_guild_by_id(session, player.guild_id)
        if guild is None:
            await message.answer("❌ Гильдия не найдена!")
            return

        # Check if owner is leaving
        if guild.owner_id == user_id:
            # Transfer ownership or disband
            members = await get_guild_members(session, guild.id)
            other_members = [m for m in members if m.user_id != user_id]
            if other_members:
                # Transfer to first other member
                new_owner = other_members[0]
                guild.owner_id = new_owner.user_id
                session.add(guild)
                await session.commit()
                await leave_guild(session, user_id)
                await message.answer(
                    f"👋 Вы покинули гильдию **{guild.name}**.\n"
                    f"Лидерство передано игроку {new_owner.username or f'user{new_owner.user_id}'}."
                )
            else:
                # Disband guild
                await leave_guild(session, user_id)
                await message.answer(
                    f"🏚️ Вы покинули гильдию **{guild.name}**.\n"
                    f"Гильдия распущена, так как вы были единственным участником."
                )
        else:
            await leave_guild(session, user_id)
            await message.answer(f"👋 Вы покинули гильдию **{guild.name}**.")


@router.message(Command("guild"))
async def cmd_guild(message: types.Message):
    """Show guild information and statistics."""
    user_id = message.from_user.id

    async with async_session_maker() as session:
        player = await get_player(session, user_id)
        if player is None:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        if not player.guild_id:
            await message.answer(
                "🏰 Вы не состоите в гильдии.\n\n"
                "Создайте свою: /create_guild\n"
                "Вступите в чужую: /join_guild <название>"
            )
            return

        guild = await get_guild_by_id(session, player.guild_id)
        if guild is None:
            await message.answer("❌ Ваша гильдия не найдена!")
            return

        members = await get_guild_members(session, guild.id)
        stats = await get_guild_stats(session, guild.id)

        # Get owner info
        owner = await get_player(session, guild.owner_id)
        owner_name = owner.username if owner and owner.username else f"user{guild.owner_id}"

        # Build members list
        members_text = ""
        for i, m in enumerate(members, 1):
            role = "👑 Лидер" if m.user_id == guild.owner_id else "⚔️ Боец"
            m_name = m.username if m.username else f"user{m.user_id}"
            members_text += f"{i}. {role} — {m_name} (Ур. {m.level})\n"

        best_fighter = stats['most_wins_player']
        best_name = best_fighter.username if best_fighter.username else f'user{best_fighter.user_id}'

        guild_text = f"""
🏰 **Гильдия: {guild.name}**

📝 **Описание:** {guild.description or "Нет описания"}
👑 **Лидер:** {owner_name}
📅 **Создана:** {guild.created_date}

📊 **Статистика гильдии:**
• Участников: {stats['member_count']}
• Общий уровень: {stats['total_level']}
• Общий XP: {stats['total_xp']}
• Всего побед: {stats['total_wins']}
• Средний уровень: {stats['avg_level']}

🏆 **Лучший боец:** {best_name} ({best_fighter.wins} побед)

👥 **Участники:**
{members_text}
"""
        await message.answer(guild_text)


@router.message(Command("guild_stats"))
async def cmd_guild_stats(message: types.Message):
    """Show guild statistics leaderboard."""
    user_id = message.from_user.id

    async with async_session_maker() as session:
        player = await get_player(session, user_id)
        if player is None:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        if not player.guild_id:
            await message.answer("❌ Вы не состоите в гильдии!")
            return

        guild = await get_guild_by_id(session, player.guild_id)
        if guild is None:
            await message.answer("❌ Ваша гильдия не найдена!")
            return

        members = await get_guild_members(session, guild.id)

        # Sort by level for leaderboard
        sorted_by_level = sorted(members, key=lambda m: m.level, reverse=True)
        sorted_by_wins = sorted(members, key=lambda m: m.wins, reverse=True)
        sorted_by_xp = sorted(members, key=lambda m: m.xp, reverse=True)

        stats_text = f"📊 **Статистика гильдии {guild.name}**\n\n"

        stats_text += "**🏆 По уровню:**\n"
        for i, m in enumerate(sorted_by_level[:5], 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            stats_text += f"{medal} {i}. {m.username or f'user{m.user_id}'} — Ур. {m.level}\n"

        stats_text += f"\n**⚔️ По победам:**\n"
        for i, m in enumerate(sorted_by_wins[:5], 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            stats_text += f"{medal} {i}. {m.username or f'user{m.user_id}'} — {m.wins} побед\n"

        stats_text += f"\n**⭐ По XP:**\n"
        for i, m in enumerate(sorted_by_xp[:5], 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            stats_text += f"{medal} {i}. {m.username or f'user{m.user_id}'} — {m.xp} XP\n"

        await message.answer(stats_text)
