document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme
    initTheme();

    // Initialize header scroll effect
    initHeaderScroll();

    // Initialize copy buttons
    initCopyButtons();

    // Initialize inline icons
    if (window.inlineIcons) {
        window.inlineIcons.replace();
    }

    // Initialize mobile navigation
    initMobileNav();

    // Initialize accordion
    initAccordion();


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
            if (metadata && metadata.generated_at) {
                const date = new Date(metadata.generated_at);
                const formatted = formatTimestamp(date);
                updateElement('#footerUpdate', formatted);
            }

            // Update stats card
            if (stats) {
                updateElement('#totalConfigs', stats.total_tested || 0);
                updateElement('#workingConfigs', stats.total_working || 0);
                updateElement('#updateFrequency', '6 hrs');
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

function initTheme() {
    const themeSwitcher = document.getElementById('theme-switcher');
    if (!themeSwitcher) return; // Early return if theme switcher doesn't exist

    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    let currentTheme = localStorage.getItem('theme');

    const setTheme = (theme, animate = false) => {
        if (animate) {
            document.body.style.transition = 'background-color var(--transition-base), color var(--transition-base)';
        } else {
            document.body.style.transition = 'none';
        }
        document.body.classList.toggle('dark', theme === 'dark');
        localStorage.setItem('theme', theme);

        // Dispatch a custom event to notify other components (like charts)
        window.dispatchEvent(new CustomEvent('themechanged', { detail: { theme } }));

        if (!animate) {
            // Force a reflow to apply the initial state without transition
            void document.body.offsetWidth;
            document.body.style.transition = '';
        }
    };

    if (!currentTheme) {
        currentTheme = prefersDark.matches ? 'dark' : 'light';
    }

    setTheme(currentTheme);

    themeSwitcher.addEventListener('click', () => {
        const newTheme = document.body.classList.contains('dark') ? 'light' : 'dark';
        setTheme(newTheme, true);
    });

    prefersDark.addEventListener('change', (e) => {
        setTheme(e.matches ? 'dark' : 'light', true);
    });
}

function initHeaderScroll() {
    const header = document.querySelector('.header');
    if (!header) return;

    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });
}

function initAccordion() {
    const accordionContainers = document.querySelectorAll('.accordion-container');
    if (accordionContainers.length === 0) return;

    const isMobile = () => window.innerWidth <= 992;

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

function initCopyButtons() {
    document.addEventListener('click', async (e) => {
        const button = e.target.closest('.copy-btn');
        if (!button) return;

        const config = button.dataset.config;
        const file = button.dataset.file;

        let textToCopy;

        if (config) {
            textToCopy = decodeURIComponent(config);
        } else if (file) {
            textToCopy = getFullUrl(file);
        } else {
            return;
        }

        await copyToClipboard(textToCopy, button);
    });
}

function initMobileNav() {
    const toggleBtn = document.getElementById('mobile-nav-toggle');
    const mainNav = document.getElementById('main-nav');
    const navOverlay = document.querySelector('.nav-overlay');

    if (!toggleBtn || !mainNav || !navOverlay) return;

    const toggleNav = () => {
        const isNavOpen = document.body.classList.toggle('nav-open');
        toggleBtn.setAttribute('aria-expanded', isNavOpen);
    };

    toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleNav();
    });

    navOverlay.addEventListener('click', toggleNav);

    // Close nav when a link is clicked
    mainNav.addEventListener('click', (e) => {
        if (e.target.classList.contains('nav-link')) {
            if (document.body.classList.contains('nav-open')) {
                toggleNav();
            }
        }
    });

    // Close nav on 'Escape' key press
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && document.body.classList.contains('nav-open')) {
            toggleNav();
        }
    });
}