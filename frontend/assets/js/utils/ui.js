/**
 * UI Initialization utilities
 */

function initMobileNav() {
    const toggleBtn = document.getElementById('mobile-nav-toggle');
    const mainNav = document.getElementById('main-nav');

    let navOverlay = document.querySelector('.nav-overlay');
    if (!navOverlay) {
        navOverlay = document.createElement('div');
        navOverlay.className = 'nav-overlay';
        document.body.appendChild(navOverlay);
    }

    if (!toggleBtn || !mainNav) return;

    let previouslyFocusedElement = null;

    const getFocusables = () => {
        return Array.from(mainNav.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'));
    };

    const updateAria = () => {
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            const isOpen = document.body.classList.contains('nav-open');
            mainNav.setAttribute('aria-hidden', String(!isOpen));
        } else {
            mainNav.removeAttribute('aria-hidden');
        }
    };

    const newBtn = toggleBtn.cloneNode(true);
    toggleBtn.parentNode.replaceChild(newBtn, toggleBtn);

    const toggleNav = (open) => {
        const shouldOpen = typeof open === 'boolean' ? open : !document.body.classList.contains('nav-open');
        document.body.classList.toggle('nav-open', shouldOpen);
        newBtn.setAttribute('aria-expanded', String(shouldOpen));
        document.body.style.overflow = shouldOpen ? 'hidden' : '';

        if (shouldOpen) {
            previouslyFocusedElement = document.activeElement;
            mainNav.setAttribute('aria-hidden', 'false');
            const focusables = getFocusables();
            if (focusables.length > 0) {
                setTimeout(() => focusables[0].focus(), 50);
            }
        } else {
            updateAria();
            if (previouslyFocusedElement && typeof previouslyFocusedElement.focus === 'function') {
                previouslyFocusedElement.focus();
            } else {
                newBtn.focus();
            }
        }
    };

    newBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleNav();
    });

    navOverlay.addEventListener('click', () => toggleNav(false));

    mainNav.addEventListener('click', (e) => {
        if (e.target.closest('.nav-link')) {
            if (document.body.classList.contains('nav-open')) toggleNav(false);
        }
    });

    document.addEventListener('keydown', (e) => {
        if (!document.body.classList.contains('nav-open')) return;

        if (e.key === 'Escape') {
            e.preventDefault();
            toggleNav(false);
            return;
        }

        if (e.key === 'Tab') {
            const focusables = getFocusables();
            if (focusables.length === 0) return;

            const first = focusables[0];
            const last = focusables[focusables.length - 1];

            if (e.shiftKey) {
                if (document.activeElement === first || !mainNav.contains(document.activeElement)) {
                    e.preventDefault();
                    last.focus();
                }
            } else {
                if (document.activeElement === last || !mainNav.contains(document.activeElement)) {
                    e.preventDefault();
                    first.focus();
                }
            }
        }
    });

    window.addEventListener('resize', updateAria);
    updateAria();
}

function initTheme() {
    const themeSwitcher = document.getElementById('theme-switcher');
    if (!themeSwitcher) return;

    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    let currentTheme = localStorage.getItem('theme');
    let userOverride = localStorage.getItem('theme-user-override') === 'true';

    const setTheme = (theme, animate = false, isUserAction = false) => {
        if (animate) {
            document.body.style.transition = 'background-color var(--transition-base), color var(--transition-base)';
        } else {
            document.body.style.transition = 'none';
        }
        document.body.classList.toggle('dark', theme === 'dark');
        localStorage.setItem('theme', theme);

        // Track if user manually set the theme
        if (isUserAction) {
            localStorage.setItem('theme-user-override', 'true');
            userOverride = true;
        }

        window.dispatchEvent(new CustomEvent('themechanged', { detail: { theme } }));

        if (!animate) {
            void document.body.offsetWidth;
            document.body.style.transition = '';
        }
    };

    // Default to system preference if no theme stored
    if (!currentTheme) {
        currentTheme = prefersDark.matches ? 'dark' : 'light';
        userOverride = false; // Not a user override, system default
    }
    setTheme(currentTheme);

    const newSwitcher = themeSwitcher.cloneNode(true);
    themeSwitcher.parentNode.replaceChild(newSwitcher, themeSwitcher);

    newSwitcher.addEventListener('click', () => {
        const newTheme = document.body.classList.contains('dark') ? 'light' : 'dark';
        setTheme(newTheme, true, true); // Mark as user action
    });

    // Only auto-update with system preference if user hasn't manually overridden
    if (!window._themeListenerAdded) {
        prefersDark.addEventListener('change', (e) => {
            if (!userOverride) {
                // Only auto-update if user hasn't manually set a preference
                setTheme(e.matches ? 'dark' : 'light', true, false);
            }
        });
        window._themeListenerAdded = true;
    }
}

function updateFreshnessColor(date) {
    const diffHours = (new Date() - date) / (1000 * 60 * 60);
    const footerUpdate = document.getElementById('footerUpdate');
    if (!footerUpdate) return;

    let color = '#22c55e'; // Green
    if (diffHours > 8) color = '#eab308'; // Yellow
    if (diffHours > 24) color = '#ef4444'; // Red

    footerUpdate.style.color = color;
    footerUpdate.style.fontWeight = 'bold';
}
