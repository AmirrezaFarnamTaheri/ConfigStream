// Boot script: establishes the site root for asset/data path resolution.
// Loaded first on every page so downstream modules (init.js, analytics.js,
// lab/*, charts.js, ...) can resolve relative resources consistently.
// Kept external (rather than inline) so the page CSP can enforce
// script-src 'self' without 'unsafe-inline'.
window.ROOT_PATH = './';
