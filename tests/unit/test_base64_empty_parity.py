# SPDX-License-Identifier: AGPL-3.0-or-later
"""An empty subscription may not contain fake node/placeholder records."""

from configstream.generators.base64 import generate_base64_subscription as public_b64
from configstream.output.subscriptions import generate_base64_subscription as output_b64


def test_empty_base64_subscription_has_exact_plaintext_parity() -> None:
    assert public_b64([]) == output_b64([]) == ""
