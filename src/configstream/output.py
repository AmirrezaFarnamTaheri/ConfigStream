import base64
import json
from typing import List, cast

import yaml

from .models import Proxy


def generate_base64_subscription(proxies: List[Proxy]) -> str:
    working_proxies = [p for p in proxies if p.is_working]
    if not working_proxies:
        return ""
    configs = [p.config for p in working_proxies]
    encoded = base64.b64encode("\n".join(configs).encode("utf-8"))
    return encoded.decode("utf-8")


def generate_clash_config(proxies: List[Proxy]) -> str:
    working_proxies = [p for p in proxies if p.is_working]
    clash_proxies = []
    for proxy in working_proxies:
        proxy_data = {
            "name": proxy.remarks or f"{proxy.protocol}-{proxy.address}",
            "type": proxy.protocol,
            "server": proxy.address,
            "port": proxy.port,
            "uuid": proxy.uuid,
        }
        if proxy.details:
            proxy_data.update(proxy.details)
        clash_proxies.append(proxy_data)

    clash_yaml = yaml.dump(
        {
            "proxies": clash_proxies,
            "proxy-groups": [
                {
                    "name": "🚀 ConfigStream",
                    "type": "select",
                    "proxies": [p["name"] for p in clash_proxies],
                }
            ],
        }
    )
    return cast(str, clash_yaml)


def generate_singbox_config(proxies: List[Proxy]) -> str:
    working_proxies = [p for p in proxies if p.is_working]
    outbounds = []
    for index, proxy in enumerate(working_proxies, start=1):
        outbound = {
            "type": proxy.protocol.lower(),
            "tag": proxy.remarks or f"{proxy.protocol}-{index}",
            "server": proxy.address,
            "server_port": proxy.port,
        }
        if proxy.uuid:
            outbound["uuid"] = proxy.uuid
        if proxy.details:
            outbound.update(proxy.details)
        outbounds.append(outbound)
    return json.dumps({"outbounds": outbounds}, indent=2)


def generate_shadowrocket_subscription(proxies: List[Proxy]) -> str:
    working = [p for p in proxies if p.is_working]
    lines = []
    for proxy in working:
        name = proxy.remarks or f"{proxy.protocol}-{proxy.address}"
        lines.append(f"{name} = {proxy.config}")  # use the raw config
    return base64.b64encode("\n".join(lines).encode("utf-8")).decode("utf-8")


def generate_quantumult_config(proxies: List[Proxy]) -> str:
    working_proxies = [p for p in proxies if p.is_working]
    lines = ["[SERVER]"]
    for proxy in working_proxies:
        name = proxy.remarks or f"{proxy.protocol}-{proxy.address}"
        lines.append(
            f"{name} = {proxy.protocol.lower()}, {proxy.address}, {proxy.port}, "
            f"password={proxy.details.get('password', '') if proxy.details else ''}"
        )
    return "\n".join(lines)


def generate_surge_config(proxies: List[Proxy]) -> str:
    working_proxies = [p for p in proxies if p.is_working]
    lines = ["[Proxy]"]
    for proxy in working_proxies:
        name = proxy.remarks or f"{proxy.protocol}-{proxy.address}"
        password = proxy.details.get("password", "") if proxy.details else ""
        surge_line = (
            f"{name} = {proxy.protocol.upper()}, {proxy.address}, "
            f"{proxy.port}, username={proxy.uuid}, password={password}"
        )
        lines.append(surge_line)
    return "\n".join(lines)
