// frontend/assets/js/byow.js

async function applyBYOW() {
    const workerUrlInput = document.getElementById('worker-url');
    // Sanitize and validate
    const rawUrl = workerUrlInput.value.trim();

    // Allow hostname or full URL, strip protocol
    const cleanUrl = rawUrl.replace(/^https?:\/\//, '').replace(/\/$/, '');

    // Strict hostname validation (dots, hyphens, alphanumeric)
    const hostnameRegex = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;

    if (!cleanUrl || !hostnameRegex.test(cleanUrl.split('/')[0])) {
        alert("Please enter a valid Worker Hostname (e.g., worker.user.workers.dev).");
        return;
    }

    // 1. Fetch the original "Smart" Config
    // We assume singbox.json is available in the same directory
    let config;
    try {
        const response = await fetch('./singbox.json');
        if (!response.ok) {
            // Audit: Retry logic or clearer error
            throw new Error(`Failed to fetch base config: ${response.status}`);
        }
        config = await response.json();

        // Audit: Validate config structure
        if (!config || typeof config !== 'object' || !Array.isArray(config.outbounds)) {
             throw new Error("Invalid base configuration format.");
        }
    } catch (e) {
        console.error("BYOW Init Failed:", e);
        alert(`Error initializing BYOW: ${e.message}. Please try refreshing the page.`);
        return;
    }

    // 2. Define the User's Worker Outbound
    // We use the Worker as a "Chain Exit".
    // REVISED STRATEGY for Sing-box + Worker:
    // Modify the transport of existing proxies to tunnel via the Worker URL (if compatible).
    // Let's assume the Worker acts as a VLESS node itself.
    // We will inject a single "User Worker" outbound and set it as the default for the "Manual" selector.

    const workerUuidInput = document.getElementById('worker-uuid');

    // Generate a random UUID v4 if not provided
    const generateUUID = () => {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    };

    let workerUuid = workerUuidInput && workerUuidInput.value.trim() ? workerUuidInput.value.trim() : generateUUID();

    // Validate UUID format
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(workerUuid)) {
        alert("Invalid UUID format. Using generated UUID.");
        workerUuid = generateUUID();
    }

    // Safe extraction of host
    const workerHost = cleanUrl.split('/')[0];

    const userWorker = {
        "type": "vless",
        "tag": "🚀 My Private Worker",
        "server": workerHost, // Extract host
        "server_port": 443,
        "uuid": workerUuid,
        "tls": {
            "enabled": true,
            "server_name": workerHost,
            "utls": { "enabled": true, "fingerprint": "chrome" } // [FIX] Enforce uTLS
        },
        "transport": {
            "type": "ws",
            "path": "/?ed=2048",
            "headers": { "Host": workerHost } // [FIX] Ensure Host header
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
