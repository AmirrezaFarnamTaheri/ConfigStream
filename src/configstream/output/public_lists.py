# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
from typing import List, Dict
from pathlib import Path

from ..models import Proxy
from ..utils import AtomicFileWriter
from ..serialize import serialize_proxy
from ..generators import generate_singbox_config
from ..generators.plaintext import generate_plaintext_subscription
from ..constants import (
    canonical_protocol_name,
    protocol_sort_key,
)

logger = logging.getLogger(__name__)


def generate_categorized_lists(
    proxies: List[Proxy],
    output_dir: Path,
) -> Dict[str, Path]:
    """
    Generates all output files categorized by protocol and country.
    """
    generated_files = {}

    # Grouping
    by_country: Dict[str, List[Proxy]] = {}
    by_protocol: Dict[str, List[Proxy]] = {}

    for p in proxies:
        cc = (p.country_code or "XX").upper()
        by_country.setdefault(cc, []).append(p)
        by_protocol.setdefault(canonical_protocol_name(p.protocol or ""), []).append(p)

    # Write Country files
    country_dir = output_dir / "countries"
    country_dir.mkdir(exist_ok=True)

    for cc in sorted(by_country.keys()):
        plist = by_country[cc]
        cpath = country_dir / f"{cc}.json"
        AtomicFileWriter.write_text(cpath, generate_singbox_config(plist))

        lpath = country_dir / f"{cc}.list.json"
        arr = [serialize_proxy(p) for p in plist]
        lcontent = json.dumps(arr, indent=2, ensure_ascii=False)
        AtomicFileWriter.write_text(lpath, lcontent)

        generated_files[f"country_{cc}"] = cpath

    # Write Protocol files (JSON + plaintext URI subscriptions)
    proto_dir = output_dir / "protocols"
    proto_dir.mkdir(exist_ok=True)

    for proto in sorted(by_protocol.keys(), key=protocol_sort_key):
        plist = by_protocol[proto]
        ppath = proto_dir / f"{proto}.json"
        AtomicFileWriter.write_text(ppath, generate_singbox_config(plist))

        lpath = proto_dir / f"{proto}.list.json"
        arr = [serialize_proxy(p) for p in plist]
        lcontent = json.dumps(arr, indent=2, ensure_ascii=False)
        AtomicFileWriter.write_text(lpath, lcontent)

        generated_files[f"proto_{proto}"] = ppath

        proto_uris = generate_plaintext_subscription(plist)
        if proto_uris.strip():
            uri_path = proto_dir / f"{proto}.txt"
            AtomicFileWriter.write_text(uri_path, proto_uris)
            generated_files[f"proto_{proto}_txt"] = uri_path

    return generated_files
