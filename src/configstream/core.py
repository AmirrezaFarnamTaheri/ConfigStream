import asyncio
import logging
import re
from typing import Any, Dict, Optional

import aiohttp

from .parsers import (
    _parse_generic,
    _parse_hysteria,
    _parse_hysteria2,
    _parse_naive,
    _parse_ss,
    _parse_ssr,
    _parse_trojan,
    _parse_tuic,
    _parse_v2ray_json,
    _parse_vless,
    _parse_vmess,
    _parse_wireguard,
    _parse_xray,
)

from .models import Proxy
from .countries import COUNTRY_NAMES

logger = logging.getLogger(__name__)


_FLAG_PATTERN = re.compile(r"[\U0001F1E6-\U0001F1FF]{2}")
_CODE_PATTERN = re.compile(r"(?<![A-Z0-9])([A-Z]{2})(?![A-Z0-9])")


def _normalise_defaults(proxy: Proxy) -> None:
    proxy.country = proxy.country or "Unknown"
    proxy.country_code = proxy.country_code or "XX"
    proxy.city = proxy.city or "Unknown"
    proxy.asn = proxy.asn or "AS0"


def _flag_to_country_code(flag: str) -> Optional[str]:
    if len(flag) != 2:
        return None
    code_points = [ord(char) - 0x1F1E6 + ord("A") for char in flag]
    if any(point < ord("A") or point > ord("Z") for point in code_points):
        return None
    return "".join(chr(point) for point in code_points)


def _country_payload_from_code(code: str) -> Optional[Dict[str, str]]:
    code = code.upper()
    if code not in COUNTRY_NAMES:
        return None
    return {"country_code": code, "country": COUNTRY_NAMES[code]}


def _infer_country_from_remarks(remarks: str) -> Optional[Dict[str, str]]:
    if not remarks:
        return None

    flag_match = _FLAG_PATTERN.search(remarks)
    if flag_match:
        code = _flag_to_country_code(flag_match.group())
        if code:
            payload = _country_payload_from_code(code)
            if payload:
                return payload

    code_match = _CODE_PATTERN.search(remarks.upper())
    if code_match:
        payload = _country_payload_from_code(code_match.group(1))
        if payload:
            return payload

    return None


async def _lookup_geoip_http(
    address: str,
    session: Optional[aiohttp.ClientSession] = None,
    timeout_seconds: float = 5.0,
) -> Optional[Dict[str, Any]]:
    if not address:
        return None

    owns_session = False
    client_session = session

    if client_session is None:
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        client_session = aiohttp.ClientSession(timeout=timeout)
        owns_session = True

    try:
        url = f"http://ip-api.com/json/{address}?fields=status,country,countryCode,city,as"
        async with client_session.get(url) as response:
            if response.status != 200:
                return None
            payload = await response.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        return None
    finally:
        if owns_session and client_session is not None:
            await client_session.close()

    if payload.get("status") != "success":
        return None

    asn_value = payload.get("as") or ""
    asn = None
    if isinstance(asn_value, str):
        parts = asn_value.split()
        if parts and parts[0].startswith("AS"):
            asn = parts[0]

    return {
        "country": payload.get("country") or "Unknown",
        "country_code": payload.get("countryCode") or "XX",
        "city": payload.get("city") or "Unknown",
        "asn": asn or "AS0",
    }


def parse_config(config_string: str) -> Proxy | None:
    if not config_string or not isinstance(config_string, str):
        return None

    config_string = config_string.strip()
    if not config_string or config_string.startswith("#"):
        return None

    try:
        if config_string.startswith("vmess://"):
            return _parse_vmess(config_string)
        if config_string.startswith("vless://"):
            return _parse_vless(config_string)
        if config_string.startswith("ss://"):
            return _parse_ss(config_string)
        if config_string.startswith("ssr://"):
            return _parse_ssr(config_string)
        if config_string.startswith("trojan://"):
            return _parse_trojan(config_string)
        if config_string.startswith("hysteria://"):
            return _parse_hysteria(config_string)
        if config_string.startswith("hy2://") or config_string.startswith("hysteria2://"):
            return _parse_hysteria2(config_string)
        if config_string.startswith("tuic://"):
            return _parse_tuic(config_string)
        if config_string.startswith("wg://") or config_string.startswith("wireguard://"):
            return _parse_wireguard(config_string)
        if config_string.startswith("naive+https://"):
            return _parse_naive(config_string)
        if config_string.startswith("xray://") or config_string.startswith("xtls://"):
            return _parse_xray(config_string)
        if config_string.lstrip().startswith("{"):
            parsed_v2ray = _parse_v2ray_json(config_string)
            if parsed_v2ray:
                return parsed_v2ray
        if any(
            config_string.startswith(f"{p}://")
            for p in ["ssh", "http", "https", "socks", "socks4", "socks5"]
        ):
            return _parse_generic(config_string)

        logger.debug(f"Unknown protocol in config: {config_string[:50]}...")
        return None

    except Exception as e:
        logger.debug(f"Error parsing config: {e}")
        return None


def parse_config_batch(config_strings: list[str]) -> list[Proxy]:
    parsed = []
    for config_string in config_strings:
        proxy = parse_config(config_string)
        if proxy is not None:
            parsed.append(proxy)
    return parsed


async def geolocate_proxy(
    proxy: Proxy,
    geoip_reader=None,
    *,
    session: Optional[aiohttp.ClientSession] = None,
) -> Proxy:
    _normalise_defaults(proxy)

    if proxy.country_code not in {"", "XX"} and proxy.country in {"", "Unknown"}:
        mapped = _country_payload_from_code(proxy.country_code)
        if mapped:
            proxy.country = mapped["country"]

    if proxy.country_code not in {"", "XX"} and proxy.country != "Unknown":
        return proxy

    inferred = _infer_country_from_remarks(proxy.remarks)
    if inferred:
        proxy.country = inferred["country"]
        proxy.country_code = inferred["country_code"]
        return proxy

    if geoip_reader is not None:
        try:
            response = geoip_reader.city(proxy.address)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("GeoIP database lookup failed for %s: %s", proxy.address, exc)
        else:
            proxy.country = response.country.name or "Unknown"
            proxy.country_code = response.country.iso_code or "XX"
            proxy.city = response.city.name or "Unknown"
            autonomous = getattr(response, "autonomous_system", None)
            if autonomous and autonomous.autonomous_system_number:
                proxy.asn = f"AS{autonomous.autonomous_system_number}"
            else:
                proxy.asn = proxy.asn or "AS0"
            return proxy

    http_result = await _lookup_geoip_http(proxy.address, session=session)
    if http_result:
        proxy.country = http_result["country"]
        proxy.country_code = http_result["country_code"]
        proxy.city = http_result["city"]
        proxy.asn = http_result.get("asn", "AS0") or "AS0"
        return proxy

    return proxy
