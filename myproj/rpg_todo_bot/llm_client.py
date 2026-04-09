"""
LLM client for estimating task difficulty (OD).
Uses external LLM API (OpenAI-compatible, YandexGPT, GigaChat, etc.)
"""

import aiohttp
import logging
from config import settings

logger = logging.getLogger(__name__)


async def estimate_od(task_name: str) -> int:
    """
    Estimate task difficulty (OD) using LLM API.
    Returns a number from 1 to 10.
    Falls back to default value (3) if API call fails.
    """
    if not settings.llm_api_url or not settings.llm_api_key:
        logger.warning("LLM API not configured, returning default OD=3")
        return 3

    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json"
            }

            prompt = (
                f"Оцени сложность следующей задачи числом от 1 до 10 (1 - очень легко, 10 - очень сложно): "
                f"\"{task_name}\". Ответь только числом."
            )

            payload = {
                "model": settings.llm_model or "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "Ты помощник для оценки сложности задач. Отвечай только числом от 1 до 10."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 10
            }

            async with session.post(
                settings.llm_api_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    logger.error(f"LLM API error: {response.status}")
                    return 3

                data = await response.json()

                # Extract response text (OpenAI-compatible format)
                if "choices" in data and len(data["choices"]) > 0:
                    text = data["choices"][0]["message"]["content"].strip()
                    # Try to parse the number
                    try:
                        od = int(text)
                        if 1 <= od <= 10:
                            logger.info(f"LLM estimated OD={od} for task: {task_name}")
                            return od
                        else:
                            logger.warning(f"LLM returned out-of-range value: {od}, using default")
                            return 3
                    except ValueError:
                        logger.warning(f"LLM returned non-numeric value: {text}, using default")
                        return 3
                else:
                    logger.warning(f"Unexpected LLM response format, using default")
                    return 3

    except aiohttp.ClientError as e:
        logger.error(f"LLM API connection error: {e}")
        return 3
    except Exception as e:
        logger.error(f"Unexpected error in LLM estimation: {e}")
        return 3
