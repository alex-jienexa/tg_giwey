import os
from dotenv import load_dotenv

# Загружаем переменные из файла .env, если он существует рядом с кодом
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("ОШИБКА: Переменная окружения BOT_TOKEN не задана! Создайте файл .env на основе .env.example.")

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
except ValueError:
    raise ValueError("ОШИБКА: ADMIN_ID должен быть целым числом.")

DB_PATH = os.getenv("DB_PATH", "giveaways.db")