document.addEventListener('DOMContentLoaded', () => {
    // Note: Common UI (Theme, Header Scroll, Mobile Nav, Copy Buttons) is now handled by common-ui.js

    // Initialize Dynamic Downloads (Client Selector)
    if (typeof initDynamicDownloads === 'function') {
        initDynamicDownloads();
    } else {
        console.warn('initDynamicDownloads is not defined. dynamic-downloads.js might be missing.');
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

                // Use total_sourced for the number of sources scraped; fall back to total_proxies if missing
                const totalSourced = stats.total_sourced || stats.total_proxies || 0;
                updateElement('#totalSourced', formatNum(totalSourced));

                // Unique & verified proxies correspond to total_proxies (unique) or total_tested on some back‑ends
                const totalConfigs = stats.unique || stats.total_unique || stats.total_proxies || stats.total_tested || 0;
                updateElement('#totalConfigs', formatNum(totalConfigs));

                // Currently online proxies
                const workingCount = stats.total_working || stats.active || stats.alive || 0;
                updateElement('#workingConfigs', formatNum(workingCount));

                updateElement('#totalRevived', formatNum(stats.total_revived || 0));
                updateElement('#threatsBlocked', formatNum(stats.total_dirty || 0));

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
