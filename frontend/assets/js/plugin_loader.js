class WasmPlugin {
    constructor(name, instance) {
        this.name = name;
        this.instance = instance;
        this.memory = instance.exports.memory;
        this.alloc = instance.exports.alloc;
        this.parseFunc = instance.exports.parse;
        this.dealloc = instance.exports.dealloc;
        this.freeString = instance.exports.free_string;
    }

    parse(config) {
        let ptr = 0;
        let resultPtr = 0;
        try {
            const encoder = new TextEncoder();
            const configBytes = encoder.encode(config);
            const len = configBytes.length;

            if (!this.alloc || !this.parseFunc) {
                console.warn(`Plugin ${this.name} missing exports`);
                return null;
            }

            ptr = this.alloc(len);
            const memView = new Uint8Array(this.memory.buffer);
            memView.set(configBytes, ptr);

            resultPtr = this.parseFunc(ptr, len);

            // Deallocate input if possible
            if (this.dealloc) {
                this.dealloc(ptr, len);
                ptr = 0;
            }

            if (resultPtr === 0) return null;

            // Read result string (null terminated)
            let end = resultPtr;

            // Audit: Validate pointer within bounds
            if (resultPtr >= this.memory.buffer.byteLength) {
                console.error("Plugin returned out-of-bounds pointer");
                return null;
            }

            const view = new Uint8Array(this.memory.buffer);
            // Safety bound to avoid infinite loop
            const maxLen = 1 * 1024 * 1024; // 1MB limit (Audit Recommendation: Reduced from 10MB)
            let count = 0;
            while (view[end] !== 0 && end < view.length && count < maxLen) {
                end++;
                count++;
            }

            const resultBytes = view.slice(resultPtr, end);
            const decoder = new TextDecoder();
            const jsonStr = decoder.decode(resultBytes);

            if (!jsonStr) return null;
            try {
                return JSON.parse(jsonStr);
            } catch (e) {
                console.error("Plugin returned invalid JSON");
                return null;
            }

        } catch (e) {
            console.error(`Plugin ${this.name} failed:`, e);
            return null;
        } finally {
            // Free result string
            if (resultPtr !== 0 && this.freeString) {
                this.freeString(resultPtr);
            }
            // Free input if not already freed (e.g. exception)
            if (ptr !== 0 && this.dealloc) {
                this.dealloc(ptr, 0); // Len might be lost or we assume 0 is ok for some allocators, or we capture len.
                // JS scoping makes capturing len easy if we didn't modify it.
            }
        }
    }
}

window.pluginManager = {
    plugins: [],

    async loadPlugins(pluginListUrl = 'assets/plugins/plugins.json') {
        try {
            const res = await fetch(pluginListUrl);
            if (!res.ok) {
                console.log("No plugins registry found.");
                return;
            }
            const list = await res.json();

            for (const p of list) {
                try {
                    // p.url should be relative to where the page is served, or absolute
                    const wasmRes = await fetch(p.url);
                    const buf = await wasmRes.arrayBuffer();
                    const { instance } = await WebAssembly.instantiate(buf, {});
                    this.plugins.push(new WasmPlugin(p.name, instance));
                    console.log(`Loaded plugin: ${p.name}`);
                } catch (e) {
                    console.error(`Failed to load plugin ${p.name}:`, e);
                }
            }
        } catch (e) {
            console.log("Plugin loading skipped or failed.");
        }
    },

    parseAll(config) {
        for (const plugin of this.plugins) {
            const res = plugin.parse(config);
            if (res) return res;
        }
        return null;
    }
};

// Auto-init
document.addEventListener('DOMContentLoaded', () => {
    window.pluginManager.loadPlugins();
});
