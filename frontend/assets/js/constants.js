// Global Constants for ConfigStream Frontend
// Attached to window.CS_CONSTANTS to avoid namespace pollution

(function(global) {
    global.CS_CONSTANTS = {
        // Ed25519 Public Key for Subscription Verification
        // [FIX P2] Set via environment variable in production builds
        // Build command: CS_PUBLIC_KEY="actual_key" npm run build
        PUBLIC_KEY: "MCowBQYDK2VwAyEA79e/79e/79e/79e/79e/79e/79e/79e/79e/79e/79e=",

        // IPNS Key for Failover
        // [FIX P2] Set via environment variable in production builds
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

    // [FIX P2] Validation: Detect placeholder values in production
    const isProduction = global.location &&
                        global.location.protocol === 'https:' &&
                        !global.location.hostname.includes('localhost') &&
                        !global.location.hostname.includes('127.0.0.1');

    if (isProduction) {
        if (global.CS_CONSTANTS.PUBLIC_KEY.includes("79e/79e/")) {
            console.error("❌ CRITICAL: Production deployment using placeholder PUBLIC_KEY!");
            console.error("   Set CS_PUBLIC_KEY environment variable during build.");
            console.error("   Subscription verification will NOT work!");
        }
        if (global.CS_CONSTANTS.IPNS_KEY.includes("...")) {
            console.error("❌ CRITICAL: Production deployment using placeholder IPNS_KEY!");
            console.error("   Set CS_IPNS_KEY environment variable during build.");
            console.error("   IPFS failover will NOT work!");
        }
    }

    console.log("✅ ConfigStream Constants Loaded");
})(typeof window !== 'undefined' ? window : self);
