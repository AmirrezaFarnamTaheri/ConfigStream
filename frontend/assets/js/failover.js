// Failover Logic (Non-Module)
// Switches to IPFS gateways if main host fails

(function(global) {
    const Failover = {
        checkConnectivity: async function() {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 2000);
                const resp = await fetch('/health', { signal: controller.signal });
                clearTimeout(timeoutId);
                return resp.ok;
            } catch (e) {
                return false;
            }
        },

        triggerFailover: function() {
            if (!global.CS_CONSTANTS) return;

            console.warn("Triggering IPFS Failover...");
            // Logic to redirect or swap asset URLs
            if (global.CS_CONSTANTS.IPFS_GATEWAYS) {
                const gateways = global.CS_CONSTANTS.IPFS_GATEWAYS;
                const currentPath = window.location.pathname + window.location.search;
                for (const gw of gateways) {
                    const altURL = gw.replace(/\/$/, "") + currentPath;
                    // Attempt to fetch an asset (e.g., a small icon or HEAD of current page) from the gateway to test connectivity
                    // Use mode: 'no-cors' since we just want to see if it's reachable (opaque response is fine vs network error)
                    fetch(altURL, { method: 'HEAD', mode: 'no-cors' }).then(() => {
                        console.warn(`Failover: switching to IPFS gateway ${gw}`);
                        window.location.href = altURL;
                    }).catch(() => {/* try next gateway */});
                }
            } else {
                console.warn("IPFS Gateways not configured.");
            }

            // Audit: Providing user-friendly message
            // alert("Connection lost. Switching to decentralized network...");
        }
    };

    // Auto-check on load
    window.addEventListener('load', async () => {
        const isOnline = await Failover.checkConnectivity();
        if (!isOnline) {
            Failover.triggerFailover();
        }
    });

    global.Failover = Failover;
})(typeof window !== 'undefined' ? window : self);
