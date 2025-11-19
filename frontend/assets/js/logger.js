/**
 * Shared logging utility for consistent logging across all JavaScript modules
 * Provides colored console output and log level filtering
 */

(function() {
  'use strict';

  /**
   * Log levels in order of severity
   */
  const LogLevel = {
    DEBUG: 0,
    INFO: 1,
    WARN: 2,
    ERROR: 3,
    NONE: 4
  };

  /**
   * Global log level (can be configured)
   */
  let globalLogLevel = LogLevel.INFO;

  /**
   * Creates a namespaced logger with consistent formatting
   *
   * @param {string} namespace - The module name (e.g., 'CacheManager')
   * @param {object} options - Configuration options
   * @returns {object} Logger instance with debug, info, warn, error methods
   *
   * @example
   * const logger = createLogger('MyModule');
   * logger.info('Initialization complete');
   * logger.error('Failed to load data', error);
   */
  function createLogger(namespace, options = {}) {
    const {
      level = globalLogLevel,
      prefix = `[${namespace}]`,
      enableTimestamps = false
    } = options;

    /**
     * Format log message with optional timestamp
     */
    function formatMessage(msg) {
      const parts = [prefix];
      if (enableTimestamps) {
        const timestamp = new Date().toISOString().split('T')[1].slice(0, -1);
        parts.push(`[${timestamp}]`);
      }
      parts.push(msg);
      return parts.join(' ');
    }

    /**
     * Log at specified level
     */
    function log(logLevel, consoleFn, msg, ...args) {
      if (logLevel >= level) {
        consoleFn(formatMessage(msg), ...args);
      }
    }

    return {
      /**
       * Log debug information (lowest priority)
       */
      debug: (msg, ...args) => log(LogLevel.DEBUG, console.debug, msg, ...args),

      /**
       * Log informational messages
       */
      info: (msg, ...args) => log(LogLevel.INFO, console.log, msg, ...args),

      /**
       * Log warnings
       */
      warn: (msg, ...args) => log(LogLevel.WARN, console.warn, msg, ...args),

      /**
       * Log errors (highest priority)
       */
      error: (msg, ...args) => log(LogLevel.ERROR, console.error, msg, ...args),

      /**
       * Create a child logger with a sub-namespace
       */
      child: (subNamespace) => createLogger(`${namespace}:${subNamespace}`, options)
    };
  }

  /**
   * Set global log level for all loggers
   * @param {string} level - 'debug', 'info', 'warn', 'error', or 'none'
   */
  function setGlobalLogLevel(level) {
    const levelMap = {
      'debug': LogLevel.DEBUG,
      'info': LogLevel.INFO,
      'warn': LogLevel.WARN,
      'error': LogLevel.ERROR,
      'none': LogLevel.NONE
    };
    globalLogLevel = levelMap[level.toLowerCase()] ?? LogLevel.INFO;
  }

  // Export to global scope
  if (typeof window !== 'undefined') {
    window.createLogger = createLogger;
    window.setGlobalLogLevel = setGlobalLogLevel;
    window.LogLevel = LogLevel;
  }

  // Export for Node.js testing
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { createLogger, setGlobalLogLevel, LogLevel };
  }

  // Initialize global logger
  const logger = createLogger('Logger');
  logger.info('Shared logging utility loaded');
})();
