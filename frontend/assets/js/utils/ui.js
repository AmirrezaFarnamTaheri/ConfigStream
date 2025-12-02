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

    const setTheme = (theme, animate = false) => {
        if (animate) {
            document.body.style.transition = 'background-color var(--transition-base), color var(--transition-base)';
        } else {
            document.body.style.transition = 'none';
        }
        document.body.classList.toggle('dark', theme === 'dark');
        localStorage.setItem('theme', theme);

        window.dispatchEvent(new CustomEvent('themechanged', { detail: { theme } }));

        if (!animate) {
            void document.body.offsetWidth;
            document.body.style.transition = '';
        }
    };

    if (!currentTheme) currentTheme = prefersDark.matches ? 'dark' : 'light';
    setTheme(currentTheme);

    const newSwitcher = themeSwitcher.cloneNode(true);
    themeSwitcher.parentNode.replaceChild(newSwitcher, themeSwitcher);

    newSwitcher.addEventListener('click', () => {
        const newTheme = document.body.classList.contains('dark') ? 'light' : 'dark';
        setTheme(newTheme, true);
    });

    if (!window._themeListenerAdded) {
        prefersDark.addEventListener('change', (e) => {
            setTheme(e.matches ? 'dark' : 'light', true);
        });
        window._themeListenerAdded = true;
    }
}
