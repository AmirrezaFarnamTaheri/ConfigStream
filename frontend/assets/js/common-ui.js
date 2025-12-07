/**
 * Common UI logic shared across all pages
 * Handles: Header Scroll, Mobile Nav, Theme Switcher, Copy Buttons, Inline Icons
 */

// Immediate fix for "White Page" issue: Remove no-js class as soon as script runs
try {
    if (typeof document !== 'undefined' && document.documentElement && document.documentElement.classList) {
        document.documentElement.classList.remove('no-js');
    } else {
        window.addEventListener('DOMContentLoaded', () => {
            document.documentElement.classList.remove('no-js');
        }, { once: true });
    }
} catch (e) {
    // Silently ignore to avoid breaking page initialization
    window.addEventListener('DOMContentLoaded', () => {
        try { document.documentElement.classList.remove('no-js'); } catch (_) {}
    }, { once: true });
}

document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme
    if (window.api && window.api.initTheme) {
        window.api.initTheme();
    }

    // Initialize header scroll effect
    initHeaderScroll();

    // Initialize mobile navigation
    if (window.api && window.api.initMobileNav) {
        window.api.initMobileNav();
    }

    // Initialize accordion (Home page specific)
    initAccordion();

    // Initialize copy buttons (if present)
    initCopyButtons();

    // Initialize inline icons (if present)
    if (window.inlineIcons) {
        window.inlineIcons.replace();
    } else if (window.feather) {
        window.feather.replace();
    }
});

function initHeaderScroll() {
    const header = document.querySelector('.header');
    if (!header) return;

    const onScroll = () => {
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    };

    window.addEventListener('scroll', onScroll);
    // Initial check
    onScroll();
}

function initCopyButtons() {
    document.addEventListener('click', async (e) => {
        const button = e.target.closest('.copy-btn');
        if (!button) return;

        // Prevent default if it's a button, though mostly used on <button>
        // If it's <a> with href, let it handle unless data-file/config is present?
        // Actually the original logic was specific.

        const config = button.dataset.config;
        const file = button.dataset.file;

        let textToCopy;

        if (config) {
            textToCopy = decodeURIComponent(config);
        } else if (file) {
             const FILE_MAP = {
                'subscribe/singbox': 'singbox.json',
                'subscribe/singbox-vpn': 'singbox-vpn.json',
                'subscribe/clash': 'clash.yaml',
                'subscribe/base64': 'base64.txt',
                'subscribe/shadowrocket': 'shadowrocket.txt',
                'subscribe/surge': 'surge.conf',
                'subscribe/loon': 'loon.conf',
                'subscribe/quantumultx': 'quantumult.conf',
                'subscribe/sip008': 'sip008.json',
                'files/chosen/base64.txt': 'chosen/base64.txt'
            };
            let targetFile = FILE_MAP[file] || file;
            if (window.getFullUrl) {
                textToCopy = window.getFullUrl(targetFile);
            } else if (window.api && window.api.getFullUrl) {
                 // fallback if attached to api
                 // But getFullUrl is usually global in utils.js
            } else {
                 // Utils might export it or global scope
                 // Assuming utils.js is loaded
                 textToCopy = getFullUrl(targetFile);
            }
        } else {
            return;
        }

        if (textToCopy) {
             await copyToClipboard(textToCopy, button);
        }
    });
}

// Re-export utility needed if not global (utils.js handles this mostly)

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
