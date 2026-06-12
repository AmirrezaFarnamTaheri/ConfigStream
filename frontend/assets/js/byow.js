// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * BYOW (Bring Your Own Worker) - Platinum Upgrade
 * Allows users to inject their own Cloudflare Worker URL into Gold configs
 */

document.addEventListener('DOMContentLoaded', () => {
    const upgradeBtn = document.getElementById('upgradePlatinumBtn');
    if (upgradeBtn) {
        upgradeBtn.addEventListener('click', applyUserWorker);
    }
});

/**
 * Apply user's Worker URL to Gold/Shielded configs
 * Fetches singbox-chains.json, modifies VLESS/VMess outbounds to use user's worker, and downloads
 */
async function applyUserWorker() {
    const userUrlRaw = document.getElementById('userWorkerUrl')?.value.trim();
    if (!userUrlRaw) {
        alert("⚠️ Please enter your Worker URL!");
        return;
    }

    // Clean the URL (remove https:// and trailing /)
    let workerHost = userUrlRaw.replace(/^https?:\/\//, '').replace(/\/$/, '');

    // Validate it looks like a workers.dev domain
    if (!workerHost.includes('.workers.dev')) {
        if (!confirm(`⚠️ "${workerHost}" doesn't look like a Cloudflare Workers URL.\n\nExpected format: your-worker.username.workers.dev\n\nContinue anyway?`)) {
            return;
        }
    }

    const button = document.getElementById('upgradePlatinumBtn');

    try {
        // Show loading state
        if (button) {
            button.disabled = true;
            button.replaceChildren();

            const icon = document.createElement('i');
            icon.setAttribute('data-feather', 'loader');

            const span = document.createElement('span');
            span.textContent = 'Processing...';

            button.appendChild(icon);
            button.appendChild(document.createTextNode(' '));
            button.appendChild(span);

            if (window.feather) window.feather.replace();
        }

        // Fetch the Gold chains config
        const root = window.ROOT_PATH || '';
        const chainsUrl = root + 'singbox-chains.json';
        const response = await fetch(chainsUrl);
        if (!response.ok) {
            throw new Error(`Failed to fetch ${chainsUrl}: ${response.status}`);
        }

        const chainsConfig = await response.json();

        // Deep copy to avoid mutating original
        let modifiedConfig = JSON.parse(JSON.stringify(chainsConfig));

        // The Surgery: Replace the Bridge Address in VLESS/VMess outbounds
        let modifiedCount = 0;

        if (modifiedConfig.outbounds && Array.isArray(modifiedConfig.outbounds)) {
            modifiedConfig.outbounds.forEach(outbound => {
                // Look for VLESS/VMess outbounds with WebSocket transport (these are the bridges)
                if ((outbound.type === "vless" || outbound.type === "vmess") &&
                    outbound.transport &&
                    outbound.transport.type === "ws") {

                    // Update the server to point to user's worker
                    // Keep the IP as a clean Cloudflare IP (or use worker hostname)
                    // The key is updating TLS server_name and WebSocket Host header

                    // Option 1: Use worker hostname directly (if Cloudflare allows)
                    // outbound.server = workerHost;
                    // outbound.server_port = 443;

                    // Option 2: Use a clean Cloudflare IP and set SNI/Host to worker domain
                    // This is more reliable as it avoids DNS resolution issues
                    if (!outbound.server || outbound.server === '127.0.0.1') {
                        // Use a known Cloudflare IP (104.16.x.x range)
                        outbound.server = "104.16.20.10"; // Clean Cloudflare IP
                    }
                    outbound.server_port = 443;

                    // CRITICAL: Set TLS server_name to worker domain
                    if (outbound.tls) {
                        outbound.tls.server_name = workerHost;
                    } else {
                        outbound.tls = { server_name: workerHost };
                    }

                    // CRITICAL: Set WebSocket Host header to worker domain
                    if (outbound.transport.headers) {
                        outbound.transport.headers.Host = workerHost;
                    } else {
                        outbound.transport.headers = { Host: workerHost };
                    }

                    // Update WebSocket path if needed (ensure it matches worker's PROXY_PATH)
                    if (!outbound.transport.path || !outbound.transport.path.includes('/my-secret-tunnel')) {
                        outbound.transport.path = '/my-secret-tunnel';
                    }

                    modifiedCount++;
                }
            });
        }

        if (modifiedCount === 0) {
            alert("⚠️ No VLESS/VMess WebSocket outbounds found in the config.\n\nMake sure you're using the Gold/Shielded chains config (singbox-chains.json).");
            if (button) {
                button.disabled = false;
                button.replaceChildren();

                const icon = document.createElement('i');
                icon.setAttribute('data-feather', 'zap');

                const span = document.createElement('span');
                span.textContent = 'Upgrade to Platinum';

                button.appendChild(icon);
                button.appendChild(document.createTextNode(' '));
                button.appendChild(span);

                if (window.feather) window.feather.replace();
            }
            return;
        }

        // Save and Export
        const blob = new Blob([JSON.stringify(modifiedConfig, null, 2)], {type: "application/json"});
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = "platinum-configstream.json";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);

        alert(`✨ Successfully upgraded ${modifiedCount} connection(s) to your Private Bridge!\n\n📥 The config has been downloaded as "platinum-configstream.json".\n\n📋 Next steps:\n1. Import it as a Subscription in Nekobox/Sing-box\n2. Select a GOLD- prefixed proxy\n3. Enjoy your private, unlimited connection!`);

    } catch (error) {
        console.error('BYOW upgrade failed:', error);
        alert(`❌ Failed to upgrade config: ${error.message}\n\nPlease check:\n- Your Worker URL is correct\n- The singbox-chains.json file is accessible\n- Your browser console for details`);
    } finally {
        // Restore button state
        if (button) {
            button.disabled = false;
            button.replaceChildren();

            const icon = document.createElement('i');
            icon.setAttribute('data-feather', 'zap');

            const span = document.createElement('span');
            span.textContent = 'Upgrade to Platinum';

            button.appendChild(icon);
            button.appendChild(document.createTextNode(' '));
            button.appendChild(span);

            if (window.feather) window.feather.replace();
        }
    }
}

// Expose globally
window.applyUserWorker = applyUserWorker;
