import discord
from datetime import datetime
from typing import Optional
import pytz

TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")


async def fetch_messages_in_range(
    channel: discord.TextChannel,
    start_utc: datetime,
    end_utc: datetime,
    target_user: Optional[discord.Member] = None,
    max_messages: int = 500,
) -> list[discord.Message]:
    """
    Fetch tất cả tin nhắn trong channel từ start_utc đến end_utc.
    Nếu target_user được chỉ định, chỉ trả về tin nhắn của user đó.

    Discord API trả về message theo thứ tự MỚI nhất trước (newest first),
    nên ta dùng `after` và `before` để giới hạn phạm vi.
    """
    messages: list[discord.Message] = []
    fetched_count = 0

    # history() nhận `after` và `before` là đối tượng datetime UTC hoặc Snowflake
    async for msg in channel.history(
        limit=max_messages,
        after=start_utc,
        before=end_utc,
        oldest_first=True,  # Lấy theo thứ tự cũ → mới (tự nhiên hơn khi đọc)
    ):
        fetched_count += 1

        # Bỏ qua tin nhắn của bot
        if msg.author.bot:
            continue

        # Bỏ qua tin nhắn là slash command (thường bắt đầu bằng /)
        if msg.content.startswith("/"):
            continue

        # Lọc theo user nếu có
        if target_user and msg.author.id != target_user.id:
            continue

        messages.append(msg)

    return messages


def format_messages_for_ai(messages: list[discord.Message]) -> str:
    """
    Chuyển danh sách discord.Message thành chuỗi text dễ đọc để gửi AI.
    Format: [HH:MM] Username: Nội dung tin nhắn
    """
    lines = []
    for msg in messages:
        local_time = msg.created_at.astimezone(TIMEZONE)
        time_str = local_time.strftime("%H:%M")
        author = msg.author.display_name

        content = msg.content.strip()

        # Xử lý trường hợp tin nhắn có attachment (ảnh, file)
        if not content and msg.attachments:
            content = f"[Đính kèm {len(msg.attachments)} file]"
        elif msg.attachments:
            content += f" [+{len(msg.attachments)} file đính kèm]"

        # Bỏ qua tin nhắn rỗng sau khi làm sạch
        if not content:
            continue

        lines.append(f"[{time_str}] {author}: {content}")

    return "\n".join(lines)
