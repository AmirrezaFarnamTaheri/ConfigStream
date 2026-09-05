// SPDX-License-Identifier: AGPL-3.0-or-later
// Pinned Xray v26.7.28 private-destination rules; parity-tested against Python.
const networks = ["0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24", "192.0.2.0/24", "192.88.99.0/24", "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24", "224.0.0.0/3", "::/127", "fc00::/7", "fe80::/10", "ff00::/8"];
const domains = ["lan", "localdomain", "example", "invalid", "localhost", "test", "local", "home.arpa", "internal"];

function ipValue(host) {
    if (!host.includes(':')) {
        const octets = host.split('.').map(Number);
        if (octets.length !== 4 || octets.some(n => !Number.isInteger(n) || n < 0 || n > 255)) return null;
        return {bits:32, value:octets.reduce((value, octet) => (value << 8n) | BigInt(octet), 0n)};
    }
    const halves = host.split('::');
    const left = halves[0] ? halves[0].split(':') : [];
    const right = halves[1] ? halves[1].split(':') : [];
    const parts = halves.length === 2 ? [...left, ...Array(8-left.length-right.length).fill('0'), ...right] : left;
    if (parts.length !== 8) return null;
    const value = parts.reduce((acc, part) => (acc << 16n) | BigInt('0x'+part), 0n);
    if (value >> 32n === 65535n) return {bits:32, value:value & 0xffffffffn};
    return {bits:128, value};
}

export function requiresXrayTransportSecurity(address) {
    let host = String(address || '').trim().replace(/^\[|\]$/g, '').toLowerCase().replace(/\.$/, '');
    if (!host) return true;
    try {
        // URL canonicalization expands IPv4-mapped addresses into IPv6 hex groups.
        host = new URL('http://' + (host.includes(':') ? '['+host+']' : host)).hostname.replace(/^\[|\]$/g, '');
        const ip = ipValue(host);
        if (ip) return !networks.some(network => {
            const [base, prefix] = network.split('/');
            const other = ipValue(base);
            const shift = BigInt(ip.bits - Number(prefix));
            return ip.bits === other.bits && shift >= 0n && ip.value >> shift === other.value >> shift;
        });
    } catch { return true; }
    return !(/^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$/.test(host) || domains.some(suffix => host === suffix || host.endsWith('.'+suffix)));
}
