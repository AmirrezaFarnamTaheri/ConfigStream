// --- 5-STATE TRUST UI CONTRACT & PROVENANCE BANNER ---
export function applyTrustState(state, metadata, options = {}) {
    let banner = document.getElementById('trustStateBanner');
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'trustStateBanner';
        banner.setAttribute('role', 'alert');
        banner.setAttribute('aria-live', 'polite');
        banner.style.cssText = 'position:sticky;top:0;z-index:9999;padding:0.65rem 1rem;text-align:center;font:600 0.875rem/1.4 system-ui,sans-serif;display:none;';
        const main = document.querySelector('main') || document.body;
        if (main && main.firstChild) {
            main.insertBefore(banner, main.firstChild);
        } else if (main) {
            main.appendChild(banner);
        }
    }

    banner.className = `trust-banner trust-banner--${state}`;

    if (state === 'stale') {
        const genTime = metadata?.last_updated_utc ? new Date(metadata.last_updated_utc).toISOString() : (metadata?.generated_at || 'Unknown');
        banner.textContent = `Warning: Showing cached telemetry generated at ${genTime}.`;
        banner.style.background = '#d97706';
        banner.style.color = '#fff';
        banner.style.display = 'block';
    } else if (state === 'invalid') {
        banner.textContent = 'Security Alert: Detached cryptographic verification failed. Feeds blocked.';
        banner.style.background = '#dc2626';
        banner.style.color = '#fff';
        banner.style.display = 'block';
    } else if (state === 'error' || state === 'empty') {
        banner.replaceChildren();
        const msg = document.createElement('span');
        msg.textContent = options.errorMessage || (state === 'empty' ? 'No telemetry data available.' : 'Failed to initialize page data.');
        banner.appendChild(msg);

        if (typeof options.onRetry === 'function') {
            const retryBtn = document.createElement('button');
            retryBtn.className = 'btn btn-secondary trust-banner-retry';
            retryBtn.style.cssText = 'margin-left:12px;padding:2px 8px;font-size:0.8rem;cursor:pointer;';
            retryBtn.textContent = 'Retry';
            retryBtn.addEventListener('click', (e) => {
                e.preventDefault();
                options.onRetry();
            });
            banner.appendChild(retryBtn);
        }
        banner.style.background = '#4b5563';
        banner.style.color = '#fff';
        banner.style.display = 'block';
    } else if (state === 'loading') {
        banner.style.display = 'none';
    } else { // 'fresh'
        banner.style.display = 'none';
    }
}

export async function initializePageData() {
    const preloader = document.getElementById('preloader');
    const logo = document.querySelector('.logo-svg');

    if (!window.stateManager) {
        logger.error("StateManager not found!");
        if (preloader) {
            preloader.classList.add('hidden');
            document.body.classList.add('loaded');
        }
        return;
    }
    window.stateManager.setLoading(true, 'Fetching latest data...');
    applyTrustState('loading');

    let sourceCount = null;
    let updateFreq = null;

    const updateHeroSubtitle = () => {
         const heroSubtitle = document.getElementById('heroSubtitle');
         const formatNum = (num) => {
             if (num === undefined || num === null) return 'N/A';
             return window.i18n && window.i18n.formatNumber ? window.i18n.formatNumber(num) : num;
         };

         if (heroSubtitle && window.i18n) {
             let text = window.i18n.t('hero.subtitle.main');
             text = text.replace('{sources}', formatNum(sourceCount));
             text = text.replace('{hours}', formatNum(updateFreq));
            if (window.DOMPurify) {
                const fragment = window.DOMPurify.sanitize(text, {
                    ALLOWED_TAGS: ['strong', 'em', 'b', 'i', 'span'],
                    RETURN_DOM_FRAGMENT: true
                });
                if (fragment && typeof fragment.nodeType === 'number') {
                    heroSubtitle.replaceChildren(fragment);
                } else {
                    heroSubtitle.textContent = String(fragment || '').replace(/<[^>]*>/g, '');
                }
            } else {
                heroSubtitle.textContent = text.replace(/<[^>]*>/g, '');
            }
         }
    };

    updateHeroSubtitle();
    window.addEventListener('languageChanged', updateHeroSubtitle);
    if (window.i18n && typeof window.i18n.init === 'function') {
        window.i18n.init().then(updateHeroSubtitle).catch(() => {});
    }

    try {
        if (!window.api || typeof window.api.requireVerifiedArtifact !== 'function') {
            throw new Error('Artifact verification API is unavailable');
        }
        await window.api.requireVerifiedArtifact();

        const [metadata, stats] = await Promise.all([
            window.api.fetchMetadata(),
            window.api.fetchStatistics()
        ]);
        window.CONFIGSTREAM_PROXY_SNAPSHOT_HASH = metadata?.proxies_snapshot_hash || null;

        if (metadata && metadata.protocol_colors) {
            window.PROTOCOL_COLORS = metadata.protocol_colors;
        }

        // Truthful freshness evaluation strictly referencing metadata.last_updated_utc
        if (metadata && (metadata.last_updated_utc || metadata.generated_at)) {
            const rawDate = metadata.last_updated_utc || metadata.generated_at;
            const date = new Date(rawDate);
            const intervalHours = Number(metadata.update_interval_hours || stats?.update_interval_hours || 6);
            const maxAgeHours = Math.min(48, Math.max(12, intervalHours * 2));
            const ageMs = Date.now() - date.getTime();
            const isStale = Number.isNaN(date.getTime()) || (ageMs > maxAgeHours * 60 * 60 * 1000);

            if (isStale) {
                applyTrustState('stale', metadata);
            } else {
                applyTrustState('fresh', metadata);
            }

            const formatted = formatTimestamp(date);
            updateElement('#footerUpdate', formatted);

            if (window.api && window.api.updateFreshnessColor) {
                window.api.updateFreshnessColor(date);
            }

            window._freshnessDate = date;
            updateFreshnessIndicator(date);

            // Start periodic freshness updates now that we have initial data
            if (!window._freshnessIntervalStarted) {
                window._freshnessIntervalStarted = true;
                setInterval(() => {
                    if (window._freshnessDate) {
                        updateFreshnessIndicator(window._freshnessDate);
                    }
                }, 60000);
            }
        } else {
            applyTrustState('stale', metadata);
        }

        if (stats) {
            const formatNum = (num) => {
                if (num === undefined || num === null) return 'N/A';
                return window.i18n && window.i18n.formatNumber ? window.i18n.formatNumber(num) : num;
            };

            const totalSourced = stats.total_lines_sourced;
            updateElement('#totalSourced', formatNum(totalSourced));

            const totalConfigs = stats.total_unique_candidates;
            updateElement('#totalConfigs', formatNum(totalConfigs));

            const workingCount = stats.total_working ?? stats.total_valid_proxies ?? stats.working ?? 0;
            updateElement('#workingConfigs', formatNum(workingCount));

            const revivedWarp = stats.revived_warp || 0;
            const revivedVwarp = stats.revived_vwarp || 0;
            const totalRevived = stats.total_revived ?? (revivedWarp + revivedVwarp);
            updateElement('#totalRevived', formatNum(totalRevived));
            updateElement('#revivedWarp', formatNum(revivedWarp));
            updateElement('#revivedVwarp', formatNum(revivedVwarp));

            const threatsBlocked = stats.total_dirty;
            updateElement('#threatsBlocked', formatNum(threatsBlocked));

            const smartChains = stats.total_smart_chains;
            updateElement('#smartChains', formatNum(smartChains));

            const vwarpWinRate = stats.vwarp_win_rate;
            const washingEnabled = stats.washing_enabled;
            const winRateDisplay = (washingEnabled !== false && vwarpWinRate !== undefined) ? `${Math.round(vwarpWinRate)}%` : 'N/A';
            updateElement('#vwarpWinRate', winRateDisplay);

            const winRateElem = document.querySelector('#vwarpWinRate');
            if (winRateElem && washingEnabled === false) {
                 winRateElem.setAttribute('title', 'Washing disabled (no keys provided)');
                 winRateElem.style.opacity = '0.7';
            }

            updateFreq = metadata?.update_interval_hours || stats.update_interval_hours || 6;
            updateElement('#updateFrequency', `${updateFreq} hrs`);

            sourceCount = metadata?.sources_count || stats.sources_count || 0;
            updateHeroSubtitle();

            const infoSourceCountElem = document.getElementById('infoSourceCount');
            if (infoSourceCountElem) {
                infoSourceCountElem.textContent = formatNum(sourceCount);
            }

            const infoUpdateFreqElem = document.getElementById('infoUpdateFrequency');
            if (infoUpdateFreqElem) {
                infoUpdateFreqElem.textContent = formatNum(updateFreq);
            }
        }

    } catch (error) {
        const errorMsg = error?.message || String(error);
        const isSecurity = /verification|signature|digest|manifest|blocked|tamper|cryptographic/i.test(errorMsg);

        if (isSecurity) {
            applyTrustState('invalid', null, {
                errorMessage: 'Security Alert: Detached cryptographic verification failed. Feeds blocked.',
                onRetry: () => initializePageData()
            });
            logger.error('Security alert - verification failed:', error);
        } else {
            applyTrustState('error', null, {
                errorMessage: `Failed to initialize page data: ${errorMsg}`,
                onRetry: () => initializePageData()
            });
            logger.error('Failed to initialize page data:', error);
        }

        window.stateManager.setError('Failed to initialize page data.', error);
        updateElement('#footerUpdate', 'N/A');
        updateElement('#totalConfigs', 'N/A');
        updateElement('#workingConfigs', 'N/A');
        sourceCount = null;
        updateFreq = null;
        updateHeroSubtitle();
        const freshnessText = document.getElementById('freshnessText');
        if (freshnessText) freshnessText.textContent = 'Distribution disabled until artifact verification succeeds';
    } finally {
        window.stateManager.setLoading(false);
        if (preloader) {
            setTimeout(() => {
                preloader.classList.add('hidden');
                document.body.classList.add('loaded');
                if (logo) {
                    logo.classList.add('loading-animation');
                }
            }, 100);
        }
    }
}

// Global artifact-state event listener for reactive trust transitions
window.addEventListener('configstream:artifact-state', (event) => {
    const detail = event.detail;
    if (detail) {
        if (detail.status === 'blocked' || detail.canDistribute === false) {
            applyTrustState('invalid', detail.metadata, {
                errorMessage: 'Security Alert: Detached cryptographic verification failed. Feeds blocked.',
                onRetry: () => initializePageData()
            });
        }
    }
});

// --- FRESHNESS INDICATOR HELPER ---
function updateFreshnessIndicator(date) {
    const dot = document.getElementById('freshnessDot');
    const text = document.getElementById('freshnessText');
    const badge = document.getElementById('footerFreshnessBadge');
    if (!dot || !text) return;

    const now = Date.now();
    const ageMs = now - date.getTime();
    const ageHours = ageMs / (1000 * 60 * 60);

    dot.classList.remove('fresh', 'aging', 'stale', 'checking');
    if (badge) badge.classList.remove('fresh', 'aging', 'stale');

    let state, label;
    if (ageHours < 2) {
        state = 'fresh';
        label = 'Data is fresh — updated less than 2 hours ago';
    } else if (ageHours < 6) {
        state = 'aging';
        label = `Data is ${Math.round(ageHours)} hours old — next update expected soon`;
    } else {
        state = 'stale';
        label = `Data is ${Math.round(ageHours)} hours old — may be stale`;
    }

    dot.classList.add(state);
    text.textContent = label;
    dot.setAttribute('aria-label', label);

    if (badge) {
        badge.classList.add(state);
        badge.textContent = state === 'fresh' ? '● Fresh' : state === 'aging' ? '◐ Aging' : '○ Stale';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const root = window.ROOT_PATH || './';
    const API_PROXIES_URL = `${root}api/proxies`;
    const API_DIFF_PROXIES_URL = `${root}api/diff/proxies`;

    // Initialize Dynamic Downloads (Client Selector)
    if (typeof initDynamicDownloads === 'function') {
        initDynamicDownloads();
    } else {
        logger.warn('initDynamicDownloads is not defined. dynamic-downloads.js might be missing.');
    }

    // --- WebSocket & Differential Updates ---
    let reconnectDelay = 5000;
    function connectWebSocket() {
        // Disable on static hosting to prevent console noise
        if (['github.io', 'pages.dev', 'netlify.app'].some(d => location.hostname.includes(d))) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/updates`;
        let ws;

        try {
            ws = new WebSocket(wsUrl);
        } catch (e) {
            logger.log('WebSocket not supported or failed to connect:', e);
            return;
        }

        ws.onopen = () => {
            logger.log('[WS] Connected');
        };

        ws.onmessage = async (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'UPDATE_AVAILABLE') {
                    logger.log('[WS] Update available:', msg.version);
                    if (window.performDifferentialUpdate) {
                        await window.performDifferentialUpdate(msg.version);
                    } else {
                        location.reload();
                    }
                }
            } catch (e) {
                logger.warn('[WS] Parse error', e);
            }
        };

        ws.onclose = () => {
            logger.log(`[WS] Disconnected, retrying in ${reconnectDelay/1000}s...`);
            setTimeout(connectWebSocket, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 1.5, 60000);
        };

        ws.onerror = (err) => {
            logger.error('[WS] Error:', err);
        };
    }

    // Dynamic API diffs are not part of the signed static artifact. When the
    // artifact guard is active, reload and re-verify the new sealed snapshot.
    window.performDifferentialUpdate = async function(newVersion) {
        if (window.api && typeof window.api.requireVerifiedArtifact === 'function') {
            const artifact = await window.api.requireVerifiedArtifact();
            if (artifact) {
                logger.log(`[Diff] Verified artifact mode active; reloading for ${newVersion}`);
                location.reload();
                return;
            }
        }

        if (!window.cacheManager) {
            logger.warn("CacheManager missing, full reload");
            location.reload();
            return;
        }

        const cached = await window.cacheManager.getCachedData(API_PROXIES_URL);
        if (!cached || !cached.version) {
            logger.log('[Diff] No cache version, fetching full');
            return window.cacheManager.fetchFresh(API_PROXIES_URL);
        }

        try {
            logger.log(`[Diff] Requesting diff from ${cached.version} to ${newVersion}`);
            const base = encodeURIComponent(cached.version);
            const response = await fetch(`${API_DIFF_PROXIES_URL}?base_version=${base}`);

            if (!response.ok) {
                 throw new Error("Diff endpoint returned " + response.status);
            }

            const update = await response.json();

            if (update.type === 'delta') {
                let proxies = cached.data;
                if (update.removed && update.removed.length > 0) {
                     const removeSet = new Set(update.removed);
                     proxies = proxies.filter(p => !removeSet.has(p.id));
                }

                if (update.added && update.added.length > 0) {
                    proxies = proxies.concat(update.added);
                }

                await window.cacheManager.cacheData(API_PROXIES_URL, proxies, newVersion);

                window.dispatchEvent(new CustomEvent('configstream:dataUpdated', {
                    detail: { count: proxies.length, generated_at: Date.now() }
                }));

                if (window.stateManager && window.stateManager.showNotification) {
                    window.stateManager.showNotification(`Data updated! +${update.added.length} -${update.removed.length} proxies.`, 'success');
                }
            } else {
                logger.log('[Diff] Server requested full reload');
                await window.cacheManager.fetchFresh(API_PROXIES_URL);
                window.dispatchEvent(new CustomEvent('configstream:dataUpdated', { detail: { generated_at: Date.now() } }));
            }
        } catch (e) {
            logger.warn('[Diff] Failed, falling back to full fetch', e);
            await window.cacheManager.fetchFresh(API_PROXIES_URL);
            window.dispatchEvent(new CustomEvent('configstream:dataUpdated', { detail: { generated_at: Date.now() } }));
        }
    };

    if (typeof WebSocket !== 'undefined') {
        connectWebSocket();
    }

    const freshnessDot = document.getElementById('freshnessDot');
    if (freshnessDot) freshnessDot.classList.add('checking');

    // --- LANDING PAGE PROXY SEARCH ---
    let _allProxiesCache = [];
    let _searchDebounce = null;

    async function fetchProxyData() {
        try {
            if (!window.api || typeof window.api.fetchProxies !== 'function') {
                throw new Error('Verified proxy API unavailable');
            }
            return await window.api.fetchProxies();
        } catch (e) {
            logger.warn('Landing proxy search: failed to fetch verified proxies', e);
            return [];
        }
    }

    function renderLandingResults(proxies, searchTerm) {
        const container = document.getElementById('landingProxyResults');
        if (!container) return;

        const tokens = searchTerm.toLowerCase().split(/\s+/).filter(Boolean);

        let filtered = proxies;
        if (tokens.length > 0) {
            filtered = proxies.filter(p => {
                const proto = (p.protocol || '').toLowerCase();
                const country = (p.country_code || '').toLowerCase();
                const city = (p.city || '').toLowerCase();
                const text = `${proto} ${country} ${city}`;
                return tokens.every(t => text.includes(t));
            });
        }

        filtered.sort((a, b) => {
            if (a.is_working !== b.is_working) return a.is_working ? -1 : 1;
            return (a.latency || 9999) - (b.latency || 9999);
        });

        const top = filtered.slice(0, 20);
        container.replaceChildren();

        if (top.length === 0 && tokens.length > 0) {
            const empty = document.createElement('div');
            empty.className = 'proxy-results-empty';
            empty.textContent = 'No proxies match your search. Try different terms.';
            container.appendChild(empty);
            return;
        }

        if (top.length === 0 && tokens.length === 0) {
            const msg = document.createElement('div');
            msg.className = 'proxy-results-loading';
            msg.textContent = 'Type to search proxies by protocol, country, or city...';
            container.appendChild(msg);
            return;
        }

        top.forEach(p => {
            const item = document.createElement('div');
            item.className = 'proxy-result-item';

            const proto = document.createElement('span');
            proto.className = 'proxy-result-proto';
            proto.textContent = (p.protocol || '?').toUpperCase();
            item.appendChild(proto);

            const loc = document.createElement('span');
            loc.className = 'proxy-result-loc';
            const cc = p.country_code || 'XX';
            loc.textContent = p.city ? `${p.city}, ${cc}` : cc;
            item.appendChild(loc);

            const lat = document.createElement('span');
            lat.className = 'proxy-result-lat';
            const latVal = p.latency;
            if (latVal && latVal < 9999) {
                lat.textContent = `${latVal}ms`;
                lat.style.color = latVal < 200 ? 'var(--success-color)' : latVal < 500 ? '#f59e0b' : 'var(--danger-color)';
            } else {
                lat.textContent = '—';
                lat.style.color = 'var(--text-secondary)';
            }
            item.appendChild(lat);

            const status = document.createElement('span');
            status.className = `proxy-result-status ${p.is_working ? 'online' : 'offline'}`;
            status.textContent = p.is_working ? 'Online' : 'Offline';
            item.appendChild(status);

            const copyBtn = document.createElement('button');
            copyBtn.className = 'proxy-result-copy';
            const copyIcon = document.createElement('i');
            copyIcon.setAttribute('data-feather', 'copy');
            copyBtn.appendChild(copyIcon);
            copyBtn.appendChild(document.createTextNode(' Copy'));
            copyBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const config = p.config || '';
                (navigator.clipboard && navigator.clipboard.writeText ? 
                        navigator.clipboard.writeText(config) : 
                        Promise.reject(new Error('Clipboard API not available'))
                    ).then(() => {
                    copyBtn.textContent = 'Copied!';
                    setTimeout(() => {
                        copyBtn.textContent = '';
                        const newIcon = document.createElement('i');
                        newIcon.setAttribute('data-feather', 'copy');
                        copyBtn.appendChild(newIcon);
                        copyBtn.appendChild(document.createTextNode(' Copy'));
                        if (window.inlineIcons) window.inlineIcons.replace();
                    }, 2000);
                }).catch(() => {});
            });
            item.appendChild(copyBtn);

            container.appendChild(item);
        });

        if (filtered.length > 20) {
            const link = document.createElement('a');
            link.className = 'proxy-results-link';
            link.href = 'proxies.html';
            link.textContent = `View all ${filtered.length} matching proxies →`;
            container.appendChild(link);
        }

        if (window.inlineIcons) window.inlineIcons.replace();
    }

    function setupLandingProxySearch() {
        const searchInput = document.getElementById('landingSearch');
        const protoSelect = document.getElementById('landingProtocol');
        const countrySelect = document.getElementById('landingCountry');
        if (!searchInput) return;

        const doSearch = () => {
            if (_searchDebounce) clearTimeout(_searchDebounce);
            _searchDebounce = setTimeout(() => {
                const searchVal = searchInput.value;
                const protoVal = protoSelect ? protoSelect.value : '';
                const countryVal = countrySelect ? countrySelect.value : '';

                let filtered = _allProxiesCache;
                if (protoVal) filtered = filtered.filter(p => p.protocol === protoVal);
                if (countryVal) filtered = filtered.filter(p => p.country_code === countryVal);

                renderLandingResults(filtered, searchVal);
            }, 250);
        };

        searchInput.addEventListener('input', doSearch);
        if (protoSelect) protoSelect.addEventListener('change', doSearch);
        if (countrySelect) countrySelect.addEventListener('change', doSearch);

        fetchProxyData().then(proxies => {
            _allProxiesCache = proxies;

            if (protoSelect) {
                const protos = [...new Set(proxies.map(p => p.protocol).filter(Boolean))].sort();
                protos.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p;
                    opt.textContent = p.toUpperCase();
                    protoSelect.appendChild(opt);
                });
            }
            if (countrySelect) {
                const countries = [...new Set(proxies.map(p => p.country_code).filter(c => c && c !== 'XX'))].sort();
                countries.forEach(cc => {
                    const opt = document.createElement('option');
                    opt.value = cc;
                    let name = cc;
                    try { name = new Intl.DisplayNames(['en'], { type: 'region' }).of(cc); } catch(e) {}
                    opt.textContent = `${name} (${cc})`;
                    countrySelect.appendChild(opt);
                });
            }
        });
    }

    setupLandingProxySearch();

    // Trigger page data initialization
    initializePageData();
});

