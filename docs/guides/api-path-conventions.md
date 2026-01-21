# API 路徑使用規範

**版本**: 1.0
**更新日期**: 2026-01-20
**狀態**: ✅ 生效中

---

## 🎯 核心規則

### 規則 1: 按服務區分路徑前綴

- **RAG Orchestrator API**: 必須使用 `/rag-api/v1/*` 前綴
- **Knowledge Admin API**: 使用 `/api/*` 前綴

### 規則 2: 統一使用 `api.js` 配置

- 所有 API 端點必須在 `src/config/api.js` 中定義
- 組件中不要硬編碼 API 路徑
- 特殊情況可以在組件中定義 `API_BASE` 常數

### 規則 3: 開發/生產環境一致

- 前端路徑在兩個環境必須相同
- 不要依賴開發環境獨有的配置

---

## 📋 RAG Orchestrator API 端點

**前端路徑前綴**: `/rag-api/v1/`
**後端實際路徑**: `/api/v1/`
**路徑轉換**: 由 Nginx/Vite 自動處理

### Chat 相關
```javascript
POST   /rag-api/v1/chat                    // AI 對話
POST   /rag-api/v1/chat/stream             // AI 對話（串流）
```

### Intent 相關
```javascript
GET    /rag-api/v1/intents                 // 意圖列表
GET    /rag-api/v1/intents/:id             // 單一意圖
```

### Business Types 相關
```javascript
GET    /rag-api/v1/business-types-config   // 業態類型配置
```

### Forms 相關
```javascript
GET    /rag-api/v1/forms                   // 表單列表
GET    /rag-api/v1/forms/:id               // 單一表單
POST   /rag-api/v1/forms                   // 創建表單
PUT    /rag-api/v1/forms/:id               // 更新表單
DELETE /rag-api/v1/forms/:id               // 刪除表單

GET    /rag-api/v1/form-submissions        // 表單提交記錄
PATCH  /rag-api/v1/form-submissions/:id    // 更新提交狀態
```

### API Endpoints 相關
```javascript
GET    /rag-api/v1/api-endpoints           // API 端點列表
GET    /rag-api/v1/api-endpoints/:id       // 單一端點
POST   /rag-api/v1/api-endpoints           // 創建端點
PUT    /rag-api/v1/api-endpoints/:id       // 更新端點
DELETE /rag-api/v1/api-endpoints/:id       // 刪除端點
```

### Knowledge 相關
```javascript
POST   /rag-api/v1/knowledge/classify      // 知識分類
POST   /rag-api/v1/knowledge/classify/batch // 批次分類
GET    /rag-api/v1/knowledge/stats         // 知識統計
POST   /rag-api/v1/knowledge/reload        // 重載知識庫
```

### Knowledge Import 相關
```javascript
POST   /rag-api/v1/knowledge-import/upload         // 上傳 LINE 聊天記錄
GET    /rag-api/v1/knowledge-import/jobs           // 導入任務列表
GET    /rag-api/v1/knowledge-import/jobs/:id       // 單一任務
POST   /rag-api/v1/knowledge-import/jobs/:id/confirm // 確認導入
DELETE /rag-api/v1/knowledge-import/jobs/:id       // 刪除任務
POST   /rag-api/v1/knowledge-import/preview        // 預覽導入
```

### Knowledge Export 相關
```javascript
POST   /rag-api/v1/knowledge-export/excel          // 導出知識為 Excel
```

### Videos 相關
```javascript
POST   /rag-api/v1/videos/upload                   // 上傳影片（S3）
DELETE /rag-api/v1/videos/:knowledge_id            // 刪除影片
GET    /rag-api/v1/videos/:knowledge_id/info       // 影片資訊
```

### Document Converter 相關
```javascript
POST   /rag-api/v1/document-converter/upload       // 上傳文檔（Word/PDF）
POST   /rag-api/v1/document-converter/:id/parse    // 解析文檔
POST   /rag-api/v1/document-converter/:id/convert  // 轉換為 Q&A
GET    /rag-api/v1/document-converter/:id          // 任務狀態
PUT    /rag-api/v1/document-converter/:id/qa-list  // 更新 Q&A
POST   /rag-api/v1/document-converter/:id/export-csv // 導出 CSV
DELETE /rag-api/v1/document-converter/:id          // 刪除任務
```

### Vendors 相關
```javascript
POST   /rag-api/v1/vendors/:id/chat                // 業者專屬對話
GET    /rag-api/v1/vendors/:id/sops                // 業者 SOP 列表
```

### Unclear Questions 相關
```javascript
GET    /rag-api/v1/unclear-questions                // 不明確問題列表
GET    /rag-api/v1/unclear-questions/:id            // 單一問題
```

### Knowledge Candidates 相關
```javascript
GET    /rag-api/v1/knowledge-candidates/pending     // 待審核知識
GET    /rag-api/v1/knowledge-candidates/stats       // 統計資訊
GET    /rag-api/v1/knowledge-candidates/:id         // 單一候選
PUT    /rag-api/v1/knowledge-candidates/:id/edit    // 編輯候選
POST   /rag-api/v1/knowledge-candidates/:id/review  // 審核（通過/拒絕）
```

### Platform SOP 相關
```javascript
GET    /rag-api/v1/platform/sop/categories          // SOP 分類
GET    /rag-api/v1/platform/sop/groups               // SOP 群組
GET    /rag-api/v1/platform/sop/templates            // SOP 模板
```

---

## 📋 Knowledge Admin API 端點

**前端路徑前綴**: `/api/`
**後端實際路徑**: `/api/`
**路徑轉換**: 無

### Knowledge Base 相關
```javascript
GET    /api/knowledge                      // 知識庫列表
GET    /api/knowledge/:id                  // 單一知識
POST   /api/knowledge                      // 創建知識
PUT    /api/knowledge/:id                  // 更新知識
DELETE /api/knowledge/:id                  // 刪除知識

POST   /api/knowledge/regenerate-embeddings // 重新生成向量
POST   /api/knowledge/:id/intents          // 關聯意圖
DELETE /api/knowledge/:id/intents/:intent_id // 移除意圖關聯
```

### Intents 相關
```javascript
GET    /api/intents                        // 意圖列表
```

### Vendors 相關
```javascript
GET    /api/vendors                        // 業者列表
GET    /api/vendors/:id                    // 單一業者
POST   /api/vendors                        // 創建業者
PUT    /api/vendors/:id                    // 更新業者
DELETE /api/vendors/:id                    // 刪除業者
```

### Test Scenarios 相關
```javascript
GET    /api/test-scenarios                 // 測試情境列表
GET    /api/test-scenarios/:id             // 單一情境
POST   /api/test-scenarios                 // 創建情境
PUT    /api/test-scenarios/:id             // 更新情境
DELETE /api/test-scenarios/:id             // 刪除情境
```

### Backtest 相關
```javascript
GET    /api/backtest/results               // 回測結果
GET    /api/backtest/summary               // 回測摘要
GET    /api/backtest/runs                  // 回測執行記錄
GET    /api/backtest/runs/:id/results      // 特定執行的結果
POST   /api/backtest/run                   // 執行回測
POST   /api/backtest/cancel                // 取消回測
GET    /api/backtest/status                // 回測狀態
```

### Target Users 相關
```javascript
GET    /api/target-users                   // 目標用戶列表
GET    /api/target-users-config            // 用戶配置
POST   /api/target-users-config            // 新增配置
PUT    /api/target-users-config/:value     // 更新配置
DELETE /api/target-users-config/:value     // 刪除配置
```

### Category Config 相關
```javascript
GET    /api/category-config                // 分類配置
POST   /api/category-config                // 新增分類
```

### Stats 相關
```javascript
GET    /api/stats                          // 統計資訊
```

### Authentication 相關
```javascript
POST   /api/auth/login                     // 登入
POST   /api/auth/logout                    // 登出
GET    /api/auth/me                        // 當前用戶資訊
```

### Admin Management 相關
```javascript
GET    /api/admins                         // 管理員列表
GET    /api/admins/:id                     // 單一管理員
POST   /api/admins                         // 創建管理員
PUT    /api/admins/:id                     // 更新管理員
DELETE /api/admins/:id                     // 刪除管理員
```

### Role Management 相關
```javascript
GET    /api/roles                          // 角色列表
GET    /api/roles/:id                      // 單一角色
POST   /api/roles                          // 創建角色
PUT    /api/roles/:id                      // 更新角色
DELETE /api/roles/:id                      // 刪除角色
```

---

## 💻 使用範例

### 在 `api.js` 中定義（推薦）

```javascript
// src/config/api.js
export const API_ENDPOINTS = {
  // ✅ RAG Orchestrator - 使用 /rag-api/v1/
  chat: `${API_BASE_URL}/rag-api/v1/chat`,
  forms: `${API_BASE_URL}/rag-api/v1/forms`,

  // ✅ Knowledge Admin - 使用 /api/
  knowledge: '/api/knowledge',
  vendors: '/api/vendors'
};
```

### 在組件中使用

```javascript
// ✅ 推薦：使用 api.js 中的定義
import { API_ENDPOINTS } from '@/config/api';

const response = await axios.get(API_ENDPOINTS.chat);
const forms = await axios.get(API_ENDPOINTS.forms);
```

### 在組件中定義常數（特殊情況）

```javascript
// ✅ 可接受：組件內定義 API_BASE
const API_BASE = '/rag-api/v1';

const response = await axios.get(`${API_BASE}/knowledge-import/jobs`);
const upload = await axios.post(`${API_BASE}/knowledge-import/upload`, data);
```

### 直接使用路徑（特殊情況）

```javascript
// ✅ 可接受：特定組件的獨有 API
const response = await axios.get('/rag-api/v1/business-types-config');
const forms = await axios.get('/rag-api/v1/forms?is_active=true');
```

---

## ❌ 常見錯誤

### 錯誤 1: 使用錯誤的前綴訪問 RAG API

```javascript
// ❌ 錯誤：在生產環境會路由到 Knowledge Admin API
const response = await axios.get('/api/v1/chat');
const forms = await axios.get('/api/v1/forms');

// ✅ 正確：使用 /rag-api/v1/ 前綴
const response = await axios.get('/rag-api/v1/chat');
const forms = await axios.get('/rag-api/v1/forms');
```

**原因：** Nginx 會將 `/api/v1/xxx` 匹配到 `/api/`，轉發給 Knowledge Admin API。

### 錯誤 2: 硬編碼 API 路徑

```javascript
// ❌ 錯誤：硬編碼路徑，難以維護
async function loadData() {
  const r1 = await axios.get('http://localhost:8100/api/v1/chat');
  const r2 = await axios.get('http://rag-orchestrator:8100/api/v1/forms');
}

// ✅ 正確：使用 api.js 配置
import { API_ENDPOINTS } from '@/config/api';

async function loadData() {
  const r1 = await axios.get(API_ENDPOINTS.chat);
  const r2 = await axios.get(API_ENDPOINTS.forms);
}
```

### 錯誤 3: 混用 RAG 和 Admin API

```javascript
// ❌ 錯誤：混淆 RAG API 和 Admin API
const ragIntents = await axios.get('/api/intents');  // 這是 Admin API
const adminIntents = await axios.get('/rag-api/v1/intents');  // 這是 RAG API

// ✅ 正確：明確區分
const ragIntents = await axios.get('/rag-api/v1/intents');    // RAG API
const adminIntents = await axios.get('/api/intents');         // Admin API
```

**注意：** 雖然兩個 API 都有 `/intents` 端點，但用途不同。

---

## 🔧 環境配置

### 開發環境 (Vite)

```javascript
// knowledge-admin/frontend/vite.config.js
export default defineConfig({
  server: {
    proxy: {
      // RAG Orchestrator API
      '/rag-api': {
        target: 'http://rag-orchestrator:8100/api',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/rag-api/, '')
      },
      // Knowledge Admin API
      '/api': {
        target: 'http://knowledge-admin-api:8000',
        changeOrigin: true
      }
    }
  }
});
```

**路徑轉換：**
- 前端 `/rag-api/v1/chat` → 後端 `rag-orchestrator:8100/api/v1/chat`
- 前端 `/api/knowledge` → 後端 `knowledge-admin-api:8000/api/knowledge`

### 生產環境 (Nginx)

```nginx
# knowledge-admin/frontend/nginx.conf
server {
    listen 80;

    # RAG Orchestrator API
    location /rag-api/ {
        rewrite ^/rag-api/(.*)$ /api/$1 break;
        proxy_pass http://rag-orchestrator:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Knowledge Admin API
    location /api/ {
        proxy_pass http://knowledge-admin-api:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**路徑轉換：**
- 前端 `/rag-api/v1/chat` → rewrite → `rag-orchestrator:8100/api/v1/chat`
- 前端 `/api/knowledge` → 直接轉發 → `knowledge-admin-api:8000/api/knowledge`

---

## ✅ 檢查清單

### 新增 API 調用時

- [ ] 確認目標服務（RAG 或 Admin）
- [ ] 使用正確的路徑前綴（`/rag-api/v1/` 或 `/api/`）
- [ ] 優先在 `api.js` 中定義端點
- [ ] 測試開發環境
- [ ] 測試生產環境

### 修改 API 路徑時

- [ ] 搜尋所有使用該路徑的地方
- [ ] 確保開發/生產環境一致
- [ ] 更新相關文檔
- [ ] 執行回歸測試

### Code Review 時

- [ ] 檢查是否使用正確的路徑前綴
- [ ] 檢查是否有硬編碼的完整 URL
- [ ] 檢查是否應該在 `api.js` 中定義
- [ ] 檢查註釋是否清晰

---

## 📚 相關資源

### 文檔
- [API 架構分析](/tmp/API_ARCHITECTURE_ANALYSIS.md)
- [API 路徑回滾報告](./API_PATH_ROLLBACK_REPORT.md)
- [Nginx 配置](../knowledge-admin/frontend/nginx.conf)
- [Vite 配置](../knowledge-admin/frontend/vite.config.js)

### 配置文件
- `src/config/api.js` - API 端點定義
- `vite.config.js` - 開發環境代理配置
- `nginx.conf` - 生產環境路由配置

### 後端路由
- `rag-orchestrator/app.py` - RAG API 路由
- `knowledge-admin/backend/app.py` - Admin API 路由

---

## 🔄 版本歷史

### v1.0 (2026-01-20)
- 初始版本
- 定義 RAG API 使用 `/rag-api/v1/` 前綴
- 定義 Admin API 使用 `/api/` 前綴
- 統計所有 API 端點
- 提供使用範例和錯誤案例

---

**最後更新**: 2026-01-20
**維護者**: Development Team
**狀態**: ✅ 生效中

如有疑問，請參考 [API 架構分析文檔](/tmp/API_ARCHITECTURE_ANALYSIS.md)。
