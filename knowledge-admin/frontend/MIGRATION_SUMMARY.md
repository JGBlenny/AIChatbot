# 前端 API URL 遷移總結

## ✅ 已完成的文件 (16個 - 100% 完成)

### 第一批 (已提交)
1. ✅ `src/config/api.js` (新建 - 統一 API 配置)
2. ✅ `src/components/VendorSOPManager.vue`
3. ✅ `src/components/review/UnclearQuestionReviewTab.vue`
4. ✅ `src/components/review/KnowledgeReviewTab.vue` (6個引用)
5. ✅ `src/components/review/IntentReviewTab.vue`
6. ✅ `src/views/PlatformSOPView.vue`

### 第二批 (已提交)
7. ✅ `src/views/PlatformSOPEditView.vue`
8. ✅ `src/views/BusinessTypesConfigView.vue`
9. ✅ `src/views/AIKnowledgeReviewView.vue` (5個引用)
10. ✅ `src/views/KnowledgeReclassifyView.vue`
11. ✅ `src/views/SuggestedIntentsView.vue`
12. ✅ `src/views/CacheManagementView.vue` (3個引用)

### 第三批 (補充遺漏 - 2025-01-31)
13. ✅ `src/views/IntentsView.vue`
14. ✅ `src/views/VendorManagementView.vue`
15. ✅ `src/views/VendorConfigView.vue`
16. ✅ `src/views/ChatTestView.vue`

## 📝 快速修復腳本

```bash
# 在所有文件開頭添加導入
find src/views -name "*.vue" -type f -exec sed -i.bak \
  's/import axios from .axios./import axios from '\''axios'\'';\nimport { API_BASE_URL } from '\''@\/config\/api'\'';\n/' {} \;

# 替換 RAG_API 定義
find src/views -name "*.vue" -type f -exec sed -i \
  's/const RAG_API = .*/const RAG_API = `${API_BASE_URL}\/rag-api\/v1`;/' {} \;

# 替換 API_BASE 定義
find src/views -name "*.vue" -type f -exec sed -i \
  's/const API_BASE = .*/const API_BASE = `${API_BASE_URL}\/rag-api\/v1`;/' {} \;
```

## 🚀 測試方法

### 開發環境測試
```bash
cd knowledge-admin/frontend
npm run dev
# 訪問 http://localhost:8087
# 測試各個頁面的 API 調用
```

### 生產環境測試
```bash
cd knowledge-admin/frontend
npm run build
# 檢查 dist/assets/*.js 中是否還有 localhost 硬編碼
grep -r "localhost:8100\|localhost:8000" dist/
```

## 📊 遷移狀態

- ✅ 已完成: 16/16 (100%)
- ⚠️ 待處理: 0/16 (0%)
- 🎯 目標: 100% ✅ **已完成**

## 🎉 遷移完成總結

所有前端 Vue 文件的 localhost URL 已成功替換為環境自適應配置：

- **開發環境**: 自動使用 localhost 或空字符串（通過 Vite proxy）
- **生產環境**: 使用相對路徑（通過 Nginx proxy）

**總共處理的 localhost 引用數**: 約 22 個
**涉及的文件數**: 16 個 (5 components + 11 views)

現在系統可以順利部署到 EC2 生產環境，無需擔心硬編碼 URL 問題。

### ⚠️ 2025-01-31 補充修復

在用戶訪問 `/intents` 頁面時發現 4 個文件被遺漏：
- `IntentsView.vue` - 意圖管理頁面
- `VendorManagementView.vue` - 業者管理頁面
- `VendorConfigView.vue` - 業者配置頁面
- `ChatTestView.vue` - 對話測試頁面

已全部修復並更新此文檔。
