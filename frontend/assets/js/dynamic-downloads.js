// Dynamic Downloads Handler - Fixed Version
function initDynamicDownloads() {
    const dropdown = document.getElementById('client-selector-dropdown') ||
                     document.getElementById('client-selector');
    const desc = document.getElementById('client-desc');
    const btn = document.getElementById('dynamic-copy-btn');
    const iconContainer = document.getElementById('dynamic-icon');

    if (!dropdown || !desc || !btn) {
        // console.warn('Dynamic downloads: Required elements not found');
        // Silent fail as this might run on pages without the download section
        return;
    }

    // Create dynamic icon element next to dropdown if it doesn't exist
    let dynamicClientIcon = document.getElementById('dynamic-client-icon');
    if (!dynamicClientIcon && dropdown.parentElement) {
        dynamicClientIcon = document.createElement('i');
        dynamicClientIcon.id = 'dynamic-client-icon';
        // Insert before the dropdown
        dropdown.parentElement.insertBefore(dynamicClientIcon, dropdown);
    }

    const clients = {
        shadowrocket: {
            desc: "Configuration format optimized for Shadowrocket on iOS.",
            file: "shadowrocket.txt",
            icon: "send"
        },
        surge: {
            desc: "Powerful rule-based utility for iOS/macOS.",
            file: "surge.conf",
            icon: "zap"
        },
        loon: {
            desc: "Lightweight network toolbox for iOS.",
            file: "loon.conf",
            icon: "moon"
        },
        quantumultx: {
            desc: "Advanced network debugging tool.",
            file: "quantumult.conf",
            icon: "box"
        },
        sip008: {
            desc: "Standard SIP008 JSON format for Shadowsocks.",
            file: "sip008.json",
            icon: "code"
        },
        singbox: {
            desc: "Hybrid Go+Python optimized configuration.",
            file: "singbox.json",
            icon: "layers"
        }
    };

    const updateUI = (clientKey) => {
        const client = clients[clientKey];
        if (!client) {
            console.warn('Unknown client:', clientKey);
            return;
        }

        desc.textContent = client.desc;
        btn.dataset.file = client.file;

        // Update main icon container
        if (iconContainer) {
            iconContainer.innerHTML = `<i data-feather="${client.icon}"></i>`;
        }

        // Update dynamic client icon next to dropdown
        if (dynamicClientIcon) {
            dynamicClientIcon.innerHTML = `<i data-feather="${client.icon}"></i>`;
        }

        // Re-render feather icons
        if (window.feather) {
            feather.replace();
        }
    };

    dropdown.addEventListener('change', (e) => updateUI(e.target.value));

    // Initial update
    updateUI(dropdown.value || 'shadowrocket');
}

// Auto-initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDynamicDownloads);
} else {
    initDynamicDownloads();
}
