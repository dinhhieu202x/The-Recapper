"""
Entry point của Discord Recap Bot.
Chạy: python bot.py
"""

import discord
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# Load biến môi trường từ .env
load_dotenv()

# ─── Flask Web Server (Dành cho Render) ──────────────────────────────────────────
app = Flask("")

@app.route("/")
def home():
    return "I am alive!"

def run_web():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("bot")

# ─── Config ────────────────────────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
if not TOKEN:
    logger.critical("❌ Thiếu DISCORD_BOT_TOKEN trong file .env!")
    sys.exit(1)

# ─── Intents ───────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True   # Cần bật trong Discord Developer Portal
intents.messages = True
intents.guilds = True
intents.members = True


# ─── Bot Setup ─────────────────────────────────────────────────────────────────
class RecapBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",   # Prefix không dùng, nhưng bắt buộc phải có
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self):
        """Gọi khi bot khởi động — load các Cog và sync slash commands."""
        logger.info("🔧 Đang load các Cog...")

        await self.load_extension("cogs.recap")
        logger.info("✅ Đã load: cogs.recap")

        # Sync slash commands lên Discord (toàn cầu)
        synced = await self.tree.sync()
        logger.info(f"✅ Đã sync {len(synced)} slash command(s) lên Discord.")

    async def on_ready(self):
        logger.info("─" * 50)
        logger.info(f"🤖 Bot đã online: {self.user} (ID: {self.user.id})")
        logger.info(f"📡 Đang phục vụ {len(self.guilds)} server(s)")
        logger.info("─" * 50)

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/recap — Tóm tắt chat",
            )
        )

    async def on_command_error(self, ctx, error):
        logger.error(f"Lỗi command: {error}")


import asyncio
import logging
import os
import sys

# ─── Main ──────────────────────────────────────────────────────────────────────
async def main():
    keep_alive()  # Khởi động web server cho Render
    bot = RecapBot()
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
