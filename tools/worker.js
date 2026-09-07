// SPDX-License-Identifier: AGPL-3.0-or-later
// ConfigStream BYOW private bridge for Cloudflare Workers.
//
// Required Worker bindings/secrets:
//   TUNNEL_TOKEN - high-entropy bearer token (at least 32 characters)
//   PROXY_HOST   - one operator-controlled public TCP upstream hostname/IP
//   PROXY_PORT   - upstream TCP port (1..65535, excluding SMTP port 25)
// Optional:
//   PROXY_PATH   - WebSocket endpoint path (default: /my-secret-tunnel)
//   FAKE_SITE_URL - HTTPS origin used for non-tunnel masquerade responses

import { connect } from 'cloudflare:sockets';

const DEFAULT_PROXY_PATH = '/my-secret-tunnel';
const DEFAULT_FAKE_SITE_URL = 'https://www.kernel.org/';
const MIN_TOKEN_LENGTH = 32;
const encoder = new TextEncoder();

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === '/health') {
      return new Response('OK', {
        status: 200,
        headers: { 'Cache-Control': 'no-store', 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }

    let proxyPath;
    try {
      proxyPath = parseProxyPath(env.PROXY_PATH);
    } catch (error) {
      return misconfiguredResponse(error);
    }

    if (url.pathname === proxyPath) {
      const upgrade = request.headers.get('Upgrade');
      if (!upgrade || upgrade.toLowerCase() !== 'websocket') {
        return new Response('Expected Upgrade: websocket', { status: 426 });
      }

      let config;
      try {
        config = parseProxyConfig(env);
      } catch (error) {
        return misconfiguredResponse(error);
      }

      if (!(await isAuthorized(request, config.token))) {
        return new Response('Unauthorized', {
          status: 401,
          headers: {
            'Cache-Control': 'no-store',
            'WWW-Authenticate': 'Bearer realm="ConfigStream BYOW"',
          },
        });
      }

      return handleProxy(config);
    }

    return masquerade(url, env.FAKE_SITE_URL);
  },
};

function parseProxyPath(rawPath) {
  const path = String(rawPath || DEFAULT_PROXY_PATH).trim();
  if (!path.startsWith('/') || path.includes('?') || path.includes('#') || path.includes('..')) {
    throw new Error('PROXY_PATH must be one absolute URL path without query, fragment, or traversal');
  }
  return path;
}

function parseProxyConfig(env) {
  const host = String(env.PROXY_HOST || '').trim();
  const port = Number(String(env.PROXY_PORT || '').trim());
  const token = String(env.TUNNEL_TOKEN || '');

  if (!host || /[\s/]/.test(host)) {
    throw new Error('PROXY_HOST must be one bare hostname or IP address');
  }
  if (!Number.isInteger(port) || port < 1 || port > 65535 || port === 25) {
    throw new Error('PROXY_PORT must be an integer from 1 through 65535 except 25');
  }
  if (token.length < MIN_TOKEN_LENGTH) {
    throw new Error(`TUNNEL_TOKEN must contain at least ${MIN_TOKEN_LENGTH} characters`);
  }

  return { host, port, token };
}

async function isAuthorized(request, expectedToken) {
  const authorization = request.headers.get('Authorization') || '';
  const prefix = 'Bearer ';
  if (!authorization.startsWith(prefix)) {
    return false;
  }
  const providedToken = authorization.slice(prefix.length);
  if (!providedToken) {
    return false;
  }

  const [expectedDigest, providedDigest] = await Promise.all([
    crypto.subtle.digest('SHA-256', encoder.encode(expectedToken)),
    crypto.subtle.digest('SHA-256', encoder.encode(providedToken)),
  ]);
  return constantTimeEqual(
    new Uint8Array(expectedDigest),
    new Uint8Array(providedDigest),
  );
}

function constantTimeEqual(left, right) {
  if (left.byteLength !== right.byteLength) {
    return false;
  }
  let difference = 0;
  for (let index = 0; index < left.byteLength; index += 1) {
    difference |= left[index] ^ right[index];
  }
  return difference === 0;
}

async function handleProxy(config) {
  let socket;
  try {
    socket = connect({ hostname: config.host, port: config.port });
    await socket.opened;
  } catch (_error) {
    if (socket) {
      try {
        await socket.close();
      } catch (_closeError) {
        // The original connection failure is the useful client-facing signal.
      }
    }
    return new Response('Upstream connection failed', {
      status: 502,
      headers: { 'Cache-Control': 'no-store' },
    });
  }

  const pair = new WebSocketPair();
  const [client, server] = Object.values(pair);
  server.accept({ allowHalfOpen: true });
  const writer = socket.writable.getWriter();
  let shuttingDown = false;

  const shutdown = async (code = 1000, reason = 'Tunnel closed') => {
    if (shuttingDown) {
      return;
    }
    shuttingDown = true;
    try {
      await socket.close();
    } catch (_error) {
      // Best-effort cleanup; close errors do not make the tunnel recoverable.
    }
    try {
      writer.releaseLock();
    } catch (_error) {
      // The stream may already have released its writer during socket close.
    }
    if (server.readyState === WebSocket.READY_STATE_OPEN) {
      try {
        server.close(code, reason);
      } catch (_error) {
        // The peer may have closed between readyState inspection and close().
      }
    }
  };

  server.addEventListener('message', (event) => {
    void (async () => {
      let chunk;
      if (typeof event.data === 'string') {
        chunk = encoder.encode(event.data);
      } else if (event.data instanceof ArrayBuffer) {
        chunk = new Uint8Array(event.data);
      } else if (ArrayBuffer.isView(event.data)) {
        chunk = new Uint8Array(
          event.data.buffer,
          event.data.byteOffset,
          event.data.byteLength,
        );
      } else {
        await shutdown(1003, 'Unsupported WebSocket message type');
        return;
      }
      try {
        await writer.write(chunk);
      } catch (_error) {
        await shutdown(1011, 'Upstream write failed');
      }
    })();
  });

  server.addEventListener('close', () => {
    void shutdown();
  });
  server.addEventListener('error', () => {
    void shutdown(1011, 'WebSocket error');
  });

  void socket.readable
    .pipeTo(
      new WritableStream({
        write(chunk) {
          if (server.readyState !== WebSocket.READY_STATE_OPEN) {
            throw new Error('WebSocket is no longer open');
          }
          server.send(chunk);
        },
      }),
    )
    .then(
      () => shutdown(1000, 'Upstream closed'),
      () => shutdown(1011, 'Upstream read failed'),
    );

  void socket.closed.catch(() => shutdown(1011, 'Upstream socket error'));

  return new Response(null, {
    status: 101,
    webSocket: client,
  });
}

async function masquerade(requestUrl, rawFakeSiteUrl) {
  let fakeSite;
  try {
    fakeSite = new URL(String(rawFakeSiteUrl || DEFAULT_FAKE_SITE_URL));
    if (fakeSite.protocol !== 'https:') {
      throw new Error('FAKE_SITE_URL must use HTTPS');
    }
  } catch (_error) {
    fakeSite = new URL(DEFAULT_FAKE_SITE_URL);
  }

  const upstream = new URL(requestUrl.pathname + requestUrl.search, fakeSite);
  try {
    const fakeResponse = await fetch(upstream, {
      redirect: 'manual',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Compatible; ConfigStream/1.0)',
        Referer: fakeSite.origin + '/',
      },
    });
    const headers = new Headers(fakeResponse.headers);
    headers.delete('set-cookie');
    headers.delete('set-cookie2');
    return new Response(fakeResponse.body, {
      status: fakeResponse.status,
      statusText: fakeResponse.statusText,
      headers,
    });
  } catch (_error) {
    return new Response('Not Found', {
      status: 404,
      headers: { 'Cache-Control': 'no-store', 'Content-Type': 'text/plain; charset=utf-8' },
    });
  }
}

function misconfiguredResponse(error) {
  console.error('BYOW relay configuration error', error);
  return new Response('Relay unavailable', {
    status: 503,
    headers: { 'Cache-Control': 'no-store' },
  });
}
