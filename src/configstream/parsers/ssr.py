import logging
from typing import Optional
from urllib.parse import parse_qs
from ..models import Proxy
from .base import safe_b64_decode, validate_b64_input

logger = logging.getLogger(__name__)


def _b64_normalize(s: str) -> str:
    # Convert urlsafe to standard and pad
    s = s.replace("-", "+").replace("_", "/")
    return s + "=" * (-len(s) % 4)


def parse_ssr(config: str) -> Optional[Proxy]:
    try:
        if not config.startswith("ssr://"):
            return None

        payload = config[len("ssr://") :]
        if len(payload) > 4096:
            return None

        # 1) decode the entire payload first
        decoded_all = safe_b64_decode(_b64_normalize(payload))
        if decoded_all is None or not decoded_all:
            return None

        # 2) split AFTER decoding
        main, _, qs = decoded_all.partition("/?")

        # 3) parse the main part
        parts = main.split(":", 5)
        if len(parts) != 6:
            logger.debug(
                "Invalid SSR payload: expected 6 colon-separated parts, got %d (%r)",
                len(parts),
                main[:120],
            )
            return None

        server, port_str, protocol, cipher, obfs, pwd_part = parts
        if len(server) > 255:
            return None

        try:
            port = int(port_str)
        except (ValueError, TypeError):
            logger.debug("Invalid port in shadowsocksr config: %s", port_str)
            return None
        if not (1 <= port <= 65535):
            return None

        # Password may be base64 (urlsafe, no pad); some generators also put it plain.
        password = safe_b64_decode(_b64_normalize(pwd_part))

        # 4) parse params; keep blanks
        raw_params = parse_qs(qs, keep_blank_values=True)
        params_decoded: dict[str, str] = {}

        for k, vals in raw_params.items():
            if not vals:
                continue
            val = vals[0]
            if val == "":
                params_decoded[k] = ""
                continue

            v_norm = _b64_normalize(val)
            decoded_val = safe_b64_decode(v_norm)

            if decoded_val is None:
                decoded_val = val

            # If it wasn't valid base64, don't fail hard—keep original.
            elif decoded_val == v_norm and validate_b64_input(v_norm) is None:
                logger.debug(
                    "SSR param '%s' not valid base64: %s; leaving as-is.", k, repr(val)
                )
                decoded_val = val

            params_decoded[k] = decoded_val

        # remarks is already decoded in params_decoded; don’t decode twice
        remarks = params_decoded.get("remarks", "")

        return Proxy(
            config=config,
            protocol="ssr",
            address=server,
            port=port,
            remarks=remarks,
            details={
                "protocol": protocol,
                "cipher": cipher,
                "obfs": obfs,
                "password": password,
                "params": params_decoded,
            },
        )
    except (ValueError, IndexError) as e:
        logger.debug("Failed to parse SSR: %s", e)
        return None
