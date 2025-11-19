from __future__ import annotations

from typing import List
from .models import Proxy


def _proxies_to_json(proxies: List[Proxy]) -> List[dict]:
    return [
        {
            "config": p.config,
            "protocol": p.protocol,
            "address": p.address,
            "port": p.port,
            "latency": p.latency,
            "country": p.country,
            "country_code": p.country_code,
            "city": p.city,
            "remarks": p.remarks,
            "is_working": p.is_working,
            "security_issues": p.security_issues,
            "tested_at": p.tested_at,
        }
        for p in proxies
    ]
