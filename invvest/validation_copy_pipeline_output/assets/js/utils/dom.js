/**
 * DOM utilities
 */

function sanitizeHTML(html) {
  const div = document.createElement('div');
  div.textContent = html;
  return div.innerHTML;
}

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

  if (clearFirst) element.innerHTML = '';

  try {
    if (method === 'innerHTML') {
      if (trustedHTML) {
        element.innerHTML = String(content);
      } else {
        let sanitized;
        if (window.DOMPurify) {
            sanitized = window.DOMPurify.sanitize(String(content));
        } else {
            sanitized = sanitizeHTML(String(content));
        }
        element.innerHTML = sanitized;
      }
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
    const originalHTML = button.innerHTML;
    button.innerHTML = '<i data-feather="check"></i>';
    if (window.inlineIcons) window.inlineIcons.replace();
    button.classList.add('copied');

    setTimeout(() => {
      button.innerHTML = originalHTML;
      if (window.inlineIcons) window.inlineIcons.replace();
      button.classList.remove('copied');
    }, 2000);
  } catch (error) {
    console.error('Failed to copy:', error);
    button.innerHTML = '<i data-feather="x"></i>';
    if (window.inlineIcons) window.inlineIcons.replace();
  }
}

// Export to window for global access
window.copyToClipboard = copyToClipboard;
