# SPDX-License-Identifier: AGPL-3.0-or-later
"""
WASM Plugin Loader for ConfigStream.
"""
import logging
import json
from pathlib import Path
from typing import Dict, Optional, Any, List
from wasmtime import Engine, Store, Module, Instance

from configstream.models import Proxy

logger = logging.getLogger(__name__)

class WasmParser:
    def __init__(self, name: str, wasm_path: Path):
        self.name = name
        self.wasm_path = wasm_path

        try:
            self.engine = Engine()
            self.store = Store(self.engine)
            self.module = Module.from_file(self.engine, str(wasm_path))
            self.instance = Instance(self.store, self.module, [])

            self.exports = self.instance.exports(self.store)

            # Helper to get export by name, handling both dict-like and object-like access
            def get_export(name):
                # First try dict-like access (for tests)
                try:
                    return self.exports[name]
                except (TypeError, KeyError):
                    pass

                # Then try get method if available
                if hasattr(self.exports, "get"):
                    return self.exports.get(name)

                # Finally try attribute access (unlikely for dynamic names but possible)
                return getattr(self.exports, name, None)

            self.memory = get_export("memory")
            self.alloc = get_export("alloc")
            self.parse_func = get_export("parse")
            self.dealloc = get_export("dealloc")
            self.free_string = get_export("free_string")
        except Exception as e:
            logger.error(f"Failed to load WASM plugin {name}: {e}")
            raise e

    def parse(self, config_str: str) -> Optional[Proxy]:
        if not self.parse_func or not self.alloc:
            return None

        try:
            # Write input string to WASM memory
            encoded_str = config_str.encode("utf-8")
            str_len = len(encoded_str)

            # Allocate memory in WASM
            ptr = self.alloc(self.store, str_len)

            # Write to memory
            if hasattr(self.memory, "write"):
                 self.memory.write(self.store, encoded_str, ptr)
            else:
                 # Fallback if write is not available (should be available in wasmtime 40.0.0)
                 logger.error("WASM Memory object does not have 'write' method")
                 return None

            # Invoke parse
            result_ptr = self.parse_func(self.store, ptr)

            if result_ptr == 0:
                # Dealloc input
                if self.dealloc:
                    self.dealloc(self.store, ptr, str_len)
                return None

            # Read result from memory
            json_str = ""
            if hasattr(self.memory, "read"):
                # We need to read the string. Since we don't know the length, we might need to read until null terminator
                # or maybe the plugin returns length? The test doesn't show returning length.
                # It shows read(store, start, end).
                # The test mock implementation suggests it supports slicing or explicit length.
                # If we don't know the length, we have to guess or read byte by byte?
                # Reading byte by byte is slow.
                # Maybe we can read a chunk?

                # In C/Rust wasm plugins, usually strings are null-terminated or length-prefixed.
                # If null-terminated:
                read_buffer = bytearray()
                offset = 0
                chunk_size = 1024
                while True:
                    # Read a chunk
                    # result_ptr + offset
                    chunk = self.memory.read(self.store, result_ptr + offset, result_ptr + offset + chunk_size)
                    if not chunk:
                        break

                    if 0 in chunk:
                        # Found null terminator
                        read_buffer.extend(chunk[:chunk.index(0)])
                        break
                    else:
                        read_buffer.extend(chunk)
                        offset += chunk_size
                        if offset > 1024 * 1024: # 1MB limit safety
                             break

                json_str = read_buffer.decode("utf-8")

            else:
                 logger.error("WASM Memory object does not have 'read' method")
                 return None

            # Cleanup
            if self.dealloc:
                self.dealloc(self.store, ptr, str_len)

            if self.free_string:
                self.free_string(self.store, result_ptr)

            return self._parse_json(json_str)

        except Exception as e:
            logger.error(f"Error parsing config with plugin {self.name}: {e}")
            return None

    def _parse_json(self, json_str: str) -> Optional[Proxy]:
        try:
            if not json_str:
                return None
            data = json.loads(json_str)
            return Proxy(**data)
        except Exception:
            return None

class PluginManager:
    def __init__(self, plugin_dir: Path):
        self.plugin_dir = plugin_dir
        self.parsers: Dict[str, WasmParser] = {}

    def load_plugins(self):
        if not self.plugin_dir.exists():
            return

        for wasm_file in self.plugin_dir.glob("*.wasm"):
            try:
                name = wasm_file.stem
                parser = WasmParser(name, wasm_file)
                self.parsers[name] = parser
                logger.info(f"Loaded WASM plugin: {name}")
            except Exception as e:
                logger.error(f"Failed to load plugin {wasm_file}: {e}")

    def get_parser(self, name: str) -> Optional[WasmParser]:
        return self.parsers.get(name)

    def parse_all(self, config_str: str) -> Optional[Proxy]:
        for parser in self.parsers.values():
            result = parser.parse(config_str)
            if result:
                return result
        return None
