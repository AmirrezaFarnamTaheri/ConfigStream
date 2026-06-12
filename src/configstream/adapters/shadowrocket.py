# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import base64
import json
import urllib.parse
from typing import List, Optional, Dict, Any
from ..models import Proxy
from ..security_validator import _safe_proxy_ref
from .common import Adapter
from ..utils.bool_parser import parse_tls_flag
from ..utils.net import is_ip_literal as _is_ip_literal
from ..converters.chains import chain_outbounds_from_details

logger = logging.getLogger(__name__)


class ShadowrocketAdapter(Adapter):
    """Export to Shadowrocket format."""

    def _update_fragment(self, raw: str, safe_name: str) -> str:
        base = raw.split("#", 1)[0].strip()
        if not safe_name:
            return base
        return f"{base}#{safe_name}"

    def _rewrite_vmess_name(
        self, raw: str, raw_name: str, safe_name: str
    ) -> Optional[str]:
        if not raw_name:
            return raw
        try:
            payload = raw.split("://", 1)[1].strip()
        except IndexError:
            return None

        padded = payload + "=" * (-len(payload) % 4)
        for decoder in (base64.b64decode, base64.urlsafe_b64decode):
            try:
                decoded = decoder(padded.encode())
                data = json.loads(decoded)
                if not isinstance(data, dict):
                    continue
                data["ps"] = raw_name
                encoded = base64.b64encode(
                    json.dumps(data, ensure_ascii=False).encode()
                ).decode()
                return f"vmess://{encoded}#{safe_name}"
            except Exception:
                continue
        return None

    def _extract_revived_uri(self, p: Proxy) -> Optional[str]:
        details = p.details or {}
        tag = "Revived" if not details.get("use_vwarp") else "Revived-VWARP"
        prefer_chain_first = bool(
            details.get("dns_safe") or details.get("dns_hardened")
        )

        def _extract_from_chain() -> Optional[str]:
            chain_obs = chain_outbounds_from_details(details)
            if chain_obs:
                from ..generators.plaintext import _proxy_from_outbound

                for ob in chain_obs:
                    if not isinstance(ob, dict) or ob.get("type") == "wireguard":
                        continue
                    relay_proxy = _proxy_from_outbound(ob, remark_prefix=f"[{tag}] ")
                    if relay_proxy:
                        uri_value = self._reconstruct_uri(relay_proxy)
                        if uri_value:
                            return uri_value
                for ob in chain_obs:
                    if not isinstance(ob, dict):
                        continue
                    wg_proxy = _proxy_from_outbound(ob, remark_prefix=f"[{tag}] ")
                    if wg_proxy:
                        uri_value = self._reconstruct_uri(wg_proxy)
                        if uri_value:
                            return uri_value
            return None

        if prefer_chain_first:
            chain_uri = _extract_from_chain()
            if chain_uri:
                return chain_uri

        origin = details.get("origin_proxy") or details.get("origin_config")
        if origin and isinstance(origin, dict):
            try:
                origin_p = Proxy(**origin)
                if prefer_chain_first:
                    resolved_ip = str(
                        origin.get("resolved_ip")
                        or (origin.get("details") or {}).get("resolved_ip")
                        or ""
                    ).strip()
                    if resolved_ip and _is_ip_literal(resolved_ip):
                        origin_p.address = resolved_ip
                        origin_p.resolved_ip = resolved_ip
                origin_p.remarks = f"[{tag}] {origin_p.remarks or origin_p.protocol}"
                uri = self._reconstruct_uri(origin_p)
                if uri:
                    return uri
            except Exception:
                pass

        return _extract_from_chain()

    def export(
        self,
        proxies: List[Proxy],
        washed_outbounds: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        lines = []
        reconstructed_count = 0
        for p in proxies:
            if p.protocol == "revived" or str(p.config).lower().startswith(
                "revived://"
            ):
                uri = self._extract_revived_uri(p)
                if uri:
                    lines.append(uri)
                    reconstructed_count += 1
                continue

            raw_cfg = (p.config or "").strip()
            if raw_cfg.startswith("{") and (p.details or {}).get("is_chain"):
                try:
                    cfg = json.loads(raw_cfg)
                    outbounds = cfg.get("outbounds", [])
                    if isinstance(outbounds, list):
                        from ..generators.plaintext import _proxy_from_outbound

                        for ob in outbounds:
                            if not isinstance(ob, dict):
                                continue
                            ob_proxy = _proxy_from_outbound(
                                ob, remark_prefix="[Chain] "
                            )
                            if ob_proxy:
                                uri = self._reconstruct_uri(ob_proxy)
                                if uri:
                                    lines.append(uri)
                                    reconstructed_count += 1
                                    break
                except (json.JSONDecodeError, TypeError):
                    pass
                continue

            if p.config and "://" in p.config:
                raw = p.config.strip()
                scheme = raw.split("://", 1)[0].lower()
                raw_fragment = ""
                if "#" in raw:
                    raw_fragment = raw.split("#", 1)[1]
                raw_name = (
                    p.remarks or urllib.parse.unquote(raw_fragment) or "ConfigStream"
                )
                safe_name = (
                    urllib.parse.quote(raw_name)
                    if p.remarks or not raw_fragment
                    else raw_fragment
                )

                if scheme == "socks":
                    uri = self._reconstruct_uri(p, name_override=raw_name)
                    if uri:
                        lines.append(uri)
                        reconstructed_count += 1
                        continue

                if scheme == "vmess":
                    updated = self._rewrite_vmess_name(raw, raw_name, safe_name)
                    if updated:
                        lines.append(updated)
                        continue

                lines.append(self._update_fragment(raw, safe_name))
                continue

            try:
                uri = self._reconstruct_uri(p)
                if uri:
                    lines.append(uri)
                    reconstructed_count += 1
            except Exception as e:
                logger.debug(f"Failed to reconstruct URI for {_safe_proxy_ref(p)}: {e}")

        logger.info(
            f"Shadowrocket export summary: {len(lines)} links (Reconstructed: {reconstructed_count})"
        )
        return "\n".join(lines)

    def _reconstruct_uri(self, p: Proxy, name_override: Optional[str] = None) -> str:
        name = urllib.parse.quote(name_override or p.remarks or "ConfigStream")

        def _join_list(value: Any) -> str:
            if isinstance(value, (list, tuple)):
                return ",".join(str(item) for item in value if item)
            return str(value) if value is not None else ""

        if p.protocol in ("ss", "shadowsocks"):
            method = p.details.get("method", "chacha20-ietf-poly1305")
            password = p.details.get("password", "")
            userpass = f"{method}:{password}"
            b64_auth = base64.urlsafe_b64encode(userpass.encode()).decode().rstrip("=")
            plugin_part = ""
            if "plugin" in p.details:
                plugin = p.details["plugin"]
                opts = p.details.get("plugin_opts", "")
                plugin_str = urllib.parse.quote(f"{plugin};{opts}")
                plugin_part = f"plugin={plugin_str}"
            query = f"?{plugin_part}" if plugin_part else ""
            return f"ss://{b64_auth}@{p.address}:{p.port}{query}#{name}"

        elif p.protocol == "trojan":
            params = {}
            sni = p.details.get("sni", "")
            if sni:
                params["peer"] = sni
                params["sni"] = sni
            net = p.details.get("net") or p.details.get("type")
            if net:
                params["type"] = net
            path = (
                p.details.get("path")
                or p.details.get("ws_path")
                or p.details.get("http_path")
            )
            if path:
                params["path"] = path
            host = p.details.get("host") or p.details.get("http_host")
            if host:
                params["host"] = host
            service_name = p.details.get("serviceName") or p.details.get(
                "grpc_service_name"
            )
            if service_name:
                params["serviceName"] = service_name
            query = urllib.parse.urlencode(params, safe=",") if params else ""
            query_part = f"?{query}" if query else ""
            return f"trojan://{p.uuid}@{p.address}:{p.port}{query_part}#{name}"

        elif p.protocol == "vmess":
            tls_enabled = parse_tls_flag(p.details.get("tls")) or p.details.get(
                "security"
            ) in ("tls", "reality")
            net = p.details.get("net") or p.details.get("type") or "tcp"
            v_obj = {
                "v": "2",
                "ps": p.remarks or "ConfigStream",
                "add": p.address,
                "port": str(p.port),
                "id": p.uuid,
                "aid": "0",
                "net": net,
                "type": "none",
                "host": p.details.get("host", ""),
                "tls": "tls" if tls_enabled else "",
            }
            path = p.details.get("path") or p.details.get("ws_path")
            if path:
                v_obj["path"] = path
            sni = p.details.get("sni")
            if sni:
                v_obj["sni"] = sni
            alpn = p.details.get("alpn")
            if alpn:
                v_obj["alpn"] = _join_list(alpn)
            fp = p.details.get("fp") or p.details.get("fingerprint")
            if fp:
                v_obj["fp"] = fp
            return "vmess://" + base64.b64encode(json.dumps(v_obj).encode()).decode()

        elif p.protocol == "vless":
            params = {}
            security = p.details.get("security")
            if not security:
                security = "tls" if parse_tls_flag(p.details.get("tls")) else "none"
            if security:
                params["security"] = security
            sni = p.details.get("sni", "")
            if sni:
                params["sni"] = sni
            net = p.details.get("net") or p.details.get("type") or "tcp"
            if net:
                params["type"] = net
            flow = p.details.get("flow")
            if flow:
                params["flow"] = flow
            encryption = p.details.get("encryption")
            if encryption:
                params["encryption"] = encryption
            host = p.details.get("host") or p.details.get("http_host")
            if host:
                params["host"] = host
            path = (
                p.details.get("path")
                or p.details.get("ws_path")
                or p.details.get("http_path")
            )
            if path:
                params["path"] = path
            service_name = p.details.get("serviceName") or p.details.get(
                "grpc_service_name"
            )
            if service_name:
                params["serviceName"] = service_name
            pbk = (
                p.details.get("pbk")
                or p.details.get("publicKey")
                or p.details.get("public_key")
            )
            if pbk:
                params["pbk"] = pbk
            sid = (
                p.details.get("sid")
                or p.details.get("shortId")
                or p.details.get("short_id")
            )
            if sid:
                params["sid"] = sid
            fp = p.details.get("fp") or p.details.get("fingerprint")
            if fp:
                params["fp"] = fp
            alpn = p.details.get("alpn")
            if alpn:
                params["alpn"] = _join_list(alpn)
            query = urllib.parse.urlencode(params, safe=",") if params else ""
            query_part = f"?{query}" if query else ""
            return f"vless://{p.uuid}@{p.address}:{p.port}{query_part}#{name}"

        elif p.protocol in ("hysteria2", "hy2"):
            sni = p.details.get("sni", "")
            params = {}
            if sni:
                params["sni"] = sni
            alpn = p.details.get("alpn")
            if alpn:
                params["alpn"] = _join_list(alpn)
            query = urllib.parse.urlencode(params, safe=",") if params else ""
            query_part = f"?{query}" if query else ""
            return f"hysteria2://{p.uuid}@{p.address}:{p.port}{query_part}#{name}"

        elif p.protocol == "tuic":
            sni = p.details.get("sni", "")
            password = p.details.get("password", "")
            query = f"?sni={urllib.parse.quote(sni)}" if sni else ""
            return f"tuic://{p.uuid}:{password}@{p.address}:{p.port}{query}#{name}"

        elif p.protocol in ("http", "socks5", "socks4", "socks"):
            scheme = "socks5" if p.protocol == "socks" else p.protocol
            if scheme == "http":
                scheme = "https" if parse_tls_flag(p.details.get("tls")) else "http"
            user = p.uuid or ""
            password = p.details.get("password", "")
            auth = ""
            if user:
                auth_user = urllib.parse.quote(user)
                if password:
                    auth_pass = urllib.parse.quote(password)
                    auth = f"{auth_user}:{auth_pass}@"
                else:
                    auth = f"{auth_user}@"
            return f"{scheme}://{auth}{p.address}:{p.port}#{name}"

        elif p.protocol == "wireguard":
            priv = p.details.get("private_key", "")
            pub = p.details.get("peer_public_key", "")
            if not priv or not pub:
                return ""
            wg_params: Dict[str, str] = {"publickey": pub}
            local_addr = p.details.get("local_address")
            if isinstance(local_addr, list) and local_addr:
                wg_params["address"] = ",".join(str(a) for a in local_addr)
            elif isinstance(local_addr, str) and local_addr:
                wg_params["address"] = local_addr
            reserved = p.details.get("reserved")
            if isinstance(reserved, list) and reserved:
                wg_params["reserved"] = ",".join(str(r) for r in reserved)
            mtu = p.details.get("mtu")
            if mtu:
                wg_params["mtu"] = str(mtu)
            query = urllib.parse.urlencode(wg_params) if wg_params else ""
            query_part = f"?{query}" if query else ""
            encoded_key = urllib.parse.quote(priv, safe="")
            return f"wireguard://{encoded_key}@{p.address}:{p.port}{query_part}#{name}"

        return ""
