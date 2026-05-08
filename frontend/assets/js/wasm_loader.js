// frontend/assets/js/wasm_loader.js

// Guard against missing Go runtime (in case wasm_exec.js failed to load)
let go = null;
let wasmReady = false;
let wasmError = null;
const WASM_SCOPE_LABEL = 'Browser-limited reachability check';

// 1. Initialize WASM
async function initWasm() {
    try {
        // Check if Go runtime is available
        if (typeof Go === 'undefined') {
            throw new Error('Go runtime (wasm_exec.js) not loaded');
        }

        go = new Go();

        if (!WebAssembly.instantiateStreaming) {
            // Polyfill for Safari/Old Browsers
            WebAssembly.instantiateStreaming = async (resp, importObject) => {
                const source = await (await resp).arrayBuffer();
                return await WebAssembly.instantiate(source, importObject);
            };
        }

        // Use correct path resolution with ROOT_PATH
        const wasmPath = (window.ROOT_PATH || './') + 'assets/wasm/tester.wasm';

        const result = await WebAssembly.instantiateStreaming(
            fetch(wasmPath),
            go.importObject
        );
        go.run(result.instance);
        wasmReady = true;

        // Signal WASM is ready
        window.wasmReady = true;
        document.dispatchEvent(new Event('wasm-ready'));
        if (window.ConfigStreamLogger) {
            window.ConfigStreamLogger.info(`${WASM_SCOPE_LABEL} loaded`);
        }
    } catch (err) {
        if (window.ConfigStreamLogger) {
            window.ConfigStreamLogger.error(`${WASM_SCOPE_LABEL} failed to load:`, err);
        } else {
            console.error(`${WASM_SCOPE_LABEL} failed to load:`, err);
        }
        wasmError = err;
        // Set wasmReady to false explicitly and expose error
        window.wasmReady = false;
        window.wasmError = err.message;
        // Dispatch event even on failure so app doesn't hang
        document.dispatchEvent(new Event('wasm-ready'));
    }
}

// 2. Cleanup Function
function cleanup() {
    if (window.cleanupWasm) {
        window.cleanupWasm();
        if (window.ConfigStreamLogger) {
            window.ConfigStreamLogger.info(`${WASM_SCOPE_LABEL} cleaned up`);
        }
    }
}
window.addEventListener('beforeunload', cleanup);

// 3. Test Function
async function verifyProxyBatch(proxies) {
    // Better error handling for WASM unavailability
    if (!wasmReady || !window.wasmReady) {
        if (window.ConfigStreamLogger) window.ConfigStreamLogger.warn(`${WASM_SCOPE_LABEL} not ready - keeping sidecar/Python results`);
        return proxies;
    }

    // Check if testProxyWasm function is available
    if (typeof window.testProxyWasm !== 'function') {
        if (window.ConfigStreamLogger) window.ConfigStreamLogger.warn(`${WASM_SCOPE_LABEL} function unavailable - keeping sidecar/Python results`);
        return proxies;
    }

    const CHUNK_SIZE = 10;
    const results = [];

    for (let i = 0; i < proxies.length; i += CHUNK_SIZE) {
        const chunk = proxies.slice(i, i + CHUNK_SIZE);
        const chunkResults = await Promise.all(chunk.map(async (p) => {
            try {
                // Browsers cannot perform native proxy handshakes; this only checks WebSocket reachability.
                let isWebSocket = false;

                // Check transport in details
                if (p.details && (p.details.type === 'ws' || p.details.transport === 'ws')) {
                    isWebSocket = true;
                }

                // Heuristic check
                if (p.config && (p.config.includes('type=ws') || p.config.includes('transport=ws'))) {
                    isWebSocket = true;
                }

                // We can only attempt WebSocket reachability from the browser.
                if (!isWebSocket) {
                     if (!p.tags) p.tags = [];
                     if (!p.tags.includes("browser-check-unsupported")) {
                         p.tags.push("browser-check-unsupported");
                     }
                     return p;
                }

                let target = p.address || p.server;
                const port = p.port || 443;
                let path = '/';

                if (p.details && p.details.path) path = p.details.path;

                // Construct WSS URL
                const targetUrl = `wss://${target}:${port}${path}`;

                const res = await window.testProxyWasm(targetUrl);

                if (res && res.alive) {
                    p.latency = res.latency;
                    if (!p.tags) p.tags = [];
                    if (!p.tags.includes("verified-local")) {
                        p.tags.push("verified-local");
                    }
                    if (!p.tags.includes("browser-limited")) {
                        p.tags.push("browser-limited");
                    }
                } else {
                    // Only override latency if proxy doesn't already have one
                    if (p.latency === null || p.latency === undefined) {
                        p.latency = 9999;
                    }
                }
            } catch (e) {
                console.warn(`WASM Test Error for ${p.address}:`, e);
                // Don't override latency on error - keep server-side value
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
