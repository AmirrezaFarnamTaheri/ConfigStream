// tools/worker.js - The "Platinum" Bridge
// ConfigStream BYOW Relay v2.0
// Deploy this to Cloudflare Workers (Free Tier)
// Enhanced with masquerading (fake website) and dynamic routing

// 1. CONFIGURATION
const PROXY_PATH = "/my-secret-tunnel"; // Only tunnel traffic here
const FAKE_SITE_URL = "https://www.kernel.org"; // The "Mask" - harmless technical site

// Optional: Restrict usage to a specific UUID (leave empty for public)
const userID = ''; // Set in Worker environment variables if needed

// Default backend (can be overridden via path: /IP/PORT)
const DEFAULT_PROXY_IP = '127.0.0.1'; // User must configure this
const DEFAULT_PROXY_PORT = 443;
const DEFAULT_PROXY_TYPE = 'vless'; // vless, vmess, or trojan

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // 1. The "Secret Handshake" - Only accept WebSocket connections on the specific path
    if (url.pathname === PROXY_PATH && request.headers.get("Upgrade") === "websocket") {
        return handleProxy(request, url);
    }
    
    // 2. The "Grey Area" Masquerade - For everyone else (Active Probes, Censors), act like a harmless mirror
    // Fetch content from a legitimate technical site
    try {
        const fakeResponse = await fetch(FAKE_SITE_URL + url.pathname, {
            headers: {
                "User-Agent": "Mozilla/5.0 (Compatible; ConfigStream/1.0)",
                "Referer": FAKE_SITE_URL
            }
        });
        
        // Return the fake content seamlessly
        return new Response(fakeResponse.body, {
            status: fakeResponse.status,
            headers: fakeResponse.headers,
        });
    } catch (error) {
        // Fallback to simple response if fetch fails
        if (url.pathname === '/health') {
            return new Response('OK', { status: 200 });
        }
        return new Response('ConfigStream BYOW Relay Active', { status: 200 });
    }
  }
};

// Proxy handler function
async function handleProxy(request, url) {
    const upgradeHeader = request.headers.get('Upgrade');
    if (!upgradeHeader || upgradeHeader !== 'websocket') {
        return new Response('Expected Upgrade: websocket', { status: 426 });
    }

    // Parse destination from path if you want "Dynamic" routing
    // e.g., wss://worker.dev/my-secret-tunnel/1.2.3.4/8080
    let targetHost = DEFAULT_PROXY_IP;
    let targetPort = DEFAULT_PROXY_PORT;
    
    const pathParts = url.pathname.split('/').filter(p => p);
    // Skip PROXY_PATH part, check for IP:PORT pattern
    if (pathParts.length >= 3 && isValidIP(pathParts[1])) {
        targetHost = pathParts[1];
        targetPort = parseInt(pathParts[2]) || DEFAULT_PROXY_PORT;
    }

    // Create WebSocket pair
    const webSocket = new WebSocketPair();
    const [client, server] = Object.values(webSocket);

    // Accept the client connection
    server.accept();

    // Note: Full TCP tunneling requires Cloudflare's connect() API
    // which may have restrictions on free tier. For now, this is a template.
    // In production, you would:
    // 1. Use connect() to establish TCP connection to targetHost:targetPort
    // 2. Pipe WebSocket messages to TCP and vice versa
    // 3. Handle errors and cleanup

    // Simplified echo for testing (replace with actual tunneling)
    server.addEventListener('message', event => {
        // In production: forward to TCP socket
        // For now: echo back (testing only)
        if (server.readyState === WebSocket.READY_STATE_OPEN) {
            server.send(event.data);
        }
    });

    return new Response(null, {
        status: 101,
        webSocket: client,
    });
}

// Helper to check if path is an IP (for dynamic routing)
function isValidIP(ip) {
    return /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(ip);
}
