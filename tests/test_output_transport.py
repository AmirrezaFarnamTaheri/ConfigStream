import pytest
from unittest.mock import patch
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
    # CRITICAL: Output must be JSON array (set of proxies), never single object
    import json

    data = json.loads(out_file.read_text())
    assert isinstance(data, list), "proxies.json must be array, not single object"
    assert len(data) == 1


def test_save_json_outputs_array_not_single_object(tmp_path, mock_history):
    """Ensure single proxy is still output as JSON array [{...}], never {...}."""
    proxy = Proxy(
        config="test", protocol="vmess", address="2.2.2.2", port=443, uuid="u2"
    )
    out_file = tmp_path / "single.json"
    save_json([proxy], out_file)
    import json

    data = json.loads(out_file.read_text())
    assert isinstance(data, list), "Must be array of proxies"
    assert len(data) == 1
    assert data[0]["address"] == "2.2.2.2"


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
