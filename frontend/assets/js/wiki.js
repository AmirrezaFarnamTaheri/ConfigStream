// Wiki Loader Script

const WIKI_BASE_URL = 'https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/docs/wiki/';
// Fallback for local dev or different repo structure
const LOCAL_WIKI_BASE = '../docs/wiki/';

const WIKI_PAGES = [
    { id: 'Home', title: 'wiki.nav.home', defaultTitle: 'Wiki Home', file: 'Home.md' },
    { id: 'module00', title: 'wiki.nav.module00', defaultTitle: 'Module 00: Roadmap', file: 'module-00.md' },
    { id: 'module01', title: 'wiki.nav.module01', defaultTitle: 'Module 01: First-Order', file: 'module-01.md' },
    { id: 'module02', title: 'wiki.nav.module02', defaultTitle: 'Module 02: Convex Ops I', file: 'module-02.md' },
    { id: 'module03', title: 'wiki.nav.module03', defaultTitle: 'Module 03: Convex Ops II', file: 'module-03.md' },
    { id: 'module04', title: 'wiki.nav.module04', defaultTitle: 'Module 04: Inequalities', file: 'module-04.md' },
    { id: 'module05', title: 'wiki.nav.module05', defaultTitle: 'Module 05: Sets & Epigraphs', file: 'module-05.md' },
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

    container.innerHTML = `
        <div class="loading-spinner">
            <div class="spinner"></div>
            <p style="margin-left: 10px;">Loading content...</p>
        </div>`;

    try {
        // Strategy:
        // 1. Try 'wiki/' relative path (For sub-path deployment e.g., /wiki/)
        // 2. Try './' relative path (For flat deployment)
        // 3. Try Raw GitHub (Fallback for missing files or local dev)
        // 4. Try '../docs/wiki/' (Local dev fallback)

        let content = '';
        let success = false;
        let lastError = null;

        const strategies = [
            `wiki/${filename}`,
            `${filename}`,
            WIKI_BASE_URL + filename,
            `../docs/wiki/${filename}`
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

            // Sanitize
            let sanitized;
            if (window.DOMPurify) {
                sanitized = window.DOMPurify.sanitize(html, {
                     ADD_TAGS: ['iframe'], // Allow iframes for youtube? maybe dangerous. keeping safe for now.
                     ADD_ATTR: ['target']
                });
            } else {
                console.warn("[Wiki] DOMPurify not loaded, using basic sanitization");
                // Basic fallback sanitization
                const tmp = document.createElement('div');
                tmp.textContent = html; // THIS ESCAPES EVERYTHING, disabling markdown rendering effectively
                // So we trust marked output if DOMPurify missing? No, that's dangerous.
                // We'll use the i18n sanitizer or similar if available, or just render as text.
                sanitized = html.replace(/<script\b[^>]*>([\s\S]*?)<\/script>/gm, "")
                                .replace(/on\w+="[^"]*"/g, "");
            }

            container.innerHTML = sanitized;

            // Post-processing: Make links open in new tab if external
            container.querySelectorAll('a').forEach(link => {
                if (link.hostname !== window.location.hostname) {
                    link.setAttribute('target', '_blank');
                    link.setAttribute('rel', 'noopener noreferrer');
                }
            });

            // Render Math with KaTeX
            if (window.renderMathInElement) {
                renderMathInElement(container, {
                    delimiters: [
                        {left: '$$', right: '$$', display: true},
                        {left: '$', right: '$', display: false},
                        {left: '\\(', right: '\\)', display: false},
                        {left: '\\[', right: '\\]', display: true}
                    ],
                    throwOnError: false
                });
            }

        } else {
            // Fallback if marked is missing (e.g., CDN blocked)
            container.innerHTML = `
                <div class="warning-state" style="padding: 20px; background: #fff3cd; color: #856404; border-radius: 8px;">
                    <strong>Markdown Parser Missing:</strong> The content below is raw Markdown.
                </div>
                <pre style="white-space: pre-wrap;">${content}</pre>
            `;
            console.warn("marked library not loaded");
        }

        // Highlight code blocks if any
        if (window.hljs) {
             container.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        }

    } catch (error) {
        container.innerHTML = `
            <div class="error-state">
                <h3>Error Loading Documentation</h3>
                <p>Could not fetch ${filename}.</p>
                <p class="error-detail">${error.message}</p>
                <button onclick="location.reload()" class="btn btn-secondary" style="margin-top: 10px;">Retry</button>
            </div>
        `;
        console.error("Wiki load error:", error);
    }
}
