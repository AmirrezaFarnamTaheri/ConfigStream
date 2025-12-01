// Wiki Loader Script

const WIKI_BASE_URL = 'https://raw.githubusercontent.com/AmirrezaFarnamTaheri/ConfigStream/main/docs/wiki/';
// Fallback for local dev or different repo structure
const LOCAL_WIKI_BASE = '../docs/wiki/';

const WIKI_PAGES = [
    { id: 'Home', title: 'Wiki Home', file: 'Home.md' },
    { id: 'intro', title: 'Introduction', file: '01-introduction.md' },
    { id: 'arch', title: 'Architecture', file: '02-architecture.md' },
    { id: 'proto', title: 'Protocols', file: '03-protocols.md' },
    { id: 'eng', title: 'Engineering', file: '04-engineering.md' },
    { id: 'devops', title: 'DevOps', file: '05-devops.md' },
    { id: 'frontend', title: 'Frontend', file: '06-frontend.md' },
    { id: 'security', title: 'Security', file: '07-security.md' },
    { id: 'api', title: 'API Reference', file: '08-api-reference.md' },
    { id: 'contributing', title: 'Contributing', file: '09-contributing.md' },
    { id: 'troubleshooting', title: 'Troubleshooting', file: '10-troubleshooting.md' },
    { id: 'home_page', title: 'Page: Home', file: 'Home_Page.md' },
    { id: 'analytics_page', title: 'Page: Analytics', file: 'Analytics_Page.md' },
    { id: 'proxies_page', title: 'Page: Proxies', file: 'Proxies_Page.md' },
    { id: 'about_page', title: 'Page: About', file: 'About_Page.md' }
];

document.addEventListener('DOMContentLoaded', () => {
    initSidebar();

    // Handle hash changes to load pages
    window.addEventListener('hashchange', loadFromHash);

    // Initial load
    loadFromHash();
});

function initSidebar() {
    const sidebar = document.getElementById('wikiSidebar');
    if (!sidebar) return;
    sidebar.innerHTML = '';

    WIKI_PAGES.forEach(page => {
        const link = document.createElement('a');
        link.className = 'wiki-nav-item';
        link.innerText = page.title;
        link.href = `#${page.id}`;
        link.id = `nav-${page.id}`;
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

    await renderPage(page.file);
}

async function renderPage(filename) {
    const container = document.getElementById('wikiRenderer');
    if (!container) return;

    container.innerHTML = '<div class="loading-spinner">Loading...</div>';

    try {
        // Strategy:
        // 1. Try fetching from 'wiki/' relative path (Production, served from output/wiki)
        // 2. Try fetching from './' relative path (If served from output/wiki/index.html)
        // 3. Try fetching from raw GitHub (Fallback)
        // 4. Try fetching from local docs folder (Local Dev)

        // Note: fetch will succeed even on 404, so we must check response.ok

        let content = '';
        let success = false;

        const strategies = [
            `wiki/${filename}`,
            `${filename}`, // For /wiki/ context
            WIKI_BASE_URL + filename,
            `../docs/wiki/${filename}`
        ];

        for (const url of strategies) {
            try {
                const response = await fetch(url);
                if (response.ok) {
                    content = await response.text();
                    success = true;
                    break;
                }
            } catch (e) {
                // Continue to next strategy
            }
        }

        if (!success) {
            throw new Error('Could not load wiki page from any source.');
        }

        // Parse Markdown
        // Check for marked library
        if (typeof marked !== 'undefined') {
            const html = marked.parse(content);
            const sanitized = window.DOMPurify ? window.DOMPurify.sanitize(html) : html;
            container.innerHTML = sanitized;
        } else {
            container.innerText = content; // Fallback text only
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
                <p>Could not fetch ${filename}. Please check your connection or try again later.</p>
                <pre>${error.message}</pre>
            </div>
        `;
    }
}
