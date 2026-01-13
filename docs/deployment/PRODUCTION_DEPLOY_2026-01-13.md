# 🚀 統一檢索路徑 - 生產環境部署指南

**功能名稱**：統一檢索路徑（選項 A）
**Git Commit**：cbf4c4f
**部署日期**：2026-01-13
**預計停機時間**：< 2 分鐘

---

## 📌 本次更新內容

### 核心改進

**解決問題**：修復知識 1262 等高相似度知識因意圖不匹配而無法檢索的問題

**技術方案**：
1. ✅ 統一所有查詢使用 `vendor_knowledge_retriever`（包括 unclear）
2. ✅ 刪除 `_handle_unclear_with_rag_fallback()` 特殊路徑
3. ✅ 意圖從「必要條件」改為「排序加成」
4. ✅ 只用向量相似度過濾（>= 0.55），不依賴意圖

### 代碼變更

| 文件 | 變更 |
|------|------|
| `rag-orchestrator/services/vendor_knowledge_retriever.py` | +34 行 |
| `rag-orchestrator/routers/chat.py` | -243 行 |
| **總計** | **-209 行**（代碼簡化） |

### 影響範圍

- ✅ **所有查詢**：unclear、明確意圖均使用統一邏輯
- ✅ **檢索準確度**：提升（消除意圖依賴區間）
- ✅ **代碼維護性**：提升（刪除複雜分支）
- ✅ **向後兼容**：完全兼容（API 無變更）

---

## ⚠️ 部署前檢查

### 必要條件

- [ ] 已閱讀完整實施報告：`docs/implementation/FINAL_2026-01-13.md`
- [ ] 確認生產服務器有足夠磁碟空間（至少 2GB）
- [ ] 確認有資料庫備份權限
- [ ] 確認可以短暫停機（< 2 分鐘）

### 風險評估

| 風險項 | 風險等級 | 緩解措施 |
|--------|---------|---------|
| 資料庫變更 | 🟢 無 | 本次無資料庫變更 |
| 服務不可用 | 🟡 低 | 預計 < 2 分鐘，備有回滾方案 |
| 查詢結果變化 | 🟢 正面 | 提升檢索準確度 |
| 向後兼容性 | 🟢 完全 | API 無變更 |

---

## 📋 部署步驟

### 步驟 1：SSH 登入生產服務器

```bash
ssh user@your-production-server
cd /path/to/AIChatbot
```

### 步驟 2：檢查當前狀態

```bash
# 確認當前分支和 commit
git branch
git log --oneline -3

# 檢查服務狀態
docker-compose -f docker-compose.prod.yml ps
```

**預期輸出**：所有服務應該是 `Up` 狀態

---

### 步驟 3：備份（保險起見）

```bash
# 備份資料庫（雖然本次不涉及資料庫變更）
docker-compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U aichatbot aichatbot_admin > backup_$(date +%Y%m%d_%H%M%S).sql

# 確認備份文件
ls -lh backup_*.sql | tail -1
```

---

### 步驟 4：拉取最新代碼

```bash
# 拉取最新代碼
git pull origin main

# 確認拉取到正確的 commit
git log --oneline -5
```

**預期看到**：
```
13b73bf refactor: 整理根目錄，建立清晰的項目結構
c38816c docs: 清理過時文檔，建立完整文檔體系
cbf4c4f feat: 統一檢索路徑，使意圖成為純排序因子  ← 目標 commit
```

---

### 步驟 5：重建並重啟 rag-orchestrator

```bash
# 停止並重建 rag-orchestrator（使用 --no-cache 確保完全重建）
docker-compose -f docker-compose.prod.yml build --no-cache rag-orchestrator

# 重啟服務
docker-compose -f docker-compose.prod.yml up -d rag-orchestrator

# 等待服務啟動
sleep 10

# 檢查服務狀態
docker-compose -f docker-compose.prod.yml ps rag-orchestrator
```

**預期輸出**：
```
NAME                  STATUS        PORTS
rag-orchestrator      Up X seconds  0.0.0.0:8100->8000/tcp
```

---

### 步驟 6：驗證部署

#### 6.1 健康檢查

```bash
# 檢查服務是否正常響應
curl -s http://localhost:8100/health | grep -q "ok" && \
  echo "✅ 服務正常" || echo "❌ 服務異常"
```

#### 6.2 測試知識 1262（核心驗證）

```bash
# 測試續約問題（知識 1262）
curl -s -X POST "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，我要續約，新的合約甚麼時候會提供?",
    "vendor_id": 2,
    "target_user": "tenant"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('✅ 找到知識數:', data.get('source_count', 0))
if data.get('sources'):
    print('✅ 首個知識 ID:', data['sources'][0].get('id'))
    print('✅ 相似度:', data['sources'][0].get('base_similarity'))
else:
    print('❌ 未找到知識')
"
```

**預期輸出**：
```
✅ 找到知識數: 5
✅ 首個知識 ID: 1262
✅ 相似度: 0.833
```

#### 6.3 測試 unclear 查詢（邊界測試）

```bash
# 測試無明確意圖的問題
curl -s -X POST "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "幫我查一下資料",
    "vendor_id": 1,
    "target_user": "customer"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('✅ 意圖:', data.get('intent_name', 'N/A'))
print('✅ 找到知識數:', data.get('source_count', 0))
print('✅ 有回答:', 'yes' if len(data.get('answer', '')) > 0 else 'no')
"
```

**預期**：即使是 unclear，也應該能找到相關知識

#### 6.4 檢查日誌（確認新邏輯）

```bash
# 檢查最近的查詢日誌
docker-compose -f docker-compose.prod.yml logs --tail 50 rag-orchestrator | \
  grep -E "Hybrid Retrieval|Primary Intent ID|boost"
```

**預期看到**：
```
[Hybrid Retrieval - Enhanced] ...
Primary Intent ID: None  (對於 unclear 查詢)
boost: 1.00x [無意圖（unclear）]
```

---

### 步驟 7：完整功能測試（推薦）

```bash
# 運行驗證腳本（如果有）
bash scripts/test_retrieval_validation.sh
```

或手動測試以下場景：

1. **明確意圖 + 高相似度**
   - 輸入：「我想要解約」
   - 預期：找到解約相關知識

2. **明確意圖 + 中等相似度**
   - 輸入：「如何終止契約」
   - 預期：找到解約知識（語義相近）

3. **unclear + 高相似度**
   - 輸入：「續約的合約什麼時候提供」
   - 預期：找到知識 1262（base=0.833）

4. **unclear + 低相似度**
   - 輸入：「你好」
   - 預期：通用回答或找不到知識

---

## ✅ 部署完成檢查清單

- [ ] Git 代碼已拉取到 commit cbf4c4f
- [ ] rag-orchestrator 容器已重建（--no-cache）
- [ ] rag-orchestrator 服務狀態為 Up
- [ ] 健康檢查通過
- [ ] 知識 1262 測試通過（找到且相似度 0.833）
- [ ] unclear 查詢測試通過
- [ ] 日誌顯示新的 Hybrid Retrieval 邏輯
- [ ] 無嚴重錯誤日誌

---

## 📊 預期改善效果

### 檢索準確度

| 場景 | 修改前 | 修改後 |
|------|--------|--------|
| **意圖不匹配 + 高相似度** | ❌ 找不到（unclear 特殊路徑） | ✅ 找到（統一邏輯） |
| **unclear + base > 0.55** | ❌ 可能找不到 | ✅ 找到 |
| **明確意圖 + base < 0.55** | ❌ 若在依賴區間會被過濾 | ✅ 正確過濾（只用向量） |
| **明確意圖 + base > 0.55** | ✅ 找到 | ✅ 找到（排序更優） |

### 系統改善

- ✅ **代碼量**：-209 行（更簡潔）
- ✅ **邏輯複雜度**：降低（無特殊路徑）
- ✅ **維護成本**：降低（統一邏輯）
- ✅ **測試覆蓋**：提升（無需測試特殊路徑）

---

## 🔄 回滾步驟（如果需要）

如果部署後發現問題，執行以下回滾：

```bash
# 1. 查看回滾目標 commit
git log --oneline -5

# 2. 回滾代碼（回到上一個穩定版本）
git reset --hard fd1b7bc  # 或其他穩定 commit

# 3. 重建並重啟
docker-compose -f docker-compose.prod.yml build --no-cache rag-orchestrator
docker-compose -f docker-compose.prod.yml up -d rag-orchestrator

# 4. 驗證
curl -s http://localhost:8100/health
```

**注意**：本次無資料庫變更，回滾不需要還原資料庫

---

## 🐛 常見問題排查

### Q1: 重建後服務無法啟動

**檢查日誌**：
```bash
docker-compose -f docker-compose.prod.yml logs rag-orchestrator --tail 100
```

**常見原因**：
- 端口衝突（8100 已被佔用）
- 環境變數缺失（檢查 .env 文件）
- 依賴服務未啟動（postgres, embedding-service）

**解決**：
```bash
# 檢查端口
lsof -i :8100

# 檢查依賴服務
docker-compose -f docker-compose.prod.yml ps

# 重啟所有服務
docker-compose -f docker-compose.prod.yml restart
```

### Q2: 重建很慢或失敗

**原因**：Docker build cache 或網路問題

**解決**：
```bash
# 清理 Docker cache
docker builder prune

# 重新嘗試
docker-compose -f docker-compose.prod.yml build --no-cache rag-orchestrator
```

### Q3: 測試通過但前端沒變化

**原因**：這次更新不涉及前端，前端不會有視覺變化

**檢查**：透過日誌確認邏輯變更
```bash
# 發送測試請求並查看日誌
docker-compose -f docker-compose.prod.yml logs -f rag-orchestrator
```

### Q4: 知識 1262 還是找不到

**排查步驟**：

```bash
# 1. 檢查知識 1262 是否存在
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin -c \
  "SELECT id, question_summary, vendor_id FROM knowledge_base WHERE id = 1262;"

# 2. 檢查意圖映射
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin -c \
  "SELECT knowledge_id, intent_id FROM knowledge_intent_mapping WHERE knowledge_id = 1262;"

# 3. 檢查 embedding 是否存在
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin -c \
  "SELECT id, embedding IS NOT NULL as has_embedding FROM knowledge_base WHERE id = 1262;"
```

**如果 embedding = false**：
```bash
# 重新生成 embedding
curl -X POST http://localhost:8087/api/knowledge/regenerate-embeddings
```

---

## 📞 需要支援

如果部署過程遇到問題，請提供：

1. **錯誤截圖或訊息**
2. **服務日誌**：
   ```bash
   docker-compose -f docker-compose.prod.yml logs rag-orchestrator --tail 200 > logs.txt
   ```
3. **環境資訊**：
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   git log --oneline -5
   ```

---

## 📝 部署記錄

**執行人員**：_________________
**執行時間**：_________________
**Git Commit**：cbf4c4f
**部署狀態**：☐ 成功  ☐ 失敗  ☐ 回滾

### 驗證結果

- [ ] 知識 1262 測試：☐ 通過  ☐ 失敗
- [ ] unclear 測試：☐ 通過  ☐ 失敗
- [ ] 日誌檢查：☐ 正常  ☐ 異常

### 備註

```
（記錄任何特殊情況或注意事項）
```

---

**文件生成日期**：2026-01-13
**相關文檔**：
- 完整實施報告：`docs/implementation/FINAL_2026-01-13.md`
- 實施總結：`docs/implementation/SUMMARY.md`
- 驗證報告：`docs/verification/report_2026-01-13.md`
