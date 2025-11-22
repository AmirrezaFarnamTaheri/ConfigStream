"""
ConfigStream Bot CLI
Command line interface for the Telegram Bot.
"""

import os
import sys
import logging
import asyncio
import json
import random
from pathlib import Path

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

try:
    from telegram import Update
    from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
except ImportError:
    logger.error("python-telegram-bot is not installed. Please install it.")
    sys.exit(1)

from configstream.tools.warp import generate_warp_account

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Welcome to ConfigStream Bot!\nCommands:\n/warp - Generate WARP Key\n/mirror - Get latest configs"
    )

async def warp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Generating WARP key... This may take a moment.")

    try:
        # Run generation in executor
        loop = asyncio.get_running_loop()
        account = await loop.run_in_executor(None, generate_warp_account)

        if account:
             msg = (
                 f"**Cloudflare WARP+**\n"
                 f"License: `{account['license']}`\n"
                 f"ID: `{account['id']}`\n"
                 f"Data: {account['referral_count']} GB"
             )
             await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Failed to generate key.")

    except Exception as e:
        logger.error(f"Error generating WARP: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="An error occurred.")

async def mirror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # In a real deployment, this would fetch from GitHub Releases or local file if available
    # For now, we assume the bot runs where output is available or we send a link

    release_url = "https://github.com/YOUR_USER/configstream/releases/latest"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Latest configs are available here: {release_url}"
    )

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('warp', warp))
    application.add_handler(CommandHandler('mirror', mirror))

    application.run_polling()

if __name__ == '__main__':
    main()
