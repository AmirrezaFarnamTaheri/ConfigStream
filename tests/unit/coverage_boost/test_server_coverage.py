# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
from pathlib import Path

import httpx
import pytest
import sniffio
from starlette.responses import Response

from configstream.server import app


@pytest.fixture
async def async_client(monkeypatch):
    monkeypatch.setattr(sniffio, "current_async_library", lambda: "asyncio")
    import anyio._back