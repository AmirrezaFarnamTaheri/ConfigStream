// ConfigStream Laboratory - UI Logic
// SPDX-License-Identifier: AGPL-3.0-or-later

import { state } from './state.js';
import { $, $$, escapeHtml } from './utils.js';

export function goToStep(step) {
    if (step < 1 || step > state.totalSteps) return;
    state.currentStep = step;

    // Update panels
    $$('.lab-step-panel').forEach((panel, i) => {
        panel.classList.toggle('active', i + 1 === step);
    });

    // Update stepper dots
    $$('.lab-step-dot').forEach((dot) => {
        const s = parseInt(dot.dataset.step);
        dot.classList.remove('active', 'completed');
        if (s === step) dot.classList.add('active');
        else if (s < step) dot.classList.add('completed');
    });

    // Update connector lines
    $$('.lab-step-line').forEach((line, i) => {
        line.classList.toggle('completed', i + 1 < step);
    });

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

export function showResultText(elId, type, text) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.className = 'lab-test-result ' + type;
    el.textContent = text;
    el.style.display = 'block';
}

export function showResultHTML(elId, type, html) {
    // SECURITY: Transitioning from innerHTML to programmatic DOM construction
    const el = document.getElementById(elId);
    if (!el) return;
    el.className = 'lab-test-result ' + type;

    // Simple parser for <strong> and <code> and <br>
    el.replaceChildren();
    const parts = html.split(/(<[^>]+>[^<]+<\/[^>]+>|<br>)/);
    for (const part of parts) {
        if (!part) continue;
        if (part === '<br>') {
            el.appendChild(document.createElement('br'));
        } else if (part.startsWith('<strong>')) {
            const strong = document.createElement('strong');
            strong.textContent = part.replace(/<\/?strong>/g, '');
            el.appendChild(strong);
        } else if (part.startsWith('<code>')) {
            const code = document.createElement('code');
            code.textContent = part.replace(/<\/?code>/g, '');
            el.appendChild(code);
        } else if (part.startsWith('<a')) {
             // Basic link support for trusted links
             const match = part.match(/href="([^"]+)"/);
             const a = document.createElement('a');
             a.href = match ? match[1] : '#';
             a.target = '_blank';
             a.rel = 'noopener';
             a.textContent = part.replace(/<[^>]+>/g, '');
             el.appendChild(a);
        } else {
            el.appendChild(document.createTextNode(part));
        }
    }
    el.style.display = 'block';
}

export function hideResult(elId) {
    const el = document.getElementById(elId);
    if (el) el.style.display = 'none';
}

export function renderGauge(score, total) {
    const gaugeWrap = $('#diagGauge');
    const arc = $('#gaugeArc');
    const label = $('#gaugeScore');
    const caption = $('#gaugeCaption');
    const detail = $('#gaugeDetail');
    if (!gaugeWrap || !arc) return;

    gaugeWrap.style.display = 'flex';
    const pct = Math.round((score / total) * 100);
    const arcLen = 235.6;
    const offset = arcLen - (arcLen * pct / 100);
    arc.style.strokeDasharray = arcLen.toString();
    arc.style.strokeDashoffset = offset.toString();

    let color, captionText, detailText;
    if (pct >= 75) {
        color = '#10b981';
        captionText = 'Minimal Censorship';
        detailText = 'Your network has good access. All strategies work: WARP, Proxy Cascade, Fragment, Worker, or direct.';
    } else if (pct >= 50) {
        color = '#3b82f6';
        captionText = 'Moderate Filtering';
        detailText = 'Some services are blocked. Try WARP, TLS Fragment, or Proxy Cascade through a local tool.';
    } else if (pct >= 25) {
        color = '#f59e0b';
        captionText = 'Heavy Censorship';
        detailText = 'Significant blocking. Try Proxy Cascade, Intranet Relay, Double WARP, or CDN Worker. Run lab-scanner.py --auto-chain.';
    } else {
        color = '#ef4444';
        captionText = 'Severe Restrictions';
        detailText = 'Very little is reachable. Use a local proxy as Layer 1, find a LAN relay (--scan-lan), or download lab-scanner.py for offline scanning.';
    }
    arc.style.stroke = color;
    if (label) { label.textContent = pct + '%'; label.style.color = color; }
    if (caption) { caption.textContent = captionText; caption.style.color = color; }
    if (detail) detail.textContent = detailText;
}

export function renderHealthBadges(results) {
    const container = $('#diagBadges');
    if (!container) return;
    container.style.display = 'flex';
    container.replaceChildren();
    const badges = [
        { key: 'cf', label: 'Cloudflare' },
        { key: 'google', label: 'Google' },
        { key: 'cf_tls', label: 'CF TLS' },
        { key: 'github', label: 'GitHub' },
        { key: 'wikipedia', label: 'Wikipedia' },
        { key: 'doh', label: 'DoH DNS' },
    ];
    for (const b of badges) {
        if (!(b.key in results)) continue;
        const cls = results[b.key] ? 'ok' : 'fail';
        const badge = document.createElement('span');
        badge.className = 'chain-health-badge ' + cls;

        const dot = document.createElement('span');
        dot.className = 'dot';
        badge.appendChild(dot);
        badge.appendChild(document.createTextNode(b.label));

        container.appendChild(badge);
    }
}
