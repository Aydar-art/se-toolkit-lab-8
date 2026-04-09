"""
Test LLM integration with actual API call
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_client import estimate_od
from config import settings


async def test_llm_integration():
    """Test actual LLM API call."""
    print("=" * 50)
    print("Testing LLM Integration with Qwen API")
    print("=" * 50)
    
    print(f"\n📋 Configuration:")
    print(f"  API URL: {settings.llm_api_url}")
    print(f"  Model: {settings.llm_model}")
    print(f"  API Key: {'✅ Set' if settings.llm_api_key else '❌ Not set'}")
    
    test_tasks = [
        "Сделать зарядку утром",
        "Прочитать 10 страниц книги",
        "Написать отчет по проекту",
        "Купить продукты в магазине",
        "Выучить 20 английских слов"
    ]
    
    print(f"\n🧪 Testing task evaluations:")
    for task_name in test_tasks:
        print(f"\nTask: '{task_name}'")
        od = await estimate_od(task_name)
        print(f"  → AI Evaluation: {od}/8 OD")
        
        # Interpret the difficulty
        if od <= 2:
            print(f"  → Difficulty: Easy")
        elif od <= 4:
            print(f"  → Difficulty: Medium")
        elif od <= 6:
            print(f"  → Difficulty: Hard")
        else:
            print(f"  → Difficulty: Very Hard")
    
    print("\n" + "=" * 50)
    print("✅ LLM Integration Test Complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_llm_integration())
