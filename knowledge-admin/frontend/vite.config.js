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
      // RAG Orchestrator API - 使用 /rag-api/ 前綴
      // 前端: /rag-api/v1/xxx → 後端: rag-orchestrator:8100/api/v1/xxx
      '/rag-api': {
        target: 'http://rag-orchestrator:8100/api',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/rag-api/, '')
      },
      // Knowledge Admin API - 使用 /api/ 前綴
      // 前端: /api/xxx → 後端: knowledge-admin-api:8000/api/xxx
      '/api': {
        target: 'http://knowledge-admin-api:8000',
        changeOrigin: true,
        // 確保轉發所有 headers（包括 Authorization）
        configure: (proxy, options) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            // 轉發原始請求的所有 headers
            if (req.headers.authorization) {
              proxyReq.setHeader('Authorization', req.headers.authorization);
            }
          });
        }
      }
    }
  }
})
