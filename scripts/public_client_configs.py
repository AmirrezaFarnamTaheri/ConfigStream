# SPDX-License-Identifier: AGPL-3.0-or-later
"""Discover public full-client configurations through one shared contract."""

from __future__ import annotations

from pathlib import Path


def _present(paths: set[Path]) -> list[Path]:
    """Return deterministic candidates, retaining symlinks for safety checks."""
    return sorted(path for path in paths if path.is_file() or path.is_symlink())


def resolve_public_config(root: Path, path: Path) -> tuple[Path | None, str | None]:
    """Resolve a discovered config without following an unsafe path boundary."""
    try:
        resolved_root = root.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except OSError as exc:
        return None, f"client config is unavailable: {type(exc).__name__}"
    if path.is_symlink():
        return None, "client config path is a symlink"
    if not resolved.is_relative_to(resolved_root):
        return None, "client config path escapes the release root"
    return resolved, None


def discover_singbox_configs(root: Path) -> list[Path]:
    """Return every public full sing-box config, excluding proxy-record arrays."""
    paths = {
        *root.glob("singbox*.json"),
        *root.glob("chains*.json"),
        *root.glob("countries/*.json"),
        *root.glob("protocols/*.json"),
    }
    chosen = root / "chosen/singbox.json"
    if chosen.is_file() or chosen.is_symlink():
        paths.add(chosen)
    return _present({path for path in paths if ".list" not in path.stem})


def discover_mihomo_configs(root: Path) -> list[Path]:
    """Return every public full Mihomo/Clash config."""
    paths = {*root.glob("clash*.yaml")}
    chosen = root / "chosen/clash.yaml"
    if chosen.is_file() or chosen.is_symlink():
        paths.add(chosen)
    return _present(paths)
