from pathlib import Path
from typing import List
import shutil
from ..models import Proxy
from ..proxy_history import ProxyHistoryTracker
from ..output import generate_smart_chains, generate_categorized_outputs, save_metadata
from ..adapters import get_adapter
from ..intelligence.washer import ProxyWasher
from ..intelligence.vectors import generate_vectors
from ..output_generators import generate_base64_subscription
from ..serialize import serialize_proxy
from ..consolidation import select_top_configs
from ..transport.stego import generate_stego_assets
from ..output_transport import inject_stego_key_into_frontend
from cryptography.fernet import Fernet
import json
import logging
import os

logger = logging.getLogger(__name__)


async def generate_pipeline_outputs(
    optimized_proxies: List[Proxy], output_path, stats, history: ProxyHistoryTracker
):
    """
    Handles all output generation logic:
    - Washing
    - Smart Chains
    - Standard Outputs (txt, json)
    - Metadata
    - Vectors
    - Adapters
    - Chosen 1000
    """
    logger.info(f"Generating outputs for {len(optimized_proxies)} proxies...")

    stats.final_count = len(optimized_proxies)

    # --- Intelligence Phase: Washing & Chaining (Centralized) ---
    washer = ProxyWasher(os.getenv("WARP_KEY_POOL", "[]"))

    # Fetch Clean IPs before washing
    await washer.fetch_clean_ips()

    washed_outbounds, washed_ids = washer.wash_batch(optimized_proxies)

    smart_chains = generate_smart_chains(optimized_proxies)

    generated_files = generate_categorized_outputs(
        optimized_proxies,
        output_path,
        washed_outbounds=washed_outbounds,
        washed_ids=washed_ids,
        smart_chains=smart_chains,
    )

    # NEW: Generate Static Vectors for Client-Side Search
    generate_vectors(optimized_proxies, output_path)

    # NEW: Generate Metadata for Frontend
    save_metadata(stats.to_dict(), optimized_proxies, output_path)

    # New Adapters Exports
    try:
        # Pass washed_outbounds to adapters that support it (Surge)
        (output_path / "surge.conf").write_text(
            get_adapter("surge").export(optimized_proxies, washed_outbounds)
        )
        (output_path / "shadowrocket.txt").write_text(
            get_adapter("shadowrocket").export(optimized_proxies, washed_outbounds)
        )
        # Loon
        (output_path / "loon.conf").write_text(
            get_adapter("loon").export(optimized_proxies, washed_outbounds)
        )
        # Quantumult X
        (output_path / "quantumult.conf").write_text(
            get_adapter("qx").export(optimized_proxies, washed_outbounds)
        )
        # SIP008
        (output_path / "sip008.json").write_text(
            get_adapter("sip008").export(optimized_proxies, washed_outbounds)
        )
    except Exception as e:
        logger.error(f"Failed to export adapters: {e}")

    # Chosen 1000 Generation
    chosen_proxies = select_top_configs(
        optimized_proxies, top_per_protocol=50, total_limit=1000
    )
    chosen_dir = output_path / "chosen"
    chosen_dir.mkdir(exist_ok=True)

    (chosen_dir / "proxies.json").write_text(
        json.dumps(
            [serialize_proxy(p, history.get_history(p.id)) for p in chosen_proxies],
            indent=2,
        )
    )
    (chosen_dir / "base64.txt").write_text(generate_base64_subscription(chosen_proxies))

    # ---------------------------------------------------------
    # ZERO CONFIGURATION STEGANOGRAPHY (Key Rotation)
    # ---------------------------------------------------------

    # 1. Generate a fresh, random key for this run
    dynamic_key = Fernet.generate_key().decode()

    # Locate cover images for steganography
    assets_dir = output_path.parent / "frontend" / "assets" / "images"
    if not assets_dir.exists():
        # Fallback logic for when running from root or elsewhere
        if os.path.exists("frontend/assets/images"):
            assets_dir = "frontend/assets/images"

    # Copy frontend assets into the output directory so static pages (wiki/about)
    # are available when serving the pipeline artifacts directly.
    for candidate in (output_path.parent / "frontend", Path("frontend")):
        if candidate.exists():
            try:
                shutil.copytree(candidate, output_path, dirs_exist_ok=True)
                logger.info(
                    f"Copied frontend assets from {candidate} into {output_path}"
                )
                break
            except Exception as e:
                logger.warning(f"Failed to copy frontend assets from {candidate}: {e}")

    assets_path = None
    for p in (
        output_path / "assets" / "images",
        output_path.parent / "frontend" / "assets" / "images",
        Path("frontend/assets/images"),
    ):
        if Path(p).exists():
            assets_path = Path(p)
            break

    if assets_path:
        logger.info(
            f"Generating Stego assets using key ending in ...{dynamic_key[-6:]}"
        )
        try:
            # 2. Generate the hidden image using this key
            generate_stego_assets(
                config_dir=output_path,  # Where singbox.json lives
                assets_dir=assets_path,  # Where cover images (background.png) live
                secret_key=dynamic_key,
            )
            logger.info("Stego assets generation completed successfully.")
        except Exception as e:
            logger.error(f"Stego generation failed: {e}", exc_info=True)
    else:
        logger.warning("Assets directory not found, skipping Stego.")

    # 3. Inject the key into the frontend code (assets/js/stego.js)
    # This ensures the static site matches the encrypted image
    # Note: frontend/assets/js/stego.js must exist.
    # We should look for it relative to where we found assets_dir or output_path

    # Try to find stego.js
    # Ensure we ONLY modify the output copy, not the source!
    source_js_path = None
    possible_paths = [
        Path("frontend/assets/js/stego.js"),
        output_path.parent / "frontend" / "assets" / "js" / "stego.js",
    ]

    for p in possible_paths:
        if p.exists():
            source_js_path = p
            break

    output_js_path = output_path / "assets" / "js" / "stego.js"

    if source_js_path:
        # Ensure output directory exists
        output_js_path.parent.mkdir(parents=True, exist_ok=True)
        # Copy source to destination before injecting key
        shutil.copy(source_js_path, output_js_path)
        inject_stego_key_into_frontend(dynamic_key, output_js_path)
    else:
        logger.warning("Could not find source stego.js to inject key.")

    # ---------------------------------------------------------

    return generated_files
