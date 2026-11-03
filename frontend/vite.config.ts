import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    target: 'es2020',
    chunkSizeWarningLimit: 1600,
  },
  server: {
    // 5173 落在 Windows 保留端口段(5141-5240)内会被系统拒绝绑定，改用 4173
    host: '127.0.0.1',
    port: 4173,
    strictPort: false,
    proxy: {
      '/api': {
        // 后端默认端口 8300，需与 run.py / WEBSTACK_PORT 保持一致
        target: 'http://127.0.0.1:8300',
        changeOrigin: true,
      },
    },
  },
})
