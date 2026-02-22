// SPDX-License-Identifier: AGPL-3.0-or-later
import { defineConfig } from "vite";

export default defineConfig({
  root: "frontend",
  base: "./",
  build: {
    outDir: "../frontend-dist",
    emptyOutDir: true,
    target: "es2020",
    sourcemap: false,
    rollupOptions: {
      input: {
        index: "frontend/index.html",
        about: "frontend/about.html",
        analytics: "frontend/analytics.html",
        lab: "frontend/lab.html",
        labOffline: "frontend/lab-offline.html",
        proxies: "frontend/proxies.html",
        wiki: "frontend/wiki.html"
      }
    }
  },
  server: {
    port: 5173,
    strictPort: true
  }
});
