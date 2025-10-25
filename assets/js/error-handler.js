/**
 * Global Error Boundary Handler
 * Catches JavaScript errors and prevents white screens of death
 */

class ErrorBoundary {
  constructor() {
    this.errors = [];
    this.setupGlobalHandlers();
  }

  setupGlobalHandlers() {
    // Catch synchronous errors
    window.addEventListener('error', (event) => {
      console.error('Global error caught:', event.error);
      this.handleError(event.error, 'global');
    });

    // Catch unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      console.error('Unhandled promise rejection:', event.reason);
      this.handleError(event.reason, 'promise');
      event.preventDefault(); // Prevent browser from logging
    });
  }

  /**
   * Wrap async functions with error handling
   * Usage: const result = await errorBoundary.wrap(fetchData(), 'fetchData');
   */
  async wrap(promise, componentName) {
    try {
      return await promise;
    } catch (error) {
      this.handleError(error, componentName);
      throw error; // Re-throw for caller to handle
    }
  }

  /**
   * Central error handler
   */
  handleError(error, componentName) {
    this.errors.push({
      message: error.message || String(error),
      component: componentName,
      timestamp: new Date().toISOString(),
      stack: error.stack
    });

    // Determine severity
    const severity = this.determineSeverity(error);

    if (severity === 'critical') {
      this.showErrorPage(error);
    } else if (severity === 'high') {
      this.showErrorNotification(error, true);
    } else {
      this.showErrorNotification(error, false);
    }

    // Log for debugging
    console.error(`[${componentName}] ${error.message}`, error);
  }

  /**
   * Determine error severity
   */
  determineSeverity(error) {
    // Critical errors that break functionality
    if (error.message.includes('Cannot read') ||
        error.message.includes('is not a function') ||
        error.message.includes('JSON')) {
      return 'critical';
    }

    // High severity
    if (error.message.includes('Failed') ||
        error.message.includes('timeout')) {
      return 'high';
    }

    return 'low';
  }

  /**
   * Show critical error page (replaces main content)
   */
  showErrorPage(error) {
    const main = document.querySelector('main');
    if (main) {
      main.innerHTML = `
        <div class="error-page">
          <div class="error-page-content">
            <i data-feather="alert-triangle" class="error-icon"></i>
            <h1>Oops! Something went wrong</h1>
            <p>The page encountered an error and needs to be reloaded.</p>
            <details class="error-details">
              <summary>Error Details</summary>
              <pre>${error.message}\n\n${error.stack}</pre>
            </details>
            <button onclick="window.location.reload()" class="btn btn-primary">
              <i data-feather="refresh-cw"></i> Reload Page
            </button>
            <button onclick="window.history.back()" class="btn btn-secondary">
              <i data-feather="arrow-left"></i> Go Back
            </button>
          </div>
        </div>
      `;

      if (window.inlineIcons) {
        window.inlineIcons.replace();
      }
    }
  }

  /**
   * Show error notification (non-critical)
   */
  showErrorNotification(error, persistent = false) {
    if (window.stateManager) {
      window.stateManager.setError(
        error.message || 'An unexpected error occurred',
        error
      );
    }
  }
}

// Create global instance
window.errorBoundary = new ErrorBoundary();

console.log('✅ Error Boundary initialized');