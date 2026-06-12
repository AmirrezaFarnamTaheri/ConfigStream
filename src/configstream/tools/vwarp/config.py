# SPDX-License-Identifier: AGPL-3.0-or-later
import copy
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from configstream.security_validator import SecurityValidator
from .constants import (
    DEFAULT_WARP_ENDPOINT,
    PSIPHON_COUNTRY_CODES,
    MASQUE_NOIZE_PRESETS,
    ATOMICNOIZE_PRESETS,
    VWARP_VERSION,
)

logger = logging.getLogger(__name__)

def build_vwarp_config(
    bind: str = "127.0.0.1:8086",
    endpoint: str = DEFAULT_WARP_ENDPOINT,
    key: Optional[str] = None,
    dns: str = "1.1.1.1",
    masque_preset: Optional[str] = None,
    atomicnoize_preset: Optional[str] = None,
    psiphon_country: Optional[str] = None,
    proxy: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Builds a complete vwarp JSON configuration file.
    """
    config: Dict[str, Any] = {
        "bind": bind,
        "endpoint": endpoint,
        "dns": dns,
    }
    if key:
        config["key"] = key
    if proxy:
        config["proxy"] = proxy

    # MASQUE configuration
    if masque_preset:
        preset_data = MASQUE_NOIZE_PRESETS.get(masque_preset, {})
        config["masque"] = {
            "enabled": True,
            "preferred": True,
            "config": dict(preset_data),
        }
    else:
        config["masque"] = {"enabled": False}

    # WireGuard + AtomicNoize configuration
    atomicnoize_data: Dict[str, Any] = {}
    if atomicnoize_preset:
        atomicnoize_data = dict(ATOMICNOIZE_PRESETS.get(atomicnoize_preset, {}))
    config["wireguard"] = {
        "enabled": True,
        "reserved": "0,0,0",
        "atomicnoize": atomicnoize_data if atomicnoize_data else {},
    }

    # Psiphon integration
    if psiphon_country:
        country = psiphon_country.upper()
        if country not in PSIPHON_COUNTRY_CODES:
            logger.warning(
                "Psiphon country '%s' not in known supported list; "
                "proceeding anyway.",
                country,
            )
        config["psiphon"] = {"enabled": True, "country": country}
    else:
        config["psiphon"] = {"enabled": False, "country": "US"}

    return config

def generate_masque_config(preset: str = "gfw") -> Dict[str, Any]:
    """Generates a vwarp MASQUE configuration dict for the given preset."""
    return build_vwarp_config(masque_preset=preset)

def get_config_extra_flags(config: Dict[str, Any]) -> List[str]:
    """Determine any extra CLI flags required by the config."""
    force_masque = os.environ.get("VWARP_FORCE_MASQUE", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if force_masque:
        return ["--masque"]
    masque_cfg = config.get("masque")
    if isinstance(masque_cfg, dict) and masque_cfg.get("enabled") is True:
        return ["--masque"]
    return []

def sanitize_config_for_binary(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove config fields rejected by vwarp v2.1.x (schema divergence).
    """
    out = copy.deepcopy(config)
    # wireguard.atomicnoize: remove JunkInterval (binary uses different schema)
    wg = out.get("wireguard")
    if isinstance(wg, dict):
        ano = wg.get("atomicnoize")
        if isinstance(ano, dict):
            ano = dict(ano)
            ano.pop("JunkInterval", None)
            out["wireguard"] = dict(wg)
            out["wireguard"]["atomicnoize"] = ano
    # masque: remove enabled/preferred (binary uses --masque CLI flag instead)
    masque = out.get("masque")
    if isinstance(masque, dict):
        masque = dict(masque)
        masque.pop("enabled", None)
        masque.pop("preferred", None)
        out["masque"] = masque
    return out

def write_temp_config(
    config: Dict[str, Any]
) -> Tuple[Optional[Path], List[str]]:
    """Writes config to temp file and returns (path, extra_flags)."""
    tmp_dir = Path(tempfile.gettempdir())
    tmp_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="vwarp-config-", suffix=".json")
    os.close(fd)
    tmp_path = Path(tmp_name)

    # Sanitize config for Vwarp binary compatibility
    write_config = copy.deepcopy(config)
    write_config.pop("version", None)
    write_config.pop("metadata", None)
    write_config.pop(
        "test_url", None
    )  # Explicitly remove test_url to avoid parse errors

    # v2.2.1+ supports full config; v2.1.x rejects JunkInterval, masque.enabled/preferred
    # For now we use the latest version default from constants
    version = os.environ.get("VWARP_VERSION", VWARP_VERSION)
    from .binary import _parse_version
    if _parse_version(version) < _parse_version("v2.2.1"):
        write_config = sanitize_config_for_binary(write_config)

    try:
        tmp_path.write_text(json.dumps(write_config), encoding="utf-8")
    except OSError as exc:
        logger.error(
            "Failed to write Vwarp config: %s",
            SecurityValidator.sanitize_log_message(str(exc)),
        )
        return None, []

    extra_flags = get_config_extra_flags(config)
    return tmp_path, extra_flags
