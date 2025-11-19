/**
 * Enhanced UI State Manager for ConfigStream
 * Coordinates state across all frontend components with race condition prevention
 * 
 * Key features:
 * - Batched state updates for performance
 * - Queued notification to prevent race conditions
 * - Automatic circular update detection
 * - Type-safe state management
 */

class UIStateManager {
  constructor() {
    // Initial state definition
    // All state keys should be defined here for clarity
    this.state = {
      // Loading states
      isLoading: false,
      loadingMessage: 'Loading...',
      
      // Page management
      currentPage: this.detectCurrentPage(),
      isPageVisible: !document.hidden,
      
      // Message states
      errorMessage: null,
      successMessage: null,
      
      // Data states
      proxiesLoaded: false,
      statisticsLoaded: false,
      metadataLoaded: false,
      
      // Timestamps
      lastUpdate: null,
      dataUpdatedAt: null,
      
      // Connection state
      isOnline: navigator.onLine
    };
    
    // Map of state key -> Set of listener callbacks
    this.listeners = new Map();
    
    // Queue for pending state updates
    this.updateQueue = [];
    
    // Flag indicating we're currently processing updates
    this.isProcessing = false;
    
    // Circular update detection
    this.updateDepth = 0;
    this.maxUpdateDepth = 10;
    
    // Logging utility
    this.log = {
      info: (msg) => console.log(`[StateManager] ${msg}`),
      warn: (msg) => console.warn(`[StateManager] ${msg}`),
      error: (msg) => console.error(`[StateManager] ${msg}`),
      debug: (msg) => console.debug(`[StateManager] ${msg}`)
    };
    
    // Initialize event listeners
    this.initializeEventListeners();
    
    this.log.info('Initialized successfully');
  }
  
  /**
   * Detect current page from URL
   */
  detectCurrentPage() {
    const path = window.location.pathname;
    
    if (path.includes('proxies.html')) return 'proxies';
    if (path.includes('statistics.html')) return 'statistics';
    return 'home';
  }
  
  /**
   * Subscribe to state changes for specific key
   * 
   * @param {string} key - State key to watch
   * @param {Function} callback - Called when key changes with (newValue, fullState)
   * @returns {Function} Unsubscribe function
   */
  subscribe(key, callback) {
    if (typeof key !== 'string') {
      this.log.error(`Subscribe key must be string, got ${typeof key}`);
      return () => {};
    }
    
    if (typeof callback !== 'function') {
      this.log.error(`Subscribe callback must be function, got ${typeof callback}`);
      return () => {};
    }
    
    // Initialize listener set for this key if needed
    if (!this.listeners.has(key)) {
      this.listeners.set(key, new Set());
    }
    
    // Add callback to set
    this.listeners.get(key).add(callback);
    
    this.log.debug(`Subscribed to '${key}' (${this.listeners.get(key).size} listeners)`);
    
    // Return unsubscribe function
    return () => {
      const listeners = this.listeners.get(key);
      if (listeners) {
        listeners.delete(callback);
        this.log.debug(`Unsubscribed from '${key}' (${listeners.size} remaining)`);
      }
    };
  }
  
  /**
   * Update state with batching and race condition prevention
   * 
   * @param {Object} updates - Key-value pairs to update
   */
  setState(updates) {
    // Validate input
    if (!updates || typeof updates !== 'object' || Array.isArray(updates)) {
      this.log.error('setState requires an object');
      return;
    }
    
    // Add to update queue
    this.updateQueue.push(updates);
    
    // Start processing if not already running
    if (!this.isProcessing) {
      this.isProcessing = true;
      
      // Schedule processing on next microtask
      // This allows multiple synchronous setState calls to batch together
      Promise.resolve().then(() => this.processQueue());
    }
  }
  
  /**
   * Process all queued updates atomically
   * This is called on the next microtask after setState
   */
  processQueue() {
    try {
      while (this.updateQueue.length > 0) {
        // Check for circular updates
        this.updateDepth++;
        
        if (this.updateDepth > this.maxUpdateDepth) {
          this.log.error(
            `Maximum update depth (${this.maxUpdateDepth}) exceeded. ` +
            'Possible infinite loop detected.'
          );
          this.updateQueue = []; // Clear queue to prevent further damage
          break;
        }
        
        // Get next batch of updates
        const updates = this.updateQueue.shift();
        
        // Apply updates and collect notifications
        this.applyUpdates(updates);
      }
    } finally {
      // Reset state
      this.updateDepth = 0;
      this.isProcessing = false;
    }
  }
  
  /**
   * Apply a batch of updates and notify listeners
   * 
   * @param {Object} updates - Updates to apply
   */
  applyUpdates(updates) {
    const changes = [];
    
    // Phase 1: Apply all updates to state
    for (const [key, value] of Object.entries(updates)) {
      // Only record actual changes
      if (this.state[key] !== value) {
        const oldValue = this.state[key];
        this.state[key] = value;
        
        changes.push({
          key,
          oldValue,
          newValue: value
        });
        
        this.log.debug(`State change: ${key} = ${JSON.stringify(value)}`);
      }
    }
    
    // Phase 2: Notify listeners (deferred to next microtask)
    if (changes.length > 0) {
      this.notifyListeners(changes);
    }
  }
  
  /**
   * Notify all relevant listeners of changes
   * This is deferred to prevent listeners from causing race conditions
   * 
   * @param {Array} changes - Array of {key, oldValue, newValue}
   */
  notifyListeners(changes) {
    // Defer notification to next microtask
    Promise.resolve().then(() => {
      for (const { key, newValue } of changes) {
        const listeners = this.listeners.get(key);
        
        if (!listeners || listeners.size === 0) {
          continue;
        }
        
        // Call each listener with the new value and full state
        for (const callback of listeners) {
          try {
            callback(newValue, this.getState());
          } catch (error) {
            this.log.error(`Listener error for '${key}': ${error.message}`);
            // Continue with other listeners despite error
          }
        }
      }
      
      // Emit global state change event
      window.dispatchEvent(new CustomEvent('stateChanged', {
        detail: {
          changes: changes.map(c => ({ key: c.key, value: c.newValue })),
          state: this.getState()
        }
      }));
    });
  }
  
  /**
   * Get immutable snapshot of current state
   * @returns {Object} State snapshot
   */
  getState() {
    return { ...this.state };
  }
  
  /**
   * Get single state value
   * @param {string} key - State key
   * @returns {*} State value
   */
  get(key) {
    return this.state[key];
  }
  
  /**
   * Helper: Set loading state
   */
  setLoading(isLoading, message = 'Loading...') {
    this.setState({
      isLoading,
      loadingMessage: message,
      errorMessage: null,
      successMessage: null
    });
    
    if (isLoading) {
      this.showLoadingUI(message);
    } else {
      this.hideLoadingUI();
    }
  }
  
  /**
   * Helper: Set error state
   */
  setError(message, details = null) {
    this.log.error(`UI Error: ${message}`, details);
    
    this.setState({
      isLoading: false,
      errorMessage: message,
      successMessage: null
    });
    
    this.showErrorNotification(message);
  }
  
  /**
   * Helper: Set success state
   */
  setSuccess(message, autoDismiss = true) {
    this.setState({
      isLoading: false,
      errorMessage: null,
      successMessage: message
    });

    this.showSuccessNotification(message);

    if (autoDismiss) {
      setTimeout(() => {
        this.setState({ successMessage: null });
        this.hideSuccessNotification();
      }, 5000);
    }
  }

  /**
   * Helper: Set informational message (alias of setSuccess without auto dismiss)
   */
  setInfo(message, autoDismiss = false) {
    this.setSuccess(message, autoDismiss);
  }
  
  /**
   * Helper: Clear all messages
   */
  clearMessages() {
    this.setState({
      errorMessage: null,
      successMessage: null
    });
    
    this.hideErrorNotification();
    this.hideSuccessNotification();
  }
  
  // UI manipulation methods
  // These directly update the DOM and shouldn't trigger state updates
  
  showLoadingUI(message) {
    const main = document.querySelector('main');
    if (main) {
      main.style.opacity = '0.5';
      main.style.pointerEvents = 'none';
    }
    
    let overlay = document.getElementById('loading-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'loading-overlay';
      overlay.className = 'loading-overlay';
      document.body.appendChild(overlay);
    }
    
    overlay.innerHTML = `
      <div class="loading-spinner">
        <div class="spinner"></div>
        <p>${message}</p>
      </div>
    `;
    overlay.style.display = 'flex';
  }
  
  hideLoadingUI() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
      overlay.style.display = 'none';
    }
    
    const main = document.querySelector('main');
    if (main) {
      main.style.opacity = '1';
      main.style.pointerEvents = 'auto';
    }
  }
  
  showErrorNotification(message) {
    // Remove existing error notifications
    this.hideErrorNotification();
    
    const notification = document.createElement('div');
    notification.id = 'error-notification';
    notification.className = 'notification notification-error';
    notification.innerHTML = `
      <div class="notification-content">
        <i data-feather="alert-circle" class="notification-icon"></i>
        <div class="notification-text">
          <h4>Error</h4>
          <p>${this.escapeHtml(message)}</p>
        </div>
        <button class="notification-close" onclick="document.getElementById('error-notification').remove()">
          <i data-feather="x"></i>
        </button>
      </div>
    `;
    
    document.body.appendChild(notification);
    
    if (window.inlineIcons) {
      window.inlineIcons.replace();
    }

    // Auto-remove after 8 seconds
    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 8000);
  }
  
  hideErrorNotification() {
    const notification = document.getElementById('error-notification');
    if (notification) {
      notification.remove();
    }
  }
  
  showSuccessNotification(message) {
    // Remove existing success notifications
    this.hideSuccessNotification();
    
    const notification = document.createElement('div');
    notification.id = 'success-notification';
    notification.className = 'notification notification-success';
    notification.innerHTML = `
      <div class="notification-content">
        <i data-feather="check-circle" class="notification-icon"></i>
        <div class="notification-text">
          <p>${this.escapeHtml(message)}</p>
        </div>
        <button class="notification-close" onclick="document.getElementById('success-notification').remove()">
          <i data-feather="x"></i>
        </button>
      </div>
    `;
    
    document.body.appendChild(notification);

    if (window.inlineIcons) {
      window.inlineIcons.replace();
    }
  }

  hideSuccessNotification() {
    const notification = document.getElementById('success-notification');
    if (notification) {
      notification.remove();
    }
  }
  
  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  /**
   * Initialize global event listeners
   */
  initializeEventListeners() {
    // Page visibility changes
    document.addEventListener('visibilitychange', () => {
      this.setState({
        isPageVisible: !document.hidden
      });
    });
    
    // Online/offline status
    window.addEventListener('online', () => {
      this.setState({ isOnline: true });
      this.setSuccess('Connection restored');
    });
    
    window.addEventListener('offline', () => {
      this.setState({ isOnline: false });
      this.setError('You are offline. Some features may not work.');
    });
    
    // Listen for data updates from cache manager
    window.addEventListener('dataUpdated', (event) => {
      this.setState({
        lastUpdate: event.detail?.generated_at || Date.now()
      });
    });
  }
}

// Create global instance
window.stateManager = new UIStateManager();

// Expose for debugging in development
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
  window.debugState = () => {
    console.log('Current State:', window.stateManager.getState());
    console.log('Listeners:', window.stateManager.listeners);
  };
}

console.log('✅ UIStateManager initialized');