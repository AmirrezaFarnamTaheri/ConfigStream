// SPDX-License-Identifier: AGPL-3.0-or-later
// Bounded DNS-over-HTTPS relay for Cloudflare Pages Functions.

const UPSTREAM_DNS_PROVIDERS = [
  'https://cloudflare-dns.com/dns-query',
  'https://dns.google/dns-query',
];
const MAX_DNS_REQUEST_SIZE = 4096;
const MAX_DNS_RESPONSE_SIZE = 65535;
const MAX_PROVIDER_ATTEMPTS = 2;
const REQUEST_TIMEOUT_MS = 6000;
const RATE_LIMIT_REQUESTS = 150;
const RATE_LIMIT_WINDOW_MS = 60000;
const MAX_CONCURRENT_REQUESTS = 80;
const rateLimitMap = new Map();
let concurrentRequests = 0;

export async function onRequest(context) {
  return handleRequest(context.request);
}

async function handleRequest(request) {
  const url = new URL(request.url);

  if (url.pathname === '/health') {
    return textResponse('OK', 200);
  }
  if (url.pathname === '/apple') {
    return generateAppleProfile(request.url);
  }
  if (url.pathname === '/') {
    return homePage(request.url);
  }
  if (url.pathname !== '/dns-query') {
    return textResponse('Not found', 404);
  }
  if (request.method === 'OPTIONS') {
    return handleOptions();
  }
  if (request.method !== 'GET' && request.method !== 'POST') {
    return new Response('Method not allowed', {
      status: 405,
      headers: { Allow: 'GET, POST, OPTIONS', 'Cache-Control': 'no-store' },
    });
  }

  const clientIP = request.headers.get('CF-Connecting-IP') || 'unknown';
  if (!checkRateLimit(clientIP)) {
    return new Response('Rate limit exceeded', {
      status: 429,
      headers: { 'Retry-After': '60', 'Cache-Control': 'no-store' },
    });
  }
  if (concurrentRequests >= MAX_CONCURRENT_REQUESTS) {
    return new Response('Server busy', {
      status: 503,
      headers: { 'Retry-After': '5', 'Cache-Control': 'no-store' },
    });
  }

  concurrentRequests += 1;
  try {
    const dnsRequest = await parseDNSRequest(request, url);
    const dnsResponse = await queryDNS(dnsRequest);
    return new Response(dnsResponse, { status: 200, headers: dnsHeaders() });
  } catch (_error) {
    return textResponse('DNS query failed', 502);
  } finally {
    concurrentRequests -= 1;
  }
}

async function parseDNSRequest(request, url) {
  let wire;
  let dnsParam = null;

  if (request.method === 'GET') {
    if (url.searchParams.size !== 1 || !url.searchParams.has('dns')) {
      throw new Error('GET requests require only the dns parameter');
    }
    dnsParam = url.searchParams.get('dns') || '';
    wire = decodeBase64Url(dnsParam);
  } else {
    const contentType = (request.headers.get('Content-Type') || '')
      .split(';', 1)[0]
      .trim()
      .toLowerCase();
    if (contentType !== 'application/dns-message') {
      throw new Error('invalid DNS content type');
    }
    const declaredLength = Number(request.headers.get('Content-Length') || '0');
    if (Number.isFinite(declaredLength) && declaredLength > MAX_DNS_REQUEST_SIZE) {
      throw new Error('DNS request too large');
    }
    wire = new Uint8Array(await request.arrayBuffer());
  }

  validateDNSQuery(wire);
  return { method: request.method, dnsParam, wire };
}

function validateDNSQuery(wire) {
  if (wire.byteLength < 12 || wire.byteLength > MAX_DNS_REQUEST_SIZE) {
    throw new Error('DNS request size is out of bounds');
  }
  if ((wire[2] & 0x80) !== 0) {
    throw new Error('DNS request is a response, not a query');
  }
  const questionCount = (wire[4] << 8) | wire[5];
  if (questionCount === 0) {
    throw new Error('DNS request has no questions');
  }
}

function decodeBase64Url(value) {
  if (!value || value.length > Math.ceil((MAX_DNS_REQUEST_SIZE * 4) / 3) + 4) {
    throw new Error('invalid dns parameter');
  }
  if (!/^[A-Za-z0-9_-]+={0,2}$/.test(value)) {
    throw new Error('invalid dns parameter');
  }
  const unpadded = value.replace(/=+$/, '');
  const standard = unpadded.replace(/-/g, '+').replace(/_/g, '/');
  const padded = standard + '='.repeat((4 - (standard.length % 4)) % 4);
  let binary;
  try {
    binary = atob(padded);
  } catch (_error) {
    throw new Error('invalid dns parameter');
  }
  const wire = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    wire[index] = binary.charCodeAt(index);
  }
  return wire;
}

async function queryDNS(dnsRequest) {
  const startIndex = crypto.getRandomValues(new Uint32Array(1))[0] % UPSTREAM_DNS_PROVIDERS.length;
  let lastError = null;

  for (let attempt = 0; attempt < Math.min(MAX_PROVIDER_ATTEMPTS, UPSTREAM_DNS_PROVIDERS.length); attempt += 1) {
    const provider = UPSTREAM_DNS_PROVIDERS[(startIndex + attempt) % UPSTREAM_DNS_PROVIDERS.length];
    try {
      return await queryProvider(provider, dnsRequest);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error('no DNS provider available');
}

async function queryProvider(provider, dnsRequest) {
  const upstream = new URL(provider);
  const headers = new Headers({
    Accept: 'application/dns-message',
    'User-Agent': 'ConfigStream-DoH-Relay/1.0',
  });
  let body;
  if (dnsRequest.method === 'GET') {
    upstream.searchParams.set('dns', dnsRequest.dnsParam);
  } else {
    headers.set('Content-Type', 'application/dns-message');
    body = dnsRequest.wire.slice().buffer;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response;
  try {
    response = await fetch(upstream, {
      method: dnsRequest.method,
      headers,
      body,
      redirect: 'error',
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    throw new Error(`upstream HTTP ${response.status}`);
  }
  const contentType = (response.headers.get('Content-Type') || '').toLowerCase();
  if (!contentType.includes('application/dns-message')) {
    throw new Error('invalid upstream content type');
  }
  const declaredLength = Number(response.headers.get('Content-Length') || '0');
  if (Number.isFinite(declaredLength) && declaredLength > MAX_DNS_RESPONSE_SIZE) {
    throw new Error('DNS response too large');
  }

  const responseWire = new Uint8Array(await response.arrayBuffer());
  validateDNSResponse(dnsRequest.wire, responseWire);
  return responseWire;
}

function validateDNSResponse(requestWire, responseWire) {
  if (responseWire.byteLength < 12 || responseWire.byteLength > MAX_DNS_RESPONSE_SIZE) {
    throw new Error('DNS response size is out of bounds');
  }
  if ((responseWire[2] & 0x80) === 0) {
    throw new Error('upstream payload is not a DNS response');
  }
  if (requestWire[0] !== responseWire[0] || requestWire[1] !== responseWire[1]) {
    throw new Error('DNS transaction ID mismatch');
  }
}

function checkRateLimit(clientIP) {
  const now = Date.now();
  const existing = rateLimitMap.get(clientIP);
  if (!existing || now >= existing.resetAt) {
    rateLimitMap.set(clientIP, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    cleanupRateLimits(now);
    return true;
  }
  if (existing.count >= RATE_LIMIT_REQUESTS) {
    return false;
  }
  existing.count += 1;
  return true;
}

function cleanupRateLimits(now) {
  if (rateLimitMap.size <= 2048) {
    return;
  }
  for (const [key, value] of rateLimitMap) {
    if (now >= value.resetAt) {
      rateLimitMap.delete(key);
    }
  }
  while (rateLimitMap.size > 2048) {
    rateLimitMap.delete(rateLimitMap.keys().next().value);
  }
}

function dnsHeaders() {
  return {
    'Content-Type': 'application/dns-message',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Accept',
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
  };
}

function handleOptions() {
  return new Response(null, {
    status: 204,
    headers: { ...dnsHeaders(), 'Access-Control-Max-Age': '86400' },
  });
}

function generateAppleProfile(requestUrl) {
  const hostname = new URL(requestUrl).hostname;
  const dohUrl = `https://${hostname}/dns-query`;
  const profileUUID = crypto.randomUUID();
  const dnsUUID = crypto.randomUUID();
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>PayloadContent</key><array><dict>
<key>DNSSettings</key><dict><key>DNSProtocol</key><string>HTTPS</string><key>ServerURL</key><string>${escapeXML(dohUrl)}</string></dict>
<key>PayloadDisplayName</key><string>ConfigStream DoH</string>
<key>PayloadIdentifier</key><string>org.configstream.dns</string>
<key>PayloadType</key><string>com.apple.dnsSettings.managed</string>
<key>PayloadUUID</key><string>${dnsUUID}</string><key>PayloadVersion</key><integer>1</integer>
</dict></array>
<key>PayloadDisplayName</key><string>ConfigStream DoH - ${escapeXML(hostname)}</string>
<key>PayloadIdentifier</key><string>org.configstream.doh</string>
<key>PayloadType</key><string>Configuration</string>
<key>PayloadUUID</key><string>${profileUUID}</string><key>PayloadVersion</key><integer>1</integer>
</dict></plist>`;
  return new Response(xml, {
    status: 200,
    headers: {
      'Content-Type': 'application/x-apple-aspen-config; charset=utf-8',
      'Content-Disposition': 'attachment; filename="configstream-doh.mobileconfig"',
      'Cache-Control': 'no-store',
    },
  });
}

function homePage(requestUrl) {
  const endpoint = new URL('/dns-query', requestUrl).href;
  return new Response(`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ConfigStream DoH</title></head><body><main><h1>ConfigStream DoH relay</h1><p>Endpoint: <code>${escapeHTML(endpoint)}</code></p><p><a href="/apple">Apple configuration profile</a></p></main></body></html>`, {
    status: 200,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Content-Security-Policy': "default-src 'none'; base-uri 'none'; frame-ancestors 'none'",
      'Cache-Control': 'public, max-age=3600',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'Referrer-Policy': 'no-referrer',
    },
  });
}

function textResponse(message, status) {
  return new Response(message, {
    status,
    headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' },
  });
}

function escapeHTML(value) {
  return value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
}

function escapeXML(value) {
  return escapeHTML(value);
}
