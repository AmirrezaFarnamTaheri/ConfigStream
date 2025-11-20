class WebSocketManager {
    constructor(url) {
        this.url = url;
        this.socket = null;
        this.reconnectInterval = 3000;
        this.maxRetries = 5;
        this.retries = 0;
        this.listeners = [];
    }

    connect() {
        this.socket = new WebSocket(this.url);

        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.retries = 0;
            this.notifyListeners({ type: 'status', status: 'connected' });
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.notifyListeners(data);
            } catch (e) {
                console.error('Error parsing WebSocket message:', e);
            }
        };

        this.socket.onclose = () => {
            console.log('WebSocket closed');
            this.notifyListeners({ type: 'status', status: 'disconnected' });
            this.retryConnection();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.socket.close();
        };
    }

    retryConnection() {
        if (this.retries < this.maxRetries) {
            setTimeout(() => {
                console.log(`Retrying WebSocket connection (${this.retries + 1}/${this.maxRetries})...`);
                this.retries++;
                this.connect();
            }, this.reconnectInterval);
        }
    }

    addListener(callback) {
        this.listeners.push(callback);
    }

    notifyListeners(data) {
        this.listeners.forEach(callback => callback(data));
    }
}

// Initialize if on the dashboard
if (document.getElementById('pipeline-feed')) {
    // Determine WebSocket URL based on current protocol
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/feed`;

    const wsManager = new WebSocketManager(wsUrl);
    wsManager.connect();

    wsManager.addListener((data) => {
        if (data.type === 'log') {
            const feed = document.getElementById('pipeline-feed');
            const entry = document.createElement('div');
            entry.className = 'feed-entry';
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${data.message}`;
            feed.prepend(entry);

            // Keep only last 50 items
            if (feed.children.length > 50) {
                feed.lastChild.remove();
            }
        }
    });
}
