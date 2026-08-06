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

        triggerFailover: async function() {
            if (!global.CS_CONSTANTS) return;
            if (Failover._hasAttemptedThisSession()) return;
            Failover._markAttemptedThisSession();

            console.warn("Triggering IPFS Failover...");
            const gateways = global.CS_CONSTANTS.IPFS_GATEWAYS;
            const ipnsKey = global.CS_CONSTANTS.IPNS_KEY;
            if (!Array.isArray(gateways) || gateways.length === 0) {
                console.warn("IPFS Gateways not configured.");
                return;
            }
            if (!ipnsKey || String(ipnsKey).includes('...')) {
                console.warn("IPFS failover skipped: IPNS_KEY not configured.");
                return;
            }

            // Preserve only the leaf page. Query strings and fragments can contain
            // user state or tokens and must not be disclosed to third-party gateways.
            const pathname = window.location.pathname || '/';
            const parts = pathname.split('/').filter(Boolean);
            const leaf = parts.length ? parts[parts.length - 1] : 'index.html';
            const page = (leaf && leaf.includes('.')) ? leaf : 'index.html';

            for (const gateway of gateways) {
                try {
                    const parsed = new URL(String(gateway));
                    if (parsed.protocol !== 'https:') {
                        console.warn(`Failover: rejected non-HTTPS gateway ${gateway}`);
                        continue;
                    }
                    parsed.pathname = `${parsed.pathname.replace(/\/(?:ipfs|ipns)\/?$/, '').replace(/\/$/, '')}/ipns/${encodeURIComponent(String(ipnsKey))}/${encodeURIComponent(page)}`;
                    parsed.search = '';
                    parsed.hash = '';
                    const altURL = parsed.toString();
                    await fetch(altURL, { method: 'HEAD', mode: 'no-cors' });
                    console.warn(`Failover: switching to IPFS gateway ${parsed.origin}`);
                    window.location.href = altURL;
                    return;
                } catch (error) {
                    console.warn(`Failover: gateway unavailable ${gateway}: ${error.message || error}`);
                }
            }
            console.warn("IPFS failover failed: no configured gateway was reachable.");
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
