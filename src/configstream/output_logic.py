# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import copy
import shutil
from typing import List, Dict, Optional, Any, Tuple, cast
from pathlib import Path

from .models import Proxy
from .intelligence.washer.core import ProxyWasher
from .intelligence.chaining import generate_smart_chains
from .generators import (
    generate_singbox_config,
    generate_clash_config,
    generate_split_outputs,
)
from .dns_profiles import (
    build_singbox_dns_profile,
    build_clash_dns_profile,
    build_resolver_sets,
)
from .utils import AtomicFileWriter
from .config import AppSettings
from .constants import (
    CHOSEN_TOTAL_TARGET,
    CHOSEN_TOP_PER_PROTOCOL,
)
from .converters.chain_outbounds import chain_obs_from_details

# Re-exports for backward compatibility (consumed by output_handler, scripts,
# and the unit-test contract surface).
from .output.metadata import (
    save_metadata as save_metadata,
    write_public_artifact_contract as write_public_artifact_contract,
)
from .output.public_lists import generate_categorized_lists
from .output.native_configs import (
    build_dns_safe_proxies as _build_dns_safe_proxies,
    build_dns_hardened_proxies as _build_dns_hardened_proxies,
    filter_outbounds_for_dns_safe as _filter_outbounds_for_dns_safe,
    filter_outbounds_for_dns_hardened as _filter_outbounds_for_dns_hardened,
    wrap_surge_or_loon_profile as _wrap_surge_or_loon_profile,
    wrap_quantumultx_profile as _wrap_quantumultx_profile,
    wrap_shadowrocket_profile as _wrap_shadowrocket_profile,
)
from .output.subscriptions import (
    generate_base64_subscription,
    generate_plaintext_subscription,
    get_export_pool as _get_export_pool,
    order_export_proxies as _order_export_proxies,
    select_chosen_proxies as _select_chosen_proxies,
    generate_side_products_pack,
)

# Public/test contract surface re-exported from this orchestrator module.
__all__ = [
    "save_metadata",
    "write_public_artifact_contract",
    "generate_categorized_lists",
    "generate_base64_subscription",
    "generate_plaintext_subscription",
    "generate_side_products_pack",
    "generate_split_outputs",
    "generate_categorized_outputs",
]

logger = logging.getLogger(__name__)


def generate_categorized_outputs(
    proxies: List[Proxy],
    output_dir: Path,
    washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    washed_ids: Optional[set] = None,
    smart_chains: Optional[Dict[str, List[List[Dict[str, Any]]]]] = None,
    washer: Optional[ProxyWasher] = None,
    dns_safe_cache: Optional[Tuple[List[Proxy], Dict[str, str]]] = None,
    dns_hardened_cache: Optional[Tuple[List[Proxy], Dict[str, str]]] = None,
) -> Dict[str, Path]:
    """
    Generates all output files categorized by protocol, country, and type.
    Now acts as an orchestrator for specialized modules in .output/
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = {}
    settings = AppSettings()

    # 0. Clean stale outputs
    stale_dirs = ["by_country", "by_protocol", "countries", "protocols"]
    for d in stale_dirs:
        shutil.rmtree(output_dir / d, ignore_errors=True)
    for f in ["raw.txt", "all.txt", "sub.txt", "vpn_subscription_base64.txt"]:
        (output_dir / f).unlink(missing_ok=True)

    if washer is None:
        washer = ProxyWasher(settings.WARP_KEY_POOL)

    # 1. Smart Chains
    if smart_chains is None:
        smart_chains = (
            generate_smart_chains(proxies, washer=washer)
            if settings.ENABLE_SMART_CHAINING
            else {}
        )

    # 2. Main Configs (Sing-box & Clash)
    export_pool = _get_export_pool(proxies)
    split_files = generate_split_outputs(
        export_pool,
        output_dir,
        washed_outbounds=washed_outbounds,
        washed_ids=washed_ids,
        smart_chains=smart_chains,
    )
    generated_files.update(split_files)
    if "singbox" in split_files:
        generated_files["singbox_full"] = split_files["singbox"]
        generated_files["master"] = split_files["singbox"]
    if "clash" in split_files:
        generated_files["clash_full"] = split_files["clash"]

    ordered_pool = _order_export_proxies(export_pool)

    # 3. Subscriptions
    raw_content = generate_plaintext_subscription(ordered_pool)
    base64_content = generate_base64_subscription(ordered_pool)

    proxies_txt_path = output_dir / "proxies.txt"
    AtomicFileWriter.write_text(proxies_txt_path, raw_content)
    generated_files["proxies_txt"] = proxies_txt_path

    base64_path = output_dir / "base64.txt"
    AtomicFileWriter.write_text(base64_path, base64_content)
    generated_files["base64"] = base64_path

    # 3b. Chosen subset
    chosen_dir = output_dir / "chosen"
    chosen_dir.mkdir(exist_ok=True)
    chosen = _select_chosen_proxies(
        proxies, CHOSEN_TOP_PER_PROTOCOL, CHOSEN_TOTAL_TARGET
    )

    chosen_paths = {
        "base64.txt": (generate_base64_subscription(chosen), "chosen_base64"),
        "proxies.txt": (generate_plaintext_subscription(chosen), "chosen_proxies_txt"),
        "singbox.json": (generate_singbox_config(chosen), "chosen_singbox"),
        "clash.yaml": (
            generate_clash_config(chosen, ignore_status=True),
            "chosen_clash",
        ),
    }
    for name, (content, key) in chosen_paths.items():
        path = chosen_dir / name
        AtomicFileWriter.write_text(path, content)
        generated_files[key] = path

    # 3c. Adapters
    from .adapters import get_adapter

    adapter_specs = {
        "shadowrocket": ("shadowrocket", "shadowrocket.txt"),
        "quantumult": ("quantumultx", "quantumult.conf"),
        "surge": ("surge", "surge.conf"),
        "loon": ("loon", "loon.conf"),
        "sip008": ("sip008", "sip008.json"),
    }
    for key, (adapter_name, filename) in adapter_specs.items():
        try:
            adapter = get_adapter(adapter_name)
            content = (
                adapter.export(ordered_pool, washed_outbounds=washed_outbounds)
                if adapter_name in ("surge", "loon")
                else adapter.export(ordered_pool)
            )
            out_path = output_dir / filename
            AtomicFileWriter.write_text(out_path, content)
            generated_files[key] = out_path
        except Exception as exc:
            logger.warning("Failed to generate %s: %s", adapter_name, exc)

    # 3d. Side Products
    zip_path = output_dir / "side_products.zip"
    if generate_side_products_pack(ordered_pool, zip_path, raw_content, output_dir):
        generated_files["side_products"] = zip_path

    # 4. Categorized Lists (Protocol & Country)
    generated_files.update(generate_categorized_lists(proxies, output_dir))

    # 5. Chains logic
    chain_obs = _collect_all_chains(proxies, washed_outbounds, smart_chains)
    chains_content = generate_singbox_config([], extra_outbounds=chain_obs)
    for name in ["singbox-chains.json", "chains.json"]:
        path = output_dir / name
        AtomicFileWriter.write_text(path, chains_content)
        generated_files[name.replace("-", "_").replace(".json", "")] = path

    # 6. DNS-safe variations
    if not settings.DNS_SAFE_OUTPUTS:
        safe_proxies, host_map = cast(Tuple[List[Proxy], Dict[str, str]], ([], {}))
    elif dns_safe_cache is not None:
        safe_proxies, host_map = dns_safe_cache
    else:
        safe_proxies, host_map = _build_dns_safe_proxies(proxies)

    _gen_dns_variation(
        safe_proxies,
        host_map,
        output_dir,
        "dns-safe",
        washed_outbounds if settings.DNS_SAFE_OUTPUTS else None,
        smart_chains if settings.DNS_SAFE_OUTPUTS else {},
        washed_ids if settings.DNS_SAFE_OUTPUTS else None,
        generated_files,
    )

    # 7. DNS-hardened variations
    if not settings.DNS_HARDENED_OUTPUTS:
        hardened_proxies, hardened_map = cast(Tuple[List[Proxy], Dict[str, str]], ([], {}))
    elif dns_hardened_cache is not None:
        hardened_proxies, hardened_map = dns_hardened_cache
    else:
        hardened_proxies, hardened_map = _build_dns_hardened_proxies(proxies)

    _gen_dns_variation(
        hardened_proxies,
        hardened_map,
        output_dir,
        "dns-hardened",
        washed_outbounds if settings.DNS_HARDENED_OUTPUTS else None,
        smart_chains if settings.DNS_HARDENED_OUTPUTS else {},
        washed_ids if settings.DNS_HARDENED_OUTPUTS else None,
        generated_files,
        is_hardened=True,
    )

    return generated_files


def _collect_all_chains(
    proxies, washed_outbounds, smart_chains
) -> List[Dict[str, Any]]:
    chain_obs = []
    seen_tags = set()

    def _append(outbounds):
        for o in copy.deepcopy(outbounds or []):
            tag = o.get("tag")
            if tag:
                base = tag
                counter = 0
                while tag in seen_tags:
                    counter += 1
                    tag = f"{base}-{counter}"
                o["tag"] = tag
                seen_tags.add(tag)
            chain_obs.append(o)

    for p in proxies:
        chain = chain_obs_from_details(p.details or {})
        if chain:
            if (p.details or {}).get("is_revived") and p.remarks:
                chain[-1]["tag"] = p.remarks
            _append(chain)

    _append(washed_outbounds)
    if smart_chains:
        for group in smart_chains.values():
            for chain in group:
                _append(chain)
    return chain_obs


def _gen_dns_variation(
    proxies,
    host_map,
    output_dir,
    suffix,
    washed_outbounds,
    smart_chains,
    washed_ids,
    generated_files,
    is_hardened=False,
):
    suffix_key = suffix.replace("-", "_")

    # Filter outbounds
    filter_fn = (
        _filter_outbounds_for_dns_hardened
        if is_hardened
        else _filter_outbounds_for_dns_safe
    )
    filtered_washed = (
        filter_fn(washed_outbounds, host_map) if washed_outbounds else None
    )

    filtered_smart = {}
    if smart_chains:
        for group, chains in smart_chains.items():
            filtered = [filter_fn(c, host_map) for c in chains]
            filtered_smart[group] = [c for c in filtered if c]

    # Split configs
    split_files = generate_split_outputs(
        _get_export_pool(proxies),
        output_dir,
        washed_outbounds=filtered_washed,
        washed_ids=washed_ids,
        smart_chains=filtered_smart,
        name_suffix=suffix,
        key_suffix=suffix_key,
        singbox_dns_profile=build_singbox_dns_profile() if is_hardened else None,
        clash_dns_profile=build_clash_dns_profile() if is_hardened else None,
    )
    generated_files.update(split_files)

    # Generate chains configs for DNS variations
    chain_obs = _collect_all_chains(proxies, filtered_washed, filtered_smart)
    chains_content = generate_singbox_config([], extra_outbounds=chain_obs)
    for prefix in ["singbox-chains", "chains"]:
        name = f"{prefix}-{suffix}.json"
        path = output_dir / name
        AtomicFileWriter.write_text(path, chains_content)
        key = name.replace("-", "_").replace(".json", "")
        generated_files[key] = path

    # Subscriptions
    ordered = _order_export_proxies(_get_export_pool(proxies))
    raw = generate_plaintext_subscription(ordered)
    base64 = generate_base64_subscription(ordered)

    txt_path = output_dir / f"proxies-{suffix}.txt"
    AtomicFileWriter.write_text(txt_path, raw)
    generated_files[f"proxies_txt_{suffix_key}"] = txt_path

    base64_path = output_dir / f"base64-{suffix}.txt"
    AtomicFileWriter.write_text(base64_path, base64)
    generated_files[f"base64_{suffix_key}"] = base64_path

    # Side products
    zip_path = output_dir / f"side_products-{suffix}.zip"
    if generate_side_products_pack(ordered, zip_path, raw, output_dir):
        generated_files[f"side_products_{suffix_key}"] = zip_path

    # Chosen subset for variation
    chosen_dir = output_dir / "chosen"
    chosen_dir.mkdir(exist_ok=True)
    chosen_var = _select_chosen_proxies(
        proxies, CHOSEN_TOP_PER_PROTOCOL, CHOSEN_TOTAL_TARGET
    )
    chosen_base64 = generate_base64_subscription(chosen_var)
    chosen_path = chosen_dir / f"base64-{suffix}.txt"
    AtomicFileWriter.write_text(chosen_path, chosen_base64)
    generated_files[f"chosen_base64_{suffix_key}"] = chosen_path

    # Third-party client profiles (DNS-hardened only)
    if is_hardened:
        _gen_hardened_third_party_profiles(
            ordered, filtered_washed, output_dir, generated_files
        )


def _gen_hardened_third_party_profiles(
    ordered: List[Proxy],
    filtered_washed: Optional[List[Dict[str, Any]]],
    output_dir: Path,
    generated_files: Dict[str, Path],
) -> None:
    """Generate DNS-hardened profiles for third-party clients.

    Each profile is generated independently; a failure in one client format
    must not block the others (fail-open per artifact).
    """
    primary, fallback = build_resolver_sets()

    try:
        out_path = output_dir / "shadowrocket-dns-hardened.txt"
        AtomicFileWriter.write_text(
            out_path, _wrap_shadowrocket_profile(ordered, primary, fallback)
        )
        generated_files["shadowrocket_dns_hardened"] = out_path
    except Exception as exc:
        logger.warning("Failed to generate dns-hardened Shadowrocket: %s", exc)

    for adapter_name in ("surge", "loon"):
        try:
            out_path = output_dir / f"{adapter_name}-dns-hardened.conf"
            AtomicFileWriter.write_text(
                out_path,
                _wrap_surge_or_loon_profile(
                    adapter_name, ordered, filtered_washed, primary, fallback
                ),
            )
            generated_files[f"{adapter_name}_dns_hardened"] = out_path
        except Exception as exc:
            logger.warning("Failed to generate dns-hardened %s: %s", adapter_name, exc)

    try:
        out_path = output_dir / "quantumult-dns-hardened.conf"
        AtomicFileWriter.write_text(
            out_path, _wrap_quantumultx_profile(ordered, primary, fallback)
        )
        generated_files["quantumult_dns_hardened"] = out_path
    except Exception as exc:
        logger.warning("Failed to generate dns-hardened Quantumult X: %s", exc)

    try:
        from .adapters import get_adapter

        out_path = output_dir / "sip008-dns-hardened.json"
        AtomicFileWriter.write_text(out_path, get_adapter("sip008").export(ordered))
        generated_files["sip008_dns_hardened"] = out_path
    except Exception as exc:
        logger.warning("Failed to generate dns-hardened SIP008: %s", exc)
