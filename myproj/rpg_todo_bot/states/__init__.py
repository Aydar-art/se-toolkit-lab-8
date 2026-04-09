"""
FSM states for task management and fights.
"""

from aiogram.fsm.state import State, StatesGroup


class AddTaskStates(StatesGroup):
    """States for adding a task."""
    waiting_for_name = State()
    waiting_for_od_choice = State()
    waiting_for_od = State()
    waiting_for_task_completion = State()


class FightStates(StatesGroup):
    """States for PvP duels."""
    waiting_for_opponent = State()
    selecting_skills = State()
    in_fight = State()
    choosing_action = State()
