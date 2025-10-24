/**
 * Incremental Loading for Large Proxy Lists
 * Loads and renders proxies in chunks for better performance
 */

class IncrementalLoader {
    constructor(proxies, chunkSize = 100) {
        this.allProxies = proxies;
        this.chunkSize = chunkSize;
        this.currentChunk = 0;
        this.loadedProxies = [];
    }

    loadNextChunk() {
        const start = this.currentChunk * this.chunkSize;
        const end = start + this.chunkSize;
        const chunk = this.allProxies.slice(start, end);
        
        if (chunk.length > 0) {
            this.loadedProxies.push(...chunk);
            this.currentChunk++;
            return chunk;
        }
        
        return null;
    }

    hasMore() {
        return this.currentChunk * this.chunkSize < this.allProxies.length;
    }

    getProgress() {
        return {
            loaded: this.loadedProxies.length,
            total: this.allProxies.length,
            percentage: (this.loadedProxies.length / this.allProxies.length) * 100
        };
    }

    reset() {
        this.currentChunk = 0;
        this.loadedProxies = [];
    }
}

window.IncrementalLoader = IncrementalLoader;
