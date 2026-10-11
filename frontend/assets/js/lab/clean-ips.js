// ConfigStream Laboratory - Clean IP Discovery
// SPDX-License-Identifier: AGPL-3.0-or-later

import { state, DEFAULT_CLEAN_IPS } from './state.js';
import { showResultText, showResultHTML, goToStep } from './ui.js';
import { $, escapeHtml } from './utils.js';

export function parseManualCleanIpLine(line) {
    const raw = String(line || '').trim();
    if (!raw) return null;

    const match = raw.match(/^(\[[0-9a-fA-F:.]+\]|[A-Za-z0-9.-]+)(?::(\d{1,5}))?$/);
    if (!match) return null;

    const host = match[1].replace(/^\[|\]$/g, '');
    const port = parseInt(match[2] || '443', 10);
    if (!Number.isInteger(port) || port < 1 || port > 65535) return null;
    if (match[1].startsWith('[')) {
        // URL's authority parser validates IPv6 syntax, not only its alphabet.
        try { new URL(`http://[${host}]/`); } catch { return null; }
    } else if (/^\d+(?:\.\d+){3}$/.test(host)) {
        if (!host.split('.').every(part => Number(part) <= 255)) return null;
    }

    return {
        ip: host,
        port,
        latency: null,
        status: 'untested'
    };
}

// Accept either a host:port string or the public {ip, port} record. Published
// candidate endpoints have not been tested from the visitor's network.
export function parsePublishedCleanIp(entry) {
    if (typeof entry === 'string') return parseManualCleanIpLine(entry);
    if (!entry || typeof entry !== 'object') return null;
    const host = String(entry.ip || '').trim();
    if (!host) return null;
    const port = Number(entry.port);
    if (!Number.isInteger(port) || port < 1 || port > 65535) return null;
    const text = host.includes(':') ? `[${host}]:${port}` : `${host}:${port}`;
    return parseManualCleanIpLine(text);
}

export function formatCleanIpEndpoint(entry) {
    const host = String(entry.ip || '');
    return `${host.includes(':') ? `[${host}]` : host}:${entry.port}`;
}

export function renderCleanIpTable() {
    const tbody = $('#cleanIpTableBody');
    const container = $('#cleanIpResults');
    if (!tbody || !container) return;

    tbody.replaceChildren();
    state.cleanIps.forEach(ip => {
        const tr = document.createElement('tr');
        const statusCls = ip.status === 'ok' ? 'status-ok' : (ip.status === 'fail' ? 'status-fail' : '');
        const statusText = ip.status === 'ok' ? 'OK' : ip.status === 'fail' ? 'Failed' : 'Untested';
        
        const tdIp = document.createElement('td');
        tdIp.textContent = formatCleanIpEndpoint(ip);
        const tdLat = document.createElement('td');
        tdLat.textContent = ip.latency !== null ? ip.latency + 'ms' : '-';
        const tdStatus = document.createElement('td');
        if (statusCls) tdStatus.className = statusCls;
        tdStatus.textContent = statusText;
        
        tr.append(tdIp, tdLat, tdStatus);
        tbody.appendChild(tr);
    });
    container.style.display = 'block';
}

export function populateWarpIpSelect() {
    const select = $('#warpCleanIp');
    if (!select) return;
    select.replaceChildren();
    state.cleanIps.forEach((ip, i) => {
        const opt = document.createElement('option');
        opt.value = formatCleanIpEndpoint(ip);
        opt.textContent = formatCleanIpEndpoint(ip) + (ip.latency !== null ? ` (${ip.latency}ms)` : '');
        if (i === 0) opt.selected = true;
        select.appendChild(opt);
    });
}

export function handleCleanIpMethodChange() {
    const method = ($('#cleanIpMethod') || {}).value;
    const manualDiv = $('#manualIpInput');
    if (manualDiv) manualDiv.style.display = method === 'manual' ? 'block' : 'none';
}

export async function handleStep2Next() {
    const method = ($('#cleanIpMethod') || {}).value;
    state.cleanIps = [];

    if (method === 'manual') {
        const raw = ($('#manualCleanIps') || {}).value || '';
        const lines = raw.split('\n').map(l => l.trim()).filter(Boolean);
        state.cleanIps = lines.map(parseManualCleanIpLine).filter(Boolean);
        if (lines.length > 0 && state.cleanIps.length === 0) {
            showResultText('step2Result', 'error', 'No valid clean IP entries found. Use host:port, IPv4:port, or [IPv6]:port.');
            return;
        }
    } else if (method === 'auto') {
        showResultText('step2Result', 'pending', 'Fetching clean IPs from ConfigStream...');
        try {
            const resp = await fetch((window.ROOT_PATH || '') + 'data/clean_ips.json?cb=' + Date.now());
            if (resp.ok) {
                const data = await resp.json();
                if (Array.isArray(data) && data.length > 0) {
                    state.cleanIps = data.slice(0, 200).map(parsePublishedCleanIp).filter(Boolean).slice(0, 20);
                }
            }
        } catch { /* fallback */ }

        if (state.cleanIps.length === 0) {
            state.cleanIps = DEFAULT_CLEAN_IPS.map(parsePublishedCleanIp).filter(Boolean);
        }
    } else if (method === 'scan') {
        showResultHTML('step2Result', 'info',
            '<strong>Local Scan:</strong> Open a terminal and run:<br>' +
            '<code>for ip in 162.159.192.1 188.114.98.224 162.159.195.2; do ' +
            'for port in 854 890 2408 500; do ' +
            'curl -x socks5://$ip:$port --connect-timeout 3 -o /dev/null -w "%{http_code} %{time_total}s $ip:$port\\n" https://cp.cloudflare.com/generate_204 2>/dev/null; ' +
            'done; done</code><br><br>Paste the working IP:port pairs into the Manual input above.'
        );
        const methodEl = $('#cleanIpMethod');
        if (methodEl) methodEl.value = 'manual';
        const manualDiv = $('#manualIpInput');
        if (manualDiv) manualDiv.style.display = 'block';
        return;
    }

    if (state.cleanIps.length === 0) {
        showResultText('step2Result', 'error', 'No clean IPs found. Try manual input or local scan.');
        return;
    }

    renderCleanIpTable();
    populateWarpIpSelect();

    showResultText('step2Result', 'success', `Loaded ${state.cleanIps.length} untested candidate endpoint(s). Actual reachability depends on your network.`);
    setTimeout(() => goToStep(3), 600);
}
