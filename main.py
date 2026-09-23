import asyncio
import logging
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from database import init_db

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Инициализация БД
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    print("🤖 Бот запущен и готов к тестам!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())