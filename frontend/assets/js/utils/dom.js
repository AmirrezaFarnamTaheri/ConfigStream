/**
 * DOM utilities
 */

function sanitizeHTML(text) {
  if (!text) return '';
  return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
}

/**
 * Safely updates an element's content.
 * @param {string} selector - CSS selector
 * @param {string|Node|NodeList} content - New content
 * @param {Object} options - Update options
 */
function updateElement(selector, content, options = {}) {
  const {
    method = 'textContent',
    clearFirst = false,
    throwError = false,
    trustedHTML = false
  } = options;

  if (!selector || typeof selector !== 'string') return false;
  if (content === null || content === undefined) return false;

  const element = document.querySelector(selector);
  if (!element) return false;

  if (clearFirst) {
    element.replaceChildren();
  }

  try {
    if (method === 'innerHTML') {
      if (content instanceof Node) {
        element.appendChild(content);
      } else if (trustedHTML) {
        element.innerHTML = String(content);
      } else {
        let sanitized;
        if (window.DOMPurify) {
          sanitized = window.DOMPurify.sanitize(String(content));
          element.innerHTML = sanitized;
        } else {
          element.textContent = String(content);
        }
      }
    } else if (content instanceof Node) {
      element.replaceChildren(content);
    } else {
      element.textContent = String(content);
    }
    element.classList.remove('loading');
    return true;
  } catch (error) {
    console.error('[updateElement] Error:', error);
    if (throwError) throw error;
    return false;
  }
}

async function copyToClipboard(text, button) {
  try {
    // Try modern Clipboard API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      // Fallback for non-secure contexts or older browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-9999px';
      textArea.style.top = '-9999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      try {
        document.execCommand('copy');
      } finally {
        document.body.removeChild(textArea);
      }
    }

    // Save original content as nodes
    const originalContent = Array.from(button.childNodes);
    
    // Create check icon
    const icon = document.createElement('i');
    icon.setAttribute('data-feather', 'check');
    button.replaceChildren(icon);
    
    if (window.inlineIcons) window.inlineIcons.replace();
    button.classList.add('copied');

    setTimeout(() => {
      button.replaceChildren(...originalContent);
      button.classList.remove('copied');
    }, 2000);
  } catch (error) {
    console.error('Failed to copy:', error);
    const icon = document.createElement('i');
    icon.setAttribute('data-feather', 'x');
    button.replaceChildren(icon);
    if (window.inlineIcons) window.inlineIcons.replace();
  }
}

// Export to window for global access
window.copyToClipboard = copyToClipboard;
