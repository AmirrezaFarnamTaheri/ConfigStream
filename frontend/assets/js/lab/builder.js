// ConfigStream Laboratory - Chain Builder
// SPDX-License-Identifier: AGPL-3.0-or-later

import { WARP_PUBLIC_KEY } from './state.js';

// --- Shared Config Skeleton ---
export function wrapConfig(outbounds, primaryTag) {
    return {
        log: { level: 'info' },
        inbounds: [{ type: 'mixed', tag: 'mixed-in', listen: '127.0.0.1', listen_port: 2080 }],
        outbounds: [...outbounds, { type: 'direct', tag: 'direct' }, { type: 'block', tag: 'block' }],
        route: { rules: [{ inbound: ['mixed-in'], outbound: primaryTag }], final: primaryTag }
    };
}

export function makeWarpOutbound(tag, ip, port, key) {
    const o = {
        type: 'wireguard', tag: tag, server: ip, server_port: port,
        local_address: ['172.16.0.2/32', 'fd01:db8:85a3::2/128'],
        private_key: 'YNS+CEQE6JIQiVWcOUJd0K8FLFeCQBONJnXCdFnMRlQ=',
        peer_public_key: WARP_PUBLIC_KEY, mtu: 1280
    };
    if (key) o.reserved = [0, 0, 0];
    return o;
}

export function applyEvasion(outbound, evasion) {
    if (!evasion) return outbound;
    if (outbound.tls && typeof outbound.tls === 'object') {
        if (evasion.fingerprint) outbound.tls.utls = { enabled: true, fingerprint: evasion.fingerprint };
        if (evasion.alpn) outbound.tls.alpn = evasion.alpn.split(',').map(s => s.trim());
    }
    if (evasion.mux) {
        outbound.multiplex = { enabled: true, protocol: evasion.mux, max_connections: 4, padding: evasion.muxPadding };
    }
    return outbound;
}

export function buildProxyOutbound(proxy) {
    const p = proxy;
    const base = { tag: 'proxy-chain', server: p.address, server_port: p.port };
    switch (p.protocol) {
        case 'vless':
            return { ...base, type: 'vless', uuid: p.uuid || '', flow: '', tls: { enabled: true, server_name: p.address }, packet_encoding: 'xudp' };
        case 'vmess':
            return { ...base, type: 'vmess', uuid: p.uuid || '', security: 'auto', tls: { enabled: true, server_name: p.address } };
        case 'trojan':
            return { ...base, type: 'trojan', password: p.uuid || '', tls: { enabled: true, server_name: p.address } };
        case 'shadowsocks': case 'ss':
            return { ...base, type: 'shadowsocks', method: 'aes-128-gcm', password: p.uuid || '' };
        case 'hysteria2':
            return { ...base, type: 'hysteria2', password: p.uuid || '', tls: { enabled: true, server_name: p.address } };
        case 'tuic':
            return { ...base, type: 'tuic', uuid: p.uuid || '', password: p.uuid || '', tls: { enabled: true, server_name: p.address } };
        case 'wireguard':
            return { ...base, type: 'wireguard', local_address: ['172.16.0.4/32'], private_key: p.uuid || '', peer_public_key: '', mtu: 1280 };
        default:
            return { ...base, type: p.protocol, uuid: p.uuid || '' };
    }
}

// --- Specific Strategy Builders ---

export function buildSingboxChain(proxy, warpIp, warpPort, key, evasion) {
    const warp = makeWarpOutbound('warp-out', warpIp, warpPort, key);
    const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
    proxyOut.detour = 'warp-out';
    return wrapConfig([proxyOut, warp], proxyOut.tag);
}

export function buildDoubleWarpChain(proxy, innerIp, innerPort, innerKey, outerSpec, outerKey, evasion) {
    const [outerIp, outerPortStr] = (outerSpec || innerIp + ':' + innerPort).split(':');
    const outerPort = parseInt(outerPortStr) || 2408;
    const outerWarp = makeWarpOutbound('warp-outer', outerIp, outerPort, outerKey);
    const innerWarp = makeWarpOutbound('warp-inner', innerIp, innerPort, innerKey);
    innerWarp.detour = 'warp-outer';
    innerWarp.local_address = ['172.16.0.3/32', 'fd01:db8:85a3::3/128'];
    const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
    proxyOut.detour = 'warp-inner';
    return wrapConfig([proxyOut, innerWarp, outerWarp], proxyOut.tag);
}

export function buildFragmentChain(proxy, fragSize, fragDelay, evasion) {
    const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
    if (proxyOut.tls && typeof proxyOut.tls === 'object') {
        const [minS, maxS] = (fragSize || '10-30').split('-').map(Number);
        const [minD, maxD] = (fragDelay || '5-10').split('-').map(Number);
        proxyOut.tls.fragment = { enabled: true, size: (minS || 10) + '-' + (maxS || 30), sleep: (minD || 5) + '-' + (maxD || 10) };
    }
    return wrapConfig([proxyOut], proxyOut.tag);
}

export function buildWorkerChain(proxy, workerUrl, evasion) {
    const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
    try {
        const u = new URL(workerUrl);
        proxyOut.server = u.hostname;
        proxyOut.server_port = u.port ? parseInt(u.port) : 443;
        if (proxyOut.tls && typeof proxyOut.tls === 'object') {
            proxyOut.tls.server_name = u.hostname;
        }
        proxyOut.transport = { type: 'ws', path: '/' + proxy.address + ':' + proxy.port, headers: { Host: u.hostname } };
    } catch { /* keep as-is */ }
    return wrapConfig([proxyOut], proxyOut.tag);
}

export function buildRelayChain(proxy, layerOuts, evasion) {
    const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
    const outbounds = [proxyOut];

    if (layerOuts.length > 0) {
        proxyOut.detour = layerOuts[layerOuts.length - 1].tag;
    }
    for (let i = layerOuts.length - 1; i > 0; i--) {
        layerOuts[i].detour = layerOuts[i - 1].tag;
    }

    outbounds.push(...layerOuts.reverse());
    return wrapConfig(outbounds, proxyOut.tag);
}

export function buildCustomChain(proxy, customOutbounds, evasion) {
    const proxyOut = applyEvasion(buildProxyOutbound(proxy), evasion);
    if (Array.isArray(customOutbounds) && customOutbounds.length > 0) {
        const lastCustomTag = customOutbounds[customOutbounds.length - 1].tag || 'custom-out';
        proxyOut.detour = lastCustomTag;
    }
    return wrapConfig([proxyOut, ...customOutbounds], proxyOut.tag);
}
