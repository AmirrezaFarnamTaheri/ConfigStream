// SPDX-License-Identifier: AGPL-3.0-or-later
// ConfigStream optional VLESS-over-WebSocket Worker with authenticated
// subscription endpoints. No credentials or fallback routes are baked into
// source; deployment secrets must come from Worker bindings.

import { connect } from 'cloudflare:sockets';

const DEFAULT_WS_PATH = '/ws';
const MAX_WS_MESSAGE_SIZE = 1024 * 1024;
const MIN_SUBSCRIPTION_TOKEN_LENGTH = 32;
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const encoder = new TextEncoder();
const fatalDecoder = new TextDecoder('utf-8', { fatal: true });

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === '/health') {
      return textResponse('OK', 200);
    }

    let config;
    try {
      config = loadConfig(env);
    } catch (error) {
      console.error('subscription worker configuration error', error);
      return textResponse('Worker unavailable', 503);
    }

    if (url.pathname === config.wsPath) {
      const upgrade = request.headers.get('Upgrade');
      if (!upgrade || upgrade.toLowerCase() !== 'websocket') {
        return new Response('Expected Upgrade: websocket', {
          status: 426,
          headers: { 'Cache-Control': 'no-store' },
        });
      }
      return handleVlessWebSocket(config);
    }

    if (url.pathname === '/subscription' || url.pathname.startsWith('/subscription/')) {
      if (!(await authorizeSubscription(request, config.subscriptionToken))) {
        return new Response('Unauthorized', {
          status: 401,
          headers: {
            'Cache-Control': 'no-store',
            'WWW-Authenticate': 'Bearer realm="ConfigStream subscription"',
          },
        });
      }
      return subscriptionResponse(url, config);
    }

    return textResponse('Not found', 404);
  },
};

function loadConfig(env) {
  const uuid = String(env.VLESS_UUID || env.uuid || '').trim().toLowerCase();
  if (!UUID_RE.test(uuid)) {
    throw new Error('VLESS_UUID must be configured as a valid UUID');
  }
  const wsPath = String(env.WS_PATH || DEFAULT_WS_PATH).trim();
  if (
    !wsPath.startsWith('/') ||
    wsPath.length > 128 ||
    wsPath.includes('?') ||
    wsPath.includes('#') ||
    wsPath.includes('..')
  ) {
    throw new Error('WS_PATH must be one bounded absolute path');
  }
  const subscriptionToken = String(env.SUBSCRIPTION_TOKEN || '');
  if (
    subscriptionToken &&
    subscriptionToken.length < MIN_SUBSCRIPTION_TOKEN_LENGTH
  ) {
    throw new Error(
      `SUBSCRIPTION_TOKEN must be empty/disabled or at least ${MIN_SUBSCRIPTION_TOKEN_LENGTH} characters`,
    );
  }
  return {
    uuid,
    uuidBytes: uuidToBytes(uuid),
    wsPath,
    subscriptionToken,
  };
}

async function authorizeSubscription(request, expectedToken) {
  if (!expectedToken || expectedToken.length < MIN_SUBSCRIPTION_TOKEN_LENGTH) {
    return false;
  }
  const authorization = request.headers.get('Authorization') || '';
  if (!authorization.startsWith('Bearer ')) {
    return false;
  }
  const provided = authorization.slice('Bearer '.length);
  if (!provided) {
    return false;
  }
  const [expectedDigest, providedDigest] = await Promise.all([
    crypto.subtle.digest('SHA-256', encoder.encode(expectedToken)),
    crypto.subtle.digest('SHA-256', encoder.encode(provided)),
  ]);
  return constantTimeEqual(
    new Uint8Array(expectedDigest),
    new Uint8Array(providedDigest),
  );
}

function subscriptionResponse(url, config) {
  const host = url.hostname;
  const uri = buildVlessUri(host, config);
  const format = url.pathname.slice('/subscription'.length).replace(/^\/+/, '');

  if (!format || format === 'plain') {
    return secretResponse(uri + '\n', 'text/plain; charset=utf-8');
  }
  if (format === 'base64') {
    return secretResponse(btoa(uri) + '\n', 'text/plain; charset=utf-8');
  }
  if (format === 'clash') {
    const quotedPath = JSON.stringify(config.wsPath);
    const quotedHost = JSON.stringify(host);
    const yaml = `proxies:\n  - name: ConfigStream-BYOW\n    type: vless\n    server: ${quotedHost}\n    port: 443\n    uuid: ${JSON.stringify(config.uuid)}\n    network: ws\n    tls: true\n    servername: ${quotedHost}\n    ws-opts:\n      path: ${quotedPath}\n      headers:\n        Host: ${quotedHost}\n`;
    return secretResponse(yaml, 'application/yaml; charset=utf-8');
  }
  if (format === 'singbox') {
    const payload = {
      outbounds: [
        {
          type: 'vless',
          tag: 'ConfigStream-BYOW',
          server: host,
          server_port: 443,
          uuid: config.uuid,
          tls: { enabled: true, server_name: host },
          transport: {
            type: 'ws',
            path: config.wsPath,
            headers: { Host: host },
          },
        },
      ],
    };
    return secretResponse(
      JSON.stringify(payload, null, 2) + '\n',
      'application/json; charset=utf-8',
    );
  }

  return textResponse('Unknown subscription format', 404);
}

function buildVlessUri(host, config) {
  const params = new URLSearchParams({
    encryption: 'none',
    security: 'tls',
    type: 'ws',
    host,
    path: config.wsPath,
    sni: host,
  });
  return `vless://${config.uuid}@${host}:443?${params.toString()}#ConfigStream-BYOW`;
}

function secretResponse(body, contentType) {
  return new Response(body, {
    status: 200,
    headers: {
      'Cache-Control': 'no-store, private',
      'Content-Type': contentType,
      'Referrer-Policy': 'no-referrer',
      'X-Content-Type-Options': 'nosniff',
    },
  });
}

async function handleVlessWebSocket(config) {
  const pair = new WebSocketPair();
  const [client, server] = Object.values(pair);
  server.accept({ allowHalfOpen: true });

  let socket = null;
  let writer = null;
  let closing = false;
  let messageChain = Promise.resolve();

  const shutdown = async (code = 1000, reason = 'Tunnel closed') => {
    if (closing) {
      return;
    }
    closing = true;
    if (socket) {
      try {
        await socket.close();
      } catch (_error) {
        // Best-effort transport cleanup.
      }
    }
    if (writer) {
      try {
        writer.releaseLock();
      } catch (_error) {
        // The socket may already have invalidated the writer.
      }
    }
    if (server.readyState === WebSocket.READY_STATE_OPEN) {
      try {
        server.close(code, reason);
      } catch (_error) {
        // Peer may close between the readyState check and close().
      }
    }
  };

  const handleMessage = async (data) => {
    const chunk = toBytes(data);
    if (chunk.byteLength === 0 || chunk.byteLength > MAX_WS_MESSAGE_SIZE) {
      await shutdown(1009, 'WebSocket message too large');
      return;
    }

    if (!socket) {
      let parsed;
      try {
        parsed = parseVlessHeader(chunk, config.uuidBytes);
      } catch (_error) {
        await shutdown(1008, 'Invalid VLESS request');
        return;
      }

      try {
        socket = connect({ hostname: parsed.address, port: parsed.port });
        await socket.opened;
        writer = socket.writable.getWriter();
        if (parsed.payload.byteLength > 0) {
          await writer.write(parsed.payload);
        }
      } catch (_error) {
        await shutdown(1011, 'Upstream connection failed');
        return;
      }

      void pipeRemoteToWebSocket(socket, server, parsed.version, shutdown);
      void socket.closed.catch(() => shutdown(1011, 'Upstream socket error'));
      return;
    }

    try {
      await writer.write(chunk);
    } catch (_error) {
      await shutdown(1011, 'Upstream write failed');
    }
  };

  server.addEventListener('message', (event) => {
    messageChain = messageChain.then(() => handleMessage(event.data));
    void messageChain.catch(() => shutdown(1011, 'Tunnel processing failed'));
  });
  server.addEventListener('close', () => {
    void shutdown();
  });
  server.addEventListener('error', () => {
    void shutdown(1011, 'WebSocket error');
  });

  return new Response(null, { status: 101, webSocket: client });
}

function parseVlessHeader(chunk, expectedUuid) {
  if (chunk.byteLength < 24) {
    throw new Error('VLESS header too short');
  }
  const version = chunk[0];
  const presentedUuid = chunk.slice(1, 17);
  if (!constantTimeEqual(presentedUuid, expectedUuid)) {
    throw new Error('invalid VLESS user');
  }

  const optionLength = chunk[17];
  const commandIndex = 18 + optionLength;
  if (commandIndex + 4 > chunk.byteLength) {
    throw new Error('truncated VLESS command');
  }
  const command = chunk[commandIndex];
  if (command !== 1) {
    throw new Error('only VLESS TCP is supported');
  }

  const portIndex = commandIndex + 1;
  const port = (chunk[portIndex] << 8) | chunk[portIndex + 1];
  if (port < 1 || port > 65535 || port === 25) {
    throw new Error('VLESS destination port is not allowed');
  }

  const addressTypeIndex = portIndex + 2;
  const addressType = chunk[addressTypeIndex];
  let cursor = addressTypeIndex + 1;
  let address;

  if (addressType === 1) {
    if (cursor + 4 > chunk.byteLength) {
      throw new Error('truncated IPv4 address');
    }
    const octets = Array.from(chunk.slice(cursor, cursor + 4));
    if (isPrivateIPv4(octets)) {
      throw new Error('private IPv4 destinations are not allowed');
    }
    address = octets.join('.');
    cursor += 4;
  } else if (addressType === 2) {
    if (cursor >= chunk.byteLength) {
      throw new Error('missing domain length');
    }
    const length = chunk[cursor];
    cursor += 1;
    if (length < 1 || length > 253 || cursor + length > chunk.byteLength) {
      throw new Error('invalid domain length');
    }
    address = fatalDecoder.decode(chunk.slice(cursor, cursor + length));
    validatePublicHostname(address);
    cursor += length;
  } else if (addressType === 3) {
    if (cursor + 16 > chunk.byteLength) {
      throw new Error('truncated IPv6 address');
    }
    const bytes = chunk.slice(cursor, cursor + 16);
    if (isPrivateIPv6(bytes)) {
      throw new Error('private IPv6 destinations are not allowed');
    }
    const groups = [];
    for (let index = 0; index < 16; index += 2) {
      groups.push(((bytes[index] << 8) | bytes[index + 1]).toString(16));
    }
    address = groups.join(':');
    cursor += 16;
  } else {
    throw new Error('unsupported VLESS address type');
  }

  return {
    version,
    address,
    port,
    payload: chunk.slice(cursor),
  };
}

async function pipeRemoteToWebSocket(socket, webSocket, version, shutdown) {
  let firstChunk = true;
  try {
    await socket.readable.pipeTo(
      new WritableStream({
        write(chunk) {
          if (webSocket.readyState !== WebSocket.READY_STATE_OPEN) {
            throw new Error('WebSocket closed');
          }
          if (firstChunk) {
            firstChunk = false;
            const response = new Uint8Array(2 + chunk.byteLength);
            response[0] = version;
            response[1] = 0;
            response.set(chunk, 2);
            webSocket.send(response);
          } else {
            webSocket.send(chunk);
          }
        },
      }),
    );
    await shutdown(1000, 'Upstream closed');
  } catch (_error) {
    await shutdown(1011, 'Upstream read failed');
  }
}

function toBytes(data) {
  if (data instanceof ArrayBuffer) {
    return new Uint8Array(data);
  }
  if (ArrayBuffer.isView(data)) {
    return new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
  }
  throw new Error('VLESS WebSocket messages must be binary');
}

function uuidToBytes(uuid) {
  const hex = uuid.replaceAll('-', '');
  const bytes = new Uint8Array(16);
  for (let index = 0; index < bytes.length; index += 1) {
    bytes[index] = Number.parseInt(hex.slice(index * 2, index * 2 + 2), 16);
  }
  return bytes;
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

function validatePublicHostname(hostname) {
  const normalized = hostname.trim().toLowerCase();
  if (
    !normalized ||
    /[\s/@\\]/.test(normalized) ||
    normalized === 'localhost' ||
    normalized.endsWith('.localhost') ||
    normalized.endsWith('.local') ||
    normalized.endsWith('.internal')
  ) {
    throw new Error('local/private hostnames are not allowed');
  }
  const parts = normalized.split('.');
  if (parts.length === 4 && parts.every((part) => /^\d{1,3}$/.test(part))) {
    const octets = parts.map(Number);
    if (octets.some((value) => value > 255) || isPrivateIPv4(octets)) {
      throw new Error('private IPv4 destinations are not allowed');
    }
  }
}

function isPrivateIPv4([a, b, c]) {
  return (
    a === 0 ||
    a === 10 ||
    a === 127 ||
    a >= 224 ||
    (a === 100 && b >= 64 && b <= 127) ||
    (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 168) ||
    (a === 192 && b === 0 && c === 0) ||
    (a === 198 && (b === 18 || b === 19))
  );
}

function isPrivateIPv6(bytes) {
  if (bytes.byteLength !== 16) {
    return true;
  }
  const allZero = bytes.every((value) => value === 0);
  const loopback = bytes.slice(0, 15).every((value) => value === 0) && bytes[15] === 1;
  const uniqueLocal = (bytes[0] & 0xfe) === 0xfc;
  const linkLocal = bytes[0] === 0xfe && (bytes[1] & 0xc0) === 0x80;
  const multicast = bytes[0] === 0xff;
  if (allZero || loopback || uniqueLocal || linkLocal || multicast) {
    return true;
  }
  const ipv4Mapped = bytes.slice(0, 10).every((value) => value === 0) && bytes[10] === 0xff && bytes[11] === 0xff;
  return ipv4Mapped && isPrivateIPv4(Array.from(bytes.slice(12, 16)));
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
