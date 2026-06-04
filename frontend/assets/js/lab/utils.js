// ConfigStream Laboratory - Utilities
// SPDX-License-Identifier: AGPL-3.0-or-later

import { PROTOCOL_PRIORITY_INDEX, PROTOCOL_PRIORITY, STATIC_HOST_SUFFIXES } from './state.js';

export const $ = (sel) => document.querySelector(sel);
export const $$ = (sel) => document.querySelectorAll(sel);

export function normalizeProtocolName(protocol) {
    const raw = String(protocol || '').trim().toLowerCase();
    if (!raw) return 'unknown';
    if (raw === 'hy2' || raw === 'husi') return 'hysteria2';
    if (raw === 'wg') return 'wireguard';
    if (raw === 'ss') return 'shadowsocks';
    if (raw === 'socks') return 'socks5';
    return raw;
}

export function compareProtocols(a, b) {
    const pa = normalizeProtocolName(a);
    const pb = normalizeProtocolName(b);
    const ia = Object.prototype.hasOwnProperty.call(PROTOCOL_PRIORITY_INDEX, pa)
        ? PROTOCOL_PRIORITY_INDEX[pa]
        : PROTOCOL_PRIORITY.length;
    const ib = Object.prototype.hasOwnProperty.call(PROTOCOL_PRIORITY_INDEX, pb)
        ? PROTOCOL_PRIORITY_INDEX[pb]
        : PROTOCOL_PRIORITY.length;
    if (ia !== ib) return ia - ib;
    return pa.localeCompare(pb);
}

export function comparePipelineProxy(a, b) {
    const protoCmp = compareProtocols(a.protocol, b.protocol);
    if (protoCmp !== 0) return protoCmp;
    const remarkCmp = String(a.remark || '').localeCompare(String(b.remark || ''));
    if (remarkCmp !== 0) return remarkCmp;
    const addressCmp = String(a.address || '').localeCompare(String(b.address || ''));
    if (addressCmp !== 0) return addressCmp;
    return Number(a.port || 0) - Number(b.port || 0);
}

export function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[ch]));
}

export function isStaticHosting() {
    const host = (window.location && window.location.hostname) || '';
    const protocol = (window.location && window.location.protocol) || '';
    return protocol === 'file:' || STATIC_HOST_SUFFIXES.some((suffix) => host.includes(suffix));
}

export function joinBase(base, file) {
    const cleanBase = String(base || '').replace(/\/+$/, '');
    const cleanFile = String(file || '').replace(/^\/+/, '');
    return `${cleanBase}/${cleanFile}`;
}
