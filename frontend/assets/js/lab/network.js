// ConfigStream Laboratory - Network Testing
// SPDX-License-Identifier: AGPL-3.0-or-later

import { showResultHTML, renderGauge, renderHealthBadges } from './ui.js';
import { $, escapeHtml } from './utils.js';

export async function runDiagnosis() {
    const tbody = $('#diagTableBody');
    const container = $('#diagResults');
    const advice = $('#diagAdvice');
    if (!tbody || !container) return;
    container.style.display = 'block';
    
    tbody.replaceChildren();
    const loadingRow = document.createElement('tr');
    const loadingCell = document.createElement('td');
    loadingCell.colSpan = 3;
    loadingCell.textContent = 'Running tests...';
    loadingRow.appendChild(loadingCell);
    tbody.appendChild(loadingRow);

    const tests = [
        { name: 'Cloudflare HTTP', url: 'https://cp.cloudflare.com/generate_204', key: 'cf' },
        { name: 'Google HTTP', url: 'https://connectivitycheck.gstatic.com/generate_204', key: 'google' },
        { name: 'Cloudflare TLS', url: 'https://1.1.1.1/cdn-cgi/trace', key: 'cf_tls' },
        { name: 'GitHub API', url: 'https://api.github.com', key: 'github' },
        { name: 'Wikipedia', url: 'https://en.wikipedia.org/w/api.php?action=sitematrix&format=json', key: 'wikipedia' },
        { name: 'Cloudflare DoH', url: 'https://cloudflare-dns.com/dns-query?dns=AAABAAABAAAAAAAAB2V4YW1wbGUDY29tAAABAAE', key: 'doh' },
    ];
    const results = {};
    tbody.replaceChildren();

    for (const t of tests) {
        const tr = document.createElement('tr');
        const start = performance.now();
        try {
            await fetch(t.url, { mode: 'no-cors', cache: 'no-store', signal: AbortSignal.timeout(6000) });
            const lat = Math.round(performance.now() - start);
            results[t.key] = true;
            
            const tdName = document.createElement('td');
            tdName.textContent = t.name;
            const tdLat = document.createElement('td');
            tdLat.textContent = lat + 'ms';
            const tdStatus = document.createElement('td');
            tdStatus.className = 'status-ok';
            tdStatus.textContent = 'Reachable';
            
            tr.append(tdName, tdLat, tdStatus);
        } catch {
            results[t.key] = false;
            const tdName = document.createElement('td');
            tdName.textContent = t.name;
            const tdLat = document.createElement('td');
            tdLat.textContent = '-';
            const tdStatus = document.createElement('td');
            tdStatus.className = 'status-fail';
            tdStatus.textContent = 'Blocked';
            
            tr.append(tdName, tdLat, tdStatus);
        }
        tbody.appendChild(tr);
    }

    const reachable = Object.values(results).filter(Boolean).length;
    renderGauge(reachable, tests.length);
    renderHealthBadges(results);

    if (advice) {
        if (reachable >= 5) {
            showResultHTML('diagAdvice', 'success',
                '<strong>Excellent connectivity!</strong> All strategies work: ' +
                'WARP, Proxy Cascade, TLS Fragment, CDN Worker, or direct connection. ' +
                'Pick whichever is most convenient.');
        } else if (reachable >= 3) {
            showResultHTML('diagAdvice', 'success',
                '<strong>Good connectivity</strong> with some filtering. ' +
                'Best strategies: <strong>WARP</strong>, <strong>Proxy Cascade</strong>, or <strong>TLS Fragment</strong>. ' +
                'If you have a working local proxy (Psiphon, V2RayN), cascade through it.');
        } else if (results.cf || results.cf_tls) {
            showResultHTML('diagAdvice', 'info',
                '<strong>Cloudflare reachable</strong> but other sites are filtered. ' +
                'Strategies: <strong>WARP chain</strong>, <strong>TLS Fragment</strong>, or <strong>Double WARP</strong>. ' +
                'If you have a local proxy with broader access, try <strong>Proxy Cascade</strong> instead.');
        } else if (results.doh) {
            showResultHTML('diagAdvice', 'info',
                '<strong>DNS-over-HTTPS works</strong> but direct HTTPS is blocked. ' +
                'Strategies: <strong>CDN Worker relay</strong>, <strong>Proxy Cascade</strong> through a local tool, ' +
                'or <strong>Intranet Relay</strong> if a LAN host has less-filtered access. ' +
                'Run <code>python lab-scanner.py --scan-lan</code> to find LAN relays.');
        } else if (reachable > 0) {
            showResultHTML('diagAdvice', 'info',
                '<strong>Limited access.</strong> Most services are blocked. ' +
                'Strategies: Use a local proxy (Psiphon, Lantern, V2RayN, Tor) as Layer 1, ' +
                'then <strong>cascade</strong> your destination proxy on top. ' +
                'Or find a <strong>LAN relay</strong> with internet: <code>python lab-scanner.py --scan-lan</code>. ' +
                'WARP may also work if stacked on top of the local proxy.');
        } else {
            showResultHTML('diagAdvice', 'error',
                '<strong>No direct internet detected.</strong> ' +
                'Strategies: 1) Install Psiphon/Lantern/Tor as Layer 1, then cascade. ' +
                '2) Find a LAN machine with internet: <code>python lab-scanner.py --scan-lan</code>. ' +
                '3) Ask your network admin for proxy settings. ' +
                '4) Run <code>python lab-scanner.py --auto-chain</code> for automatic path discovery (tries 6 strategies).');
        }
    }
}
