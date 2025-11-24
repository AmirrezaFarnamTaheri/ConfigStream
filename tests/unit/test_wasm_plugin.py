import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import json

from configstream.plugins.loader import WasmParser
from configstream.auto_detect import auto_detect_and_parse
from configstream.models import Proxy


class TestWasmPlugin(unittest.TestCase):
    def setUp(self):
        self.mock_wasm_path = Path("dummy.wasm")

    @patch("configstream.plugins.loader.Engine")
    @patch("configstream.plugins.loader.Store")
    @patch("configstream.plugins.loader.Module")
    @patch("configstream.plugins.loader.Instance")
    def test_wasm_parser_loading(self, MockInstance, MockModule, MockStore, MockEngine):
        # Setup mocks
        mock_instance = MockInstance.return_value
        mock_exports = MagicMock()
        mock_instance.exports.return_value = mock_exports

        # Mock memory and functions
        mock_memory = MagicMock()
        mock_memory.data_len.return_value = 10000

        mock_exports.__getitem__.side_effect = lambda key: {
            "memory": mock_memory,
            "alloc": MagicMock(return_value=123),
            "parse": MagicMock(return_value=456),  # result ptr
            "dealloc": MagicMock(),
            "free_string": MagicMock(),
        }.get(key)

        parser = WasmParser("test_plugin", self.mock_wasm_path)

        self.assertIsNotNone(parser.engine)
        self.assertIsNotNone(parser.store)
        self.assertIsNotNone(parser.instance)
        self.assertEqual(parser.alloc.return_value, 123)
        self.assertIsNotNone(parser.free_string)

    @patch("configstream.plugins.loader.Engine")
    @patch("configstream.plugins.loader.Store")
    @patch("configstream.plugins.loader.Module")
    @patch("configstream.plugins.loader.Instance")
    def test_wasm_parser_execution(
        self, MockInstance, MockModule, MockStore, MockEngine
    ):
        # Setup mocks to simulate successful parsing
        mock_instance = MockInstance.return_value
        mock_exports = MagicMock()
        mock_instance.exports.return_value = mock_exports

        mock_memory = MagicMock()
        mock_memory.data_len.return_value = 2048

        # Setup exports
        mock_alloc = MagicMock(return_value=100)
        mock_parse = MagicMock(return_value=500)
        mock_dealloc = MagicMock()
        mock_free_string = MagicMock()

        def get_export(key, default=None):
            return {
                "memory": mock_memory,
                "alloc": mock_alloc,
                "parse": mock_parse,
                "dealloc": mock_dealloc,
                "free_string": mock_free_string,
            }.get(key, default)

        mock_exports.__getitem__.side_effect = lambda key: get_export(key)
        mock_exports.get.side_effect = get_export

        # Prepare the result
        proxy_data = {
            "config": "vless://example.com:443?uuid=test-uuid",
            "protocol": "vless",
            "address": "example.com",
            "port": 443,
            "uuid": "test-uuid",
            "remarks": "WASM Proxy",
        }
        proxy_json = json.dumps(proxy_data)

        # Mock memory.read to return the JSON string + null terminator
        # The parser reads in chunks. We need to make sure it gets the data.
        # It calls read(store, start, end)

        def side_effect_read(store, start, end):
            # If reading from 500 (result ptr)
            offset = start - 500
            content = proxy_json.encode("utf-8") + b"\0"
            if 0 <= offset < len(content):
                length = end - start
                return content[offset : offset + length]
            return b"\0" * (end - start)  # Default empty

        mock_memory.read.side_effect = side_effect_read

        parser = WasmParser("test_plugin", self.mock_wasm_path)

        config_str = "vless://example.com:443?uuid=test-uuid"
        result = parser.parse(config_str)

        self.assertIsNotNone(result)
        self.assertEqual(result.protocol, "vless")
        self.assertEqual(result.remarks, "WASM Proxy")

        # Verify alloc was called
        mock_alloc.assert_called()

        # Verify write was called
        # args: (store, bytes, ptr)
        mock_memory.write.assert_called()
        call_args = mock_memory.write.call_args
        self.assertEqual(call_args[0][1], config_str.encode("utf-8"))
        self.assertEqual(call_args[0][2], 100)  # ptr

        # Verify parse called
        mock_parse.assert_called()

        # Verify dealloc called for input
        mock_dealloc.assert_called_with(
            parser.store, 100, len(config_str.encode("utf-8"))
        )

        # Verify free_string called for result
        mock_free_string.assert_called_with(parser.store, 500)

    @patch("configstream.auto_detect.PLUGIN_MANAGER")
    def test_auto_detect_uses_plugins(self, mock_plugin_manager):
        config = "juicity://user:pass@1.1.1.1:443"
        mock_proxy = Proxy(
            config=config,
            protocol="juicity",
            address="1.1.1.1",
            port=443,
            uuid="abc",
            remarks="Plugin",
        )
        mock_plugin_manager.parse_all.return_value = mock_proxy

        result = auto_detect_and_parse(config)

        self.assertEqual(result, mock_proxy)
        mock_plugin_manager.parse_all.assert_called_with(config)


if __name__ == "__main__":
    unittest.main()
