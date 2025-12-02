/**
 * Common UI logic shared across all pages
 * Handles: Header Scroll, Mobile Nav, Theme Switcher, Copy Buttons, Inline Icons
 */

// Immediate fix for "White Page" issue: Remove no-js class as soon as script runs
document.documentElement.classList.remove('no-js');

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
