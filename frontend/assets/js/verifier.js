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

        // Verify Signature
        verifySignature: async function(content, signatureBase64) {
            try {
                if (!global.CS_CONSTANTS || !global.CS_CONSTANTS.PUBLIC_KEY) {
                    console.warn("Missing Public Key, skipping verification.");
                    return false;
                }

                const publicKeyBuffer = this._base64ToArrayBuffer(global.CS_CONSTANTS.PUBLIC_KEY);
                const signatureBuffer = this._base64ToArrayBuffer(signatureBase64);
                const dataBuffer = new TextEncoder().encode(content);

                const key = await window.crypto.subtle.importKey(
                    "spki",
                    publicKeyBuffer,
                    { name: "Ed25519" },
                    true,
                    ["verify"]
                );

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
    };

    // Expose to global scope
    global.Verifier = Verifier;

    // Alias for the button onclick in HTML
    global.runLocalVerification = Verifier.runLocalVerification.bind(Verifier);

})(typeof window !== 'undefined' ? window : self);
