// frontend/assets/js/stego.js

const logger = window.createLogger ? window.createLogger('Stego') : console;
const MAGIC_MARKER = "CSTREAM_PAYLOAD_START>>";

// ⚠️ DO NOT CHANGE THIS LINE MANUALLY ⚠️
// This is a PLACEHOLDER. The Python pipeline injects the real key from STEGO_KEY environment variable.
// If deploying manually, set STEGO_KEY in your environment or this feature will not work.
// The key below is rotated every 6 hours by GitHub Actions.
// NOTE: This key provides OBFUSCATION ONLY, not strong confidentiality, as it is visible in client-side code.
// Ideally, use per-session keys or public-key crypto if strict confidentiality is required.
// [SECURITY FIX] Use placeholder that will fail validation if not injected by CI/CD
const SECRET_KEY = "PLACEHOLDER_KEY_INJECTED_BY_CI";

async function fetchStegoConfig(imageUrl) {
    try {
        // Validate that key was injected
        if (SECRET_KEY === "PLACEHOLDER_KEY_INJECTED_BY_CI" || SECRET_KEY.length < 20) {
            throw new Error("Stego key not configured. This deployment did not inject STEGO_KEY.");
        }

        if(window.updateStatus) updateStatus("Fetching stealth image...");
        const response = await fetch(imageUrl, { cache: "no-store" });
        const buffer = await response.arrayBuffer();

        // 1. Find Marker
        const markerSeq = new TextEncoder().encode(MAGIC_MARKER);
        const dataView = new Uint8Array(buffer);

        let payloadStart = -1;

        // Naive search (fast enough for 5MB images)
        // Prevent negative start index for small images
        const searchStart = Math.max(0, buffer.byteLength - window.CS_CONSTANTS.STEGO_SEARCH_WINDOW);

        for (let i = searchStart; i < buffer.byteLength; i++) {
            // Optimization: Scan last 500KB only
            if (dataView[i] === markerSeq[0]) {
                let match = true;
                for (let j = 1; j < markerSeq.length; j++) {
                    if (dataView[i + j] !== markerSeq[j]) {
                        match = false;
                        break;
                    }
                }
                if (match) {
                    payloadStart = i + markerSeq.length;
                    break;
                }
            }
        }

        if (payloadStart === -1) throw new Error("No stealth payload found in image.");

        // 2. Extract Encrypted Blob
        // Use subarray instead of slice to avoid copying memory
        const encryptedBytes = dataView.subarray(payloadStart);
        const encryptedString = new TextDecoder().decode(encryptedBytes);

        // 3. Decrypt (Fernet)
        // Assuming 'fernet' library is loaded globally via <script>
        const secret = new fernet.Secret(SECRET_KEY);
        const token = new fernet.Token({
            secret: secret,
            token: encryptedString,
            ttl: 0 // Disable TTL check
        });

        const compressedString = token.decode();

        // 4. Decompress (Zlib/Pako)
        // Audit: Limit payload size to avoid memory exhaustion
        if (compressedString.length > window.CS_CONSTANTS.STEGO_MAX_PAYLOAD_SIZE) {
             throw new Error("Decompressed payload too large (security limit)");
        }

        const jsonString = pako.inflate(compressedString, { to: 'string' });

        return JSON.parse(jsonString);

    } catch (e) {
        logger.error("Stego extraction failed:", e);
        alert("Failed to load stealth config. See console.");
        return null;
    }
}

// UI Helper
function loadAndApplyStego(url) {
    fetchStegoConfig(url).then(config => {
        if (config) {
            // Generate Blob URL
            const blob = new Blob([JSON.stringify(config, null, 2)], {type: "application/json"});
            const dlUrl = URL.createObjectURL(blob);

            // Trigger "Stealth" Download
            const a = document.createElement('a');
            a.href = dlUrl;
            a.download = "singbox-stealth.json";
            a.click();
        }
    });
}
