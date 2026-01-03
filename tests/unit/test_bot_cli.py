# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from configstream.bot_cli import start, warp, mirror, main as bot_main
from telegram import Update
from telegram.ext import ContextTypes

# Mock register_warp_account globally for this module if possible,
# or use sys.modules patch if it's imported inside the function.
# Since it's imported inside 'warp', patching 'configstream.bot_cli.register_warp_account'
# might fail if it hasn't been imported yet? No, patch should work if we target where it's used.
# But since it is a local import "from .tools.warp import register_warp_account",
# we need to patch 'configstream.tools.warp.register_warp_account' and ensure it's mocked
# before the function runs.

# BUT, the error says: <module 'configstream.bot_cli'> does not have attribute 'register_warp_account'.
# This confirms `patch("configstream.bot_cli.register_warp_account")` is wrong because it's not a global name.
# We should mock `configstream.tools.warp.register_warp_account`.


@pytest.mark.asyncio
async def test_start_command():
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot.send_message = AsyncMock()

    await start(update, context)
    context.bot.send_message.assert_called_once()
    assert "Welcome" in context.bot.send_message.call_args[1]["text"]


@pytest.mark.asyncio
async def test_warp_command():
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot.send_message = AsyncMock()

    # We need to mock the module where it is defined, so the local import picks up the mock
    with patch(
        "configstream.tools.warp.register_warp_account", new_callable=AsyncMock
    ) as mock_reg:
        mock_reg.return_value = {
            "id": "123",
            "private_key": "key",
            "address": "1.1.1.1",
        }

        # We also need to make sure configstream.tools.warp exists or is importable
        # If it doesn't exist, we might need to create a dummy one or sys.modules hack
        # Let's assume it exists based on code reading.

        await warp(update, context)

    context.bot.send_message.assert_called()
    # Check that we got success message (contains ID)
    args = context.bot.send_message.call_args[1]["text"]
    assert "ID:" in args


@pytest.mark.asyncio
async def test_warp_command_fail():
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot.send_message = AsyncMock()

    with patch(
        "configstream.tools.warp.register_warp_account", new_callable=AsyncMock
    ) as mock_reg:
        mock_reg.side_effect = Exception("Fail")
        await warp(update, context)

    # Should catch exception and send error message
    args = context.bot.send_message.call_args[1]["text"]
    assert "error" in args or "Failed" in args


@pytest.mark.asyncio
async def test_mirror_command():
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot.send_message = AsyncMock()

    await mirror(update, context)
    context.bot.send_message.assert_called_once()


def test_main_no_token():
    # Mock AppSettings to return None for TELEGRAM_BOT_TOKEN
    # Since AppSettings is imported inside main(), we patch configstream.config.AppSettings
    # effectively, or wherever it is resolved. But main() does "from configstream.config import AppSettings"
    # Actually, main() doesn't import AppSettings, run_bot does? No, I added imports in main() in previous patch?
    # Let's check bot_cli.py content. I added it to `main` and `run_bot`.
    # Wait, `main` calls `run_bot`.
    # Let's patch `configstream.config.AppSettings`.
    with patch("configstream.config.AppSettings") as mock_settings:
        mock_settings.return_value.TELEGRAM_BOT_TOKEN = None
        with patch("configstream.bot_cli.logger") as mock_logger:
            bot_main()
            mock_logger.error.assert_called_with("TELEGRAM_BOT_TOKEN not set")


def test_main_with_token():
    with (
        patch("configstream.config.AppSettings") as mock_settings,
        patch("configstream.bot_cli.ApplicationBuilder") as mock_builder,
    ):
        mock_settings.return_value.TELEGRAM_BOT_TOKEN = "fake_token"

        mock_app = MagicMock()
        mock_builder.return_value.token.return_value.build.return_value = mock_app

        bot_main()
        mock_app.run_polling.assert_called_once()
