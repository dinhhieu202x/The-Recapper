import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from datetime import datetime
import pytz
import logging

from utils.time_parser import build_datetime_range, format_local_time
from utils.constants import MAX_MESSAGES
from services.message_fetcher import fetch_messages_in_range, format_messages_for_ai
from services.summarizer import summarize
from services.formatter import build_recap_embed, build_error_embed, build_warning_embed
from services import context_db

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
        target_channel="Kênh muốn recap (Để trống = kênh hiện tại)",
    )
    async def recap(
        self,
        interaction: discord.Interaction,
        start: Optional[str] = None,
        end: Optional[str] = None,
        user: Optional[discord.Member] = None,
        date: Optional[str] = None,
        target_channel: Optional[discord.TextChannel] = None,
    ):
        # Defer ngay để tránh timeout (việc fetch + AI có thể mất vài giây)
        # Dùng ephemeral=False vì kết quả sẽ post công khai lên kênh
        await interaction.response.defer(ephemeral=False, thinking=True)

        # Ưu tiên kênh được chọn, nếu không thì lấy kênh hiện tại
        channel = target_channel or interaction.channel

        # --- Kiểm tra channel hợp lệ ---
        if not isinstance(channel, discord.TextChannel):
            await interaction.edit_original_response(
                embed=build_error_embed(
                    "Kênh không hợp lệ",
                    "Lệnh `/recap` chỉ hoạt động trong **Text Channel**.",
                )
            )
            return

        # --- Parse thời gian ---
        start_utc, end_utc = build_datetime_range(start, end, date)
        if start_utc is None or end_utc is None:
            await interaction.edit_original_response(
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
            f"[RECAP] #{channel.name} (Source) | {format_local_time(start_utc)} → "
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
        target_channel="Kênh muốn recap (Để trống = kênh hiện tại)",
    )
    async def recap_today(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
        target_channel: Optional[discord.TextChannel] = None,
    ):
        await interaction.response.defer(ephemeral=False, thinking=True)

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

        # Ưu tiên kênh được chọn
        channel = target_channel or interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.edit_original_response(embed=build_error_embed("Lỗi", "Chỉ dùng lệnh này được trong kênh chat văn bản."))
            return

        # Gọi logic fetch và recap (tận dụng code đã có)
        await self._do_recap_process(interaction, channel, start_utc, end_utc, user)

    async def _do_recap_process(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        start_utc,
        end_utc,
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
                try:
                    await interaction.edit_original_response(
                        embed=build_warning_embed(
                            "Không có tin nhắn",
                            f"Không tìm thấy tin nhắn{user_text} nào từ đầu ngày đến giờ."
                        )
                    )
                except discord.NotFound:
                    logger.warning("[RECAP] Interaction không còn tồn tại khi gửi thông báo 'Không có tin nhắn'.")
                return

            # Load context của người dùng từ DB
            user_context = await context_db.get_context(interaction.user.id)

            conversation_text = format_messages_for_ai(messages)
            summary = await summarize(conversation_text, context=user_context)

            embeds = build_recap_embed(
                summary=summary,
                channel=channel,
                start_utc=start_utc,
                end_utc=end_utc,
                message_count=len(messages),
                target_user=user,
            )

            try:
                await interaction.edit_original_response(embed=embeds[0])
            except discord.NotFound:
                # Nếu interaction bị xóa, gửi trực tiếp vào channel như phương án dự phòng
                await channel.send(content=f"{interaction.user.mention} Kết quả recap của bạn:", embed=embeds[0])
            
            for extra_embed in embeds[1:]:
                await channel.send(embed=extra_embed)

        except discord.Forbidden:
            logger.error(f"[RECAP] Thiếu quyền truy cập trong #{channel.name}")
            try:
                await interaction.edit_original_response(
                    embed=build_error_embed(
                        "Thiếu quyền truy cập",
                        f"Bot không có quyền xem hoặc đọc lịch sử tin nhắn trong kênh {channel.mention}.\n"
                        "Vui lòng kiểm tra lại quyền **View Channel** và **Read Message History**."
                    )
                )
            except discord.NotFound:
                logger.warning("[RECAP] Interaction không còn tồn tại khi gửi thông báo 'Thiếu quyền'.")
        except Exception as e:
            logger.error(f"[RECAP] Lỗi hệ thống: {e}")
            try:
                await interaction.edit_original_response(
                    embed=build_error_embed("Lỗi hệ thống", f"Đã xảy ra lỗi: `{str(e)}`")
                )
            except discord.NotFound:
                logger.warning(f"[RECAP] Interaction không còn tồn tại khi gửi báo lỗi: {e}")


    @app_commands.command(
        name="set_context",
        description="🧠 Thiết lập ngữ cảnh bổ sung cho AI khi tóm tắt (lưu theo tài khoản Discord)",
    )
    @app_commands.describe(
        context="Nội dung ngữ cảnh (VD: đây là kênh nghiệp vụ của team kỹ thuật)",
    )
    async def set_context(
        self,
        interaction: discord.Interaction,
        context: str,
    ):
        """Lưu ngữ cảnh bổ sung vào DB theo Discord ID của người dùng."""
        await context_db.set_context(
            discord_id=interaction.user.id,
            username=str(interaction.user),
            context=context,
        )
        logger.info(f"[CONTEXT] Set bởi {interaction.user} ({interaction.user.id}): {context!r}")
        embed = discord.Embed(
            title="✅ Đã lưu ngữ cảnh",
            description=f"**Ngữ cảnh của bạn:**\n```\n{context}\n```\n\nAI sẽ dùng ngữ cảnh này khi bạn gọi `/recap`.",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Lưu cho: {interaction.user.display_name} | ID: {interaction.user.id}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="clear_context",
        description="🗑️ Xóa ngữ cảnh của bạn khỏi hệ thống",
    )
    async def clear_context(self, interaction: discord.Interaction):
        """Xóa context của user hiện tại trong DB."""
        cleared = await context_db.clear_context(interaction.user.id)
        logger.info(f"[CONTEXT] Xóa bởi {interaction.user} ({interaction.user.id})")
        if cleared:
            embed = discord.Embed(
                title="🗑️ Đã xóa ngữ cảnh",
                description="Ngữ cảnh của bạn đã được xóa.\nAI sẽ tóm tắt theo chế độ mặc định.",
                color=discord.Color.orange(),
            )
        else:
            embed = discord.Embed(
                title="ℹ️ Không có ngữ cảnh",
                description="Bạn chưa thiết lập ngữ cảnh nào. Dùng `/set_context` để thêm.",
                color=discord.Color.light_grey(),
            )
        embed.set_footer(text=f"User: {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="show_context",
        description="👁️ Xem ngữ cảnh hiện tại của bạn đang được dùng cho AI",
    )
    async def show_context(self, interaction: discord.Interaction):
        """Hiển thị context hiện tại từ DB của user."""
        ctx = await context_db.get_context(interaction.user.id)
        if ctx:
            embed = discord.Embed(
                title="🧠 Ngữ cảnh của bạn",
                description=f"```\n{ctx}\n```",
                color=discord.Color.blurple(),
            )
        else:
            embed = discord.Embed(
                title="🧠 Ngữ cảnh của bạn",
                description="*(Chưa có ngữ cảnh nào)* — Dùng `/set_context` để thiết lập.",
                color=discord.Color.light_grey(),
            )
        embed.set_footer(text=f"User: {interaction.user.display_name} | ID: {interaction.user.id}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RecapCog(bot))
