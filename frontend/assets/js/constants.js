// Global Constants for ConfigStream Frontend
// Attached to window.CS_CONSTANTS to avoid namespace pollution

(function(global) {
    global.CS_CONSTANTS = {
        // Ed25519 Public Key for Subscription Verification (Replace with actual prod key)
        PUBLIC_KEY: "MCowBQYDK2VwAyEA79e/79e/79e/79e/79e/79e/79e/79e/79e/79e/79e=",

        // IPNS Key for Failover (Replace with actual)
        IPNS_KEY: "k51qzi5uqu5d...",

        // API Endpoints
        API_BASE: "/api",
        IPFS_GATEWAYS: [
            "https://ipfs.io/ipfs/",
            "https://cloudflare-ipfs.com/ipfs/",
            "https://dweb.link/ipfs/"
        ]
    };
    console.log("✅ ConfigStream Constants Loaded");
})(typeof window !== 'undefined' ? window : self);
