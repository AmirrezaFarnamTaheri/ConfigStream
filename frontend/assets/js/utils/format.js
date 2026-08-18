/**
 * Formatting utilities
 */

function getCountryFlag(countryCode) {
  if (countryCode === null || countryCode === undefined) return '🌍';
  if (typeof countryCode !== 'string') return '🌍';
  const trimmed = countryCode.trim();
  if (trimmed.length !== 2 || !/^[A-Za-z]{2}$/.test(trimmed)) return '🌍';

  try {
    const codePoints = trimmed.toUpperCase().split('').map(char => 127397 + char.charCodeAt(0));
    return String.fromCodePoint(...codePoints);
  } catch (error) {
    console.error('[getCountryFlag] Failed to generate flag:', error);
    return '🌍';
  }
}

function formatTimestamp(timestamp, format = 'MM/DD/YYYY HH:mm:ss') {
  if (timestamp == null) return 'N/A';
  let dateObj;
  try {
    dateObj = new Date(timestamp);
  } catch (e) { return 'N/A'; }

  if (isNaN(dateObj.getTime())) return 'Invalid Date';

  const parts = {
    YYYY: dateObj.getFullYear().toString(),
    MM: String(dateObj.getMonth() + 1).padStart(2, '0'),
    DD: String(dateObj.getDate()).padStart(2, '0'),
    HH: String(dateObj.getHours()).padStart(2, '0'),
    mm: String(dateObj.getMinutes()).padStart(2, '0'),
    ss: String(dateObj.getSeconds()).padStart(2, '0')
  };

  let result = format;
  for (const [token, value] of Object.entries(parts)) {
    result = result.replace(token, value);
  }
  return result;
}

function getProtocolColor(protocol) {
  const colors = {
    'vmess': '#FF6B6B',
    'vless': '#4ECDC4',
    'shadowsocks': '#45B7D1',
    'trojan': '#96CEB4',
    'hysteria': '#FFEAA7',
    'hysteria2': '#DFE6E9',
    'tuic': '#A29BFE',
    'wireguard': '#74B9FF',
    'naive': '#FD79A8',
    'http': '#FDCB6E',
    'https': '#6C5CE7',
    'socks': '#00B894'
  };
  return colors[protocol?.toLowerCase()] || '#95A5A6';
}

function parseLatency(value) {
  if (value == null) return -1;
  const num = Number(value);
  if (isNaN(num) || num < 0 || num > 100000) return -1;
  return Math.round(num);
}

function getStatusIcon(isWorking) {
  return isWorking ? '✅' : '❌';
}

// Expose utilities globally for non-module scripts
// These functions are called from main.js and other scripts that may not use ES6 imports
if (typeof window !== 'undefined') {
  window.formatTimestamp = formatTimestamp;
  window.getCountryFlag = getCountryFlag;
  window.getProtocolColor = getProtocolColor;
  window.parseLatency = parseLatency;
  window.getStatusIcon = getStatusIcon;
}
