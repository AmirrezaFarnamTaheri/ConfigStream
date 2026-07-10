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

function stripUnsafeHTML(fragment) {
  fragment.querySelectorAll('script, object, embed, applet, iframe, form').forEach(
      node => node.remove()
  );
  fragment.querySelectorAll('*').forEach(node => {
    [...node.attributes].forEach(attr => {
      const name = attr.name.toLowerCase();
      const value = attr.value || '';
      if (name.startsWith('on')) {
        node.removeAttribute(attr.name);
        return;
      }
      if ((name === 'href' || name === 'src') && /^(javascript|data|vbscript):/i.test(value.replace(/[\u0000-\u0020]/g, ''))) {
        node.removeAttribute(attr.name);
      }
    });
  });
}

function htmlToFragment(html) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(String(html), 'text/html');
  const fragment = document.createDocumentFragment();
  Array.from(doc.body.childNodes).forEach(node => {
    fragment.appendChild(document.importNode(node, true));
  });
  stripUnsafeHTML(fragment);
  return fragment;
}

function sanitizeHTMLToFragment(html) {
  if (window.DOMPurify) {
    const sanitized = window.DOMPurify.sanitize(String(html), {
      RETURN_DOM_FRAGMENT: true
    });
    if (sanitized && typeof sanitized.nodeType === 'number') {
      stripUnsafeHTML(sanitized);
      return sanitized;
    }
    return htmlToFragment(sanitized || '');
  }

  const fragment = document.createDocumentFragment();
  fragment.appendChild(document.createTextNode(String(html)));
  return fragment;
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
    throwError = false
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
        element.replaceChildren(content);
      } else {
        element.replaceChildren(sanitizeHTMLToFragment(content));
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
window.sanitizeHTML = sanitizeHTML;
window.htmlToSafeFragment = htmlToFragment;
window.updateElement = updateElement;
window.copyToClipboard = copyToClipboard;
