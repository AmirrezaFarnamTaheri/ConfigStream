# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Lab chain tester: test a sing-box config via the API server.
Uses singbox2proxy when available; returns structured result for POST /api/lab/test-chain.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from aiohttp_socks import ProxyConnector

from ..security_validator import SecurityValidator
from .utils import SecureConfigContext

import ipaddress
import socket

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / metadata
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT
    ipaddress.ip_network("0.0.0.0/8"),
]


def _is_private_or_local(host: str) -> bool:
    """Return True if host resolves to or IS a private/local/loopback address."""
    try:
        addr = ipaddress.ip_address(host)
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        pass
    try:
        resolved = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for _family, _type, _proto, _canonname, sockaddr in resolved:
            ip = sockaddr[0]
            try:
                addr = ipaddress.ip_address(ip)
                if any(addr in net for net in _PRIVATE_NETWORKS):
                    return True
            except ValueError:
                continue
    except (socket.gaierror, OSError):
        pass
    return False


def _validate_outbound_no_ssrf(outbound: Any, depth: int = 0) -> None:
    """Recursively validate outbound entries for SSRF targets."""
    if depth > 10:
        return
    if not isinstance(outbound, dict):
        raise ValueError(f"outbound entry is not a dict at depth {depth}")
    server = outbound.get("server") or outbound.get("address") or ""
    if server and _is_private_or_local(str(server)):
        raise ValueError(
            f"SSRF rejected: outbound server '{SecurityValidator.sanitize_log_message(str(server))}' "
            "resolves to a private/local address"
        )
    for key in ("outbound", "detour", "next"):
        child = outbound.get(key)
        if isinstance(child, dict):
            _validate_outbound_no_ssrf(child, depth + 1)
        elif isinstance(child, list):
            for item in child:
                if isinstance(item, dict):
                    _validate_outbound_no_ssrf(item, depth + 1)


logger = logging.getLogger(__name__)

_SINGBOX_AVAILABLE: Optional[bool] = None


def _singbox_available() -> bool:
    """Check if singbox2proxy (and thus sing-box) is available."""
    global _SINGBOX_AVAILABLE
    if _SINGBOX_AVAILABLE is not None:
        return _SINGBOX_AVAILABLE
    try:
        from singbox2proxy import SingBoxProxy  # type: ignore

        _SINGBOX_AVAILABLE = SingBoxProxy is not None
    except ImportError:
        _SINGBOX_AVAILABLE = False
    return _SINGBOX_AVAILABLE


def _ensure_config_ready(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure config has required fields for sing-box run.
    Adds inbounds (mixed) if missing; adds minimal log/route if absent.
    """
    cfg = dict(config)
    if "log" not in cfg or not cfg["log"]:
        cfg["log"] = {"level": "warn"}
    if "outbounds" not in cfg or not cfg["outbounds"]:
        raise ValueError("Config must have at least one outbound")
    if "inbounds" not in cfg or not cfg["inbounds"]:
        cfg["inbounds"] = [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 0,
            }
        ]
    if "route" not in cfg or not cfg["route"]:
        cfg["route"] = {"rules": [{"outbound": "direct", "protocol": ["dns"]}]}
    return cfg


async def test_chain_config(
    config: Dict[str, Any],
    timeout: float = 15.0,
    test_url: str = "https://www.google.com/generate_204",
    ipify_url: str = "https://api.ipify.org?format=json",
) -> Dict[str, Any]:
    """
    Test a sing-box chain config. Starts sing-box, measures latency, optionally fetches exit IP.

    Returns:
        { "success": True, "latency": float, "exit_ip": str? } on success
        { "success": False, "error": str } on failure
    """
    if not _singbox_available():
        return {"success": False, "error": "singbox2proxy not installed"}

    try:
        if isinstance(config, dict):
            outbounds = config.get("outbounds", [])
            if isinstance(outbounds, list):
                for ob in outbounds:
                    _validate_outbound_no_ssrf(ob)
        ready_config = _ensure_config_ready(config)
        config_content = json.dumps(ready_config)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    try:
        from singbox2proxy import SingBoxProxy  # type: ignore
    except ImportError:
        return {
            "success": False,
            "error": "singbox2proxy not installed, cannot test chain natively",
        }
    import aiohttp

    loop = asyncio.get_running_loop()
    sb_instance = None
    with SecureConfigContext(config_content) as config_path:
        try:
            sb_instance = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: SingBoxProxy(config_path)),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return {"success": False, "error": "sing-box start timed out"}
        except Exception as e:
            err_msg = SecurityValidator.sanitize_log_message(str(e))
            logger.debug("sing-box start failed: %s", err_msg)
            return {"success": False, "error": f"sing-box start failed: {err_msg}"}

        if not sb_instance or not (
            sb_instance.http_proxy_url or sb_instance.socks5_proxy_url
        ):
            return {"success": False, "error": "No proxy URL from sing-box"}

        proxy_url = sb_instance.http_proxy_url or sb_instance.socks5_proxy_url
        connector = ProxyConnector.from_url(proxy_url)

        latency: Optional[float] = None
        exit_ip: Optional[str] = None

        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                # Measure latency
                start = time.monotonic()
                async with session.get(
                    test_url,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    allow_redirects=False,
                ) as resp:
                    if 200 <= resp.status < 300:
                        latency = (time.monotonic() - start) * 1000
                        latency = round(latency, 2)

                # Fetch exit IP if latency succeeded
                if latency is not None:
                    try:
                        async with session.get(
                            ipify_url,
                            timeout=aiohttp.ClientTimeout(total=5.0),
                            allow_redirects=False,
                        ) as ip_resp:
                            if ip_resp.status == 200:
                                data = await ip_resp.json()
                                exit_ip = (
                                    data.get("ip") if isinstance(data, dict) else None
                                )
                    except Exception:  # nosec B110
                        logging.getLogger(__name__).debug(
                            "Suppressed broad exception", exc_info=True
                        )
                        pass

        except asyncio.TimeoutError:
            return {"success": False, "error": "Connection test timed out"}
        except Exception as e:
            logging.getLogger(__name__).debug(
                "Suppressed broad exception", exc_info=True
            )
            return {
                "success": False,
                "error": SecurityValidator.sanitize_log_message(str(e)),
            }
        finally:
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(None, sb_instance.stop),
                    timeout=5.0,
                )
            except Exception as e:
                logger.debug(
                    "sing-box stop cleanup failed: %s",
                    SecurityValidator.sanitize_log_message(str(e)),
                )

        if latency is None:
            return {"success": False, "error": "Connection test failed"}

        result: Dict[str, Any] = {"success": True, "latency": latency}
        if exit_ip:
            result["exit_ip"] = exit_ip
        return result
