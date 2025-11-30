"""
Output Logic Module.
Orchestrates the generation of various output formats and file structures.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Any, Set

from .models import Proxy
from .intelligence.washer import ProxyWasher, generate_smart_chains
from .utils import AtomicFileWriter
from .output_transport import save_json
from .output_generators import generate_split_outputs
import json

logger = logging.getLogger(__name__)


def generate_categorized_outputs(
    proxies: List[Proxy],
    output_dir: Path,
    washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    washed_ids: Optional[Set[str]] = None,
    smart_chains: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Path]:
    """
    Generate files organized by protocol and country.
    """
    files: Dict[str, Path] = {}

    # 1. Master List (Standard)
    master_file = output_dir / "proxies.json"
    save_json(proxies, master_file, compress=True)
    files["master"] = master_file

    # 1.1 Generate Advanced (Washed & Chained) Proxies
    # If not provided, generate them (backward compatibility / standalone use)
    if washed_outbounds is None or washed_ids is None:
        washer = ProxyWasher(os.getenv("WARP_KEY_POOL", "[]"))
        washed_outbounds, washed_ids = washer.wash_batch(proxies)

    if smart_chains is None:
        smart_chains = generate_smart_chains(proxies)

    # Save Chains separately (Sing-box only)
    chains_file = output_dir / "singbox-chains.json"
    all_chains = []
    for k, v in smart_chains.items():
        all_chains.extend(v)

    chain_config = {"outbounds": all_chains}
    AtomicFileWriter.write_text(chains_file, json.dumps(chain_config, indent=2))
    files["chains"] = chains_file
    logger.info(f"Generated singbox-chains.json with {len(all_chains)} chains.")

    # 2. By Protocol
    proto_dir = output_dir / "by_protocol"
    proto_dir.mkdir(exist_ok=True)

    by_proto: Dict[str, List[Proxy]] = {}
    for p in proxies:
        proto = p.protocol.lower()
        if proto not in by_proto:
            by_proto[proto] = []
        by_proto[proto].append(p)

    for proto, subset in by_proto.items():
        fpath = proto_dir / f"{proto}.json"
        save_json(subset, fpath)
        files[f"proto_{proto}"] = fpath
    logger.info(f"Generated {len(by_proto)} protocol-specific files.")

    # 3. By Country
    country_dir = output_dir / "by_country"
    country_dir.mkdir(exist_ok=True)

    by_country: Dict[str, List[Proxy]] = {}
    for p in proxies:
        cc = (p.country_code or "UNK").upper()
        if cc not in by_country:
            by_country[cc] = []
        by_country[cc].append(p)

    for cc, subset in by_country.items():
        fpath = country_dir / f"{cc}.json"
        save_json(subset, fpath)
        files[f"country_{cc}"] = fpath
    logger.info(f"Generated {len(by_country)} country-specific files.")

    # 4. Generate Split Outputs (Tank, Sniper, Diplomat)
    logger.debug("Generating split outputs (Tank/Sniper/Diplomat)...")
    split_files = generate_split_outputs(
        proxies, output_dir, washed_outbounds, washed_ids, smart_chains
    )
    files.update(split_files)

    logger.info(
        f"Categorized outputs generated: "
        f"{len(by_proto)} protocols, {len(by_country)} countries, "
        f"{len(files)} total files."
    )
    return files
