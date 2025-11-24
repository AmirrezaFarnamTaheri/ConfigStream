// frontend/assets/js/byow.js

async function applyBYOW() {
    const workerUrlInput = document.getElementById('worker-url');
    const workerUrl = workerUrlInput.value.trim();
    if (!workerUrl) {
        alert("Please enter a valid Worker URL.");
        return;
    }

    // 1. Fetch the original "Smart" Config
    // We assume singbox.json is available in the same directory
    let config;
    try {
        const response = await fetch('./singbox.json');
        if (!response.ok) throw new Error("Failed to fetch singbox.json");
        config = await response.json();
    } catch (e) {
        console.error(e);
        alert("Could not load base config to modify.");
        return;
    }

    // 2. Define the User's Worker Outbound
    // We use the Worker as a "Chain Exit".
    // REVISED STRATEGY for Sing-box + Worker:
    // Modify the transport of existing proxies to tunnel via the Worker URL (if compatible).
    // Let's assume the Worker acts as a VLESS node itself.
    // We will inject a single "User Worker" outbound and set it as the default for the "Manual" selector.

    const cleanUrl = workerUrl.replace('https://', '').replace('http://', '').replace(/\/$/, '');
    const userWorker = {
        "type": "vless",
        "tag": "🚀 My Private Worker",
        "server": cleanUrl.split('/')[0], // Extract host
        "server_port": 443,
        "uuid": "uuid-placeholder", // Ideally this should be input by user too, but VLESS workers often use a static one or ignore it
        "tls": { "enabled": true },
        "transport": {
            "type": "ws",
            "path": "/?ed=2048"
        }
    };

    // Inject into outbounds
    if (!config.outbounds) config.outbounds = [];
    config.outbounds.unshift(userWorker);

    // Add to Auto/Manual Groups
    // Find the selectors and append "🚀 My Private Worker" to them
    config.outbounds.forEach(out => {
        if (out.type === 'selector' || out.type === 'urltest' || out.type === 'fallback') {
            if (out.outbounds && Array.isArray(out.outbounds)) {
                out.outbounds.unshift(userWorker.tag);
            }
        }
    });

    // 3. Generate Download Link
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const btn = document.getElementById('btn-singbox-byow');
    btn.href = url;
    btn.download = "singbox-turbo.json";

    document.getElementById('byow-links').style.display = 'block';
    alert("Turbo Config Generated! Download it below.");
}
