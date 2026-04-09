"""
Inline keyboard factories for the bot.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_od_selection_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for choosing OD evaluation method."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✍️ Ввести вручную", callback_data="od_manual"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="od_cancel"))
    return builder.as_markup()


def get_skill_selection_keyboard(skills: list, max_select: int = 3) -> InlineKeyboardMarkup:
    """Get keyboard for selecting skills before fight."""
    builder = InlineKeyboardBuilder()
    for skill in skills:
        builder.row(InlineKeyboardButton(
            text=f"{skill.name} ({skill.od_cost} ОД)",
            callback_data=f"skill_select_{skill.id}"
        ))
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="skill_done"))
    return builder.as_markup()


def get_fight_action_keyboard(skills: list) -> InlineKeyboardMarkup:
    """Get keyboard for fight actions."""
    builder = InlineKeyboardBuilder()
    
    # Basic attack
    builder.row(InlineKeyboardButton(text="⚔️ Атака (1 ОД)", callback_data="fight_action_attack"))
    
    # Skills
    for skill in skills:
        if skill.id != 1:  # Skip basic attack (already added)
            builder.row(InlineKeyboardButton(
                text=f"{skill.name} ({skill.od_cost} ОД)",
                callback_data=f"fight_action_skill_{skill.id}"
            ))
    
    # Defense
    builder.row(InlineKeyboardButton(text="🛡️ Защита (0 ОД)", callback_data="fight_action_defend"))
    
    return builder.as_markup()


def get_fight_challenge_keyboard(challenger_id: int) -> InlineKeyboardMarkup:
    """Get keyboard for accepting/rejecting fight challenge."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚔️ Принять", callback_data=f"fight_accept_{challenger_id}"))
    builder.row(InlineKeyboardButton(text="❌ Отказаться", callback_data=f"fight_reject_{challenger_id}"))
    return builder.as_markup()
