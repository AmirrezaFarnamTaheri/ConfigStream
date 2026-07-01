# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Dict, Any

# Constants for Vwarp binary management
# Latest: v2.2.2 (2025-12-16) - https://github.com/voidr3aper-anon/Vwarp/releases
# v2.2.1+ supports full JSON config (JunkInterval, masque.enabled, masque.preferred)
VWARP_VERSION = "v2.2.2"
VWARP_SHA256_AMD64 = "90619d5e8ceec07fe09b967904f490d5a45f812951f7fae4cb375b60207b6312"
VWARP_ASSET_AMD64 = "vwarp_linux-amd64.zip"
VWARP_ASSET_ARM64 = "vwarp_linux-arm64.zip"
VWARP_RELEASE_BASE = "https://github.com/voidr3aper-anon/Vwarp/releases/download"

# Default Cloudflare WARP endpoint
DEFAULT_WARP_ENDPOINT = "162.159.192.1:2408"

# Psiphon country codes supported by vwarp (--cfon --country <CODE>)
# Source: official vwarp CONFIG_FORGE.md
PSIPHON_COUNTRY_CODES = frozenset(
    {
        # Americas
        "US",
        "CA",
        "BR",
        # Europe
        "GB",
        "DE",
        "FR",
        "IT",
        "ES",
        "NL",
        "SE",
        "NO",
        "DK",
        "FI",
        "CH",
        "AT",
        "BE",
        "IE",
        "PT",
        "PL",
        "CZ",
        "HU",
        "RO",
        "BG",
        "HR",
        "EE",
        "LV",
        "SK",
        "RS",
        # Asia-Pacific
        "JP",
        "SG",
        "AU",
        "IN",
    }
)

# MASQUE noize presets aligned with official vwarp presets
# Keys map to --masque-noize-preset values and config file Jc levels
MASQUE_NOIZE_PRESETS: Dict[str, Dict[str, Any]] = {
    "light": {
        "Jc": 2,
        "Jmin": 32,
        "Jmax": 64,
        "JcBeforeHS": 2,
        "JcDuringHS": 0,
        "JcAfterHS": 0,
        "JunkInterval": 10000000,
        "HandshakeDelay": 20000000,
        "MimicProtocol": "quic",
        "FragmentInitial": False,
        "RandomPadding": False,
    },
    "medium": {
        "Jc": 3,
        "Jmin": 40,
        "Jmax": 80,
        "JcBeforeHS": 2,
        "JcDuringHS": 1,
        "JcAfterHS": 0,
        "JunkInterval": 15000000,
        "HandshakeDelay": 25000000,
        "MimicProtocol": "https",
        "PaddingMin": 8,
        "PaddingMax": 32,
        "RandomPadding": True,
    },
    "heavy": {
        "Jc": 6,
        "Jmin": 32,
        "Jmax": 128,
        "JcBeforeHS": 3,
        "JcDuringHS": 2,
        "JcAfterHS": 1,
        "JunkInterval": 25000000,
        "HandshakeDelay": 75000000,
        "MimicProtocol": "https",
        "FragmentInitial": True,
        "FragmentSize": 512,
        "PaddingMin": 16,
        "PaddingMax": 64,
        "RandomPadding": True,
        "SNIFragmentation": True,
    },
    "gfw": {
        "Jc": 15,
        "Jmin": 30,
        "Jmax": 120,
        "JcBeforeHS": 3,
        "JcAfterI1": 2,
        "JcDuringHS": 5,
        "JcAfterHS": 3,
        "JunkInterval": 20000000,
        "HandshakeDelay": 30000000,
        "MimicProtocol": "https",
        "FragmentInitial": True,
        "FragmentSize": 512,
        "PaddingMin": 16,
        "PaddingMax": 64,
        "RandomPadding": True,
        "SNIFragmentation": True,
        "CustomHeaders": True,
        "MimicTLS": True,
    },
}

# AtomicNoize presets for WireGuard obfuscation
ATOMICNOIZE_PRESETS: Dict[str, Dict[str, Any]] = {
    "light": {
        "I1": "<b 0c0d0e0f>",
        "Jc": 10,
        "Jmin": 40,
        "Jmax": 90,
        "JcAfterI1": 1,
        "JcBeforeHS": 1,
        "JcAfterHS": 1,
        "JunkInterval": 100000000,
        "HandshakeDelay": 10000000,
        "AllowZeroSize": False,
    },
    "medium": {
        "I1": "<b 0c0d0e0f>",
        "I3": "<b 040506>",
        "Jc": 25,
        "Jmin": 40,
        "Jmax": 90,
        "JcAfterI1": 2,
        "JcBeforeHS": 3,
        "JcAfterHS": 2,
        "JunkInterval": 150000000,
        "HandshakeDelay": 25000000,
        "AllowZeroSize": True,
    },
    "heavy": {
        "I1": "<b 0c0d0e0f>",
        "I3": "<b 040506>",
        "I4": "<b 0708>",
        "I5": "<b 09>",
        "Jc": 85,
        "Jmin": 40,
        "Jmax": 90,
        "JcAfterI1": 3,
        "JcBeforeHS": 5,
        "JcAfterHS": 4,
        "JunkInterval": 150000000,
        "HandshakeDelay": 25000000,
        "AllowZeroSize": True,
    },
}
