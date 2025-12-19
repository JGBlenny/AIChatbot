# 部署步驟 - 2024-12-19 更新

## 📋 更新概述

本次更新包含以下主要功能：

### ✅ 核心功能
1. **Keywords 融入 Embedding** (方案 A)
   - 所有 embedding 生成路徑包含 keywords
   - 批量更新 1240 筆現有知識
   - 新增專用更新腳本

2. **前端 UI 優化**
   - 簡化測試頁面（移除冗餘信息）
   - 新增系統配置狀態顯示
   - 對外展示頁移除技術細節
   - 業者管理新增展示頁快速訪問
   - 知識匯入進度顯示增強

3. **後端服務增強**
   - 引入語義意圖匹配器
   - 移除模板變數自動處理
   - 優化知識檢索邏輯
   - 修復 optimization_method 缺失問題

4. **基礎設施改進**
   - Docker 依賴關係使用 health checks
   - 統一 RAG 檢索閾值配置
   - 標記廢棄的 SOP 意圖映射

---

## 🚀 部署步驟

### 環境說明

- **開發環境**: 使用 `docker-compose.yml`
- **生產環境**: 使用 `docker-compose.prod.yml` ⭐

以下步驟中，請根據環境替換命令：
- 開發環境: `docker-compose`
- 生產環境: `docker-compose -f docker-compose.prod.yml`

### 前置檢查

```bash
# 1. 確認當前位置
cd /path/to/AIChatbot  # 請替換為實際路徑

# 2. 檢查 Git 狀態
git status

# 3. 確認分支（應該在 main）
git branch

# 4. 拉取最新程式碼（如果是從遠端部署）
git pull origin main

# 5. 確認環境（開發或生產）
echo "當前環境: [開發/生產]"  # 請確認
```

### 步驟 1: 備份資料庫（重要！）⭐ **先備份再停止**

```bash
# 確保資料庫正在運行
# 開發環境:
docker-compose ps postgres

# 生產環境:
docker-compose -f docker-compose.prod.yml ps postgres

# 執行備份
# 開發環境:
docker exec aichatbot-postgres pg_dump \
  -U postgres \
  -d ai_knowledge_db \
  > backup_$(date +%Y%m%d_%H%M%S).sql

# 生產環境（相同命令）:
docker exec aichatbot-postgres pg_dump \
  -U postgres \
  -d ai_knowledge_db \
  > backup_$(date +%Y%m%d_%H%M%S).sql

echo "✅ 資料庫備份完成"
```

### 步驟 2: 執行資料庫遷移（添加 intents.embedding 欄位）⭐ **NEW**

**⚠️ 重要**: 在服務運行時執行，為語義意圖匹配做準備

```bash
# 確保 PostgreSQL 正在運行
# 開發環境:
docker-compose ps postgres

# 生產環境:
docker-compose -f docker-compose.prod.yml ps postgres

# 執行遷移腳本
docker exec -i aichatbot-postgres psql -U postgres -d ai_knowledge_db < database/migrations/add_intent_embedding.sql

# 驗證欄位已添加
docker exec aichatbot-postgres psql -U postgres -d ai_knowledge_db -c "\d intents"
# 應該看到 embedding | vector(1536) 欄位

echo "✅ 資料庫遷移完成"
```

### 步驟 3: 更新 Embeddings（重要！）⭐ **在服務運行時執行**

本步驟包含兩個子任務，**都需要在服務運行時執行**：

#### 3.1 更新知識庫 Embeddings（方案 A - Keywords）

**⚠️ 重要**: 此步驟會更新所有現有知識的 embeddings 以包含 keywords

```bash
# 確保必要服務正在運行（postgres + embedding-api）
# 開發環境:
docker-compose ps postgres embedding-api

# 生產環境:
docker-compose -f docker-compose.prod.yml ps postgres embedding-api

# 如果沒有運行，先啟動（僅需要這兩個服務）
# 開發環境:
docker-compose up -d postgres embedding-api

# 生產環境:
docker-compose -f docker-compose.prod.yml up -d postgres embedding-api

# 等待服務就緒
sleep 10

# 執行更新腳本（自動確認模式，推薦用於部署）
python3 scripts/update_embeddings_with_keywords.py --yes

# 監控進度日誌
tail -f /tmp/embedding_update.log
```

**預期結果**:
- 處理 1240 筆知識
- 成功率應為 100%
- 執行時間約 15-20 分鐘（取決於 embedding API 速度）

#### 3.2 生成意圖 Embeddings（方案 2 - 語義匹配）⭐ **NEW**

**⚠️ 新功能**: 此步驟為意圖生成向量表示，支持語義意圖匹配

```bash
# 確保步驟 2 的資料庫遷移已完成
# 確保必要服務正在運行（postgres + embedding-api）

# 生成所有意圖的 embeddings
python3 scripts/generate_intent_embeddings.py --yes
```

**預期結果**:
- 處理所有意圖（數量取決於系統中的意圖數量，通常 20-50 個）
- 成功率應為 100%
- 執行時間約 1-3 分鐘

**如何驗證**:
```bash
# 檢查意圖表的 embedding 欄位
docker exec aichatbot-postgres psql -U postgres -d ai_knowledge_db -c "SELECT id, name, (embedding IS NOT NULL) as has_embedding FROM intents ORDER BY id;"

# 應該看到所有意圖的 has_embedding 都是 't' (true)
```

### 步驟 4: 停止現有服務

```bash
# 停止所有容器
# 開發環境:
docker-compose down

# 生產環境:
docker-compose -f docker-compose.prod.yml down

# 可選：清理舊的容器和網路（謹慎使用）
# docker-compose down --volumes --remove-orphans
```

### 步驟 5: 重建 Docker 映像

```bash
# 開發環境:
# 重建所有服務映像
docker-compose build --no-cache

# 或只重建特定服務
docker-compose build knowledge-admin-api rag-orchestrator knowledge-admin-web

# 生產環境:
docker-compose -f docker-compose.prod.yml build --no-cache

# 或只重建特定服務
docker-compose -f docker-compose.prod.yml build knowledge-admin-api rag-orchestrator knowledge-admin-web
```

### 步驟 6: 啟動服務

```bash
# 開發環境:
docker-compose up -d

# 生產環境:
docker-compose -f docker-compose.prod.yml up -d

# 檢查服務狀態
# 開發環境:
docker-compose ps

# 生產環境:
docker-compose -f docker-compose.prod.yml ps

# 查看啟動日誌
# 開發環境:
docker-compose logs -f

# 生產環境:
docker-compose -f docker-compose.prod.yml logs -f
```

**驗證健康檢查**:
```bash
# 開發環境:
# PostgreSQL
docker-compose ps postgres | grep "healthy"

# Redis
docker-compose ps redis | grep "healthy"

# 確認依賴服務都已就緒
docker-compose ps

# 生產環境:
docker-compose -f docker-compose.prod.yml ps postgres | grep "healthy"
docker-compose -f docker-compose.prod.yml ps redis | grep "healthy"
docker-compose -f docker-compose.prod.yml ps
```

### 步驟 7: 驗證部署

#### 7.1 檢查容器狀態
```bash
# 所有容器應該處於 "Up" 狀態
# 開發環境:
docker-compose ps

# 生產環境:
docker-compose -f docker-compose.prod.yml ps

# 檢查容器日誌（無報錯）
# 開發環境:
docker-compose logs --tail=50 rag-orchestrator
docker-compose logs --tail=50 knowledge-admin-api
docker-compose logs --tail=50 knowledge-admin-web

# 生產環境:
docker-compose -f docker-compose.prod.yml logs --tail=50 rag-orchestrator
docker-compose -f docker-compose.prod.yml logs --tail=50 knowledge-admin-api
docker-compose -f docker-compose.prod.yml logs --tail=50 knowledge-admin-web
```

#### 7.2 測試 API 端點
```bash
# 測試 RAG Orchestrator
# 開發環境:
curl http://localhost:8100/health

# 生產環境（請替換為實際域名或 IP）:
curl http://your-production-domain:8100/health

# 測試 Knowledge Admin API
# 開發環境:
curl http://localhost:8086/health

# 生產環境:
curl http://your-production-domain:8086/health

# 測試前端（應返回 HTML）
# 開發環境:
curl http://localhost:8087/

# 生產環境:
curl http://your-production-domain:8087/
```

#### 7.3 功能驗證

**測試 Keywords Embedding**:
1. 訪問 http://localhost:8087/knowledge
2. 創建測試知識（ID 應為新 ID）
   - 問題摘要：測試 keywords embedding
   - 關鍵字：測試,embedding,功能驗證
   - 答案：這是測試 keywords 是否正確融入 embedding
3. 檢查資料庫確認 embedding 已生成

**測試聊天介面**:
1. 訪問 http://localhost:8087/chat-test
2. 選擇業者（例如 VENDOR_A）
3. 驗證新 UI 功能：
   - ✅ 業者代碼可點擊跳轉展示頁
   - ✅ 系統配置狀態顯示（所有處理路徑和 LLM 策略）
   - ✅ 當前選項有藍色高亮
   - ✅ 沒有訂閱方案、狀態、業務範圍、快速測試按鈕

**測試展示頁**:
1. 訪問 http://localhost:8087/VENDOR_A/chat
2. 驗證：
   - ✅ 沒有顯示信心度百分比
   - ✅ 只顯示意圖標籤
   - ✅ 介面簡潔專業

**測試業者管理**:
1. 訪問 http://localhost:8087/vendors
2. 驗證：
   - ✅ 有「展示頁」列
   - ✅ 紫色「🔗 展示」按鈕
   - ✅ 點擊可跳轉到展示頁

**測試知識匯入進度**:
1. 訪問 http://localhost:8087/knowledge-import
2. 上傳 Excel 文件
3. 驗證：
   - ✅ 大進度條（32px 高度）
   - ✅ 漸層藍色填充
   - ✅ 脈衝動畫
   - ✅ 階段標籤顯示
   - ✅ 百分比和數量雙重顯示

#### 7.4 語義匹配測試
```bash
# 測試語義意圖匹配
# 開發環境:
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "租金幾號要繳？",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "test_semantic"
  }'

# 生產環境:
curl -X POST http://your-production-domain:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "租金幾號要繳？",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "test_semantic"
  }'
```

---

## 🔧 故障排除

### 問題 1: Embedding 更新失敗

**症狀**: 腳本執行中斷或成功率 < 100%

**解決方法**:
```bash
# 檢查 embedding API 是否正常
docker-compose logs embedding-api

# 確認資料庫連接
docker-compose exec postgres psql -U postgres -d ai_knowledge_db -c "SELECT COUNT(*) FROM ai_knowledge;"

# 重新執行更新腳本（知識庫）
python3 scripts/update_embeddings_with_keywords.py --yes

# 重新執行更新腳本（意圖）
python3 scripts/generate_intent_embeddings.py --yes
```

### 問題 1.5: 意圖 Embedding 欄位不存在

**症狀**: `generate_intent_embeddings.py` 報錯 "column 'embedding' does not exist"

**解決方法**:
```bash
# 確認是否執行了遷移腳本
docker exec aichatbot-postgres psql -U postgres -d ai_knowledge_db -c "\d intents"

# 如果沒有 embedding 欄位，執行遷移
docker exec -i aichatbot-postgres psql -U postgres -d ai_knowledge_db < database/migrations/add_intent_embedding.sql

# 再次執行生成腳本
python3 scripts/generate_intent_embeddings.py --yes
```

### 問題 2: 容器無法啟動

**症狀**: `docker-compose ps` 顯示 "Exited" 狀態

**解決方法**:
```bash
# 查看詳細錯誤日誌
docker-compose logs [service_name]

# 常見原因：
# 1. 依賴服務未就緒 → 檢查 postgres, redis health
# 2. 端口被占用 → 使用 lsof -i :8100 檢查
# 3. 環境變數錯誤 → 檢查 .env 文件
```

### 問題 3: Health Check 失敗

**症狀**: 容器卡在 "starting" 狀態

**解決方法**:
```bash
# PostgreSQL health check
docker-compose exec postgres pg_isready -U postgres

# Redis health check
docker-compose exec redis redis-cli ping

# 如果持續失敗，調整 docker-compose.yml 中的 health check 間隔
```

### 問題 4: 前端無法訪問

**症狀**: 訪問 http://localhost:8087 顯示 502 或無法連接

**解決方法**:
```bash
# 檢查前端容器日誌
docker-compose logs knowledge-admin-web

# 檢查 Nginx 配置
docker-compose exec knowledge-admin-web cat /etc/nginx/conf.d/default.conf

# 重啟前端服務
docker-compose restart knowledge-admin-web
```

---

## 📊 環境變數配置

本次更新涉及的關鍵環境變數：

```bash
# RAG 檢索閾值（已統一）
KB_SIMILARITY_THRESHOLD=0.55        # 統一檢索閾值（含語義匹配）
HIGH_QUALITY_THRESHOLD=0.8          # 高質量知識過濾閾值
SOP_SIMILARITY_THRESHOLD=0.75       # SOP 檢索閾值

# ⚠️ 已廢棄（保留兼容性）
FALLBACK_SIMILARITY_THRESHOLD=0.55  # 已移除獨立 RAG fallback
RAG_SIMILARITY_THRESHOLD=0.6        # 待移除

# LLM 優化策略閾值
PERFECT_MATCH_THRESHOLD=0.90
SYNTHESIS_THRESHOLD=0.80
FAST_PATH_THRESHOLD=0.75

# 功能開關
ENABLE_ANSWER_SYNTHESIS=true
```

---

## 📝 回滾步驟

如果部署後發現問題，可按以下步驟回滾：

### 1. 停止服務
```bash
docker-compose down
```

### 2. 回滾代碼
```bash
# 查看提交歷史
git log --oneline -10

# 回滾到上一個穩定版本（根據實際情況調整）
git reset --hard <commit-hash>
```

### 3. 恢復資料庫備份
```bash
# 啟動資料庫
docker-compose up -d postgres

# 等待資料庫就緒
sleep 5

# 恢復備份（替換為實際備份文件名）
docker exec -i aichatbot-postgres psql -U postgres -d ai_knowledge_db < backup_YYYYMMDD_HHMMSS.sql
```

### 4. 重啟服務
```bash
docker-compose up -d
```

---

## ✅ 部署檢查清單

### 部署前準備
- [ ] 已備份資料庫
- [ ] 已通知用戶維護時間

### Embedding 更新
- [ ] 已執行資料庫遷移（intents.embedding 欄位）⭐ **NEW**
- [ ] 已執行知識庫 embedding 更新腳本（成功率 100%）
- [ ] 已執行意圖 embedding 生成腳本（成功率 100%）⭐ **NEW**
- [ ] 已驗證意圖 embeddings 生成成功（所有意圖都有 embedding）⭐ **NEW**

### 服務狀態
- [ ] 所有容器處於 "healthy" 或 "running" 狀態
- [ ] PostgreSQL health check 通過
- [ ] Redis health check 通過
- [ ] API 端點測試通過
- [ ] 前端可正常訪問

### 功能驗證
- [ ] Keywords embedding 功能驗證通過
- [ ] 聊天測試頁 UI 優化驗證通過
- [ ] 展示頁簡化驗證通過
- [ ] 業者管理展示頁連結驗證通過
- [ ] 知識匯入進度顯示驗證通過
- [ ] 語義意圖匹配測試通過⭐ **NEW**
- [ ] 無錯誤日誌

---

## 📅 部署記錄

**部署日期**: 2024-12-19
**執行者**: [填寫執行者]
**環境**: [Development / Staging / Production]

**變更摘要**:
- 4 個新提交（keywords + UI 優化 + 文檔 + 配置）
- 更新 1240 筆 embeddings
- 新增語義意圖匹配器
- 優化 Docker 依賴管理

**部署結果**:
- [ ] 成功
- [ ] 部分成功（說明原因）
- [ ] 失敗（說明原因）

**備註**:


---

## 🔗 相關文檔

- [更新日誌](./CHANGELOG_2024-12-19_KEYWORDS_UI_IMPROVEMENTS.md)
- [清理報告](./CLEANUP_REPORT_2024-12-19.md)
- [開發環境部署指南](./guides/DEVELOPMENT_DEPLOYMENT.md)
- [生產環境部署指南](./guides/PRODUCTION_DEPLOYMENT.md)
- [知識匯入匯出指南](./guides/KNOWLEDGE_IMPORT_EXPORT_GUIDE.md)

---

**文檔版本**: 1.0
**最後更新**: 2024-12-19
**維護者**: Claude Code
