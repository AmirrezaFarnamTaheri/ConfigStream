// SPDX-License-Identifier: AGPL-3.0-or-later
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { defineConfig } from "vite";

const __dirname = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(__dirname, "frontend");

export default defineConfig({
  root: frontendRoot,
  base: "./",
  build: {
    outDir: resolve(__dirname, "frontend-dist"),
    emptyOutDir: true,
    target: "es2020",
    sourcemap: false,
    rollupOptions: {
      input: {
        index: resolve(frontendRoot, "index.html"),
        about: resolve(frontendRoot, "about.html"),
        analytics: resolve(frontendRoot, "analytics.html"),
        evidence: resolve(frontendRoot, "evidence.html"),
        lab: resolve(frontendRoot, "lab.html"),
        proxies: resolve(frontendRoot, "proxies.html"),
        wiki: resolve(frontendRoot, "wiki.html")
      }
    }
  },
  server: {
    port: 5173,
    strictPort: true
  }
});
