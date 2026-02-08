import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from configstream.output_transport import save_json, inject_stego_key_into_frontend
from configstream.models import Proxy


@pytest.fixture
def mock_history():
    with patch("configstream.output_transport.ProxyHistoryTracker") as MockHistory:
        hist = MockHistory.return_value
        hist.get_history.return_value = {}
        yield hist


def test_save_json(tmp_path, mock_history):
    proxy = Proxy(
        config="test", protocol="vmess", address="1.1.1.1", port=443, uuid="u"
    )
    proxies = [proxy]

    out_file = tmp_path / "proxies.json"
    save_json(proxies, out_file)

    assert out_file.exists()
    assert "1.1.1.1" in out_file.read_text()


def test_save_json_compress(tmp_path, mock_history):
    proxy = Proxy(
        config="test", protocol="vmess", address="1.1.1.1", port=443, uuid="u"
    )
    proxies = [proxy]

    out_file = tmp_path / "proxies.json"
    save_json(proxies, out_file, compress=True)

    gz_file = tmp_path / "proxies.json.gz"
    assert gz_file.exists()


def test_inject_stego_key(tmp_path):
    js_file = tmp_path / "app.js"
    js_file.write_text('const SECRET_KEY = "OLD";\nconsole.log("Hi");')

    new_key = "NEW_SECRET_KEY_123"
    inject_stego_key_into_frontend(new_key, js_file)

    content = js_file.read_text()
    assert 'const SECRET_KEY = "NEW_SECRET_KEY_123";' in content
