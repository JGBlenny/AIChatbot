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
    port: 5173,
    strictPort: true,
    watch: {
      usePolling: true     // Docker 環境需要 polling 模式
    },
    proxy: {
      '/api': {
        target: 'http://knowledge-admin-api:8000',
        changeOrigin: true
      }
    }
  }
})
```

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
