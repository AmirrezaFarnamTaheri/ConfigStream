# SPDX-License-Identifier: AGPL-3.0-or-later
"""Frontend/backend contract tests for endpoints, artifacts, and protocol ordering."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from configstream.constants import OUTPUT_PROTOCOL_ORDER

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_UTILS_PATH = REPO_ROOT / "src" / "configstream" / "server" / "utils.py"
SERVER_PROXIES_PATH = (
    REPO_ROOT / "src" / "configstream" / "server" / "routes" / "proxies.py"
)
OUTPUT_LOGIC_PATH = REPO_ROOT / "src" / "configstream" / "output" / "public_lists.py"
COMMON_UI_PATH = REPO_ROOT / "frontend" / "assets" / "js" / "common-ui.js"
DYNAMIC_DOWNLOADS_PATH = (
    REPO_ROOT / "frontend" / "assets" / "js" / "dynamic-downloads.js"
)
LAB_JS_PATH = REPO_ROOT / "frontend" / "assets" / "js" / "lab" / "state.js"


def _load_server_maps() -> tuple[dict[str, str], dict[str, str]]:
    source_utils = SERVER_UTILS_PATH.read_text(encoding="utf-8")
    tree_utils = ast.parse(source_utils)

    root_output_files: dict[str, str] = {}
    subscribe_file_map: dict[str, str] = {}

    for node in tree_utils.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ROOT_OUTPUT_FILES":
                    parsed = ast.literal_eval(node.value)
                    if isinstance(parsed, dict):
                        root_output_files = {
                            str(k): str(v)
                            for k, v in parsed.items()
                            if isinstance(k, str)
                        }

    source_proxies = SERVER_PROXIES_PATH.read_text(encoding="utf-8")
    tree_proxies = ast.parse(source_proxies)

    for node in tree_proxies.body:
        if (
            isinstance(node, ast.AsyncFunctionDef)
            and node.name == "download_subscription"
        ):
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "file_map":
                            parsed = ast.literal_eval(stmt.value)
                            if isinstance(parsed, dict):
                                subscribe_file_map = {
                                    str(k): str(v)
                                    for k, v in parsed.items()
                                    if isinstance(k, str)
                                }
                            break

    assert root_output_files, "Failed to parse ROOT_OUTPUT_FILES from utils.py"
    assert subscribe_file_map, "Failed to parse subscribe file_map from proxies.py"
    return root_output_files, subscribe_file_map


def _parse_common_ui_file_map() -> dict[str, str]:
    source = COMMON_UI_PATH.read_text(encoding="utf-8")
    block_match = re.search(r"const FILE_MAP = \{(.*?)\};", source, re.DOTALL)
    assert block_match, "FILE_MAP object not found in common-ui.js"
    block = block_match.group(1)
    pairs = re.findall(r"'([^']+)'\s*:\s*'([^']+)'", block)
    assert pairs, "No FILE_MAP key/value pairs found in common-ui.js"
    return {k: v for k, v in pairs}


def _parse_dynamic_download_files() -> set[str]:
    source = DYNAMIC_DOWNLOADS_PATH.read_text(encoding="utf-8")
    found = re.findall(r"\b(?:file|dnsFile|dnsHardenedFile):\s*\"([^\"]+)\"", source)
    return {item for item in found if item}


def _parse_lab_protocol_priority() -> list[str]:
    source = LAB_JS_PATH.read_text(encoding="utf-8")
    match = re.search(r"export const PROTOCOL_PRIORITY = \[(.*?)\];", source, re.DOTALL)
    assert match, "PROTOCOL_PRIORITY array not found in state.js"
    body = match.group(1)
    return re.findall(r"'([^']+)'", body)


def test_common_ui_subscribe_map_matches_server_formats() -> None:
    _, subscribe_map = _load_server_maps()
    common_ui_map = _parse_common_ui_file_map()

    subscribe_entries = {
        key: value
        for key, value in common_ui_map.items()
        if key.startswith("subscribe/")
    }
    assert subscribe_entries, "No subscribe/* entries found in common-ui FILE_MAP"

    for route_key, expected_filename in subscribe_entries.items():
        fmt = route_key.split("/", 1)[1]
        assert fmt in subscribe_map, f"Missing /subscribe/{fmt} in server file_map"
        assert subscribe_map[fmt] == expected_filename


def test_dynamic_download_files_are_root_outputs() -> None:
    root_output_files, _ = _load_server_maps()
    dynamic_files = _parse_dynamic_download_files()

    assert dynamic_files, "No dynamic download files parsed from dynamic-downloads.js"
    missing = dynamic_files.difference(root_output_files.keys())
    assert not missing, (
        "frontend/assets/js/dynamic-downloads.js references files not served at root: "
        f"{sorted(missing)}"
    )


def test_lab_protocol_priority_matches_backend_order() -> None:
    lab_priority = _parse_lab_protocol_priority()
    assert lab_priority == OUTPUT_PROTOCOL_ORDER


def test_country_protocol_api_contract_uses_list_json_files() -> None:
    server_source = SERVER_PROXIES_PATH.read_text(encoding="utf-8")
    output_logic_source = OUTPUT_LOGIC_PATH.read_text(encoding="utf-8")

    assert ".list.json" in server_source
    assert 'countries" / f"{country.upper()}.list.json"' in server_source
    assert 'protocols" / f"{protocol.lower()}.list.json"' in server_source
    assert 'country_dir / f"{cc}.list.json"' in output_logic_source
    assert 'proto_dir / f"{proto}.list.json"' in output_logic_source
