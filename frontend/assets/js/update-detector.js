/**
 * Smart Update Detector for ConfigStream
 *
 * Implements context-aware cache invalidation by:
 * 1. Polling a lightweight update status endpoint every 4 minutes
 * 2. Comparing timestamps to detect actual data changes
 * 3. Triggering selective data fetches only when updates are detected
 * 4. F4 Fix: Resetting cached timestamps when version changes
 *
 * This avoids relying on GitHub Action schedules and ensures
 * data is always fresh without unnecessary network requests.
 */

class UpdateDetector {
    constructor() {
        this.pollInterval = 4 * 60 * 1000; // 4 minutes in milliseconds
        this.pollTimer = null;
        this.lastKnownTimestamps = {};
        this.updateCallbacks = new Map();
        this.isPolling = false;

        // F4 Fix: Reset timestamps if version mismatch
        this.checkVersionAndReset();

        // Initialize from localStorage if available
        this.loadLastKnownTimestamps();
    }

    /**
     * Check version and reset timestamps if necessary
     */
    checkVersionAndReset() {
        try {
            const currentVersion = window.ConfigStreamCache ? window.ConfigStreamCache.VERSION : 'unknown';
            const storedVersion = localStorage.getItem('configstream_version');

            if (storedVersion !== currentVersion) {
                console.log(`[UpdateDetector] Version change detected (${storedVersion} -> ${currentVersion}). Resetting update timestamps.`);
                localStorage.removeItem('configstream_last_timestamps');
                localStorage.setItem('configstream_version', currentVersion);
                // Also clear detailed cache if cacheManager is available
                if (window.cacheManager) {
                    window.cacheManager.clear().catch(e => console.warn('Failed to clear cache on version bump', e));
                }
            }
        } catch (error) {
            console.warn('[UpdateDetector] Failed to check version:', error);
        }
    }

    /**
     * Load last known timestamps from localStorage
     */
    loadLastKnownTimestamps() {
        try {
            const stored = localStorage.getItem('configstream_last_timestamps');
            if (stored) {
                this.lastKnownTimestamps = JSON.parse(stored);
            }
        } catch (error) {
            console.warn('[UpdateDetector] Failed to load timestamps from storage:', error);
        }
    }

    /**
     * Save timestamps to localStorage for persistence across sessions
     */
    saveLastKnownTimestamps() {
        try {
            localStorage.setItem('configstream_last_timestamps', JSON.stringify(this.lastKnownTimestamps));
        } catch (error) {
            console.warn('[UpdateDetector] Failed to save timestamps:', error);
        }
    }

    /**
     * Register a callback for when a specific resource is updated
     * @param {string} resource - Resource name (e.g., 'metadata', 'proxies', 'statistics')
     * @param {Function} callback - Function to call when resource is updated
     */
    onUpdate(resource, callback) {
        if (!this.updateCallbacks.has(resource)) {
            this.updateCallbacks.set(resource, []);
        }
        this.updateCallbacks.get(resource).push(callback);
    }

    /**
     * Trigger callbacks for a specific resource
     * @param {string} resource - Resource name
     * @param {object} data - Optional data to pass to callbacks
     */
    triggerUpdate(resource, data = null) {
        const callbacks = this.updateCallbacks.get(resource);
        if (callbacks) {
            callbacks.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[UpdateDetector] Callback error for ${resource}:`, error);
                }
            });
        }
    }

    /**
     * Check for updates by fetching lightweight status endpoint
     * This endpoint should return: { metadata: {last_updated: "..."}, proxies: {...}, ... }
     */
    async checkForUpdates() {
        try {
            const basePath = (window.ROOT_PATH || '') + 'metadata.json';
            // Fetch metadata.json but only parse the timestamp
            // This is lightweight as we only need the header/timestamp field
            const response = await fetch(basePath, {
                method: 'HEAD',
                cache: 'no-cache'
            });

            // If HEAD is not supported, fall back to GET with minimal parsing
            let lastModified = response.headers.get('Last-Modified');

            if (!lastModified) {
                // Fallback: fetch metadata.json and extract timestamp
                const dataResponse = await fetch(basePath, {
                    cache: 'no-cache'
                });

                if (dataResponse.ok) {
                    const data = await dataResponse.json();
                    const timestamps = {
                        metadata: data.last_updated_utc || data.last_updated,
                        proxies: data.last_updated_utc || data.last_updated,
                        statistics: data.last_updated_utc || data.last_updated
                    };

                    return this.processTimestamps(timestamps);
                }
            } else {
                // Use Last-Modified header for quick check
                const timestamp = new Date(lastModified).toISOString();
                const timestamps = {
                    metadata: timestamp,
                    proxies: timestamp,
                    statistics: timestamp
                };

                return this.processTimestamps(timestamps);
            }
        } catch (error) {
            console.warn('[UpdateDetector] Failed to check for updates:', error);
            return { hasUpdates: false, updated: [] };
        }
    }

    /**
     * Process timestamps and detect changes
     * @param {object} timestamps - Object with resource timestamps
     * @returns {object} - { hasUpdates: boolean, updated: string[] }
     */
    processTimestamps(timestamps) {
        const updated = [];

        for (const [resource, newTimestamp] of Object.entries(timestamps)) {
            const oldTimestamp = this.lastKnownTimestamps[resource];

            if (!oldTimestamp || new Date(newTimestamp) > new Date(oldTimestamp)) {
                // Update detected
                updated.push(resource);
                this.lastKnownTimestamps[resource] = newTimestamp;

                console.log(`[UpdateDetector] Update detected for ${resource}:`, {
                    old: oldTimestamp,
                    new: newTimestamp
                });
            }
        }

        if (updated.length > 0) {
            this.saveLastKnownTimestamps();
        }

        return {
            hasUpdates: updated.length > 0,
            updated: updated
        };
    }

    /**
     * Fetch updated resources
     * @param {string[]} resources - Array of resource names to fetch
     */
    async fetchUpdatedResources(resources) {
        const fetchPromises = resources.map(async (resource) => {
            try {
                let url;
                const basePath = window.ROOT_PATH || '';
                switch (resource) {
                    case 'metadata':
                        url = basePath + 'metadata.json';
                        break;
                    case 'proxies':
                        url = basePath + 'proxies.json';
                        break;
                    case 'statistics':
                        // [UNIFIED] statistics now uses metadata.json - single source of truth
                        url = basePath + 'metadata.json';
                        break;
                    default:
                        return null;
                }

                const response = await fetch(url, { cache: 'reload' });
                if (response.ok) {
                    const data = await response.json();

                    // Clear cache for this resource to ensure fresh data
                    if (window.cacheManager) {
                        await window.cacheManager.invalidate(url);
                    }

                    // Trigger update callbacks
                    this.triggerUpdate(resource, data);

                    return { resource, data };
                }
            } catch (error) {
                console.error(`[UpdateDetector] Failed to fetch ${resource}:`, error);
            }
            return null;
        });

        return Promise.all(fetchPromises);
    }

    /**
     * Start polling for updates
     */
    startPolling() {
        if (this.isPolling) {
            console.warn('[UpdateDetector] Already polling');
            return;
        }

        this.isPolling = true;
        console.log('[UpdateDetector] Starting polling (interval: 4 minutes)');

        // Initial check
        this.poll();

        // Set up recurring polling
        this.pollTimer = setInterval(() => {
            this.poll();
        }, this.pollInterval);
    }

    /**
     * Stop polling for updates
     */
    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
            this.isPolling = false;
            console.log('[UpdateDetector] Polling stopped');
        }
    }

    /**
     * Perform a single poll operation
     */
    async poll() {
        console.log('[UpdateDetector] Polling for updates...');

        const result = await this.checkForUpdates();

        if (result.hasUpdates) {
            console.log('[UpdateDetector] Updates found:', result.updated);

            // Fetch updated resources
            const updatedData = await this.fetchUpdatedResources(result.updated);

            // Dispatch global event for other components
            window.dispatchEvent(new CustomEvent('configstream:dataUpdated', {
                detail: {
                    resources: result.updated,
                    data: updatedData
                }
            }));
        } else {
            console.log('[UpdateDetector] No updates detected');
        }
    }

    /**
     * Force an immediate update check
     */
    async forceCheck() {
        return this.poll();
    }
}

// Initialize global instance
window.updateDetector = new UpdateDetector();

// Auto-start polling when page is visible
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.updateDetector.startPolling();
    });
} else {
    window.updateDetector.startPolling();
}

// Pause polling when page is hidden to save resources
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        window.updateDetector.stopPolling();
    } else {
        window.updateDetector.startPolling();
    }
});

console.log('✅ UpdateDetector loaded successfully');
