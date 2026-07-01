# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import re
from typing import Dict, Any
from ..utils.bool_parser import parse_bool, parse_tls_flag
from ..security_validator import SecurityValidator

logger = logging.getLogger(__name__)

# Matches a lone '%' NOT followed by two hex digits (broken percent-encoding)
_BAD_PERCENT_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")


def add_transport_sb(out: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to add transport options for Sing-box."""
    net = details.get("net") or details.get("type") or "tcp"

    transport: Dict[str, Any] = {}

    def _safe_path(raw: str) -> str:
        """Fix broken percent-encoding that crashes sing-box."""
        return _BAD_PERCENT_RE.sub("%25", raw)

    if net == "ws":
        transport["type"] = "ws"
        if "path" in details:
            transport["path"] = _safe_path(str(details["path"]))
        if "host" in details or "sni" in details:
            host_val = details.get("host") or details.get("sni")
            # Prevent str(None) → "None" string corruption
            if host_val and str(host_val).lower() != "none":
                transport["headers"] = {"Host": str(host_val)}
    elif net == "grpc":
        transport["type"] = "grpc"
        if "serviceName" in details:
            service_name = details["serviceName"]
            # Prevent str(None) → "None" string corruption
            if service_name and str(service_name).lower() != "none":
                transport["service_name"] = str(service_name)
    elif net in ("http", "h2"):
        transport["type"] = "http"
        if "path" in details:
            transport["path"] = _safe_path(str(details["path"]))
        if "host" in details:
            transport["host"] = [str(details["host"])]
    # Add httpupgrade transport support per sing-box schema.
    elif net == "httpupgrade":
        transport["type"] = "httpupgrade"
        if "path" in details:
            transport["path"] = _safe_path(str(details["path"]))
        if "host" in details or "sni" in details:
            host_val = details.get("host") or details.get("sni")
            if host_val and str(host_val).lower() != "none":
                transport["host"] = str(host_val)

    if transport:
        out["transport"] = transport

    # Add packet_encoding for VLESS/VMess (critical for UDP support).
    # Without this, UDP traffic is silently dropped by some servers.
    if out.get("type") in ("vless", "vmess"):
        pkt_enc = details.get("packet_encoding") or details.get("packetEncoding")
        if pkt_enc and str(pkt_enc).lower() in ("xudp", "packetaddr"):
            out["packet_encoding"] = str(pkt_enc).lower()
        elif out.get("type") == "vless":
            # Default to xudp for VLESS (recommended by sing-box docs)
            out["packet_encoding"] = "xudp"

    # TLS
    security = details.get("security", "")

    tls_enabled = (
        parse_tls_flag(details.get("tls"))
        or security in ["tls", "reality"]
        or out.get("type") == "trojan"
    )

    if tls_enabled:
        tls: Dict[str, Any] = {"enabled": True}
        if "sni" in details:
            tls["server_name"] = str(details["sni"])

        # Ensure uTLS fingerprint is set for Reality (required).
        fp = details.get("fp")
        if not fp and security == "reality":
            fp = "chrome"  # Default for Reality

        if fp:
            tls["utls"] = {"enabled": True, "fingerprint": str(fp)}

        # Map insecure flags (CRITICAL FIX)
        # Force insecure=True for testing stability on free proxies if needed,
        # but keeping strict check unless explicitly insecure for general cases,
        # except Hysteria/TUIC which are handled separately.
        if (
            parse_bool(details.get("allowInsecure"))
            or parse_bool(details.get("insecure"))
            or parse_bool(details.get("skip_cert_verify"))
        ):
            tls["insecure"] = True
            logger.debug(
                "Enabled insecure TLS for %s",
                SecurityValidator.sanitize_log_message(str(out.get("server"))),
            )

        if security == "reality":
            # Validate pbk exists - str(None) would create "None" string (data corruption)
            pbk = details.get("pbk")
            if pbk and str(pbk).lower() != "none":
                tls["reality"] = {
                    "enabled": True,
                    "public_key": str(pbk),
                    "short_id": str(details.get("sid", "") or ""),
                }
            else:
                # Fail validation for Reality without PBK
                logger.debug(
                    "Skipping invalid Reality TLS for %s: missing pbk",
                    SecurityValidator.sanitize_log_message(str(out.get("server"))),
                )
                return {}  # Return empty dict to signal failure

        out["tls"] = tls

    return out


def apply_stealth_profile(
    outbound_config: Dict[str, Any], protocol: str
) -> Dict[str, Any]:
    """
    Injects anti-censorship features (Multiplexing, Padding, Headers).
    Only applies to TCP-based protocols (VMess, VLESS, Trojan).
    """
    # NOTE: 'brutal' and 'multiplex' are disabled by default for testing
    # because they require specific client/kernel support (TCP Brutal)
    # which causes tests to fail in standard CI/Docker environments.

    # 2. Browser Mimicry (The "Camouflage" Layer)
    # If transport is WebSocket or HTTP, enforce User-Agent.
    transport = outbound_config.get("transport", {})
    if transport.get("type") in ["ws", "http"]:
        headers = transport.get("headers", {})
        # Overwrite or add User-Agent if missing
        if "User-Agent" not in headers:
            headers["User-Agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        transport["headers"] = headers
        outbound_config["transport"] = transport

    return outbound_config
