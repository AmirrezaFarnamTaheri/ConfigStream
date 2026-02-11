# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Dict, Any
from ..utils.bool_parser import parse_tls_flag


def add_transport_opts(base: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to add ws/grpc/http options to Clash config."""
    net = details.get("network") or details.get("net") or details.get("type") or "tcp"
    base["network"] = net

    if net == "ws":
        ws_opts: Dict[str, Any] = {}
        if "path" in details:
            ws_opts["path"] = str(details["path"])
        if "host" in details or "sni" in details:
            host_val = details.get("host") or details.get("sni")
            # Prevent str(None) → "None" string corruption
            if host_val and str(host_val).lower() != "none":
                ws_opts["headers"] = {"Host": str(host_val)}
        if ws_opts:
            base["ws-opts"] = ws_opts

    elif net == "grpc":
        grpc_opts: Dict[str, Any] = {}
        if "serviceName" in details:
            grpc_opts["grpc-service-name"] = str(details["serviceName"])
        if grpc_opts:
            base["grpc-opts"] = grpc_opts

    elif net in ("h2", "http"):
        h2_opts: Dict[str, Any] = {}
        if "path" in details:
            h2_opts["path"] = str(details["path"])
        if "host" in details:
            h2_opts["host"] = [str(details["host"])]
        if h2_opts:
            base["h2-opts"] = h2_opts

    # Common TLS fields
    tls_enabled = parse_tls_flag(details.get("tls")) or details.get("security") in [
        "tls",
        "reality",
    ]
    if tls_enabled:
        base["tls"] = True
        if "sni" in details:
            base["servername"] = str(details["sni"])
        if "fp" in details:
            base["client-fingerprint"] = str(details["fp"])
        if details.get("security") == "reality":
            base["client-fingerprint"] = str(details.get("fp", "chrome"))
            # Validate pbk exists - str(None) would create "None" string (data corruption)
            pbk = details.get("pbk")
            if pbk and str(pbk).lower() != "none":
                base["reality-opts"] = {
                    "public-key": str(pbk),
                    "short-id": str(details.get("sid", "") or ""),
                }

    return base
