/**
 * Global Error Boundary Handler
 * Catches JavaScript errors and prevents white screens of death
 */

class ErrorBoundary {
  constructor() {
    this.errors = [];
    this.logger = window.createLogger ? window.createLogger('ErrorBoundary') : console;
    this.setupGlobalHandlers();
  }

  setupGlobalHandlers() {
    // Catch synchronous errors
    window.addEventListener('error', (event) => {
      this.logger.error('Global error caught:', event.error);
      this.handleError(event.error, 'global');
    });

    // Catch unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.logger.error('Unhandled promise rejection:', event.reason);
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
    // Audit: Limit log size
    if (this.errors.length >= 50) {
        this.errors.shift();
    }

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
    this.logger.error(`[${componentName}] ${error.message}`, error);
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
      const page = document.createElement('div');
      page.className = 'error-page';

      const content = document.createElement('div');
      content.className = 'error-page-content';

      const icon = document.createElement('i');
      icon.dataset.feather = 'alert-triangle';
      icon.className = 'error-icon';

      const title = document.createElement('h1');
      title.textContent = 'Oops! Something went wrong';

      const message = document.createElement('p');
      message.textContent = 'The page encountered an error and needs to be reloaded.';

      const details = document.createElement('details');
      details.className = 'error-details';
      const summary = document.createElement('summary');
      summary.textContent = 'Error Details';
      const pre = document.createElement('pre');
      pre.textContent = `${error.message || 'Unknown Error'}\n\n${error.stack || ''}`;
      details.append(summary, pre);

      const reloadButton = document.createElement('button');
      reloadButton.type = 'button';
      reloadButton.className = 'btn btn-primary';
      const reloadIcon = document.createElement('i');
      reloadIcon.dataset.feather = 'refresh-cw';
      reloadButton.append(reloadIcon, document.createTextNode(' Reload Page'));
      reloadButton.addEventListener('click', () => window.location.reload());

      const backButton = document.createElement('button');
      backButton.type = 'button';
      backButton.className = 'btn btn-secondary';
      const backIcon = document.createElement('i');
      backIcon.dataset.feather = 'arrow-left';
      backButton.append(backIcon, document.createTextNode(' Go Back'));
      backButton.addEventListener('click', () => window.history.back());

      content.append(icon, title, message, details, reloadButton, backButton);
      page.appendChild(content);
      main.replaceChildren(page);

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

// Log initialization using logger if available
if (window.createLogger) {
  const logger = window.createLogger('ErrorBoundary');
  logger.info('Error Boundary initialized');
}
