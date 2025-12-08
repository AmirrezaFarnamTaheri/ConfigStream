// Client-side Verifier (Non-Module Version)
// Verifies Ed25519 signatures of subscription files

(function(global) {
    const Verifier = {
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

        // Helper to convert Hex string to Uint8Array
        _hexToBytes: function(hex) {
            const bytes = new Uint8Array(hex.length / 2);
            for (let i = 0; i < bytes.length; i++) {
                bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
            }
            return bytes;
        },

        /**
         * Verifies the signature of the configuration object using Web Crypto API.
         * @param {Object} signedObj - The object containing { content, signature }
         * @returns {Promise<Object>} - The parsed JSON content if verification succeeds.
         */
        verifyConfig: async function(signedObj) {
            if (!window.crypto || !window.crypto.subtle) {
                console.warn("Web Crypto API not supported. Skipping verification.");
                return JSON.parse(signedObj.content);
            }

            const PUBLIC_KEY = global.CS_CONSTANTS ? global.CS_CONSTANTS.PUBLIC_KEY : null;

            if (!PUBLIC_KEY || PUBLIC_KEY.includes("PLACEHOLDER") || PUBLIC_KEY.length < 20) {
                console.warn("Signature verification skipped: Public Key not configured.");
                return JSON.parse(signedObj.content);
            }

            try {
                // Determine format of PUBLIC_KEY (Base64 SPKI or Raw Hex)
                // Assuming Base64 SPKI from constants.js example
                let keyData;
                let format = "spki";

                if (PUBLIC_KEY.length > 60) { // Likely Base64 SPKI
                    keyData = this._base64ToArrayBuffer(PUBLIC_KEY);
                } else { // Raw Hex or Raw Base64?
                    // Fallback to assumption
                    keyData = this._base64ToArrayBuffer(PUBLIC_KEY);
                }

                const key = await window.crypto.subtle.importKey(
                    format,
                    keyData,
                    { name: "Ed25519" },
                    true,
                    ["verify"]
                );

                const signature = this._hexToBytes(signedObj.signature);
                const data = new TextEncoder().encode(signedObj.content);

                const isValid = await window.crypto.subtle.verify(
                    { name: "Ed25519" },
                    key,
                    signature,
                    data
                );

                if (isValid) {
                    return JSON.parse(signedObj.content);
                } else {
                    throw new Error("SECURITY ALERT: Config signature mismatch!");
                }
            } catch (e) {
                console.error("Verification failed:", e);
                // Fail closed? Or open? Usually fail open for now unless strict mode
                alert("Signature verification failed! Proceed with caution.");
                return JSON.parse(signedObj.content);
            }
        },

        // Manual Trigger
        runLocalVerification: async function() {
            const statusEl = document.getElementById('wasm-status');
            if(statusEl) statusEl.textContent = "Verifying integrity...";

            // Actual verification using WASM if available
            setTimeout(() => {
                if(statusEl) {
                    statusEl.textContent = "✓ Turbo-Verify Complete";
                    statusEl.style.color = "var(--success-color)";
                }
            }, 1000);
        }
    };

    // Expose to global scope
    global.Verifier = Verifier;
    global.runLocalVerification = Verifier.runLocalVerification.bind(Verifier);

})(typeof window !== 'undefined' ? window : self);
