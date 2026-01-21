# API 路徑清理更改記錄

**日期**: 2026-01-20
**任務**: 移除 `/rag-api/` 前綴，統一使用 `/api/v1/`
**原因**: Vite proxy 導致開發和生產環境不一致

---

## 📊 問題分析

### 問題
- 前端使用 `/rag-api/v1/*` 路徑
- 後端實際路徑是 `/api/v1/*`
- Vite 開發環境有 proxy 轉換，生產環境沒有
- 導致生產環境 404 錯誤

### 解決方案
- 移除所有 `/rag-api/` 使用
- 統一使用後端實際路徑 `/api/v1/`
- 開發和生產環境完全一致

---

## 🔍 發現的使用位置

### 配置文件
- ✅ `src/config/api.js` - 15+ 處使用 `/rag-api/v1/`

### Vue 組件
1. ✅ `src/views/FormEditorView.vue` - 2 處
2. ✅ `src/views/FormManagementView.vue` - 1 處
3. ✅ `src/views/KnowledgeImportView.vue` - 1 處
4. ✅ `src/views/KnowledgeExportView.vue` - 1 處
5. ✅ `src/views/KnowledgeView.vue` - 4 處（包括已修復的 1 處）
6. ✅ `src/views/DocumentConverterView.vue` - 1 處

### Vite 配置
- ✅ `vite.config.js` - `/rag-api` proxy 配置

**總計**: 約 25+ 處需要修改

---

## 📝 詳細更改記錄

### 1. 配置文件：src/config/api.js

**修改前**:
```javascript
// Vite proxy 會將 /rag-api/* 路由到 rag-orchestrator:8100/api/*
export const API_ENDPOINTS = {
  chat: `${API_BASE_URL}/rag-api/v1/chat`,
  intents: `${API_BASE_URL}/rag-api/v1/intents`,
  // ... 更多
};
```

**修改後**:
```javascript
// 直接使用後端實際路徑
export const API_ENDPOINTS = {
  chat: `${API_BASE_URL}/api/v1/chat`,
  intents: `${API_BASE_URL}/api/v1/intents`,
  // ... 更多
};
```

**影響範圍**:
- 所有使用 `API_ENDPOINTS` 的組件
- 自動修復約 50+ 個調用點

---

### 2. FormEditorView.vue

#### Line 331
**修改前**:
```javascript
const data = await api.get('/rag-api/v1/api-endpoints?scope=form&is_active=true');
```

**修改後**:
```javascript
const data = await api.get('/api/v1/api-endpoints?scope=form&is_active=true');
```

**原因**: 直接寫死的路徑，需要手動修改

---

#### Line 552
**修改前**:
```javascript
await api.post('/rag-api/v1/forms', data);
```

**修改後**:
```javascript
await api.post('/api/v1/forms', data);
```

---

### 3. FormManagementView.vue

#### Line 213
**修改前**:
```javascript
const response = await api.get('/rag-api/v1/forms', { params });
```

**修改後**:
```javascript
const response = await api.get('/api/v1/forms', { params });
```

---

### 4. KnowledgeImportView.vue

#### Line 472
**修改前**:
```javascript
const API_BASE = '/rag-api/v1';
```

**修改後**:
```javascript
const API_BASE = '/api/v1';
```

**影響**: 該文件中所有使用 `API_BASE` 的地方都會自動更新

---

### 5. KnowledgeExportView.vue

#### Line 183
**修改前**:
```javascript
const API_BASE = '/rag-api/v1';
```

**修改後**:
```javascript
const API_BASE = '/api/v1';
```

---

### 6. KnowledgeView.vue

#### Line 725
**修改前**:
```javascript
const response = await axios.get('/rag-api/v1/business-types-config');
```

**修改後**:
```javascript
const response = await axios.get('/api/v1/business-types-config');
```

---

#### Line 784
**修改前**:
```javascript
const response = await axios.get('/rag-api/v1/forms?is_active=true');
```

**修改後**:
```javascript
const response = await axios.get('/api/v1/forms?is_active=true');
```

---

#### Line 795 (已完成)
**修改前**:
```javascript
const response = await axios.get('/rag-api/v1/api-endpoints?scope=knowledge&is_active=true');
```

**修改後**:
```javascript
const response = await axios.get('/api/v1/api-endpoints?scope=knowledge&is_active=true');
```

**狀態**: ✅ 已在之前修復

---

#### Line 1280
**修改前**:
```javascript
const response = await fetch('/rag-api/v1/videos/upload', {
```

**修改後**:
```javascript
const response = await fetch('/api/v1/videos/upload', {
```

---

### 7. DocumentConverterView.vue

#### Line 219
**修改前**:
```javascript
const API_BASE = '/rag-api/v1';
```

**修改後**:
```javascript
const API_BASE = '/api/v1';
```

---

### 8. vite.config.js

#### 移除 /rag-api proxy

**修改前**:
```javascript
proxy: {
  '/api/v1': {
    target: 'http://rag-orchestrator:8100',
    changeOrigin: true
  },
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
```

**修改後**:
```javascript
proxy: {
  '/api/v1': {
    target: 'http://rag-orchestrator:8100',
    changeOrigin: true
  },
  '/api': {
    target: 'http://knowledge-admin-api:8000',
    changeOrigin: true
  }
  // 移除 /rag-api proxy - 不再需要
}
```

**原因**: 不再使用 `/rag-api/`，直接用實際路徑

---

## ✅ 驗證步驟

### 1. 搜尋確認
```bash
# 確認沒有遺漏的 /rag-api/ 使用
grep -r "'/rag-api/" src/ --include="*.vue" --include="*.js"
# 預期結果：無任何匹配
```

### 2. 編譯測試
```bash
cd knowledge-admin/frontend
npm run build
# 預期結果：編譯成功，無錯誤
```

### 3. 功能測試
- [ ] 知識管理頁面載入 API endpoints
- [ ] 表單管理頁面正常工作
- [ ] 知識匯入/匯出功能
- [ ] 文檔轉換功能
- [ ] 聊天功能正常

---

## 📊 影響評估

### 開發環境
- ✅ 仍然正常工作（Vite proxy 已配置 `/api/v1`）
- ✅ 不依賴 `/rag-api/` rewrite

### 生產環境
- ✅ 修復 404 錯誤
- ✅ API 路徑與後端一致

### 向後兼容性
- ⚠️ 如果有其他服務依賴 `/rag-api/` 前綴，需要同步更新
- ✅ 前端內部完全獨立，不影響其他服務

---

## 🎯 預期效果

### 問題解決
- ✅ 開發和生產環境完全一致
- ✅ 不再有 API 路徑混亂
- ✅ 代碼更清晰易懂

### 維護改善
- ✅ 減少一層 proxy rewrite
- ✅ 路徑即服務（一看就知道是哪個後端）
- ✅ 新開發者更容易理解

---

## 📋 後續工作

### 立即（本次完成）
- [x] 搜尋所有使用位置
- [x] 修改所有文件
- [x] 移除 Vite proxy 配置
- [x] 編譯測試
- [x] 創建詳細記錄文檔

### 短期（建議）
- [ ] 創建 API 路徑規範文檔
- [ ] 添加 ESLint 規則防止直接寫死路徑
- [ ] 更新開發者指南

### 長期（可選）
- [ ] 添加 pre-commit hook 檢查
- [ ] CI/CD 中添加 API 路徑驗證
- [ ] 創建自動化測試覆蓋 API 調用

---

## 🔧 回滾方案

如果需要回滾，執行以下步驟：

1. 恢復所有文件的修改
2. 恢復 `vite.config.js` 的 `/rag-api` proxy
3. 重新編譯

備份位置：Git 歷史記錄

---

## 📞 聯繫資訊

**執行者**: Claude Code
**日期**: 2026-01-20
**相關 Issue**: API 路徑不一致問題

---

## 附錄：完整文件列表

### 修改的文件
1. `knowledge-admin/frontend/src/config/api.js`
2. `knowledge-admin/frontend/src/views/FormEditorView.vue`
3. `knowledge-admin/frontend/src/views/FormManagementView.vue`
4. `knowledge-admin/frontend/src/views/KnowledgeImportView.vue`
5. `knowledge-admin/frontend/src/views/KnowledgeExportView.vue`
6. `knowledge-admin/frontend/src/views/KnowledgeView.vue`
7. `knowledge-admin/frontend/src/views/DocumentConverterView.vue`
8. `knowledge-admin/frontend/vite.config.js`

### 新增的文件
1. `docs/CHANGELOG_RAG_API_PATH_CLEANUP.md` (本文件)
2. `docs/API_PATH_CONVENTIONS.md` (待創建)

---

**更改記錄完成** ✅
