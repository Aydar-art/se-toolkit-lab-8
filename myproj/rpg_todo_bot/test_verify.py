"""
Simple test script to verify core functionality.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, async_session_maker, upgrade_db
from db import (
    create_player, get_player, create_task, get_user_tasks, complete_task, update_player,
    get_all_skills, get_player_skills, has_skill, unlock_skill, update_skill_progress,
    save_fight_history, get_player_history, get_rating
)
from models import Player, Task, Skill, PlayerSkill, SkillProgress, FightHistory


async def test_database():
    """Test database operations."""
    print("🧪 Testing database operations...")

    # Initialize database
    await init_db()
    print("✅ Database initialized")

    # Test player creation
    test_user_id = 12345
    async with async_session_maker() as session:
        player = await create_player(session, test_user_id, "test_user")
        assert player.user_id == test_user_id
        assert player.level == 1
        assert player.xp == 0
        assert player.hp == 25
        assert player.wins == 0  # New field
        print("✅ Player created successfully")

        # Test player retrieval
        retrieved = await get_player(session, test_user_id)
        assert retrieved is not None
        assert retrieved.user_id == test_user_id
        print("✅ Player retrieved successfully")

        # Test task creation
        task = await create_task(session, test_user_id, "Test Task", 3)
        assert task.user_id == test_user_id
        assert task.name == "Test Task"
        assert task.od == 3
        assert task.completed == False
        print("✅ Task created successfully")

        # Test task retrieval
        tasks = await get_user_tasks(session, test_user_id)
        assert len(tasks) > 0
        assert tasks[0].name == "Test Task"
        print("✅ Tasks retrieved successfully")

        # Test task completion
        await complete_task(session, task)
        assert task.completed == True
        print("✅ Task completed successfully")

        # Test player update (XP and level)
        player.xp += 30
        player.wins += 1
        await update_player(session, player)
        assert player.xp == 30
        assert player.wins == 1
        print("✅ Player updated successfully")

    print("\n✅ All database tests passed!")


async def test_skills():
    """Test skill system."""
    print("\n🧪 Testing skill system...")
    
    test_user_id = 12345
    
    async with async_session_maker() as session:
        # Test getting all skills
        skills = await get_all_skills(session)
        assert len(skills) >= 4
        print(f"✅ Retrieved {len(skills)} skills")
        
        # Test unlocking a skill
        has_skill_before = await has_skill(session, test_user_id, 2)
        if not has_skill_before:
            await unlock_skill(session, test_user_id, 2)
        has_skill_after = await has_skill(session, test_user_id, 2)
        assert has_skill_after == True
        print("✅ Skill unlocked successfully")
        
        # Test skill progress
        progress = await update_skill_progress(session, test_user_id, 3, target_steps=5, increment=1)
        assert progress.current_step == 1
        assert progress.target_steps == 5
        print("✅ Skill progress updated")
        
        # Test getting player skills
        player_skills = await get_player_skills(session, test_user_id)
        assert len(player_skills) > 0
        print(f"✅ Retrieved {len(player_skills)} player skills")
    
    print("\n✅ All skill tests passed!")


async def test_fight_history():
    """Test fight history system."""
    print("\n🧪 Testing fight history...")
    
    player1_id = 12345
    player2_id = 67890
    winner_id = player1_id
    
    async with async_session_maker() as session:
        # Save fight history
        fight = await save_fight_history(
            session,
            player1_id,
            player2_id,
            winner_id,
            player1_od_spent=5,
            player2_od_spent=3,
            skills_used_json='{"player1_skills": [1, 2], "player2_skills": [1]}'
        )
        assert fight.player1_id == player1_id
        assert fight.winner_id == winner_id
        print("✅ Fight history saved")
        
        # Retrieve fight history
        history = await get_player_history(session, player1_id, limit=5)
        assert len(history) > 0
        print(f"✅ Retrieved {len(history)} fight(s)")
        
        # Test rating
        rating = await get_rating(session, limit=10)
        assert len(rating) > 0
        print(f"✅ Retrieved rating with {len(rating)} players")
    
    print("\n✅ All fight history tests passed!")


async def test_llm_client():
    """Test LLM client (without actual API call)."""
    print("\n🧪 Testing LLM client...")
    
    from llm_client import estimate_od
    
    # Test with no API configured (should return default)
    od = await estimate_od("Test task")
    assert 1 <= od <= 8
    print(f"✅ LLM client returned valid OD: {od}")
    
    print("\n✅ LLM client test passed!")


async def test_config():
    """Test configuration loading."""
    print("\n🧪 Testing configuration...")

    from config import settings
    assert settings.bot_token is not None or settings.bot_token == "your_bot_token_here"
    assert settings.db_name == "rpg_bot.db"
    print("✅ Configuration loaded successfully")


async def main():
    """Run all tests."""
    print("=" * 50)
    print("RPG To-Do Bot - Verification Tests")
    print("=" * 50)

    try:
        await test_config()
        await test_database()
        await test_skills()
        await test_fight_history()
        await test_llm_client()

        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED!")
        print("=" * 50)
        print("\nThe bot is ready to run!")
        print("To start: python bot.py")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
