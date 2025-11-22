/**
 * ConfigStream Signed Honeypot Worker
 * Verifies that a request actually passed through a proxy and wasn't spoofed.
 *
 * Environment Variables:
 * - HONEYPOT_SECRET: The shared secret key used for HMAC signature.
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const token = url.searchParams.get("token");

    if (!token) {
      return new Response("Missing token", { status: 400 });
    }

    if (!env.HONEYPOT_SECRET) {
      return new Response("Server configuration error", { status: 500 });
    }

    // Calculate HMAC-SHA256 Signature
    const signature = await hmacSha256(env.HONEYPOT_SECRET, token);

    return new Response(
      JSON.stringify({
        signature: signature,
        timestamp: new Date().toISOString(),
        ip: request.headers.get("CF-Connecting-IP")
      }),
      {
        headers: { "Content-Type": "application/json" }
      }
    );
  },
};

// Helper: HMAC-SHA256
async function hmacSha256(secret, message) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    enc.encode(message)
  );

  // Convert ArrayBuffer to Hex String
  return [...new Uint8Array(signature)]
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}
