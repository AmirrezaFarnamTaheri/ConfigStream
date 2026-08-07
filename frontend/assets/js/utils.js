/**
 * Utils Wrapper
 * Connects the split utility modules to the global window.api
 */

window.api = {
  fetchProxies: typeof fetchProxies !== 'undefined' ? fetchProxies : null,
  fetchMetadata: typeof fetchMetadata !== 'undefined' ? fetchMetadata : null,
  fetchStatistics: typeof fetchStatistics !== 'undefined' ? fetchStatistics : null,
  fetchVerifiedArtifactJson: typeof fetchVerifiedArtifactJson !== 'undefined' ? fetchVerifiedArtifactJson : null,
  requireVerifiedArtifact: typeof requireVerifiedArtifact !== 'undefined' ? requireVerifiedArtifact : null,
  clearCache: typeof clearCache !== 'undefined' ? clearCache : null,
  initMobileNav: typeof initMobileNav !== 'undefined' ? initMobileNav : null,
  initTheme: typeof initTheme !== 'undefined' ? initTheme : null,
  updateFreshnessColor: typeof updateFreshnessColor !== 'undefined' ? updateFreshnessColor : null
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {};
}

if (typeof window !== 'undefined') {
    window.api = window.api || {};

    if (typeof fetchProxies === 'function') window.api.fetchProxies = fetchProxies;
    if (typeof fetchMetadata === 'function') window.api.fetchMetadata = fetchMetadata;
    if (typeof fetchStatistics === 'function') window.api.fetchStatistics = fetchStatistics;
    if (typeof fetchVerifiedArtifactJson === 'function') window.api.fetchVerifiedArtifactJson = fetchVerifiedArtifactJson;
    if (typeof requireVerifiedArtifact === 'function') window.api.requireVerifiedArtifact = requireVerifiedArtifact;
    if (typeof clearCache === 'function') window.api.clearCache = clearCache;
    if (typeof initMobileNav === 'function') window.api.initMobileNav = initMobileNav;
    if (typeof initTheme === 'function') window.api.initTheme = initTheme;
    if (typeof updateFreshnessColor === 'function') window.api.updateFreshnessColor = updateFreshnessColor;
}
