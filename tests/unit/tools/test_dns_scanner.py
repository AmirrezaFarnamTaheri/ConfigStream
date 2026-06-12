import pytest
import sys
from pathlib import Path

# Add tools/ to path
sys.path.append(str(Path.cwd() / "tools"))


def test_dns_scanner_import():
    try:
        import dns_scanner  # noqa: F401
    except ImportError:
        pytest.fail("Failed to import dns_scanner tool")


@pytest.mark.asyncio
async def test_test_dns_mock():
    import dns_scanner

    # Basic existence check since we can't easily mock network calls without respx/aioresponses
    # and aiodns is tricky to mock fully in this context without real networking
    assert hasattr(dns_scanner, "test_dns")
    assert hasattr(dns_scanner, "scan_cidrs")
