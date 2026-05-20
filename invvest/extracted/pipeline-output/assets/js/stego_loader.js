// Steganography Loader (Non-Module)
// Extracts hidden configurations from images using window.stego

(function(global) {
    const StegoLoader = {
        extractFromImage: async function(imageUrl) {
            try {
                if (global.stego && global.stego.extract) {
                    const config = await global.stego.extract(imageUrl);
                    return config;
                } else {
                    console.warn("Stego extractor not found on window.stego.extract");
                    return null;
                }
            } catch (e) {
                console.error("Stego extraction failed:", e);
                return null;
            }
        }
    };

    global.StegoLoader = StegoLoader;
})(typeof window !== 'undefined' ? window : self);
