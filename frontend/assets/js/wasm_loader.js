// WASM Loader for Client-Side Proxy Testing
// Zero-Cost distributed testing using user browsers

const go = new Go();
let wasmLoaded = false;

async function loadWasm() {
    if (wasmLoaded) return;

    try {
        const result = await WebAssembly.instantiateStreaming(
            fetch('assets/wasm/tester.wasm'),
            go.importObject
        );
        go.run(result.instance);
        wasmLoaded = true;
        console.log("ConfigStream WASM Tester Loaded");
    } catch (err) {
        console.warn("WASM Tester failed to load:", err);
        console.log("Falling back to static data.");
    }
}

// Exposed API for the frontend to check a proxy
window.testProxy = async (proxyConfig) => {
    if (!wasmLoaded) return { success: false, error: "WASM not loaded" };

    // This function 'checkProxy' must be exported by the Go WASM code
    // For now, this is a placeholder for the interface
    if (window.checkProxy) {
        return await window.checkProxy(proxyConfig);
    }
    return { success: false, error: "Function not exported" };
};

// Auto-load on idle
requestIdleCallback(() => loadWasm());
