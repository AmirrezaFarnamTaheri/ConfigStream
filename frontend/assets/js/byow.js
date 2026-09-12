// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * BYOW (Bring Your Own Worker) UI guard.
 *
 * The former browser-side generator rewrote arbitrary VLESS/VMess WebSocket
 * outbounds to a single generic Worker. That transformation could not preserve
 * the original upstream WebSocket/TLS transport and could therefore produce
 * configurations that looked valid but were not transport-equivalent.
 *
 * Keep the deployment link visible for advanced operators, but fail closed in
 * the browser until a transport-preserving generator is implemented.
 */

const BYOW_DISABLED_MESSAGE =
    'Automatic Private Bridge generation is currently disabled. ' +
    'A generic Cloudflare Worker cannot safely preserve arbitrary upstream ' +
    'VLESS/VMess WebSocket transport semantics. Advanced operators may deploy ' +
    'tools/worker.js and configure one compatible raw-TCP upstream manually.';

document.addEventListener('DOMContentLoaded', () => {
    const inputs = [
        document.getElementById('userWorkerUrl'),
        document.getElementById('worker-url'),
        document.getElementById('worker-uuid'),
    ].filter(Boolean);
    const buttons = [
        document.getElementById('generatePrivateBridgeBtn'),
        document.getElementById('apply-byow-btn'),
    ].filter(Boolean);

    inputs.forEach((input) => {
        input.disabled = true;
        input.setAttribute('aria-disabled', 'true');
        input.placeholder = 'Manual BYOW configuration required';
    });

    buttons.forEach((button) => {
        button.disabled = true;
        button.setAttribute('aria-disabled', 'true');
        button.setAttribute('aria-label', 'Manual Bridge Setup Required');
        button.title = BYOW_DISABLED_MESSAGE;
        // i18n.js updates data-i18n nodes after DOMContentLoaded. Remove this
        // legacy key so it cannot restore the old actionable label.
        button.removeAttribute('data-i18n');
        button.replaceChildren();

        const icon = document.createElement('i');
        icon.setAttribute('data-feather', 'shield');
        icon.setAttribute('aria-hidden', 'true');
        const label = document.createElement('span');
        label.textContent = 'Manual Bridge Setup Required';
        button.appendChild(icon);
        button.appendChild(document.createTextNode(' '));
        button.appendChild(label);
    });

    const group = document.querySelector('.byow-input-group, .byow-panel');
    if (group && !document.getElementById('byowSafetyNotice')) {
        const notice = document.createElement('p');
        notice.id = 'byowSafetyNotice';
        notice.setAttribute('role', 'status');
        notice.style.margin = '0.5rem 0 0';
        notice.style.fontSize = '0.85rem';
        notice.textContent = BYOW_DISABLED_MESSAGE;
        group.insertAdjacentElement('afterend', notice);
    }

    // Icon rendering is centralized in inline-icons.js. Do not invoke the
    // vendored Feather global here: its all-document replacement aborts on an
    // icon name outside that older bundle and can escalate an unrelated marker
    // into the application's fatal-error UI.
});

async function applyUserWorker() {
    throw new Error(BYOW_DISABLED_MESSAGE);
}

window.applyUserWorker = applyUserWorker;
