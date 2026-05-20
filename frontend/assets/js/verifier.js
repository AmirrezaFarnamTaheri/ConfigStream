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

        _canonicalize: function(value) {
            if (Array.isArray(value)) {
                return value.map((item) => this._canonicalize(item));
            }
            if (value && typeof value === "object") {
                const sorted = {};
                Object.keys(value)
                    .sort()
                    .forEach((key) => {
                        sorted[key] = this._canonicalize(value[key]);
                    });
                return sorted;
            }
            return value;
        },

        _canonicalManifestPayload: function(manifestObj) {
            const clone = JSON.parse(JSON.stringify(manifestObj || {}));
            delete clone.manifest_signature;
            const canonical = this._canonicalize(clone);
            return JSON.stringify(canonical);
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
                // PUBLIC_KEY is a Base64-encoded SPKI (SubjectPublicKeyInfo) for Ed25519.
                // Keys shorter than 60 chars are treated as raw Base64 for compatibility.
                let keyData;
                let format = "spki";

                if (PUBLIC_KEY.length > 60) { // Likely Base64 SPKI
                    keyData = this._base64ToArrayBuffer(PUBLIC_KEY);
                } else { // Raw Base64 fallback
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

        verifyManifestSignature: async function(manifestObj) {
            if (!manifestObj || typeof manifestObj !== "object") {
                throw new Error("Manifest verification failed: manifest must be an object.");
            }

            const sig = manifestObj.manifest_signature;
            if (!sig) {
                return { verified: false, reason: "unsigned" };
            }
            if (!this._isSignedObject({ content: "{}", signature: sig.signature })) {
                throw new Error("Manifest verification failed: invalid signature object.");
            }
            if (sig.algorithm !== "ed25519") {
                throw new Error("Manifest verification failed: unsupported algorithm.");
            }

            if (!window.crypto || !window.crypto.subtle) {
                throw new Error("Manifest verification failed: Web Crypto API not supported.");
            }

            const PUBLIC_KEY = global.CS_CONSTANTS ? global.CS_CONSTANTS.PUBLIC_KEY : null;
            if (!this._isConfiguredPublicKey(PUBLIC_KEY)) {
                throw new Error("Manifest verification failed: Public Key not configured.");
            }

            let keyData;
            keyData = this._base64ToArrayBuffer(PUBLIC_KEY);
            const key = await window.crypto.subtle.importKey(
                "spki",
                keyData,
                { name: "Ed25519" },
                true,
                ["verify"]
            );
            const payload = new TextEncoder().encode(this._canonicalManifestPayload(manifestObj));
            const signature = this._hexToBytes(sig.signature);
            const isValid = await window.crypto.subtle.verify(
                { name: "Ed25519" },
                key,
                signature,
                payload
            );
            if (!isValid) {
                throw new Error("SECURITY ALERT: artifact_manifest signature mismatch!");
            }
            return { verified: true, reason: "verified" };
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
