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
        shadowrocket: {
            descKey: "downloads.client.shadowrocket.desc",
            desc: "Configuration format optimized for Shadowrocket on iOS.",
            file: "shadowrocket.txt",
            dnsFile: "shadowrocket-dns-safe.txt",
            icon: "send"
        },
        surge: {
            descKey: "downloads.client.surge.desc",
            desc: "Powerful rule-based utility for iOS/macOS.",
            file: "surge.conf",
            dnsFile: "surge-dns-safe.conf",
            icon: "zap"
        },
        loon: {
            descKey: "downloads.client.loon.desc",
            desc: "Lightweight network toolbox for iOS.",
            file: "loon.conf",
            dnsFile: "loon-dns-safe.conf",
            icon: "moon"
        },
        quantumultx: {
            descKey: "downloads.client.quantumultx.desc",
            desc: "Advanced network debugging tool.",
            file: "quantumult.conf",
            dnsFile: "quantumult-dns-safe.conf",
            icon: "box"
        },
        sip008: {
            descKey: "downloads.client.sip008.desc",
            desc: "Standard SIP008 JSON format for Shadowsocks.",
            file: "sip008.json",
            dnsFile: "sip008-dns-safe.json",
            icon: "code"
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
            iconContainer.innerHTML = `<i data-feather="${client.icon}"></i>`;
        }

        // Re-render feather icons
        if (window.feather) {
            feather.replace();
        }
    };

    dropdown.addEventListener('change', (e) => updateUI(e.target.value));
    if (profileSelector) {
        profileSelector.addEventListener('change', () => updateUI(dropdown.value || 'shadowrocket'));
    }
    if (dnsToggle) {
        dnsToggle.addEventListener('change', () => updateUI(dropdown.value || 'shadowrocket'));
    }
    window.addEventListener('languageChanged', () => updateUI(dropdown.value || 'shadowrocket'));

    // Initial update
    updateUI(dropdown.value || 'shadowrocket');

    window.updateDynamicDownloads = () => updateUI(dropdown.value || 'shadowrocket');
}

// Auto-initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDynamicDownloads);
} else {
    initDynamicDownloads();
}
