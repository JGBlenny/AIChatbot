# 開發工作流程指南

本文件說明如何在開發時快速修改程式碼，避免每次都要重新打包 Docker 映像檔。

## 方案一：生產模式 + Volume 掛載（推薦）

這種方式使用 nginx 容器提供靜態檔案，但透過 volume 掛載本地編譯後的檔案。

### 優點
- ✅ 接近生產環境
- ✅ 修改程式碼後只需本地重新編譯（無需重建 Docker）
- ✅ 快速更新（1-2 秒）

### 使用步驟

1. **首次設定（或 package.json 變更後）**
   ```bash
   cd knowledge-admin/frontend
   npm install
   ```

2. **修改程式碼後，重新編譯**
   ```bash
   cd knowledge-admin/frontend
   npm run build
   ```
   編譯完成後，刷新瀏覽器即可看到變更（dist 目錄已透過 volume 掛載到容器）

3. **重啟前端容器（如果需要）**
   ```bash
   docker-compose restart knowledge-admin-web
   ```

### 當前配置
`docker-compose.yml` 已配置 volume 掛載：
```yaml
knowledge-admin-web:
  volumes:
    - ./knowledge-admin/frontend/dist:/usr/share/nginx/html
    - ./knowledge-admin/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
```

---

## 方案二：開發模式 + 熱重載（適合頻繁修改）

這種方式使用 Vite 開發伺服器，支援熱重載（HMR），修改程式碼後自動重新編譯。

### 優點
- ✅ 支援熱重載（儲存後自動更新）
- ✅ 快速開發體驗
- ✅ 無需手動編譯

### 缺點
- ⚠️ 與生產環境稍有差異
- ⚠️ 首次啟動較慢（需要安裝依賴）

### 使用步驟

1. **啟動開發環境**
   ```bash
   # 停止生產環境的前端服務
   docker-compose stop knowledge-admin-web

   # 啟動開發環境
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d knowledge-admin-web-dev
   ```

2. **查看日誌（確認 Vite 已啟動）**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f knowledge-admin-web-dev
   ```
   看到 `ready in XXX ms` 表示啟動成功

3. **開始開發**
   - 修改 `knowledge-admin/frontend/src` 中的任何檔案
   - 儲存後瀏覽器會自動重新載入

4. **返回生產模式**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml stop knowledge-admin-web-dev
   docker-compose up -d knowledge-admin-web
   ```

---

## 方案三：完全本地開發（不使用 Docker）

如果你想要最快的開發體驗，可以完全在本地運行前端。

### 使用步驟

1. **安裝依賴**
   ```bash
   cd knowledge-admin/frontend
   npm install
   ```

2. **啟動開發伺服器**
   ```bash
   npm run dev
   ```
   預設會在 http://localhost:5173 啟動

3. **修改 API 端點配置（開發時）**

   由於本地開發時沒有 nginx 代理，你可能需要：

   選項 A：使用 Vite 的 proxy 功能

   在 `vite.config.js` 中添加：
   ```javascript
   export default {
     server: {
       proxy: {
         '/api': 'http://localhost:8000',
         '/rag-api': 'http://localhost:8100'
       }
     }
   }
   ```

   選項 B：暫時修改程式碼中的 API 端點
   ```javascript
   // 開發時使用完整 URL
   const API_BASE = 'http://localhost:8000/api';
   const RAG_API = 'http://localhost:8100/api/v1';
   ```

---

## 比較表格

| 特性 | 方案一（Volume 掛載） | 方案二（開發模式） | 方案三（完全本地） |
|------|---------------------|-------------------|------------------|
| 更新速度 | ⚡️ 快（1-2秒） | ⚡️⚡️⚡️ 最快（即時） | ⚡️⚡️⚡️ 最快（即時） |
| 與生產環境一致性 | ✅ 高 | ⚠️ 中 | ⚠️ 低 |
| 需要手動編譯 | ✅ 是 | ❌ 否 | ❌ 否 |
| Docker 依賴 | ✅ 是 | ✅ 是 | ❌ 否 |
| 適合場景 | 小修改、測試 | 大量開發 | 純前端開發 |

---

## 推薦工作流程

### 日常開發
1. 使用 **方案二（開發模式）** 或 **方案三（完全本地）**
2. 頻繁修改程式碼，利用熱重載快速驗證

### 測試與驗證
1. 使用 **方案一（Volume 掛載）**
2. 在接近生產環境的狀態下測試
3. 本地編譯後立即看到結果

### 部署前檢查
1. 使用 **完整 Docker 構建**（不用 volume）
2. 確保所有變更都正確打包
   ```bash
   docker-compose build --no-cache knowledge-admin-web
   docker-compose up -d knowledge-admin-web
   ```

---

## 疑難排解

### 問題：修改程式碼後沒有變化

**方案一（Volume 掛載）**
```bash
# 確認是否重新編譯
cd knowledge-admin/frontend
npm run build

# 檢查 dist 目錄更新時間
ls -la dist/

# 重啟容器
docker-compose restart knowledge-admin-web

# 清除瀏覽器快取
Ctrl+Shift+R (強制重新整理)
```

**方案二（開發模式）**
```bash
# 檢查容器日誌
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs knowledge-admin-web-dev

# 重啟開發容器
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart knowledge-admin-web-dev
```

### 問題：Volume 掛載後容器無法啟動

```bash
# 檢查 dist 目錄是否存在
ls -la knowledge-admin/frontend/dist/

# 如果不存在，先編譯
cd knowledge-admin/frontend
npm run build

# 檢查容器日誌
docker-compose logs knowledge-admin-web
```

### 問題：API 端點 404 錯誤

檢查 nginx 配置中的 proxy_pass：
```bash
cat knowledge-admin/frontend/nginx.conf
```

確認路徑配置正確：
- `/api/` → `http://knowledge-admin-api:8000/api/`
- `/rag-api/` → `http://rag-orchestrator:8100/api/`

---

## 後端開發（Python）

後端也可以使用類似的 volume 掛載方式：

### 方案：使用 docker-compose.dev.yml 中的開發配置

```bash
# 停止生產環境的後端服務
docker-compose stop knowledge-admin-api rag-orchestrator

# 啟動開發環境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d knowledge-admin-api-dev rag-orchestrator-dev
```

修改 Python 程式碼後，變更會立即生效（FastAPI 預設支援熱重載）。

---

## 總結

- 🚀 **快速開發**：使用方案二或方案三
- 🎯 **測試驗證**：使用方案一
- 📦 **部署前**：完整 Docker 構建

選擇適合你當前需求的方案，提升開發效率！
