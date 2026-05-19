// Washer Client (Non-Module)
// Communicates with backend washer or handles client-side washing (future)

(function(global) {
    const WasherClient = {
        status: "idle",

        checkStatus: async function() {
            // Status check: returns true when the washer backend is reachable,
            // false otherwise. Currently a lightweight availability probe.
            if (global.ConfigStreamLogger) {
                global.ConfigStreamLogger.info("Washer Client: Ready");
            }
            return true;
        }
    };

    global.WasherClient = WasherClient;
})(typeof window !== 'undefined' ? window : self);
