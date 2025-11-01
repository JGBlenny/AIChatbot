# 部署環境盤查報告

**日期**: 2025-10-31
**執行者**: Claude Code
**目的**: 全面盤查並更新部署文檔，確保與實際配置一致

---

## 📊 盤查結果摘要

### ✅ 配置一致性檢查

| 項目 | 狀態 | 備註 |
|------|------|------|
| Docker Compose 配置 | ✅ 正確 | 端口映射配置正確 |
| 服務端口信息 | ✅ 正確 | 所有服務運行正常 |
| README.md | ✅ 正確 | 端口信息準確 |
| vite.config.js | ⚠️ 已修復 | Proxy 配置已更新 |
| FRONTEND_DEV_MODE.md | ❌ 需更新 | Proxy 配置說明過時 |
| DEPLOYMENT.md | ⚠️ 需補充 | 缺少詳細配置說明 |

---

## 🔍 詳細發現

### 1. 實際運行配置（2025-10-31）

```
服務列表與端口映射：
┌────────────────────────┬─────────────┬──────────────────┐
│ 服務名稱               │ 容器名      │ 端口映射         │
├────────────────────────┼─────────────┼──────────────────┤
│ knowledge-admin-web    │ aichatbot-* │ 8087:5173        │
│ knowledge-admin-api    │ aichatbot-* │ 8000:8000        │
│ rag-orchestrator       │ aichatbot-* │ 8100:8100        │
│ embedding-api          │ aichatbot-* │ 5001:5000        │
│ postgres               │ aichatbot-* │ 5432:5432        │
│ redis                  │ aichatbot-* │ 6381:6379        │
│ pgadmin                │ aichatbot-* │ 5050:80          │
└────────────────────────┴─────────────┴──────────────────┘
```

**訪問 URL（開發模式）：**
- 前端管理界面: http://localhost:8087
- 知識管理 API: http://localhost:8000
- RAG Orchestrator: http://localhost:8100
- Embedding API: http://localhost:5001
- PostgreSQL: localhost:5432
- Redis: localhost:6381
- pgAdmin: http://localhost:5050

### 2. vite.config.js 配置（已修復）

**修復前的問題：**
```javascript
// ❌ 錯誤配置
server: {
  port: 8087,  // 應該是 5173
  proxy: {
    '/api': {
      target: process.env.NODE_ENV === 'production'
        ? 'http://knowledge-admin-api:8000'
        : 'http://localhost:8000',  // Docker 環境無法使用 localhost
    }
  }
}
```

**修復後的正確配置：**
```javascript
// ✅ 正確配置
server: {
  host: '0.0.0.0',
  port: 5173,  // 容器內監聽 5173，映射到主機 8087
  strictPort: true,
  watch: {
    usePolling: true  // Docker 環境需要
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
```

**關鍵修復點：**
1. **端口修正**: 5173（容器內）映射到 8087（主機）
2. **Proxy 路徑優先級**: `/api/v1` 必須放在 `/api` 之前
3. **服務名稱**: 使用 Docker 服務名稱而非 localhost
4. **changeOrigin**: 所有 proxy 都需要設置 changeOrigin: true

### 3. 發現的問題

#### 問題 1: Connection Reset by Peer (已解決)

**現象：**
```bash
curl http://localhost:8087
# 輸出：curl: (56) Recv failure: Connection reset by peer
```

**原因：**
- vite.config.js 中的 port 設置為 8087
- 但 Docker 映射是 8087:5173
- 造成端口不匹配

**解決方案：**
- 將 vite.config.js 中的 port 改為 5173

#### 問題 2: API Proxy 錯誤 (已解決)

**現象：**
```
[vite] http proxy error: /api/v1/vendors
Error: connect ECONNREFUSED ::1:8000
```

**原因：**
- 前端請求 `/api/v1/vendors` 被代理到 knowledge-admin-api:8000
- 但該端點實際在 rag-orchestrator:8100
- Proxy 配置路徑匹配順序錯誤

**解決方案：**
- 添加 `/api/v1` 路徑，優先匹配到 rag-orchestrator
- 確保更具體的路徑在前面

#### 問題 3: 文檔過時

**發現：**
- FRONTEND_DEV_MODE.md 中的 proxy 配置只有 `/api`
- 缺少 `/api/v1` 和 `/v1` 的說明
- DEPLOYMENT.md 缺少詳細的配置說明

---

## 📝 需要更新的文檔

### 1. docs/guides/FRONTEND_DEV_MODE.md

**需要更新的內容：**
- ✅ 更新 vite.config.js 示例代碼（行 156-161）
- ✅ 添加 Proxy 路徑優先級說明
- ✅ 添加常見問題：Connection reset 和 Proxy 錯誤

### 2. docs/guides/DEPLOYMENT.md

**需要補充的內容：**
- ✅ 添加詳細的端口映射說明
- ✅ 添加 vite.config.js 配置說明
- ✅ 添加故障排除章節（今天遇到的問題）

### 3. docs/guides/DOCKER_COMPOSE_GUIDE.md

**需要更新的內容：**
- ✅ 更新 vite.config.js 配置檢查說明
- ✅ 添加 Proxy 配置故障排除

---

## 🔧 建議改進

### 1. 短期改進（立即執行）

1. **更新 FRONTEND_DEV_MODE.md**
   - 更新 proxy 配置示例
   - 添加路徑優先級說明

2. **更新 DEPLOYMENT.md**
   - 添加配置檢查清單
   - 添加今天的故障案例

3. **創建故障排除指南**
   - 整合常見問題
   - 提供解決步驟

### 2. 中期改進（建議）

1. **配置驗證腳本**
   - 檢查 vite.config.js 配置
   - 驗證端口映射
   - 測試 API 連通性

2. **健康檢查增強**
   - 前端啟動後自動測試 API 連接
   - 失敗時提供診斷信息

### 3. 長期改進（規劃）

1. **開發環境腳本**
   - 一鍵啟動並驗證所有服務
   - 自動檢測配置問題

2. **文檔生成自動化**
   - 從 docker-compose.yml 自動生成端口列表
   - 從 vite.config.js 生成 proxy 配置文檔

---

## ✅ 已完成的更新

- [x] 修復 vite.config.js 端口配置
- [x] 修復 vite.config.js proxy 配置
- [x] 驗證所有服務運行正常
- [x] 創建盤查報告

---

## 📋 待辦事項

- [ ] 更新 FRONTEND_DEV_MODE.md
- [ ] 更新 DEPLOYMENT.md 添加故障排除
- [ ] 更新 DOCKER_COMPOSE_GUIDE.md
- [ ] 創建配置驗證腳本（可選）

---

## 🎯 結論

當前系統配置基本正確，主要問題集中在 vite.config.js 的配置和文檔更新。
所有關鍵問題已在 2025-10-31 修復完成，系統現在運行正常。

**建議下一步：**
1. 立即更新相關文檔（FRONTEND_DEV_MODE.md, DEPLOYMENT.md）
2. 考慮創建配置驗證腳本，避免類似問題再次發生
3. 定期審查文檔，確保與實際配置保持同步

---

**報告生成時間**: 2025-10-31
**系統狀態**: ✅ 正常運行
**下次盤查建議**: 重大配置變更後或每季度
