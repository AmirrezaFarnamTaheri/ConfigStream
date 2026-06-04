// Wiki Loader Script

const WIKI_PAGES = [
    { id: 'Home', title: 'wiki.nav.home', defaultTitle: 'Wiki Home', file: 'Home.md' },
    { id: 'intro', title: 'wiki.nav.intro', defaultTitle: 'Introduction', file: '01-introduction.md' },
    { id: 'arch', title: 'wiki.nav.arch', defaultTitle: 'Architecture', file: '02-architecture.md' },
    { id: 'proto', title: 'wiki.nav.proto', defaultTitle: 'Protocols', file: '03-protocols.md' },
    { id: 'eng', title: 'wiki.nav.eng', defaultTitle: 'Engineering', file: '04-engineering.md' },
    { id: 'devops', title: 'wiki.nav.devops', defaultTitle: 'DevOps', file: '05-devops.md' },
    { id: 'frontend', title: 'wiki.nav.frontend', defaultTitle: 'Frontend', file: '06-frontend.md' },
    { id: 'security', title: 'wiki.nav.security', defaultTitle: 'Security', file: '07-security.md' },
    { id: 'api', title: 'wiki.nav.api', defaultTitle: 'API Reference', file: '08-api-reference.md' },
    { id: 'contributing', title: 'wiki.nav.contributing', defaultTitle: 'Contributing', file: '09-contributing.md' },
    { id: 'troubleshooting', title: 'wiki.nav.troubleshooting', defaultTitle: 'Troubleshooting', file: '10-troubleshooting.md' },
    { id: 'home_page', title: 'wiki.nav.page_home', defaultTitle: 'Page: Home', file: 'Home_Page.md' },
    { id: 'analytics_page', title: 'wiki.nav.page_analytics', defaultTitle: 'Page: Analytics', file: 'Analytics_Page.md' },
    { id: 'proxies_page', title: 'wiki.nav.page_proxies', defaultTitle: 'Page: Proxies', file: 'Proxies_Page.md' },
    { id: 'about_page', title: 'wiki.nav.page_about', defaultTitle: 'Page: About', file: 'About_Page.md' }
];

document.addEventListener('DOMContentLoaded', () => {
    initSidebar();

    // Handle hash changes to load pages
    window.addEventListener('hashchange', loadFromHash);

    // Listen for language changes to update sidebar titles
    window.addEventListener('languageChanged', () => {
        initSidebar();
        // Also re-highlight active
        const hash = window.location.hash.substring(1) || 'Home';
        const page = WIKI_PAGES.find(p => p.id === hash) || WIKI_PAGES[0];
        const activeNav = document.getElementById(`nav-${page.id}`);
        if (activeNav) activeNav.classList.add('active');
    });

    // Initial load
    loadFromHash();
});

function initSidebar() {
    const sidebar = document.getElementById('wikiSidebar');
    if (!sidebar) return;

    // Preserve active state if rebuilding
    const currentHash = window.location.hash.substring(1) || 'Home';

    sidebar.innerHTML = '';

    WIKI_PAGES.forEach(page => {
        const link = document.createElement('a');
        link.className = 'wiki-nav-item';

        // Use i18n if available, otherwise default
        let displayTitle = page.defaultTitle;
        if (window.i18n && window.i18n.t) {
            const translated = window.i18n.t(page.title);
            if (translated !== page.title) {
                displayTitle = translated;
            }
        }

        link.innerText = displayTitle;
        link.href = `#${page.id}`;
        link.id = `nav-${page.id}`;
        if (page.id === currentHash) {
            link.classList.add('active');
        }
        sidebar.appendChild(link);
    });
}

async function loadFromHash() {
    const hash = window.location.hash.substring(1) || 'Home';
    const page = WIKI_PAGES.find(p => p.id === hash) || WIKI_PAGES[0];

    // Update Active State
    document.querySelectorAll('.wiki-nav-item').forEach(el => el.classList.remove('active'));
    const activeNav = document.getElementById(`nav-${page.id}`);
    if (activeNav) activeNav.classList.add('active');

    // Scroll sidebar to active item on mobile/small screens
    if (activeNav && window.innerWidth < 900) {
        activeNav.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
    }

    await renderPage(page.file);
}

async function renderPage(filename) {
    const container = document.getElementById('wikiRenderer');
    if (!container) return;

    // Loading state
    container.replaceChildren();
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-spinner';
    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    const loadingText = document.createElement('p');
    loadingText.style.marginLeft = '10px';
    loadingText.textContent = 'Loading content...';
    loadingDiv.appendChild(spinner);
    loadingDiv.appendChild(loadingText);
    container.appendChild(loadingDiv);

    try {
        // Strategy:
        // Prefer same-origin wiki files so the page remains usable when external
        // network access is blocked. Remote GitHub fallbacks are deliberately
        // avoided for local-first production behavior.

        let content = '';
        let success = false;
        let lastError = null;

        const strategies = [
            // GitHub Pages artifact layout (deploy-pages copies frontend/ into output/):
            //   wiki.html lives at site root and wiki markdown is under docs/wiki/project/
            `docs/wiki/project/${filename}`,
            // Local dev: opening frontend/wiki.html directly
            `../docs/wiki/project/${filename}`,
            // Alternative layouts (if a wiki/ folder exists next to wiki.html)
            `wiki/${filename}`,
            `${filename}`,
        ];

        for (const url of strategies) {
            try {
                console.debug(`[Wiki] Trying to fetch: ${url}`);
                const response = await fetch(url, { cache: 'no-cache' }); // Avoid stale content
                if (response.ok) {
                    content = await response.text();

                    // Basic validation: ensure it looks like markdown or text, not HTML 404 page
                    if (content.trim().toLowerCase().startsWith('<!doctype html')) {
                         console.warn(`[Wiki] Fetched HTML instead of Markdown from ${url} (Soft 404)`);
                         continue;
                    }

                    success = true;
                    console.debug(`[Wiki] Successfully loaded from ${url}`);
                    break;
                }
            } catch (e) {
                console.warn(`[Wiki] Failed to fetch from ${url}: ${e.message}`);
                lastError = e;
            }
        }

        if (!success) {
            throw new Error('Could not load wiki page from any source. Please check your network connection.');
        }

        // Parse Markdown
        if (typeof marked !== 'undefined') {
            // Configure marked for security
            // marked.use({ ... }) if needed

            const html = marked.parse(content);

            // Sanitize with strengthened fallback
            let sanitized;
            if (window.DOMPurify) {
                sanitized = window.DOMPurify.sanitize(html, {
                     ADD_ATTR: ['target', 'rel'],
                     FORBID_TAGS: ['script', 'object', 'embed', 'applet', 'iframe', 'form'],
                     FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover']
                });
                container.innerHTML = sanitized; // Sanitized by DOMPurify
            } else {
                // CRITICAL: If DOMPurify fails, render as plain text
                console.error("[Wiki] DOMPurify not loaded - rendering as plain text for security");
                container.replaceChildren();
                
                const warnDiv = document.createElement('div');
                warnDiv.className = 'warning-state';
                warnDiv.style.padding = '20px';
                warnDiv.style.background = '#fff3cd';
                warnDiv.style.color = '#856404';
                warnDiv.style.borderRadius = '8px';
                warnDiv.style.marginBottom = '20px';
                
                const warnStrong = document.createElement('strong');
                warnStrong.textContent = '⚠️ Security Warning: ';
                warnDiv.appendChild(warnStrong);
                warnDiv.appendChild(document.createTextNode('DOMPurify library failed to load. Content is displayed as plain text to prevent XSS vulnerabilities.'));
                
                const pre = document.createElement('pre');
                pre.style.whiteSpace = 'pre-wrap';
                pre.style.background = '#f5f5f5';
                pre.style.padding = '15px';
                pre.style.borderRadius = '4px';
                pre.textContent = content;
                
                container.appendChild(warnDiv);
                container.appendChild(pre);
                return; 
            }

            // Post-processing: Make links open in new tab if external
            container.querySelectorAll('a').forEach(link => {
                if (link.hostname !== window.location.hostname) {
                    link.setAttribute('target', '_blank');
                    link.setAttribute('rel', 'noopener noreferrer');
                }
            });

        } else {
            // Fallback if marked is missing (e.g., CDN blocked)
            container.replaceChildren();
            const warnDiv = document.createElement('div');
            warnDiv.className = 'warning-state';
            warnDiv.style.padding = '20px';
            warnDiv.style.background = '#fff3cd';
            warnDiv.style.color = '#856404';
            warnDiv.style.borderRadius = '8px';
            
            const warnStrong = document.createElement('strong');
            warnStrong.textContent = 'Markdown Parser Missing: ';
            warnDiv.appendChild(warnStrong);
            warnDiv.appendChild(document.createTextNode('The content below is raw Markdown.'));
            
            const pre = document.createElement('pre');
            pre.style.whiteSpace = 'pre-wrap';
            pre.textContent = content;
            
            container.appendChild(warnDiv);
            container.appendChild(pre);
            console.warn("marked library not loaded");
        }

        // Highlight code blocks if any
        if (window.hljs) {
             container.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        }

    } catch (error) {
        container.replaceChildren();
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-state';
        
        const h3 = document.createElement('h3');
        h3.textContent = 'Error Loading Documentation';
        
        const p1 = document.createElement('p');
        p1.textContent = `Could not fetch ${filename}.`;
        
        const p2 = document.createElement('p');
        p2.className = 'error-detail';
        p2.textContent = error.message;
        
        const btn = document.createElement('button');
        btn.className = 'btn btn-secondary';
        btn.style.marginTop = '10px';
        btn.textContent = 'Retry';
        btn.onclick = () => location.reload();
        
        errorDiv.appendChild(h3);
        errorDiv.appendChild(p1);
        errorDiv.appendChild(p2);
        errorDiv.appendChild(btn);
        
        container.appendChild(errorDiv);
        console.error("Wiki load error:", error);
    }
}
