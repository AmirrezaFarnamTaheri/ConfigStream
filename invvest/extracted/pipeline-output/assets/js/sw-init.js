if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        const logger = window.createLogger ? window.createLogger('ServiceWorker') : console;
        // Fixed path to sw.js
        navigator.serviceWorker.register('service-worker.js')
            .then(reg => {
                logger.info('SW registered: ', reg);
            })
            .catch(err => {
                logger.error('SW registration failed: ', err);
            });
    });
}

// Listen for language changes to update UI label
window.addEventListener('languageChanged', (e) => {
        const lang = e.detail?.lang;
        const label = document.getElementById('current-lang-label');
        if(label && lang) {
        label.textContent = lang.toUpperCase();
        }
});

// Initial set label
document.addEventListener('DOMContentLoaded', () => {
        const label = document.getElementById('current-lang-label');
        if(label && window.i18n) label.textContent = window.i18n.currentLang.toUpperCase();
});
