"""
Task data access operations.
Following the pattern from backend/db/items.py
"""

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Task
from typing import List, Optional
from datetime import date
import logging

logger = logging.getLogger(__name__)


async def create_task(session: AsyncSession, user_id: int, name: str, od: int) -> Task:
    """Create a new task."""
    task = Task(user_id=user_id, name=name, od=od)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def get_user_tasks(session: AsyncSession, user_id: int) -> List[Task]:
    """Get all incomplete tasks for a user from today."""
    from datetime import date
    result = await session.execute(
        select(Task).where(
            Task.user_id == user_id,
            Task.completed == False,
            Task.created_date == date.today()
        ).order_by(Task.id)
    )
    return result.scalars().all()


async def get_task(session: AsyncSession, task_id: int) -> Optional[Task]:
    """Get task by ID."""
    result = await session.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def complete_task(session: AsyncSession, task: Task) -> Task:
    """Mark task as completed."""
    task.completed = True
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task
