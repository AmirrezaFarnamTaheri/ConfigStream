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

// 2. Test Function
async function verifyProxyBatch(proxies) {
    if (!wasmReady) {
        console.warn("WASM not ready yet.");
        return proxies;
    }

    console.log(`🚀 Starting WASM Verification for ${proxies.length} nodes...`);

    // Run tests in parallel (Browser limit usually ~6-10 concurrent requests)
    // We chunk them to avoid overwhelming the browser
    const CHUNK_SIZE = 10;
    const results = [];

    for (let i = 0; i < proxies.length; i += CHUNK_SIZE) {
        const chunk = proxies.slice(i, i + CHUNK_SIZE);
        const chunkResults = await Promise.all(chunk.map(async (p) => {
            try {
                // Call the Go function exported in Task 8
                // Note: The Go function expects a string argument.
                // We pass the server address or the full config URL if supported.
                // Our simple implementation takes a URL string to HEAD.
                // We'll try the server address (as http) or generate_204 via proxy?
                // The Go code does `client.Head(proxyURL)`.
                // If `p.server` is just an IP, we might need `http://${p.server}`.

                let target = p.server;
                if (!target.startsWith('http')) target = `http://${target}`;

                const res = await window.testProxyWasm(target);
                if (res.alive) {
                    p.latency = res.latency;
                    if (!p.tags) p.tags = [];
                    p.tags.push("verified-local");
                } else {
                    p.latency = 9999;
                }
            } catch (e) {
                p.latency = 9999;
            }
            return p;
        }));
        results.push(...chunkResults);
    }

    // Re-sort by new local latency
    return results.sort((a, b) => (a.latency || 9999) - (b.latency || 9999));
}

// Auto-init on load
initWasm();

// Expose to global scope for proxies.js to use
window.verifyProxyBatch = verifyProxyBatch;
