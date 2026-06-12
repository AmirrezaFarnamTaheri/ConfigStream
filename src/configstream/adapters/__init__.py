# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Callable, Dict

from .common import Adapter
from .surge import SurgeAdapter
from .loon import LoonAdapter
from .quantumult import QuantumultXAdapter
from .shadowrocket import ShadowrocketAdapter
from .sip008 import SIP008Adapter

_ADAPTER_MAP: Dict[str, Callable[[], Adapter]] = {
    "surge": SurgeAdapter,
    "loon": LoonAdapter,
    "qx": QuantumultXAdapter,
    "quantumultx": QuantumultXAdapter,
    "sip008": SIP008Adapter,
    "shadowrocket": ShadowrocketAdapter,
}


def get_adapter(format_name: str) -> Adapter:
    cls = _ADAPTER_MAP.get(format_name.lower())
    if cls is None:
        raise ValueError(f"Unknown format: {format_name}")
    return cls()
