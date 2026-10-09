import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

const environment = loadEnv('development', fileURLToPath(new URL('.', import.meta.url)), '')

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5175,
    strictPort: true,
    proxy: {
      '/api': {
        target: process.env.API_PROXY_TARGET || environment.API_PROXY_TARGET || 'http://127.0.0.1:28080',
        changeOrigin: true
      }
    }
  }
})
