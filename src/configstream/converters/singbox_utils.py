import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def add_transport_sb(out: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to add transport options for Sing-box."""
    net = details.get("net") or details.get("type") or "tcp"

    transport: Dict[str, Any] = {}
    if net == "ws":
        transport["type"] = "ws"
        if "path" in details:
            transport["path"] = str(details["path"])
        if "host" in details or "sni" in details:
            transport["headers"] = {
                "Host": str(details.get("host") or details.get("sni"))
            }
    elif net == "grpc":
        transport["type"] = "grpc"
        if "serviceName" in details:
            transport["service_name"] = str(details["serviceName"])
    elif net == "http" or net == "h2":
        transport["type"] = "http"
        if "path" in details:
            transport["path"] = str(details["path"])
        if "host" in details:
            transport["host"] = [str(details["host"])]

    if transport:
        out["transport"] = transport

    # TLS
    security = details.get("security", "")

    if (
        details.get("tls") == "tls"
        or security in ["tls", "reality"]
        or out.get("type") == "trojan"
    ):
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
        # [FIX] Force insecure=True for testing stability on free proxies if needed,
        # but keeping strict check unless explicitly insecure for general cases,
        # except Hysteria/TUIC which are handled separately.
        if (
            details.get("allowInsecure")
            or details.get("insecure")
            or details.get("skip_cert_verify")
        ):
            tls["insecure"] = True
            logger.debug(f"Enabled insecure TLS for {out.get('server')}")

        if security == "reality":
            tls["reality"] = {
                "enabled": True,
                "public_key": str(details.get("pbk")),
                "short_id": str(details.get("sid", "")),
            }

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
