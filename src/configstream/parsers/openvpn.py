# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import re
from typing import Optional
from ..models import Proxy
from ..constants import MAX_OPENVPN_CONFIG_SIZE
from ..security_validator import SecurityValidator

logger = logging.getLogger(__name__)

# Pre-compiled patterns for OpenVPN parsing
_CLIENT_DIRECTIVE_RE = re.compile(r"(^|\s)client(\s|$)", re.MULTILINE)
_REMOTE_LINE_RE = re.compile(r"^remote\s+(\S+)\s+(\d+)", re.MULTILINE)
_REMOTE_FALLBACK_RE = re.compile(r"remote\s+(\S+)\s+(\d+)")
_HOSTNAME_FORMAT_RE = re.compile(r"^[\w\.\-