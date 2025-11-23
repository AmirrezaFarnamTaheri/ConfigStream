// Wiki Loader Script

const WIKI_BASE_URL = 'https://raw.githubusercontent.com/yebekhe/ConfigStream/main/docs/wiki/';
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
    container.innerHTML = '<div class="loading-spinner">Loading...</div>';

    try {
        // Try fetching from potential locations (Raw GitHub or Local)
        // In a real deployment, these MD files might be copied to a specific folder during build
        // For now, we try a relative path assuming standard deployment structure or the raw GitHub URL as fallback

        let content = '';

        // Strategy: Try relative 'wiki/' path first (if copied by build), then raw GitHub
        // Since we can't guarantee the build process copies them yet, I'll assume they are accessible via raw URL
        // OR we need to ensure the build process copies `docs/wiki` to `output/wiki` or `frontend/wiki`.

        // For this implementation, I'll try to fetch from a local path relative to the HTML
        // assuming the user will instruct the build to copy them, or I will add that to the build plan.
        // Let's try a common convention: /wiki/filename

        const responses = await Promise.allSettled([
            fetch(`wiki/${filename}`), // Production (if copied)
            fetch(WIKI_BASE_URL + filename), // Fallback
            fetch(`../docs/wiki/${filename}`) // Local Dev
        ]);

        const successful = responses.find(r => r.status === 'fulfilled' && r.value.ok);

        if (!successful) {
            throw new Error('Could not load wiki page');
        }

        content = await successful.value.text();

        // Parse Markdown
        const html = marked.parse(content);
        const sanitized = DOMPurify.sanitize(html);
        container.innerHTML = sanitized;

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
