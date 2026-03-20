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
        start="Giờ bắt đầu (Mặc định: 00:00). VD: 10h30",
        end="Giờ kết thúc (Mặc định: 23:59). VD: 12h30",
        user="Chỉ recap tin nhắn của user này (để trống = tất cả)",
        date="Ngày cần recap (Mặc định: hôm nay). VD: yesterday, 2024-03-20",
    )
    async def recap(
        self,
        interaction: discord.Interaction,
        start: Optional[str] = None,
        end: Optional[str] = None,
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

        # Gọi logic xử lý tin nhắn và AI
        await self._do_recap_process(interaction, channel, start_utc, end_utc, user)


    @app_commands.command(
        name="recap_today",
        description="📅 Tóm tắt nhanh toàn bộ chat từ 00:00 hôm nay đến bây giờ",
    )
    @app_commands.describe(
        user="Chỉ recap tin nhắn của user này (để trống = tất cả)",
    )
    async def recap_today(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
    ):
        await interaction.response.defer(ephemeral=False, thinking=True)

        from datetime import datetime, time
        import pytz
        
        # Thiết lập múi giờ
        tz = pytz.timezone("Asia/Ho_Chi_Minh")
        now_local = datetime.now(tz)
        
        # Bắt đầu từ 00:00 hôm nay (theo giờ local)
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        # Kết thúc tại thời điểm hiện tại
        end_local = now_local
        
        # Chuyển sang UTC để gọi API Discord
        start_utc = start_local.astimezone(pytz.utc)
        end_utc = end_local.astimezone(pytz.utc)

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send(embed=build_error_embed("Lỗi", "Chỉ dùng lệnh này được trong kênh chat văn bản."))
            return

        # Gọi logic fetch và recap (tận dụng code đã có)
        await self._do_recap_process(interaction, channel, start_utc, end_utc, user)

    async def _do_recap_process(
        self, 
        interaction: discord.Interaction, 
        channel: discord.TextChannel, 
        start_utc: datetime, 
        end_utc: datetime, 
        user: Optional[discord.Member]
    ):
        """Hàm helper chứa logic chính của việc recap để dùng chung cho nhiều lệnh."""
        try:
            messages = await fetch_messages_in_range(
                channel=channel,
                start_utc=start_utc,
                end_utc=end_utc,
                target_user=user,
                max_messages=MAX_MESSAGES,
            )
            
            if not messages:
                user_text = f" của **{user.display_name}**" if user else ""
                await interaction.followup.send(
                    embed=build_warning_embed(
                        "Không có tin nhắn",
                        f"Không tìm thấy tin nhắn{user_text} nào từ đầu ngày đến giờ."
                    )
                )
                return

            conversation_text = format_messages_for_ai(messages)
            summary = await summarize(conversation_text)

            embeds = build_recap_embed(
                summary=summary,
                channel=channel,
                start_utc=start_utc,
                end_utc=end_utc,
                message_count=len(messages),
                target_user=user,
            )

            await interaction.followup.send(embed=embeds[0])
            for extra_embed in embeds[1:]:
                await channel.send(embed=extra_embed)

        except Exception as e:
            logger.error(f"[RECAP] Lỗi hệ thống: {e}")
            await interaction.followup.send(embed=build_error_embed("Lỗi hệ thống", str(e)))


async def setup(bot: commands.Bot):
    await bot.add_cog(RecapCog(bot))
