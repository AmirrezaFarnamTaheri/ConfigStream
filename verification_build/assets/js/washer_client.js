/**
 * client-side logic for "Bring Your Own Worker" (BYOW).
 * Rewrites proxy configurations to tunnel through a user-provided Cloudflare Worker.
 */

export function wrapWithUserWorker(originalProxy, workerHost, userUUID) {
    if (!workerHost || !userUUID) return originalProxy;

    // We only wrap if the original proxy supports the transport needed (e.g. standard TCP target).
    // However, the Worker is VLESS-over-WS.
    // The Worker connects to the Target.

    // Construct the VLESS config that points to the Worker
    return {
        "type": "vless",
        "tag": `${originalProxy.tag} (via Worker)`,
        "server": workerHost,
        "server_port": 443,
        "uuid": userUUID,
        "flow": "",
        "tls": {
            "enabled": true,
            "server_name": workerHost,
            "utls": {
                "enabled": true,
                "fingerprint": "chrome"
            }
        },
        "packet_encoding": "xudp",
        "transport": {
            "type": "ws",
            "path": "/?ed=2048",
            "headers": {
                "Host": workerHost,
                "X-Forward-To": `${originalProxy.server}:${originalProxy.server_port}`
            }
        }
    };
}
