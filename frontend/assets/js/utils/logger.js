/**
 * Production-Safe Logger Utility
 *
 * Provides conditional logging that automatically disables verbose logging
 * in production environments to prevent information disclosure and improve performance.
 *
 * Usage:
 *   import logger from './utils/logger.js';
 *   logger.log('Debug message');     // Only in development
 *   logger.warn('Warning message');   // Only in development
 *   logger.error('Error message');    // Always logged
 *   logger.info('Info message');      // Only in development
 *
 * Addresses security concern: console logging in production.
 */

class Logger {
    constructor() {
        // Detect production environment
        // Production indicators:
        // 1. hostname is not localhost/127.0.0.1
        // 2. protocol is https
        // 3. No query param ?debug=true
        this.isProduction = this.detectProduction();
        this.debugMode = this.detectDebugMode();

        if (this.isProduction && !this.debugMode) {
            this.log('ConfigStream Logger: Production mode - verbose logging disabled');
        }
    }

    detectProduction() {
        const hostname = window.location.hostname;
        const isLocal = hostname === 'localhost' ||
                       hostname === '127.0.0.1' ||
                       hostname.startsWith('192.168.') ||
                       hostname.startsWith('10.') ||
                       hostname.endsWith('.local');

        return !isLocal;
    }

    detectDebugMode() {
        // Allow debug mode via query parameter: ?debug=true
        const params = new URLSearchParams(window.location.search);
        return params.get('debug') === 'true' ||
               localStorage.getItem('configstream_debug') === 'true';
    }

    /**
     * Enable debug mode (persists across sessions)
     */
    enableDebug() {
        localStorage.setItem('configstream_debug', 'true');
        this.debugMode = true;
        console.log('ConfigStream Debug mode enabled');
    }

    /**
     * Disable debug mode
     */
    disableDebug() {
        localStorage.removeItem('configstream_debug');
        this.debugMode = false;
        console.log('ConfigStream Debug mode disabled');
    }

    /**
     * Debug logging - only in development or with ?debug=true
     */
    log(...args) {
        if (!this.isProduction || this.debugMode) {
            console.log(...args);
        }
    }

    /**
     * Debug logging alias (for compatibility)
     */
    debug(...args) {
        this.log(...args);
    }

    /**
     * Info logging - only in development or with ?debug=true
     */
    info(...args) {
        if (!this.isProduction || this.debugMode) {
            console.info(...args);
        }
    }

    /**
     * Warning logging - only in development or with ?debug=true
     */
    warn(...args) {
        if (!this.isProduction || this.debugMode) {
            console.warn(...args);
        }
    }

    /**
     * Error logging - ALWAYS enabled (errors should always be logged)
     */
    error(...args) {
        console.error(...args);
    }

    /**
     * Debug table - only in development
     */
    table(data) {
        if (!this.isProduction || this.debugMode) {
            console.table(data);
        }
    }

    /**
     * Group logging - only in development
     */
    group(label) {
        if (!this.isProduction || this.debugMode) {
            console.group(label);
        }
    }

    groupCollapsed(label) {
        if (!this.isProduction || this.debugMode) {
            console.groupCollapsed(label);
        }
    }

    groupEnd() {
        if (!this.isProduction || this.debugMode) {
            console.groupEnd();
        }
    }

    /**
     * Time measurement - only in development
     */
    time(label) {
        if (!this.isProduction || this.debugMode) {
            console.time(label);
        }
    }

    timeEnd(label) {
        if (!this.isProduction || this.debugMode) {
            console.timeEnd(label);
        }
    }

    /**
     * Trace logging - only in development
     */
    trace(...args) {
        if (!this.isProduction || this.debugMode) {
            console.trace(...args);
        }
    }
}

// Export singleton instance
const logger = new Logger();

// Expose to global scope for debugging
if (typeof window !== 'undefined') {
    window.ConfigStreamLogger = logger;
}

export default logger;
