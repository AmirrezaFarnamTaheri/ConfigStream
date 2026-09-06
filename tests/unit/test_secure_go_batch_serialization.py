# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
from unittest.mock import patch

import pytest

from configstream.testers.go_tester.secure_manager import (
    GoBatchTester,
    _StreamingGoBatchTester as BaseTester,
)


@pytest.mark.asyncio
async def test_secure_manager_serializes_and_chunks_to_worker_capacity():
    tester = object.__new__(GoBatchTester)
    tester.available = True
    tester.workers = 2
    tester._request_lock = asyncio.Lock()
    proxies = [object(), object(), object(), object(), object()]
    active = 0
    max_active = 0
    sizes = []

    async def fake_base(self, wave, check_honeypot=False):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        sizes.append(len(wave))
        await asyncio.sleep(0)
        active -= 1
        return wave

    with patch.object(BaseTester, "test_batch", new=fake_base):
        first = asyncio.create_task(tester.test_batch(proxies))
        second = asyncio.create_task(tester.test_batch(proxies[:2]))
        await asyncio.gather(first, second)

    assert sizes == [2, 2, 1, 2]
    assert max_active == 1


@pytest.mark.asyncio
async def test_secure_manager_chunks_custom_configs():
    tester = object.__new__(GoBatchTester)
    tester.available = True
    tester.workers = 2
    tester._request_lock = asyncio.Lock()
    calls = []

    async def fake_base(self, wave, check_honeypot=False):
        calls.append(len(wave))
        return {str(id(item)): True for item in wave}

    with patch.object(BaseTester, "test_custom_configs", new=fake_base):
        result = await tester.test_custom_configs([{}, {}, {}, {}, {}])

    assert calls == [2, 2, 1]
    assert len(result) == 5
