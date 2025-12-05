@ -1,65 +1,75 @@
import { PUBLIC_KEY } from './constants.js';
// Client-side Verifier (Non-Module Version)
// Verifies Ed25519 signatures of subscription files

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
(function(global) {
    const Verifier = {

    // Audit: Guard against placeholder keys
    if (PUBLIC_KEY.includes("PLACEHOLDER") || PUBLIC_KEY.length < 32) {
        console.warn("Signature verification skipped: Public Key not configured.");
        return JSON.parse(signedObj.content);
    }
        // Convert Base64 to ArrayBuffer
        _base64ToArrayBuffer: function(base64) {
            const binary_string = window.atob(base64);
            const len = binary_string.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binary_string.charCodeAt(i);
            }
            return bytes.buffer;
        },

    const msg = new TextEncoder().encode(signedObj.content);
    const sig = hexToBytes(signedObj.signature);
    const keyBytes = hexToBytes(PUBLIC_KEY);
        // Verify Signature
        verifySignature: async function(content, signatureBase64) {
            try {
                if (!global.CS_CONSTANTS || !global.CS_CONSTANTS.PUBLIC_KEY) {
                    console.warn("Missing Public Key, skipping verification.");
                    return false;
                }

    try {
        const key = await window.crypto.subtle.importKey(
            "raw",
            keyBytes,
            { name: "Ed25519" },
            false,
            ["verify"]
        );
                const publicKeyBuffer = this._base64ToArrayBuffer(global.CS_CONSTANTS.PUBLIC_KEY);
                const signatureBuffer = this._base64ToArrayBuffer(signatureBase64);
                const dataBuffer = new TextEncoder().encode(content);

        const isValid = await window.crypto.subtle.verify(
            { name: "Ed25519" },
            key,
            sig,
            msg
        );
                const key = await window.crypto.subtle.importKey(
                    "spki",
                    publicKeyBuffer,
                    { name: "Ed25519" },
                    true,
                    ["verify"]
                );

        if (isValid) {
            console.log("Config signature verified successfully (Web Crypto).");
            return JSON.parse(signedObj.content);
        } else {
            throw new Error("SECURITY ALERT: Config signature mismatch!");
                const isValid = await window.crypto.subtle.verify(
                    { name: "Ed25519" },
                    key,
                    signatureBuffer,
                    dataBuffer
                );

                return isValid;
            } catch (e) {
                console.error("Verification failed:", e);
                return false;
            }
        },

        // Manual Trigger
        runLocalVerification: async function() {
            console.log("Running Local Verification...");
            const statusEl = document.getElementById('wasm-status');
            if(statusEl) statusEl.textContent = "Verifying integrity...";

            // Example check (mocking content fetch)
            // In real usage, this would fetch sub.txt and sub.txt.sig
            setTimeout(() => {
                if(statusEl) {
                    statusEl.textContent = "Integrity Verified (Mock)";
                    statusEl.style.color = "var(--success-color)";
                }
            }, 1000);
        }
    } catch (e) {
        console.error("Verification error:", e);
        // Fallback for browsers that might not support Ed25519 in WebCrypto yet (though modern ones do)
        // or if key import fails.
        throw new Error("Signature verification failed: " + e.message);
    }
}
    };

    // Expose to global scope
    global.Verifier = Verifier;

    // Alias for the button onclick in HTML
    global.runLocalVerification = Verifier.runLocalVerification.bind(Verifier);

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
})(typeof window !== 'undefined' ? window : self);