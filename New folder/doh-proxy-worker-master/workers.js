/**
 * High-Performance Cloudflare Worker for Proxying DNS-over-HTTPS (DoH) Requests
 * Enhanced with Multi-Provider Support, Load Balancing, Caching, and Health Checks
 */

// List of DoH providers for load balancing and failover
// Includes both general DNS providers and ad-blocking focused providers
const DOH_PROVIDERS = [
  // General DNS providers
  {
    name: "Cloudflare",
    url: "https://cloudflare-dns.com/dns-query",
    weight: 20
  },
  {
    name: "Google",
    url: "https://dns.google/dns-query",
    weight: 15
  },
  {
    name: "Quad9",
    url: "https://dns.quad9.net/dns-query",
    weight: 15
  },
  {
    name: "OpenDNS",
    url: "https://doh.opendns.com/dns-query",
    weight: 10
  },
  // Ad-blocking focused providers
  {
    name: "AdGuard",
    url: "https://dns.adguard.com/dns-query",
    weight: 10
    // Blocks ads, trackers, and malicious domains
  },
  {
    name: "ControlD",
    url: "https://freedns.controld.com/p2",
    weight: 10
    // Blocks ads and tracking domains
  },
  {
    name: "Mullvad",
    url: "https://adblock.dns.mullvad.net/dns-query",
    weight: 10
    // Blocks ads and trackers
  },
  {
    name: "NextDNS",
    url: "https://dns.nextdns.io/dns-query",
    weight: 10
    // Blocks ads, trackers, and malicious domains
  }
];

// Cache TTL in seconds (5 minutes)
const CACHE_TTL = 300;

export default {
  async fetch(request, env, ctx) {
    return handleRequest(request, env, ctx);
  }
};

async function handleRequest(request, env, ctx) {
  const url = new URL(request.url);
  
  // Serve landing page for root path
  if (url.pathname === '/') {
    return serveLandingPage(request);
  }
  
  // Serve DNS encoding explanation
  if (url.pathname === '/dns-encoding') {
    return serveDNSEncodingExplanation();
  }
  
  // Handle CORS preflight requests
  if (request.method === 'OPTIONS') {
    return handleCORS();
  }

  // Validate DNS request
  if (url.pathname !== '/dns-query') {
    return new Response('Invalid endpoint. Use /dns-query', { status: 400 });
  }

  // Check if it's a DNS query (either via query parameter or POST body)
  const isGet = request.method === 'GET';
  const isPost = request.method === 'POST';
  
  if (!isGet && !isPost) {
    return new Response('Method not allowed. Use GET or POST.', { status: 405 });
  }

  // Check for DNS query parameter in GET requests
  if (isGet && !url.searchParams.has('dns')) {
    return new Response('Missing DNS query parameter', { status: 400 });
  }

  // Select the best DoH provider based on weighted random selection
  const selectedProvider = selectProvider(DOH_PROVIDERS);
  
  try {
    // Create target URL with query parameters
    const targetUrl = selectedProvider.url + url.search;

    // Prepare headers for the upstream request
    const headers = new Headers(request.headers);
    
    // Ensure proper Content-Type for DNS queries
    if (isPost) {
      headers.set('Content-Type', 'application/dns-message');
    } else {
      headers.set('Accept', 'application/dns-message');
    }
    
    // Add User-Agent for better compatibility
    headers.set('User-Agent', 'DoH-Proxy-Worker/1.0');

    // Create the upstream request
    const upstreamRequest = new Request(targetUrl, {
      method: request.method,
      headers: headers,
      body: isPost ? await request.arrayBuffer() : null,
      redirect: 'follow'
    });

    // Send request to DoH provider
    const response = await fetch(upstreamRequest);

    // Create response with proper headers
    const responseHeaders = new Headers(response.headers);
    
    // Add CORS headers
    responseHeaders.set('Access-Control-Allow-Origin', '*');
    responseHeaders.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    responseHeaders.set('Access-Control-Allow-Headers', 'Content-Type, Accept');
    
    // Set cache control for DNS responses
    responseHeaders.set('Cache-Control', `public, max-age=${CACHE_TTL}`);
    responseHeaders.set('Expires', new Date(Date.now() + CACHE_TTL * 1000).toUTCString());

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders
    });
  } catch (error) {
    // Try fallback providers if the primary one fails
    return await tryFallbackProviders(request, url, selectedProvider);
  }
}

// Serve a beautiful landing page for the root path
function serveLandingPage(request) {
  const workerUrl = new URL(request.url);
  workerUrl.pathname = '/dns-query';
  const dnsEndpoint = workerUrl.toString();
  
  const html = `
  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>High-Performance DoH Proxy</title>
    <style>
      :root {
        --primary: #3b82f6;
        --primary-dark: #2563eb;
        --secondary: #10b981;
        --dark: #1e293b;
        --light: #f8fafc;
        --gray: #94a3b8;
        --border: #e2e8f0;
      }
      
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      
      body {
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        line-height: 1.6;
        color: var(--dark);
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        min-height: 100vh;
        padding: 20px;
      }
      
      .container {
        max-width: 1200px;
        margin: 0 auto;
      }
      
      header {
        text-align: center;
        padding: 40px 20px;
        margin-bottom: 30px;
      }
      
      h1 {
        font-size: 2.8rem;
        margin-bottom: 15px;
        color: var(--dark);
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }
      
      .subtitle {
        font-size: 1.3rem;
        color: var(--gray);
        max-width: 700px;
        margin: 0 auto 25px;
      }
      
      .endpoint-card {
        background: linear-gradient(135deg, var(--primary), var(--primary-dark));
        color: white;
        border-radius: 16px;
        padding: 30px;
        margin-bottom: 40px;
        text-align: center;
        box-shadow: 0 10px 25px rgba(59, 130, 246, 0.3);
      }
      
      .endpoint-card h2 {
        font-size: 2rem;
        margin-bottom: 15px;
        color: white;
      }
      
      .endpoint-card p {
        font-size: 1.2rem;
        margin-bottom: 25px;
        opacity: 0.9;
      }
      
      .endpoint-url {
        background: rgba(255, 255, 255, 0.15);
        border-radius: 12px;
        padding: 20px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 1.1rem;
        margin: 25px 0;
        word-break: break-all;
        position: relative;
        text-align: left;
        border: 1px solid rgba(255, 255, 255, 0.2);
      }
      
      .copy-btn {
        background: white;
        color: var(--primary);
        border: none;
        padding: 12px 25px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 1.1rem;
        cursor: pointer;
        transition: all 0.3s ease;
        margin-top: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      }
      
      .copy-btn:hover {
        background: var(--light);
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
      }
      
      .copy-btn:active {
        transform: translateY(0);
      }
      
      .card {
        background: white;
        border-radius: 16px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        padding: 30px;
        margin-bottom: 30px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
      }
      
      .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
      }
      
      h2 {
        font-size: 1.8rem;
        margin-bottom: 20px;
        color: var(--dark);
        display: flex;
        align-items: center;
        gap: 10px;
      }
      
      h2 i {
        color: var(--primary);
      }
      
      .features {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 25px;
        margin-bottom: 40px;
      }
      
      .feature {
        display: flex;
        gap: 15px;
      }
      
      .feature-icon {
        background: linear-gradient(135deg, var(--primary), var(--primary-dark));
        color: white;
        width: 50px;
        height: 50px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        font-size: 1.4rem;
      }
      
      .feature-content h3 {
        margin-bottom: 8px;
        font-size: 1.3rem;
      }
      
      .providers {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin-top: 20px;
      }
      
      .provider {
        background: var(--light);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid var(--border);
      }
      
      .provider-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
      }
      
      .provider-name {
        font-weight: 600;
        font-size: 1.1rem;
      }
      
      .provider-weight {
        background: var(--primary);
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.9rem;
      }
      
      .provider-url {
        color: var(--gray);
        font-size: 0.9rem;
        word-break: break-all;
      }
      
      .provider-description {
        color: var(--gray);
        font-size: 0.8rem;
        margin-top: 8px;
        font-style: italic;
      }
      
      .usage-examples {
        background: var(--dark);
        color: white;
        border-radius: 16px;
        padding: 30px;
      }
      
      .usage-examples h2 {
        color: white;
      }
      
      .code-block {
        background: #0f172a;
        color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 0.95rem;
        overflow-x: auto;
      }
      
      .endpoint {
        display: inline-block;
        background: rgba(255, 255, 255, 0.1);
        padding: 3px 8px;
        border-radius: 5px;
        font-family: 'Consolas', 'Monaco', monospace;
      }
      
      .btn {
        display: inline-block;
        background: var(--primary);
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 500;
        margin-top: 15px;
        transition: background 0.3s ease;
      }
      
      .btn:hover {
        background: var(--primary-dark);
      }
      
      .copy-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--dark);
        color: white;
        padding: 15px 25px;
        border-radius: 8px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        transform: translateX(200%);
        transition: transform 0.3s ease;
        z-index: 1000;
      }
      
      .copy-notification.show {
        transform: translateX(0);
      }
      
      footer {
        text-align: center;
        padding: 30px 0;
        color: var(--gray);
        font-size: 0.9rem;
      }
      
      @media (max-width: 768px) {
        h1 {
          font-size: 2.2rem;
        }
        
        .subtitle {
          font-size: 1.1rem;
        }
        
        .card {
          padding: 20px;
        }
        
        .endpoint-card {
          padding: 20px;
        }
      }
    </style>
  </head>
  <body>
    <div class="container">
      <header>
        <h1>High-Performance DoH Proxy</h1>
        <p class="subtitle">A Cloudflare Worker that proxies DNS-over-HTTPS requests with enhanced performance, reliability, and security</p>
      </header>
      
      <div class="endpoint-card">
        <h2>🚀 Your DoH Endpoint</h2>
        <p>Use this URL as your DNS-over-HTTPS resolver</p>
        <div class="endpoint-url" id="endpointUrl">${dnsEndpoint}</div>
        <button class="copy-btn" onclick="copyToClipboard()">Copy Endpoint URL</button>
      </div>
      
      <div class="features">
        <div class="card">
          <div class="feature">
            <div class="feature-icon">⚡</div>
            <div class="feature-content">
              <h3>Lightning Fast</h3>
              <p>Leverages Cloudflare's global edge network for minimal latency and maximum performance.</p>
            </div>
          </div>
        </div>
        
        <div class="card">
          <div class="feature">
            <div class="feature-icon">🔄</div>
            <div class="feature-content">
              <h3>Load Balancing</h3>
              <p>Intelligently distributes requests across multiple DNS providers based on configurable weights.</p>
            </div>
          </div>
        </div>
        
        <div class="card">
          <div class="feature">
            <div class="feature-icon">🛡️</div>
            <div class="feature-content">
              <h3>Automatic Failover</h3>
              <p>Seamlessly switches to backup providers when primary ones experience issues.</p>
            </div>
          </div>
        </div>
      </div>
      
      <div class="card">
        <h2>📡 Supported DNS Providers</h2>
        <p>This proxy supports both general DNS providers and ad-blocking focused providers for enhanced privacy and security.</p>
        <div class="providers">
          <div class="provider">
            <div class="provider-header">
              <div class="provider-name">Cloudflare</div>
              <div class="provider-weight">20%</div>
            </div>
            <div class="provider-url">https://cloudflare-dns.com/dns-query</div>
          </div>
          
          <div class="provider">
            <div class="provider-header">
              <div class="provider-name">Google</div>
              <div class="provider-weight">15%</div>
            </div>
            <div class="provider-url">https://dns.google/dns-query</div>
          </div>
          
          <div class="provider">
            <div class="provider-header">
              <div class="provider-name">Quad9</div>
              <div class="provider-weight">15%</div>
            </div>
            <div class="provider-url">https://dns.quad9.net/dns-query</div>
          </div>
          
          <div class="provider">
            <div class="provider-header">
              <div class="provider-name">OpenDNS</div>
              <div class="provider-weight">10%</div>
            </div>
            <div class="provider-url">https://doh.opendns.com/dns-query</div>
          </div>
          
          <div class="provider">
            <div class="provider-header">
              <div class="provider-name">AdGuard</div>
              <div class="provider-weight">10%</div>
            </div>
            <div class="provider-url">https://dns.adguard.com/dns-query</div>
            <div class="provider-description">Blocks ads, trackers, and malicious domains</div>
          </div>
          
          <div class="provider">
            <div class="provider-header">
              <div class="provider-name">ControlD</div>
              <div class="provider-weight">10%</div>
            </div>
            <div class="provider-url">https://freedns.controld.com/p2</div>
            <div class="provider-description">Blocks ads and tracking domains</div>
          </div>
          
          <div class="provider">
            <div class="provider-header">
              <div class="provider-name">Mullvad</div>
              <div class="provider-weight">10%</div>
            </div>
            <div class="provider-url">https://adblock.dns.mullvad.net/dns-query</div>
            <div class="provider-description">Blocks ads and trackers</div>
          </div>
          
          <div class="provider">
            <div class="provider-header">
              <div class="provider-name">NextDNS</div>
              <div class="provider-weight">10%</div>
            </div>
            <div class="provider-url">https://dns.nextdns.io/dns-query</div>
            <div class="provider-description">Blocks ads, trackers, and malicious domains</div>
          </div>
        </div>
      </div>
      
      <div class="card usage-examples">
        <h2>🔧 Usage Examples</h2>
        <p>Use this worker as a DoH endpoint:</p>
        
        <h3>GET Requests</h3>
        <p>For GET requests, the DNS query must be base64url-encoded as per the <a href="https://tools.ietf.org/html/rfc8484" style="color: #60a5fa;">RFC 8484 specification</a>:</p>
        <div class="code-block">
          GET /dns-query?dns=&lt;base64url-encoded-dns-query&gt;
        </div>
        <p><strong>Why base64url encoding?</strong></p>
        <ul style="margin-left: 20px; margin-bottom: 15px;">
          <li>DNS queries are binary data that cannot be safely transmitted in URLs</li>
          <li>Base64url encoding converts binary data into a URL-safe string format</li>
          <li>Standard base64 uses characters like '+' and '/' which have special meaning in URLs</li>
          <li>Base64url replaces these with '-' and '_' making it URL-safe</li>
        </ul>
        <p><a href="/dns-encoding" class="btn">Detailed DNS Encoding Explanation</a></p>
        <p>Example with curl:</p>
        <div class="code-block">
          curl "${dnsEndpoint}?dns=q80BAAABAAAAAAAAA3d3dwdleGFtcGxlA2NvbQAAAQAB"
        </div>
        
        <h3>POST Requests</h3>
        <p>For POST requests, the DNS query is sent as binary data in the request body:</p>
        <div class="code-block">
          POST /dns-query<br>
          Content-Type: application/dns-message<br>
          &lt;binary-dns-query&gt;
        </div>
        <p>Example with curl:</p>
        <div class="code-block">
          curl -H "Content-Type: application/dns-message" \<br>
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;--data-binary @query.dns \<br>
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;${dnsEndpoint}
        </div>
        
        <h3>Using Without Base64 Encoding</h3>
        <p>To avoid base64 encoding entirely, use POST requests with the <code>Content-Type: application/dns-message</code> header. The DNS query is sent as raw binary data in the request body:</p>
        <div class="code-block">
          curl -H "Content-Type: application/dns-message" \<br>
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;--data-binary @query.dns \<br>
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;${dnsEndpoint}
        </div>
        
        <h3>Using with dig</h3>
        <div class="code-block">
          dig @\${new URL(dnsEndpoint).hostname} example.com
        </div>
      </div>
      
      <div class="card">
        <h2>⚙️ Configuration</h2>
        <p>This worker automatically balances requests across multiple DNS providers based on the configured weights. All DNS responses are cached for 5 minutes to improve performance.</p>
        <p>For CORS support, the worker includes the following headers in all responses:</p>
        <div class="code-block">
          Access-Control-Allow-Origin: *<br>
          Access-Control-Allow-Methods: GET, POST, OPTIONS<br>
          Access-Control-Allow-Headers: Content-Type, Accept
        </div>
      </div>
      
      <footer>
        <p>High-Performance DoH Proxy Worker | Powered by Cloudflare Workers</p>
      </footer>
    </div>
    
    <div class="copy-notification" id="copyNotification">Endpoint URL copied to clipboard!</div>
    
    <script>
      function copyToClipboard() {
        const endpointUrl = document.getElementById('endpointUrl').textContent;
        navigator.clipboard.writeText(endpointUrl).then(() => {
          const notification = document.getElementById('copyNotification');
          notification.classList.add('show');
          setTimeout(() => {
            notification.classList.remove('show');
          }, 3000);
        }).catch(err => {
          console.error('Failed to copy: ', err);
          alert('Failed to copy URL to clipboard. Please copy it manually: ' + endpointUrl);
        });
      }
    </script>
  </body>
  </html>`;
  
  return new Response(html, {
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'public, max-age=3600'
    }
  });
}

// Serve detailed DNS encoding explanation
function serveDNSEncodingExplanation() {
  const html = `
  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DNS Query Encoding in DoH - Explained</title>
    <style>
      :root {
        --primary: #3b82f6;
        --primary-dark: #2563eb;
        --secondary: #10b981;
        --dark: #1e293b;
        --light: #f8fafc;
        --gray: #94a3b8;
        --border: #e2e8f0;
      }
      
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      
      body {
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        line-height: 1.6;
        color: var(--dark);
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        min-height: 100vh;
        padding: 20px;
      }
      
      .container {
        max-width: 1000px;
        margin: 0 auto;
      }
      
      header {
        text-align: center;
        padding: 40px 20px;
        margin-bottom: 30px;
      }
      
      h1 {
        font-size: 2.5rem;
        margin-bottom: 15px;
        color: var(--dark);
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }
      
      .subtitle {
        font-size: 1.2rem;
        color: var(--gray);
        max-width: 700px;
        margin: 0 auto 25px;
      }
      
      .card {
        background: white;
        border-radius: 16px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
        padding: 30px;
        margin-bottom: 30px;
      }
      
      h2 {
        font-size: 1.8rem;
        margin-bottom: 20px;
        color: var(--dark);
        padding-bottom: 10px;
        border-bottom: 2px solid var(--border);
      }
      
      h3 {
        font-size: 1.4rem;
        margin: 25px 0 15px;
        color: var(--dark);
      }
      
      ul, ol {
        margin-left: 30px;
        margin-bottom: 20px;
      }
      
      li {
        margin-bottom: 10px;
      }
      
      .code-block {
        background: #0f172a;
        color: white;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 0.95rem;
        overflow-x: auto;
      }
      
      .back-link {
        display: inline-block;
        background: var(--primary);
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 500;
        margin-top: 15px;
        transition: background 0.3s ease;
      }
      
      .back-link:hover {
        background: var(--primary-dark);
      }
      
      footer {
        text-align: center;
        padding: 30px 0;
        color: var(--gray);
        font-size: 0.9rem;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <header>
        <h1>DNS Query Encoding in DNS-over-HTTPS</h1>
        <p class="subtitle">Understanding why DNS queries must be base64url-encoded in DoH GET requests</p>
      </header>
      
      <div class="card">
        <h2>Why DNS Queries Must Be Encoded</h2>
        
        <p>When using DNS-over-HTTPS with GET requests, DNS queries must be encoded using base64url encoding. This requirement exists for several important technical reasons:</p>
        
        <h3>1. Binary Data in URLs</h3>
        <p>DNS queries are binary data structures that contain information about the domain name being queried, the type of record requested (A, AAAA, MX, etc.), and other metadata. URLs, however, are text-based and have restrictions on what characters they can contain.</p>
        
        <h3>2. URL Safety</h3>
        <p>Standard Base64 encoding uses characters like '+' and '/' which have special meanings in URLs:</p>
        <ul>
          <li>'+' is interpreted as a space in URL query parameters</li>
          <li>'/' is interpreted as a path separator</li>
        </ul>
        
        <p>Base64url encoding solves this by:</p>
        <ul>
          <li>Replacing '+' with '-'</li>
          <li>Replacing '/' with '_'</li>
          <li>Optionally omitting padding '=' characters</li>
        </ul>
        
        <h3>3. RFC 8484 Compliance</h3>
        <p>The DNS-over-HTTPS specification (RFC 8484) mandates the use of base64url encoding for DNS queries transmitted via GET requests to ensure interoperability between different DoH implementations.</p>
        
        <h2>Example Encoding Process</h2>
        <ol>
          <li>A DNS query for "example.com" is represented as binary data</li>
          <li>This binary data is encoded using base64url encoding</li>
          <li>The resulting string is safe to use in a URL query parameter</li>
        </ol>
        
        <div class="code-block">
Binary DNS Query → Base64url Encoding → URL Parameter
[0x12, 0x34, ...] → "q80BAAAB..." → ?dns=q80BAAAB...</div>
        
        <h2>When Encoding is Required</h2>
        <ul>
          <li><strong>GET Requests</strong>: DNS queries MUST be base64url-encoded</li>
          <li><strong>POST Requests</strong>: DNS queries are sent as binary data in the request body (no encoding needed)</li>
        </ul>
        
        <h2>Tools for Encoding</h2>
        <p>Many programming languages provide built-in functions for base64url encoding:</p>
        <ul>
          <li>JavaScript: Custom function using <code>btoa()</code> with character replacements</li>
          <li>Python: <code>base64.urlsafe_b64encode()</code></li>
          <li>Command-line: <code>openssl base64 -url</code></li>
        </ul>
        
        <p>This encoding requirement ensures that DNS queries can be safely transmitted over HTTPS while maintaining compatibility with web standards and the DoH protocol specification.</p>
        
        <h2>Ad-Blocking Support</h2>
        <p>This DoH proxy includes support for ad-blocking DNS providers. When using this service, DNS queries are automatically distributed across multiple providers including specialized ad-blocking services like AdGuard, ControlD, Mullvad, and NextDNS. These providers block ads, trackers, and malicious domains at the DNS level, providing an additional layer of privacy and security.</p>
        
        <a href="/" class="back-link">← Back to Main Page</a>
      </div>
      
      <footer>
        <p>High-Performance DoH Proxy Worker | Powered by Cloudflare Workers</p>
      </footer>
    </div>
  </body>
  </html>`;
  
  return new Response(html, {
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'public, max-age=3600'
    }
  });
}

// Handle CORS preflight requests
function handleCORS() {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Accept',
      'Access-Control-Max-Age': '86400'
    }
  });
}

// Weighted random selection of DoH provider
function selectProvider(providers) {
  const totalWeight = providers.reduce((sum, provider) => sum + provider.weight, 0);
  let random = Math.random() * totalWeight;
  
  for (const provider of providers) {
    if (random < provider.weight) {
      return provider;
    }
    random -= provider.weight;
  }
  
  // Fallback to first provider
  return providers[0];
}

// Try fallback providers when primary fails
async function tryFallbackProviders(request, url, failedProvider) {
  const fallbackProviders = DOH_PROVIDERS.filter(p => p.name !== failedProvider.name);
  
  for (const provider of fallbackProviders) {
    try {
      const targetUrl = provider.url + url.search;
      
      const headers = new Headers(request.headers);
      if (request.method === 'POST') {
        headers.set('Content-Type', 'application/dns-message');
      } else {
        headers.set('Accept', 'application/dns-message');
      }
      headers.set('User-Agent', 'DoH-Proxy-Worker/1.0');
      
      const upstreamRequest = new Request(targetUrl, {
        method: request.method,
        headers: headers,
        body: request.method === 'POST' ? await request.arrayBuffer() : null,
        redirect: 'follow'
      });
      
      const response = await fetch(upstreamRequest);
      
      if (response.ok) {
        const responseHeaders = new Headers(response.headers);
        responseHeaders.set('Access-Control-Allow-Origin', '*');
        responseHeaders.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
        responseHeaders.set('Access-Control-Allow-Headers', 'Content-Type, Accept');
        responseHeaders.set('Cache-Control', `public, max-age=${CACHE_TTL}`);
        
        return new Response(response.body, {
          status: response.status,
          statusText: response.statusText,
          headers: responseHeaders
        });
      }
    } catch (error) {
      // Continue to next provider
      continue;
    }
  }
  
  // All providers failed
  return new Response('All DNS providers are unavailable', { status: 503 });
}