"""
Handlers for task management with FSM.
Following the router pattern from backend/routers/
"""

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import AddTaskStates
from database import async_session_maker
from db import get_player, update_player, create_task, get_user_tasks, get_task, complete_task
from db import get_all_skills, get_player_skills, has_skill, unlock_skill, update_skill_progress
from keyboards.inline import get_od_selection_keyboard
from config import settings
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("add_task"))
async def cmd_add_task(message: types.Message, state: FSMContext):
    """Start the task creation process."""
    user_id = message.from_user.id

    async with async_session_maker() as session:
        player = await get_player(session, user_id)
        if player is None:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

    await message.answer("📝 Введите название задачи:")
    await state.set_state(AddTaskStates.waiting_for_name)


@router.message(AddTaskStates.waiting_for_name)
async def process_task_name(message: types.Message, state: FSMContext):
    """Process task name and ask for OD evaluation method."""
    task_name = message.text.strip()

    if len(task_name) > 100:
        await message.answer("❌ Название слишком длинное. Введите название до 100 символов:")
        return

    await state.update_data(task_name=task_name)
    await message.answer(
        "⚡ Выберите способ оценки сложности:",
        reply_markup=get_od_selection_keyboard()
    )
    await state.set_state(AddTaskStates.waiting_for_od_choice)


@router.callback_query(F.data == "od_manual")
async def process_od_manual(callback: types.CallbackQuery, state: FSMContext):
    """User chose manual OD input."""
    await callback.message.edit_text("⚡ Введите количество ОД (1-10):")
    await state.set_state(AddTaskStates.waiting_for_od)


@router.message(AddTaskStates.waiting_for_od)
async def process_task_od(message: types.Message, state: FSMContext):
    """Process OD value and create task."""
    try:
        od = int(message.text.strip())
        if od < 1 or od > 10:
            await message.answer("❌ ОД должно быть от 1 до 10. Введите значение:")
            return
    except ValueError:
        await message.answer("❌ Введите число от 1 до 10:")
        return

    user_id = message.from_user.id
    data = await state.get_data()
    task_name = data.get("task_name")

    async with async_session_maker() as session:
        task = await create_task(session, user_id, task_name, od)
        logger.info(f"Task created: {task.id} for user {user_id}")

    await message.answer(f"✅ Задача '{task_name}' добавлена! (ОД: {od})")
    await state.clear()


@router.callback_query(F.data == "od_cancel")
async def cancel_od_selection(callback: types.CallbackQuery, state: FSMContext):
    """Cancel OD selection."""
    await callback.message.edit_text("❌ Создание задачи отменено.")
    await state.clear()


@router.message(Command("tasks"))
async def cmd_tasks(message: types.Message):
    """Show user's tasks."""
    user_id = message.from_user.id

    async with async_session_maker() as session:
        player = await get_player(session, user_id)
        if player is None:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        tasks = await get_user_tasks(session, user_id)

        if not tasks:
            await message.answer("📋 У вас нет задач на сегодня.\nИспользуйте /add_task чтобы добавить задачу.")
            return

        tasks_text = "📋 **Ваши задачи:**\n\n"
        for i, task in enumerate(tasks, 1):
            status = "✅" if task.completed else "⏳"
            tasks_text += f"{i}. {status} {task.name} (ОД: {task.od})\n"

        tasks_text += f"\n💡 Используйте /complete <номер> чтобы выполнить задачу"
        await message.answer(tasks_text)


@router.message(Command("complete"))
async def cmd_complete(message: types.Message, state: FSMContext):
    """Show tasks with numbers for completion."""
    user_id = message.from_user.id

    async with async_session_maker() as session:
        tasks = await get_user_tasks(session, user_id)

        if not tasks:
            await message.answer("📋 У вас нет задач для выполнения.")
            return

        tasks_text = "Выберите задачу для выполнения (введите номер):\n\n"
        for i, task in enumerate(tasks, 1):
            tasks_text += f"{i}. {task.name} (ОД: {task.od})\n"

        await message.answer(tasks_text)
        # Set state to waiting for task selection
        await state.set_state(AddTaskStates.waiting_for_task_completion)


@router.message(AddTaskStates.waiting_for_task_completion, F.text.isdigit())
async def process_complete_task(message: types.Message, state: FSMContext):
    """Complete a task by number."""
    task_number = int(message.text.strip())
    user_id = message.from_user.id

    async with async_session_maker() as session:
        tasks = await get_user_tasks(session, user_id)

        if task_number < 1 or task_number > len(tasks):
            await message.answer("❌ Неверный номер задачи.")
            return

        task = tasks[task_number - 1]
        player = await get_player(session, user_id)

        # Complete the task
        await complete_task(session, task)

        # Calculate rewards
        xp_reward = task.od * 10

        # Enforce daily OD limit
        max_od = settings.max_daily_od
        od_gained = min(task.od, max_od - player.od_today)
        if od_gained < 0:
            od_gained = 0

        player.xp += xp_reward
        player.od_today += od_gained  # Track total earned today (for limit)
        player.od_current += od_gained  # Add to available OD (for spending)

        # Level up check: each level requires (level * 100) XP
        # Level 1→2: 100 XP, Level 2→3: 200 XP, Level 3→4: 300 XP, etc.
        level_up_msg = ""
        while True:
            xp_needed = player.level * 100
            if player.xp >= xp_needed:
                player.xp -= xp_needed  # Carry over excess XP
                player.level += 1
                player.max_hp += 5
                player.hp = player.max_hp
                level_up_msg = f"\n🎉 **УРОВЕНЬ ПОВЫШЕН!** Теперь вы уровень {player.level}!"
            else:
                break

        # OD limit warning
        od_limit_msg = ""
        if od_gained < task.od:
            od_limit_msg = f"\n⚠️ **Лимит ОД на сегодня!** Получено {od_gained}/{max_od} ОД"
        elif player.od_today >= max_od:
            od_limit_msg = f"\n⚠️ Вы достигли лимита ОД на сегодня ({max_od}/{max_od})"

        await update_player(session, player)

        # Check skill progress after task completion
        unlocked_skills = await check_skill_progress_after_task(session, user_id, task, player)

        skill_unlock_msg = ""
        if unlocked_skills:
            skill_unlock_msg = f"\n\n🎉 **Новые навыки:**\n"
            for skill_name in unlocked_skills:
                skill_unlock_msg += f"✅ {skill_name}\n"

        await message.answer(
            f"✅ Задача '{task.name}' выполнена!\n"
            f"+{xp_reward} XP | +{od_gained} ОД сегодня{level_up_msg}{od_limit_msg}{skill_unlock_msg}"
            f"\nТекущий статус: Уровень {player.level} | XP: {player.xp} | HP: {player.hp} | ОД: {player.od_current} (заработано сегодня: {player.od_today}/{max_od})"
        )
        logger.info(f"Task {task.id} completed by user {user_id}")

        # Clear the state after successful completion
        await state.clear()


@router.message(F.text.isdigit())
async def handle_random_digit(message: types.Message):
    """Handle digit messages outside of task completion flow."""
    await message.answer(
        "💡 Если вы хотите выполнить задачу, используйте /complete\n"
        "Чтобы добавить задачу, используйте /add_task"
    )


async def check_skill_progress_after_task(session, user_id, task, player):
    """Check and update skill progress after completing a task."""
    unlocked_skills = []

    # Skill 2: "Сильный удар" - complete 3 tasks
    skill_2_progress = await update_skill_progress(session, user_id, 2, target_steps=3, increment=1)
    if skill_2_progress.current_step >= skill_2_progress.target_steps:
        has_skill_2 = await has_skill(session, user_id, 2)
        if not has_skill_2:
            await unlock_skill(session, user_id, 2)
            unlocked_skills.append("Сильный удар")
            logger.info(f"User {user_id} unlocked skill: Сильный удар")

    # Skill 3: "Защита" - complete 5 low OD tasks (1-2)
    if task.od <= 2:
        skill_3_progress = await update_skill_progress(session, user_id, 3, target_steps=5, increment=1)
        if skill_3_progress.current_step >= skill_3_progress.target_steps:
            has_skill_3 = await has_skill(session, user_id, 3)
            if not has_skill_3:
                await unlock_skill(session, user_id, 3)
                unlocked_skills.append("Защита")
                logger.info(f"User {user_id} unlocked skill: Защита")

    # Skill 4: "Восстановление" - complete 3 high OD tasks (5+)
    if task.od >= 5:
        skill_4_progress = await update_skill_progress(session, user_id, 4, target_steps=3, increment=1)
        if skill_4_progress.current_step >= skill_4_progress.target_steps:
            has_skill_4 = await has_skill(session, user_id, 4)
            if not has_skill_4:
                await unlock_skill(session, user_id, 4)
                unlocked_skills.append("Восстановление")
                logger.info(f"User {user_id} unlocked skill: Восстановление")

    # Skill 5: "Критический удар" - unlock at level 5
    if player.level >= 5:
        has_skill_5 = await has_skill(session, user_id, 5)
        if not has_skill_5:
            await unlock_skill(session, user_id, 5)
            unlocked_skills.append("Критический удар")
            logger.info(f"User {user_id} unlocked skill: Критический удар (level {player.level})")

    # Skill 6: "Щит титана" - unlock at level 10
    if player.level >= 10:
        has_skill_6 = await has_skill(session, user_id, 6)
        if not has_skill_6:
            await unlock_skill(session, user_id, 6)
            unlocked_skills.append("Щит титана")
            logger.info(f"User {user_id} unlocked skill: Щит титана (level {player.level})")

    # Skill 7: "Вампиризм" - unlock at 10 wins
    if player.wins >= 10:
        has_skill_7 = await has_skill(session, user_id, 7)
        if not has_skill_7:
            await unlock_skill(session, user_id, 7)
            unlocked_skills.append("Вампиризм")
            logger.info(f"User {user_id} unlocked skill: Вампиризм (wins {player.wins})")

    # Skill 8: "Мегаудар" - unlock at level 20
    if player.level >= 20:
        has_skill_8 = await has_skill(session, user_id, 8)
        if not has_skill_8:
            await unlock_skill(session, user_id, 8)
            unlocked_skills.append("Мегаудар")
            logger.info(f"User {user_id} unlocked skill: Мегаудар (level {player.level})")

    # Skill 9: "Ярость берсерка" - unlock at 25 wins
    if player.wins >= 25:
        has_skill_9 = await has_skill(session, user_id, 9)
        if not has_skill_9:
            await unlock_skill(session, user_id, 9)
            unlocked_skills.append("Ярость берсерка")
            logger.info(f"User {user_id} unlocked skill: Ярость берсерка (wins {player.wins})")

    # Skill 10: "Феникс" - unlock at level 50
    if player.level >= 50:
        has_skill_10 = await has_skill(session, user_id, 10)
        if not has_skill_10:
            await unlock_skill(session, user_id, 10)
            unlocked_skills.append("Феникс")
            logger.info(f"User {user_id} unlocked skill: Феникс (level {player.level})")

    # Notify user about unlocked skills
    if unlocked_skills:
        logger.info(f"User {user_id} unlocked skills: {unlocked_skills}")

    return unlocked_skills
