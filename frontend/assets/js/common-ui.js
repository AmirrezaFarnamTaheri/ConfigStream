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
    onScroll();
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
                 textToCopy = window.api.getFullUrl(targetFile);
            } else if (typeof getFullUrl === 'function') {
                 textToCopy = getFullUrl(targetFile);
            }
        } else {
            return;
        }

        if (textToCopy) {
             // Use global copyToClipboard utility
             if (window.copyToClipboard) {
                 await window.copyToClipboard(textToCopy, button);
             } else {
                 console.warn('copyToClipboard utility not found');
             }
        }
    });

    // F8 Fix: Add ARIA labels to copy buttons if missing
    document.querySelectorAll('.copy-btn').forEach(btn => {
        if (!btn.hasAttribute('aria-label')) {
            const label = btn.dataset.file ? `Copy link for ${btn.dataset.file}` : 'Copy to clipboard';
            btn.setAttribute('aria-label', label);
        }
        // Ensure keyboard accessibility
        if (!btn.hasAttribute('tabindex') && btn.tagName !== 'BUTTON') {
            btn.setAttribute('tabindex', '0');
        }
        // Add keydown listener for Enter/Space
        btn.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                btn.click();
            }
        });
    });
}

function initAccordion() {
    const accordionContainers = document.querySelectorAll('.accordion-container');
    if (accordionContainers.length === 0) return;

    const isMobile = () => window.innerWidth <= 768;

    const setupAccordion = (container) => {
        const items = container.querySelectorAll('.accordion-item');
        if (items.length === 0) return;

        items.forEach((item, index) => {
            const header = item.querySelector('.accordion-header');
            const content = item.querySelector('.accordion-content');

            // F8 Fix: ID and ARIA attributes
            const contentId = `accordion-content-${index}`;
            content.id = contentId;
            header.setAttribute('aria-controls', contentId);

            // On mobile, all accordions start collapsed. On desktop, they start open.
            const isExpanded = !isMobile();

            header.setAttribute('aria-expanded', isExpanded);
            content.style.gridTemplateRows = isExpanded ? '1fr' : '0fr';
            // Also hide/show content for screen readers
            content.setAttribute('aria-hidden', !isExpanded);
        });

        items.forEach(item => {
            const header = item.querySelector('.accordion-header');
            const content = item.querySelector('.accordion-content');

            if (!header.hasAttribute('data-accordion-initialized')) {
                header.setAttribute('data-accordion-initialized', 'true');
                header.addEventListener('click', () => {
                    const isExpanded = header.getAttribute('aria-expanded') === 'true';

                    if (isMobile()) {
                        // On mobile, opening one closes others.
                        items.forEach(otherItem => {
                            if (otherItem !== item) {
                                const otherHeader = otherItem.querySelector('.accordion-header');
                                const otherContent = otherItem.querySelector('.accordion-content');
                                otherHeader.setAttribute('aria-expanded', 'false');
                                otherContent.style.gridTemplateRows = '0fr';
                                otherContent.setAttribute('aria-hidden', 'true');
                            }
                        });
                    }

                    // Toggle the clicked accordion
                    header.setAttribute('aria-expanded', !isExpanded);
                    content.style.gridTemplateRows = !isExpanded ? '1fr' : '0fr';
                    content.setAttribute('aria-hidden', isExpanded);
                });

                // Keyboard accessibility for header
                if (!header.hasAttribute('tabindex')) {
                    header.setAttribute('tabindex', '0');
                }
                header.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        header.click();
                    }
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
