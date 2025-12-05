// Failover Logic (Non-Module)
// Switches to IPFS gateways if main host fails

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

        triggerFailover: function() {
            if (!global.CS_CONSTANTS) return;

            console.warn("Triggering IPFS Failover...");
            // Logic to redirect or swap asset URLs
            // For now, just log
            global.CS_CONSTANTS.IPFS_GATEWAYS.forEach(gw => {
                console.log(`Trying gateway: ${gw}`);
            });
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
