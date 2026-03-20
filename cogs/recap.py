import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import logging

from utils.time_parser import build_datetime_range, format_local_time
from utils.constants import MAX_MESSAGES
from services.message_fetcher import fetch_messages_in_range, format_messages_for_ai
from services.summarizer import summarize
from services.formatter import build_recap_embed, build_error_embed, build_warning_embed

logger = logging.getLogger(__name__)


class RecapCog(commands.Cog):
    """Cog xử lý lệnh /recap — tóm tắt nội dung chat theo khung giờ."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="recap",
        description="📋 Tóm tắt nội dung chat trong kênh theo khung giờ",
    )
    @app_commands.describe(
        start="Thời gian bắt đầu (VD: 10h30, 10:30, 10h)",
        end="Thời gian kết thúc (VD: 12h30, 12:30, 12h)",
        user="Chỉ recap tin nhắn của user này (để trống = tất cả)",
        date="Ngày cần recap (VD: today, yesterday, 2024-03-20). Mặc định: hôm nay",
    )
    async def recap(
        self,
        interaction: discord.Interaction,
        start: str,
        end: str,
        user: Optional[discord.Member] = None,
        date: Optional[str] = None,
    ):
        # Defer ngay để tránh timeout (việc fetch + AI có thể mất vài giây)
        # Dùng ephemeral=False vì kết quả sẽ post công khai lên kênh
        await interaction.response.defer(ephemeral=False, thinking=True)

        channel = interaction.channel

        # --- Kiểm tra channel hợp lệ ---
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send(
                embed=build_error_embed(
                    "Kênh không hợp lệ",
                    "Lệnh `/recap` chỉ hoạt động trong **Text Channel**.",
                )
            )
            return

        # --- Parse thời gian ---
        start_utc, end_utc = build_datetime_range(start, end, date)
        if start_utc is None or end_utc is None:
            await interaction.followup.send(
                embed=build_error_embed(
                    "Thời gian không hợp lệ",
                    f"Không thể hiểu định dạng thời gian:\n"
                    f"• Start: `{start}`\n"
                    f"• End: `{end}`\n\n"
                    f"**Định dạng hỗ trợ:** `10h30`, `10:30`, `10h`, `10`",
                )
            )
            return

        logger.info(
            f"[RECAP] #{channel.name} | {format_local_time(start_utc)} → "
            f"{format_local_time(end_utc)} | user={user}"
        )

        # --- Fetch messages ---
        try:
            messages = await fetch_messages_in_range(
                channel=channel,
                start_utc=start_utc,
                end_utc=end_utc,
                target_user=user,
                max_messages=MAX_MESSAGES,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                embed=build_error_embed(
                    "Thiếu quyền",
                    "Bot không có quyền đọc lịch sử tin nhắn trong kênh này.\n"
                    "Vui lòng cấp quyền **Read Message History** cho bot.",
                )
            )
            return
        except Exception as e:
            logger.error(f"[RECAP] Lỗi fetch messages: {e}")
            await interaction.followup.send(
                embed=build_error_embed(
                    "Lỗi hệ thống",
                    f"Không thể đọc tin nhắn: `{e}`",
                )
            )
            return

        # --- Không có tin nhắn ---
        if not messages:
            user_text = f" của **{user.display_name}**" if user else ""
            await interaction.followup.send(
                embed=build_warning_embed(
                    "Không có tin nhắn",
                    f"Không tìm thấy tin nhắn{user_text} trong khoảng:\n"
                    f"🕐 `{format_local_time(start_utc)}` → `{format_local_time(end_utc)}`",
                )
            )
            return

        # --- Format và gửi AI ---
        conversation_text = format_messages_for_ai(messages)
        summary = await summarize(conversation_text)

        # --- Tạo Embed và post lên kênh ---
        embeds = build_recap_embed(
            summary=summary,
            channel=channel,
            start_utc=start_utc,
            end_utc=end_utc,
            message_count=len(messages),
            target_user=user,
        )

        # Gửi embed đầu tiên qua followup, các embed tiếp theo gửi trực tiếp vào kênh
        await interaction.followup.send(embed=embeds[0])
        for extra_embed in embeds[1:]:
            await channel.send(embed=extra_embed)

        logger.info(
            f"[RECAP] Hoàn thành: {len(messages)} tin nhắn, "
            f"{len(embeds)} embed(s) gửi lên #{channel.name}"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(RecapCog(bot))
