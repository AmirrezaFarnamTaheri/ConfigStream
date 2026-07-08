import { defineConfig } from 'vite';

export default defineConfig({
  root: 'frontend',
  build: {
    outDir: '../frontend-dist',
    emptyOutDir: true,
  },
});
