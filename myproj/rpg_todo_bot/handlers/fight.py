"""
Handlers for PvP duels with full automated turn-based system.
Following the router pattern from backend/routers/
"""

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import FightStates
from database import async_session_maker
from db import (
    get_player, update_player, get_player_skills, save_fight_history,
    get_player_history, get_rating
)
from keyboards.inline import (
    get_fight_challenge_keyboard, get_skill_selection_keyboard,
    get_fight_action_keyboard
)
import logging
import random
import json
from datetime import date
from typing import Dict

logger = logging.getLogger(__name__)

router = Router()

# In-memory fight sessions
fight_sessions: Dict[str, dict] = {}

# In-memory pending fight challenges: {opponent_user_id: {challenger_id, challenger_username, message}}
pending_challenges: Dict[int, dict] = {}

# Maps user_id to their active fight_id (so both players can find their fight)
user_fight_map: Dict[int, str] = {}


@router.message(Command("fight"))
async def cmd_fight(message: types.Message, state: FSMContext):
    """Initiate a PvP duel."""
    challenger_id = message.from_user.id
    challenger_username = message.from_user.username or f"user{challenger_id}"

    async with async_session_maker() as session:
        challenger = await get_player(session, challenger_id)
        if challenger is None:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        if challenger.od_current < 3:
            await message.answer("❌ Нужно минимум 3 ОД для вызова на дуэль!")
            return

    # Store challenger data and wait for opponent username
    await state.update_data(
        challenger_id=challenger_id,
        challenger_username=challenger_username
    )
    await state.set_state(FightStates.waiting_for_opponent)

    await message.answer(
        "⚔️ Введите имя противника (username без @):"
    )


@router.message(FightStates.waiting_for_opponent)
async def process_fight_opponent(message: types.Message, state: FSMContext):
    """Process opponent username and send challenge."""
    opponent_username = message.text.strip().lstrip("@")

    if not opponent_username:
        await message.answer("❌ Введите имя противника:")
        return

    data = await state.get_data()
    challenger_id = data.get("challenger_id")
    challenger_username = data.get("challenger_username")

    async with async_session_maker() as session:
        # Look up opponent by username in the database
        from sqlmodel import select
        from models import Player
        result = await session.execute(
            select(Player).where(Player.username == opponent_username)
        )
        opponent = result.scalar_one_or_none()

        if opponent is None:
            # Try matching by user_id if username is like "user123"
            if opponent_username.startswith("user"):
                try:
                    potential_id = int(opponent_username[4:])
                    result = await session.execute(
                        select(Player).where(Player.user_id == potential_id)
                    )
                    opponent = result.scalar_one_or_none()
                except (ValueError, IndexError):
                    pass

        if opponent is None:
            await message.answer(f"❌ Игрок {opponent_username} не найден!")
            await state.clear()
            return

        if opponent.user_id == challenger_id:
            await message.answer("❌ Нельзя вызывать себя на дуэль!")
            await state.clear()
            return

        # Check if there's already a pending challenge for this opponent
        if opponent.user_id in pending_challenges:
            await message.answer(f"❌ У {opponent_username} уже есть ожидающий вызов!")
            await state.clear()
            return

    # Store pending challenge
    pending_challenges[opponent.user_id] = {
        "challenger_id": challenger_id,
        "challenger_username": challenger_username,
        "timestamp": date.today()
    }

    await message.answer(
        f"⚔️ Вызов отправлен игроку {opponent_username}!\n"
        f"Ожидание принятия..."
    )

    # Notify the opponent via direct message
    try:
        await message.bot.send_message(
            opponent.user_id,
            f"⚔️ {challenger_username} вызывает вас на дуэль!\n"
            f"Стоимость: 3 ОД\n\n"
            f"Используйте /accept чтобы принять вызов.",
            reply_markup=get_fight_challenge_keyboard(challenger_id)
        )
    except Exception as e:
        logger.warning(f"Could not notify opponent {opponent.user_id}: {e}")

    await state.clear()


@router.message(Command("accept"))
async def cmd_accept_fight(message: types.Message, state: FSMContext):
    """Accept a pending fight challenge."""
    user_id = message.from_user.id

    async with async_session_maker() as session:
        player = await get_player(session, user_id)
        if player is None:
            await message.answer("❌ Вы не зарегистрированы!")
            return

        if player.od_current < 3:
            await message.answer("❌ Нужно минимум 3 ОД для принятия дуэли!")
            return

    # Check if there's a pending challenge for this user
    if user_id not in pending_challenges:
        await message.answer(
            "❌ У вас нет ожидающих вызовов!\n"
            "Кто-то должен вызвать вас через /fight @your_username"
        )
        return

    challenge = pending_challenges.pop(user_id)
    challenger_id = challenge["challenger_id"]
    challenger_username = challenge["challenger_username"]

    # Verify challenger still has enough OD
    async with async_session_maker() as session:
        challenger = await get_player(session, challenger_id)
        if challenger is None or challenger.od_current < 3:
            await message.answer("❌ Вызывающий больше не может участвовать в дуэли!")
            return

    await message.answer("⚔️ Вы приняли вызов! Переходим к выбору навыков...")

    # Start fight between two real players
    acceptor_username = message.from_user.username or f"user{user_id}"
    await start_fight_between(message, state, user_id, acceptor_username, challenger_username, challenger_id)


async def start_fight_between(message, state, acceptor_id, acceptor_username, challenger_username, challenger_id):
    """Start a fight between two real players."""

    async with async_session_maker() as session:
        # Get skills for both players
        acceptor_skills = await get_player_skills(session, acceptor_id)
        challenger_skills = await get_player_skills(session, challenger_id)

        # Ensure both have basic attack skill
        from db import has_skill, unlock_skill
        if not acceptor_skills:
            has_basic = await has_skill(session, acceptor_id, 1)
            if not has_basic:
                await unlock_skill(session, acceptor_id, 1)
                acceptor_skills = await get_player_skills(session, acceptor_id)

        if not challenger_skills:
            has_basic = await has_skill(session, challenger_id, 1)
            if not has_basic:
                await unlock_skill(session, challenger_id, 1)
                challenger_skills = await get_player_skills(session, challenger_id)

    # Limit to first 3 skills for each player
    acceptor_selected = acceptor_skills[:3]
    challenger_selected = challenger_skills[:3]

    # Store fight session
    fight_id = f"{challenger_id}_{acceptor_id}"
    fight_sessions[fight_id] = {
        "player1": {
            "user_id": challenger_id,
            "username": challenger_username,
            "hp": 25,
            "max_hp": 25,
            "od": 10,
            "skills": challenger_selected,
            "od_spent": 0,
            "defending": False
        },
        "player2": {
            "user_id": acceptor_id,
            "username": acceptor_username,
            "hp": 25,
            "max_hp": 25,
            "od": 10,
            "skills": acceptor_selected,
            "od_spent": 0,
            "defending": False
        },
        "current_turn": challenger_id,  # Challenger goes first
        "round": 1,
        "fight_id": fight_id
    }

    # Register both players in the fight map
    user_fight_map[challenger_id] = fight_id
    user_fight_map[acceptor_id] = fight_id

    await state.update_data(fight_id=fight_id)
    await state.set_state(FightStates.in_fight)

    # Notify both players
    try:
        # Send to acceptor
        await send_fight_status(message, fight_sessions[fight_id], acceptor_id)

        # Send to challenger
        bot = message.bot
        challenger_msg = await bot.send_message(
            challenger_id,
            f"⚔️ {acceptor_username} принял ваш вызов! Бой начинается!\n\n"
            f"Ваш ход!"
        )
        await send_fight_status(challenger_msg, fight_sessions[fight_id], challenger_id)
    except Exception as e:
        logger.warning(f"Could not notify both players: {e}")
        await message.answer(f"⚔️ Бой начался! Ваш противник: {challenger_username}")


async def start_skill_selection(message, state, user_id, opponent_username, opponent_id):
    """Start skill selection phase for both players."""
    async with async_session_maker() as session:
        skills = await get_player_skills(session, user_id)
        
        if not skills:
            # Give player basic attack skill if they have none
            from db import has_skill, unlock_skill
            has_basic = await has_skill(session, user_id, 1)
            if not has_basic:
                await unlock_skill(session, user_id, 1)
                skills = await get_player_skills(session, user_id)
    
    # For demo, limit to 3 skills
    selected_skills = skills[:3]
    
    # Store fight session
    fight_id = f"{user_id}_{opponent_id}"
    fight_sessions[fight_id] = {
        "player1": {
            "user_id": user_id,
            "username": message.from_user.username or f"user{user_id}",
            "hp": 25,
            "max_hp": 25,
            "od": 10,
            "skills": selected_skills,
            "od_spent": 0,
            "defending": False
        },
        "player2": {
            "user_id": opponent_id,
            "username": opponent_username,
            "hp": 25,
            "max_hp": 25,
            "od": 10,
            "skills": selected_skills,  # For demo, same skills
            "od_spent": 0,
            "defending": False
        },
        "current_turn": user_id,
        "round": 1,
        "fight_id": fight_id
    }
    
    await state.update_data(fight_id=fight_id)
    await state.set_state(FightStates.in_fight)
    
    # Send fight status
    await send_fight_status(message, fight_sessions[fight_id], user_id)


@router.callback_query(F.data.startswith("fight_accept_"))
async def callback_fight_accept(callback: types.CallbackQuery, state: FSMContext):
    """Handle fight acceptance via inline button."""
    challenger_id = int(callback.data.split("_")[2])
    opponent_id = callback.from_user.id

    # Check if this challenge is still pending
    if opponent_id not in pending_challenges:
        await callback.answer("❌ Этот вызов уже недействителен!", show_alert=True)
        return

    challenge = pending_challenges.pop(opponent_id)

    async with async_session_maker() as session:
        opponent = await get_player(session, opponent_id)
        if opponent is None:
            await callback.answer("❌ Вы не зарегистрированы!", show_alert=True)
            return

        if opponent.od_current < 3:
            await callback.answer("❌ Нужно минимум 3 ОД!", show_alert=True)
            return

        # Verify challenger still has enough OD
        challenger = await get_player(session, challenger_id)
        if challenger is None or challenger.od_current < 3:
            await callback.answer("❌ Вызывающий больше не может участвовать!", show_alert=True)
            return

    await callback.message.edit_text("⚔️ Вы приняли вызов! Бой начинается!")

    # Start fight between two real players
    acceptor_username = callback.from_user.username or f"user{opponent_id}"
    await start_fight_between(callback.message, state, opponent_id, acceptor_username, challenge["challenger_username"], challenger_id)


@router.callback_query(F.data.startswith("fight_reject_"))
async def callback_fight_reject(callback: types.CallbackQuery, state: FSMContext):
    """Handle fight rejection via inline button."""
    challenger_id = int(callback.data.split("_")[2])
    opponent_id = callback.from_user.id

    # Remove pending challenge
    if opponent_id in pending_challenges:
        del pending_challenges[opponent_id]

    await callback.message.edit_text("❌ Вы отказались от дуэли.")

    # Notify the challenger
    try:
        await callback.bot.send_message(
            challenger_id,
            f"❌ Игрок {callback.from_user.username or f'user{opponent_id}'} отказался от вашей дуэли."
        )
    except Exception as e:
        logger.warning(f"Could not notify challenger {challenger_id}: {e}")

    await state.clear()


async def send_fight_status(message, fight_data, user_id):
    """Send updated fight status to a player."""
    p1 = fight_data["player1"]
    p2 = fight_data["player2"]
    
    is_player1 = (user_id == p1["user_id"])
    current_player = p1 if is_player1 else p2
    opponent = p2 if is_player1 else p1
    
    is_my_turn = (fight_data["current_turn"] == user_id)
    
    status_text = f"""
⚔️ **БОЙ - Раунд {fight_data["round"]}**

👤 **Вы:** {current_player["username"]}
❤️ HP: {current_player["hp"]}/{current_player["max_hp"]}
⚡ ОД: {current_player["od"]}

👤 **Противник:** {opponent["username"]}
❤️ HP: {opponent["hp"]}/{opponent["max_hp"]}
⚡ ОД: {opponent["od"]}

{"🎯 **ВАШ ХОД!** Выберите действие:" if is_my_turn else "⏳ Ход противника..."}
"""
    
    if is_my_turn:
        await message.answer(status_text, reply_markup=get_fight_action_keyboard(current_player["skills"]))
    else:
        await message.answer(status_text)


@router.callback_query(F.data == "fight_action_attack")
async def callback_fight_attack(callback: types.CallbackQuery, state: FSMContext):
    """Handle basic attack in fight."""
    await process_fight_action(callback, state, "attack")


@router.callback_query(F.data.startswith("fight_action_skill_"))
async def callback_fight_skill(callback: types.CallbackQuery, state: FSMContext):
    """Handle skill usage in fight."""
    skill_id = int(callback.data.split("_")[3])
    await process_fight_action(callback, state, "skill", skill_id)


@router.callback_query(F.data == "fight_action_defend")
async def callback_fight_defend(callback: types.CallbackQuery, state: FSMContext):
    """Handle defense in fight."""
    await process_fight_action(callback, state, "defend")


async def process_fight_action(callback, state, action_type, skill_id=None):
    """Process a fight action."""
    user_id = callback.from_user.id
    fight_data = await state.get_data()
    fight_id = fight_data.get("fight_id")

    # Fallback: look up fight_id from user_fight_map
    if not fight_id:
        fight_id = user_fight_map.get(user_id)

    if not fight_id or fight_id not in fight_sessions:
        await callback.answer("❌ Бой не найден!", show_alert=True)
        return
    
    fight = fight_sessions[fight_id]
    
    # Check if it's player's turn
    if fight["current_turn"] != user_id:
        await callback.answer("⏳ Сейчас не ваш ход!", show_alert=True)
        return
    
    current_player = fight["player1"] if user_id == fight["player1"]["user_id"] else fight["player2"]
    opponent = fight["player2"] if user_id == fight["player1"]["user_id"] else fight["player1"]
    
    # Process action
    damage = 0
    od_cost = 0
    action_name = ""
    
    if action_type == "attack":
        od_cost = 1
        if current_player["od"] < od_cost:
            await callback.answer("❌ Недостаточно ОД!", show_alert=True)
            return
        
        damage = random.randint(3, 7)
        action_name = "⚔️ Атака"
        
    elif action_type == "skill":
        # Find skill
        skill = None
        for s in current_player["skills"]:
            if s.id == skill_id:
                skill = s
                break
        
        if skill is None:
            await callback.answer("❌ Навык не найден!", show_alert=True)
            return
        
        od_cost = skill.od_cost
        if current_player["od"] < od_cost:
            await callback.answer("❌ Недостаточно ОД!", show_alert=True)
            return
        
        if skill.effect_type == "damage":
            damage = skill.effect_value + random.randint(-2, 2)
            action_name = f"💥 {skill.name}"
        elif skill.effect_type == "heal":
            heal_amount = skill.effect_value
            current_player["hp"] = min(current_player["hp"] + heal_amount, current_player["max_hp"])
            action_name = f"💚 {skill.name} (+{heal_amount} HP)"
            damage = 0
        elif skill.effect_type == "crit_damage":
            # 30% chance for double damage
            is_crit = random.random() < 0.3
            damage = skill.effect_value
            if is_crit:
                damage = skill.effect_value  # Already doubled in effect_value
                action_name = f"💥💥 {skill.name} — КРИТ! ({damage} урона)"
            else:
                damage = skill.effect_value // 2
                action_name = f"💥 {skill.name} ({damage} урона)"
        elif skill.effect_type == "full_block":
            current_player["blocking"] = True
            action_name = f"🛡️ {skill.name} — следующая атака заблокирована!"
            damage = 0
        elif skill.effect_type == "drain":
            damage = skill.effect_value
            heal_amount = skill.effect_value // 2
            current_player["hp"] = min(current_player["hp"] + heal_amount, current_player["max_hp"])
            action_name = f"🧛 {skill.name} ({damage} урон, +{heal_amount} HP)"
        elif skill.effect_type == "berserk":
            # More damage when HP is low: multiplier from 1x to 3x
            hp_ratio = current_player["hp"] / current_player["max_hp"]
            multiplier = 1 + (1 - hp_ratio) * 2  # 1.0 at full HP, 3.0 at 0 HP
            damage = int(skill.effect_value * multiplier)
            action_name = f"🔥 {skill.name} (x{multiplier:.1f}) — {damage} урона!"
        elif skill.effect_type == "phoenix":
            # Passive skill - set flag for later
            current_player["phoenix_active"] = True
            action_name = f"🔥 {skill.name} — пассивная защита активирована!"
            damage = 0
            
    elif action_type == "defend":
        od_cost = 0
        current_player["defending"] = True
        action_name = "🛡️ Защита"
        damage = 0
    
    # Apply damage
    if damage > 0:
        # Check for full block (Щит титана)
        if opponent.get("blocking"):
            damage = 0
            opponent["blocking"] = False
            action_msg = f"{action_name}! 🛡️ Заблокировано Щитом титана!"
        elif opponent["defending"]:
            damage = damage // 2
            opponent["defending"] = False
            action_msg = f"{action_name}! Урон: {damage} (защита -50%)"
        else:
            action_msg = f"{action_name}! Урон: {damage}"

        opponent["hp"] = max(0, opponent["hp"] - damage)

        # Check for phoenix passive (survive with 1 HP once per fight)
        if opponent["hp"] <= 0 and opponent.get("phoenix_active"):
            opponent["hp"] = 1
            opponent["phoenix_active"] = False
            action_msg += "\n🔥 Феникс спас от смерти! (1 HP)"
    else:
        action_msg = f"{action_name}! "
        if damage > 0:
            action_msg += f"Урон: {damage}"

    # Deduct OD
    current_player["od"] -= od_cost
    current_player["od_spent"] += od_cost

    # Switch turns
    fight["current_turn"] = opponent["user_id"]
    if fight["current_turn"] == fight["player1"]["user_id"]:
        fight["round"] += 1

    # Check if fight ended
    if opponent["hp"] <= 0:
        await end_fight(callback, state, fight, user_id)
        return

    # Update the acting player's message with action result + new status
    await callback.message.edit_text(f"{action_msg}\n\n{callback.message.text}")

    # Send turn notification to the opponent
    try:
        bot = callback.bot
        opponent_msg = await bot.send_message(
            opponent["user_id"],
            f"⚔️ {current_player['username']} использовал(а) {action_name}!\n"
            f"{'Урон: ' + str(damage) if damage > 0 else 'Защита!'}\n\n"
            f"🎯 **ВАШ ХОД!** Выберите действие:"
        )
        await send_fight_status(opponent_msg, fight, opponent["user_id"])
    except Exception as e:
        logger.warning(f"Could not notify opponent {opponent['user_id']}: {e}")

    # Also update the acting player with "waiting" status
    await send_fight_status(callback.message, fight, user_id)


async def end_fight(callback, state, fight, winner_id):
    """End the fight and process rewards."""
    winner = fight["player1"] if winner_id == fight["player1"]["user_id"] else fight["player2"]
    loser = fight["player2"] if winner_id == fight["player1"]["user_id"] else fight["player1"]

    winner_username = winner["username"]
    loser_username = loser["username"]

    # Calculate rewards
    winner_xp = 50
    loser_xp = 10

    end_text = f"""
🏆 **БОЙ ЗАВЕРШЁН!**

🥇 **Победитель:** {winner_username}
🥈 **Проигравший:** {loser_username}

🎁 Награды:
• {winner_username}: +{winner_xp} XP
• {loser_username}: +{loser_xp} XP
"""

    # Update the acting player's message temporarily
    await callback.message.edit_text(end_text)
    
    # Update database
    async with async_session_maker() as session:
        winner_player = await get_player(session, winner_id)
        loser_player = await get_player(session, loser["user_id"])

        # Calculate OD spent for each player
        p1_od_spent = fight["player1"]["od_spent"]
        p2_od_spent = fight["player2"]["od_spent"]

        # Level up helper
        def check_level_up(player):
            level_ups = []
            while True:
                xp_needed = player.level * 100
                if player.xp >= xp_needed:
                    player.xp -= xp_needed
                    player.level += 1
                    player.max_hp += 5
                    player.hp = player.max_hp
                    level_ups.append(player.level)
                else:
                    break
            return level_ups

        if winner_player:
            winner_player.xp += winner_xp
            winner_player.wins += 1
            winner_od_spent = p1_od_spent if winner_id == fight["player1"]["user_id"] else p2_od_spent
            winner_player.od_current = max(0, winner_player.od_current - winner_od_spent)
            winner_level_ups = check_level_up(winner_player)
            await update_player(session, winner_player)

        if loser_player:
            loser_player.xp += loser_xp
            loser_od_spent = p2_od_spent if winner_id == fight["player1"]["user_id"] else p1_od_spent
            loser_player.od_current = max(0, loser_player.od_current - loser_od_spent)
            loser_level_ups = check_level_up(loser_player)
            await update_player(session, loser_player)
        
        # Save fight history
        skills_json = json.dumps({
            "player1_skills": [s.id for s in fight["player1"]["skills"]],
            "player2_skills": [s.id for s in fight["player2"]["skills"]]
        })

        await save_fight_history(
            session,
            fight["player1"]["user_id"],
            fight["player2"]["user_id"],
            winner_id,
            fight["player1"]["od_spent"],
            fight["player2"]["od_spent"],
            skills_json
        )

        # Check skill unlocks for both players after fight
        from db import has_skill, unlock_skill
        winner_unlocked = []
        loser_unlocked = []

        # Skill 5: Критический удар (level 5)
        if winner_player and winner_player.level >= 5:
            if not await has_skill(session, winner_id, 5):
                await unlock_skill(session, winner_id, 5)
                winner_unlocked.append("Критический удар")
        if loser_player and loser_player.level >= 5:
            if not await has_skill(session, loser_player.user_id, 5):
                await unlock_skill(session, loser_player.user_id, 5)
                loser_unlocked.append("Критический удар")

        # Skill 6: Щит титана (level 10)
        if winner_player and winner_player.level >= 10:
            if not await has_skill(session, winner_id, 6):
                await unlock_skill(session, winner_id, 6)
                winner_unlocked.append("Щит титана")
        if loser_player and loser_player.level >= 10:
            if not await has_skill(session, loser_player.user_id, 6):
                await unlock_skill(session, loser_player.user_id, 6)
                loser_unlocked.append("Щит титана")

        # Skill 7: Вампиризм (10 wins)
        if winner_player and winner_player.wins >= 10:
            if not await has_skill(session, winner_id, 7):
                await unlock_skill(session, winner_id, 7)
                winner_unlocked.append("Вампиризм")
        if loser_player and loser_player.wins >= 10:
            if not await has_skill(session, loser_player.user_id, 7):
                await unlock_skill(session, loser_player.user_id, 7)
                loser_unlocked.append("Вампиризм")

        # Skill 8: Мегаудар (level 20)
        if winner_player and winner_player.level >= 20:
            if not await has_skill(session, winner_id, 8):
                await unlock_skill(session, winner_id, 8)
                winner_unlocked.append("Мегаудар")
        if loser_player and loser_player.level >= 20:
            if not await has_skill(session, loser_player.user_id, 8):
                await unlock_skill(session, loser_player.user_id, 8)
                loser_unlocked.append("Мегаудар")

        # Skill 9: Ярость берсерка (25 wins)
        if winner_player and winner_player.wins >= 25:
            if not await has_skill(session, winner_id, 9):
                await unlock_skill(session, winner_id, 9)
                winner_unlocked.append("Ярость берсерка")
        if loser_player and loser_player.wins >= 25:
            if not await has_skill(session, loser_player.user_id, 9):
                await unlock_skill(session, loser_player.user_id, 9)
                loser_unlocked.append("Ярость берсерка")

        # Skill 10: Феникс (level 50)
        if winner_player and winner_player.level >= 50:
            if not await has_skill(session, winner_id, 10):
                await unlock_skill(session, winner_id, 10)
                winner_unlocked.append("Феникс")
        if loser_player and loser_player.level >= 50:
            if not await has_skill(session, loser_player.user_id, 10):
                await unlock_skill(session, loser_player.user_id, 10)
                loser_unlocked.append("Феникс")

    # Notify players about level ups and skill unlocks
    try:
        bot = callback.bot

        # Notify winner
        winner_msg = end_text
        if winner_level_ups:
            winner_msg += f"\n🎉 **Новый уровень:** {winner_player.level}!"
        if winner_unlocked:
            winner_msg += f"\n\n🎯 **Разблокированы навыки:**\n"
            for s in winner_unlocked:
                winner_msg += f"✅ {s}\n"
        await bot.send_message(winner_id, winner_msg)

        # Notify loser
        loser_msg = end_text
        if loser_level_ups:
            loser_msg += f"\n🎉 **Новый уровень:** {loser_player.level}!"
        if loser_unlocked:
            loser_msg += f"\n\n🎯 **Разблокированы навыки:**\n"
            for s in loser_unlocked:
                loser_msg += f"✅ {s}\n"
        await bot.send_message(loser["user_id"], loser_msg)
    except Exception as e:
        logger.warning(f"Could not notify players about level ups: {e}")
    
    # Clean up
    fight_id_to_clean = fight["fight_id"]
    if fight_id_to_clean in fight_sessions:
        del fight_sessions[fight_id_to_clean]

    # Clean up user fight map
    for uid in list(user_fight_map.keys()):
        if user_fight_map[uid] == fight_id_to_clean:
            del user_fight_map[uid]

    await state.clear()


@router.message(Command("skills"))
async def cmd_skills(message: types.Message):
    """Show player's skills and progress."""
    user_id = message.from_user.id

    async with async_session_maker() as session:
        from db import get_all_skills, get_all_skill_progress, has_skill
        
        all_skills = await get_all_skills(session)
        player_skills = await get_player_skills(session, user_id)
        player_skill_ids = {s.id for s in player_skills}
        all_progress = await get_all_skill_progress(session, user_id)
        progress_dict = {p.skill_id: p for p in all_progress}
        
        skills_text = "🎯 **Ваши навыки:**\n\n"
        
        for skill in all_skills:
            is_unlocked = skill.id in player_skill_ids
            progress = progress_dict.get(skill.id)
            
            if is_unlocked:
                skills_text += f"✅ **{skill.name}** ({skill.od_cost} ОД)\n"
                skills_text += f"   {skill.description}\n\n"
            else:
                current = progress.current_step if progress else 0
                if progress:
                    target = progress.target_steps
                else:
                    # Parse unlock condition JSON for display
                    import json
                    cond = json.loads(skill.unlock_condition)
                    target = cond.get("count", "?")

                # Build human-readable unlock requirement
                import json
                cond = json.loads(skill.unlock_condition)
                cond_type = cond.get("type", "")
                if cond_type == "always":
                    unlock_text = "Доступно всегда"
                elif cond_type == "tasks_completed":
                    unlock_text = f"Выполните {cond['count']} задач"
                elif cond_type == "low_od_tasks":
                    unlock_text = f"Выполните {cond['count']} задач с ОД 1-2"
                elif cond_type == "high_od_tasks":
                    unlock_text = f"Выполните {cond['count']} задач с ОД 5+"
                elif cond_type == "level":
                    # Hide level requirements for hard skills
                    unlock_text = "???"
                    current = "?"
                    target = "?"
                elif cond_type == "wins":
                    # Hide win requirements for hard skills
                    unlock_text = "???"
                    current = "?"
                    target = "?"
                else:
                    unlock_text = f"Прогресс: {current}/{target}"

                skills_text += f"🔒 **{skill.name}** — {current}/{target}\n"
                skills_text += f"   _{unlock_text}_\n\n"
        
        if not all_skills:
            skills_text = "📋 У вас пока нет навыков. Выполняйте задачи, чтобы открыть их!"
        
        await message.answer(skills_text)


@router.message(Command("history"))
async def cmd_history(message: types.Message):
    """Show player's fight history."""
    user_id = message.from_user.id

    async with async_session_maker() as session:
        history = await get_player_history(session, user_id, limit=5)

        if not history:
            await message.answer("📋 У вас пока нет боёв в истории.")
            return

        # Get all players for username lookup
        from sqlmodel import select
        from models import Player
        all_players_result = await session.execute(select(Player))
        all_players = {p.user_id: p.username or f"user{p.user_id}" for p in all_players_result.scalars().all()}

        history_text = "📜 **Последние бои:**\n\n"

        for i, fight in enumerate(history, 1):
            opponent_id = fight.player2_id if fight.player1_id == user_id else fight.player1_id
            opponent_name = all_players.get(opponent_id, f"user{opponent_id}")
            result = "🏆 Победа" if fight.winner_id == user_id else "❌ Поражение"

            history_text += f"{i}. {result} против {opponent_name}\n"
            history_text += f"   Дата: {fight.fight_date}\n\n"

        await message.answer(history_text)


@router.message(Command("rating"))
async def cmd_rating(message: types.Message):
    """Show player rating leaderboard."""
    async with async_session_maker() as session:
        rating = await get_rating(session, limit=10)
        
        if not rating:
            await message.answer("📋 Рейтинг пока пуст.")
            return
        
        rating_text = "🏆 **Таблица лидеров:**\n\n"
        
        for i, (player, wins) in enumerate(rating, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            rating_text += f"{medal} {i}. {player.username or f'user{player.user_id}'}\n"
            rating_text += f"    Уровень: {player.level} | Победы: {wins}\n\n"
        
        await message.answer(rating_text)
