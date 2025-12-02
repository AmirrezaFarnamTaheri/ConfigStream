import json
import os
import shutil
import logging
from pathlib import Path
from collections import defaultdict
from typing import List, Dict

from .setup_path import setup_python_path

setup_python_path()

from cryptography.fernet import Fernet  # noqa: E402

from configstream.models import Proxy  # noqa: E402
from configstream.output_generators import (  # noqa: E402
    generate_base64_subscription,
    generate_singbox_config,
    generate_clash_config,
)
from configstream.output import save_metadata  # noqa: E402
from configstream.adapters import get_adapter  # noqa: E402
from configstream.crypto.signer import Signer  # noqa: E402
from configstream.transport.stego import generate_stego_assets  # noqa: E402
from configstream.output_transport import inject_stego_key_into_frontend  # noqa: E402

logger = logging.getLogger(__name__)


def generate_outputs(
    ranked_proxies: List[Proxy],
    chosen_proxies: List[Proxy],
    output_dir: Path,
    total_processed: int,
    root_dir: Path,
):
    """Generates all output files."""

    # Clear existing outputs (except data/)
    output_dir.mkdir(exist_ok=True)
    for file_path in output_dir.glob("*.*"):
        if file_path.is_file():
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

    # 5. Client Configs
    with open(output_dir / "clash.yaml", "w") as f:
        f.write(generate_clash_config(ranked_proxies))

    singbox_content = generate_singbox_config(ranked_proxies)
    with open(output_dir / "singbox.json", "w") as f:
        f.write(singbox_content)

    if signer:
        try:
            signed_singbox = signer.sign_subscription(singbox_content)
            with open(output_dir / "singbox.signed.json", "w") as f:
                json.dump(signed_singbox, f)
        except Exception as e:
            logger.warning(f"⚠️ Failed to sign singbox: {e}")

    # 6. Steganography
    _generate_stego(output_dir, root_dir)

    # 7. Adapters
    _generate_adapters(ranked_proxies, output_dir)

    # 8. Statistics & Metadata
    _generate_statistics(
        ranked_proxies,
        chosen_proxies,
        output_dir,
        total_processed,
        proxies_by_protocol,
        chosen_by_protocol,
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


def _generate_adapters(proxies: List[Proxy], output_dir: Path):
    try:
        (output_dir / "surge.conf").write_text(get_adapter("surge").export(proxies))
        (output_dir / "shadowrocket.txt").write_text(
            get_adapter("shadowrocket").export(proxies)
        )
        (output_dir / "loon.conf").write_text(get_adapter("loon").export(proxies))
        (output_dir / "quantumult.conf").write_text(get_adapter("qx").export(proxies))
        (output_dir / "sip008.json").write_text(get_adapter("sip008").export(proxies))
    except Exception as e:
        logger.warning(f"⚠️ Failed to generate adapter configs: {e}")


def _generate_statistics(
    ranked: List[Proxy],
    chosen: List[Proxy],
    output_dir: Path,
    total_processed: int,
    proxies_by_protocol: Dict,
    chosen_by_protocol: Dict,
):
    working_proxies = sum(1 for p in ranked if p.is_working)
    working_chosen = sum(1 for p in chosen if p.is_working)

    country_counts = defaultdict(int)
    for p in ranked:
        country_counts[p.country] += 1

    asn_counts = defaultdict(int)
    for p in ranked:
        if p.asn:
            asn_counts[p.asn] += 1

    stats = {
        "total_fetched": total_processed,
        "total_tested": len(ranked),
        "total_working": working_proxies,
        "protocols": {k: len(v) for k, v in proxies_by_protocol.items()},
        "countries": dict(sorted(country_counts.items())),
        "asns": dict(sorted(asn_counts.items())),
        "chosen": {
            "total": len(chosen),
            "working": working_chosen,
            "protocols": {k: len(v) for k, v in chosen_by_protocol.items()},
        },
        # Legacy
        "total_proxies": len(ranked),
        "proxies_by_protocol": {k: len(v) for k, v in proxies_by_protocol.items()},
        "proxies_by_country": dict(sorted(country_counts.items())),
        "top_10_countries": sorted(
            country_counts.items(), key=lambda item: item[1], reverse=True
        )[:10],
    }

    with open(output_dir / "statistics.json", "w") as f:
        json.dump(stats, f, indent=2)

    meta_stats = {
        "working": working_proxies,
        "fetched_lines": total_processed,
        "duration": 0.0,
    }
    save_metadata(meta_stats, ranked, output_dir)

    # Batch Stats
    batch_stats = defaultdict(lambda: {"total": 0, "working": 0})
    protocols_stats = defaultdict(lambda: defaultdict(int))
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
    wiki_src = root_dir / "docs" / "wiki"
    wiki_dest = output_dir / "wiki"

    if wiki_src.exists():
        wiki_dest.mkdir(exist_ok=True)
        for md_file in wiki_src.glob("*.md"):
            (wiki_dest / md_file.name).write_text(md_file.read_text())

        if (root_dir / "frontend/wiki.html").exists():
            (wiki_dest / "index.html").write_text(
                (root_dir / "frontend/wiki.html").read_text()
            )

    about_dest = output_dir / "about"
    about_dest.mkdir(exist_ok=True)
    if (root_dir / "frontend/about.html").exists():
        (about_dest / "index.html").write_text(
            (root_dir / "frontend/about.html").read_text()
        )

    for filename in ["about.html", "wiki.html"]:
        p = output_dir / filename
        if p.exists():
            p.unlink()
