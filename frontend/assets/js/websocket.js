/**
 * WebSocket Client for ConfigStream Live Feed
 * Connects to the backend to receive real-time pipeline updates.
 */

class LiveFeed {
    constructor(feedElementId) {
        this.feedElement = document.getElementById(feedElementId);
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // Use relative path /ws/feed assuming served by same origin or configured proxy
        const wsUrl = `${protocol}//${window.location.host}/ws/feed`;

        // Fallback for static hosting (Github Pages):
        // If we are on github pages, we can't connect to WS easily unless we have a backend running.
        // We will try, but gracefully fail if connection is refused.
        // This feature is primarily for the Docker/Self-hosted version.

        try {
            this.socket = new WebSocket(wsUrl);

            this.socket.onopen = () => {
                this.log("Connected to live feed.", "success");
                this.reconnectAttempts = 0;
            };

            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleEvent(data);
                } catch (e) {
                    console.error("Failed to parse WS message", e);
                }
            };

            this.socket.onclose = () => {
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    setTimeout(() => this.connect(), 2000 * this.reconnectAttempts);
                } else {
                    this.log("Live feed disconnected (Backend unavailable).", "warning");
                }
            };

            this.socket.onerror = (error) => {
                // console.error("WebSocket Error", error);
            };

        } catch (e) {
            console.log("WebSocket init failed", e);
        }
    }

    handleEvent(event) {
        // Event types: pipeline_start, fetch_success, fetch_blocked, test_success, pipeline_finish
        let msg = "";
        let type = "info";

        switch (event.type) {
            case "pipeline_start":
                msg = `🚀 ${event.message}`;
                type = "info";
                break;
            case "fetch_success":
                msg = `📥 ${event.message}`;
                type = "success";
                break;
            case "fetch_blocked":
                msg = `🛡️ ${event.message}`;
                type = "warning";
                break;
            case "test_success":
                msg = `✅ ${event.message}`;
                type = "success";
                break;
            case "pipeline_finish":
                msg = `🏁 ${event.message}`;
                type = "info";
                break;
            default:
                msg = event.message || JSON.stringify(event);
        }

        this.log(msg, type);
    }

    log(message, type = "info") {
        if (!this.feedElement) return;

        const entry = document.createElement("div");
        entry.className = `feed-entry ${type}`;
        entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;

        this.feedElement.insertBefore(entry, this.feedElement.firstChild);

        // Limit history
        if (this.feedElement.children.length > 50) {
            this.feedElement.removeChild(this.feedElement.lastChild);
        }
    }
}

// Initialize
document.addEventListener("DOMContentLoaded", () => {
    const feed = new LiveFeed("pipeline-feed");
    feed.connect();
});
