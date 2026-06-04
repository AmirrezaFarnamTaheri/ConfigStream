// ConfigStream Laboratory - Proxy Parser
// SPDX-License-Identifier: AGPL-3.0-or-later

export function parseProxyUri(uri) {
    uri = (uri || '').trim();
    if (!uri) return null;

    // Extract protocol
    const schemeMatch = uri.match(/^([a-zA-Z][a-zA-Z0-9+.-]*):\/\//);
    if (!schemeMatch) return null;

    let protocol = schemeMatch[1].toLowerCase();
    // Normalize
    if (protocol === 'hy2' || protocol === 'husi') protocol = 'hysteria2';
    if (protocol === 'wg') protocol = 'wireguard';
    if (protocol === 'socks') protocol = 'socks5';

    // Try to extract address:port from URI
    let address = '', port = 443, uuid = '', remark = '';
    try {
        // Remove fragment (remark)
        const fragIdx = uri.indexOf('#');
        if (fragIdx !== -1) {
            remark = decodeURIComponent(uri.substring(fragIdx + 1));
            uri = uri.substring(0, fragIdx);
        }

        if (protocol === 'vmess') {
            // VMess uses base64-encoded JSON
            const b64 = uri.replace(/^vmess:\/\//, '');
            try {
                const json = JSON.parse(atob(b64));
                address = json.add || json.addr || '';
                port = parseInt(json.port) || 443;
                uuid = json.id || '';
                remark = remark || json.ps || '';
            } catch {
                return null;
            }
        } else {
            // Standard URI parsing for vless, trojan, ss, etc.
            const url = new URL(uri);
            address = url.hostname || '';
            port = parseInt(url.port) || 443;
            uuid = url.username ? decodeURIComponent(url.username) : '';
        }
    } catch {
        return null;
    }

    if (!address) return null;

    return {
        protocol,
        address,
        port,
        uuid,
        remark: remark || `${protocol}@${address}`,
        config: uri // original without fragment
    };
}
