// Washer Client (Non-Module)
// Communicates with backend washer or handles client-side washing (future)

(function(global) {
    const WasherClient = {
        status: "idle",

        checkStatus: async function() {
            // Mock status check
            console.log("Washer Client: Ready");
            return true;
        }
    };

    global.WasherClient = WasherClient;
})(typeof window !== 'undefined' ? window : self);
