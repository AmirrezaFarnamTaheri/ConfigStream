# SPDX-License-Identifier: AGPL-3.0-or-later
from unittest.mock import MagicMock, patch

import pytest

from configstream.constants import is_tester_infrastructure_drop_reason
from configstream.models import Proxy
from configstream.testers.python import PythonTester


@pytest.mark.asyncio
async def test_unavailable_singbox_fallback_remains_release_blocking():
    settings = MagicMock()
    tester = PythonTester(settings)
    proxy = Proxy(
        protocol="vless",
        address="1.1.1.1",
        port=443,
        config="vless://00000000-0000-0000-0000-000000000001@1.1.1.1:443",
        uuid="00000000-0000-0000-0000-000000000001",
    )

    with patch("configstream.testers.python._get_singbox_factory", return_value=None):
        result = await tester.test_via_singbox(proxy)

    assert result.is_working is False
    assert result.details["tester_error_category"] == "python_fallback_unavailable"
    assert result.details["failure_category"] == "tester_unavailable"
    assert is_tester_infrastructure_drop_reason(result.details["failure_category"])
