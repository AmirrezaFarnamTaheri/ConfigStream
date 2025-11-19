/* ============================================
   LOGO ANIMATION CONTROLLER
   ============================================ */

class LogoController {
  constructor() {
    this.headerLogo = document.getElementById('headerLogo');
    this.hasSeenAnimation = sessionStorage.getItem('hasSeenLogoAnimation') === 'true';
    this.prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.cssInjected = false;
    this.isReady = false;

    this.init();
  }

  init() {
    if (!this.headerLogo) {
      return;
    }

    this.headerLogo.addEventListener('load', () => {
      this.handleLogoReady().catch((error) => {
        console.error('Failed to initialize logo animation:', error);
      });
    });

    if (this.headerLogo.contentDocument) {
      this.handleLogoReady().catch((error) => {
        console.error('Failed to initialize logo animation:', error);
      });
    }
  }

  async handleLogoReady() {
    if (this.isReady) {
      return;
    }

    await this.injectStyles();

    if (this.prefersReducedMotion) {
      this.skipAnimation();
      this.isReady = true;
      return;
    }

    if (this.hasSeenAnimation) {
      this.skipAnimation();
      this.isReady = true;
      return;
    }

    this.isReady = true;
    this.playAnimation();
  }

  playAnimation() {
    sessionStorage.setItem('hasSeenLogoAnimation', 'true');

    const svg = this.getEmbeddedSvg();
    if (!svg) {
      return;
    }

    svg.classList.add('animating');

    // Complete animation after 2.5 seconds
    setTimeout(() => {
      this.completeAnimation();
    }, 2500);
  }

  completeAnimation() {
    const svg = this.getEmbeddedSvg();
    if (!svg) {
      return;
    }

    svg.classList.add('animation-complete');
    svg.classList.remove('animating');
  }

  skipAnimation() {
    const svg = this.getEmbeddedSvg();
    if (!svg) {
      return;
    }

    svg.classList.remove('animating');
    svg.classList.add('skip-animation');
    svg.classList.add('animation-complete');
  }

  getEmbeddedSvg() {
    if (!this.headerLogo.contentDocument) {
      return null;
    }

    return this.headerLogo.contentDocument.querySelector('svg');
  }

  async injectStyles() {
    if (this.cssInjected) {
      return;
    }

    const doc = this.headerLogo.contentDocument;
    if (!doc) {
      return;
    }

    if (doc.querySelector('style[data-logo-styles="true"]')) {
      this.cssInjected = true;
      return;
    }

    const css = await LogoController.getLogoCss();
    if (!css) {
      return;
    }

    const style = doc.createElement('style');
    style.type = 'text/css';
    style.setAttribute('data-logo-styles', 'true');
    style.textContent = css;
    doc.documentElement.appendChild(style);

    this.cssInjected = true;
  }

  static async getLogoCss() {
    if (LogoController.cachedCss !== undefined) {
      return LogoController.cachedCss;
    }

    try {
      const response = await fetch('assets/css/logo-animations.css', { cache: 'force-cache' });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      LogoController.cachedCss = await response.text();
    } catch (error) {
      console.error('Failed to load logo animations CSS:', error);
      LogoController.cachedCss = '';
    }

    return LogoController.cachedCss;
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new LogoController();
  });
} else {
  new LogoController();
}
