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

    const toggleNav = () => {
        const isNavOpen = document.body.classList.toggle('nav-open');
        toggleBtn.setAttribute('aria-expanded', isNavOpen);
        document.body.style.overflow = isNavOpen ? 'hidden' : '';
    };

    const newBtn = toggleBtn.cloneNode(true);
    toggleBtn.parentNode.replaceChild(newBtn, toggleBtn);

    newBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleNav();
    });

    navOverlay.addEventListener('click', toggleNav);

    mainNav.addEventListener('click', (e) => {
        if (e.target.classList.contains('nav-link')) {
            if (document.body.classList.contains('nav-open')) toggleNav();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && document.body.classList.contains('nav-open')) toggleNav();
    });
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
