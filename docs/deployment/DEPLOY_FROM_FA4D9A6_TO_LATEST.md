# 從 fa4d9a6 部署到最新版本 (e3a6ff9) - 完整指南

**部署日期**: 2026-01-28
**源版本**: fa4d9a6 (Migration 追蹤系統)
**目標版本**: e3a6ff9 (Reranker + 智能檢索)
**涉及 Commits**: 5 個重大更新
**影響範圍**: SOP 系統、檢索引擎、知識庫、前端介面
**預估停機時間**: ~5 分鐘（完整重建）
**預估部署時間**: ~30-40 分鐘（含測試）

---

## 📋 更新概要

### 涉及的 5 個 Commits

1. **dc61ff5** - SOP 流程配置嚴格限制與專案整理
2. **18d9484** - SOP 流程配置完整功能實施（補充）
3. **78e21f6** - Primary Embedding 修復，大幅提升 SOP 檢索準確度
4. **0ca9a16** - SOP 功能完整文檔與相關服務實施
5. **e3a6ff9** - Reranker 二階段檢索與智能檢索系統完整實施 ⭐

###重大變更統計

```
98 files changed
+32,959 lines added
-333 lines removed
```

### 核心功能更新

| 功能模組 | 變更內容 | 影響等級 |
|---------|---------|---------|
| **Reranker 二階段檢索** | Knowledge 準確率 25%→75% (+200%) | 🔴 Critical |
| **智能檢索系統** | SOP 與知識庫並行檢索 + 分數比較 | 🔴 Critical |
| **SOP 流程配置** | 7 種有效組合 + 嚴格驗證 | 🟡 Major |
| **Primary Embedding** | 涵蓋率 66.7%→92.6% (+25.9%) | 🟡 Major |
| **SOP Orchestrator** | 完整的 SOP 編排系統 | 🟡 Major |
| **觸發模式系統** | immediate/manual/none 三種模式 | 🟢 Minor |
| **前端優化** | 新增 Rerank 分數，移除混亂欄位 | 🟢 Minor |

---

## ⚠️ 部署前必讀

### 重要風險提醒

1. **🔴 需要完整重建**：新增 `sentence-transformers` 和 `torch` 依賴（~2GB）
2. **🔴 資料庫遷移**：4 個新的 migration 文件
3. **🟡 首次啟動慢**：Reranker 模型需下載（~500MB，2-3 分鐘）
4. **🟡 需重新生成 Embeddings**：56 個 SOP 需重新生成（非必須，但建議）
5. **🟢 前端需重建**：Vue 文件有大量更新

### 系統需求檢查

```bash
# 磁碟空間（至少需要 8GB 可用空間）
df -h /
# 需要 ≥ 8GB 可用空間（依賴 2GB + 模型 500MB + 餘裕 5.5GB）

# Docker 版本
docker --version  # 應該 >= 20.10
docker-compose --version  # 應該 >= 1.29

# Python 版本（容器內）
docker exec aichatbot-rag-orchestrator python3 --version  # 應該 >= 3.9

# 記憶體
free -h  # 建議 ≥ 8GB 總記憶體
```

### 建議部署時間

- 🌙 **深夜時段**（凌晨 2:00-4:00）- 最佳
- 📅 **週末或假日** - 次佳
- ⚠️ **避免尖峰時段**（上午 9:00-下午 6:00）

---

## 🚀 完整部署流程

### 階段 1：部署前準備（5-10 分鐘）

#### 步驟 1.1：通知用戶

```bash
# 發送維護通知（提前 30 分鐘）
cat <<EOF
【系統維護通知】
維護時間：$(date -d '+30 minutes' '+%Y-%m-%d %H:%M')
預計時長：30-40 分鐘
維護內容：檢索系統重大升級（準確率提升 3 倍）
影響範圍：所有聊天機器人服務
備用聯絡：[緊急聯絡方式]
EOF
```

#### 步驟 1.2：檢查當前狀態

```bash
cd /path/to/AIChatbot

# 確認當前版本
git log --oneline -1
# 應該顯示：fa4d9a6 docs: 更新部署文檔以整合 Migration 追蹤系統

# 確認服務狀態
docker-compose ps
# 所有服務應該是 Up

# 確認分支
git branch
# 應該在 main 分支

# 檢查工作區
git status
# 應該是 clean
```

#### 步驟 1.3：備份資料庫

⚠️ **極其重要！本次更新有 4 個 migration，必須備份！**

```bash
# 創建備份目錄
mkdir -p database/backups/2026-01-28_major_update

# 備份資料庫
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > \
  database/backups/2026-01-28_major_update/before_update_$(date +%Y%m%d_%H%M%S).sql

# 驗證備份文件大小（應該 > 1MB）
ls -lh database/backups/2026-01-28_major_update/

# 備份 .env 文件
cp .env .env.backup_$(date +%Y%m%d_%H%M%S)
```

#### 步驟 1.4：檢查磁碟空間

```bash
# 檢查可用空間
df -h /
# 需要 ≥ 8GB 可用空間

# 如果空間不足，清理 Docker
docker system prune -a --volumes  # ⚠️ 會刪除未使用的容器和映像
```

---

### 階段 2：代碼更新（2-3 分鐘）

#### 步驟 2.1：拉取最新代碼

```bash
# 拉取最新代碼
git pull origin main

# 確認更新成功
git log --oneline -5
# 應該看到：
# e3a6ff9 feat: Reranker 二階段檢索與智能檢索系統完整實施
# 0ca9a16 docs: SOP 功能完整文檔與相關服務實施
# 78e21f6 feat: Primary Embedding 修復，大幅提升 SOP 檢索準確度
# 18d9484 feat: SOP 流程配置完整功能實施（補充）
# dc61ff5 feat: SOP 流程配置嚴格限制與專案整理
```

#### 步驟 2.2：查看變更文件

```bash
# 查看本次更新變更的關鍵文件
git diff --name-status fa4d9a6..HEAD | grep -E "(requirements|migration|docker-compose)"
```

---

### 階段 3：資料庫遷移（5-8 分鐘）

⚠️ **必須在停止服務前執行 migration！**

#### 步驟 3.1：預覽待執行的 Migration

```bash
./database/run_migrations.sh docker-compose.yml --dry-run
```

**預期輸出**：
```
⚠️  發現 4 個待執行的 migration:
  1. add_form_sessions_metadata.sql
  2. add_sop_next_action_fields.sql
  3. add_trigger_mode_to_knowledge_base.sql
  4. insert_maintenance_sop_examples.sql
```

#### 步驟 3.2：執行 Migration

```bash
# 自動執行（含自動備份）
./database/run_migrations.sh docker-compose.yml

# 如果出現錯誤，立即停止並查看日誌
ls -lt /tmp/migration_*.log | head -1
```

**執行預計時間**：
- add_form_sessions_metadata.sql: ~5 秒
- add_sop_next_action_fields.sql: ~10 秒（較多欄位）
- add_trigger_mode_to_knowledge_base.sql: ~10 秒
- insert_maintenance_sop_examples.sql: ~20 秒（插入範例數據）
- **總計**: ~45 秒

#### 步驟 3.3：驗證 Migration 執行結果

```bash
# 驗證所有 migration 已執行
./database/run_migrations.sh docker-compose.yml --dry-run
# 應該顯示：✓ 所有 migration 都已執行，無需執行

# 手動驗證關鍵欄位
docker exec -it aichatbot-postgres psql -U aichatbot aichatbot_admin -c "\d platform_sop_templates" | grep -E "(trigger_mode|next_action)"
docker exec -it aichatbot-postgres psql -U aichatbot aichatbot_admin -c "\d knowledge_base" | grep trigger_mode
```

**預期輸出**：
```
trigger_mode          | character varying(20) | DEFAULT NULL
next_action           | character varying(50)
next_form_id          | character varying(100)
next_api_endpoint_id  | integer
immediate_prompt      | text
```

---

### 階段 4：停止服務（30 秒）

```bash
# 停止所有服務
docker-compose down

# 確認服務已停止
docker-compose ps
# 應該是空的或顯示 "No containers"
```

---

### 階段 5：重新構建映像（5-8 分鐘）

⚠️ **必須使用 --no-cache 確保安裝新依賴！**

```bash
# 重新構建（需要 5-8 分鐘）
docker-compose build --no-cache rag-orchestrator knowledge-admin-api

# 監控構建進度
# 會看到：
# Step X/Y : RUN pip install -r requirements.txt
# Collecting sentence-transformers==5.2.2...
# Collecting torch==2.5.0...
# Successfully installed sentence-transformers-5.2.2 torch-2.5.0
```

**構建檢查點**：
- ✅ `Collecting sentence-transformers==5.2.2`
- ✅ `Collecting torch==2.5.0`
- ✅ `Successfully installed sentence-transformers-5.2.2 torch-2.5.0`

---

### 階段 6：啟動服務（2-3 分鐘）

```bash
# 啟動所有服務
docker-compose up -d

# 查看啟動日誌（重要！）
docker-compose logs -f rag-orchestrator
```

**關鍵日誌檢查點**：
```
✅ [Reranker] 正在初始化...
✅ [Reranker] 下載模型: BAAI/bge-reranker-base
✅ Downloading: 100%|██████████| 500MB/500MB
✅ [Reranker] 模型載入完成
✅ [智能檢索] 系統初始化完成
✅ Application startup complete
```

**首次啟動預期時間**：
- 模型下載：2-3 分鐘（僅首次）
- 服務啟動：30 秒
- **總計**: 2.5-3.5 分鐘

**如果模型下載失敗**：
```bash
# 檢查網路連線
docker exec aichatbot-rag-orchestrator curl -I https://huggingface.co

# 使用鏡像站（中國大陸用戶）
docker-compose down
# 在 docker-compose.yml 中添加：
# environment:
#   HF_ENDPOINT: https://hf-mirror.com
docker-compose up -d
```

---

### 階段 7：前端重建（2-3 分鐘）

```bash
cd knowledge-admin/frontend

# 安裝依賴（如果 package.json 有變更）
npm install

# 構建前端
npm run build

# 返回根目錄
cd ../..

# 重啟前端服務
docker-compose restart knowledge-admin-web

# 確認前端服務狀態
docker-compose ps knowledge-admin-web
```

---

### 階段 8：驗證測試（10-15 分鐘）

#### 步驟 8.1：服務狀態檢查

```bash
# 檢查所有服務狀態
docker-compose ps
```

**預期結果**：
```
NAME                          STATUS
aichatbot-postgres            Up
aichatbot-redis               Up
aichatbot-embedding-api       Up
aichatbot-rag-orchestrator    Up
aichatbot-knowledge-admin     Up
aichatbot-knowledge-web       Up
```

所有服務都應該是 `Up` 狀態，沒有 `Restarting`。

#### 步驟 8.2：日誌檢查

```bash
# 查看各服務日誌，確認無錯誤
docker-compose logs --tail=100 rag-orchestrator | grep -E "(Error|錯誤|Exception|Traceback)"
docker-compose logs --tail=50 knowledge-admin-api | grep -E "(Error|錯誤|Exception)"
docker-compose logs --tail=50 knowledge-admin-web | grep -E "(error|Error)"
```

**應該看到**：沒有輸出（表示無錯誤）

#### 步驟 8.3：Reranker 功能測試

```bash
# 執行自動化測試（3 個場景）
/tmp/test_smart_retrieval.sh
```

**預期輸出**：
```
==================================
智能檢索系統 - 完整測試
==================================

📝 測試: SOP 顯著更高
   問題: 租金怎麼繳
   處理路徑: sop_orchestrator
   SOP 分數: 0.967 (1 個候選)
   知識庫分數: 0.616 (0 個候選)
   決策類型: sop_significantly_higher

📝 測試: 知識庫顯著更高
   問題: 押金是多少
   處理路徑: knowledge
   SOP 分數: 0.000 (0 個候選)
   知識庫分數: 0.842 (2 個候選)
   決策類型: knowledge_significantly_higher

📝 測試: 分數接近且 SOP 有動作
   問題: 我想要報修
   處理路徑: sop_orchestrator
   SOP 分數: 0.929 (1 個候選)
   知識庫分數: 0.960 (2 個候選)
   決策類型: close_scores_sop_has_action

==================================
✅ 測試完成！
==================================
```

#### 步驟 8.4：手動功能測試

1. **訪問前端**：http://your-domain:8000

2. **登入管理後台**

3. **測試基本聊天功能**：
   - 問題：「租金怎麼繳」
   - 預期：返回 SOP 標準流程答案
   - 檢查：處理路徑顯示「SOP 標準流程」

4. **檢查 Debug 資訊**：
   - 問題：「我想要報修」
   - 展開「查看處理流程詳情」
   - 確認：
     - ✅ SOP 候選顯示 1 個
     - ✅ 知識庫候選顯示 2 個
     - ✅ **Rerank 分數**欄位有值
     - ✅ **不顯示**：意圖加成、意圖相似度、Scope權重
     - ✅ 比較元數據完整

5. **測試 SOP 管理介面**：
   - 進入「Vendor SOP 管理」
   - 檢查：觸發模式下拉選單有 3 個選項
   - 檢查：後續動作下拉選單根據觸發模式動態變化

#### 步驟 8.5：效能測試

```bash
# 測試響應時間（10 次請求平均）
for i in {1..10}; do
  time curl -s -X POST http://localhost:8100/api/v1/message \
    -H "Content-Type: application/json" \
    -d '{"message": "租金怎麼繳", "vendor_id": 1, "user_role": "tenant", "user_id": "test"}' \
    > /dev/null
done
```

**預期響應時間**：
- 第一次請求：500-800ms（模型初始化）
- 後續請求：200-400ms（正常範圍）
- Reranker 開銷：+50-100ms（可接受）

#### 步驟 8.6：資源使用檢查

```bash
# 查看資源使用
docker stats --no-stream

# 重點檢查 rag-orchestrator
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep rag-orchestrator
```

**預期資源使用**：
- CPU: 5-20%（閒置時）
- 記憶體: 2-4GB（正常範圍，包含模型）
- ⚠️ 如果記憶體 > 6GB，可能需要調整

---

### 階段 9：資料重新生成（可選，15-20 分鐘）

⚠️ **可選步驟，但強烈建議執行！**

#### 步驟 9.1：重新生成 SOP Embeddings

```bash
# 重新生成所有 SOP embeddings
python3 scripts/regenerate_sop_embeddings.py
```

**預期輸出**：
```
====================================================================================================
📊 重新生成完成
====================================================================================================
✅ 成功: 56/56
❌ 失敗: 0/56
成功率: 100.0%

執行時間: 2分35秒
```

**為什麼建議重新生成？**
- Primary Embedding 修復（commit 78e21f6）改變了生成邏輯
- 涵蓋率可提升至 92.6%（之前 66.7%）
- 關鍵問題（如「垃圾要怎麼丟」）將正確匹配

#### 步驟 9.2：驗證 Embeddings 更新

```bash
# 測試關鍵問題
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "垃圾要怎麼丟",
    "vendor_id": 1,
    "user_role": "tenant",
    "user_id": "test",
    "include_debug_info": true
  }' | python3 -m json.tool | grep -A 5 "sop_candidates"
```

**預期結果**：
- 第一名：「垃圾收取規範」（分數 > 0.55）
- 而不是：「馬桶堵塞」

---

### 階段 10：部署完成與監控（持續 1 週）

#### 步驟 10.1：發送完成通知

```bash
cat <<EOF
【系統維護完成】
完成時間：$(date '+%Y-%m-%d %H:%M')
維護時長：[實際時長] 分鐘
更新內容：
  ✅ Reranker 二階段檢索（準確率提升 3 倍）
  ✅ 智能檢索系統（SOP + 知識庫並行決策）
  ✅ SOP 流程配置嚴格限制
  ✅ Primary Embedding 修復
系統狀態：正常運行
感謝您的耐心等待！
EOF
```

#### 步驟 10.2：設置監控（1 週）

**監控腳本**（建議設置 cron job）：

```bash
#!/bin/bash
# 文件：/path/to/monitor_deployment.sh

echo "=== 部署監控報告 - $(date) ==="
echo ""

echo "1. 服務狀態："
docker-compose ps | grep -E "(Up|Restarting|Down)"
echo ""

echo "2. 過去 1 小時錯誤數："
docker-compose logs rag-orchestrator --since 1h | grep -c "Error"
echo ""

echo "3. 資源使用："
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep rag-orchestrator
echo ""

echo "4. 最近 10 次請求響應時間："
docker-compose logs rag-orchestrator --since 1h | grep "Processing time" | tail -10
echo ""

# 保存到日誌文件
# >> /var/log/deployment_monitor.log
```

**設置 cron job**：
```bash
# 編輯 crontab
crontab -e

# 添加（每小時執行一次，持續 1 週）
0 * * * * /path/to/monitor_deployment.sh >> /var/log/deployment_monitor.log 2>&1
```

#### 步驟 10.3：監控重點指標（1 週）

**Day 1-2（關鍵期）- 每小時檢查**：
- ✅ 服務可用性 = 100%
- ✅ Knowledge 準確率 ≥ 75%
- ✅ SOP 準確率 ≥ 90%
- ✅ 平均響應時間 < 500ms
- ✅ 錯誤率 < 0.1%
- ✅ CPU 使用 < 80%
- ✅ 記憶體使用 < 4GB

**Day 3-7（觀察期）- 每天檢查**：
- ✅ 系統穩定運行（無重啟）
- ✅ 用戶反饋正面
- ✅ 無異常日誌
- ✅ 決策類型分佈合理

---

## 🔄 回滾計畫

### 回滾觸發條件

如果出現以下情況，**立即執行回滾**：

1. ❌ 服務不斷重啟（超過 3 次/小時）
2. ❌ Knowledge 準確率 < 50%（低於修復前）
3. ❌ 平均響應時間 > 1 秒
4. ❌ 大量錯誤日誌（> 10 條/分鐘）
5. ❌ CPU 或記憶體使用率 > 90%
6. ❌ 用戶大量投訴

### 回滾步驟（預計 15 分鐘）

#### 步驟 1：停止服務

```bash
docker-compose down
```

#### 步驟 2：回滾代碼

```bash
# 回滾到 fa4d9a6
git checkout fa4d9a6

# 確認回滾
git log --oneline -1
# 應該顯示：fa4d9a6 docs: 更新部署文檔以整合 Migration 追蹤系統
```

#### 步驟 3：恢復資料庫

```bash
# 找到備份文件
ls -lt database/backups/2026-01-28_major_update/

# 恢復資料庫
docker-compose up -d postgres  # 只啟動 postgres
sleep 10  # 等待 postgres 啟動

docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
  database/backups/2026-01-28_major_update/before_update_*.sql

# 驗證恢復
docker exec -it aichatbot-postgres psql -U aichatbot aichatbot_admin -c "\d platform_sop_templates" | grep -c "trigger_mode"
# 應該輸出：0（表示欄位不存在，恢復成功）
```

#### 步驟 4：重新構建並啟動

```bash
# 重新構建（使用舊代碼）
docker-compose build --no-cache

# 啟動服務
docker-compose up -d

# 驗證服務狀態
docker-compose ps
```

#### 步驟 5：驗證回滾成功

```bash
# 測試基本功能
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{"message": "租金怎麼繳", "vendor_id": 1, "user_role": "tenant", "user_id": "test"}'

# 確認服務正常
docker-compose logs --tail=50 rag-orchestrator | grep -E "(Error|錯誤)"
# 應該沒有錯誤
```

#### 步驟 6：通知用戶

```bash
cat <<EOF
【緊急回滾通知】
回滾時間：$(date '+%Y-%m-%d %H:%M')
回滾原因：[具體原因]
當前版本：fa4d9a6（穩定版本）
系統狀態：已恢復正常
後續計畫：將分析問題原因，擇期重新部署
抱歉造成不便！
EOF
```

---

## 📊 部署檢查清單

### 部署前（Checklist）

- [ ] 代碼審查完成（98 個文件變更）
- [ ] 單元測試通過
- [ ] 資料庫備份完成（2 份：自動 + 手動）
- [ ] .env 文件備份完成
- [ ] 磁碟空間充足（≥8GB）
- [ ] 依賴版本確認（requirements.txt）
- [ ] 回滾計畫就緒並測試
- [ ] 用戶通知已發送（提前 30 分鐘）
- [ ] 緊急聯絡方式準備
- [ ] 團隊待命（至少 1 人）

### 部署中（Checklist）

- [ ] 代碼拉取成功（fa4d9a6 → e3a6ff9）
- [ ] Migration 預覽執行（4 個待執行）
- [ ] Migration 執行成功（4/4 通過）
- [ ] Migration 驗證通過（欄位檢查）
- [ ] 服務停止成功
- [ ] Docker 構建成功（無錯誤）
- [ ] 依賴安裝成功（sentence-transformers, torch）
- [ ] 服務啟動成功（所有服務 Up）
- [ ] Reranker 模型下載成功（~500MB）
- [ ] 前端重建成功（dist 目錄更新）

### 部署後（Checklist）

- [ ] 所有服務運行正常（docker-compose ps）
- [ ] 日誌無錯誤訊息（Error, Exception, Traceback）
- [ ] Reranker 功能測試通過（3/3 場景）
- [ ] 手動功能測試通過（5 個檢查點）
- [ ] 前端驗證通過（Debug 資訊完整）
- [ ] 效能測試通過（響應時間 < 500ms）
- [ ] 資源使用正常（CPU <80%, 記憶體 <4GB）
- [ ] Embeddings 重新生成（可選，56/56 成功）
- [ ] 完成通知已發送
- [ ] 監控系統啟動（cron job 設置）

### 1 週後複查（Checklist）

- [ ] Knowledge 準確率達標（≥75%）
- [ ] SOP 準確率達標（≥90%）
- [ ] 系統穩定運行（無重啟）
- [ ] 無用戶投訴
- [ ] 效能指標正常
- [ ] 決策類型分佈合理
- [ ] 考慮調整閾值（如需要）
- [ ] 文檔更新完整
- [ ] 團隊培訓完成

---

## 📚 相關文檔

### 完整技術文檔

- **[DEPLOYMENT_2026-01-28.md](DEPLOYMENT_2026-01-28.md)** - 單個功能詳細部署
- **[SMART_RETRIEVAL_IMPLEMENTATION.md](../SMART_RETRIEVAL_IMPLEMENTATION.md)** - 智能檢索實施報告
- **[SMART_RETRIEVAL_QUICK_REF.md](../SMART_RETRIEVAL_QUICK_REF.md)** - 快速參考指南
- **[RERANKER_FEATURE.md](../features/RERANKER_FEATURE.md)** - Reranker 功能文檔
- **[CHANGELOG_2026-01-28.md](../CHANGELOG_2026-01-28.md)** - 完整更新日誌
- **[PRIMARY_EMBEDDING_FIX.md](../features/PRIMARY_EMBEDDING_FIX.md)** - Embedding 修復文檔
- **[SOP_FLOW_STRICT_VALIDATION_2026-01-26.md](../features/SOP_FLOW_STRICT_VALIDATION_2026-01-26.md)** - SOP 配置驗證

### Commit 詳細說明

1. **dc61ff5** - [SOP_FLOW_STRICT_VALIDATION_2026-01-26.md](../features/SOP_FLOW_STRICT_VALIDATION_2026-01-26.md)
2. **18d9484** - [SOP_NEXT_ACTION_IMPLEMENTATION.md](../development/SOP_NEXT_ACTION_IMPLEMENTATION.md)
3. **78e21f6** - [PRIMARY_EMBEDDING_FIX.md](../features/PRIMARY_EMBEDDING_FIX.md)
4. **0ca9a16** - 文檔完善（無功能變更）
5. **e3a6ff9** - [RERANKER_FEATURE.md](../features/RERANKER_FEATURE.md) + [SMART_RETRIEVAL_IMPLEMENTATION.md](../SMART_RETRIEVAL_IMPLEMENTATION.md)

### 測試與驗證

- **[/tmp/test_smart_retrieval.sh](/tmp/test_smart_retrieval.sh)** - 自動化測試腳本
- **[test_fix_verification.py](scripts/testing/archive/2026-01-26/test_fix_verification.py)** - Embedding 修復驗證
- **[test_threshold_evaluation.py](scripts/testing/archive/2026-01-26/test_threshold_evaluation.py)** - 閾值評估

---

## 🎯 成功指標

### 技術指標

| 指標 | Before (fa4d9a6) | After (e3a6ff9) | 目標 | 狀態 |
|------|------------------|-----------------|------|------|
| Knowledge 準確率 | 25% | **75%** | ≥75% | ⏳ 監控中 |
| SOP 準確率 | 66.7% | **92.6%** | ≥90% | ⏳ 監控中 |
| 平均響應時間 | 200ms | **250-350ms** | <500ms | ⏳ 監控中 |
| 服務可用性 | 99.9% | - | ≥99.9% | ⏳ 監控中 |
| 錯誤率 | <0.1% | - | <0.1% | ⏳ 監控中 |

### 業務指標

- ⏳ 用戶滿意度提升（待收集）
- ⏳ 問題解決率提升（待統計）
- ⏳ 客服工作量減少（待評估）

---

## 👥 參與人員

- **部署實施**: [您的名字]
- **技術支援**: Claude Code
- **測試人員**: [測試人員名字]
- **批准人員**: [管理者名字]

---

## 📝 部署記錄

### 部署執行記錄

**實際部署時間**: ___:___ - ___:___
**實際停機時間**: ___ 分鐘
**遇到的問題**: [記錄實際遇到的問題]
**解決方案**: [記錄實際採取的解決方案]
**最終狀態**: [ ] 成功 [ ] 部分成功 [ ] 失敗（已回滾）

### 部署後觀察

**Day 1**: [記錄觀察結果]
**Day 2**: [記錄觀察結果]
**Day 7**: [記錄最終評估]

---

**部署文檔版本**: 1.0
**最後更新**: 2026-01-28
**文檔狀態**: ✅ 可用於生產部署

---

## ⚡ 快速參考

### 快速命令索引

```bash
# 備份
docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > backup_$(date +%Y%m%d_%H%M%S).sql

# 更新代碼
git pull origin main && git log --oneline -5

# Migration
./database/run_migrations.sh docker-compose.yml --dry-run
./database/run_migrations.sh docker-compose.yml

# 重建
docker-compose down
docker-compose build --no-cache rag-orchestrator knowledge-admin-api
docker-compose up -d

# 測試
/tmp/test_smart_retrieval.sh
docker-compose ps
docker-compose logs -f rag-orchestrator

# 監控
docker stats --no-stream
docker-compose logs --tail=100 rag-orchestrator | grep -E "(Error|錯誤)"

# 回滾
git checkout fa4d9a6
docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < backup_*.sql
docker-compose build --no-cache && docker-compose up -d
```

---

**祝部署順利！🚀**
