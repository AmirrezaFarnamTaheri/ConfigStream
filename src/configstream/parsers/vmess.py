# SPDX-License-Identifier: AGPL-3.0-or-later
import binascii
import json
import logging
from typing import Optional
from pydantic import ValidationError
from ..models import Proxy
from ..constants import MAX_CONFIG_LINE_LENGTH
from .base import normalize_proxy_details, safe_b64_decode
from ..security_validator import safe_log_text

logger = logging.getLogger(__name__)


def parse_vmess(config: str) -> Optional[Proxy]:
    try:
        if not config.startswith("vmess://"):
            return None
        data = config[len("vmess://") :]

        # Use safe_b64_decode to handle URL-encoding and padding automatically
        decoded = safe_b64_decode(data)
        if decoded is None:
            return None

        # safe_b64_decode returns original data on failure; check if it looks like JSON
        if not decoded.strip().startswith("{"):
            return None

        if MAX_CONFIG_LINE_LENGTH > 0 and len(decoded) > MAX_CONFIG_LINE_LENGTH:
            logger.warning("VMess decoded data too large: %d bytes", len(decoded))
            return None

        vmess_data = json.loads(decoded)

        if not all(k in vmess_data for k in ["add", "port", "id"]):
            return None

        try:
            port = int(vmess_data["port"])
        except (ValueError, TypeError):
            return None

        if not (1 <= port <= 65535):
            return None

        address = vmess_data["add"]
        if not address or len(str(address)) > 255:
            return None

        uuid = vmess_data["id"]
        # Basic UUID length check (standard is 36, but some implementations use different IDs)
        if not uuid or len(str(uuid)) > 100:
            return None

        # Respect AlterID if provided, otherwise default to 0 (AEAD mode)
        if "aid" in vmess_data:
            try:
                vmess_data["aid"] = int(vmess_data["aid"])
            except (ValueError, TypeError):
                vmess_data["aid"] = 0
        else:
            vmess_data["aid"] = 0

        ps = vmess_data.get("ps", "")
        if isinstance(ps, str):
            ps = ps[:200]
        else:
            ps = str(ps)[:200]

        # Build a schema-clean details dict: only include keys allowed by
        # proxy.schema.json #/$defs/vmess_details (additionalProperties: false).
        # Remap legacy vmess-URI keys to their canonical schema names.
        details: dict = {}
        # Remap id -> uuid (required by vmess_details schema)
        if "id" in vmess_data:
            details["uuid"] = vmess_data["id"]
        # aid is allowed as-is
        if "aid" in vmess_data:
            details["aid"] = vmess_data["aid"]
        # net, type, host, path are all allowed
        for key in ("net", "type", "host", "path"):
            if key in vmess_data:
                details[key] = vmess_data[key]
        # Remap scy -> security (legacy alias)
        if "scy" in vmess_data:
            details["security"] = vmess_data["scy"]
        # tls, sni, fp, fingerprint, alpn, server_name are all allowed
        for key in ("tls", "sni", "fp", "fingerprint", "alpn", "server_name"):
            if key in vmess_data:
                details[key] = vmess_data[key]
        # grpc_service_name is allowed (grpc-specific)
        if "servicename" in vmess_data:
            details["grpc_service_name"] = vmess_data["servicename"]
        # http_host, ws_host are allowed; ws/http paths
        for key in ("http_host", "ws_host", "http_path", "ws_path"):
            if key in vmess_data:
                details[key] = vmess_data[key]
        # StreamLabs / HTTP/2 specific
        if "serviceName" in vmess_data:
            details["serviceName"] = vmess_data["serviceName"]
        # allowInsecure and skip_cert_verify are allowed (canonical names)
        for key in ("allowInsecure", "skip_cert_verify"):
            if key in vmess_data:
                details[key] = vmess_data[key]
        # Remap legacy aliases for TLS verification flags
        if "insecure" in vmess_data and "allowInsecure" not in details:
            details["allowInsecure"] = bool(vmess_data["insecure"])
        if "skip-cert-verify" in vmess_data and "skip_cert_verify" not in details:
            details["skip_cert_verify"] = bool(vmess_data["skip-cert-verify"])
        # Drop legacy/top-level keys that must NOT appear in details:
        # add, port, id, ps, v, scy (already remapped above), encrypt, etc.
        for key in (
            "add",
            "port",
            "id",
            "ps",
            "v",
            "scy",
            "encrypt",
            "insecure",
            "skip-cert-verify",
            "pcs",
            "vcn",
        ):
            details.pop(key, None)

        proxy = Proxy(
            config=config,
            protocol="vmess",
            address=str(address),
            port=port,
            uuid=str(uuid),
            remarks=ps,
            details=details,
        )
        normalize_proxy_details(proxy)
        return proxy
    except (
        ValidationError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        TimeoutError,
        IndexError,
        TypeError,
        binascii.Error,
    ) as e:
        logger.debug("Failed to parse VMess: %s", safe_log_text(str(e)[:100]))
        return None
