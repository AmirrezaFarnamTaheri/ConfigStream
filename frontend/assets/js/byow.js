// frontend/assets/js/byow.js

async function applyBYOW() {
    const workerUrlInput = document.getElementById('worker-url');
    // Sanitize and validate
    const rawUrl = workerUrlInput.value.trim();

    // 1. Strict URL Validation
    // Protocol must be https://
    if (!rawUrl.startsWith('https://')) {
        alert("Security Error: Worker URL must start with https://");
        return;
    }

    // Use URL object for robust parsing
    let urlObj;
    try {
        urlObj = new URL(rawUrl);
    } catch (e) {
        alert("Invalid URL format.");
        return;
    }

    const hostname = urlObj.hostname;

    // 2. Allowlist Check (Optional but recommended)
    // We allow workers.dev, pages.dev, and custom domains if explicitly trusted by user context
    // For now, we enforce HTTPS and valid hostname structure to prevent XSS/injection in config.
    // Audit: Restrict BYOW to fetch from a whitelist of domains (e.g., worker.cloudflare.com) if possible.
    // Since users bring their OWN worker, we can't strict whitelist everything, but we can enforce HTTPS.

    // Strict hostname validation (dots, hyphens, alphanumeric)
    const hostnameRegex = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
    if (!hostnameRegex.test(hostname)) {
        alert("Invalid Hostname.");
        return;
    }

    // 3. Fetch Base Configuration
    let config;
    try {
        // [FIX] Use root-relative path with proper fallback handling
        const basePath = (window.ROOT_PATH || './').replace(/\/$/, '') + '/';

        // Try fetching from base path first, then fallback to current directory
        let response;
        try {
            response = await fetch(basePath + 'singbox.json');
        } catch (fetchErr) {
            console.warn('BYOW: Primary fetch failed, trying fallback path');
            response = await fetch('./singbox.json');
        }

        if (!response.ok) {
            throw new Error(`Failed to fetch base config: ${response.status} ${response.statusText}`);
        }
        config = await response.json();

        // 4. Validate Base Config Schema
        if (!config || typeof config !== 'object' || !Array.isArray(config.outbounds)) {
             throw new Error("Invalid base configuration format.");
        }
    } catch (e) {
        console.error("BYOW Init Failed:", e);
        alert(`Error initializing BYOW: ${e.message}. Please try refreshing the page.`);
        return;
    }

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

    const userWorker = {
        "type": "vless",
        "tag": "🚀 My Private Worker",
        "server": hostname,
        "server_port": 443,
        "uuid": workerUuid,
        "tls": {
            "enabled": true,
            "server_name": hostname,
            "utls": { "enabled": true, "fingerprint": "chrome" }
        },
        "transport": {
            "type": "ws",
            "path": urlObj.pathname === '/' ? '/?ed=2048' : urlObj.pathname,
            "headers": { "Host": hostname }
        }
    };

    // Inject into outbounds
    if (!config.outbounds) config.outbounds = [];
    config.outbounds.unshift(userWorker);

    // Add to Auto/Manual Groups
    config.outbounds.forEach(out => {
        if (out.type === 'selector' || out.type === 'urltest' || out.type === 'fallback') {
            if (out.outbounds && Array.isArray(out.outbounds)) {
                out.outbounds.unshift(userWorker.tag);
            }
        }
    });

    // 5. Generate Download Link (Use Blob for client-side generation)
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const btn = document.getElementById('btn-singbox-byow');
    btn.href = url;
    btn.download = "singbox-turbo.json";

    document.getElementById('byow-links').style.display = 'block';
    alert("Turbo Config Generated! Download it below.");
}
