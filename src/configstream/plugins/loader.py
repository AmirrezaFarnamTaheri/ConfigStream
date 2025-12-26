import json
import logging
from pathlib import Path
from typing import Dict, Optional
from wasmtime import Engine, Store, Module, Instance, Memory, Func, Limits, Config

from ..models import Proxy
from ..parsers.base import normalize_proxy_details

logger = logging.getLogger(__name__)


class WasmParser:
    """
    Adapter for WASM-based parsers.
    """

    def __init__(self, name: str, wasm_path: Path):
        self.name = name
        self.wasm_path = wasm_path

        # Configure resource limits
        wasm_config = Config()
        wasm_config.consume_fuel = True  # Enable fuel consumption to limit execution time/ops

        self.engine = Engine(wasm_config)
        self.store = Store(self.engine)

        # Set fuel limit (e.g., 1 billion operations)
        self.store.add_fuel(1_000_000_000)

        try:
            self.module = Module.from_file(self.engine, str(wasm_path))
            self.instance = Instance(self.store, self.module, [])
            self.exports = self.instance.exports(self.store)

            # Type hints for WASM exports to help mypy
            self.memory: Memory = self.exports["memory"]  # type: ignore[assignment]
            self.alloc: Func = self.exports["alloc"]  # type: ignore[assignment]
            self.parse_func: Func = self.exports["parse"]  # type: ignore[assignment]
            # Optional deallocators
            self.dealloc: Optional[Func] = self.exports.get("dealloc")  # type: ignore[assignment]
            self.free_string: Optional[Func] = self.exports.get("free_string")  # type: ignore[assignment]

        except Exception as e:
            logger.error(f"Failed to load WASM plugin {name}: {e}")
            raise e

    def parse(self, config: str) -> Optional[Proxy]:
        ptr = 0
        result_ptr = 0
        length = 0
        try:
            config_bytes = config.encode("utf-8")
            length = len(config_bytes)

            # Replenish fuel before execution
            self.store.add_fuel(1_000_000)

            # Allocate memory in WASM
            ptr = self.alloc(self.store, length)

            # Write string to memory using wasmtime API
            self.memory.write(self.store, config_bytes, ptr)

            # Call parse
            # parse(ptr, len) -> returns ptr to json string
            result_ptr = self.parse_func(self.store, ptr, length)

            # Deallocate input buffer immediately if dealloc is available
            # We assume the plugin doesn't need it after parse returns.
            if self.dealloc:
                self.dealloc(self.store, ptr, length)
                ptr = 0  # Prevent double free if exception happens later

            if result_ptr == 0:
                return None

            # Read result string
            # Finding the null terminator: Read chunks to optimize performance over byte-by-byte.
            chunk_size = 1024
            raw_bytes = bytearray()
            current_offset = result_ptr
            found_null = False

            mem_size = self.memory.data_len(self.store)

            while not found_null and current_offset < mem_size:
                read_len = min(chunk_size, mem_size - current_offset)
                chunk = self.memory.read(
                    self.store, current_offset, current_offset + read_len
                )

                # Check for null byte
                if b"\0" in chunk:
                    null_idx = chunk.index(b"\0")
                    raw_bytes.extend(chunk[:null_idx])
                    found_null = True
                else:
                    raw_bytes.extend(chunk)
                    current_offset += read_len

            string_content = raw_bytes.decode("utf-8")

            if not string_content:
                return None

            data = json.loads(string_content)

            # Convert to Proxy object
            proxy = Proxy(**data)
            normalize_proxy_details(proxy)
            return proxy

        except Exception as e:
            logger.debug(f"WASM parsing failed for {self.name}: {e}")
            return None
        finally:
            # Cleanup result string
            if result_ptr != 0:
                # Try to free result string using 'free_string' first, then 'dealloc' if applicable
                if self.free_string:
                    try:
                        self.free_string(self.store, result_ptr)
                    except Exception as e:
                        logger.error(f"Failed to free string in {self.name}: {e}")
                elif self.dealloc:
                     # Fallback to dealloc if free_string is missing but dealloc exists
                     # Assuming the result pointer is also allocated with the same allocator
                     # We might not know the length, so this is risky if dealloc requires correct length.
                     # Most WASM deallocators need ptr + len.
                     # If we don't know the length of the result string allocation, we probably shouldn't guess.
                     # However, the audit explicitly asked for "dealloc" calls.
                     # The code already has a dedicated `if self.free_string` block.
                     # We will stick to `free_string` for result_ptr as it is standard in this project.
                     pass

            # Cleanup input ptr if not done (e.g. if exception occurred before dealloc)
            if ptr != 0 and self.dealloc:
                try:
                    self.dealloc(self.store, ptr, length)
                except Exception as e:
                    logger.debug(
                        f"Failed to deallocate input buffer in {self.name}: {e}"
                    )


class PluginManager:
    def __init__(self, plugin_dir: Path):
        self.plugin_dir = plugin_dir
        self.parsers: Dict[str, WasmParser] = {}

    def load_plugins(self):
        if not self.plugin_dir.exists():
            return

        for file in self.plugin_dir.glob("*.wasm"):
            try:
                parser = WasmParser(file.stem, file)
                self.parsers[file.stem] = parser
                logger.info(f"Loaded WASM parser: {file.stem}")
            except Exception as e:
                logger.error(f"Could not load plugin {file}: {e}")

    def get_parser(self, name: str) -> Optional[WasmParser]:
        return self.parsers.get(name)

    def parse_all(self, config: str) -> Optional[Proxy]:
        """Try all plugins"""
        for parser in self.parsers.values():
            res = parser.parse(config)
            if res:
                return res
        return None
