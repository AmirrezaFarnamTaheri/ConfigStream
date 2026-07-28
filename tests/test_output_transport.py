import json
from unittest.mock import patch

import pytest

from configstream.models import Proxy
from configstream.output_transport import inject_stego_key_into_frontend, save_json


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
    out_file = tmp_path / "proxies.json"
    save_json([proxy], out_file)

    data = json.loads(out_file.read_text())
    assert isinstance(data, list), "proxies.json must be array, not single object"
    assert len(data) == 1
    assert data[0]["address"] == "1.1.1.1"


def test_save_json_outputs_array_not_single_object(tmp_path, mock_history):
    proxy = Proxy(
        config="test", protocol="vmess", address="2.2.2.2", port=443, uuid="u2"
    )
    out_file = tmp_path / "single.json"
    save_json([proxy], out_file)
    data = json.loads(out_file.read_text())
    assert isinstance(data, list), "Must be array of proxies"
    assert len(data) == 1
    assert data[0]["address"] == "2.2.2.2"


def test_save_json_compress(tmp_path, mock_history):
    proxy = Proxy(
        config="test", protocol="vmess", address="1.1.1.1", port=443, uuid="u"
    )
    out_file = tmp_path / "proxies.json"
    save_json([proxy], out_file, compress=True)
    assert (tmp_path / "proxies.json.gz").exists()


def test_frontend_secret_key_is_removed_not_replaced(tmp_path):
    js_file = tmp_path / "app.js"
    js_file.write_text('const SECRET_KEY = "OLD";\nconsole.log("Hi");')

    inject_stego_key_into_frontend("NEW_SECRET_KEY_123", js_file)

    content = js_file.read_text()
    assert 'const SECRET_KEY = "";' in content
    assert "OLD" not in content
    assert "NEW_SECRET_KEY_123" not in content
