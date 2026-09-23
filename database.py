import aiosqlite
import secrets
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                winner_id INTEGER
            )
        """)
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
    return secrets.token_hex(6)

async def create_giveaway(title: str, channel_id: str, custom_id: str = None) -> str:
    giveaway_id = custom_id if custom_id else generate_hex_id()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO giveaways (id, title, channel_id) VALUES (?, ?, ?)",
            (giveaway_id, title, channel_id)
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

async def close_giveaway(giveaway_id: str, winner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE giveaways SET is_active = 0, winner_id = ? WHERE id = ?",
            (winner_id, giveaway_id)
        )
        await db.commit()

async def get_giveaway(giveaway_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, title, channel_id, is_active, winner_id FROM giveaways WHERE id = ?",
            (giveaway_id,)
        ) as cursor:
            return await cursor.fetchone()