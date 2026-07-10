// ConfigStream Laboratory - Chain Builder
// SPDX-License-Identifier: AGPL-3.0-or-later

import { WARP_PUBLIC_KEY } from './state.js';

function parsePort(value, fallback = null) {
    const text = String(value ?? '').trim();
    if (!text) return fallback;
    if (!/^\d{1,5}$/.test(text)) return null;
    const port = Number(text);
    return Number.isInteger(port) && port >= 1 && port <= 65535 ? port : null;
}

function normalizeHost(value) {
    const raw = String(value ?? '').trim();
    if (!raw || raw.length > 253 || /[\s/@]/.test(raw)) return null;
    try {
        const candidate = raw.includes(':') && !raw.startsWith('[') ? `[${raw}]` : raw;
        const parsed = new URL(`https://${candidate}`);
        return parsed.hostname || null;
    } catch {
        return null;
    }
}

function parseEndpoint(value, fallbackHost, fallbackPort) {
    const raw = String(value ?? '').trim();
    if (!raw) return { host: fallbackHost, port: fallbackPort };
    try {
        const parsed = new URL(`udp://${raw}`);
        const host = normalizeHost(parsed.hostname);
        const port = parsePort(parsed.port, fallbackPort);
        if (!host || port === null) return null;
        return { host, port };
    } catch {
        const host = normalizeHost(raw);
        return host ? { host, port: fallbackPort } : null;
    }
}

function parseRange(value, fallbackMin, fallbackMax, minAllowed, maxAllowed) {
    const text = String(value ?? `${fallbackMin}-${fallbackMax}`).trim();
    const match = /^(\d+)-(\d+)$/.exec(text);
    if (!match) return null;
    const min = Number(match[1]);
    const max = Number(match[2]);
    if (!Number.isSafeInteger(min) || !Number.isSafeInteger(max) || min > max) return null;
    if (min < minAllowed || max > maxAllowed) return null;
    return `${min}-${max}`;
}

function tlsConfig(proxy) {
    const serverName = normalizeHost(proxy.server_name || proxy.sni || proxy.address);
    return serverName ? { enabled: true, server_name: serverName } : { enabled: true };
}

export function wrapConfig(outbounds, primaryTag) {
    return {
        log: { level: 'info' },
        inbounds: [{ type: 'mixed', tag: 'mixed-in', listen: '127.0.0.1', listen_port: 2080 }],
        outbounds: [...outbounds, { type: 'direct', tag: 'direct' }, { type: 'block', tag: 'block' }],
        route: { rules: [{ inbound: ['mixed-in'], outbound: primaryTag }], final: primaryTag }
    };
}

export function makeWarpOutbound(tag, ip, port, key) {
    const host = normalizeHost(ip);
    const validPort = parsePort(port);
    const privateKey = String(key || '').trim();
    if (!host || validPort === null) throw new TypeError('Invalid WARP endpoint');
    if (!privateKey) throw new TypeError('A WARP private key is required');
    return {
        type: 'wireguard', tag: String(tag), server: host, server_port: validPort,
        local_address: ['172.16.0.2/32', 'fd01:db8:85a3::2/128'],
        private_key: privateKey,
        peer_public_key: WARP_PUBLIC_KEY, mtu: 1280, reserved: [0, 0, 0]
    };
}

export function applyEvasion(outbound, evasion) {
    if (!evasion) return outbound;
    if (outbound.tls && typeof outbound.tls === 'object') {
        if (evasion.fingerprint) outbound.tls.utls = { enabled: true, fingerprint: String(evasion.fingerprint) };
        if (evasion.alpn) outbound.tls.alpn = String(evasion.alpn).split(',').map(s => s.trim()).filter(Boolean);
        if (evasion.tlsPadding) outbound.tls.padding = true;
        if (evasion.ech) outbound.tls.ech = { enabled: true, config: String(evasion.ech) };
    }
    if (evasion.mux) outbound.multiplex = { enabled: true, protocol: String(evasion.mux), max_connections: 4, padding: Boolean(evasion.muxPadding) };
    if (evasion.tfo || evasion.mptcp) {
        const dial = outbound.dial && typeof outbound.dial === 'object' ? outbound.dial : {};
        if (evasion.tfo) dial.tcp_fast_open = true;
        if (evasion.mptcp) dial.tcp_multi_path = true;
        outbound.dial = dial;
    }
    return outbound;
}

export function buildProxyOutbound(proxy) {
    const p = proxy || {};
    const server = normalizeHost(p.address);
    const serverPort = parsePort(p.port);
    if (!server || serverPort === null) throw new TypeError('Invalid proxy endpoint');
    const base = { tag: 'proxy-chain', server, server_port: serverPort };
    switch (String(p.protocol || '').toLowerCase()) {
        case 'vless': return { ...base, type: 'vless', uuid: p.uuid || '', flow: '', tls: tlsConfig(p), packet_encoding: 'xudp' };
        case 'vmess': return { ...base, type: 'vmess', uuid: p.uuid || '', security: 'auto', tls: tlsConfig(p) };
        case 'trojan': return { ...base, type: 'trojan', password: p.uuid || '', tls: tlsConfig(p) };
        case 'shadowsocks': case 'ss': return { ...base, type: 'shadowsocks', method: 'aes-128-gcm', password: p.uuid || '' };
        case 'hysteria2': return { ...base, type: 'hysteria2', password: p.uuid || '', tls: tlsConfig(p) };
        case 'tuic': return { ...base, type: 'tuic', uuid: p.uuid || '', password: p.uuid || '', tls: tlsConfig(p) };
        case 'wireguard': return { ...base, type: 'wireguard', local_address: ['172.16.0.4/32'], private_key: p.uuid || '', peer_public_key: '', mtu: 1280 };
        default: return { ...base, type: String(p.protocol || 'unknown'), uuid: p.uuid || '' };
    }
}

export function buildSingboxChain(proxy, warpIp, warpPort, key, evasion) {
    const warp = makeWarpOutbound('warp-out', warpIp, warpPort, key);
    const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
    proxyOut.detour = 'warp-out';
    return wrapConfig([proxyOut, warp], proxyOut.tag);
}

export function buildDoubleWarpChain(proxy, innerIp, innerPort, innerKey, outerSpec, outerKey, evasion) {
    const innerHost = normalizeHost(innerIp);
    const validInnerPort = parsePort(innerPort);
    if (!innerHost || validInnerPort === null) throw new TypeError('Invalid inner WARP endpoint');
    const outer = parseEndpoint(outerSpec, innerHost, validInnerPort);
    if (!outer) throw new TypeError('Invalid outer WARP endpoint');
    const outerWarp = makeWarpOutbound('warp-outer', outer.host, outer.port, outerKey);
    const innerWarp = makeWarpOutbound('warp-inner', innerHost, validInnerPort, innerKey);
    innerWarp.detour = 'warp-outer';
    innerWarp.local_address = ['172.16.0.3/32', 'fd01:db8:85a3::3/128'];
    const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
    proxyOut.detour = 'warp-inner';
    return wrapConfig([proxyOut, innerWarp, outerWarp], proxyOut.tag);
}

export function buildFragmentChain(proxy, fragSize, fragDelay, evasion) {
    const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
    if (proxyOut.tls && typeof proxyOut.tls === 'object') {
        const size = parseRange(fragSize, 10, 30, 1, 65535);
        const sleep = parseRange(fragDelay, 5, 10, 0, 60000);
        if (!size || !sleep) throw new TypeError('Invalid fragmentation range');
        proxyOut.tls.fragment = { enabled: true, size, sleep };
    }
    return wrapConfig([proxyOut], proxyOut.tag);
}

export function buildWorkerChain(proxy, workerUrl, evasion) {
    const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
    const worker = new URL(String(workerUrl || ''));
    if (worker.protocol !== 'https:') throw new TypeError('Worker URL must use HTTPS');
    const host = normalizeHost(worker.hostname);
    const port = parsePort(worker.port, 443);
    if (!host || port === null) throw new TypeError('Invalid worker endpoint');
    const target = `${proxyOut.server}:${proxyOut.server_port}`;
    proxyOut.server = host;
    proxyOut.server_port = port;
    if (proxyOut.tls && typeof proxyOut.tls === 'object') proxyOut.tls.server_name = host;
    proxyOut.transport = { type: 'ws', path: `/${target}`, headers: { Host: host } };
    return wrapConfig([proxyOut], proxyOut.tag);
}

export function buildRelayChain(proxy, layerOuts, evasion) {
    const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
    const layers = Array.isArray(layerOuts) ? layerOuts.map(layer => ({ ...layer })) : [];
    const outbounds = [proxyOut];
    if (layers.length > 0) proxyOut.detour = layers[layers.length - 1].tag;
    for (let i = layers.length - 1; i > 0; i--) layers[i].detour = layers[i - 1].tag;
    outbounds.push(...layers.reverse());
    return wrapConfig(outbounds, proxyOut.tag);
}

export function buildCustomChain(proxy, customOutbounds, evasion) {
    const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
    const custom = Array.isArray(customOutbounds) ? customOutbounds : [];
    if (custom.length > 0) proxyOut.detour = custom[custom.length - 1].tag || 'custom-out';
    return wrapConfig([proxyOut, ...custom], proxyOut.tag);
}
