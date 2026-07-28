# SPDX-License-Identifier: AGPL-3.0-or-later
"""Apply the final reviewed PR531 source-only repairs."""

from pathlib import Path


def require_replace(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise SystemExit(f"required repair anchor missing: {label}")


native_path = Path("scripts/native_client_checks.py")
native = native_path.read_text(encoding="utf-8")
native = require_replace(
    native,
    "from typing import Any\n",
    "from typing import Any\n\nfrom configstream.security_validator import SecurityValidator\n",
    "native import",
)
native = require_replace(
    native,
    "    binary: Path,\n) -> dict[str, Any]:",
    "    binary_digest: str,\n) -> dict[str, Any]:",
    "native run signature",
)
native = require_replace(
    native,
    '        "binary_sha256": digest(binary),',
    '        "binary_sha256": binary_digest,',
    "native digest argument",
)
native = require_replace(
    native,
    '    output = (result.stderr or result.stdout or "").strip()\n'
    "    if len(output) > MAX_OUTPUT_CHARS:",
    '    output = (result.stderr or result.stdout or "").strip()\n'
    "    output = SecurityValidator.sanitize_log_message(output)\n"
    "    if len(output) > MAX_OUTPUT_CHARS:",
    "native sanitizer",
)
helper_anchor = "\n\ndef main() -> int:\n"
helper = (
    "\n\ndef missing_artifact(\n"
    "    core: str, relative: str, binary_digest: str\n"
    ") -> dict[str, Any]:\n"
    "    return {\n"
    '        "core": core,\n'
    '        "path": relative,\n'
    '        "status": "failed",\n'
    '        "command": None,\n'
    '        "artifact_sha256": None,\n'
    '        "binary_sha256": binary_digest,\n'
    '        "error": "required native artifact is unavailable",\n'
    "    }\n"
)
if "def missing_artifact(" not in native:
    if helper_anchor not in native:
        raise SystemExit("native helper insertion anchor missing")
    native = native.replace(helper_anchor, helper + helper_anchor, 1)
start = native.index('    if binaries["sing-box"]:')
end = native.index("    summary = {", start)
replacement = (
    "    binary_digests = {\n"
    "        name: digest(binary) if binary is not None else None\n"
    "        for name, binary in binaries.items()\n"
    "    }\n\n"
    '    singbox_binary = binaries["sing-box"]\n'
    '    singbox_digest = binary_digests["sing-box"]\n'
    "    if singbox_binary is not None and singbox_digest is not None:\n"
    '        singbox_paths = sorted(root.glob("singbox*.json"))\n'
    "        if not singbox_paths:\n"
    '            checks.append(missing_artifact("sing-box", "singbox.json", singbox_digest))\n'
    "        for path in singbox_paths:\n"
    "            checks.append(\n"
    "                run(\n"
    "                    root,\n"
    '                    [str(singbox_binary), "check", "-c", str(path)],\n'
    '                    "sing-box",\n'
    "                    path,\n"
    "                    singbox_digest,\n"
    "                )\n"
    "            )\n\n"
    '    mihomo_binary = binaries["mihomo"]\n'
    '    mihomo_digest = binary_digests["mihomo"]\n'
    "    if mihomo_binary is not None and mihomo_digest is not None:\n"
    '        mihomo_paths = sorted(root.glob("clash*.yaml"))\n'
    "        if not mihomo_paths:\n"
    '            checks.append(missing_artifact("mihomo", "clash.yaml", mihomo_digest))\n'
    "        for path in mihomo_paths:\n"
    "            checks.append(\n"
    "                run(\n"
    "                    root,\n"
    '                    [str(mihomo_binary), "-t", "-f", str(path)],\n'
    '                    "mihomo",\n'
    "                    path,\n"
    "                    mihomo_digest,\n"
    "                )\n"
    "            )\n\n"
    '    xray_binary = binaries["xray"]\n'
    '    xray_digest = binary_digests["xray"]\n'
    '    xray_path = root / "xray.json"\n'
    "    if xray_binary is not None and xray_digest is not None:\n"
    "        if xray_path.is_file() and not xray_path.is_symlink():\n"
    "            checks.append(\n"
    "                run(\n"
    "                    root,\n"
    '                    [str(xray_binary), "run", "-test", "-config", str(xray_path)],\n'
    '                    "xray",\n'
    "                    xray_path,\n"
    "                    xray_digest,\n"
    "                )\n"
    "            )\n"
    "        else:\n"
    '            checks.append(missing_artifact("xray", "xray.json", xray_digest))\n'
)
native = native[:start] + replacement + native[end:]
native = require_replace(
    native,
    '                "binary_sha256": digest(binary) if binary else None,',
    '                "binary_sha256": binary_digests[name],',
    "native tools digest",
)
native_path.write_text(native, encoding="utf-8")


gate_path = Path("scripts/release_gate.py")
gate = gate_path.read_text(encoding="utf-8")
gate = require_replace(
    gate,
    "from typing import Any\n",
    "from typing import Any, Optional, Union\n",
    "gate imports",
)
gate = require_replace(
    gate,
    "def safe_int(value: Any) -> int:",
    "def safe_int(value: Optional[Union[int, float]]) -> int:",
    "safe_int type",
)
gate = require_replace(
    gate,
    "def safe_float(value: Any) -> float:",
    "def safe_float(value: Optional[Union[int, float]]) -> float:",
    "safe_float type",
)
gate = require_replace(
    gate,
    '        if not path.is_file() or path.name == "artifact_manifest.json":\n'
    "            continue\n"
    "        relative = path.relative_to(root).as_posix()",
    "        relative = path.relative_to(root).as_posix()\n"
    '        if not path.is_file() or relative == "artifact_manifest.json":\n'
    "            continue",
    "manifest root exclusion",
)
start = gate.index("def validate_manifest(")
end = gate.index("\n\ndef validate_native_report", start)
manifest_function = '''def validate_manifest(root: Path, manifest: Any) -> list[str]:
    if not isinstance(manifest, dict):
        return ["artifact manifest must be an object"]
    files = manifest.get("files")
    if not isinstance(files, list):
        return ["artifact manifest files must be a list"]
    if len(files) > MAX_FILES:
        return ["artifact manifest exceeds file-count limit"]

    errors: list[str] = []
    try:
        actual_entries = manifest_entries(root)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    actual = {str(item["path"]): item for item in actual_entries}

    listed: set[str] = set()
    total = 0
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            errors.append("malformed artifact manifest entry")
            continue
        relative = item["path"]
        if relative in listed:
            errors.append(f"duplicate manifest path: {relative}")
            continue
        listed.add(relative)
        try:
            path = safe_path(root, relative)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if path.is_symlink():
            errors.append(f"manifest file is a symlink: {relative}")
            continue
        actual_item = actual.get(relative)
        if actual_item is None:
            if not path.is_file():
                errors.append(f"manifest file missing: {relative}")
            else:
                errors.append(f"manifest path is not public payload: {relative}")
            continue
        size = int(actual_item["size_bytes"])
        total += size
        if item.get("size_bytes") != size:
            errors.append(f"manifest size mismatch: {relative}")
        if item.get("sha256") != actual_item["sha256"]:
            errors.append(f"manifest hash mismatch: {relative}")
    if manifest.get("file_count") not in (None, len(files)):
        errors.append("artifact manifest file_count does not match files")
    if manifest.get("total_size_bytes") not in (None, total):
        errors.append("artifact manifest total_size_bytes does not match files")
    for relative in sorted(set(actual) - listed):
        errors.append(f"public file omitted from manifest: {relative}")
    return errors
'''
gate = gate[:start] + manifest_function + gate[end:]
gate_path.write_text(gate, encoding="utf-8")


storage_path = Path("src/configstream/quality/storage.py")
storage = storage_path.read_text(encoding="utf-8")
storage = require_replace(
    storage,
    "        src: sqlite3.Connection | None = None\n",
    "        src: Optional[sqlite3.Connection] = None\n",
    "storage optional type",
)
storage = require_replace(
    storage,
    "            src = sqlite3.connect(other)\n",
    "            src = sqlite3.connect(other, timeout=20)\n",
    "storage timeout",
)
storage_path.write_text(storage, encoding="utf-8")
