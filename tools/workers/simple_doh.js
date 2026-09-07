// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Minimal DNS-over-HTTPS relay for Cloudflare Workers.
 *
 * The worker deliberately forwards only DNS wire data and protocol-required
 * headers. Client cookies, authorization headers, Cloudflare metadata, and
 * arbitrary query parameters never cross the upstream trust boundary.
 */

const DOH_PROVIDERS = [
  'https://cloudflare-dns.com/dns-query',
  'https://dns.google/dns-query',
];
const MAX_DNS_REQUEST_SIZE = 4096;
const MAX_DNS_RESPONSE_SIZE = 65535;
const MAX_PROVIDER_ATTEMPTS = 2;
const UPSTREAM_TIMEOUT_MS = 6000;

export default {
  async fetch(request) {
    return handleRequest(request);
  },
};

async function handleRequest(request) {
  const url = new URL(request.url);

  if (url.pathname === '/') {
    return serveLandingPage(request.url);
  }
  if (url.pathname === '/dns-encoding') {
    return serveDNSEncodingExplanation();
  }
  if (url.pathname !== '/dns-query') {
    return textResponse('Not found', 404);
  }
  if (request.method === 'OPTIONS') {
    return handleCORS();
  }
  if (request.method !== 'GET' && request.method !== 'POST') {
    return new Response('Method not allowed', {
      status: 405,
      headers: {
        Allow: 'GET, POST, OPTIONS',
        'Cache-Control': 'no-store',
        'Content-Type': 'text/plain; charset=utf-8',
      },
    });
  }

  let dnsRequest;
  try {
    dnsRequest = await parseDNSRequest(request, url);
  } catch (error) {
    return textResponse(error instanceof Error ? error.message : 'Invalid DNS request', 400);
  }

  const startIndex = crypto.getRandomValues(new Uint32Array(1))[0] % DOH_PROVIDERS.length;
  for (let attempt = 0; attempt < Math.min(MAX_PROVIDER_ATTEMPTS, DOH_PROVIDERS.length); attempt += 1) {
    const provider = DOH_PROVIDERS[(startIndex + attempt) % DOH_PROVIDERS.length];
    try {
      const responseBody = await queryProvider(provider, dnsRequest);
      return new Response(responseBody, {
        status: 200,
        headers: dnsResponseHeaders(),
      });
    } catch (_error) {
      // Try the next bounded provider. No client headers or mutable Request body
      // are reused across attempts.
    }
  }

  return textResponse('All DNS providers are unavailable', 503);
}

async function parseDNSRequest(request, url) {
  if (request.method === 'GET') {
    if (url.searchParams.size !== 1 || !url.searchParams.has('dns')) {
      throw new Error('GET requests require only the dns query parameter');
    }
    const dnsParam = url.searchParams.get('dns') || '';
    const decoded = decodeBase64Url(dnsParam);
    if (decoded.byteLength === 0 || decoded.byteLength > MAX_DNS_REQUEST_SIZE) {
      throw new Error('DNS request size is out of bounds');
    }
    return { method: 'GET', dnsParam, body: null };
  }

  const contentType = (request.headers.get('Content-Type') || '')
    .split(';', 1)[0]
    .trim()
    .toLowerCase();
  if (contentType !== 'application/dns-message') {
    throw new Error('POST Content-Type must be application/dns-message');
  }
  const declaredLength = Number(request.headers.get('Content-Length') || '0');
  if (Number.isFinite(declaredLength) && declaredLength > MAX_DNS_REQUEST_SIZE) {
    throw new Error('DNS request size is out of bounds');
  }

  const body = await request.arrayBuffer();
  if (body.byteLength === 0 || body.byteLength > MAX_DNS_REQUEST_SIZE) {
    throw new Error('DNS request size is out of bounds');
  }
  return { method: 'POST', dnsParam: null, body };
}

function decodeBase64Url(value) {
  if (!value || value.length > Math.ceil((MAX_DNS_REQUEST_SIZE * 4) / 3) + 4) {
    throw new Error('Invalid dns query parameter');
  }
  if (!/^[A-Za-z0-9_-]+={0,2}$/.test(value)) {
    throw new Error('Invalid dns query parameter');
  }
  const firstPadding = value.indexOf('=');
  if (firstPadding !== -1 && firstPadding < value.length - 2) {
    throw new Error('Invalid dns query parameter');
  }

  const unpadded = value.replace(/=+$/, '');
  const standard = unpadded.replace(/-/g, '+').replace(/_/g, '/');
  const padded = standard + '='.repeat((4 - (standard.length % 4)) % 4);
  let binary;
  try {
    binary = atob(padded);
  } catch (_error) {
    throw new Error('Invalid dns query parameter');
  }
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

async function queryProvider(provider, dnsRequest) {
  const upstreamUrl = new URL(provider);
  const headers = new Headers({
    Accept: 'application/dns-message',
    'User-Agent': 'ConfigStream-DoH-Relay/1.0',
  });

  let body;
  if (dnsRequest.method === 'GET') {
    upstreamUrl.searchParams.set('dns', dnsRequest.dnsParam);
  } else {
    headers.set('Content-Type', 'application/dns-message');
    body = dnsRequest.body.slice(0);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);
  let response;
  try {
    response = await fetch(upstreamUrl, {
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
    throw new Error(`upstream returned HTTP ${response.status}`);
  }
  const contentType = (response.headers.get('Content-Type') || '').toLowerCase();
  if (!contentType.includes('application/dns-message')) {
    throw new Error('upstream returned an invalid content type');
  }
  const declaredLength = Number(response.headers.get('Content-Length') || '0');
  if (Number.isFinite(declaredLength) && declaredLength > MAX_DNS_RESPONSE_SIZE) {
    throw new Error('upstream DNS response is too large');
  }

  const responseBody = await response.arrayBuffer();
  if (responseBody.byteLength === 0 || responseBody.byteLength > MAX_DNS_RESPONSE_SIZE) {
    throw new Error('upstream DNS response size is out of bounds');
  }
  return responseBody;
}

function dnsResponseHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Accept',
    'Cache-Control': 'no-store',
    'Content-Type': 'application/dns-message',
    'X-Content-Type-Options': 'nosniff',
  };
}

function handleCORS() {
  return new Response(null, {
    status: 204,
    headers: {
      ...dnsResponseHeaders(),
      'Access-Control-Max-Age': '86400',
    },
  });
}

function serveLandingPage(requestUrl) {
  const endpoint = new URL('/dns-query', requestUrl).href;
  return htmlResponse(`<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ConfigStream DoH Relay</title></head>
<body><main><h1>ConfigStream DoH Relay</h1><p>Endpoint: <code>${escapeHtml(endpoint)}</code></p><p>The relay accepts RFC 8484 GET and POST DNS wire messages and uses bounded failover between standard public resolvers.</p><p><a href="/dns-encoding">DNS encoding notes</a></p></main></body>
</html>`);
}

function serveDNSEncodingExplanation() {
  return htmlResponse(`<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DoH encoding</title></head>
<body><main><h1>DNS-over-HTTPS encoding</h1><p>GET requests use a base64url-encoded DNS wire message in the <code>dns</code> parameter. POST requests send the DNS wire message as <code>application/dns-message</code>.</p><p><a href="/">Back</a></p></main></body>
</html>`);
}

function htmlResponse(html) {
  return new Response(html, {
    status: 200,
    headers: {
      'Cache-Control': 'public, max-age=3600',
      'Content-Security-Policy': "default-src 'none'; style-src 'none'; img-src 'none'; base-uri 'none'; frame-ancestors 'none'",
      'Content-Type': 'text/html; charset=utf-8',
      'Referrer-Policy': 'no-referrer',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
    },
  });
}

function textResponse(message, status) {
  return new Response(message, {
    status,
    headers: {
      'Cache-Control': 'no-store',
      'Content-Type': 'text/plain; charset=utf-8',
    },
  });
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}
