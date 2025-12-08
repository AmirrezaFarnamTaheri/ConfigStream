/**
 * Helper utilities
 */

function deepClone(obj) {
  if (obj === null || obj === undefined || typeof obj !== 'object') return obj;
  try {
    return JSON.parse(JSON.stringify(obj));
  } catch (error) {
    return null;
  }
}

function debounce(func, wait) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

function validateURL(url) {
  if (!url || typeof url !== 'string') return null;
  try {
    const urlObj = new URL(url);
    if (!['http:', 'https:'].includes(urlObj.protocol)) return null;
    if (!urlObj.hostname) return null;
    return urlObj.toString();
  } catch (error) {
    return null;
  }
}

function getFullUrl(file) {
  if (!file) return '';
  try {
    // If it's already absolute, return it
    if (file.startsWith('http://') || file.startsWith('https://')) {
        return file;
    }
    // Resolve relative to current page (handles subdirectories like /repo/)
    return new URL(file, window.location.href).href;
  } catch (e) {
    console.error('Error constructing URL:', e);
    return file;
  }
}

function exportJSON(data, filename = 'export.json') {
  const jsonString = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonString], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

// Expose globally for copy button functionality
if (typeof window !== 'undefined') {
    window.getFullUrl = getFullUrl;
}
