import { IPNS_KEY } from './constants.js';

const GATEWAYS = [
    "https://ipfs.io/ipns/",
    "https://cloudflare-ipfs.com/ipns/",
    "https://dweb.link/ipns/"
];

// Fallback logic for fetching configuration
async function fetchWithFallback(primaryUrl) {
    try {
        const response = await fetch(primaryUrl);
        if (!response.ok) throw new Error("Primary failed");
        return await response.json();
    } catch (e) {
        console.warn("Primary fetch failed, attempting IPFS fallback...");

        // Validate IPNS key was configured
        if (IPNS_KEY === "PLACEHOLDER_IPNS_KEY_INJECTED_BY_CI" || IPNS_KEY.length < 20) {
            console.error("IPFS fallback not configured: IPNS_KEY is placeholder");
            // Audit: Providing user-friendly message
            alert("Connection lost. Fallback unavailable because IPNS is not configured.");
            throw new Error("IPFS fallback unavailable - IPNS_KEY not configured");
        }

        // Try DNSLink first (faster than IPNS resolve)
        // Assuming we have a domain like _dnslink.fallback.com
        // We can query it via DoH

        // For this implementation, we race the gateways with the IPNS key
        const controller = new AbortController();
        const promises = GATEWAYS.map(gw =>
            fetch(`${gw}${IPNS_KEY}`, { signal: controller.signal })
                .then(r => {
                    if(r.ok) return r.json();
                    throw new Error("Gateway failed");
                })
        );

        try {
            const result = await Promise.any(promises);
            controller.abort(); // Cancel others
            return result;
        } catch (err) {
            console.error("All fallbacks failed.");
            throw err;
        }
    }
}
