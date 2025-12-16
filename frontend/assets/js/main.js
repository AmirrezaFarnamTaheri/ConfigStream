document.addEventListener('DOMContentLoaded', () => {
    // Note: Common UI (Theme, Header Scroll, Mobile Nav, Copy Buttons) is now handled by common-ui.js

    // Initialize Dynamic Downloads (Client Selector)
    if (typeof initDynamicDownloads === 'function') {
        initDynamicDownloads();
    } else {
        console.warn('initDynamicDownloads is not defined. dynamic-downloads.js might be missing.');
    }

    // --- WebSocket & Differential Updates ---
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // Adjust port if running on different port, but usually relative to current host
        const wsUrl = `${protocol}//${window.location.host}/ws/updates`;
        let ws;

        try {
            ws = new WebSocket(wsUrl);
        } catch (e) {
            console.log('WebSocket not supported or failed to connect:', e);
            return;
        }

        ws.onopen = () => {
            console.log('[WS] Connected');
        };

        ws.onmessage = async (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'UPDATE_AVAILABLE') {
                    console.log('[WS] Update available:', msg.version);
                    // Trigger differential update via cache manager if available, or reload
                    if (window.performDifferentialUpdate) {
                        await window.performDifferentialUpdate(msg.version);
                    } else {
                        // Reload page or re-fetch data
                        location.reload();
                    }
                }
            } catch (e) {
                console.warn('[WS] Parse error', e);
            }
        };

        ws.onclose = () => {
            console.log('[WS] Disconnected, retrying in 5s...');
            setTimeout(connectWebSocket, 5000); // Auto-reconnect
        };

        ws.onerror = (err) => {
            console.error('[WS] Error:', err);
        };
    }

    // Expose Diff Update Logic globally so it can be used or extended
    window.performDifferentialUpdate = async function(newVersion) {
        if (!window.cacheManager) {
            console.warn("CacheManager missing, full reload");
            location.reload();
            return;
        }

        const cached = await window.cacheManager.getCachedData('/api/proxies');
        if (!cached || !cached.version) {
            // No cache, fetch full
            console.log('[Diff] No cache version, fetching full');
            return window.cacheManager.fetchFresh('/api/proxies');
        }

        try {
            // Try fetching diff
            console.log(`[Diff] Requesting diff from ${cached.version} to ${newVersion}`);
            const response = await fetch(`/api/diff/proxies?base_version=${cached.version}`);

            if (!response.ok) {
                 throw new Error("Diff endpoint returned " + response.status);
            }

            const update = await response.json();

            if (update.type === 'delta') {
                let proxies = cached.data;
                // Apply deletions
                if (update.removed && update.removed.length > 0) {
                     const removeSet = new Set(update.removed);
                     // Assuming proxies have 'id'
                     proxies = proxies.filter(p => !removeSet.has(p.id));
                }

                // Apply additions
                if (update.added && update.added.length > 0) {
                    proxies = proxies.concat(update.added);
                }

                // Save new state
                await window.cacheManager.cacheData('/api/proxies', proxies, newVersion);

                // Dispatch event for UI updates
                window.dispatchEvent(new CustomEvent('data-updated', { detail: { count: proxies.length } }));

                // Use state manager notification instead of alert() for better UX
                if (window.stateManager && window.stateManager.showNotification) {
                    window.stateManager.showNotification(`Data updated! +${update.added.length} -${update.removed.length} proxies.`, 'success');
                }
            } else {
                // Full reload required
                console.log('[Diff] Server requested full reload');
                await window.cacheManager.fetchFresh('/api/proxies');
                window.dispatchEvent(new CustomEvent('data-updated'));
            }
        } catch (e) {
            console.warn('[Diff] Failed, falling back to full fetch', e);
            await window.cacheManager.fetchFresh('/api/proxies');
            window.dispatchEvent(new CustomEvent('data-updated'));
        }
    };

    // Start WebSocket listener if we are in a browser environment that supports it
    if (typeof WebSocket !== 'undefined') {
        connectWebSocket();
    }


    // --- DATA FETCHING & INITIALIZATION ---
    (async () => {
        const preloader = document.getElementById('preloader');
        const logo = document.querySelector('.logo-svg');

        if (!window.stateManager) {
            console.error("StateManager not found!");
            if (preloader) {
                preloader.classList.add('hidden');
                document.body.classList.add('loaded');
            }
            return;
        }
        window.stateManager.setLoading(true, 'Fetching latest data...');
        try {
            // Fetch metadata and statistics in parallel
            const [metadata, stats] = await Promise.all([
                fetchMetadata(),
                fetchStatistics()
            ]);

            // Store protocol colors globally
            if (metadata && metadata.protocol_colors) {
                window.PROTOCOL_COLORS = metadata.protocol_colors;
            }

            // Update footer timestamp
            if (metadata && metadata.last_updated_utc) {
                const date = new Date(metadata.last_updated_utc);
                const formatted = formatTimestamp(date);
                updateElement('#footerUpdate', formatted);

                // Update freshness indicator
                if (window.api && window.api.updateFreshnessColor) {
                    window.api.updateFreshnessColor(date);
                }
            }

            // Update stats card
            if (stats) {
                // Use formatNumber for all numeric displays
                const formatNum = (num) => window.i18n && window.i18n.formatNumber ? window.i18n.formatNumber(num) : num;

                // Use comprehensive fallback chain to match analytics.js
                const totalSourced = stats.total_lines_sourced || stats.fetched_lines || stats.fetched_sources ||
                                     stats.total_fetched || stats.total_sourced || stats.total_proxies || 0;
                updateElement('#totalSourced', formatNum(totalSourced));

                // Unique & verified proxies with comprehensive fallback chain
                const totalConfigs = stats.total_unique_candidates || stats.parsed || stats.unique ||
                                     stats.total_unique || stats.total_proxies || stats.total_tested || 0;
                updateElement('#totalConfigs', formatNum(totalConfigs));

                // Currently online proxies with comprehensive fallback chain
                const workingCount = stats.total_valid_proxies || stats.total_working || stats.working ||
                                     stats.active || stats.alive || 0;
                updateElement('#workingConfigs', formatNum(workingCount));

                // Revived/Washed proxies with fallback
                const totalRevived = stats.total_revived || stats.washer_success_count || 0;
                updateElement('#totalRevived', formatNum(totalRevived));

                // Threats blocked with fallback
                const threatsBlocked = stats.total_dirty || stats.threats_blocked || 0;
                updateElement('#threatsBlocked', formatNum(threatsBlocked));

                // Smart Chains count
                const smartChains = stats.smart_chain_count || 0;
                updateElement('#smartChains', formatNum(smartChains));

                // Vwarp Win Rate (efficiency percentage)
                const vwarpWinRate = stats.vwarp_win_rate || 0;
                updateElement('#vwarpWinRate', `${Math.round(vwarpWinRate)}%`);

                // Dynamic update frequency from metadata or fallback to 6 hours
                const updateFreq = metadata?.update_interval_hours || 6;
                updateElement('#updateFrequency', `${updateFreq} hrs`);

                // Update source count from metadata
                const sourceCount = metadata?.sources_count || stats.total_sources || 668;

                // Update hero subtitle dynamic values
                const heroSourceCountElem = document.getElementById('heroSourceCount');
                if (heroSourceCountElem) {
                    heroSourceCountElem.textContent = formatNum(sourceCount);
                }

                const heroUpdateFreqElem = document.getElementById('heroUpdateFrequency');
                if (heroUpdateFreqElem) {
                    heroUpdateFreqElem.textContent = formatNum(updateFreq);
                }

                // Update "How it works" section dynamic values
                const infoSourceCountElem = document.getElementById('infoSourceCount');
                if (infoSourceCountElem) {
                    infoSourceCountElem.textContent = formatNum(sourceCount);
                }

                const infoUpdateFreqElem = document.getElementById('infoUpdateFrequency');
                if (infoUpdateFreqElem) {
                    infoUpdateFreqElem.textContent = formatNum(updateFreq);
                }
            }

        } catch (error) {
            window.stateManager.setError('Failed to initialize page data.', error);
            // Update UI to show that data loading failed
            updateElement('#footerUpdate', 'N/A');
            updateElement('#totalConfigs', 'N/A');
            updateElement('#workingConfigs', 'N/A');
        } finally {
            window.stateManager.setLoading(false);
            // Hide preloader after data fetching is complete
            if (preloader) {
                setTimeout(() => {
                    preloader.classList.add('hidden');
                    document.body.classList.add('loaded');
                    if (logo) {
                        logo.classList.add('loading-animation');
                    }
                }, 100);
            }
        }
    })();
});
