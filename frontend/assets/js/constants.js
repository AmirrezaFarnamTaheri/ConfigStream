// Global Constants for ConfigStream Frontend
// Attached to window.CS_CONSTANTS to avoid namespace pollution

(function(global) {
    const runtimeConfig = global.CS_RUNTIME_CONFIG || {};
    global.CS_CONSTANTS = {
        // Ed25519 Public Key for Subscription Verification
        // Set by generated assets/js/runtime-config.js in production deploys.
        PUBLIC_KEY: runtimeConfig.PUBLIC_KEY || "",

        // IPNS Key for Failover
        // Set by generated assets/js/runtime-config.js when configured.
        IPNS_KEY: runtimeConfig.IPNS_KEY || "",

        // API Endpoints
        API_BASE: "/api",
        IPFS_GATEWAYS: [
            "https://ipfs.io/ipfs/",
            "https://cloudflare-ipfs.com/ipfs/",
            "https://dweb.link/ipfs/"
        ],

        // Steganography Constants
        STEGO_SEARCH_WINDOW: 500000,  // 500KB - Search window for payload marker
        STEGO_MAX_PAYLOAD_SIZE: 2 * 1024 * 1024  // 2MB - Max decompressed payload size
    };

    // Validation: Detect placeholder values in production
    const isProduction = global.location &&
                        global.location.protocol === 'https:' &&
                        !global.location.hostname.includes('localhost') &&
                        !global.location.hostname.includes('127.0.0.1');

    if (isProduction) {
        // [AUDIT] Errors here are critical config issues, keeping console.error is appropriate
        // but wrapping in logger if available is better practice
        const logError = (window.ConfigStreamLogger && window.ConfigStreamLogger.error)
                         ? window.ConfigStreamLogger.error
                         : console.error;

        if (!global.CS_CONSTANTS.PUBLIC_KEY) {
            logError("❌ CRITICAL: Production deployment missing PUBLIC_KEY!");
            logError("   Generate assets/js/runtime-config.js during deploy.");
            logError("   Subscription verification will NOT work!");
        }
        if (!global.CS_CONSTANTS.IPNS_KEY) {
            logError("❌ CRITICAL: Production deployment missing IPNS_KEY!");
            logError("   Generate assets/js/runtime-config.js during deploy.");
            logError("   IPFS failover will NOT work!");
        }
    }

    if (window.ConfigStreamLogger) {
        window.ConfigStreamLogger.info("✅ ConfigStream Constants Loaded");
    }
})(typeof window !== 'undefined' ? window : self);
