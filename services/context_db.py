"""
Quản lý SQLite database để lưu trữ context ngữ cảnh cho từng user Discord.
Sử dụng aiosqlite để tương thích với event loop async của bot.
"""

import logging
from datetime import datetime
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

# Đường dẫn file database (cùng thư mục với bot.py)
DB_PATH = Path(__file__).parent.parent / "data" / "bot_data.db"


async def init_db() -> None:
    """Khởi tạo database và tạo bảng nếu chưa tồn tại."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_context (
                discord_id  TEXT PRIMARY KEY,
                username    TEXT,
                context     TEXT NOT NULL DEFAULT '',
                updated_at  TEXT NOT NULL
            )
        """)
        await db.commit()
    logger.info(f"✅ Database khởi tạo thành công tại: {DB_PATH}")


async def get_context(discord_id: int) -> str:
    """
    Lấy context của một user theo discord_id.
    Trả về chuỗi rỗng nếu chưa có.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT context FROM user_context WHERE discord_id = ?",
            (str(discord_id),),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else ""


async def set_context(discord_id: int, username: str, context: str) -> None:
    """
    Lưu hoặc cập nhật context của một user.
    Dùng UPSERT (INSERT OR REPLACE) để xử lý cả tạo mới lẫn cập nhật.
    """
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_context (discord_id, username, context, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET
                username   = excluded.username,
                context    = excluded.context,
                updated_at = excluded.updated_at
            """,
            (str(discord_id), username, context, now),
        )
        await db.commit()
    logger.info(f"[DB] Context đã lưu cho user {username} ({discord_id})")


async def clear_context(discord_id: int) -> bool:
    """
    Xóa context của một user (set về rỗng).
    Trả về True nếu có record để xóa, False nếu user chưa có context.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM user_context WHERE discord_id = ?",
            (str(discord_id),),
        ) as cursor:
            exists = await cursor.fetchone()

        if exists:
            now = datetime.utcnow().isoformat()
            await db.execute(
                "UPDATE user_context SET context = '', updated_at = ? WHERE discord_id = ?",
                (now, str(discord_id)),
            )
            await db.commit()
            logger.info(f"[DB] Context đã xóa cho user ID {discord_id}")
            return True
        return False


async def list_all_contexts() -> list[dict]:
    """
    Lấy danh sách tất cả users đang có context (dùng cho admin).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT discord_id, username, context, updated_at FROM user_context WHERE context != '' ORDER BY updated_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
