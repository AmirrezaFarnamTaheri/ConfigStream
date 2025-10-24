import base64
import json
from pathlib import Path
from typing import Dict, List, cast

import yaml

from .models import Proxy


def generate_base64_subscription(proxies: List[Proxy]) -> str:
    working_proxies = [p for p in proxies if p.is_working]
    if not working_proxies:
        return ""
    configs = [p.config for p in working_proxies]
    encoded = base64.b64encode("\n".join(configs).encode("utf-8"))
    return encoded.decode("utf-8")


def generate_categorized_outputs(all_proxies: List[Proxy], output_dir: Path) -> Dict[str, str]:
    """
    Generate categorized output files for better organization and smaller file sizes.

    Categories:
    - passed_filters.json: Working proxies with no security issues
    - insecure.json: Proxies with security issues
    - unavailable.json: Proxies that failed connectivity tests
    - by_protocol/: Separate files for each protocol
    - by_country/: Separate files for each country

    Returns:
        Dictionary mapping category names to file paths
    """
    output_files: Dict[str, str] = {}

    # Categorize proxies by status
    passed = [p for p in all_proxies if p.is_working and not p.security_issues]
    insecure = [p for p in all_proxies if p.security_issues]
    unavailable = [p for p in all_proxies if not p.is_working]

    # Helper function to serialize proxy to dict
    def proxy_to_dict(proxy: Proxy) -> Dict:
        return {
            "config": proxy.config,
            "protocol": proxy.protocol,
            "address": proxy.address,
            "port": proxy.port,
            "latency": proxy.latency,
            "country": proxy.country,
            "country_code": proxy.country_code,
            "city": proxy.city,
            "remarks": proxy.remarks,
            "is_working": proxy.is_working,
            "security_issues": proxy.security_issues,
            "tested_at": proxy.tested_at,
        }

    # Generate status-based files
    passed_path = output_dir / "passed_filters.json"
    passed_path.write_text(json.dumps([proxy_to_dict(p) for p in passed], indent=2))
    output_files["passed_filters"] = str(passed_path)

    if insecure:
        insecure_path = output_dir / "insecure.json"
        insecure_path.write_text(json.dumps([proxy_to_dict(p) for p in insecure], indent=2))
        output_files["insecure"] = str(insecure_path)

    if unavailable:
        unavailable_path = output_dir / "unavailable.json"
        unavailable_path.write_text(json.dumps([proxy_to_dict(p) for p in unavailable], indent=2))
        output_files["unavailable"] = str(unavailable_path)

    # Generate protocol-based breakdown
    protocol_dir = output_dir / "by_protocol"
    protocol_dir.mkdir(parents=True, exist_ok=True)

    protocols: Dict[str, List[Proxy]] = {}
    for proxy in passed:
        protocol = proxy.protocol.lower()
        if protocol not in protocols:
            protocols[protocol] = []
        protocols[protocol].append(proxy)

    for protocol, proxies in protocols.items():
        protocol_path = protocol_dir / f"{protocol}.json"
        protocol_path.write_text(json.dumps([proxy_to_dict(p) for p in proxies], indent=2))
        output_files[f"protocol_{protocol}"] = str(protocol_path)

    # Generate country-based breakdown
    country_dir = output_dir / "by_country"
    country_dir.mkdir(parents=True, exist_ok=True)

    countries: Dict[str, List[Proxy]] = {}
    for proxy in passed:
        country_code = proxy.country_code or "unknown"
        if country_code not in countries:
            countries[country_code] = []
        countries[country_code].append(proxy)

    for country_code, proxies in countries.items():
        country_path = country_dir / f"{country_code.lower()}.json"
        country_path.write_text(json.dumps([proxy_to_dict(p) for p in proxies], indent=2))
        output_files[f"country_{country_code}"] = str(country_path)

    # Generate summary stats
    summary = {
        "total_tested": len(all_proxies),
        "passed_filters": len(passed),
        "insecure": len(insecure),
        "unavailable": len(unavailable),
        "by_protocol": {k: len(v) for k, v in protocols.items()},
        "by_country": {k: len(v) for k, v in countries.items()},
    }

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    output_files["summary"] = str(summary_path)

    return output_files


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
