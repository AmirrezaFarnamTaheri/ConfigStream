import pytest

@pytest.fixture(autouse=True)
def mock_latency_checks(monkeypatch):
    """
    Automatically mock all latency checks to prevent real network calls
    and ensure predictable results in integration tests.
    """
    async def mock_measure_latency(*args, **kwargs):
        return 123.45

    # Mock the main latency measurement method in the tester
    monkeypatch.setattr(
        "configstream.testers.SingBoxTester._measure_latency_robust",
        mock_measure_latency,
    )
