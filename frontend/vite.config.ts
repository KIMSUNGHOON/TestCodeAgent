import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    },
    watch: {
      // FIXED: Exclude directories to prevent ENOSPC file watcher limit error
      ignored: [
        '**/node_modules/**',
        '**/dist/**',
        '**/dist-ssr/**',
        '**/.git/**',
        '**/backend/**',         // Backend files not needed in frontend watch
        '**/*.log',
        '**/data/**',
        '**/workspace/**',
        '**/__pycache__/**',
        '**/*.pyc'
      ],
      // Use polling as fallback (less resource intensive)
      usePolling: false,
    }
  }
})
