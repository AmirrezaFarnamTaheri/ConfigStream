import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
from telegram import Update, User, Chat, Message, CallbackQuery
from telegram.ext import ContextTypes
import nest_asyncio

nest_asyncio.apply()

from configstream.tools.telegram_bot import ConfigStreamBot


@pytest.fixture
def mock_app_builder():
    with patch("configstream.tools.telegram_bot.ApplicationBuilder") as mock:
        yield mock


@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.message = MagicMock(spec=Message)
    return update


@pytest.fixture
def mock_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    return context


def test_bot_initialization(mock_app_builder):
    ConfigStreamBot("fake_token")
    mock_app_builder.return_value.token.assert_called_with("fake_token")
    mock_app_builder.return_value.token.return_value.build.assert_called_once()


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context, mock_app_builder):
    bot = ConfigStreamBot("fake_token")
    await bot.start(mock_update, mock_context)

    mock_context.bot.send_message.assert_called_once()
    args = mock_context.bot.send_message.call_args[1]
    assert "ConfigStream Bot" in args["text"]


@pytest.mark.asyncio
async def test_start_command_unauthorized(mock_update, mock_context, mock_app_builder):
    bot = ConfigStreamBot("fake_token", allowed_ids=[99999])
    mock_update.effective_user.id = 12345

    await bot.start(mock_update, mock_context)

    mock_context.bot.send_message.assert_called_once()
    assert "Unauthorized" in mock_context.bot.send_message.call_args[1]["text"]


@pytest.mark.asyncio
async def test_stats_command_no_metadata(
    mock_update, mock_context, mock_app_builder, fs
):
    fs.create_dir("output")

    bot = ConfigStreamBot("fake_token", output_dir=Path("output"))
    await bot.stats(mock_update, mock_context)

    mock_context.bot.send_message.assert_called_once()
    assert "Metadata not found" in mock_context.bot.send_message.call_args[1]["text"]


@pytest.mark.asyncio
async def test_stats_command_with_metadata(
    mock_update, mock_context, mock_app_builder, fs
):
    fs.create_file(
        "output/metadata.json", contents='{"total_working": 100, "total_proxies": 200}'
    )

    # aiofiles doesn't work well with pyfakefs directly. We need to mock aiofiles.open
    # However, since we are integration testing the bot logic, we can mock the file reading part.

    with patch("aiofiles.open", new_callable=MagicMock) as mock_open:
        # Setup async context manager mock
        mock_file = AsyncMock()
        mock_file.read.return_value = '{"total_working": 100, "total_proxies": 200}'
        mock_open.return_value.__aenter__.return_value = mock_file

        bot = ConfigStreamBot("fake_token", output_dir=Path("output"))
        await bot.stats(mock_update, mock_context)

        mock_context.bot.send_message.assert_called_once()
        text = mock_context.bot.send_message.call_args[1]["text"]
        assert "Working: `100` / `200`" in text


@pytest.mark.asyncio
async def test_proxies_command(mock_update, mock_context, mock_app_builder):
    bot = ConfigStreamBot("fake_token")
    await bot.proxies(mock_update, mock_context)

    mock_context.bot.send_message.assert_called_once()
    assert "Select a protocol" in mock_context.bot.send_message.call_args[1]["text"]


@pytest.mark.asyncio
async def test_button_handler(mock_context, mock_app_builder, fs):
    fs.create_file("output/by_protocol/vmess.json", contents="[]")

    bot = ConfigStreamBot("fake_token", output_dir=Path("output"))

    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.data = "proto_vmess"
    update.callback_query.message.chat_id = 12345

    await bot.button(update, mock_context)

    update.callback_query.answer.assert_called_once()
    mock_context.bot.send_document.assert_called_once()
    args = mock_context.bot.send_document.call_args[1]
    assert "vmess.json" in str(args["filename"])
