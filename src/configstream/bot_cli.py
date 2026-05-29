# SPDX-License-Identifier: AGPL-3.0-or-later
"""
ConfigStream Bot CLI
Command line interface for the Telegram Bot.
"""

from __future__ import annotations

import functools
import sys
import logging
from typing import TYPE_CHECKING, Awaitable, Callable, Optional, Set, Tuple, TypeVar

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

_HandlerT = TypeVar(
    "_HandlerT",
    bound=Callable[["Update", "ContextTypes.DEFAULT_TYPE"], Awaitable[None]],
)

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


def _load_allowed_users() -> Tuple[Set[int], bool]:
    """
    Resolve the set of authorized Telegram user IDs from settings.

    Returns ``(allowed_ids, allow_all)``. ``allow_all`` is True only when the
    operator explicitly configured ``*``. An empty/unset value yields an empty
    set with ``allow_all=False`` so the bot is locked down by default.
    """
    from configstream.config import AppSettings

    raw = (AppSettings().TELEGRAM_ALLOWED_USERS or "").strip()
    if raw == "*":
        return set(), True

    allowed: Set[int] = set()
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            allowed.add(int(token))
        except ValueError:
            logger.warning("Ignoring invalid Telegram user ID in allowlist: %r", token)
    return allowed, False


def _is_authorized(user_id: Optional[int]) -> bool:
    """Return True if ``user_id`` is permitted to invoke bot commands."""
    allowed, allow_all = _load_allowed_users()
    if allow_all:
        return True
    if user_id is None:
        return False
    return user_id in allowed


def require_authorization(handler: _HandlerT) -> _HandlerT:
    """
    Decorator enforcing per-user authorization before running a command handler.

    Unauthorized users get a short refusal message and the handler body never
    runs, preventing an unconfigured/public bot from being abused to consume
    WARP-account quota or leak release info.
    """

    @functools.wraps(handler)
    async def wrapper(
        update: "Update", context: "ContextTypes.DEFAULT_TYPE"
    ) -> None:
        user = getattr(update, "effective_user", None)
        user_id = getattr(user, "id", None)
        if not _is_authorized(user_id):
            logger.warning("Refused unauthorized bot command from user_id=%s", user_id)
            chat = getattr(update, "effective_chat", None)
            if chat is not None:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="You are not authorized to use this bot.",
                )
            return
        await handler(update, context)

    return wrapper  # type: ignore[return-value]


@require_authorization
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Welcome to ConfigStream Bot!\nCommands:\n/warp - Generate WARP Key\n/mirror - Get latest configs",
        )


@require_authorization
async def warp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Generating WARP key... This may take a moment.",
    )

    try:
        from .tools.warp import register_warp_account

        # It's async, no need for executor if async
        account = await register_warp_account()

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


@require_authorization
async def mirror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    release_url = "https://github.com/AmirrezaFarnamTaheri/ConfigStream/releases/latest"
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

    from configstream.config import AppSettings

    token = AppSettings().TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return
    run_bot(token)


def run_bot(token: str):
    if ApplicationBuilder is None:
        raise ImportError("python-telegram-bot is not installed")

    allowed, allow_all = _load_allowed_users()
    if allow_all:
        logger.warning(
            "TELEGRAM_ALLOWED_USERS='*' — the bot will accept commands from ANY "
            "user. This is NOT recommended for public bots."
        )
    elif not allowed:
        logger.warning(
            "TELEGRAM_ALLOWED_USERS is empty — the bot is locked down and will "
            "refuse all commands. Set TELEGRAM_ALLOWED_USERS to a comma-separated "
            "list of authorized user IDs to enable it."
        )

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("warp", warp))
    application.add_handler(CommandHandler("mirror", mirror))

    application.run_polling()


if __name__ == "__main__":
    main()
