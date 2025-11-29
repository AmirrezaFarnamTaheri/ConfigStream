document.addEventListener('DOMContentLoaded', () => {
    // Note: Common UI (Theme, Header Scroll, Mobile Nav, Copy Buttons) is now handled by common-ui.js

    // Initialize accordion (Home page specific)
    initAccordion();

    // Initialize Dynamic Downloads (Client Selector)
    initDynamicDownloads();

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
                updateFreshness(date);
            }

            // Update stats card
            if (stats) {
                updateElement('#totalSourced', stats.total_fetched || 0);
                updateElement('#totalConfigs', stats.total_tested || 0);
                updateElement('#workingConfigs', stats.total_working || 0);
                updateElement('#updateFrequency', '6 hrs');

                // Update Hero Text
                const heroCount = document.getElementById('heroSourceCount');
                if (heroCount && stats.total_fetched) {
                    heroCount.textContent = stats.total_fetched;
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

function updateFreshness(date) {
    const diffHours = (new Date() - date) / (1000 * 60 * 60);
    const footerUpdate = document.getElementById('footerUpdate');
    if (!footerUpdate) return;

    let color = '#22c55e'; // Green
    if (diffHours > 8) color = '#eab308'; // Yellow
    if (diffHours > 24) color = '#ef4444'; // Red

    footerUpdate.style.color = color;
    footerUpdate.style.fontWeight = 'bold';
}

function initAccordion() {
    const accordionContainers = document.querySelectorAll('.accordion-container');
    if (accordionContainers.length === 0) return;

    const isMobile = () => window.innerWidth <= 768;

    const setupAccordion = (container) => {
        const items = container.querySelectorAll('.accordion-item');
        if (items.length === 0) return;

        // On mobile, all accordions start collapsed. On desktop, they start open.
        items.forEach((item, index) => {
            const header = item.querySelector('.accordion-header');
            const content = item.querySelector('.accordion-content');

            // Mobile: all collapsed. Desktop: all expanded.
            const isExpanded = !isMobile();

            header.setAttribute('aria-expanded', isExpanded);
            content.style.gridTemplateRows = isExpanded ? '1fr' : '0fr';
        });

        items.forEach(item => {
            const header = item.querySelector('.accordion-header');
            if (!header.hasAttribute('data-accordion-initialized')) {
                header.setAttribute('data-accordion-initialized', 'true');
                header.addEventListener('click', () => {
                    const isExpanded = header.getAttribute('aria-expanded') === 'true';

                    if (isMobile()) {
                        // On mobile, opening one closes others.
                        items.forEach(otherItem => {
                            if (otherItem !== item) {
                                const otherHeader = otherItem.querySelector('.accordion-header');
                                otherHeader.setAttribute('aria-expanded', 'false');
                                otherItem.querySelector('.accordion-content').style.gridTemplateRows = '0fr';
                            }
                        });
                    }

                    // Toggle the clicked accordion
                    header.setAttribute('aria-expanded', !isExpanded);
                    item.querySelector('.accordion-content').style.gridTemplateRows = !isExpanded ? '1fr' : '0fr';
                });
            }
        });
    };

    let resizeTimeout;
    const onResize = () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            accordionContainers.forEach(setupAccordion);
        }, 200);
    };

    accordionContainers.forEach(setupAccordion);
    window.addEventListener('resize', onResize);
}
