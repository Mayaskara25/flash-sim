import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

import { fileURLToPath } from 'node:url'

// H0: incident fixtures are imported directly from docs/contracts/fixtures
// (one directory above this repo's frontend/ root) rather than copied into
// src/, so `server.fs.allow` needs to reach the repo root for dev — see
// frontend/src/incident/fixtures.ts.
const repoRoot = fileURLToPath(new URL('..', import.meta.url))

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    fs: {
      allow: [repoRoot],
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
