import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    host: '0.0.0.0', // 允許 Docker 容器外部訪問
    port: 5173,
    strictPort: true,
    watch: {
      usePolling: true // Docker 環境需要 polling 模式
    },
    proxy: {
      // RAG API 路徑（需要放在 /api 之前，因為更具體）
      '/api/v1': {
        target: 'http://rag-orchestrator:8100',
        changeOrigin: true
      },
      '/v1': {
        target: 'http://rag-orchestrator:8100',
        changeOrigin: true
      },
      // Knowledge Admin API 路徑
      '/api': {
        target: 'http://knowledge-admin-api:8000',
        changeOrigin: true
      },
      '/rag-api': {
        target: 'http://rag-orchestrator:8100/api',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/rag-api/, '')
      }
    }
  }
})
