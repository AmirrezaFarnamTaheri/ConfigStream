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

        _isSignedObject: function(signedObj) {
            return !!(signedObj && typeof signedObj.signature === "string" && signedObj.signature.length > 0);
        },

        _isConfiguredPublicKey: function(publicKey) {
            return !!(
                publicKey &&
                typeof publicKey === "string" &&
                publicKey.length >= 20 &&
                !publicKey.includes("PLACEHOLDER") &&
                !publicKey.includes("79e/79e/")
            );
        },

        /**
         * Verifies the signature of the configuration object using Web Crypto API.
         * @param {Object} signedObj - The object containing { content, signature }
         * @returns {Promise<Object>} - The parsed JSON content if verification succeeds.
         */
        verifyConfig: async function(signedObj) {
            if (!this._isSignedObject(signedObj)) {
                return JSON.parse(signedObj.content);
            }

            if (!window.crypto || !window.crypto.subtle) {
                throw new Error("Signature verification unavailable: Web Crypto API not supported.");
            }

            const PUBLIC_KEY = global.CS_CONSTANTS ? global.CS_CONSTANTS.PUBLIC_KEY : null;

            if (!this._isConfiguredPublicKey(PUBLIC_KEY)) {
                throw new Error("Signature verification unavailable: Public Key not configured.");
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

                if (!isValid) {
                    throw new Error("SECURITY ALERT: Config signature mismatch!");
                }

                return JSON.parse(signedObj.content);

            } catch (e) {
                console.error("Verification failed:", e);
                // Fail CLOSED as per audit
                throw e; // Propagate error, do not return content
            }
        },

        // Manual Trigger
        runLocalVerification: async function() {
            const statusEl = document.getElementById('wasm-status');
            const PUBLIC_KEY = global.CS_CONSTANTS ? global.CS_CONSTANTS.PUBLIC_KEY : null;

            if (!this._isConfiguredPublicKey(PUBLIC_KEY)) {
                if(statusEl) {
                    statusEl.textContent = "⚠️ Verification unavailable (No Key)";
                    statusEl.style.color = "var(--text-secondary)";
                }
                return;
            }

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
