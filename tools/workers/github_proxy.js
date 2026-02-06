// Simple GitHub Raw Proxy Worker
// Use this to proxy raw.githubusercontent.com requests
// Usage: https://your-worker.dev/owner/repo/branch/path/to/file.ext

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/^\/+/, "");
    const parts = path.split("/");
    if (parts.length < 4) {
      return new Response("Usage: /owner/repo/branch/path/to/file.ext", { status: 400 });
    }
    const [owner, repo, branch, ...filePathParts] = parts;
    const filePath = filePathParts.join("/");
    const rawUrl = `https://raw.githubusercontent.com/${owner}/${repo}/${branch}/${filePath}`;
    
    try {
        const resp = await fetch(rawUrl, {
            headers: {
                "User-Agent": "ConfigStream-Proxy/1.0"
            }
        });
        
        // Add CORS headers
        const newHeaders = new Headers(resp.headers);
        newHeaders.set("Access-Control-Allow-Origin", "*");
        
        return new Response(resp.body, {
            status: resp.status,
            headers: newHeaders,
        });
    } catch (e) {
        return new Response("Proxy Error: " + e.message, { status: 502 });
    }
  }
};
