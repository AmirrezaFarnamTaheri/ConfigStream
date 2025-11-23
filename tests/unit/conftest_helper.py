import pytest
from configstream.models import Proxy


def create_test_proxy(
    config: str = "vmess://test",
    protocol: str = "vmess",
    address: str = "1.1.1.1",
    port: int = 443,
    is_working: bool = True,
    **kwargs,
):
    return Proxy(
        config=config,
        protocol=protocol,
        address=address,
        port=port,
        is_working=is_working,
        **kwargs,
    )


@pytest.fixture
def test_proxy():
    return create_test_proxy()
