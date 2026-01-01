# Phase 19: Configuration & Constants - Analysis Report

## 19. Overview
This phase audits `src/configstream/constants.py` for safety, completeness, and correctness.

## 19.1. Security Constants
**Analysis**:
*   `DANGEROUS_PORTS`:
    *   **Audit**: `[21, 22, 23, 25, 110, 143, 445, 3389]`.
    *   **Correctness**: These are standard dangerous ports (FTP, SSH, Telnet, SMTP, POP3, IMAP, SMB, RDP).
    *   **Removed**: DB ports (3306, 5432, etc.) were removed to allow tunneling. This is a deliberate decision documented in the code comments.
*   `SUSPICIOUS_DOMAINS`:
    *   `[..., "192.168.", "10." ]`. Blocks private ranges.
    *   **Missing**: `172.16.` to `172.31.` (Class B private). `fc00::/7` (IPv6 ULA).
    *   **Risk**: A proxy pointing to `172.16.0.1` could access internal networks.
    *   **Action**: Add `172.16.` through `172.31.` regex or prefix logic in the validator (Regex is better for simple list, or `ipaddress` check).
*   `MAX_B64_INPUT_SIZE`: 10MB.
    *   **Discrepancy**: `src/configstream/parsers/extraction.py` ignores this constant and uses a hardcoded limit of `50 * 1024 * 1024` (50MB) in `extract_config_lines`.
    *   **Action**: Update `extraction.py` to use `MAX_B64_INPUT_SIZE` (or a separate `MAX_PAYLOAD_SIZE` constant) for consistency.
*   `MAX_CONFIG_LINE_LENGTH`: 10,000 chars. Prevents regex DoS on massive lines.

## 19.2. Protocol Support
*   `VALID_PROTOCOLS`: Comprehensive list (vmess, vless, hysteria2, wireguard, etc.).
*   `PROTOCOL_COLORS`: Used for UI. Consistent with `VALID_PROTOCOLS`.

## 19.3. Blocked Domains
*   `BLOCKED_DOMAINS`: Includes GitHub, GitLab, Telegram, PaaS domains.
*   **Purpose**: Likely used to prevent `fetcher` from treating a subscription link ITSELF as a proxy config if it parses incorrectly, or maybe to prevent "recursive" fetching if a proxy config points back to a subscription URL?
    *   Wait, `fetcher` downloads *from* these domains.
    *   The usage of `BLOCKED_DOMAINS` needs to be checked. Is it for *source URLs* or *proxy addresses*?
    *   If it's for *proxy addresses*, then blocking `workers.dev` or `cloudflare.com` is BAD, because many proxies are hosted there (Cloudflare Workers, Vless on Pages).
    *   **Hypothesis**: It's used to filter "junk" lines in parsers that might be accidental links.
    *   **Verification**: Confirmed in `src/configstream/parsers/extraction.py`. It is used to reject lines that look like URLs pointing to these domains if they are not proxy configs (don't contain `@` and start with http/s). This prevents the parser from treating a subscription link as a proxy config.
    *   **Risk**: Low. It correctly avoids false positives for subscription URLs.

## Recommendations
1.  **Private IP Ranges**: Update `SUSPICIOUS_DOMAINS` or the `SecurityValidator` logic to cover ALL private ranges (Class B `172.16-31`, IPv6 `fc00::`).
2.  **Verify Blocked Domains Usage**: Ensure `BLOCKED_DOMAINS` doesn't block legitimate Cloudflare Worker proxies (`*.workers.dev`).
