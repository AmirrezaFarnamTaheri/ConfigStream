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
    const el = document.getElementById(elId);
    if (!el) return;
    el.className = 'lab-test-result ' + type;
    
    // SECURITY FIX (#490): Use DOMPurify instead of hand-rolled regex.
    // Allow only safe tags: <strong>, <code>, <br>, <a> with restricted attributes.
    el.replaceChildren();
    if (window.DOMPurify) {
        const fragment = window.DOMPurify.sanitize(String(html), {
            RETURN_DOM_FRAGMENT: true,
            ALLOWED_TAGS: ['strong', 'code', 'br', 'a'],
            ALLOWED_ATTR: ['href', 'target', 'rel'],
            ALLOW_DATA_ATTR: false,
        });
        // Enforce safe link attributes on all <a> elements
        if (fragment && fragment.querySelectorAll) {
            fragment.querySelectorAll('a').forEach(a => {
                const href = a.getAttribute('href') || '';
                if (/^javascript:/i.test(href.replace(/[\u0000-\u0020]/g, ''))) {
                    a.removeAttribute('href');
                }
                a.target = '_blank';
                a.rel = 'noopener';
            });
        }
        el.appendChild(fragment);
    } else {
        // Fallback: DOMPurify unavailable — render as safe text only
        el.textContent = String(html).replace(/<br>/gi, '\n');
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
