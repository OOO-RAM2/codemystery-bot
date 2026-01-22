import asyncio
import logging
from datetime import datetime, time
from telegram import Bot
from telegram.error import TelegramError
import google.genai as genai
import requests
from io import BytesIO
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API ключи
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID', '@codemystery52')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Инициализация API клиентов
bot = Bot(token=TELEGRAM_TOKEN)
client = genai.Client(api_key=GOOGLE_API_KEY)

# Темы для генерации контента
TOPICS = [
    "JavaScript frameworks",
    "Machine Learning в образовании",
    "Cloud Architecture",
    "Киберспорт и стриминг",
    "Data Science trends",
    "DevOps лучшие практики",
    "Фронтенд оптимизация",
    "Киберсекурность",
    "Mobile development",
    "Фиджитал в спорте",
    "Python для анализа данных",
    "Web3 и блокчейн",
    "AI/ML приложения",
    "Е-спорт турниры",
    "UI/UX дизайн",
    "Backend масштабирование",
    "Кибератлетика",
    "Game development",
    "Soft skills для IT",
    "Киберспортивные организации"
]

async def generate_content_idea():
    """Генерирует идею для поста с помощью Google Gemini"""
    
    import random
    selected_topic = random.choice(TOPICS)
    
    prompt = f"""Создай уникальную, интересную идею для поста в Telegram канал про IT образование, спорт и киберспорт.

Тема: {selected_topic}
Уровень: intermediate/advanced
Язык: Основной русский, некоторые термины на английском

Ответ должен быть в формате JSON с полями:
- "title": короткий заголовок (максимум 50 символов)
- "description": подробное описание для фото (2-3 предложения, 100-150 символов)
- "image_prompt": описание для генерации изображения на английском (детальное, 150-200 символов)
- "hashtags": список релевантных хештегов (5-7 штук)

Не добавляй markdown форматирование, только чистый JSON.
Начни ответ сразу с {{"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        response_text = response.text
        
        # Парсим JSON
        import json
        import re
        
        # Извлекаем JSON из ответа
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            content_data = json.loads(json_match.group())
            logger.info(f"✅ Идея сгенерирована: {content_data['title']}")
            return content_data
        else:
            logger.error("Не удалось парсить JSON из ответа Gemini")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации идеи: {e}")
        return None

async def generate_image_pollinations(image_prompt):
    """Генерирует изображение через Pollinations.ai (полностью бесплатно)"""
    
    try:
        # Pollinations.ai - полностью бесплатный сервис
        encoded_prompt = image_prompt.replace(" ", "%20")
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1920&height=1080&nologo=true"
        
        # Проверяем доступность
        response = requests.head(image_url, timeout=10)
        if response.status_code == 200:
            logger.info(f"✅ Изображение сгенерировано через Pollinations")
            return image_url
        else:
            logger.error(f"Pollinations вернул статус {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации изображения: {e}")
        return None

async def post_to_channel(content_data):
    """Публикует пост в Telegram канал"""
    
    try:
        if not content_data:
            logger.error("❌ Нет данных для публикации")
            return False
        
        # Генерируем изображение
        image_url = await generate_image_pollinations(content_data['image_prompt'])
        
        if not image_url:
            logger.error("❌ Не удалось сгенерировать изображение")
            return False
        
        # Формируем текст поста
        hashtags_text = " ".join(content_data['hashtags'])
        caption = f"""<b>{content_data['title']}</b>

{content_data['description']}

{hashtags_text}

#CodeMystery #ITEducation"""
        
        # Отправляем фото в канал
        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=image_url,
            caption=caption,
            parse_mode='HTML'
        )
        
        logger.info(f"✅ Пост опубликован: {content_data['title']}")
        return True
        
    except TelegramError as e:
        logger.error(f"❌ Ошибка Telegram: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка при публикации: {e}")
        return False

async def daily_post():
    """Основная функция для ежедневной публикации"""
    
    logger.info("🚀 Запуск генерации контента...")
    
    # Генерируем идею
    content_data = await generate_content_idea()
    
    if content_data:
        # Публикуем в канал
        success = await post_to_channel(content_data)
        
        if success:
            logger.info("✅ Цикл успешно завершен")
        else:
            logger.error("❌ Ошибка при публикации")
    else:
        logger.error("❌ Ошибка при генерации контента")

async def scheduler():
    """Планировщик для запуска постов в определенное время"""
    
    # Время публикации (например, 10:00 по MSK)
    publish_time = time(10, 0)
    
    logger.info(f"📅 Бот запущен. Пост будет публиковаться ежедневно в {publish_time.strftime('%H:%M')}")
    
    while True:
        now = datetime.now().time()
        
        # Проверяем, пришло ли время публикации
        if now.hour == publish_time.hour and now.minute == publish_time.minute:
            logger.info("⏰ Время публикации наступило!")
            await daily_post()
            
            # Ждем минуту, чтобы не запустить дважды
            await asyncio.sleep(60)
        
        # Проверяем каждые 30 секунд
        await asyncio.sleep(30)

async def main():
    """Главная функция"""
    
    logger.info("=" * 60)
    logger.info("🤖 CodeMystery AI Bot (с Google Gemini) запущен")
    logger.info(f"📍 Канал: {CHANNEL_ID}")
    logger.info("=" * 60)
    
    # Проверяем наличие API ключей
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден")
        return
    
    if not GOOGLE_API_KEY:
        logger.error("❌ GOOGLE_API_KEY не найден")
        return
    
    # Запускаем планировщик
    await scheduler()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⛔ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
