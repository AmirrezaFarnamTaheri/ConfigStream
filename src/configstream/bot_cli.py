"""
ConfigStream Bot CLI
Command line interface for the Telegram Bot.
"""

from __future__ import annotations

import os
import sys
import logging
from typing import TYPE_CHECKING

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

try:
    from telegram import Update  # noqa: F811
    from telegram.ext import (
        ApplicationBuilder,
        CommandHandler,
    )

    if not TYPE_CHECKING:
        from telegram.ext import ContextTypes  # noqa: F811
except ImportError:
    logger.warning(
        "python-telegram-bot is not installed. Bot features will be disabled."
    )
    Update = None  # type: ignore
    ApplicationBuilder = None  # type: ignore
    ContextTypes = None  # type: ignore
    CommandHandler = None  # type: ignore


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Welcome to ConfigStream Bot!\nCommands:\n/warp - Generate WARP Key\n/mirror - Get latest configs",
        )


async def warp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Generating WARP key... This may take a moment.",
    )

    try:
        # Run generation in executor
        # Note: generate_warp_account returns account dict with license, id, referral_count
        # We need to fix the import if it's missing, or mock it if tools.warp doesn't have it
        # Looking at tools/warp.py, it has register_warp_account but it returns different keys.
        # It returns {id, private_key, ...}. It does NOT return license or referral_count.
        # This CLI seems to expect a different warp generator (maybe legacy).
        # We'll use register_warp_account but adapt the message.

        from .tools.warp import register_warp_account

        account = (
            await register_warp_account()
        )  # It's async, no need for executor if async

        if account:
            msg = (
                f"**Cloudflare WARP Device**\n"
                f"ID: `{account.get('id')}`\n"
                f"Private Key: `{account.get('private_key')}`\n"
                f"IPv4: `{account.get('address')}`"
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=msg, parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text="Failed to generate key."
            )

    except Exception as e:
        logger.error(f"Error generating WARP: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="An error occurred."
        )


async def mirror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    release_url = "https://github.com/YOUR_USER/configstream/releases/latest"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Latest configs are available here: {release_url}",
    )


def main():
    if ApplicationBuilder is None:
        logger.error(
            "python-telegram-bot is not installed. Please install it to use the bot CLI."
        )
        sys.exit(1)

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return
    run_bot(token)


def run_bot(token: str):
    if ApplicationBuilder is None:
        raise ImportError("python-telegram-bot is not installed")

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("warp", warp))
    application.add_handler(CommandHandler("mirror", mirror))

    application.run_polling()


if __name__ == "__main__":
    main()
