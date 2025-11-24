from configstream.filtering import filter_unique_endpoints
from tests.unit.conftest_helper import create_test_proxy


def test_filter_unique_endpoints():
    p1 = create_test_proxy(
        source="s1", address="1.1.1.1", port=443, protocol="vmess", is_working=True
    )
    p2 = create_test_proxy(
        source="s2", address="1.1.1.1", port=443, protocol="vmess", is_working=True
    )  # Duplicate
    p3 = create_test_proxy(
        source="s3", address="2.2.2.2", port=443, protocol="vmess", is_working=True
    )

    result = filter_unique_endpoints([p1, p2, p3])
    assert len(result) == 2
    ips = {p.address for p in result}
    assert "1.1.1.1" in ips
    assert "2.2.2.2" in ips


def test_filter_different_protocols_same_port():
    p1 = create_test_proxy(
        source="s1", address="1.1.1.1", port=443, protocol="vmess", is_working=True
    )
    p2 = create_test_proxy(
        source="s2", address="1.1.1.1", port=443, protocol="vless", is_working=True
    )  # Diff proto

    result = filter_unique_endpoints([p1, p2])
    # Wait, filter_unique_endpoints hashes (IP:Port|UUID|Path|SNI). Protocol is IGNORED.
    # So if they have same IP, Port, UUID (default ""), Path (""), SNI (""), they COLLIDE.
    # But p1 and p2 are created with create_test_proxy which sets default config.
    # We should set different UUIDs if we want them to differ, OR assert they are merged if logic ignores protocol.
    # The logic explicitly comments: "# We ignore 'remarks', 'protocol' (sometimes vmess/vless are confused but same backend)"
    # So expected is 1 if UUIDs are same.
    assert len(result) == 1


def test_filter_with_auth_diff():
    p1 = create_test_proxy(
        source="s1",
        address="1.1.1.1",
        port=443,
        protocol="vmess",
        uuid="u1",
        is_working=True,
    )
    p2 = create_test_proxy(
        source="s2",
        address="1.1.1.1",
        port=443,
        protocol="vmess",
        uuid="u2",
        is_working=True,
    )

    result = filter_unique_endpoints([p1, p2])
    # UUID makes them unique
    assert len(result) == 2
