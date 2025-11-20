"""
Telegram Bot Interface for ConfigStream.
Allows users to query statistics and fetch proxies directly from Telegram.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List

import aiofiles
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
)

logger = logging.getLogger(__name__)


class ConfigStreamBot:
    def __init__(
        self,
        token: str,
        output_dir: Path = Path("output"),
        allowed_ids: Optional[List[int]] = None,
    ):
        self.token = token
        self.output_dir = output_dir
        self.allowed_ids = allowed_ids
        self.app = ApplicationBuilder().token(token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        """Register command handlers."""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.start))
        self.app.add_handler(CommandHandler("stats", self.stats))
        self.app.add_handler(CommandHandler("proxies", self.proxies))
        self.app.add_handler(CallbackQueryHandler(self.button))

    def _is_authorized(self, update: Update) -> bool:
        if not self.allowed_ids:
            return True
        user = update.effective_user
        return user is not None and user.id in self.allowed_ids

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message."""
        if not update.effective_chat:
            return

        if not self._is_authorized(update):
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text="⛔ Unauthorized."
            )
            return

        text = (
            "🚀 *ConfigStream Bot*\n\n"
            "I can help you find high-speed proxies.\n\n"
            "commands:\n"
            "/stats - Show pipeline statistics\n"
            "/proxies - Get proxy subscriptions by protocol"
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=text, parse_mode="Markdown"
        )

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pipeline statistics."""
        if not update.effective_chat:
            return

        if not self._is_authorized(update):
            return

        metadata_file = self.output_dir / "metadata.json"
        if not metadata_file.exists():
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Metadata not found. Run pipeline first.",
            )
            return

        try:
            async with aiofiles.open(metadata_file, mode="r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

            # Safe access to nested keys
            total = data.get("total_proxies", 0)
            working = data.get("total_working", 0)
            duration = data.get("duration_seconds", 0)
            updated = data.get("last_updated_utc", "Unknown")

            latency = data.get("latency_distribution", {})
            fast = latency.get("fast", 0)

            msg = (
                "📊 *Pipeline Statistics*\n\n"
                f"✅ Working: `{working}` / `{total}`\n"
                f"⏱️ Duration: `{duration:.1f}s`\n"
                f"⚡ Fast Proxies (<100ms): `{fast}`\n"
                f"🕒 Updated: `{updated}`"
            )

            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=msg, parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Stats error: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text="❌ Error reading statistics."
            )

    async def proxies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show buttons to select protocol."""
        if not update.effective_chat:
            return

        if not self._is_authorized(update):
            return

        keyboard = [
            [
                InlineKeyboardButton("VMess", callback_data="proto_vmess"),
                InlineKeyboardButton("VLESS", callback_data="proto_vless"),
            ],
            [
                InlineKeyboardButton("Trojan", callback_data="proto_trojan"),
                InlineKeyboardButton("Shadowsocks", callback_data="proto_shadowsocks"),
            ],
            [
                InlineKeyboardButton("Hysteria2", callback_data="proto_hysteria2"),
                InlineKeyboardButton("Tuic", callback_data="proto_tuic"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Select a protocol to download:",
            reply_markup=reply_markup,
        )

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks."""
        query = update.callback_query
        if not query:
            return

        await query.answer()

        if not self._is_authorized(update):
            return

        data = query.data
        if not data or not data.startswith("proto_"):
            return

        protocol = data.replace("proto_", "")
        await self._send_proxy_file(query.message.chat_id, protocol, context)  # type: ignore

    async def _send_proxy_file(
        self, chat_id: int, protocol: str, context: ContextTypes.DEFAULT_TYPE
    ):
        """Helper to send the proxy file."""
        file_path = self.output_dir / "by_protocol" / f"{protocol}.json"

        if not file_path.exists():
            await context.bot.send_message(
                chat_id=chat_id, text=f"⚠️ No proxies found for {protocol.upper()}."
            )
            return

        try:
            # For sending files, we can use the file path directly and python-telegram-bot handles it.
            # Or read with aiofiles if we want to send bytes.
            # Using path is easier for ptb, but let's stick to async safety if we were reading.
            # PTB's send_document can take a path. It will open it.
            # Since this is an I/O op, running in a thread is handled by PTB if we pass a file object?
            # Actually, passing a Path object usually makes PTB open it.
            # To be strictly async safe, we can read it into memory if small, or rely on PTB's handling.
            # Given potential file size, let's just pass the path. PTB v20 is async native.

            await context.bot.send_document(
                chat_id=chat_id,
                document=file_path,
                filename=f"{protocol}.json",
                caption=f"📂 {protocol.upper()} Proxies",
            )
        except Exception as e:
            logger.error(f"Send file error: {e}")
            await context.bot.send_message(
                chat_id=chat_id, text="❌ Error sending file."
            )

    def run(self):
        """Run the bot."""
        print("🤖 Telegram Bot Started...")
        if self.allowed_ids:
            print(f"🔒 Restricted to users: {self.allowed_ids}")
        self.app.run_polling()
