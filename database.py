import aiosqlite
import secrets
from datetime import datetime
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица сохраненных каналов пользователя
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                user_id INTEGER,
                channel_id TEXT,
                title TEXT,
                PRIMARY KEY (user_id, channel_id)
            )
        """)

        # Таблица розыгрышей (id сделан TEXT для сохранения hex-строк)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                id TEXT PRIMARY KEY,
                creator_id INTEGER,
                channel_id TEXT,
                title TEXT,
                description TEXT,
                end_time TEXT,
                winners_count INTEGER,
                is_active INTEGER DEFAULT 1,
                winner_ids TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблица участников
        await db.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                giveaway_id TEXT,
                user_id INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (giveaway_id, user_id)
            )
        """)
        await db.commit()

def generate_hex_id() -> str:
    """Генерация уникального 12-значного HEX ID"""
    return secrets.token_hex(6)

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С КАНАЛАМИ ---

async def save_channel(user_id: int, channel_id: str, title: str):
    """Сохранение или обновление названия канала для пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO channels (user_id, channel_id, title) 
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, channel_id) DO UPDATE SET title=excluded.title""",
            (user_id, str(channel_id), title)
        )
        await db.commit()

async def get_user_channels(user_id: int) -> list[dict]:
    """Получение списка сохраненных каналов пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT channel_id, title FROM channels WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{"channel_id": row[0], "title": row[1]} for row in rows]

async def delete_channel(user_id: int, channel_id: str):
    """Удаление канала из списка пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM channels WHERE user_id = ? AND channel_id = ?",
            (user_id, str(channel_id))
        )
        await db.commit()

async def create_giveaway(creator_id: int, title: str, channel_id: str, winners_count: int, end_time: str) -> str:
    giveaway_id = generate_hex_id()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO giveaways 
               (id, creator_id, title, channel_id, winners_count, end_time, is_active) 
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            (giveaway_id, creator_id, title, str(channel_id), winners_count, end_time)
        )
        await db.commit()
    return giveaway_id

async def add_participant(giveaway_id: str, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO participants (giveaway_id, user_id) VALUES (?, ?)",
                (giveaway_id, user_id)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def get_participants(giveaway_id: str) -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM participants WHERE giveaway_id = ?", 
            (giveaway_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_giveaway(giveaway_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, creator_id, title, channel_id, winners_count, end_time, is_active, winner_ids FROM giveaways WHERE id = ?",
            (giveaway_id,)
        ) as cursor:
            return await cursor.fetchone()

async def close_giveaway(giveaway_id: str, winner_ids: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE giveaways SET is_active = 0, winner_ids = ? WHERE id = ?",
            (winner_ids, giveaway_id)
        )
        await db.commit()