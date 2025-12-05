@ -1,49 +1,39 @@
import { IPNS_KEY } from './constants.js';
// Failover Logic (Non-Module)
// Switches to IPFS gateways if main host fails

const GATEWAYS = [
    "https://ipfs.io/ipns/",
    "https://cloudflare-ipfs.com/ipns/",
    "https://dweb.link/ipns/"
];
(function(global) {
    const Failover = {
        checkConnectivity: async function() {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 2000);
                const resp = await fetch('/health_check', { signal: controller.signal });
                clearTimeout(timeoutId);
                return resp.ok;
            } catch (e) {
                return false;
            }
        },

// Fallback logic for fetching configuration
async function fetchWithFallback(primaryUrl) {
    try {
        const response = await fetch(primaryUrl);
        if (!response.ok) throw new Error("Primary failed");
        return await response.json();
    } catch (e) {
        console.warn("Primary fetch failed, attempting IPFS fallback...");
        triggerFailover: function() {
            if (!global.CS_CONSTANTS) return;

        // Validate IPNS key was configured
        if (IPNS_KEY === "PLACEHOLDER_IPNS_KEY_INJECTED_BY_CI" || IPNS_KEY.length < 20) {
            console.error("IPFS fallback not configured: IPNS_KEY is placeholder");
            // Audit: Providing user-friendly message
            alert("Connection lost. Fallback unavailable because IPNS is not configured.");
            throw new Error("IPFS fallback unavailable - IPNS_KEY not configured");
            console.warn("Triggering IPFS Failover...");
            // Logic to redirect or swap asset URLs
            // For now, just log
            global.CS_CONSTANTS.IPFS_GATEWAYS.forEach(gw => {
                console.log(`Trying gateway: ${gw}`);
            });
        }
    };

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
    // Auto-check on load
    window.addEventListener('load', async () => {
        const isOnline = await Failover.checkConnectivity();
        if (!isOnline) {
            Failover.triggerFailover();
        }
    }
}
    });

    global.Failover = Failover;
})(typeof window !== 'undefined' ? window : self);