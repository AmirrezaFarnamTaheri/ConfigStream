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
            // An Ed25519 public key in SPKI/Base64 form is ~68 characters.
            // The raw hex form is exactly 64 characters (32 bytes).
            // The previous minimum of 20 was far too low and would accept
            // garbage values. Require at least 60 to reject clearly wrong keys
            // while remaining tolerant of minor encoding variants.
            return !!(
                publicKey &&
                typeof publicKey === "string" &&
                publicKey.length >= 60 &&
                !publicKey.includes("PLACEHOLDER") &&
                !publicKey.includes("79e/79e/")
            );
        },

        /**
         * Build the canonical signed payload used by the Python signer.
         *
         * Layout: big-endian uint64 timestamp (8 bytes) || UTF-8 content bytes.
         * When no timestamp is present (legacy unsigned responses) we fall back
         * to verifying over the raw content bytes only.
         *
         * @param {string} content - The content string.
         * @param {number|null} timestamp - Integer seconds (UTC), or null for legacy.
         * @returns {Uint8Array}
         */
        _buildSignedPayload: function(content, timestamp) {
            const contentBytes = new TextEncoder().encode(content);
            if (timestamp == null) {
                return contentBytes;
            }
            // Pack timestamp as big-endian uint64 into 8 bytes.
            // JavaScript numbers are IEEE-754 doubles; timestamps fit in 53-bit
            // safe integer range for decades to come.
            const tsBytes = new Uint8Array(8);
            const ts = Math.floor(timestamp);
            // Write high 32 bits then low 32 bits (big-endian uint64).
            const hi = Math.floor(ts / 0x100000000);
            const lo = ts >>> 0;
            tsBytes[0] = (hi >>> 24) & 0xff;
            tsBytes[1] = (hi >>> 16) & 0xff;
            tsBytes[2] = (hi >>> 8) & 0xff;
            tsBytes[3] = hi & 0xff;
            tsBytes[4] = (lo >>> 24) & 0xff;
            tsBytes[5] = (lo >>> 16) & 0xff;
            tsBytes[6] = (lo >>> 8) & 0xff;
            tsBytes[7] = lo & 0xff;
            const payload = new Uint8Array(8 + contentBytes.length);
            payload.set(tsBytes, 0);
            payload.set(contentBytes, 8);
            return payload;
        },

        /**
         * Verifies the signature of the configuration object using Web Crypto API.
         *
         * Replay protection: if the signed object carries a `timestamp` field the
         * verifier reconstructs the same payload the Python signer used
         * (big-endian uint64 ts || content) and additionally checks that the
         * signature is not older than MAX_SIGNATURE_AGE_SECONDS.
         *
         * @param {Object} signedObj - The object containing { content, signature, timestamp? }
         * @returns {Promise<Object>} - The parsed JSON content if verification succeeds.
         */
        verifyConfig: async function(signedObj) {
            // Maximum acceptable age of a signed payload in seconds (must match
            // SIGNATURE_MAX_AGE_SECONDS in signer.py).
            const MAX_SIGNATURE_AGE_SECONDS = 300;

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

            // Replay-protection age check (only when timestamp is present).
            const timestamp = signedObj.timestamp != null ? Number(signedObj.timestamp) : null;
            if (timestamp != null) {
                const age = Math.floor(Date.now() / 1000) - timestamp;
                if (age < 0 || age > MAX_SIGNATURE_AGE_SECONDS) {
                    throw new Error(
                        `SECURITY ALERT: Signature age ${age}s exceeds maximum ${MAX_SIGNATURE_AGE_SECONDS}s — possible replay attack.`
                    );
                }
            }

            try {
                // PUBLIC_KEY is a Base64-encoded SPKI (SubjectPublicKeyInfo) for Ed25519.
                const keyData = this._base64ToArrayBuffer(PUBLIC_KEY);

                const key = await window.crypto.subtle.importKey(
                    "spki",
                    keyData,
                    { name: "Ed25519" },
                    true,
                    ["verify"]
                );

                const signature = this._hexToBytes(signedObj.signature);
                // Reconstruct the exact payload the Python signer produced.
                const payload = this._buildSignedPayload(signedObj.content, timestamp);

                const isValid = await window.crypto.subtle.verify(
                    { name: "Ed25519" },
                    key,
                    signature,
                    payload
                );

                if (!isValid) {
                    throw new Error("SECURITY ALERT: Config signature mismatch!");
                }

                return JSON.parse(signedObj.content);

            } catch (e) {
                console.error("Verification failed:", e);
                // Fail CLOSED — propagate error, do not return content.
                throw e;
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

        // Manual Trigger: fetch the artifact manifest and verify its Ed25519
        // signature for real (previously this was a fake setTimeout that always
        // reported success without verifying anything).
        runLocalVerification: async function() {
            const statusEl = document.getElementById('wasm-status');
            const PUBLIC_KEY = global.CS_CONSTANTS ? global.CS_CONSTANTS.PUBLIC_KEY : null;

            const setStatus = (text, color) => {
                if (statusEl) {
                    statusEl.textContent = text;
                    if (color) statusEl.style.color = color;
                }
            };

            if (!this._isConfiguredPublicKey(PUBLIC_KEY)) {
                setStatus("\u26A0\uFE0F Verification unavailable (No Key)", "var(--text-secondary)");
                return { verified: false, reason: "no-key" };
            }

            setStatus("Verifying integrity...");

            try {
                const root = global.ROOT_PATH || "./";
                const response = await fetch(`${root}artifact_manifest.json`, { cache: "no-store" });
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                const manifest = await response.json();
                const result = await this.verifyManifestSignature(manifest);
                if (result.verified) {
                    setStatus("\u2713 Manifest signature verified", "var(--success-color)");
                } else {
                    setStatus("\u26A0\uFE0F Manifest is unsigned", "var(--text-secondary)");
                }
                return result;
            } catch (e) {
                console.error("Local verification failed:", e);
                setStatus("\u2717 Verification failed", "var(--error-color, red)");
                return { verified: false, reason: "error", error: e.message };
            }
        }
    };

    // Expose to global scope
    global.Verifier = Verifier;
    global.runLocalVerification = Verifier.runLocalVerification.bind(Verifier);

})(typeof window !== 'undefined' ? window : self);
