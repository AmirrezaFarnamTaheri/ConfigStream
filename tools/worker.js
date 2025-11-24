// Cloudflare Worker Script for "Bring Your Own Worker" (BYOW)
// Acts as a VLESS-over-WebSocket relay.

// To deploy:
// 1. Copy this code.
// 2. Go to Cloudflare Dashboard -> Workers -> Create Service.
// 3. Paste and Deploy.

const userID = 'user-generated-uuid'; // REPLACE THIS with your UUID
const proxyIP = '1.2.3.4'; // Default fallback, or dynamic via header
const proxyPort = 443;

addEventListener("fetch", event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const upgradeHeader = request.headers.get("Upgrade");
  if (!upgradeHeader || upgradeHeader !== "websocket") {
    return new Response("ConfigStream Worker is Alive", { status: 200 });
  }

  // Extract target from custom header if present (Client-Side Chaining)
  let targetIP = proxyIP;
  let targetPort = proxyPort;

  const forwardHeader = request.headers.get("X-Forward-To");
  if (forwardHeader) {
      const parts = forwardHeader.split(":");
      if (parts.length === 2) {
          targetIP = parts[0];
          targetPort = parseInt(parts[1]);
      }
  }

  const webSocket = new WebSocketPair();
  const [client, server] = Object.values(webSocket);

  server.accept();

  // Dial the target TCP socket
  // Note: Standard Workers cannot dial arbitrary TCP ports directly unless using connect() (Beta)
  // or if wrapping traffic via WebSocket to another endpoint.
  // Assuming the target allows WebSocket connections (VLESS-ws).

  // For raw TCP, we need 'cloudflare:sockets' (connect).
  // This example assumes VLESS-over-WS relay to another WS endpoint.

  // Implementation for TCP dialing (requires Workers Unbound or specific plan features):
  try {
      const socket = connect({ hostname: targetIP, port: targetPort });
      const writer = socket.writable.getWriter();
      const reader = socket.readable.getReader();

      server.addEventListener('message', async event => {
          await writer.write(event.data);
      });

      // Pump back
      (async () => {
          while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              server.send(value);
          }
          server.close();
      })();

      return new Response(null, {
          status: 101,
          webSocket: client,
      });

  } catch (err) {
      return new Response(err.stack, { status: 500 });
  }
}
