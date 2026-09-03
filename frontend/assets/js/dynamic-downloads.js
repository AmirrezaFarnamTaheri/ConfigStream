// Dynamic Downloads Handler - Fixed Version
function initDynamicDownloads() {
    const dropdown = document.getElementById('client-selector-dropdown') ||
                     document.getElementById('client-selector');
    const desc = document.getElementById('client-desc');
    const btn = document.getElementById('dynamic-copy-btn');
    const iconContainer = document.getElementById('dynamic-icon');
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
            desc: "Sing-box JSON config (V2rayN, NekoRay, NekoBox, Hiddify).",
            file: "singbox.json",
            dnsFile: "singbox-dns-safe.json",
            dnsHardenedFile: "singbox-dns-hardened.json",
            icon: "shield"
        },
        singboxvpn: {
            descKey: "downloads.client.singboxvpn.desc",
            desc: "Sing-box TUN/VPN mode (full device tunneling).",
            file: "singbox-vpn.json",
            dnsFile: "singbox-vpn-dns-safe.json",
            dnsHardenedFile: "singbox-vpn-dns-hardened.json",
            icon: "lock"
        },
        clash: {
            descKey: "downloads.client.clash.desc",
            desc: "Clash YAML config (Clash Meta, Mihomo, Stash).",
            file: "clash.yaml",
            dnsFile: "clash-dns-safe.yaml",
            dnsHardenedFile: "clash-dns-hardened.yaml",
            icon: "layers"
        },
        base64: {
            descKey: "downloads.client.base64.desc",
            desc: "Base64-encoded subscription (universal format).",
            file: "base64.txt",
            dnsFile: "base64-dns-safe.txt",
            dnsHardenedFile: "base64-dns-hardened.txt",
            icon: "file-text"
        },
        plaintext: {
            descKey: "downloads.client.plaintext.desc",
            desc: "Plain text proxy URI list (one per line).",
            file: "proxies.txt",
            dnsFile: "proxies-dns-safe.txt",
            dnsHardenedFile: "proxies-dns-hardened.txt",
            icon: "list"
        },
        shadowrocket: {
            descKey: "downloads.client.shadowrocket.desc",
            desc: "Configuration format optimized for Shadowrocket on iOS.",
            file: "shadowrocket.txt",
            dnsFile: "shadowrocket-dns-safe.txt",
            dnsHardenedFile: "shadowrocket-dns-hardened.txt",
            icon: "send"
        },
        surge: {
            descKey: "downloads.client.surge.desc",
            desc: "Powerful rule-based utility for iOS/macOS.",
            file: "surge.conf",
            dnsFile: "surge-dns-safe.conf",
            dnsHardenedFile: "surge-dns-hardened.conf",
            icon: "zap"
        },
        loon: {
            descKey: "downloads.client.loon.desc",
            desc: "Lightweight network toolbox for iOS.",
            file: "loon.conf",
            dnsFile: "loon-dns-safe.conf",
            dnsHardenedFile: "loon-dns-hardened.conf",
            icon: "moon"
        },
        quantumultx: {
            descKey: "downloads.client.quantumultx.desc",
            desc: "Advanced network debugging tool.",
            file: "quantumult.conf",
            dnsFile: "quantumult-dns-safe.conf",
            dnsHardenedFile: "quantumult-dns-hardened.conf",
            icon: "box"
        },
        sip008: {
            descKey: "downloads.client.sip008.desc",
            desc: "Standard SIP008 JSON format for Shadowsocks.",
            file: "sip008.json",
            dnsFile: "sip008-dns-safe.json",
            dnsHardenedFile: "sip008-dns-hardened.json",
            icon: "code"
        },
        chains: {
            descKey: "downloads.client.chains.desc",
            desc: "WARP-shielded chain configs (Gold/Revived proxies, sing-box format).",
            file: "singbox-chains.json",
            dnsFile: "singbox-chains-dns-safe.json",
            dnsHardenedFile: "singbox-chains-dns-hardened.json",
            icon: "link-2"
        },
        sideproducts: {
            descKey: "downloads.client.sideproducts.desc",
            desc: "ZIP archive with WireGuard .conf, OpenVPN .ovpn, and plain URI list.",
            file: "side_products.zip",
            dnsFile: "side_products-dns-safe.zip",
            dnsHardenedFile: "side_products-dns-hardened.zip",
            icon: "package"
        }
    };

    const evasionModeSelector = document.getElementById('evasion-mode-selector');
    
    const dnsProfile = () => {
        if (window.getDnsProfile) {
            return window.getDnsProfile();
        }
        if (profileSelector && profileSelector.value) {
            return profileSelector.value;
        }
        return dnsToggle && dnsToggle.checked ? 'dns-safe' : 'standard';
    };
    
    const evasionMode = () => {
        if (evasionModeSelector && evasionModeSelector.value) {
            return evasionModeSelector.value;
        }
        return 'standard';
    };

    const updateUI = (clientKey) => {
        const client = clients[clientKey];
        if (!client) {
            console.warn('Unknown client:', clientKey);
            return;
        }

        if (window.i18n && typeof window.i18n.t === 'function' && client.descKey) {
            desc.textContent = window.i18n.t(client.descKey) || client.desc;
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
        btn.dataset.file = target;

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

    dropdown.addEventListener('change', (e) => updateUI(e.target.value));
    if (profileSelector) {
        profileSelector.addEventListener('change', () => updateUI(dropdown.value || 'singbox'));
    }
    if (dnsToggle) {
        dnsToggle.addEventListener('change', () => updateUI(dropdown.value || 'singbox'));
    }
    if (evasionModeSelector) {
        evasionModeSelector.addEventListener('change', () => updateUI(dropdown.value || 'singbox'));
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
