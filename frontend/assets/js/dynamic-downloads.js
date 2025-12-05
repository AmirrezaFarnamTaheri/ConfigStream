function initDynamicDownloads() {
    const dropdown = document.getElementById('client-selector-dropdown');
    const desc = document.getElementById('client-desc');
    const btn = document.getElementById('dynamic-copy-btn');
    const iconContainer = document.getElementById('dynamic-icon');

    if (!dropdown || !desc || !btn || !iconContainer) return;

    const clients = {
        shadowrocket: {
            desc: "Configuration format optimized for Shadowrocket on iOS.",
            file: "subscribe/shadowrocket",
            icon: "file-text"
        },
        surge: {
            desc: "Powerful rule-based utility.",
            file: "subscribe/surge",
            icon: "zap"
        },
        loon: {
            desc: "Lightweight network toolbox.",
            file: "subscribe/loon",
            icon: "smartphone"
        },
        quantumultx: {
            desc: "Advanced network tool.",
            file: "subscribe/quantumultx",
            icon: "box"
        },
        sip008: {
            desc: "Standard format.",
            file: "subscribe/sip008",
            icon: "code"
        }
    };

    const updateUI = (clientKey) => {
        const client = clients[clientKey];
        if (client) {
            desc.textContent = client.desc;
            btn.dataset.file = client.file;
            iconContainer.innerHTML = `<i data-feather="${client.icon}"></i>`;
            if (window.feather) feather.replace();
            if (window.inlineIcons) window.inlineIcons.replace();
        }
    };

    dropdown.addEventListener('change', (e) => {
        updateUI(e.target.value);
    });

    // Initialize with default
    updateUI(dropdown.value);
}
