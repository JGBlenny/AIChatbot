# 前端開發模式設定指南

## 概述

本專案前端已配置雙模式架構：

- **開發模式（預設）**：支援熱重載（Hot Reload），修改代碼後自動更新
- **生產模式**：使用 Nginx 提供優化後的靜態文件

## 架構說明

### 開發模式 (knowledge-admin-web)

**特點：**
- ✅ 支援熱重載（Hot Module Replacement）
- ✅ 修改代碼後即時生效，無需重新編譯
- ✅ 開發效率高
- ✅ 支援 Vue DevTools
- ⚠️ 記憶體使用較高
- ⚠️ 不適合生產環境

**啟動方式：**
```bash
docker-compose up -d knowledge-admin-web
```

**訪問地址：**
- 前端：http://localhost:8080
- 後端 API：http://localhost:8000
- RAG API：http://localhost:8100

**技術細節：**
- 使用 Vite 開發伺服器（port 5173）
- 對外映射到 port 8080
- 掛載原始碼目錄到容器
- 啟用 polling 模式以支援 Docker 環境的檔案監控

### 生產模式 (knowledge-admin-web-prod)

**特點：**
- ✅ 效能優化
- ✅ 檔案壓縮
- ✅ 記憶體使用低
- ✅ 適合生產環境
- ❌ 無熱重載
- ❌ 修改代碼需要重新編譯

**啟動方式：**
```bash
# 僅啟動生產模式前端
docker-compose --profile production up -d knowledge-admin-web-prod

# 或同時啟動開發和生產模式
docker-compose --profile production up -d
```

**訪問地址：**
- 前端：http://localhost:8081

**技術細節：**
- 使用 Nginx 提供靜態文件（port 80）
- 對外映射到 port 8081
- 使用預先編譯的 dist 目錄
- 需要明確指定 `--profile production` 才會啟動

## 快速開始

### 日常開發流程

1. **啟動開發環境**
   ```bash
   docker-compose up -d
   ```

2. **修改代碼**
   - 編輯 `knowledge-admin/frontend/src/` 下的任何檔案
   - 瀏覽器會自動重新載入變更

3. **查看日誌**
   ```bash
   # 查看前端日誌
   docker logs -f aichatbot-knowledge-admin-web

   # 查看後端日誌
   docker logs -f aichatbot-knowledge-admin-api
   ```

4. **重啟服務（如有需要）**
   ```bash
   docker-compose restart knowledge-admin-web
   ```

### 生產環境部署

1. **切換到生產模式**
   ```bash
   # 停止開發模式
   docker-compose stop knowledge-admin-web

   # 啟動生產模式
   docker-compose --profile production up -d knowledge-admin-web-prod
   ```

2. **重新編譯前端**
   ```bash
   docker-compose --profile production build --no-cache knowledge-admin-web-prod
   docker-compose --profile production up -d knowledge-admin-web-prod
   ```

## 配置檔案

### docker-compose.yml

```yaml
# 開發模式（預設）
knowledge-admin-web:
  build:
    context: ./knowledge-admin/frontend
    target: builder  # 使用 Node.js 環境
  command: npm run dev
  ports:
    - "8080:5173"
  volumes:
    # 掛載原始碼以支援熱重載
    - ./knowledge-admin/frontend/src:/app/src
    - ./knowledge-admin/frontend/public:/app/public
    - ./knowledge-admin/frontend/index.html:/app/index.html
    - ./knowledge-admin/frontend/vite.config.js:/app/vite.config.js
    - ./knowledge-admin/frontend/package.json:/app/package.json
  environment:
    - NODE_ENV=development

# 生產模式
knowledge-admin-web-prod:
  build: ./knowledge-admin/frontend
  ports:
    - "8081:80"
  volumes:
    - ./knowledge-admin/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
  profiles:
    - production  # 需明確指定才會啟動
```

### vite.config.js

```javascript
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',       // 允許容器外部訪問
    port: 5173,            // 容器內端口（映射到主機 8087）
    strictPort: true,
    watch: {
      usePolling: true     // Docker 環境需要 polling 模式
    },
    proxy: {
      // ⚠️ 重要：更具體的路徑要放在前面

      // RAG API 路徑（優先匹配）
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

      // RAG API 別名
      '/rag-api': {
        target: 'http://rag-orchestrator:8100/api',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/rag-api/, '')
      }
    }
  }
})
```

**配置說明：**

1. **端口映射**:
   - 容器內：5173
   - 主機訪問：8087
   - Docker Compose: `"8087:5173"`

2. **Proxy 路徑優先級**:
   - `/api/v1` 必須放在 `/api` 之前
   - Vite 按順序匹配，第一個匹配的規則生效
   - 更具體的路徑要先定義

3. **服務名稱**:
   - ✅ 使用: `http://rag-orchestrator:8100`
   - ❌ 錯誤: `http://localhost:8100`
   - Docker 網絡內使用服務名稱通信

## 常見問題

### Q: 修改代碼後頁面沒有自動更新？

**A: 檢查以下項目：**

1. 確認使用的是開發模式：
   ```bash
   docker ps | grep knowledge-admin-web
   # 應該看到 "5173/tcp" 而非 "80/tcp"
   ```

2. 檢查 volume 是否正確掛載：
   ```bash
   docker inspect aichatbot-knowledge-admin-web | grep -A 10 Mounts
   ```

3. 查看前端日誌是否有錯誤：
   ```bash
   docker logs -f aichatbot-knowledge-admin-web
   ```

4. 重啟服務：
   ```bash
   docker-compose restart knowledge-admin-web
   ```

### Q: 熱重載在 Docker 中不工作？

**A: 確認 vite.config.js 中有設定 `usePolling: true`：**

```javascript
watch: {
  usePolling: true  // 這是必須的
}
```

Docker 環境的檔案系統事件可能無法正常觸發，需要使用 polling 模式。

### Q: 前端無法連接（Connection reset by peer）？

**A: 這通常是端口配置問題：**

**症狀：**
```bash
curl http://localhost:8087
# 輸出：curl: (56) Recv failure: Connection reset by peer
```

**解決方案：**

1. 檢查 vite.config.js 端口配置：
   ```javascript
   server: {
     port: 5173,  // ✅ 應該是 5173（不是 8087）
   }
   ```

2. 檢查 Docker 端口映射：
   ```bash
   docker-compose ps knowledge-admin-web
   # 應該看到：0.0.0.0:8087->5173/tcp
   ```

3. 如果配置錯誤，修正後重啟：
   ```bash
   docker-compose restart knowledge-admin-web
   ```

### Q: API 請求失敗（500 錯誤或 ECONNREFUSED）？

**A: 這是 Proxy 配置問題：**

**症狀：**
```
[vite] http proxy error: /api/v1/vendors
Error: connect ECONNREFUSED ::1:8000
```

**原因：**
- 前端請求 `/api/v1/vendors` 被錯誤地代理到 knowledge-admin-api
- 實際應該代理到 rag-orchestrator

**解決方案：**

1. 檢查 vite.config.js 的 proxy 配置順序：
   ```javascript
   proxy: {
     // ✅ 正確：/api/v1 在前面
     '/api/v1': {
       target: 'http://rag-orchestrator:8100',
       changeOrigin: true
     },
     '/api': {
       target: 'http://knowledge-admin-api:8000',
       changeOrigin: true
     }
   }
   ```

2. 確認使用 Docker 服務名稱（不是 localhost）：
   ```javascript
   // ✅ 正確
   target: 'http://rag-orchestrator:8100'

   // ❌ 錯誤（Docker 環境不適用）
   target: 'http://localhost:8100'
   ```

3. 修改後重啟前端容器：
   ```bash
   docker-compose restart knowledge-admin-web
   ```

4. 驗證服務連通性：
   ```bash
   # 從容器內測試
   docker exec aichatbot-knowledge-admin-web \
     wget -q -O - http://rag-orchestrator:8100/api/v1/vendors/1
   ```

### Q: 如何在開發模式和生產模式之間切換？

**A: 使用以下指令：**

```bash
# 切換到開發模式
docker-compose stop knowledge-admin-web-prod
docker-compose up -d knowledge-admin-web

# 切換到生產模式
docker-compose stop knowledge-admin-web
docker-compose --profile production up -d knowledge-admin-web-prod
```

### Q: 開發模式可以用於生產環境嗎？

**A: 不建議。**

開發模式：
- 記憶體使用較高
- 效能較低
- 包含開發工具和完整的 source map
- 不適合長時間運行

生產環境請使用 `knowledge-admin-web-prod`。

### Q: 需要安裝 Node.js 嗎？

**A: 不需要。**

所有前端工具都已包含在 Docker 容器中，本機不需要安裝 Node.js 或 npm。

## 效能比較

| 項目 | 開發模式 | 生產模式 |
|------|----------|----------|
| 熱重載 | ✅ 是 | ❌ 否 |
| 修改代碼後 | 即時生效 | 需重新編譯 |
| 啟動時間 | ~2-3 秒 | ~1 秒 |
| 記憶體使用 | ~200MB | ~20MB |
| 檔案大小 | 原始碼 | 壓縮後 |
| 除錯工具 | ✅ 完整 | ❌ 無 |
| Source Map | ✅ 是 | ❌ 否 |

## 技術架構

### 開發模式架構圖

```
本機原始碼
    ↓ (volume mount)
Docker 容器 (Node.js + Vite)
    ↓ (port 5173)
本機 (port 8080)
    ↓
瀏覽器
```

檔案變更 → Vite 監測 → HMR → 瀏覽器自動更新

### 生產模式架構圖

```
本機原始碼
    ↓ (COPY in Dockerfile)
Docker Build (npm run build)
    ↓
dist/ (靜態文件)
    ↓
Docker 容器 (Nginx)
    ↓ (port 80)
本機 (port 8081)
    ↓
瀏覽器
```

## 維護建議

1. **日常開發**：使用開發模式
2. **測試部署**：偶爾測試生產模式確保編譯正常
3. **CI/CD**：生產環境使用生產模式
4. **效能測試**：使用生產模式進行效能測試

## 相關文件

- [Vite 官方文件](https://vitejs.dev/)
- [Vue Router 文件](https://router.vuejs.org/)
- [Docker Compose 文件](https://docs.docker.com/compose/)

## 更新日誌

### 2025-10-12
- ✅ 實作前端開發模式（Hot Reload）
- ✅ 修改 vite.config.js 支援 Docker 環境
- ✅ 更新 docker-compose.yml 支援雙模式
- ✅ 新增生產模式 profile 配置
- ✅ 文件化開發流程
