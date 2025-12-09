// frontend/assets/js/wasm_loader.js

const go = new Go(); // Defined in wasm_exec.js
let wasmReady = false;

// 1. Initialize WASM
async function initWasm() {
    try {
        const result = await WebAssembly.instantiateStreaming(
            fetch("assets/wasm/tester.wasm"),
            go.importObject
        );
        go.run(result.instance);
        wasmReady = true;
        console.log("✅ ConfigStream WASM Core Loaded");
    } catch (err) {
        console.error("❌ WASM Load Failed:", err);
    }
}

// 2. Cleanup Function
function cleanup() {
    if (window.cleanupWasm) {
        window.cleanupWasm();
        console.log("🧹 WASM Cleaned up");
    }
}
window.addEventListener('beforeunload', cleanup);

// 3. Test Function
async function verifyProxyBatch(proxies) {
    if (!wasmReady) {
        console.warn("WASM not ready yet.");
        return proxies;
    }

    const CHUNK_SIZE = 10;
    const results = [];

    for (let i = 0; i < proxies.length; i += CHUNK_SIZE) {
        const chunk = proxies.slice(i, i + CHUNK_SIZE);
        const chunkResults = await Promise.all(chunk.map(async (p) => {
            try {
                // Determine if proxy is testable via WebSocket
                let isWebSocket = false;

                // Check transport in details
                if (p.details && (p.details.type === 'ws' || p.details.transport === 'ws')) {
                    isWebSocket = true;
                }

                // Heuristic check
                if (p.config && (p.config.includes('type=ws') || p.config.includes('transport=ws'))) {
                    isWebSocket = true;
                }

                // We can only test WebSocket endpoints from browser
                if (!isWebSocket) {
                     return p;
                }

                let target = p.address || p.server;
                const port = p.port || 443;
                let path = '/';

                if (p.details && p.details.path) path = p.details.path;

                // Construct WSS URL
                const targetUrl = `wss://${target}:${port}${path}`;

                const res = await window.testProxyWasm(targetUrl);

                if (res.alive) {
                    p.latency = res.latency;
                    if (!p.tags) p.tags = [];
                    if (!p.tags.includes("verified-local")) {
                        p.tags.push("verified-local");
                    }
                } else {
                    p.latency = 9999;
                }
            } catch (e) {
                console.warn(`WASM Test Error for ${p.address}:`, e);
                p.latency = 9999;
            }
            return p;
        }));
        results.push(...chunkResults);
    }

    // Re-sort by new local latency
    return results.sort((a, b) => {
        const latA = (a.latency === null || a.latency === undefined) ? 9999 : a.latency;
        const latB = (b.latency === null || b.latency === undefined) ? 9999 : b.latency;
        return latA - latB;
    });
}

// Auto-init on load
initWasm();

// Expose to global scope for proxies.js to use
window.verifyProxyBatch = verifyProxyBatch;
