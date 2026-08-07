// ConfigStream Laboratory - Proxy Parser
// SPDX-License-Identifier: AGPL-3.0-or-later

const UUID_PROTOCOLS = new Set(['vless', 'vmess', 'tuic']);
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function parsePort(value, fallback = 443) {
    if (value === undefined || value === null || value === '') return fallback;
    const text = String(value).trim();
    if (!/^\d{1,5}$/.test(text)) return null;
    const port = Number(text);
    return Number.isInteger(port) && port >= 1 && port <= 65535 ? port : null;
}

function decodeBase64Utf8(value) {
    const normalized = String(value).replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized + '='.repeat((4 - normalized.length % 4) % 4);
    const binary = atob(padded);
    const bytes = Uint8Array.from(binary, char => char.charCodeAt(0));
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
}

function validIdentifier(protocol, value) {
    if (!UUID_PROTOCOLS.has(protocol)) return true;
    return UUID_RE.test(String(value || ''));
}

export function parseProxyUri(input) {
    let uri = String(input || '').trim();
    if (!uri || uri.length > 16384) return null;

    const schemeMatch = uri.match(/^([a-zA-Z][a-zA-Z0-9+.-]*):\/\//);
    if (!schemeMatch) return null;

    let protocol = schemeMatch[1].toLowerCase();
    if (protocol === 'hy2' || protocol === 'husi') protocol = 'hysteria2';
    if (protocol === 'wg') protocol = 'wireguard';
    if (protocol === 'socks') protocol = 'socks5';

    let address = '';
    let port = 443;
    let uuid = '';
    let remark = '';

    try {
        const fragIdx = uri.indexOf('#');
        if (fragIdx !== -1) {
            try {
                remark = decodeURIComponent(uri.substring(fragIdx + 1));
            } catch {
                console.debug('[lab parser] Rejected malformed proxy URI fragment');
                return null;
            }
            uri = uri.substring(0, fragIdx);
        }

        if (protocol === 'vmess') {
            const encoded = uri.replace(/^vmess:\/\//i, '');
            const data = JSON.parse(decodeBase64Utf8(encoded));
            if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
            address = String(data.add || data.addr || '').trim();
            const parsedPort = parsePort(data.port);
            if (parsedPort === null) return null;
            port = parsedPort;
            uuid = String(data.id || '').trim();
            remark = remark || String(data.ps || '').trim();
        } else {
            const url = new URL(uri);
            address = String(url.hostname || '').trim();
            const parsedPort = parsePort(url.port);
            if (parsedPort === null) return null;
            port = parsedPort;
            uuid = url.username ? decodeURIComponent(url.username) : '';
        }
    } catch (error) {
        console.debug('[lab parser] Rejected malformed proxy URI');
        return null;
    }

    if (!address || address.length > 253 || /[\s/@]/.test(address)) return null;
    if (!validIdentifier(protocol, uuid)) return null;

    return {
        protocol,
        address,
        port,
        uuid,
        remark: remark || `${protocol}@${address}`,
        config: uri,
    };
}
