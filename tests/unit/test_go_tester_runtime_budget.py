# SPDX-License-Identifier: AGPL-3.0-or-later

from configstream.testers.go_tester.manager import GoBatchTester


def test_go_tester_timeout_threshold_is_configurable(monkeypatch) -> None:
    monkeypatch.setenv("GO_TESTER_MAX_CONSECUTIVE_TIMEOUTS", "3")

    tester = GoBatchTester(binary_path="/definitely-not-present")

    assert tester._max_consecutive_timeouts == 3


def test_go_tester_result_timeout_scales_with_worker_waves() -> None:
    fast = GoBatchTester(
        binary_path="/definitely-not-present", workers=128, timeout=15
    )
    conservative = GoBatchTester(
        binary_path="/definitely-not-present", workers=20, timeout=10
    )

    assert fast._result_timeout_seconds(500) == 90.0
    assert conservative._result_timeout_seconds(500) == 280.0
    assert fast._result_timeout_seconds(1) == 60.0
    assert fast._result_timeout_seconds(0) == 60.0
