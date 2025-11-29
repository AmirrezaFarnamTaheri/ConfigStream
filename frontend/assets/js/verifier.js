import { PUBLIC_KEY } from './constants.js';

/**
 * Verifies the signature of the configuration object using Web Crypto API.
 *
 * @param {Object} signedObj - The object containing { content, signature, timestamp }
 * @returns {Promise<Object>} - The parsed JSON content if verification succeeds.
 * @throws {Error} - If verification fails.
 */
export async function verifyConfig(signedObj) {
    if (!window.crypto || !window.crypto.subtle) {
        console.warn("Web Crypto API not supported. Skipping verification.");
        return JSON.parse(signedObj.content);
    }

    // Audit: Guard against placeholder keys
    if (PUBLIC_KEY.includes("PLACEHOLDER") || PUBLIC_KEY.length < 32) {
        console.warn("Signature verification skipped: Public Key not configured.");
        return JSON.parse(signedObj.content);
    }

    const msg = new TextEncoder().encode(signedObj.content);
    const sig = hexToBytes(signedObj.signature);
    const keyBytes = hexToBytes(PUBLIC_KEY);

    try {
        const key = await window.crypto.subtle.importKey(
            "raw",
            keyBytes,
            { name: "Ed25519" },
            false,
            ["verify"]
        );

        const isValid = await window.crypto.subtle.verify(
            { name: "Ed25519" },
            key,
            sig,
            msg
        );

        if (isValid) {
            console.log("Config signature verified successfully (Web Crypto).");
            return JSON.parse(signedObj.content);
        } else {
            throw new Error("SECURITY ALERT: Config signature mismatch!");
        }
    } catch (e) {
        console.error("Verification error:", e);
        // Fallback for browsers that might not support Ed25519 in WebCrypto yet (though modern ones do)
        // or if key import fails.
        throw new Error("Signature verification failed: " + e.message);
    }
}

/**
 * Helper to convert Hex string to Uint8Array
 */
function hexToBytes(hex) {
    const bytes = new Uint8Array(hex.length / 2);
    for (let i = 0; i < bytes.length; i++) {
        bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
    }
    return bytes;
}
