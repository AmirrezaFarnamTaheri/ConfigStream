export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const secret = env.HONEYPOT_SECRET;

    if (url.pathname === "/verify") {
        const token = url.searchParams.get("token");
        if (!token) {
            return new Response("Missing token", { status: 400 });
        }

        // Simple HMAC-SHA256 Signature
        const encoder = new TextEncoder();
        const keyData = encoder.encode(secret);
        const key = await crypto.subtle.importKey(
            "raw", keyData, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
        );

        const signature = await crypto.subtle.sign(
            "HMAC", key, encoder.encode(token)
        );

        const hexSignature = [...new Uint8Array(signature)]
            .map(b => b.toString(16).padStart(2, "0"))
            .join("");

        return new Response(JSON.stringify({ signature: hexSignature }), {
            headers: { "Content-Type": "application/json" }
        });
    }

    return new Response("ConfigStream Honeypot Active", { status: 200 });
  },
};
