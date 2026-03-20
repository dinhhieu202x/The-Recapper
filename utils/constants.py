"""Hằng số cấu hình toàn dự án."""

MAX_MESSAGES = 500          # Số tin nhắn tối đa fetch mỗi lần recap
MAX_AI_CHARS = 12000        # Số ký tự tối đa gửi lên AI (tránh vượt token limit)
CHUNK_SIZE = 4000           # Ký tự mỗi chunk khi cần chia nhỏ cho AI

EMBED_COLOR_PRIMARY = 0x5865F2   # Discord Blurple
EMBED_COLOR_SUCCESS = 0x57F287   # Xanh lá
EMBED_COLOR_ERROR   = 0xED4245   # Đỏ
EMBED_COLOR_WARNING = 0xFEE75C   # Vàng
