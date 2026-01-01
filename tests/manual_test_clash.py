
import sys
import os
# Ensure src is in path
sys.path.insert(0, os.path.abspath("src"))

from configstream.models import Proxy
from configstream.converters.clash import to_clash_proxy

def run_clash_modern_manual():
    # Hysteria2
    hy2 = Proxy(
        config="hy2://",
        protocol="hysteria2",
        address="1.1.1.1",
        port=443,
        uuid="pass123",
        details={
            "sni": "google.com",
            "allowInsecure": True,
            "obfs": "salamander",
            "obfs-password": "secret",
        },
        is_working=True
    )
    clash_hy2 = to_clash_proxy(hy2)
    assert clash_hy2["type"] == "hysteria2"
    assert clash_hy2["password"] == "pass123"
    assert clash_hy2["sni"] == "google.com"
    assert clash_hy2["skip-cert-verify"] is True
    assert clash_hy2["obfs"] == "salamander"
    print("Hysteria2 passed")

    # TUIC
    tuic = Proxy(
        config="tuic://",
        protocol="tuic",
        address="2.2.2.2",
        port=8443,
        uuid="uuid-tuic",
        details={
            "password": "pass",
            "congestion_controller": "bbr",
            "allowInsecure": False
        },
        is_working=True
    )
    clash_tuic = to_clash_proxy(tuic)
    assert clash_tuic["type"] == "tuic"
    assert clash_tuic["uuid"] == "uuid-tuic"
    assert clash_tuic["congestion-controller"] == "bbr"
    print("TUIC passed")

    # WireGuard
    wg = Proxy(
        config="wg://",
        protocol="wireguard",
        address="3.3.3.3",
        port=51820,
        details={
            "private_key": "priv",
            "peer_public_key": "pub",
            "local_address": ["10.0.0.1"],
            "mtu": 1280
        },
        is_working=True
    )
    clash_wg = to_clash_proxy(wg)
    assert clash_wg["type"] == "wireguard"
    assert clash_wg["ip"] == "10.0.0.1"
    assert clash_wg["private-key"] == "priv"
    assert clash_wg["mtu"] == 1280
    print("WireGuard passed")

if __name__ == "__main__":
    try:
        run_clash_modern_manual()
        print("All manual tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
