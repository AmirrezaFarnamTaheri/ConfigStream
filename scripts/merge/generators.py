# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import os
import shutil
import logging
import sqlite3
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Optional

from cryptography.fernet import Fernet

from configstream.models import Proxy
from datetime import datetime, timezone
from configstream.output_generators import (
    generate_base64_subscription,
    generate_clash_config,
    generate_split_outputs,
)
from configstream.adapters import get_adapter
from configstream.crypto.signer import Signer
from configstream.transport.stego import generate_stego_assets
from configstream.output_transport import inject_stego_key_into_frontend

logger = logging.getLogger(__name__)


def generate_outputs(
    ranked_proxies: List[Proxy],
    chosen_proxies: List[Proxy],
    output_dir: Path,
    total_processed: int,
    root_dir: Path,
    washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    smart_chains: Optional[Dict[str, List[List[Dict[str, Any]]]]] = None,
    total_washed: int = 0,
    total_revived: int = 0,
    # Add vwarp and revived stats parameters
    revived_warp: int = 0,
    revived_vwarp: int = 0,
    vwarp_attempts: int = 0,
    vwarp_success: int = 0,
    total_configured_sources: int = 0,
    washing_enabled: bool = False,
):
    """Generates all output files with comprehensive stats."""

    # Clear existing outputs (except data/)
    output_dir.mkdir(exist_ok=True)
    removable = {
        "proxies.json",
        "base64.txt",
        "all.txt",
        "base64.signed.json",
        "singbox.json",
        "singbox-vpn.json",
        "clash.yaml",
        "side_products.zip",
        "surge.conf",
        "shadowrocket.txt",
        "loon.conf",
        "quantumult.conf",
        "sip008.json",
    }
    for file_path in output_dir.iterdir():
        if file_path.is_file() and file_path.name in removable:
            file_path.unlink()

    # 1. proxies.json
    with open(output_dir / "proxies.json", "w") as f:
        json.dump([p.model_dump() for p in ranked_proxies], f, indent=2)
    logger.info(f"✓ Generated proxies.json ({len(ranked_proxies)} proxies)")

    # 2. Protocol text files
    proxies_by_protocol = defaultdict(list)
    for proxy in ranked_proxies:
        proxies_by_protocol[proxy.protocol].append(proxy.config)

    for protocol, configs in proxies_by_protocol.items():
        with open(output_dir / f"{protocol}.txt", "w") as f:
            f.write("\n".join(configs))
    logger.info(f"✓ Generated protocol files ({len(proxies_by_protocol)} protocols)")

    # 3. Subscriptions (all.txt, base64) & Signing
    all_configs = [p.config for p in ranked_proxies]
    signing_key = os.environ.get("SIGNING_KEY")
    signer = None
    if signing_key:
        try:
            signer = Signer(private_key_hex=signing_key)
            logger.info("🔐 Signing enabled.")
        except Exception as e:
            logger.warning(f"⚠️ Signing setup failed: {e}")

    if all_configs:
        with open(output_dir / "all.txt", "w") as f:
            f.write("\n".join(all_configs))

        # [Task 5] Create proxies.txt as a copy of all.txt for "Raw Configs"
        with open(output_dir / "proxies.txt", "w") as f:
            f.write("\n".join(all_configs))

        base64_content = generate_base64_subscription(ranked_proxies)
        with open(output_dir / "base64.txt", "w") as f:
            f.write(base64_content)

        if signer:
            try:
                signed_b64 = signer.sign_subscription(base64_content)
                with open(output_dir / "base64.signed.json", "w") as f:
                    json.dump(signed_b64, f)
                logger.info("✓ Generated base64.signed.json")
            except Exception as e:
                logger.warning(f"⚠️ Failed to sign base64: {e}")

    # 4. CHOSEN Subset
    chosen_dir = output_dir / "chosen"
    chosen_dir.mkdir(exist_ok=True)
    with open(chosen_dir / "proxies.json", "w") as f:
        json.dump([p.model_dump() for p in chosen_proxies], f, indent=2)

    chosen_configs = [p.config for p in chosen_proxies]
    with open(chosen_dir / "all.txt", "w") as f:
        f.write("\n".join(chosen_configs))

    chosen_base64 = generate_base64_subscription(chosen_proxies)
    with open(chosen_dir / "base64.txt", "w") as f:
        f.write(chosen_base64)

    chosen_by_protocol = defaultdict(list)
    for proxy in chosen_proxies:
        chosen_by_protocol[proxy.protocol].append(proxy.config)
    for protocol, configs in chosen_by_protocol.items():
        with open(chosen_dir / f"{protocol}.txt", "w") as f:
            f.write("\n".join(configs))

    # 5. Client Configs - Generate both Sniper (singbox.json) and Tank (singbox-vpn.json)
    # Use generate_split_outputs to create both singbox variants
    washed_ids = None
    if washed_outbounds:
        # Extract IDs from washed proxies to avoid duplicates
        washed_ids = set()
        for outbound in washed_outbounds:
            tag = outbound.get("tag", "")
            # Extract proxy ID from tag if possible
            if tag.startswith("🛡️ Secure"):
                washed_ids.add(tag)

    split_files = generate_split_outputs(
        ranked_proxies,
        output_dir,
        washed_outbounds=washed_outbounds,
        washed_ids=washed_ids,
        smart_chains=smart_chains,
    )
    logger.info(f"✓ Generated split outputs: {list(split_files.keys())}")

    # Also generate Clash config
    with open(output_dir / "clash.yaml", "w") as f:
        f.write(generate_clash_config(ranked_proxies))

    # Sign singbox.json if signer available
    if signer and (output_dir / "singbox.json").exists():
        try:
            singbox_content = (output_dir / "singbox.json").read_text()
            signed_singbox = signer.sign_subscription(singbox_content)
            with open(output_dir / "singbox.signed.json", "w") as f:
                json.dump(signed_singbox, f)
        except Exception as e:
            logger.warning(f"⚠️ Failed to sign singbox: {e}")

    # 6. Steganography
    _generate_stego(output_dir, root_dir)

    # 7. Adapters (including smart chains and revived proxies)
    _generate_adapters(ranked_proxies, output_dir, washed_outbounds=washed_outbounds)

    # 7.1 Non-Singbox Protocol Outputs (OpenVPN, etc.)
    _generate_native_protocol_outputs(ranked_proxies, output_dir)

    # 8. Statistics & Metadata
    _generate_statistics(
        ranked_proxies,
        chosen_proxies,
        output_dir,
        total_processed,
        proxies_by_protocol,
        chosen_by_protocol,
        washed_outbounds,
        smart_chains,
        total_washed,
        total_revived,
        revived_warp,
        revived_vwarp,
        vwarp_attempts,
        vwarp_success,
        total_configured_sources,
        washing_enabled,
    )

    # 9. Wiki & Pages
    _copy_pages(root_dir, output_dir)

    return proxies_by_protocol


def _generate_stego(output_dir: Path, root_dir: Path):
    frontend_src = root_dir / "frontend"
    if frontend_src.exists():
        try:
            shutil.copytree(frontend_src, output_dir, dirs_exist_ok=True)
        except Exception as e:
            logger.warning(f"⚠️ Failed to copy frontend assets: {e}")

    dynamic_key = os.environ.get("STEGO_KEY") or Fernet.generate_key().decode()

    assets_images = output_dir / "assets" / "images"
    if assets_images.exists():
        try:
            generate_stego_assets(
                config_dir=output_dir, assets_dir=assets_images, secret_key=dynamic_key
            )
        except Exception as e:
            logger.warning(f"⚠️ Stego generation failed: {e}")

    js_path = output_dir / "assets" / "js" / "stego.js"
    if js_path.exists():
        try:
            inject_stego_key_into_frontend(dynamic_key, js_path)
        except Exception as e:
            logger.warning(f"⚠️ Failed to inject stego key: {e}")


def _generate_native_protocol_outputs(proxies: List[Proxy], output_dir: Path):
    """
    Generate native protocol outputs for non-Singbox clients.
    Supports: OpenVPN (.ovpn), WireGuard (.conf), plain URIs (.txt)
    Creates a ZIP archive of all side products for easy download.
    """
    import zipfile
    from datetime import datetime

    side_products_dir = output_dir / "side_products"
    side_products_dir.mkdir(exist_ok=True)
    generated_count = 0

    try:
        # 1. OpenVPN Export (.ovpn files)
        openvpn_proxies = [p for p in proxies if p.protocol == "openvpn"]
        if openvpn_proxies:
            ovpn_dir = side_products_dir / "openvpn"
            ovpn_dir.mkdir(exist_ok=True)

            for idx, proxy in enumerate(openvpn_proxies, start=1):
                if proxy.config and len(proxy.config) > 50:
                    country = proxy.country_code or "XX"
                    filename = f"{country}_{idx}.ovpn"
                    filepath = ovpn_dir / filename
                    filepath.write_text(proxy.config, encoding="utf-8")
                    generated_count += 1

            # Concatenated file
            all_ovpn_path = ovpn_dir / "all_configs.txt"
            with open(all_ovpn_path, "w", encoding="utf-8") as f:
                for idx, proxy in enumerate(openvpn_proxies, start=1):
                    if proxy.config:
                        f.write(f"# OpenVPN Config {idx}\n")
                        f.write(f"# Country: {proxy.country_code or 'Unknown'}\n")
                        f.write(f"# Address: {proxy.address}:{proxy.port}\n")
                        f.write(proxy.config)
                        f.write("\n\n" + "=" * 60 + "\n\n")

            logger.info(f"✓ Generated {len(openvpn_proxies)} OpenVPN configs")

        # 2. WireGuard Export (.conf files)
        wireguard_proxies = [p for p in proxies if p.protocol == "wireguard"]
        if wireguard_proxies:
            wg_dir = side_products_dir / "wireguard"
            wg_dir.mkdir(exist_ok=True)

            for idx, proxy in enumerate(wireguard_proxies, start=1):
                try:
                    # Generate WireGuard config from proxy details
                    country = proxy.country_code or "XX"
                    filename = f"{country}_{idx}.conf"
                    filepath = wg_dir / filename

                    # Build WireGuard config
                    private_key = proxy.details.get("private_key", "")
                    address = proxy.details.get("local_address", ["10.0.0.2/32"])
                    if isinstance(address, list):
                        address = address[0]

                    # Peer info
                    public_key = proxy.details.get("peer_public_key", "")
                    endpoint = f"{proxy.address}:{proxy.port}"
                    reserved = proxy.details.get("reserved", [0, 0, 0])

                    wg_config = f"""[Interface]
PrivateKey = {private_key}
Address = {address}
DNS = 1.1.1.1, 1.0.0.1

[Peer]
PublicKey = {public_key}
Endpoint = {endpoint}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
                    if reserved and any(r != 0 for r in reserved):
                        wg_config += f"# Reserved: {','.join(map(str, reserved))}\n"

                    filepath.write_text(wg_config, encoding="utf-8")
                    generated_count += 1
                except Exception as e:
                    logger.debug(f"Failed to generate WireGuard config {idx}: {e}")

            logger.info(f"✓ Generated {len(wireguard_proxies)} WireGuard configs")

        # 3. Plain URI Lists (for manual import)
        uri_dir = side_products_dir / "plain_uris"
        uri_dir.mkdir(exist_ok=True)

        # Group by protocol
        protocol_groups: Dict[str, List[str]] = {}
        for proxy in proxies:
            if proxy.protocol not in ["openvpn"]:  # Skip protocols already handled
                if proxy.config:  # Has URI representation
                    protocol_groups.setdefault(proxy.protocol, []).append(proxy.config)

        for protocol, configs in protocol_groups.items():
            if configs:
                filepath = uri_dir / f"{protocol}_uris.txt"
                filepath.write_text(
                    "\n".join(configs[:500]), encoding="utf-8"
                )  # Limit to 500
                generated_count += len(configs[:500])

        if protocol_groups:
            logger.info(
                f"✓ Generated plain URI files for {len(protocol_groups)} protocols"
            )

        # 4. Create README
        readme_path = side_products_dir / "README.txt"
        readme_content = f"""ConfigStream Side Products
Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

This archive contains native protocol configurations that can be used
with various VPN clients without requiring Sing-box or Clash.

CONTENTS:
=========

1. openvpn/
   - Individual .ovpn files (one per server)
   - all_configs.txt (concatenated list)
   - Compatible with: OpenVPN Connect, Tunnelblick, OpenVPN GUI

2. wireguard/
   - Individual .conf files (one per server)
   - Compatible with: WireGuard official client, wireguard-tools

3. plain_uris/
   - Protocol-specific URI lists
   - Can be imported into compatible clients manually

USAGE:
======

OpenVPN:
  Import .ovpn files directly into your OpenVPN client

WireGuard:
  - GUI: Import .conf files via "Import tunnel(s) from file"
  - CLI: wg-quick up /path/to/config.conf

Plain URIs:
  Copy-paste URIs into your client's subscription/manual add dialog

For more information, visit: https://github.com/AmirrezaFarnamTaheri/ConfigStream
"""
        readme_path.write_text(readme_content, encoding="utf-8")

        # 5. Create ZIP archive
        if generated_count > 0:
            zip_path = output_dir / "side_products.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file in side_products_dir.rglob("*"):
                    if file.is_file():
                        arcname = file.relative_to(side_products_dir)
                        zipf.write(file, arcname)

            zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
            logger.info(
                f"✓ Created side_products.zip ({zip_size_mb:.2f} MB, {generated_count} configs)"
            )
        else:
            logger.debug("No side products generated (no compatible protocols found)")

    except Exception as e:
        logger.warning(f"⚠️ Failed to generate native protocol outputs: {e}")


def _generate_adapters(
    proxies: List[Proxy],
    output_dir: Path,
    washed_outbounds: Optional[List[Dict[str, Any]]] = None,
):
    """Generate adapter configs including smart chains and revived proxies."""
    try:
        (output_dir / "surge.conf").write_text(
            get_adapter("surge").export(proxies, washed_outbounds=washed_outbounds)
        )
        (output_dir / "shadowrocket.txt").write_text(
            get_adapter("shadowrocket").export(
                proxies, washed_outbounds=washed_outbounds
            )
        )
        (output_dir / "loon.conf").write_text(
            get_adapter("loon").export(proxies, washed_outbounds=washed_outbounds)
        )
        (output_dir / "quantumult.conf").write_text(
            get_adapter("qx").export(proxies, washed_outbounds=washed_outbounds)
        )
        (output_dir / "sip008.json").write_text(
            get_adapter("sip008").export(proxies, washed_outbounds=washed_outbounds)
        )
        logger.info(
            f"✓ Generated adapter configs with {len(washed_outbounds) if washed_outbounds else 0} smart chains"
        )
    except Exception as e:
        logger.warning(f"⚠️ Failed to generate adapter configs: {e}")


def _generate_statistics(
    ranked: List[Proxy],
    chosen: List[Proxy],
    output_dir: Path,
    total_processed: int,
    proxies_by_protocol: Dict,
    chosen_by_protocol: Dict,
    washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    smart_chains: Optional[Dict[str, List[List[Dict[str, Any]]]]] = None,
    total_washed: int = 0,
    total_revived: int = 0,
    # Add vwarp and revived stats parameters
    revived_warp: int = 0,
    revived_vwarp: int = 0,
    vwarp_attempts: int = 0,
    vwarp_success: int = 0,
    total_configured_sources: int = 0,
    washing_enabled: bool = False,
):
    working_proxies = sum(1 for p in ranked if p.is_working)
    working_chosen = sum(1 for p in chosen if p.is_working)

    country_counts: Dict[str, int] = defaultdict(int)
    for p in ranked:
        country_counts[p.country] += 1

    asn_counts: Dict[str, int] = defaultdict(int)
    for p in ranked:
        if p.asn:
            asn_counts[p.asn] += 1

    total_smart_chains_count = (
        sum(len(v) for v in smart_chains.values()) if smart_chains else 0
    )

    port_counts: Dict[str, int] = defaultdict(int)
    for p in ranked:
        port_counts[str(p.port)] += 1

    # Rejection Reasons Aggregation
    rejection_reasons: Dict[str, int] = defaultdict(int)
    db_path = output_dir / "data" / "source_quality.db"
    if db_path.exists():
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.execute("SELECT failure_modes_json FROM source_runs")
                for (json_str,) in cursor:
                    if json_str and json_str != "{}":
                        try:
                            modes = json.loads(json_str)
                            for k, v in modes.items():
                                rejection_reasons[k] += v
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.warning(f"Failed to aggregate rejection reasons: {e}")

    # Latency Distribution
    latency_dist = {"fast": 0, "medium": 0, "slow": 0, "very_slow": 0}
    for p in ranked:
        lat = p.latency if p.latency is not None else 9999
        if lat < 100:
            latency_dist["fast"] += 1
        elif lat < 500:
            latency_dist["medium"] += 1
        elif lat < 1500:
            latency_dist["slow"] += 1
        else:
            latency_dist["very_slow"] += 1

    # Latency by Country & Protocol
    latency_by_country: Dict[str, list] = defaultdict(list)
    latency_by_protocol: Dict[str, list] = defaultdict(list)
    for p in ranked:
        if p.latency is not None and p.latency < 9000:  # Valid latency
            # FIX: Use country_code (e.g., "US") not country (e.g., "United States")
            # to match frontend expectations (analytics.js)
            cc = p.country_code or "XX"
            latency_by_country[cc].append(p.latency)
            latency_by_protocol[p.protocol].append(p.latency)

    # Calculate averages
    avg_latency_by_country = {
        country: round(sum(lats) / len(lats))
        for country, lats in latency_by_country.items()
        if lats
    }
    avg_latency_by_protocol = {
        protocol: round(sum(lats) / len(lats))
        for protocol, lats in latency_by_protocol.items()
        if lats
    }

    # Globe Sampling Logic
    globe_points = []
    try:
        # 1. Filter proxies with location
        located = [p for p in ranked if p.details.get("lat") and p.details.get("lng")]

        # 2. Cluster by 1-degree grid
        grid = defaultdict(list)
        for p in located:
            k = (round(p.details["lat"]), round(p.details["lng"]))
            grid[k].append(p)

        # 3. Sort each cell by latency
        for k in grid:
            grid[k].sort(key=lambda p: (p.latency if p.latency is not None else 9999))

        # 4. Selection
        selected = []
        # Pass 1: Top 1 from each cell
        for k in grid:
            selected.append(grid[k][0])

        # Pass 2: Up to 2 more from cells if total < 300
        if len(selected) < 300:
            remaining_slots = 300 - len(selected)
            candidates = []
            for k in grid:
                candidates.extend(grid[k][1:3])  # 2nd and 3rd best
            candidates.sort(
                key=lambda p: (p.latency if p.latency is not None else 9999)
            )
            selected.extend(candidates[:remaining_slots])

        # 5. Format
        for p in selected:
            globe_points.append(
                {
                    "lat": p.details["lat"],
                    "lng": p.details["lng"],
                    "latency": p.latency,
                    "country": p.country_code,
                    "protocol": p.protocol,
                }
            )
    except Exception as e:
        logger.warning(f"Failed to generate globe points: {e}")

    # [UNIFIED] Single metadata.json - merged statistics.json into metadata.json
    # This is now the single source of truth for all frontend stats
    washed_chains_count = 0
    if (output_dir / "singbox.json").exists():
        try:
            with open(output_dir / "singbox.json", "r") as f:
                sb_config = json.load(f)
                washed_chains_count = sum(
                    1
                    for out in sb_config.get("outbounds", [])
                    if out.get("tag", "").startswith("🛡️ Secure")
                )
        except Exception:
            pass

    # Use vwarp stats passed as parameters instead of recalculating
    # These stats are already aggregated from all batches in merge/core.py
    vwarp_win_rate = (
        (vwarp_success / vwarp_attempts * 100) if vwarp_attempts > 0 else 0.0
    )

    # Get update interval from environment or default to 6 hours
    update_interval_hours = int(os.getenv("UPDATE_INTERVAL_HOURS", "6"))

    # If we still don't have total_configured_sources, try to count from environment or use fallback
    if total_configured_sources == 0:
        sources_list = []
        sources_env = os.getenv("SOURCES_URL", "")
        if sources_env:
            sources_list = [s.strip() for s in sources_env.split(",") if s.strip()]

        if not sources_list:
            source_dir = Path("sources")
            if source_dir.exists():
                for batch_file in source_dir.glob("batch_*.txt"):
                    if batch_file.is_file():
                        sources_list.extend(
                            [
                                line.strip()
                                for line in batch_file.read_text().splitlines()
                                if line.strip()
                            ]
                        )

        if not sources_list:
            consol_sources = Path("consolidated_sources.txt")
            if consol_sources.exists():
                sources_list = [
                    line.strip()
                    for line in consol_sources.read_text().splitlines()
                    if line.strip()
                ]

        total_configured_sources = len(sources_list)

    # Unified metadata.json - single source of truth
    meta = {
        # Schema version for frontend compatibility checks
        "schema_version": "2.3.0",
        # Timestamps
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        # Canonical Keys (used by frontend)
        "total_lines_sourced": total_processed,
        "total_unique_candidates": len(ranked),
        "total_valid_proxies": working_proxies,
        "total_proxies": total_processed,
        "total_sourced": total_processed,
        "total_tested": len(ranked),
        "total_working": working_proxies,
        "success_rate": (working_proxies / len(ranked)) if ranked else 0,
        # Metrics
        "total_clean": working_proxies,
        "total_dirty": total_processed - working_proxies,
        "total_washed": total_washed,
        "total_revived": total_revived,
        "total_smart_chains": total_smart_chains_count,
        "smart_chain_count": total_smart_chains_count,
        "washed_chains": washed_chains_count,
        "smart_chains_breakdown": (
            {k: len(v) for k, v in smart_chains.items()} if smart_chains else {}
        ),
        # Vwarp efficiency stats
        "vwarp_attempts": vwarp_attempts,
        "vwarp_success": vwarp_success,
        "vwarp_win_rate": round(vwarp_win_rate, 1),
        "washing_enabled": washing_enabled,
        # Revived proxy stats (WARP and Vwarp breakdown)
        "revived_warp": revived_warp,
        "revived_vwarp": revived_vwarp,
        # Frontend display values
        "sources_count": total_configured_sources,
        "total_sources": total_configured_sources,
        "update_interval_hours": update_interval_hours,
        # Distribution data
        "latency_distribution": latency_dist,
        "latency_by_country": avg_latency_by_country,
        "latency_by_protocol": avg_latency_by_protocol,
        "protocols": {k: len(v) for k, v in proxies_by_protocol.items()},
        "proxies_by_protocol": {k: len(v) for k, v in proxies_by_protocol.items()},
        "country_stats": dict(sorted(country_counts.items())),
        "countries": dict(sorted(country_counts.items())),
        "proxies_by_country": dict(sorted(country_counts.items())),
        "top_10_countries": sorted(
            country_counts.items(), key=lambda item: item[1], reverse=True
        )[:10],
        "rejection_reasons": dict(rejection_reasons),
        "asns": dict(sorted(asn_counts.items())),
        "ports": dict(
            sorted(port_counts.items(), key=lambda item: item[1], reverse=True)[:10]
        ),
        # Globe visualization data
        "proxy_locations": globe_points,
        # Chosen proxies breakdown
        "chosen": {
            "total": len(chosen),
            "working": working_chosen,
            "protocols": {k: len(v) for k, v in chosen_by_protocol.items()},
        },
    }

    with open(output_dir / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    # NOTE: statistics.json removed - metadata.json is now single source of truth
    # FIX: Removed save_metadata() call which was overwriting metadata.json
    # with a different schema, causing zero values in frontend.
    # The 'meta' dict above already contains all required fields.

    # Batch Stats
    batch_stats: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"total": 0, "working": 0}
    )
    protocols_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for p in ranked:
        src = p.batch_source or "unknown"
        batch_stats[src]["total"] += 1
        if p.is_working:
            batch_stats[src]["working"] += 1
        protocols_stats[src][p.protocol] += 1

    final_batch_stats = {
        k: {
            "total": v["total"],
            "working": v["working"],
            "protocols": protocols_stats[k],
        }
        for k, v in batch_stats.items()
    }
    with open(output_dir / "batch_statistics.json", "w") as f:
        json.dump(final_batch_stats, f, indent=2)

    # Store for use in logs
    return final_batch_stats


def _copy_pages(root_dir: Path, output_dir: Path):
    """
    Copies documentation and ensures HTML pages are in the root.
    Removes subdirectory index.html logic to simplify path resolution.
    """
    wiki_src = root_dir / "docs" / "wiki"
    wiki_dest = output_dir / "wiki"

    # Copy markdown files to wiki/ folder so they can be fetched
    if wiki_src.exists():
        wiki_dest.mkdir(exist_ok=True)
        for md_file in wiki_src.glob("*.md"):
            (wiki_dest / md_file.name).write_text(md_file.read_text())

    # Ensure generated files like singbox-vpn.json are at the root
    # Note: frontend/ files are copied by _generate_stego
    # We should ensure specific files generated in output_dir are preserved/copied if needed

    # 2025-05-27 Update: Ensure singbox-vpn.json is available for download
    # It is already generated in output_dir by generate_split_outputs

    # If there are any other specific files that need to be moved to 'root' from a subfolder, do it here
    pass

    # Note: frontend/ files (including about.html, wiki.html) are already
    # copied to output_dir root by _generate_stego -> shutil.copytree.
    # We do NOT move them to subdirectories or delete them from root.
    # This ensures window.ROOT_PATH = './' works everywhere.
