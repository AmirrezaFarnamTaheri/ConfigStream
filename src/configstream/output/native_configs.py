# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import copy
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path

from ..models import Proxy
from ..utils import AtomicFileWriter
from ..adapters import get_adapter, ShadowrocketAdapter
from ..generators import (
    generate_singbox_config,
    generate_clash_config,
)
from ..constants import (
    canonical_protocol_name,
)
from ..utils.net import (
    normalize_host as _normalize_host,
    is_ip_literal as _is_ip_literal,
    is_global_ip as _is_global_ip,
)
from ..converters.chains import chain_obs_from_details, update_chain_details

logger = logging.getLogger(__name__)

def _rewrite_openvpn_remote(config: str, original_host: str, ip_value: str) -> str:
    if not config or not original_host or not ip_value:
        return config
    out_lines: List[str] = []
    for line in config.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            out_lines.append(line)
            continue
        if stripped.lower().startswith("remote "):
            parts = stripped.split()
            if len(parts) >= 2 and _normalize_host(parts[1]) == _normalize_host(
                original_host
            ):
                parts[1] = ip_value
                line = " ".join(parts)
        out_lines.append(line)
    return "\n".join(out_lines) + ("\n" if config.endswith("\n") else "")

def _rewrite_chain_obs_for_dns(
    details: Dict[str, Any], host_map: Dict[str, str]
) -> None:
    chain = chain_obs_from_details(details)
    if not chain:
        return
    rewritten_chain: List[Dict[str, Any]] = []
    changed = False
    for outbound in chain:
        if not isinstance(outbound, dict):
            continue
        item = copy.deepcopy(outbound)
        server = item.get("server")
        if isinstance(server, str) and server and not _is_ip_literal(server):
            mapped = host_map.get(_normalize_host(server))
            if mapped:
                item["server"] = mapped
                tls = item.get("tls")
                if isinstance(tls, dict) and not tls.get("server_name"):
                    tls = dict(tls)
                    tls["server_name"] = server
                    item["tls"] = tls
                changed = True
        rewritten_chain.append(item)
    if changed and rewritten_chain:
        update_chain_details(details, rewritten_chain)

def build_dns_safe_proxies(
    proxies: List[Proxy],
) -> Tuple[List[Proxy], Dict[str, str]]:
    safe: List[Proxy] = []
    host_map: Dict[str, str] = {}

    for proxy in proxies:
        addr = (proxy.address or "").strip()
        if not addr:
            continue

        if _is_ip_literal(addr):
            if _is_global_ip(addr):
                host_map[_normalize_host(addr)] = addr
                clone = proxy.model_copy(deep=True)
                details = dict(clone.details or {})
                details["dns_safe"] = True
                _rewrite_chain_obs_for_dns(details, host_map)
                clone.details = details
                safe.append(clone)
            continue

        resolved = (proxy.resolved_ip or "").strip()
        if not resolved or not _is_ip_literal(resolved) or not _is_global_ip(resolved):
            continue

        host_map[_normalize_host(addr)] = resolved

        clone = proxy.model_copy(deep=True)
        clone.address = resolved
        clone.resolved_ip = resolved

        details = dict(clone.details or {})
        details.setdefault("_origin_id", proxy.id)
        details.setdefault("original_host", addr)
        details["dns_safe"] = True
        if not details.get("sni"):
            details["sni"] = addr
        if (
            not details.get("host")
            and not details.get("http_host")
            and not details.get("ws_host")
        ):
            details["host"] = addr
        if details.get("server_name") is None:
            details["server_name"] = addr
        _rewrite_chain_obs_for_dns(details, host_map)
        clone.details = details

        if isinstance(clone.config, str) and "://" in clone.config:
            _adapter = ShadowrocketAdapter()
            rebuilt = _adapter._reconstruct_uri(clone)
            clone.config = rebuilt or ""

        safe.append(clone)

    return safe, host_map

def build_dns_hardened_proxies(
    proxies: List[Proxy],
) -> Tuple[List[Proxy], Dict[str, str]]:
    hardened: List[Proxy] = []
    host_map: Dict[str, str] = {}
    adapter = ShadowrocketAdapter()

    for proxy in proxies:
        addr = (proxy.address or "").strip()
        if not addr:
            continue

        if _is_ip_literal(addr):
            clone = proxy.model_copy(deep=True)
            details = dict(clone.details or {})
            details["dns_hardened"] = True
            _rewrite_chain_obs_for_dns(details, host_map)
            clone.details = details
            hardened.append(clone)
            continue

        resolved = (proxy.resolved_ip or "").strip()
        if resolved and _is_ip_literal(resolved) and _is_global_ip(resolved):
            host_map[_normalize_host(addr)] = resolved

            clone = proxy.model_copy(deep=True)
            clone.address = resolved
            clone.resolved_ip = resolved

            details = dict(clone.details or {})
            details.setdefault("_origin_id", proxy.id)
            details.setdefault("original_host", addr)
            details["dns_hardened"] = True
            if not details.get("sni"):
                details["sni"] = addr
            if (
                not details.get("host")
                and not details.get("http_host")
                and not details.get("ws_host")
            ):
                details["host"] = addr
            if details.get("server_name") is None:
                details["server_name"] = addr
            _rewrite_chain_obs_for_dns(details, host_map)
            clone.details = details

            if isinstance(clone.config, str) and "://" in clone.config:
                rebuilt = adapter._reconstruct_uri(clone)
                clone.config = rebuilt or ""

            hardened.append(clone)
        else:
            clone = proxy.model_copy(deep=True)
            details = dict(clone.details or {})
            details["dns_hardened"] = True
            _rewrite_chain_obs_for_dns(details, host_map)
            clone.details = details
            hardened.append(clone)

    return hardened, host_map

def _rewrite_outbound_for_dns_safe(
    outbound: Dict[str, Any], host_map: Dict[str, str]
) -> Optional[Dict[str, Any]]:
    server = outbound.get("server")
    if isinstance(server, str) and server:
        if _is_ip_literal(server):
            if not _is_global_ip(server):
                return None
            return outbound
        mapped = host_map.get(_normalize_host(server))
        if not mapped:
            return None
        outbound["server"] = mapped
        tls = outbound.get("tls")
        if isinstance(tls, dict) and not tls.get("server_name"):
            tls = dict(tls)
            tls["server_name"] = server
            outbound["tls"] = tls
    return outbound

def _rewrite_outbound_for_dns_hardened(
    outbound: Dict[str, Any], host_map: Dict[str, str]
) -> Dict[str, Any]:
    server = outbound.get("server")
    if isinstance(server, str) and server:
        if _is_ip_literal(server):
            return outbound
        mapped = host_map.get(_normalize_host(server))
        if mapped:
            outbound["server"] = mapped
            tls = outbound.get("tls")
            if isinstance(tls, dict) and not tls.get("server_name"):
                tls = dict(tls)
                tls["server_name"] = server
                outbound["tls"] = tls
    return outbound

def _prune_dangling_detours(cleaned: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    changed = True
    while changed:
        changed = False
        tags = {o.get("tag") for o in cleaned if o.get("tag")}
        new_cleaned: List[Dict[str, Any]] = []
        for outbound in cleaned:
            detour = outbound.get("detour")
            if detour and detour not in tags:
                changed = True
                continue
            if isinstance(outbound.get("outbounds"), list):
                filtered = [t for t in outbound["outbounds"] if t in tags]
                if not filtered:
                    changed = True
                    continue
                if filtered != outbound["outbounds"]:
                    outbound = dict(outbound)
                    outbound["outbounds"] = filtered
            new_cleaned.append(outbound)
        cleaned = new_cleaned
    return cleaned

def filter_outbounds_for_dns_safe(
    outbounds: List[Dict[str, Any]], host_map: Dict[str, str]
) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for outbound in outbounds:
        if not isinstance(outbound, dict):
            continue
        candidate: Dict[str, Any] = copy.deepcopy(outbound)
        if "server" in candidate:
            rewritten = _rewrite_outbound_for_dns_safe(candidate, host_map)
            if rewritten is None:
                continue
            candidate = rewritten
        cleaned.append(candidate)
    return _prune_dangling_detours(cleaned)

def filter_outbounds_for_dns_hardened(
    outbounds: List[Dict[str, Any]], host_map: Dict[str, str]
) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for outbound in outbounds:
        if not isinstance(outbound, dict):
            continue
        candidate = copy.deepcopy(outbound)
        if "server" in candidate:
            candidate = _rewrite_outbound_for_dns_hardened(candidate, host_map)
        cleaned.append(candidate)
    return _prune_dangling_detours(cleaned)

def _render_dns_comment_block(primary: List[str], fallback: List[str]) -> List[str]:
    lines = ["# DNS resolvers (DoH/DoT/DoQ):"]
    for resolver in primary:
        lines.append(f"# - {resolver}")
    if fallback:
        lines.append("# DNS fallback order:")
        for resolver in fallback:
            lines.append(f"# - {resolver}")
    return lines

def wrap_surge_or_loon_profile(
    adapter_name: str,
    proxies: List[Proxy],
    washed_outbounds: Optional[List[Dict[str, Any]]],
    primary: List[str],
    fallback: List[str],
) -> str:
    adapter = get_adapter(adapter_name)
    content = (
        adapter.export(proxies, washed_outbounds=washed_outbounds)
        if adapter_name in ("surge", "loon")
        else adapter.export(proxies)
    )
    proxy_lines = content.splitlines()
    if proxy_lines and proxy_lines[0].startswith("#"):
        proxy_lines = proxy_lines[1:]
    lines = [
        f"# ConfigStream DNS-hardened profile ({adapter_name})",
        "# Prefer IP when available; SNI/Host pinned for TLS.",
        "[Proxy]",
    ]
    lines.extend(proxy_lines)
    lines.extend(["", "[DNS]"])
    if primary:
        lines.append(f"dns-server = {', '.join(primary)}")
    if fallback:
        lines.append(f"fallback-dns-server = {', '.join(fallback)}")
    return "\n".join(lines).rstrip() + "\n"

def wrap_quantumultx_profile(
    proxies: List[Proxy],
    primary: List[str],
    fallback: List[str],
) -> str:
    adapter = get_adapter("quantumultx")
    content = adapter.export(proxies)
    proxy_lines = content.splitlines()
    lines = [
        "# ConfigStream DNS-hardened profile (quantumultx)",
        "# Prefer IP when available; SNI/Host pinned for TLS.",
        "[server_local]",
    ]
    lines.extend(proxy_lines)
    lines.extend(["", "[dns]"])
    for resolver in primary:
        lines.append(f"server={resolver}")
    for resolver in fallback:
        lines.append(f"server={resolver}")
    return "\n".join(lines).rstrip() + "\n"

def wrap_shadowrocket_profile(
    proxies: List[Proxy],
    primary: List[str],
    fallback: List[str],
) -> str:
    adapter = get_adapter("shadowrocket")
    content = adapter.export(proxies)
    lines = [
        "# ConfigStream DNS-hardened list (Shadowrocket)",
        "# Prefer IP when available; SNI/Host pinned for TLS.",
    ]
    lines.extend(_render_dns_comment_block(primary, fallback))
    if content:
        lines.append("")
        lines.append("# Proxy list")
        lines.extend(content.splitlines())
    return "\n".join(lines).rstrip() + "\n"

def build_wireguard_config(proxy: Proxy) -> Optional[str]:
    details = proxy.details or {}
    private_key = details.get("private_key") or proxy.uuid or ""
    peer_public_key = details.get("peer_public_key") or details.get("public_key") or ""

    local_address = details.get("local_address") or details.get("private_ipv4")
    addresses: List[str] = []
    if isinstance(local_address, list):
        addresses = [str(item) for item in local_address if item]
    elif isinstance(local_address, str) and local_address:
        addresses = [local_address]

    if not private_key or not peer_public_key:
        return None

    allowed_ips = details.get("allowed_ips") or "0.0.0.0/0, ::/0"
    endpoint = f"{proxy.address}:{proxy.port}"
    keepalive = details.get("persistent_keepalive") or details.get("keepalive")
    dns = details.get("dns")

    mtu = details.get("mtu", 1280)
    lines = [
        "[Interface]",
        f"PrivateKey = {private_key}",
    ]
    if addresses:
        lines.append(f"Address = {', '.join(addresses)}")
    lines.append(f"MTU = {mtu}")
    if dns:
        lines.append(f"DNS = {dns}")
    lines.append("")
    lines.extend(
        [
            "[Peer]",
            f"PublicKey = {peer_public_key}",
            f"AllowedIPs = {allowed_ips}",
            f"Endpoint = {endpoint}",
        ]
    )
    if keepalive:
        lines.append(f"PersistentKeepalive = {keepalive}")

    return "\n".join(lines) + "\n"

def generate_quantumultx_profile(
    proxies: List[Proxy],
    primary: List[str],
    fallback: List[str],
) -> str:
    return wrap_quantumultx_profile(proxies, primary, fallback)

def generate_surge_profile(
    proxies: List[Proxy],
    washed_outbounds: Optional[List[Dict[str, Any]]],
    primary: List[str],
    fallback: List[str],
) -> str:
    return wrap_surge_or_loon_profile("surge", proxies, washed_outbounds, primary, fallback)
