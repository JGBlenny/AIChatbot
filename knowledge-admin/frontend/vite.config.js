import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0', // 允許 Docker 容器外部訪問
    port: 5173,
    strictPort: true,
    watch: {
      usePolling: true // Docker 環境需要 polling 模式
    },
    proxy: {
      '/api': {
        target: 'http://knowledge-admin-api:8000', // Docker 內部服務名稱
        changeOrigin: true
      },
      '/rag-api': {
        target: 'http://rag-orchestrator:8100/api', // RAG Orchestrator API
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/rag-api/, '')
      }
    }
  }
})
