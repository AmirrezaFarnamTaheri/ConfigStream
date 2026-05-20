// Failover Logic (Non-Module)
// Switches to IPFS gateways if main host fails

(function(global) {
    const Failover = {
        _hasAttemptedThisSession: function() {
            try {
                return sessionStorage.getItem('configstream_failover_attempted') === '1';
            } catch (e) {
                return false;
            }
        },

        _markAttemptedThisSession: function() {
            try {
                sessionStorage.setItem('configstream_failover_attempted', '1');
            } catch (e) {
                // ignore
            }
        },

        _getConnectivityProbeUrl: function() {
            // Prefer a static asset that is guaranteed to exist on GitHub Pages/static hosting.
            // Using `/health` breaks on static sites (404 triggers false failover).
            const root = (global.ROOT_PATH || './');
            return root + 'assets/svg/favicon.svg';
        },

        checkConnectivity: async function() {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 2000);
                const probeUrl = Failover._getConnectivityProbeUrl();
                // Use GET to avoid false negatives if HEAD is blocked by some intermediaries.
                const resp = await fetch(probeUrl, { cache: 'no-store', signal: controller.signal });
                clearTimeout(timeoutId);
                return resp.ok;
            } catch (e) {
                return false;
            }
        },

        triggerFailover: function() {
            if (!global.CS_CONSTANTS) return;
            if (Failover._hasAttemptedThisSession()) return;
            Failover._markAttemptedThisSession();

            console.warn("Triggering IPFS Failover...");
            // Logic to redirect or swap asset URLs
            if (global.CS_CONSTANTS.IPFS_GATEWAYS) {
                const gateways = global.CS_CONSTANTS.IPFS_GATEWAYS;
                const ipnsKey = global.CS_CONSTANTS.IPNS_KEY;
                if (!ipnsKey || String(ipnsKey).includes('...')) {
                    console.warn("IPFS failover skipped: IPNS_KEY not configured.");
                    return;
                }

                // Preserve the leaf page when switching origins (GitHub Pages is usually hosted under /<repo>/,
                // while IPNS gateways are typically rooted at /ipns/<key>/).
                const pathname = window.location.pathname || '/';
                const parts = pathname.split('/').filter(Boolean);
                const leaf = parts.length ? parts[parts.length - 1] : 'index.html';
                const page = (leaf && leaf.includes('.')) ? leaf : 'index.html';

                const suffix = page + window.location.search + window.location.hash;

                for (const gw of gateways) {
                    // Gateways might be provided as ".../ipfs/" or just host. Normalize and build /ipns/ URL.
                    let base = String(gw).replace(/\/+$/, '');
                    base = base.replace(/\/ipfs$/, '').replace(/\/ipns$/, '');
                    const altURL = `${base}/ipns/${encodeURIComponent(String(ipnsKey))}/${suffix.replace(/^\/+/, '')}`;
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
