// [FIX P1] Import production-safe logger (disables console.log in production)
import logger from './utils/logger.js';

document.addEventListener('DOMContentLoaded', () => {
    // Note: Common UI (Theme, Header Scroll, Mobile Nav, Copy Buttons) is now handled by common-ui.js

    // Initialize Dynamic Downloads (Client Selector)
    if (typeof initDynamicDownloads === 'function') {
        initDynamicDownloads();
    } else {
        logger.warn('initDynamicDownloads is not defined. dynamic-downloads.js might be missing.');
    }

    // --- WebSocket & Differential Updates ---
    let reconnectDelay = 5000;
    function connectWebSocket() {
        // Disable on static hosting to prevent console noise
        if (['github.io', 'pages.dev', 'netlify.app'].some(d => location.hostname.includes(d))) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // Adjust port if running on different port, but usually relative to current host
        const wsUrl = `${protocol}//${window.location.host}/ws/updates`;
        let ws;

        try {
            ws = new WebSocket(wsUrl);
        } catch (e) {
            logger.log('WebSocket not supported or failed to connect:', e);
            return;
        }

        ws.onopen = () => {
            logger.log('[WS] Connected');
        };

        ws.onmessage = async (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'UPDATE_AVAILABLE') {
                    logger.log('[WS] Update available:', msg.version);
                    // Trigger differential update via cache manager if available, or reload
                    if (window.performDifferentialUpdate) {
                        await window.performDifferentialUpdate(msg.version);
                    } else {
                        // Reload page or re-fetch data
                        location.reload();
                    }
                }
            } catch (e) {
                logger.warn('[WS] Parse error', e);
            }
        };

        ws.onclose = () => {
            logger.log(`[WS] Disconnected, retrying in ${reconnectDelay/1000}s...`);
            setTimeout(connectWebSocket, reconnectDelay);
            // Exponential backoff cap at 60s
            reconnectDelay = Math.min(reconnectDelay * 1.5, 60000);
        };

        ws.onerror = (err) => {
            logger.error('[WS] Error:', err);
        };
    }

    // Expose Diff Update Logic globally so it can be used or extended
    window.performDifferentialUpdate = async function(newVersion) {
        if (!window.cacheManager) {
            logger.warn("CacheManager missing, full reload");
            location.reload();
            return;
        }

        const cached = await window.cacheManager.getCachedData('/api/proxies');
        if (!cached || !cached.version) {
            // No cache, fetch full
            logger.log('[Diff] No cache version, fetching full');
            return window.cacheManager.fetchFresh('/api/proxies');
        }

        try {
            // Try fetching diff
            logger.log(`[Diff] Requesting diff from ${cached.version} to ${newVersion}`);
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
                logger.log('[Diff] Server requested full reload');
                await window.cacheManager.fetchFresh('/api/proxies');
                window.dispatchEvent(new CustomEvent('data-updated'));
            }
        } catch (e) {
            logger.warn('[Diff] Failed, falling back to full fetch', e);
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
            logger.error("StateManager not found!");
            if (preloader) {
                preloader.classList.add('hidden');
                document.body.classList.add('loaded');
            }
            return;
        }
        window.stateManager.setLoading(true, 'Fetching latest data...');

        // Define defaults and updater function outside try/catch to ensure availability
        let sourceCount = 0;
        let updateFreq = 6;

        const updateHeroSubtitle = () => {
             const heroSubtitle = document.getElementById('heroSubtitle');
             const formatNum = (num) => {
                 if (num === undefined || num === null) return 'N/A';
                 return window.i18n && window.i18n.formatNumber ? window.i18n.formatNumber(num) : num;
             };

             if (heroSubtitle && window.i18n) {
                 let text = window.i18n.t('hero.subtitle.main');
                 text = text.replace('{sources}', formatNum(sourceCount));
                 text = text.replace('{hours}', formatNum(updateFreq));
                 // [FIX] Sanitize before innerHTML to prevent XSS if metadata is poisoned.
                // The text template comes from i18n (trusted) and values are numbers,
                // but defense-in-depth requires sanitization.
                if (window.DOMPurify) {
                    heroSubtitle.innerHTML = window.DOMPurify.sanitize(text, {ALLOWED_TAGS: ['strong', 'em', 'b', 'i', 'span']});
                } else {
                    heroSubtitle.textContent = text.replace(/<[^>]*>/g, '');
                }
             }
        };

        // Initialize immediately with defaults to avoid "--" flash or placeholders
        updateHeroSubtitle();
        window.addEventListener('languageChanged', updateHeroSubtitle);

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
                const formatNum = (num) => {
                    if (num === undefined || num === null) return 'N/A';
                    return window.i18n && window.i18n.formatNumber ? window.i18n.formatNumber(num) : num;
                };

                // STANDARDIZED BACKEND-FRONTEND MAPPING
                // Single source of truth: metadata.json canonical fields (from output_logic.py)
                // All fields use canonical names from backend with minimal fallbacks

                const totalSourced = stats.total_lines_sourced;
                updateElement('#totalSourced', formatNum(totalSourced));

                const totalConfigs = stats.total_unique_candidates;
                updateElement('#totalConfigs', formatNum(totalConfigs));

                const workingCount = stats.total_valid_proxies;
                updateElement('#workingConfigs', formatNum(workingCount));

                const revivedWarp = stats.revived_warp || 0;
                const revivedVwarp = stats.revived_vwarp || 0;
                const totalRevived = stats.total_revived ?? (revivedWarp + revivedVwarp);
                updateElement('#totalRevived', formatNum(totalRevived));
                updateElement('#revivedWarp', formatNum(revivedWarp));
                updateElement('#revivedVwarp', formatNum(revivedVwarp));

                const threatsBlocked = stats.total_dirty;
                updateElement('#threatsBlocked', formatNum(threatsBlocked));

                const smartChains = stats.total_smart_chains;
                updateElement('#smartChains', formatNum(smartChains));

                const vwarpWinRate = stats.vwarp_win_rate;
                const washingEnabled = stats.washing_enabled;
                const winRateDisplay = (washingEnabled !== false && vwarpWinRate !== undefined) ? `${Math.round(vwarpWinRate)}%` : 'N/A';
                updateElement('#vwarpWinRate', winRateDisplay);

                // Add tooltip or visual indicator if washing is disabled
                const winRateElem = document.querySelector('#vwarpWinRate');
                if (winRateElem && washingEnabled === false) {
                     winRateElem.setAttribute('title', 'Washing disabled (no keys provided)');
                     winRateElem.style.opacity = '0.7';
                }

                // Configuration values from metadata (or stats as fallback)
                // Default to 6 hours if metadata is missing
                updateFreq = metadata?.update_interval_hours || stats.update_interval_hours || 6;
                updateElement('#updateFrequency', `${updateFreq} hrs`);

                sourceCount = metadata?.sources_count || stats.sources_count || 0;

                // Re-run updater with new data
                updateHeroSubtitle();

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
