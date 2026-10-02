// Dynamic Downloads Handler - Fixed Version
function initDynamicDownloads() {
    const dropdown = document.getElementById('client-selector-dropdown') ||
                     document.getElementById('client-selector');
    const desc = document.getElementById('client-desc');
    const btn = document.getElementById('dynamic-action-btn');
    const iconContainer = document.getElementById('dynamic-icon');
    const actionIconContainer = document.getElementById('dynamic-action-icon');
    const actionLabel = document.getElementById('dynamic-action-label');
    const profileSelector = document.getElementById('dns-profile-selector');
    const dnsToggle = document.getElementById('dns-safe-toggle');

    if (!dropdown || !desc || !btn) {
        // console.warn('Dynamic downloads: Required elements not found');
        // Silent fail as this might run on pages without the download section
        return;
    }

    const clients = {
        singbox: {
            descKey: "downloads.client.singbox.desc",
            desc: "Sing-box JSON subscription. Updating the subscription imports every standalone outbound/endpoint as an independent proxy entry.",
            file: "singbox.json",
            dnsFile: "singbox-dns-safe.json",
            dnsHardenedFile: "singbox-dns-hardened.json",
            icon: "shield",
            action: "node"
        },
        xray: {
            descKey: "downloads.client.xray.desc",
            desc: "Xray JSON subscription. The outbounds-only payload is expanded into independent subscription entries by compatible clients such as v2rayN.",
            file: "xray.json",
            dnsFile: null,
            dnsHardenedFile: null,
            icon: "code",
            action: "node"
        },
        nekobox: {
            descKey: "downloads.client.nekobox.desc",
            desc: "NekoBox multi-node JSON subscription; each standalone outbound/endpoint imports as a separate node.",
            file: "nekobox.json",
            dnsFile: "nekobox-dns-safe.json",
            dnsHardenedFile: "nekobox-dns-hardened.json",
            icon: "server",
            action: "node"
        },
        singboxvpn: {
            descKey: "downloads.client.singboxvpn.desc",
            desc: "Sing-box TUN/VPN mode (full device tunneling).",
            file: "singbox-vpn.json",
            dnsFile: "singbox-vpn-dns-safe.json",
            dnsHardenedFile: "singbox-vpn-dns-hardened.json",
            icon: "lock",
            action: "download"
        },
        clash: {
            descKey: "downloads.client.clash.desc",
            desc: "Clash/Mihomo proxies-only subscription. Updating the URL refreshes the independent proxy list.",
            file: "clash.yaml",
            dnsFile: "clash-dns-safe.yaml",
            dnsHardenedFile: "clash-dns-hardened.yaml",
            icon: "layers",
            action: "node"
        },
        base64: {
            descKey: "downloads.client.base64.desc",
            desc: "Base64-encoded subscription (universal format).",
            file: "base64.txt",
            dnsFile: "base64-dns-safe.txt",
            dnsHardenedFile: "base64-dns-hardened.txt",
            icon: "file-text",
            action: "node"
        },
        plaintext: {
            descKey: "downloads.client.plaintext.desc",
            desc: "Plain text proxy URI list (one per line).",
            file: "proxies.txt",
            dnsFile: "proxies-dns-safe.txt",
            dnsHardenedFile: "proxies-dns-hardened.txt",
            icon: "list",
            action: "node"
        },
        shadowrocket: {
            descKey: "downloads.client.shadowrocket.desc",
            desc: "Configuration format optimized for Shadowrocket on iOS.",
            file: "shadowrocket.txt",
            dnsFile: "shadowrocket-dns-safe.txt",
            dnsHardenedFile: "shadowrocket-dns-hardened.txt",
            icon: "send",
            action: "copy"
        },
        surge: {
            descKey: "downloads.client.surge.desc",
            desc: "Powerful rule-based utility for iOS/macOS.",
            file: "surge.conf",
            dnsFile: "surge-dns-safe.conf",
            dnsHardenedFile: "surge-dns-hardened.conf",
            icon: "zap",
            action: "copy"
        },
        loon: {
            descKey: "downloads.client.loon.desc",
            desc: "Lightweight network toolbox for iOS.",
            file: "loon.conf",
            dnsFile: "loon-dns-safe.conf",
            dnsHardenedFile: "loon-dns-hardened.conf",
            icon: "moon",
            action: "copy"
        },
        quantumultx: {
            descKey: "downloads.client.quantumultx.desc",
            desc: "Advanced network debugging tool.",
            file: "quantumult.conf",
            dnsFile: "quantumult-dns-safe.conf",
            dnsHardenedFile: "quantumult-dns-hardened.conf",
            icon: "box",
            action: "copy"
        },
        sip008: {
            descKey: "downloads.client.sip008.desc",
            desc: "SIP008 Shadowsocks server list. DNS-Hardened falls back to DNS-Safe endpoints because SIP008 cannot encode resolver policy.",
            file: "sip008.json",
            dnsFile: "sip008-dns-safe.json",
            dnsHardenedFile: null,
            icon: "code",
            action: "copy"
        },
        chains: {
            descKey: "downloads.client.chains.desc",
            desc: "WARP-shielded chain configs (Gold/Revived proxies, sing-box format).",
            file: "singbox-chains.json",
            dnsFile: "singbox-chains-dns-safe.json",
            dnsHardenedFile: "singbox-chains-dns-hardened.json",
            icon: "link-2",
            action: "download"
        },
        sideproducts: {
            descKey: "downloads.client.sideproducts.desc",
            desc: "ZIP archive with WireGuard .conf, OpenVPN .ovpn, and plain URI list.",
            file: "side_products.zip",
            dnsFile: "side_products-dns-safe.zip",
            dnsHardenedFile: "side_products-dns-hardened.zip",
            icon: "package",
            action: "download"
        }
    };
    
    const dnsProfile = () => {
        if (window.getDnsProfile) {
            return window.getDnsProfile();
        }
        if (profileSelector && profileSelector.value) {
            return profileSelector.value;
        }
        return dnsToggle && dnsToggle.checked ? 'dns-safe' : 'standard';
    };

    const updateUI = (clientKey) => {
        const client = clients[clientKey];
        if (!client) {
            console.warn('Unknown client:', clientKey);
            return;
        }

        if (window.i18n && typeof window.i18n.t === 'function' && client.descKey) {
            const translated = window.i18n.t(client.descKey);
            desc.textContent = translated && translated !== client.descKey
                ? translated
                : client.desc;
        } else {
            desc.textContent = client.desc;
        }
        const profile = dnsProfile();
        let target = client.file;
        if (profile === 'dns-hardened') {
            if (client.dnsHardenedFile) {
                target = client.dnsHardenedFile;
            } else if (client.dnsFile) {
                target = client.dnsFile;
            }
        } else if (profile === 'dns-safe' && client.dnsFile) {
            target = client.dnsFile;
        }
        btn.dataset.baseFile = client.file;
        if (client.dnsFile) {
            btn.dataset.dnsFile = client.dnsFile;
        } else {
            delete btn.dataset.dnsFile;
        }
        if (client.dnsHardenedFile) {
            btn.dataset.dnsHardenedFile = client.dnsHardenedFile;
        } else {
            delete btn.dataset.dnsHardenedFile;
        }
        btn.dataset.file = target;

        const isDownload = client.action === "download";
        const isNodeSubscription = client.action === "node";
        btn.dataset.action = isDownload ? "download" : "copy";
        btn.classList.toggle('copy-btn', !isDownload);

        const actionKey = isDownload
            ? "downloads.download"
            : isNodeSubscription
                ? "downloads.copyNodeSubscription"
                : "table.copy";
        const fallbackAction = isDownload
            ? "Download"
            : isNodeSubscription
                ? "Copy Node Subscription URL"
                : "Copy Link";
        if (actionLabel) {
            actionLabel.dataset.i18n = actionKey;
            const translated = window.i18n && typeof window.i18n.t === 'function'
                ? window.i18n.t(actionKey)
                : null;
            actionLabel.textContent = translated && translated !== actionKey ? translated : fallbackAction;
        }
        btn.setAttribute(
            'aria-label',
            isDownload ? `Download ${target}` : `Copy link for ${target}`,
        );
        if (actionIconContainer) {
            actionIconContainer.textContent = '';
            const actionIcon = document.createElement('i');
            actionIcon.setAttribute('data-feather', isDownload ? 'download-cloud' : 'copy');
            actionIconContainer.appendChild(actionIcon);
        }

        // Update main icon container
        if (iconContainer) {
            iconContainer.textContent = '';
            const icon = document.createElement('i');
            icon.setAttribute('data-feather', client.icon);
            iconContainer.appendChild(icon);
        }

        // Use the local icon renderer when it is ready.  Calling the legacy
        // Feather global scans every icon element on the page and throws
        // if any optional icon is unavailable, which must not break downloads.
        if (window.inlineIcons && typeof window.inlineIcons.replace === 'function') {
            window.inlineIcons.replace();
        }
    };

    btn.addEventListener('click', () => {
        if (btn.dataset.action !== 'download') return;
        const target = btn.dataset.file;
        if (!target) return;

        // Route full-config/archive downloads through the same manifest-verified
        // <a download> path used by the static download controls.
        const anchor = document.createElement('a');
        anchor.href = target;
        anchor.download = target.split('/').pop();
        anchor.dataset.file = target;
        anchor.hidden = true;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
    });

    dropdown.addEventListener('change', (e) => updateUI(e.target.value));
    if (profileSelector) {
        profileSelector.addEventListener('change', () => updateUI(dropdown.value || 'singbox'));
    }
    if (dnsToggle) {
        dnsToggle.addEventListener('change', () => updateUI(dropdown.value || 'singbox'));
    }
    window.addEventListener('languageChanged', () => updateUI(dropdown.value || 'singbox'));

    // Initial update
    updateUI(dropdown.value || 'singbox');

    window.updateDynamicDownloads = () => updateUI(dropdown.value || 'singbox');
}

// Auto-initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDynamicDownloads);
} else {
    initDynamicDownloads();
}
