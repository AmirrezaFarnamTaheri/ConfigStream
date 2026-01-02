# SPDX-License-Identifier: AGPL-3.0-or-later
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
        # args: (store, ptr, bytes)
        mock_memory.write.assert_called()
        call_args = mock_memory.write.call_args
        self.assertEqual(call_args[0][1], 100)  # ptr
        self.assertEqual(call_args[0][2], config_str.encode("utf-8"))

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

    @patch("configstream.plugins.loader.Engine")
    @patch("configstream.plugins.loader.Store")
    @patch("configstream.plugins.loader.Module")
    @patch("configstream.plugins.loader.Instance")
    def test_wasm_parser_returns_none_on_zero_result_ptr(
        self, MockInstance, MockModule, MockStore, MockEngine
    ):
        """Test that parse returns None when WASM function returns 0."""
        mock_instance = MockInstance.return_value
        mock_exports = MagicMock()
        mock_instance.exports.return_value = mock_exports

        mock_memory = MagicMock()
        mock_memory.data_len.return_value = 2048

        mock_alloc = MagicMock(return_value=100)
        mock_parse = MagicMock(return_value=0)  # Returns 0 (NULL)
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

        parser = WasmParser("test_plugin", self.mock_wasm_path)
        result = parser.parse("test://config")

        self.assertIsNone(result)

    @patch("configstream.plugins.loader.Engine")
    @patch("configstream.plugins.loader.Store")
    @patch("configstream.plugins.loader.Module")
    @patch("configstream.plugins.loader.Instance")
    def test_wasm_parser_handles_empty_json_response(
        self, MockInstance, MockModule, MockStore, MockEngine
    ):
        """Test handling of empty JSON string from WASM."""
        mock_instance = MockInstance.return_value
        mock_exports = MagicMock()
        mock_instance.exports.return_value = mock_exports

        mock_memory = MagicMock()
        mock_memory.data_len.return_value = 2048

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

        # Return empty string with null terminator
        mock_memory.read.return_value = b"\0"

        parser = WasmParser("test_plugin", self.mock_wasm_path)
        result = parser.parse("test://config")

        self.assertIsNone(result)

    @patch("configstream.plugins.loader.Engine")
    @patch("configstream.plugins.loader.Store")
    @patch("configstream.plugins.loader.Module")
    @patch("configstream.plugins.loader.Instance")
    def test_wasm_parser_handles_json_decode_error(
        self, MockInstance, MockModule, MockStore, MockEngine
    ):
        """Test handling of invalid JSON from WASM."""
        mock_instance = MockInstance.return_value
        mock_exports = MagicMock()
        mock_instance.exports.return_value = mock_exports

        mock_memory = MagicMock()
        mock_memory.data_len.return_value = 2048

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

        # Return invalid JSON
        invalid_json = b"not valid json{[}\0"
        mock_memory.read.return_value = invalid_json

        parser = WasmParser("test_plugin", self.mock_wasm_path)
        result = parser.parse("test://config")

        self.assertIsNone(result)

    @patch("configstream.plugins.loader.Engine")
    @patch("configstream.plugins.loader.Store")
    @patch("configstream.plugins.loader.Module")
    @patch("configstream.plugins.loader.Instance")
    def test_wasm_parser_without_optional_functions(
        self, MockInstance, MockModule, MockStore, MockEngine
    ):
        """Test WasmParser when optional dealloc/free_string are missing."""
        mock_instance = MockInstance.return_value
        mock_exports = MagicMock()
        mock_instance.exports.return_value = mock_exports

        mock_memory = MagicMock()
        mock_memory.data_len.return_value = 2048

        mock_alloc = MagicMock(return_value=100)
        mock_parse = MagicMock(return_value=500)

        def get_export(key, default=None):
            exports = {
                "memory": mock_memory,
                "alloc": mock_alloc,
                "parse": mock_parse,
            }
            return exports.get(key, default)

        mock_exports.__getitem__.side_effect = lambda key: get_export(key)
        mock_exports.get.side_effect = get_export

        proxy_data = {
            "config": "test://example.com:443",
            "protocol": "test",
            "address": "example.com",
            "port": 443,
        }
        proxy_json = json.dumps(proxy_data)

        def side_effect_read(store, start, end):
            offset = start - 500
            content = proxy_json.encode("utf-8") + b"\0"
            if 0 <= offset < len(content):
                length = end - start
                return content[offset : offset + length]
            return b"\0" * (end - start)

        mock_memory.read.side_effect = side_effect_read

        parser = WasmParser("test_plugin", self.mock_wasm_path)
        self.assertIsNone(parser.dealloc)
        self.assertIsNone(parser.free_string)

        result = parser.parse("test://config")
        self.assertIsNotNone(result)

    @patch("configstream.plugins.loader.Engine")
    @patch("configstream.plugins.loader.Store")
    @patch("configstream.plugins.loader.Module")
    def test_wasm_parser_loading_error(self, MockModule, MockStore, MockEngine):
        """Test WasmParser initialization failure."""
        MockModule.from_file.side_effect = Exception("Failed to load WASM module")

        with self.assertRaises(Exception):
            WasmParser("failing_plugin", self.mock_wasm_path)

    @patch("configstream.plugins.loader.Path")
    def test_plugin_manager_no_plugin_dir(self, MockPath):
        """Test PluginManager when plugin directory doesn't exist."""
        from configstream.plugins.loader import PluginManager

        mock_path = MagicMock()
        mock_path.exists.return_value = False

        manager = PluginManager(mock_path)
        manager.load_plugins()

        # Should not crash, no plugins loaded
        self.assertEqual(len(manager.parsers), 0)

    @patch("configstream.plugins.loader.Path")
    @patch("configstream.plugins.loader.WasmParser")
    def test_plugin_manager_load_plugins(self, MockWasmParser, MockPath):
        """Test PluginManager loads plugins from directory."""
        from configstream.plugins.loader import PluginManager

        mock_file1 = MagicMock()
        mock_file1.stem = "plugin1"
        mock_file2 = MagicMock()
        mock_file2.stem = "plugin2"

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.glob.return_value = [mock_file1, mock_file2]

        mock_parser1 = MagicMock()
        mock_parser2 = MagicMock()
        MockWasmParser.side_effect = [mock_parser1, mock_parser2]

        manager = PluginManager(mock_path)
        manager.load_plugins()

        self.assertEqual(len(manager.parsers), 2)
        self.assertEqual(manager.parsers["plugin1"], mock_parser1)
        self.assertEqual(manager.parsers["plugin2"], mock_parser2)

    @patch("configstream.plugins.loader.Path")
    @patch("configstream.plugins.loader.WasmParser")
    def test_plugin_manager_load_plugins_with_errors(self, MockWasmParser, MockPath):
        """Test PluginManager handles plugin loading errors gracefully."""
        from configstream.plugins.loader import PluginManager

        mock_file1 = MagicMock()
        mock_file1.stem = "good_plugin"
        mock_file2 = MagicMock()
        mock_file2.stem = "bad_plugin"

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.glob.return_value = [mock_file1, mock_file2]

        mock_parser = MagicMock()
        MockWasmParser.side_effect = [mock_parser, Exception("Failed to load")]

        manager = PluginManager(mock_path)
        manager.load_plugins()

        # Only the good plugin should be loaded
        self.assertEqual(len(manager.parsers), 1)
        self.assertEqual(manager.parsers["good_plugin"], mock_parser)

    def test_plugin_manager_get_parser_exists(self):
        """Test PluginManager.get_parser for existing plugin."""
        from configstream.plugins.loader import PluginManager

        manager = PluginManager(Path("/nonexistent"))
        mock_parser = MagicMock()
        manager.parsers["test_plugin"] = mock_parser

        result = manager.get_parser("test_plugin")
        self.assertEqual(result, mock_parser)

    def test_plugin_manager_get_parser_not_exists(self):
        """Test PluginManager.get_parser for non-existent plugin."""
        from configstream.plugins.loader import PluginManager

        manager = PluginManager(Path("/nonexistent"))

        result = manager.get_parser("nonexistent_plugin")
        self.assertIsNone(result)

    def test_plugin_manager_parse_all_no_plugins(self):
        """Test PluginManager.parse_all with no plugins loaded."""
        from configstream.plugins.loader import PluginManager

        manager = PluginManager(Path("/nonexistent"))

        result = manager.parse_all("test://config")
        self.assertIsNone(result)

    def test_plugin_manager_parse_all_no_match(self):
        """Test PluginManager.parse_all when no plugin matches."""
        from configstream.plugins.loader import PluginManager

        manager = PluginManager(Path("/nonexistent"))

        mock_parser1 = MagicMock()
        mock_parser1.parse.return_value = None
        mock_parser2 = MagicMock()
        mock_parser2.parse.return_value = None

        manager.parsers = {"plugin1": mock_parser1, "plugin2": mock_parser2}

        result = manager.parse_all("test://config")
        self.assertIsNone(result)

    def test_plugin_manager_parse_all_first_match(self):
        """Test PluginManager.parse_all returns first match."""
        from configstream.plugins.loader import PluginManager

        manager = PluginManager(Path("/nonexistent"))

        mock_proxy = Proxy(
            config="test://example.com:443",
            protocol="test",
            address="example.com",
            port=443,
        )

        mock_parser1 = MagicMock()
        mock_parser1.parse.return_value = mock_proxy
        mock_parser2 = MagicMock()
        mock_parser2.parse.return_value = None

        manager.parsers = {"plugin1": mock_parser1, "plugin2": mock_parser2}

        result = manager.parse_all("test://config")
        self.assertEqual(result, mock_proxy)
        # Should stop after first match
        mock_parser1.parse.assert_called_once()


if __name__ == "__main__":
    unittest.main()
