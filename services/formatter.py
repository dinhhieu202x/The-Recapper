import discord
from datetime import datetime
from typing import Optional
import pytz
from utils.constants import EMBED_COLOR_PRIMARY, EMBED_COLOR_ERROR, EMBED_COLOR_WARNING

TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")

DISCORD_MAX_FIELD_VALUE = 1024   # Giới hạn ký tự của 1 field trong Embed
DISCORD_MAX_DESC = 4096          # Giới hạn description của Embed


def build_recap_embed(
    summary: str,
    channel: discord.TextChannel,
    start_utc: datetime,
    end_utc: datetime,
    message_count: int,
    target_user: Optional[discord.Member] = None,
) -> list[discord.Embed]:
    """
    Tạo Discord Embed chứa kết quả recap.
    Nếu nội dung tóm tắt quá dài → chia thành nhiều Embed.
    """
    start_local = start_utc.astimezone(TIMEZONE).strftime("%H:%M")
    end_local = end_utc.astimezone(TIMEZONE).strftime("%H:%M")
    date_str = start_utc.astimezone(TIMEZONE).strftime("%d/%m/%Y")
    user_str = target_user.display_name if target_user else "Tất cả thành viên"

    embeds: list[discord.Embed] = []

    # Chia summary theo số ký tự để không vượt giới hạn Discord
    summary_parts = _split_text(summary, DISCORD_MAX_DESC)

    for idx, part in enumerate(summary_parts):
        is_first = idx == 0

        embed = discord.Embed(
            color=EMBED_COLOR_PRIMARY,
        )

        if is_first:
            embed.title = "📋  RECAP CHAT"
            embed.description = f"📝  **TÓM TẮT**\n\n{part}"
            
            embed.add_field(
                name="📍 Kênh",
                value=channel.mention,
                inline=True,
            )
            embed.add_field(
                name="🕐 Khung giờ",
                value=f"`{start_local} → {end_local}`  ({date_str})",
                inline=True,
            )
            embed.add_field(
                name="👤 Xem của",
                value=f"`{user_str}`",
                inline=True,
            )
            embed.add_field(
                name="💬 Số tin nhắn",
                value=f"`{message_count} tin nhắn`",
                inline=True,
            )
        else:
            embed.title = f"📝  TÓM TẮT (tiếp theo — phần {idx + 1})"
            embed.description = part

        if idx == len(summary_parts) - 1:
            embed.set_footer(text="⚡ Recap by Antigravity Bot  •  Powered by Gemini AI")

        embeds.append(embed)

    return embeds


def build_error_embed(title: str, description: str) -> discord.Embed:
    """Tạo Embed thông báo lỗi."""
    return discord.Embed(
        title=f"❌  {title}",
        description=description,
        color=EMBED_COLOR_ERROR,
    )


def build_warning_embed(title: str, description: str) -> discord.Embed:
    """Tạo Embed cảnh báo."""
    return discord.Embed(
        title=f"⚠️  {title}",
        description=description,
        color=EMBED_COLOR_WARNING,
    )


def _split_text(text: str, max_len: int) -> list[str]:
    """Chia text thành các đoạn không vượt quá max_len ký tự, tại ranh giới dòng."""
    if len(text) <= max_len:
        return [text]

    parts: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in text.split("\n"):
        if current_len + len(line) + 1 > max_len and current:
            parts.append("\n".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line) + 1

    if current:
        parts.append("\n".join(current))

    return parts
