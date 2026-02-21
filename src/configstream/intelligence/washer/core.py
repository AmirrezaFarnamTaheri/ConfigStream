import shutil

# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import base64
import binascii
import json
import hashlib
import logging
import threading
import httpx
import time
from typing import List, Dict, Optional, Set, Any, Tuple
from cachetools import LRUCache  # type: ignore

from configstream.models import Proxy
from configstream.converters import to_singbox_outbound
from configstream.warp_scanner import WarpScannerWorker
from configstream.intelligence.washer.warp_scraper import WarpScraper
from configstream.intelligence.washer.key_generator import (
    KeyGenerator,
)  # Import the new key generator
from configstream.tools.vwarp import VwarpTool
from pathlib import Path
from configstream.intelligence.chaining import find_optimal_relay, ProxyStub, COUNTRIES
from configstream.pipeline_stats import PipelineStats
from configstream.config import AppSettings
from configstream.constants import VWARP_SOCKS5_PORT, VWARP_BIND_ADDRESS
from configstream.tagging import (
    get_flag_emoji,
    build_proxy_stack,
    format_proxy_name,
    ProxyTagger,
)

logger = logging.getLogger(__name__)

# Cache settings to avoid repeated pydantic_settings instantiation in per-proxy hot paths
_SETTINGS_CACHE = AppSettings()

# Static fallback if fetch fails
DEFAULT_CLEAN_IPS = [
    "162.159.192.1",
    "162.159.193.10",
    "162.159.195.5",
    "66.235.200.115",
    "141.101.75.118",
    "198.41.212.19",
    "172.69.54.168",
    "195.85.59.165",
    "162.158.201.59",
    "162.159.64.117",
    "154.84.16.96",
    "45.85.118.225",
    "23.227.60.163",
    "162.158.203.4",
    "154.84.20.118",
    "162.158.117.94",
    "172.68.83.4",
    "172.70.144.226",
    "185.162.231.101",
    "172.67.196.109",
    "23.178.112.44",
    "162.158.244.60",
    "172.68.248.45",
    "185.176.24.192",
    "93.114.65.234",
    "172.67.221.149",
    "188.114.103.40",
    "45.8.105.201",
    "203.34.80.55",
    "172.69.239.111",
    "172.68.35.144",
    "162.158.212.204",
    "172.69.246.35",
    "104.21.53.148",
    "103.160.204.4",
    "168.100.6.209",
    "162.44.107.103",
    "103.22.201.152",
    "108.162.255.82",
    "104.30.213.188",
    "203.23.103.87",
    "162.158.95.231",
    "45.84.59.232",
    "45.84.59.111",
    "154.84.24.98",
    "91.192.107.138",
    "154.84.24.209",
    "154.84.24.5",
    "91.192.107.125",
    "191.101.251.141",
    "104.16.143.190",
    "172.65.232.209",
    "197.234.242.143",
    "172.65.38.220",
    "188.114.98.161",
    "188.114.107.163",
    "190.93.253.49",
    "104.26.53.66",
    "104.26.143.51",
    "104.27.175.49",
    "173.245.49.172",
    "104.24.71.65",
    "104.27.204.7",
    "172.65.89.46",
    "104.19.48.148",
    "162.158.0.154",
    "104.24.235.255",
    "190.93.252.105",
    "104.27.34.213",
    "190.93.248.216",
    "104.27.47.4",
    "172.64.34.78",
    "188.114.97.255",
    "104.20.166.35",
    "190.93.240.19",
    "188.114.108.115",
    "173.245.49.56",
    "188.114.111.47",
    "104.26.61.100",
    "173.245.49.14",
    "104.20.21.137",
    "190.93.242.41",
    "104.22.6.139",
    "104.25.229.241",
    "190.93.255.150",
    "188.114.100.152",
    "190.93.240.129",
    "172.64.83.58",
    "104.25.26.134",
    "172.65.11.244",
    "188.114.98.38",
    "104.18.76.253",
    "104.19.192.254",
    "104.21.95.43",
    "104.18.254.194",
    "104.27.37.213",
    "104.25.155.29",
    "104.19.216.104",
    "104.24.166.15",
    "190.93.255.243",
    "91.192.107.89",
    "185.18.250.64",
    "195.245.221.110",
    "154.83.2.180",
    "203.22.223.7",
    "185.38.135.65",
    "194.36.49.63",
    "162.159.231.57",
    "194.152.44.187",
    "172.83.72.136",
    "205.233.181.142",
    "66.235.200.224",
    "103.172.111.110",
    "89.116.250.117",
    "108.165.216.124",
    "203.34.28.52",
    "185.238.228.36",
    "89.116.250.236",
]
# Default Cloudflare WARP Server Public Key (Standard)
# Note: This key can rotate. Audit suggested ensuring it's valid.
# Ideally, this should be fetched from an API or env var.
# For now, we allow overriding via AppSettings if defined, else use this standard one.
DEFAULT_WARP_SERVER_KEY = "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="

# Fallback Clean IPs from user reports
FALLBACK_CLEAN_IPS = [
    "188.114.97.204:7103",
    "188.114.99.73:2506",
    "162.159.192.166:5956",
    "188.114.99.120:1074",
    "162.159.192.253:7103",
    "188.114.99.153:5956",
    "188.114.99.73:955",
    "188.114.96.101:2506",
    "188.114.97.204:1002",
    "188.114.98.201:7103",
    "162.159.192.253:890",
    "162.159.192.83:890",
    "188.114.98.224:3476",
    "188.114.98.224:500",
    "188.114.98.224:2371",
    "188.114.98.224:1070",
    "188.114.98.224:854",
    "188.114.98.224:864",
    "188.114.98.224:939",
    "188.114.98.224:2408",
    "188.114.98.224:908",
    "188.114.96.145:1074",
    "162.159.192.4:3854",
    "162.159.192.13:859",
    "162.159.192.5:3581",
    "162.159.195.2:8742",
    "162.159.192.10:934",
    "162.159.192.14:943",
    "162.159.192.17:1387",
    "162.159.192.3:7103",
    "162.159.192.5:854",
    "162.159.192.17:8742",
    "162.159.192.13:7156",
    "162.159.192.9:4198",
    "162.159.192.5:2408",
    "162.159.192.10:2371",
    "162.159.192.9:1010",
    "162.159.192.6:943",
    "162.159.195.4:8742",
    "162.159.192.14:8742",
    "162.159.192.20:1387",
    "162.159.192.15:3138",
    "162.159.195.2:864",
    "162.159.192.11:4233",
    "162.159.195.6:854",
    "162.159.195.9:1014",
    "162.159.198.2:443",
    "162.159.198.1:443",
    "162.159.198.0:443",
    "162.159.192.1:4500",
    "162.159.192.1:2408",
    "162.159.192.1:1701",
    "162.159.192.1:500",
    "195.137.167.251",
    "195.137.167.253",
    "147.185.161.90",
    "198.217.251.133",
    "207.189.149.248",
    "103.169.142.142",
    "65.110.63.188",
    "91.199.81.216",
    "91.199.81.114",
    "195.85.59.186",
    "104.254.140.132",
    "203.22.223.11",
    "203.34.28.238",
    "203.24.103.171",
    "108.165.216.127",
    "154.85.99.62",
    "216.120.181.34",
    "194.36.49.47",
    "190.93.247.123",
    "170.114.46.33",
    "203.32.121.220",
    "203.24.109.200",
    "45.85.119.199",
    "185.170.166.208",
    "198.41.208.121",
    "185.176.24.55",
    "203.34.28.104",
    "207.189.149.18",
    "190.93.244.91",
    "172.67.159.197",
    "23.227.37.244",
    "93.114.64.195",
    "104.25.208.126",
    "194.36.49.14",
    "193.9.49.76",
    "172.67.191.93",
    "196.13.241.68",
    "203.17.126.171",
    "45.8.211.82",
    "203.29.52.77",
    "45.85.119.67",
    "192.65.217.206",
    "192.65.217.92",
    "172.66.44.30",
    "65.110.63.183",
    "188.244.122.174",
    "141.101.90.26",
    "5.226.181.52",
    "170.114.45.198",
    "203.23.103.87",
    "170.114.45.184",
    "104.24.71.209",
    "104.254.140.229",
    "104.21.192.184",
    "103.160.204.43",
    "190.93.245.225",
    "147.78.140.112",
    "103.172.111.182",
    "45.8.211.228",
    "23.227.39.218",
    "203.28.8.194",
    "185.176.26.233",
    "205.233.181.111",
    "203.55.107.102",
    "89.47.57.23",
    "185.207.92.120",
    "91.193.59.7",
    "203.24.103.156",
    "147.185.161.7",
    "207.189.149.119",
    "188.244.122.171",
    "185.109.21.98",
    "89.47.56.41",
    "173.245.59.114",
    "103.172.111.126",
    "66.81.255.90",
    "205.233.181.56",
    "203.22.223.73",
    "195.245.221.231",
    "147.185.161.24",
    "195.245.221.30",
    "185.174.138.24",
    "104.254.140.10",
    "45.85.118.91",
    "45.12.31.181",
    "185.174.138.68",
    "203.17.126.16",
    "172.66.2.251",
    "199.181.197.152",
    "172.67.239.105",
    "191.101.251.32",
    "203.34.80.243",
    "198.41.215.53",
    "195.85.23.56",
    "91.192.107.82",
    "154.84.24.44",
    "91.192.107.180",
    "198.41.219.149",
    "204.68.111.39",
    "203.34.80.202",
    "185.67.124.175",
    "91.192.107.89",
    "45.133.247.118",
    "160.153.0.71",
    "185.18.250.64",
    "195.245.221.110",
    "195.245.221.100",
    "154.83.2.180",
    "203.22.223.7",
    "45.145.28.31",
    "198.217.251.107",
    "185.38.135.65",
    "212.239.86.240",
    "194.36.49.63",
    "196.13.241.117",
    "23.227.60.227",
    "172.65.67.110",
    "173.245.59.41",
    "162.159.231.57",
    "5.226.181.225",
    "194.152.44.187",
    "172.83.72.136",
    "203.30.189.120",
    "205.233.181.142",
    "45.142.120.17",
    "66.235.200.224",
    "89.116.250.149",
    "103.172.111.110",
    "89.116.250.117",
    "154.85.99.214",
    "185.213.240.220",
    "108.165.216.124",
    "156.239.154.66",
    "194.36.49.199",
    "212.239.86.167",
    "203.34.28.52",
    "154.85.99.53",
    "185.238.228.36",
    "45.133.247.52",
    "89.116.250.236",
    "185.221.160.30",
    "185.221.160.211",
    "45.84.59.188",
    "185.213.240.193",
    "185.174.138.85",
    "154.85.99.14",
    "156.239.154.165",
    "212.239.86.174",
    "156.239.154.92",
    "193.188.14.105",
    "212.239.86.171",
    "156.239.154.187",
    "185.244.106.27",
    "212.239.86.247",
    "185.244.106.68",
    "156.239.154.251",
    "156.239.154.229",
    "156.239.154.127",
    "212.239.86.178",
    "191.101.251.166",
    "191.101.251.98",
    "45.133.247.17",
    "185.109.21.36",
    "156.239.154.133",
    "185.244.106.30",
    "154.85.99.114",
    "104.234.158.3",
    "156.239.154.44",
    "191.101.251.35",
    "154.85.99.188",
    "154.85.99.81",
    "185.244.106.174",
    "91.192.107.114",
    "195.137.167.3",
    "185.67.124.152",
    "204.209.72.136",
    "185.213.243.30",
    "204.209.72.153",
    "204.209.72.133",
    "185.213.243.27",
    "204.209.73.39",
    "185.213.243.23",
    "191.101.251.45",
    "191.101.251.7",
    "191.101.251.33",
    "191.101.251.21",
    "191.101.251.52",
    "159.246.55.190",
    "154.84.24.109",
    "154.84.24.208",
    "154.84.24.25",
    "154.84.24.209",
    "154.84.24.149",
    "154.84.24.98",
    "154.84.24.5",
    "154.84.24.206",
    "154.84.24.45",
    "154.84.24.205",
    "191.101.251.28",
    "191.101.251.253",
    "185.213.240.129",
    "156.239.154.103",
    "156.239.154.52",
    "156.239.154.246",
    "156.239.154.24",
    "156.239.154.51",
    "156.239.154.144",
    "156.239.154.69",
    "156.239.154.120",
    "156.239.154.147",
    "156.239.154.135",
    "156.239.154.138",
    "156.239.154.95",
    "156.239.154.244",
    "156.239.154.163",
    "156.239.154.85",
    "156.239.154.64",
    "156.239.154.177",
    "156.239.154.129",
    "156.239.154.219",
    "156.239.154.38",
    "156.239.154.212",
    "156.239.154.21",
    "156.239.154.59",
    "156.239.154.195",
    "156.239.154.216",
    "156.239.154.73",
    "156.239.154.17",
    "156.239.154.97",
    "156.239.154.75",
    "156.239.154.14",
    "156.239.154.42",
    "156.239.154.32",
    "156.239.154.61",
    "156.239.154.41",
    "156.239.154.115",
    "156.239.154.89",
    "156.239.154.213",
    "156.239.154.170",
    "156.239.154.209",
    "156.239.154.81",
    "156.239.154.250",
    "156.239.154.232",
    "156.239.154.222",
    "156.239.154.169",
    "156.239.154.143",
    "156.239.154.223",
    "156.239.154.157",
    "156.239.154.239",
    "156.239.154.132",
    "156.239.154.145",
    "156.239.154.65",
    "156.239.154.253",
    "156.239.154.131",
    "156.239.154.106",
    "156.239.154.2",
    "156.239.154.37",
    "156.239.154.189",
    "156.239.154.218",
    "156.239.154.137",
    "156.239.154.207",
    "156.239.154.36",
    "156.239.154.224",
    "172.65.191.188",
    "172.65.163.56",
    "172.65.185.215",
    "162.159.250.181",
    "162.159.194.65",
    "162.159.203.113",
    "162.159.203.134",
    "162.159.226.101",
    "162.159.203.99",
    "162.159.203.181",
    "162.159.203.183",
    "162.159.203.71",
    "162.159.226.102",
    "162.159.226.35",
    "162.159.226.17",
    "162.159.203.136",
    "162.159.226.0",
    "162.159.226.37",
    "162.159.203.196",
    "162.159.203.234",
    "162.159.226.13",
    "162.159.203.214",
    "162.159.203.252",
    "162.159.203.185",
    "162.159.203.86",
    "162.159.226.34",
    "162.159.203.51",
    "162.159.226.4",
    "162.159.203.76",
    "162.159.203.209",
    "162.159.203.237",
    "162.159.203.56",
    "162.159.203.63",
    "162.159.226.30",
    "162.159.203.251",
    "162.159.203.141",
    "162.159.203.198",
    "162.159.203.34",
    "162.159.203.103",
    "162.159.203.116",
    "162.159.226.6",
    "162.159.226.24",
    "162.159.203.149",
    "162.159.203.229",
    "162.159.203.192",
    "162.159.22.126",
    "162.159.15.52",
    "162.159.13.115",
    "162.159.56.216",
    "162.159.49.207",
    "162.159.7.55",
    "172.67.134.247",
    "172.67.114.19",
    "172.67.206.135",
    "172.67.202.152",
    "104.30.129.178",
    "104.30.129.102",
    "104.30.128.152",
    "104.30.129.106",
    "104.30.129.101",
    "104.30.129.181",
    "104.30.128.26",
    "104.30.128.238",
    "104.30.129.154",
    "104.30.129.110",
    "104.30.129.157",
    "104.30.128.165",
    "104.30.128.243",
    "104.30.128.211",
    "104.30.128.44",
    "104.30.128.150",
    "104.30.128.147",
    "104.30.128.84",
    "104.30.129.94",
    "104.30.129.109",
    "104.30.129.244",
    "104.30.129.100",
    "104.30.129.235",
    "104.30.128.11",
    "104.30.128.254",
    "104.30.128.228",
    "104.30.128.155",
    "104.30.128.215",
    "104.30.128.27",
    "104.30.129.108",
    "104.30.129.124",
    "104.30.129.95",
    "104.30.129.85",
    "104.30.129.0",
    "104.30.129.89",
    "104.30.129.130",
    "104.30.129.105",
    "141.101.113.168",
    "104.30.129.185",
    "104.30.128.130",
    "104.30.128.49",
    "104.30.129.179",
    "104.30.128.178",
    "104.30.129.26",
    "104.30.129.27",
    "104.30.128.135",
    "104.30.128.236",
    "104.30.129.140",
    "104.30.128.240",
    "104.30.128.56",
    "104.30.128.17",
    "104.30.129.99",
    "104.30.128.7",
    "104.30.129.55",
    "104.30.129.138",
    "104.30.128.248",
    "104.30.128.36",
    "104.30.128.235",
    "104.30.128.143",
    "104.30.129.59",
    "104.30.129.13",
    "104.30.128.160",
    "104.30.128.8",
    "104.30.129.134",
    "104.30.129.83",
    "104.30.129.103",
    "104.30.128.142",
    "104.30.129.60",
    "104.30.129.136",
    "104.30.129.56",
    "104.30.129.236",
    "103.21.244.117",
    "91.234.214.100",
    "103.81.228.1",
    "91.234.214.1",
    "91.234.214.101",
    "91.234.214.209",
    "103.81.228.2",
    "103.81.228.3",
    "104.19.101.241",
    "104.21.85.163",
    "104.18.83.86",
    "104.21.229.153",
    "104.20.25.142",
    "104.25.112.217",
    "104.25.15.125",
    "104.25.60.205",
    "104.24.242.182",
    "104.24.206.46",
]

# Multiple fallback sources for Clean IP endpoints
CLEAN_IP_SOURCES = [
    # "https://raw.githubusercontent.com/ircfspace/warpendpoint/main/result/warp-ip.txt", # Dead
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/warp.txt",
    "https://www.cloudflare.com/ips-v4",
    "https://raw.githubusercontent.com/MortezaBashsiz/CFScanner/main/config/cf.local.iplist",
]

# Optimized reserved bytes for resistant regions
OPTIMIZED_RESERVED = [
    [84, 146, 56],
    [87, 96, 242],
    [100, 206, 89],
    [98, 157, 152],
    [54, 207, 87],
    [226, 124, 93],
    [22, 18, 221],
    [210, 106, 14],
    [155, 40, 24],
    [60, 173, 68],
]


class ProxyWasher:
    def __init__(self, warp_keys_json: str):
        try:
            parsed = json.loads(warp_keys_json) if warp_keys_json else []
            if not isinstance(parsed, list):
                logger.warning(f"warp_keys_json is not a list, got {type(parsed)}")
                self._warp_keys: List[Dict[str, Any]] = []
            else:
                self._warp_keys = self._normalize_warp_keys(parsed)
                if self._warp_keys:
                    logger.info(f"Loaded {len(self._warp_keys)} WARP keys for washing")
                else:
                    # Don't log warning here, we will try to generate/fetch later
                    logger.debug("No initial WARP keys configured")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse warp_keys_json: {e}")
            self._warp_keys = []

        self.seen_chains: LRUCache[str, bool] = LRUCache(maxsize=50000)
        self._seen_chains_lock = threading.Lock()
        self._state_lock = threading.Lock()
        # Critical: Add asyncio lock for async operations to prevent race conditions
        self._async_state_lock = asyncio.Lock()
        self._clean_ips: List[Tuple[str, int]] = []

        # Initialize defaults immediately if not provided
        if not self._warp_keys:
            env_keys = _SETTINGS_CACHE.WARP_KEY_POOL

            if env_keys and env_keys != "[]":
                try:
                    parsed = json.loads(env_keys)
                except json.JSONDecodeError:
                    # Fallback to comma-separated format
                    parsed = [k.strip() for k in env_keys.split(",") if k.strip()]

                if isinstance(parsed, list):
                    self._warp_keys = self._normalize_warp_keys(parsed)

        self.scanner = WarpScannerWorker()
        self.key_gen = KeyGenerator()

    @staticmethod
    def _normalize_wg_key(key: str) -> Optional[str]:
        if not key:
            return None
        cleaned = "".join(str(key).split())
        if not cleaned:
            return None
        cleaned = cleaned.replace("-", "+").replace("_", "/")
        pad = len(cleaned) % 4
        if pad:
            cleaned += "=" * (4 - pad)
        try:
            decoded = base64.b64decode(cleaned, validate=True)
        except (binascii.Error, ValueError):
            try:
                decoded = base64.b64decode(cleaned, validate=False)
            except Exception:  # nosec
                return None
        if len(decoded) != 32:
            return None
        return cleaned

    @classmethod
    def _normalize_warp_keys(cls, entries: List[Any]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        invalid_private = 0
        invalid_peer = 0
        for item in entries:
            if isinstance(item, dict):
                if "private_key" not in item:
                    if "private-key" in item:
                        item["private_key"] = item.pop("private-key")
                    elif "privateKey" in item:
                        item["private_key"] = item.pop("privateKey")
                private_key = cls._normalize_wg_key(item.get("private_key", ""))
                if private_key:
                    item["private_key"] = private_key
                    peer_key = item.get("peer_public_key")
                    if peer_key:
                        peer_norm = cls._normalize_wg_key(peer_key)
                        if peer_norm:
                            item["peer_public_key"] = peer_norm
                        else:
                            invalid_peer += 1
                            item.pop("peer_public_key", None)
                    normalized.append(item)
                else:
                    invalid_private += 1
                continue
            if isinstance(item, str):
                key_str = cls._normalize_wg_key(item)
                if key_str:
                    normalized.append({"private_key": key_str})
                else:
                    invalid_private += 1
        if invalid_private:
            logger.warning(
                "Dropped %d invalid WARP private keys during normalization.",
                invalid_private,
            )
        if invalid_peer and logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Dropped %d invalid WARP peer public keys during normalization.",
                invalid_peer,
            )
        return normalized

    @property
    def warp_keys(self) -> List[Dict[str, Any]]:
        """Thread-safe read of warp_keys."""
        with self._state_lock:
            return self._warp_keys[:]

    @warp_keys.setter
    def warp_keys(self, value: List[Dict[str, Any]]) -> None:
        """Thread-safe write of warp_keys."""
        with self._state_lock:
            self._warp_keys = value

    @property
    def clean_ips(self) -> List[Tuple[str, int]]:
        """Thread-safe read of clean_ips."""
        with self._state_lock:
            return self._clean_ips[:]

    @clean_ips.setter
    def clean_ips(self, value: List[Tuple[str, int]]) -> None:
        """Thread-safe write of clean_ips."""
        with self._state_lock:
            self._clean_ips = value

    async def fetch_clean_ips(self) -> None:
        """
        Fetches the latest clean IPs for WARP endpoints.
        Uses async lock for the ENTIRE method to prevent N consumers
        from triggering N redundant fetches (check-then-act race).
        """
        async with self._async_state_lock:
            # Early exit: already populated by a previous caller
            if self._warp_keys and self._clean_ips:
                return

            current_keys = self._warp_keys[:]
            current_ips = self._clean_ips[:]

            # --- STRATEGY 0.5: WARP KEYS & IPs FROM SCRAPER (Priority 1) ---
            if not current_keys or not current_ips:
                try:
                    scraper = WarpScraper()
                    scraped_keys = await scraper.scrape_warp_sources()

                    fresh_endpoints = scraper.get_scraped_endpoints()
                    new_keys = []

                    for p in scraped_keys:
                        key_dict = {
                            "private_key": p.details.get("private_key"),
                            "peer_public_key": p.details.get("peer_public_key"),
                            "id": p.uuid,
                        }
                        if key_dict["private_key"] and key_dict["peer_public_key"]:
                            new_keys.append(key_dict)

                    if fresh_endpoints:
                        self._clean_ips = []
                        for ep in fresh_endpoints:
                            if isinstance(ep, str):
                                if self._looks_like_ip(ep):
                                    self._clean_ips.append((ep, 2408))
                            elif isinstance(ep, tuple) and len(ep) == 2:
                                if self._looks_like_ip(str(ep[0])):
                                    self._clean_ips.append(ep)
                        if self._clean_ips:
                            logger.info(
                                f"Loaded {len(self._clean_ips)} clean IPs from Scraper"
                            )

                    if new_keys:
                        self._warp_keys = new_keys
                        logger.info(
                            f"Loaded {len(new_keys)} WARP keys from community sources"
                        )
                except Exception as e:
                    logger.warning(f"WARP scraper failed: {e}")

            # --- STRATEGY 0: VWARP SCANNER (Priority 2 if Scraper insufficient) ---
            if not self._clean_ips:
                try:
                    vwarp = VwarpTool()
                    if await vwarp.is_available():
                        scanned_ips_vwarp = await vwarp.scan_endpoints()
                        if scanned_ips_vwarp:
                            self._clean_ips = list(scanned_ips_vwarp)
                            logger.info(
                                f"Loaded {len(scanned_ips_vwarp)} clean IPs from Vwarp"
                            )
                    else:
                        logger.debug("Vwarp binary not found - skipping Vwarp scan.")
                except Exception as e:
                    logger.warning(f"Vwarp scanner failed: {e}")

            # --- STRATEGY 1: ACTIVE SCANNING ---
            if self.scanner.available and not self._clean_ips:
                try:
                    logger.info("Attempting active IP scan...")
                    scanned_ips = await self.scanner.scan_endpoints(
                        limit=50, timeout=5, max_latency=800
                    )

                    if scanned_ips and len(scanned_ips) >= 5:
                        self._clean_ips = [
                            (ip, 2408)
                            for ip in scanned_ips
                            if self._looks_like_ip(str(ip))
                        ]
                        logger.info(
                            f"Active Scan Success: Using {len(self._clean_ips)} fresh IPs."
                        )
                except Exception as e:
                    logger.error(f"Active scan failed: {e}")

            # --- STRATEGY 2: STATIC LISTS ---
            if not self._clean_ips:
                logger.info("Starting static list fetch sequence...")
                for source_url in CLEAN_IP_SOURCES:
                    try:
                        async with httpx.AsyncClient(timeout=10) as client:
                            resp = await client.get(source_url)
                            if resp.status_code == 200:
                                lines = [
                                    line.strip()
                                    for line in resp.text.splitlines()
                                    if line.strip() and not line.startswith("#")
                                ]
                                valid_ips: list[str] = []
                                for raw_ip in lines:
                                    host = raw_ip.split("/")[0]
                                    if host.count(".") != 3 or not host[0].isdigit():
                                        continue
                                    # CIDR base addresses (x.x.x.0) are not usable
                                    # endpoints; offset to a real host IP.
                                    octets = host.split(".")
                                    try:
                                        last = int(octets[3])
                                    except (IndexError, ValueError):
                                        continue
                                    if last == 0:
                                        octets[3] = "1"
                                        host = ".".join(octets)
                                    elif last == 255:
                                        octets[3] = "254"
                                        host = ".".join(octets)
                                    if self._looks_like_ip(host):
                                        valid_ips.append(host)
                                if valid_ips:
                                    self._clean_ips = [
                                        (ip, 2408) for ip in valid_ips[:100]
                                    ]
                                    logger.info(
                                        f"Fetched {len(valid_ips)} clean IPs from {source_url.split('/')[2]}"
                                    )
                                    break  # Stop after one success
                    except Exception:  # nosec
                        pass

            # --- STRATEGY 3: DEFAULTS ---
            if not self._clean_ips:
                logger.warning(
                    f"All scanners failed. Using {len(DEFAULT_CLEAN_IPS)} default IPs."
                )
                self._clean_ips = [(ip, 2408) for ip in DEFAULT_CLEAN_IPS]

            # --- KEY GENERATION FALLBACK (Last Resort) ---
            # If still no keys, try to generate one
            if not self._warp_keys:
                logger.info(
                    "No WARP keys found. Attempting to generate a new account..."
                )
                try:
                    new_account = await self.key_gen.generate_account()
                    if new_account:
                        self._warp_keys = [new_account]
                        logger.info("Successfully generated a new WARP account/key.")
                    else:
                        logger.error(
                            "Failed to generate WARP account. Washing disabled."
                        )
                except Exception as e:
                    logger.error(f"Key generation failed: {e}")

    @staticmethod
    def _looks_like_ip(host: str) -> bool:
        """Quick check that a host string resembles an IP (not a timestamp/garbage)."""
        host = host.strip()
        if not host:
            return False
        # IPv4: starts with digit and has exactly 3 dots
        if host[0].isdigit() and host.count(".") == 3:
            return all(
                part.isdigit() and 0 <= int(part) <= 255 for part in host.split(".")
            )
        # IPv6: hex/colon/dot chars only AND at least 2 colons (real IPv6 has 2-7)
        if host.count(":") >= 2 and all(c in "0123456789abcdefABCDEF:." for c in host):
            return True
        return False

    def _get_clean_endpoint(self, relay_id: str) -> Tuple[str, int]:
        pool = self.clean_ips
        if not pool:
            # Parse fallback IPs
            pool = []
            for item in FALLBACK_CLEAN_IPS:
                host = str(item).strip()
                if not host:
                    continue

                ip = host
                port = 2408

                if host.startswith("[") and "]" in host:
                    # Bracketed IPv6: [addr]:port — strip brackets
                    end = host.find("]")
                    ip = host[1:end]
                    rest = host[end + 1 :].lstrip()
                    if rest.startswith(":"):
                        try:
                            port = int(rest[1:])
                        except ValueError:
                            continue
                elif ":" in host:
                    ip_part, port_part = host.rsplit(":", 1)
                    try:
                        port = int(port_part)
                    except ValueError:
                        continue
                    ip = ip_part

                if not (1 <= port <= 65535):
                    continue

                pool.append((ip, port))
            # Append defaults
            pool.extend([(ip, 2408) for ip in DEFAULT_CLEAN_IPS])

        # Filter out any non-IP entries that slipped through scan parsing
        valid_pool = []
        for ep in pool:
            if isinstance(ep, tuple) and len(ep) == 2:
                if self._looks_like_ip(str(ep[0])):
                    valid_pool.append(ep)
            elif isinstance(ep, str) and self._looks_like_ip(ep):
                valid_pool.append((ep, 2408))

        if not valid_pool:
            return ("162.159.192.1", 2408)

        hash_val = int(hashlib.sha256(relay_id.encode()).hexdigest(), 16)
        return valid_pool[hash_val % len(valid_pool)]

    def _get_consistent_exit(
        self, relay_id: str, exit_pool: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if not exit_pool:
            return None

        current_epoch = int(time.time() / (7 * 86400))
        hash_input = f"{relay_id}-{current_epoch}".encode()
        hash_val = int(hashlib.sha256(hash_input).hexdigest(), 16)

        pool_len = len(exit_pool)
        start_index = hash_val % pool_len

        for i in range(pool_len):
            idx = (start_index + i) % pool_len
            key = exit_pool[idx]
            # Allow key if it has private key, inject peer key if missing
            if key.get("private_key"):
                return key

        return None

    def _get_optimized_reserved(self, seed: str) -> List[int]:
        """
        Selects a reserved bytes array from OPTIMIZED_RESERVED deterministically based on seed.
        """
        if not OPTIMIZED_RESERVED:
            return [0, 0, 0]  # Default fallback

        h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
        return OPTIMIZED_RESERVED[h % len(OPTIMIZED_RESERVED)]

    def _generate_deterministic_ip(self, seed: str) -> str:
        h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
        # Use 10.x.x.x range for 16M+ unique IPs
        # Bit shift to utilize more of the hash entropy
        octet_2 = (h >> 16) % 255
        octet_3 = (h >> 8) % 255
        octet_4 = (h % 254) + 1  # 1-254
        return f"10.{octet_2}.{octet_3}.{octet_4}/32"

    def get_warp_config(self, seed: str) -> Optional[Dict[str, Any]]:
        """
        Generate a WARP WireGuard config for a given seed (used by chaining.py).
        Returns None if no WARP keys are available.
        """
        exit_key = self._get_consistent_exit(seed, self.warp_keys)
        if not exit_key:
            return None

        endpoint_data = self._get_clean_endpoint(seed)
        if isinstance(endpoint_data, tuple):
            clean_endpoint, clean_port = endpoint_data
        else:
            clean_endpoint = str(endpoint_data)
            clean_port = 2408

        unique_ip = self._generate_deterministic_ip(seed)

        reserved = self._get_optimized_reserved(seed)

        # Ensure valid peer public key
        # Check environment or use default
        peer_key = exit_key.get("peer_public_key")
        if not peer_key:
            peer_key = _SETTINGS_CACHE.WARP_PEER_KEY or DEFAULT_WARP_SERVER_KEY

        return {
            "type": "wireguard",
            "local_address": [unique_ip],
            "private_key": exit_key["private_key"],
            "server": clean_endpoint,
            "server_port": clean_port,
            "peer_public_key": peer_key,
            "reserved": reserved,
            "mtu": 1280,
        }

    def is_vwarp_available(self) -> bool:
        """Check if Vwarp tunnel is likely operational."""
        # Check if binary exists (fast)
        if not shutil.which("vwarp"):
            # Check common paths from VwarpTool logic if needed, but shutil.which covers PATH
            # Fallback to local check
            if not Path("vwarp").exists() and not Path("/usr/local/bin/vwarp").exists():
                return False

        # If binary exists, we assume it MIGHT work, but really we should check the port.
        # But checking port 8086 requires async or socket.
        # Given consumer.py calls this in async context, but wash_failed is not async?
        # Wait, wash_failed is synchronous in core.py?
        # "def wash_failed(self, ...):" -> Yes, it is sync.
        # So we cannot use "await vwarp.is_available()".
        # We can use a simple socket check.

        import socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                # Check Vwarp SOCKS port (8086 default)
                if s.connect_ex((VWARP_BIND_ADDRESS, VWARP_SOCKS5_PORT)) == 0:
                    return True
        except Exception:
            pass

        # If port check fails, maybe it"s just not started yet, or dead.
        # But if it"s not started, using it will fail anyway.
        # So returning False is safe to prevent wasting resources.
        return False

    def wash_failed(
        self,
        failed_proxies: List[Proxy],
        stats: Optional[PipelineStats] = None,
        use_vwarp: bool = False,
    ) -> Tuple[List[Proxy], int]:
        """
        Attempts to REVIVE failed proxies by wrapping them in WARP.
        Returns a list of NEW Proxy objects (the chains) ready for re-testing.
        """
        revived_candidates: List[Proxy] = []
        revived_count = 0

        if not self.warp_keys:
            return [], 0

        # Prevent infinite recursion: Filter out proxies that are already revived
        candidates = [
            p
            for p in failed_proxies
            if p.protocol != "revived" and not p.details.get("is_revived")
        ]

        for relay in candidates:
            # Basic plausibility check before reviving
            if not relay.address or not relay.port:
                continue

            exit_key = self._get_consistent_exit(relay.id, self.warp_keys)
            if not exit_key:
                continue

            # Use different tag prefixes for WARP vs Vwarp revivals
            if use_vwarp:
                chain_id = f"VWARP-REVIVE-{relay.id[:8]}"
                relay_tag_prefix = "VWARP-RELAY"
            else:
                chain_id = f"WARP-REVIVE-{relay.id[:8]}"
                relay_tag_prefix = "WARP-RELAY"

            endpoint_data = self._get_clean_endpoint(relay.id)
            if isinstance(endpoint_data, tuple):
                clean_endpoint, clean_port = endpoint_data
            else:
                clean_endpoint = str(endpoint_data)
                clean_port = 2408

            unique_ip = self._generate_deterministic_ip(chain_id)

            relay_out = to_singbox_outbound(relay)
            if not relay_out:
                continue

            relay_out["tag"] = f"{relay_tag_prefix}-{relay.id[:8]}"
            relay_out["_origin_country_code"] = relay.country_code or ""
            relay_out["_origin_latency"] = relay.latency

            reserved_bytes = self._get_optimized_reserved(chain_id)

            # Ensure valid peer public key
            peer_key = exit_key.get("peer_public_key")
            if not peer_key:
                peer_key = _SETTINGS_CACHE.WARP_PEER_KEY or DEFAULT_WARP_SERVER_KEY

            if use_vwarp:
                # Vwarp Revival: Client -> Vwarp (SOCKS5) -> Relay
                # Use local Vwarp tunnel to unblock access to the Relay
                warp_out = {
                    "type": "socks",
                    "tag": chain_id,
                    "server": VWARP_BIND_ADDRESS,
                    "server_port": VWARP_SOCKS5_PORT,
                    "version": "5",
                }
                # Detour Relay through Vwarp
                relay_out["detour"] = chain_id
            else:
                # Standard Revival: Client -> Relay -> Warp
                # Use Relay to tunnel Warp (Warp over Proxy)
                warp_out = {
                    "type": "wireguard",
                    "tag": chain_id,
                    "local_address": [unique_ip],
                    "private_key": exit_key["private_key"],
                    "server": clean_endpoint,
                    "server_port": clean_port,
                    "peer_public_key": peer_key,
                    "reserved": reserved_bytes,
                    "mtu": 1280,
                    "detour": relay_out["tag"],
                }

            # We bundle BOTH outbounds into the proxy details for special handling
            # Serialize relay object to prevent JSON errors.
            # Use the canonical Pydantic method for serialization.
            origin_dict = relay.model_dump(mode="json")

            vwarp_mode = "STANDARD"
            if use_vwarp:
                settings = AppSettings()
                if settings.VWARP_MASQUE_ENABLED:
                    vwarp_mode = "MASQUE"

            # Sing-box requires detour targets before referrers. Vwarp: relay detours to warp
            # → warp first. Standard WARP: warp detours to relay → relay first.
            chain_order = [warp_out, relay_out] if use_vwarp else [relay_out, warp_out]
            process_tag = "revived-vwarp" if use_vwarp else "revived-warp"
            revived_proxy = Proxy(
                config=f"revived://{relay.address}",  # Dummy config
                protocol="revived",  # Special protocol
                address=clean_endpoint,
                port=clean_port,
                uuid=chain_id,
                remarks="",  # Set below via format_proxy_name
                process=process_tag,
                details={
                    "chain_outbounds": chain_order,  # The full chain (inner hop first)
                    "is_revived": True,
                    "use_vwarp": use_vwarp,
                    "vwarp_mode": vwarp_mode if use_vwarp else None,
                    "origin_proxy": origin_dict,
                    "origin_id": relay.id,
                },
            )
            # Unified scheme: geo | tech/protocol stack | latency | process | etc
            _tpl = _SETTINGS_CACHE.RENAME_TEMPLATE or ProxyTagger.DEFAULT_TEMPLATE
            revived_proxy.remarks = format_proxy_name(_tpl, revived_proxy)

            revived_candidates.append(revived_proxy)
            revived_count += 1

            if stats:
                lock = getattr(stats, "_lock", None)
                if lock:
                    with lock:
                        if use_vwarp:
                            stats.vwarp_attempts += 1
                        else:
                            stats.warp_attempts += 1
                else:
                    if use_vwarp:
                        stats.vwarp_attempts += 1
                    else:
                        stats.warp_attempts += 1

        return revived_candidates, revived_count

    def wash_batch(
        self, proxies: List[Proxy], stats: Optional[PipelineStats] = None
    ) -> Tuple[List[Dict[str, Any]], Set[str], Dict[str, int]]:
        """
        Standard Washing: Process WORKING proxies to create WARP chains.
        """
        washed_outbounds: List[Dict[str, Any]] = []
        washed_ids: Set[str] = set()
        skip_reasons: Dict[str, int] = {}

        keys = self.warp_keys
        if not keys:
            return washed_outbounds, washed_ids, skip_reasons

        candidates = [p for p in proxies if p.is_working]

        target_exit = ProxyStub("US", 37.09, -95.71, "wireguard")
        origin_country = _SETTINGS_CACHE.OPTIMAL_RELAY_ORIGIN

        for i, relay in enumerate(candidates):
            exit_key = self._get_consistent_exit(relay.id, keys)
            if not exit_key:
                skip_reasons["invalid_warp_key"] = (
                    skip_reasons.get("invalid_warp_key", 0) + 1
                )
                continue

            chain_id = f"CHAIN-{relay.country_code}-{relay.id[:6]}-{exit_key.get('id', '00')[:4]}"

            with self._seen_chains_lock:
                if chain_id in self.seen_chains:
                    skip_reasons["duplicate_chain"] = (
                        skip_reasons.get("duplicate_chain", 0) + 1
                    )
                    continue
                self.seen_chains[chain_id] = True

            relay_out = to_singbox_outbound(relay)
            if not relay_out:
                continue

            relay_tag = f"RELAY-{chain_id}"
            relay_out["tag"] = relay_tag
            relay_out["_origin_country_code"] = relay.country_code or ""
            relay_out["_origin_latency"] = relay.latency

            endpoint_data = self._get_clean_endpoint(relay.id)
            if isinstance(endpoint_data, tuple):
                clean_endpoint, clean_port = endpoint_data
            else:
                clean_endpoint = str(endpoint_data)
                clean_port = 2408

            unique_ip = self._generate_deterministic_ip(chain_id)

            is_optimal = False
            try:
                if relay.country_code and relay.country_code in COUNTRIES:
                    # Pass measured latency for better optimization
                    relay_stub = ProxyStub(
                        relay.country_code,
                        0.0,
                        0.0,
                        relay.protocol,
                        latency=relay.latency or 0.0,
                    )
                    relay_stub.lat, relay_stub.lon = COUNTRIES[relay.country_code]
                    res = find_optimal_relay(origin_country, target_exit, [relay_stub])
                    if isinstance(res, dict) and "relay" in res:
                        if float(res.get("total_distance", 99999)) < 15000:
                            is_optimal = True
            except Exception:  # nosec
                pass

            flag = get_flag_emoji(relay.country_code or "XX")
            lat_str = f"{int(relay.latency)}ms" if relay.latency else "N/A"
            stack = build_proxy_stack(relay)
            tier = "🛡️ OPTIMAL" if is_optimal else "🛡️ SECURE"

            # Unified scheme: geo | tech/protocol stack | latency | etc (like naive proxies)
            exit_tag = f"{flag} | {stack} | {tier} | WARP | {lat_str}"

            reserved_bytes = self._get_optimized_reserved(chain_id)

            # Ensure valid peer public key
            peer_key = exit_key.get("peer_public_key")
            if not peer_key:
                peer_key = _SETTINGS_CACHE.WARP_PEER_KEY or DEFAULT_WARP_SERVER_KEY

            warp_out = {
                "type": "wireguard",
                "tag": exit_tag,
                "local_address": [unique_ip],
                "private_key": exit_key["private_key"],
                "server": clean_endpoint,
                "server_port": clean_port,
                "peer_public_key": peer_key,
                "reserved": reserved_bytes,
                "mtu": 1280,
                "detour": relay_tag,
            }

            washed_outbounds.append(relay_out)
            # Add metadata for process tracking
            warp_out["_process"] = "washed"
            washed_outbounds.append(warp_out)
            washed_ids.add(relay.id)
            if stats:
                lock = getattr(stats, "_lock", None)
                if lock:
                    with lock:
                        stats.warp_attempts += 1
                else:
                    stats.warp_attempts += 1

        if stats:
            lock = getattr(stats, "_lock", None)
            if lock:
                with lock:
                    stats.washer_success_count = len(washed_ids)
            else:
                stats.washer_success_count = len(washed_ids)

        return washed_outbounds, washed_ids, skip_reasons

    def shield_batch(
        self,
        proxies: List[Proxy],
        stats: Optional[PipelineStats] = None,
    ) -> Tuple[List[Dict[str, Any]], Set[str]]:
        """
        [ALCHEMY MODE] Shields dead proxies behind a WARP tunnel.
        Topology: Client -> WARP (Clean Endpoint) -> Proxy -> Internet

        This converts 'Dead Copper' (Blocked Proxy) into 'Gold' (Tunnelled Proxy).
        Use this to UNBLOCK dead proxies by inverting the topology.
        """
        shielded_outbounds: List[Dict[str, Any]] = []
        shielded_ids: Set[str] = set()

        if not self.warp_keys:
            return [], set()

        # Iterate through proxies (typically those that failed direct connection)
        for i, relay in enumerate(proxies):
            # 1. Generate the Shield (WARP Config)
            # This uses your existing logic to get clean IPs and keys
            warp_out = self.get_warp_config(relay.id)
            if not warp_out:
                continue

            # Tag the shield uniquely
            shield_tag = f"SHIELD-{relay.country_code or 'XX'}-{i}"
            warp_out["tag"] = shield_tag
            warp_out["_process"] = "shield_base"

            # CRITICAL: The Shield connects DIRECTLY to the internet (or via local gateway)
            # It does NOT use a detour. It IS the transport.
            warp_out.pop("detour", None)  # Remove any existing detour

            # 2. Convert the 'Dirty' Proxy
            relay_out = to_singbox_outbound(relay)
            if not relay_out:
                continue

            relay_out["_origin_country_code"] = relay.country_code or ""
            relay_out["_origin_latency"] = relay.latency

            # 3. THE ALCHEMY: Wrap the Proxy INSIDE the Shield
            # Sing-box logic: "detour" means "send this outbound's traffic through..."
            relay_out["detour"] = shield_tag

            # 4. Branding & Optimization
            # Unified scheme: geo | tech/protocol stack | latency | process | etc
            # CRITICAL: Append relay.id[:8] so each chain has a UNIQUE tag. Without this,
            # format_proxy_name can produce identical tags for similar proxies, causing
            # _append_chain to skip chains and collapse thousands into one "single proxy".
            shield_proxy = Proxy(
                config=relay.config or "",
                protocol=relay.protocol or "unknown",
                address=relay.address,
                port=relay.port,
                uuid=relay.uuid or "",
                remarks=relay.remarks or "",
                country_code=relay.country_code or "",
                city=relay.city or "",
                latency=relay.latency,
                is_working=relay.is_working,
                process="shielded",
                details=(relay.details or {}) | {"is_shielded": True},
            )
            _tpl = _SETTINGS_CACHE.RENAME_TEMPLATE or ProxyTagger.DEFAULT_TEMPLATE
            base_tag = format_proxy_name(_tpl, shield_proxy)
            relay_out["tag"] = f"{base_tag} | {relay.id[:8]}"
            relay_out["_process"] = "shield_payload"
            # Keep shield metadata on outbound only.
            # Do not mutate the source proxy object (process/details), otherwise
            # native/revived labels are lost in final outputs and merge stage.
            relay_out["_is_shielded"] = True

            # 5. Append to output
            # Order: Shield first, then Proxy (though Sing-box resolves by tag)
            shielded_outbounds.append(warp_out)
            shielded_outbounds.append(relay_out)
            shielded_ids.add(relay.id)

            # 6. Update Stats
            if stats:
                lock = getattr(stats, "_lock", None)
                if lock:
                    with lock:
                        stats.warp_attempts += 1
                else:
                    stats.warp_attempts += 1

        return shielded_outbounds, shielded_ids
