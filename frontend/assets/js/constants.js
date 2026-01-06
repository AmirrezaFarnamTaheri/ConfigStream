// Global Constants for ConfigStream Frontend
// Attached to window.CS_CONSTANTS to avoid namespace pollution

(function(global) {
    global.CS_CONSTANTS = {
        // Ed25519 Public Key for Subscription Verification
        // Set via environment variable in production builds
        // Build command: CS_PUBLIC_KEY="actual_key" npm run build
        PUBLIC_KEY: "MCowBQYDK2VwAyEA79e/79e/79e/79e/79e/79e/79e/79e/79e/79e/79e=",

        // IPNS Key for Failover
        // Set via environment variable in production builds
        // Build command: CS_IPNS_KEY="actual_key" npm run build
        IPNS_KEY: "k51qzi5uqu5d...",

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

        if (global.CS_CONSTANTS.PUBLIC_KEY.includes("79e/79e/")) {
            logError("❌ CRITICAL: Production deployment using placeholder PUBLIC_KEY!");
            logError("   Set CS_PUBLIC_KEY environment variable during build.");
            logError("   Subscription verification will NOT work!");
        }
        if (global.CS_CONSTANTS.IPNS_KEY.includes("...")) {
            logError("❌ CRITICAL: Production deployment using placeholder IPNS_KEY!");
            logError("   Set CS_IPNS_KEY environment variable during build.");
            logError("   IPFS failover will NOT work!");
        }
    }

    if (window.ConfigStreamLogger) {
        window.ConfigStreamLogger.info("✅ ConfigStream Constants Loaded");
    }
})(typeof window !== 'undefined' ? window : self);
