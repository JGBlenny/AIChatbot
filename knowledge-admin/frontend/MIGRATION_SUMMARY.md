# 前端 API URL 遷移總結

## ✅ 已完成的文件 (6個)

1. ✅ `src/components/VendorSOPManager.vue`
2. ✅ `src/components/review/UnclearQuestionReviewTab.vue`
3. ✅ `src/components/review/KnowledgeReviewTab.vue` (6個引用)
4. ✅ `src/components/review/IntentReviewTab.vue`
5. ✅ `src/views/PlatformSOPView.vue`
6. ✅ `src/config/api.js` (新建)

## ⚠️ 待完成的文件 (6個)

這些文件仍需手動更新或在下次部署前處理：

1. `src/views/PlatformSOPEditView.vue`
   - 第 483 行: `const RAG_API = import.meta.env.VITE_RAG_API || 'http://localhost:8100';`

2. `src/views/BusinessTypesConfigView.vue`
   - 第 176 行: `const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8100/api/v1';`

3. `src/views/AIKnowledgeReviewView.vue` (5個引用)
   - 多處硬編碼 `http://localhost:8100/api/v1/knowledge-candidates/...`

4. `src/views/KnowledgeReclassifyView.vue`
   - 第 335 行: `const RAG_API = 'http://localhost:8100/api/v1';`

5. `src/views/SuggestedIntentsView.vue`
   - 第 112 行: `const RAG_API = 'http://localhost:8100/api/v1';`

6. `src/views/CacheManagementView.vue` (3個引用)
   - 多處使用 `http://localhost:8100/api/v1/cache/...`

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

- ✅ 已完成: 6/12 (50%)
- ⚠️ 待處理: 6/12 (50%)
- 🎯 目標: 100%

**下一步**: 完成剩餘 6 個文件的更新
