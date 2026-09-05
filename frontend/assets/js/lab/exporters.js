// ConfigStream Laboratory - Exporters
// SPDX-License-Identifier: AGPL-3.0-or-later

import { WARP_PUBLIC_KEY } from './state.js';
import { requiresXrayTransportSecurity } from './xray-security.js';

function requirePort(value) {
    const port = Number(value);
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
        throw new TypeError('Invalid proxy port');
    }
    return port;
}

function requireString(value, field) {
    const text = String(value ?? '');
    if (!text && field) throw new TypeError(`${field} is required`);
    return text;
}

function toBase64Utf8(value) {
    const bytes = new TextEncoder().encode(String(value));
    let binary = '';
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return btoa(binary);
}

function normalizeReserved(value) {
    const input = Array.isArray(value) ? value : [0, 0, 0];
    const result = input.slice(0, 3).map(item => Number(item));
    while (result.length < 3) result.push(0);
    if (result.some(item => !Number.isInteger(item) || item < 0 || item > 255)) {
        throw new TypeError('WireGuard reserved bytes must be integers from 0 to 255');
    }
    return result;
}

function transportOptions(sbOut, clashProxy) {
    const transport = sbOut.transport && typeof sbOut.transport === 'object'
        ? sbOut.transport
        : {};
    const tls = sbOut.tls && typeof sbOut.tls === 'object' ? sbOut.tls : {};

    if (transport.type === 'ws' || transport.type === 'httpupgrade') {
        clashProxy.network = 'ws';
        clashProxy['ws-opts'] = {
            path: String(transport.path || '/'),
            headers: transport.headers && typeof transport.headers === 'object'
                ? Object.fromEntries(
                    Object.entries(transport.headers).map(([key, value]) => [String(key), String(value)])
                )
                : {},
        };
        if (transport.type === 'httpupgrade') {
            clashProxy['ws-opts']['v2ray-http-upgrade'] = true;
        }
    } else if (transport.type === 'grpc') {
        clashProxy.network = 'grpc';
        clashProxy['grpc-opts'] = {
            'grpc-service-name': String(transport.service_name || ''),
        };
    } else if (transport.type === 'http') {
        clashProxy.network = 'h2';
        const hosts = Array.isArray(transport.host)
            ? transport.host.map(String)
            : transport.host
                ? [String(transport.host)]
                : [];
        clashProxy['h2-opts'] = { path: String(transport.path || '/'), host: hosts };
    }

    if (tls.utls && tls.utls.fingerprint) {
        clashProxy['client-fingerprint'] = String(tls.utls.fingerprint);
    }
    if (Array.isArray(tls.alpn) && tls.alpn.length) {
        clashProxy.alpn = tls.alpn.map(String);
    }
}

export function singboxOutboundToClash(sbOut) {
    if (!sbOut || typeof sbOut !== 'object') throw new TypeError('Invalid outbound');
    const type = String(sbOut.type || '');
    const name = requireString(sbOut.tag, 'Outbound tag');
    const server = requireString(sbOut.server, 'Outbound server');
    const port = requirePort(sbOut.server_port);
    const tls = sbOut.tls && typeof sbOut.tls === 'object' ? sbOut.tls : {};
    const sni = String(tls.server_name || server);
    let proxy;

    switch (type) {
        case 'vless':
            proxy = {
                name, type: 'vless', server, port,
                uuid: requireString(sbOut.uuid, 'VLESS UUID'),
                tls: tls.enabled === true,
                servername: sni,
            };
            if (sbOut.flow) proxy.flow = String(sbOut.flow);
            break;
        case 'vmess':
            proxy = {
                name, type: 'vmess', server, port,
                uuid: requireString(sbOut.uuid, 'VMess UUID'),
                alterId: 0, cipher: 'auto',
                tls: tls.enabled === true,
                servername: sni,
            };
            break;
        case 'trojan':
            proxy = {
                name, type: 'trojan', server, port,
                password: requireString(sbOut.password, 'Trojan password'),
                sni,
            };
            break;
        case 'shadowsocks':
            proxy = {
                name, type: 'ss', server, port,
                cipher: String(sbOut.method || 'aes-128-gcm'),
                password: requireString(sbOut.password, 'Shadowsocks password'),
            };
            break;
        case 'socks':
            if (sbOut.version && String(sbOut.version) !== '5') throw new TypeError('Clash requires SOCKS5');
            proxy = { name, type: 'socks5', server, port };
            break;
        case 'http':
            proxy = { name, type: 'http', server, port };
            break;
        case 'wireguard': {
            const privateKey = requireString(sbOut.private_key, 'WireGuard private key');
            const publicKey = requireString(sbOut.peer_public_key || WARP_PUBLIC_KEY, 'WireGuard public key');
            const localAddress = Array.isArray(sbOut.local_address)
                ? String(sbOut.local_address[0] || '172.16.0.2/32')
                : String(sbOut.local_address || '172.16.0.2/32');
            proxy = {
                name, type: 'wireguard', server, port,
                ip: localAddress.split('/')[0],
                'private-key': privateKey,
                'public-key': publicKey,
                reserved: normalizeReserved(sbOut.reserved),
                mtu: Number.isInteger(Number(sbOut.mtu)) ? Number(sbOut.mtu) : 1280,
                udp: true,
            };
            break;
        }
        case 'hysteria2':
            proxy = {
                name, type: 'hysteria2', server, port,
                password: requireString(sbOut.password, 'Hysteria2 password'),
                sni,
            };
            break;
        case 'tuic':
            proxy = {
                name, type: 'tuic', server, port,
                uuid: requireString(sbOut.uuid, 'TUIC UUID'),
                password: requireString(sbOut.password, 'TUIC password'),
                sni,
            };
            break;
        default:
            throw new TypeError(`Unsupported Clash outbound type: ${type}`);
    }

    if (type === 'socks' || type === 'http') {
        if (sbOut.username) {
            proxy.username = String(sbOut.username);
            proxy.password = String(sbOut.password || '');
        }
        proxy.tls = tls.enabled === true;
        if (proxy.tls) proxy.sni = sni;
    }
    if (tls.enabled === true) proxy['skip-cert-verify'] = tls.insecure === true;
    if (tls.reality && tls.reality.enabled) {
        proxy['reality-opts'] = {
            'public-key': String(tls.reality.public_key || ''),
            'short-id': String(tls.reality.short_id || ''),
        };
    }
    transportOptions(sbOut, proxy);
    if (sbOut.detour) proxy['dialer-proxy'] = String(sbOut.detour);
    return proxy;
}

export function buildClashYaml(chainConfig) {
    if (!chainConfig || !Array.isArray(chainConfig.outbounds)) {
        throw new TypeError('Missing chain outbounds');
    }
    const proxies = chainConfig.outbounds
        .filter(outbound => outbound && !['direct', 'block'].includes(outbound.type))
        .map(singboxOutboundToClash);
    const primaryTag = proxies.length ? proxies[0].name : 'DIRECT';
    const clash = {
        'mixed-port': 2080,
        'allow-lan': false,
        proxies,
        'proxy-groups': [
            { name: 'Chain', type: 'select', proxies: [primaryTag, 'DIRECT'] },
        ],
        rules: ['MATCH,Chain'],
    };
    if (chainConfig._vwarp && typeof chainConfig._vwarp === 'object') {
        clash['x-configstream-vwarp'] = chainConfig._vwarp;
    }
    // JSON is a strict subset of YAML 1.2. Serializing the complete data model
    // prevents attacker-controlled values from becoming YAML keys or structure.
    return JSON.stringify(clash, null, 2) + '\n';
}

export function singboxOutboundToXray(sbOut) {
    if (!sbOut || typeof sbOut !== 'object') throw new TypeError('Invalid outbound');
    const xOut = { tag: requireString(sbOut.tag, 'Outbound tag') };
    const type = String(sbOut.type || '');

    function buildStreamSettings(outbound) {
        const tls = outbound.tls && typeof outbound.tls === 'object' ? outbound.tls : {};
        const transport = outbound.transport && typeof outbound.transport === 'object'
            ? outbound.transport
            : {};
        const sni = String(tls.server_name || outbound.server || '');
        const stream = {
            method: 'raw',
            security: tls.enabled === true ? 'tls' : 'none',
        };
        if (stream.security === 'tls') {
            stream.tlsSettings = { serverName: sni };
            if (Array.isArray(tls.alpn) && tls.alpn.length) stream.tlsSettings.alpn = tls.alpn.map(String);
            if (tls.utls && tls.utls.fingerprint) stream.tlsSettings.fingerprint = String(tls.utls.fingerprint);
        }
        if (tls.reality && tls.reality.enabled) {
            stream.security = 'reality';
            stream.realitySettings = {
                serverName: sni,
                password: String(tls.reality.public_key || ''),
                shortId: String(tls.reality.short_id || ''),
                fingerprint: String((tls.utls && tls.utls.fingerprint) || 'chrome'),
            };
            delete stream.tlsSettings;
        }
        if (transport.type === 'ws') {
            stream.method = 'websocket';
            stream.wsSettings = {
                path: String(transport.path || '/'),
                headers: transport.headers && typeof transport.headers === 'object'
                    ? transport.headers
                    : {},
            };
        } else if (transport.type === 'grpc') {
            stream.method = 'grpc';
            stream.grpcSettings = { serviceName: String(transport.service_name || '') };
        } else if (transport.type === 'httpupgrade') {
            stream.method = 'httpupgrade';
            stream.httpupgradeSettings = {
                path: String(transport.path || '/'),
                host: String(transport.host || sni),
            };
        } else if (transport.type === 'http') {
            stream.method = 'xhttp';
            stream.xhttpSettings = {
                path: String(transport.path || '/'),
                host: transport.host
                    ? (Array.isArray(transport.host) ? transport.host.map(String) : [String(transport.host)])
                    : [sni],
            };
        }
        if (stream.method === 'raw') stream.rawSettings = { header: { type: 'none' } };
        return stream;
    }

    const address = requireString(sbOut.server, 'Outbound server');
    const port = requirePort(sbOut.server_port);
    if (type === 'vless') {
        const user = { id: requireString(sbOut.uuid, 'VLESS UUID'), encryption: 'none' };
        if (sbOut.flow) user.flow = String(sbOut.flow);
        xOut.protocol = 'vless';
        xOut.settings = { address, port, ...user };
        xOut.streamSettings = buildStreamSettings(sbOut);
    } else if (type === 'vmess') {
        xOut.protocol = 'vmess';
        xOut.settings = {
            address, port, id: requireString(sbOut.uuid, 'VMess UUID'), security: String(sbOut.security || 'auto'),
        };
        xOut.streamSettings = buildStreamSettings(sbOut);
    } else if (type === 'trojan') {
        xOut.protocol = 'trojan';
        xOut.settings = { address, port, password: requireString(sbOut.password, 'Trojan password') };
        xOut.streamSettings = buildStreamSettings(sbOut);
    } else if (type === 'shadowsocks') {
        xOut.protocol = 'shadowsocks';
        xOut.settings = {
            address, port, method: requireString(sbOut.method, 'Shadowsocks method'), password: requireString(sbOut.password, 'Shadowsocks password'),
        };
    } else if (type === 'socks' || type === 'http') {
        xOut.protocol = type;
        xOut.settings = { address, port };
        if (sbOut.username) { xOut.settings.user = String(sbOut.username); xOut.settings.pass = String(sbOut.password || ''); }
    } else if (type === 'wireguard') {
        xOut.protocol = 'wireguard';
        xOut.settings = {
            secretKey: requireString(sbOut.private_key, 'WireGuard private key'),
            address: Array.isArray(sbOut.local_address) ? sbOut.local_address.map(String) : [String(sbOut.local_address || '172.16.0.2/32')],
            peers: [{ endpoint: `${address.includes(':') ? '[' + address.replace(/^\[|\]$/g, '') + ']' : address}:${port}`, publicKey: requireString(sbOut.peer_public_key, 'WireGuard public key') }],
            reserved: normalizeReserved(sbOut.reserved),
            mtu: Number.isInteger(Number(sbOut.mtu)) ? Number(sbOut.mtu) : 1280,
        };
    } else if (type === 'hysteria2' || type === 'tuic') {
        throw new TypeError(`${type} is not supported by Xray; use sing-box.`);
    } else {
        throw new TypeError(`Unsupported Xray outbound type: ${type}`);
    }
    if (type !== 'wireguard') xOut.streamSettings = buildStreamSettings(sbOut);
    if (['trojan', 'vless'].includes(type) && xOut.streamSettings.security === 'none'
        && requiresXrayTransportSecurity(address)) {
        throw new TypeError(`${type} to a public destination requires TLS in Xray.`);
    }
    if (sbOut.detour) xOut.proxySettings = { tag: String(sbOut.detour) };
    return xOut;
}

export function buildXrayJson(chainConfig) {
    if (!chainConfig || !Array.isArray(chainConfig.outbounds) || !chainConfig.outbounds.length) {
        throw new TypeError('Missing chain outbounds');
    }
    const xray = {
        log: { loglevel: 'warning' },
        inbounds: [{ tag: 'socks', port: 2080, listen: '127.0.0.1', protocol: 'socks', settings: { udp: true } }],
        outbounds: [],
        routing: { rules: [{ type: 'field', inboundTag: ['socks'], outboundTag: String(chainConfig.outbounds[0].tag) }] },
    };
    if (chainConfig._vwarp && typeof chainConfig._vwarp === 'object') xray._vwarp = chainConfig._vwarp;
    for (const outbound of chainConfig.outbounds) {
        if (outbound.type === 'direct') xray.outbounds.push({ tag: String(outbound.tag), protocol: 'freedom', settings: {} });
        else if (outbound.type === 'block') xray.outbounds.push({ tag: String(outbound.tag), protocol: 'blackhole', settings: {} });
        else xray.outbounds.push(singboxOutboundToXray(outbound));
    }
    return JSON.stringify(xray, null, 2);
}

export function buildNekoboxLink(chainConfig) {
    if (!chainConfig) return '';
    return 'nekobox://import-singbox?config=' + encodeURIComponent(toBase64Utf8(JSON.stringify(chainConfig)));
}

export function buildPythonScript(chainConfig) {
    const configB64 = toBase64Utf8(JSON.stringify(chainConfig));
    return `#!/usr/bin/env python3
"""ConfigStream chain runner generated by Laboratory."""
import base64
import json
import os
import shutil
import subprocess
import tempfile

CONFIG = json.loads(base64.b64decode("${configB64}").decode("utf-8"))

def main():
    binary = shutil.which("sing-box")
    if not binary:
        raise RuntimeError("sing-box is required and must be installed from an official release")
    fd, path = tempfile.mkstemp(prefix="configstream-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(CONFIG, handle)
        subprocess.run([binary, "run", "-c", path], check=True)
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass

if __name__ == "__main__":
    main()
`;
}

export function buildBashScript(chainConfig) {
    const configB64 = toBase64Utf8(JSON.stringify(chainConfig));
    return `#!/usr/bin/env bash
set -euo pipefail

if ! command -v sing-box >/dev/null 2>&1; then
    echo "sing-box is required and must be installed from an official release" >&2
    exit 1
fi

CFG="$(mktemp -t cs-chain.XXXXXX.json)"
cleanup() { rm -f -- "$CFG"; }
trap cleanup EXIT INT TERM
printf '%s' '${configB64}' | base64 -d > "$CFG"
exec sing-box run -c "$CFG"
`;
}
