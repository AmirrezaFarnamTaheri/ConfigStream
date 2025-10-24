/* ============================================
   LOADING & ANIMATION CONTROLLER
   ============================================ */

class LoadingController {
  constructor() {
    this.loadingScreen = document.getElementById('loading-screen');
    this.loadingText = document.getElementById('loadingText');
    this.loadingAnnounce = document.getElementById('loadingAnnounce');
    this.loadStartTime = Date.now();
    this.minLoadingTime = 500; // Minimum loading screen time (ms)
    this.maxLoadingTime = 10000; // Maximum loading time before timeout (ms)
    this.loadingTimeout = null;

    this.init();
  }

  init() {
    // Check if user prefers reduced motion
    this.prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Set up loading screen
    if (document.readyState === 'loading') {
      this.showLoadingScreen();

      // Listen for page load
      if (document.readyState !== 'complete') {
        window.addEventListener('load', () => this.handlePageLoad());
      }

      // Safety timeout
      this.loadingTimeout = setTimeout(() => {
        this.handleLoadError();
      }, this.maxLoadingTime);
    } else {
      // Page already loaded
      this.hideLoadingScreen();
    }

    // Fetch data and handle completion
    this.fetchData();
  }

  showLoadingScreen() {
    if (this.loadingScreen) {
      this.loadingScreen.classList.remove('hidden');

      // Announce to screen readers
      if (this.loadingAnnounce) {
        this.loadingAnnounce.textContent = 'Loading content, please wait';
      }
    }
  }

  async fetchData() {
    try {
      // Fetch your data here
      // Example: fetching metadata
      const response = await fetch('output/metadata.json');

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      // Update loading message
      if (this.loadingText) {
        this.loadingText.textContent = 'Loading configurations...';
      }

      // Store data for page use
      window.configStreamData = data;

      // Data fetched successfully
      this.handleDataLoaded();

    } catch (error) {
      console.error('Failed to fetch data:', error);
      this.handleLoadError();
    }
  }

  handleDataLoaded() {
    const loadTime = Date.now() - this.loadStartTime;

    // Ensure minimum loading time for smooth transition
    const remainingTime = Math.max(0, this.minLoadingTime - loadTime);

    setTimeout(() => {
      this.hideLoadingScreen();

      // Announce completion to screen readers
      if (this.loadingAnnounce) {
        this.loadingAnnounce.textContent = 'Content loaded successfully';
      }
    }, remainingTime);
  }

  handlePageLoad() {
    clearTimeout(this.loadingTimeout);
    // Page load complete, data should be loaded by now
    // If not already hidden, hide after min time
    if (!this.loadingScreen.classList.contains('hidden')) {
      this.handleDataLoaded();
    }
  }

  handleLoadError() {
    if (this.loadingText) {
      this.loadingText.textContent = 'Failed to load data. Retrying...';
      this.loadingText.style.color = '#ff6b6b';
    }

    // Retry once after 2 seconds
    setTimeout(() => {
      this.fetchData();
    }, 2000);

    // If still failing, proceed anyway
    setTimeout(() => {
      this.hideLoadingScreen();
    }, 5000);
  }

  hideLoadingScreen() {
    if (this.loadingScreen) {
      this.loadingScreen.classList.add('hidden');

      // Remove from DOM after transition
      setTimeout(() => {
        if (this.loadingScreen && this.loadingScreen.parentNode) {
          this.loadingScreen.parentNode.removeChild(this.loadingScreen);
        }
      }, 400);

    }
  }
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new LoadingController();
  });
} else {
  new LoadingController();
}

/* ============================================
   NAVIGATION PRELOAD (Performance boost)
   ============================================ */

// Preload on hover for instant navigation
document.addEventListener('DOMContentLoaded', () => {
  const navLinks = document.querySelectorAll('a[href^="./"], a[href^="/"]');

  navLinks.forEach(link => {
    link.addEventListener('mouseenter', () => {
      const href = link.getAttribute('href');
      if (href && !link.dataset.preloaded) {
        // Preload the page
        const preload = document.createElement('link');
        preload.rel = 'prefetch';
        preload.href = href;
        document.head.appendChild(preload);
        link.dataset.preloaded = 'true';
      }
    });
  });
});

/* ============================================
   THEME INTEGRATION (if you have theme toggle)
   ============================================ */

// Listen for theme changes
const themeObserver = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    if (mutation.attributeName === 'data-theme') {
      updateLogoForTheme();
    }
  });
});

function updateLogoForTheme() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const logoObject = document.getElementById('headerLogo');

  if (!logoObject) {
    return;
  }

  const applyTheme = () => {
    const svg = logoObject.contentDocument && logoObject.contentDocument.querySelector('svg');
    if (!svg) {
      return;
    }

    if (isDark) {
      svg.classList.add('theme-dark');
    } else {
      svg.classList.remove('theme-dark');
    }
  };

  if (logoObject.contentDocument) {
    applyTheme();
  } else {
    logoObject.addEventListener('load', applyTheme, { once: true });
  }
}

// Observe theme changes
if (document.documentElement) {
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
  });
}

updateLogoForTheme();
/* ============================================
   PERFORMANCE MONITORING
   ============================================ */

// Monitor animation performance
if ('PerformanceObserver' in window) {
  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      // Log slow animations
      if (entry.duration > 16.67) { // 60fps threshold
        console.warn('Slow animation detected:', entry.name, entry.duration);
      }
    }
  });

  observer.observe({ entryTypes: ['measure'] });
}

// GPU acceleration hint
const logoElement = document.getElementById('headerLogo');
if (logoElement) {
  logoElement.style.willChange = 'transform';

  // Remove will-change after animation
  setTimeout(() => {
    logoElement.style.willChange = 'auto';
  }, 1500);
}
