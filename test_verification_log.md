# 50 題驗證測試記錄

**測試日期**：2026-03-27
**測試人員**：
**環境**：本地 Docker

---

## 第一次迭代

### 基本資訊
- **Loop ID**：_________
- **開始時間**：__:__
- **結束時間**：__:__
- **總耗時**：_____ 分鐘

### 測試情境選取
- **選取策略**：分層隨機 / 順序 / 完全隨機
- **scenario_ids（前 10 個）**：[ _____, _____, _____, ... ]
- **難度分布**：
  - Easy: _____ 題
  - Medium: _____ 題
  - Hard: _____ 題

### 回測結果
- **總題數**：50
- **通過數**：_____
- **失敗數**：_____
- **通過率**：_____%
- **回測耗時**：_____ 分鐘

### 知識缺口分析
- **失敗案例數**：_____
- **分類結果**：
  - sop_knowledge: _____ 個
  - form_fill: _____ 個
  - system_config: _____ 個
  - api_query: _____ 個

### 聚類結果
- **SOP 組聚類數**：_____
- **Knowledge 組聚類數**：_____

### 知識生成
- **生成 SOP 數**：_____
- **生成一般知識數**：_____
- **總生成數**：_____
- **生成耗時**：_____ 秒

### 成本統計
- **OpenAI API 調用次數**：_____
- **估算成本**：$ _____

---

## 測試驗證 1：測試集固定性

### 驗證方法
```sql
SELECT scenario_ids FROM knowledge_completion_loops WHERE id = ______;
```

### 驗證結果
- **scenario_ids 已儲存**：✅ / ❌
- **陣列長度**：_____
- **scenario_ids（完整）**：
```
[_________________________________]
```

### 結論
- ✅ PASS：scenario_ids 已正確儲存
- ❌ FAIL：原因 __________

---

## 人工審核階段

### 審核方式
- ⬜ 前端審核（LoopKnowledgeReviewTab）
- ⬜ 直接資料庫操作（測試用）

### 審核統計
- **待審核數**：_____
- **批准數**：_____
- **拒絕數**：_____
- **審核耗時**：_____ 分鐘

### 批量審核測試（如果使用前端）
- **是否支援全選**：✅ / ❌
- **是否支援批量批准**：✅ / ❌
- **批量操作耗時**：_____ 秒
- **是否有失敗項目**：✅ / ❌
- **失敗原因**：__________

---

## 測試驗證 2：立即同步

### 驗證方法
```sql
-- 檢查同步到正式庫的知識
SELECT COUNT(*) FROM knowledge_base WHERE source = 'loop' AND source_loop_id = ______;
SELECT COUNT(*) FROM vendor_sop_items WHERE source = 'loop' AND source_loop_id = ______;
```

### 驗證結果
- **knowledge_base 新增數**：_____
- **vendor_sop_items 新增數**：_____
- **總同步數**：_____
- **是否匹配批准數**：✅ / ❌

### RAG 即時生效測試
**測試問題**（選擇一個生成的知識）：__________

**RAG 回答**：
```
_________________________________
```

**是否包含新知識**：✅ / ❌

### 結論
- ✅ PASS：立即同步正常
- ❌ FAIL：原因 __________

---

## 第二次迭代

### 基本資訊
- **Loop ID**：_________ (應與第一次相同)
- **開始時間**：__:__
- **結束時間**：__:__
- **總耗時**：_____ 分鐘

### 測試情境驗證
**驗證方法**：
```sql
SELECT scenario_ids FROM knowledge_completion_loops WHERE id = ______;
```

**驗證結果**：
- **scenario_ids 是否與第一次相同**：✅ / ❌
- **如不同，差異內容**：__________

### 回測結果
- **總題數**：50（應保持不變）
- **通過數**：_____
- **失敗數**：_____
- **通過率**：_____%
- **改善幅度**：_____% (新通過率 - 舊通過率)

### 知識生成
- **失敗案例數**：_____
- **生成知識數**：_____

---

## 測試驗證 3：改善幅度可追蹤

### 對比分析
| 項目 | 第 1 次 | 第 2 次 | 變化 |
|------|---------|---------|------|
| 通過率 | ____% | ____% | ____% |
| 失敗數 | ____ | ____ | ____ |
| 測試集 | [___] | [___] | 相同✅ / 不同❌ |

### 結論
- ✅ PASS：改善幅度可靠（測試集相同 且 通過率提升）
- ⚠️ WARNING：通過率未提升（但測試集相同，屬正常情況）
- ❌ FAIL：測試集不同，無法比較

---

## 驗證回測（可選）

### 執行驗證
- **驗證範圍**：failed_only / all / failed_plus_sample
- **測試題數**：_____
- **新通過率**：_____%
- **改善幅度**：_____%
- **是否達標（>5%）**：✅ / ❌

### Regression 檢測（如使用 failed_plus_sample）
- **抽樣通過案例數**：_____
- **Regression 數**：_____（原本通過現在失敗）
- **是否有 regression**：✅ / ❌

---

## 測試驗證 4：資料完整性

### 資料表檢查

**knowledge_completion_loops**：
```sql
SELECT * FROM knowledge_completion_loops WHERE id = ______ \gx
```
- ✅ scenario_ids 已填寫
- ✅ status 正確
- ✅ current_iteration 正確
- ✅ current_pass_rate 正確

**knowledge_gap_analysis**：
```sql
SELECT COUNT(*), gap_type, COUNT(DISTINCT cluster_id)
FROM knowledge_gap_analysis
WHERE loop_id = ______ AND iteration = 1
GROUP BY gap_type;
```
- ✅ 所有失敗案例已記錄
- ✅ gap_type 分類正確
- ✅ cluster_id 已分配

**loop_generated_knowledge**：
```sql
SELECT COUNT(*), knowledge_type, status
FROM loop_generated_knowledge
WHERE loop_id = ______
GROUP BY knowledge_type, status;
```
- ✅ 生成知識已記錄
- ✅ knowledge_type 正確
- ✅ status 正確

**loop_execution_logs**：
```sql
SELECT event_type, COUNT(*)
FROM loop_execution_logs
WHERE loop_id = ______
GROUP BY event_type
ORDER BY MIN(created_at);
```
- ✅ 所有步驟已記錄
- ✅ 事件順序正確

---

## 總體評估

### 功能驗證結果

| 測試項目 | 結果 | 備註 |
|----------|------|------|
| 測試集固定性 | ⬜ PASS ⬜ FAIL | |
| 回測效能 | ⬜ PASS ⬜ FAIL | 耗時: ___ 分鐘 |
| 分類準確性 | ⬜ PASS ⬜ FAIL | |
| 知識生成質量 | ⬜ PASS ⬜ FAIL | |
| 立即同步 | ⬜ PASS ⬜ FAIL | |
| 改善幅度可追蹤 | ⬜ PASS ⬜ FAIL | |
| 批量審核（如測試） | ⬜ PASS ⬜ FAIL | |
| 資料完整性 | ⬜ PASS ⬜ FAIL | |

### 發現的問題

1. **問題描述**：
   - 嚴重度：⬜ P0 ⬜ P1 ⬜ P2
   - 影響範圍：
   - 重現步驟：
   - 建議修復：

2. **問題描述**：
   - 嚴重度：⬜ P0 ⬜ P1 ⬜ P2
   - 影響範圍：
   - 重現步驟：
   - 建議修復：

### 效能指標

| 指標 | 目標值 | 實際值 | 達標 |
|------|--------|--------|------|
| 回測時間（50 題） | < 10 分鐘 | ___ 分鐘 | ⬜ ✅ ⬜ ❌ |
| 單次迭代總時間 | < 20 分鐘 | ___ 分鐘 | ⬜ ✅ ⬜ ❌ |
| 知識生成時間 | < 3 分鐘 | ___ 秒 | ⬜ ✅ ⬜ ❌ |
| 審核時間（人工） | < 10 分鐘 | ___ 分鐘 | ⬜ ✅ ⬜ ❌ |
| API 成本 | < $0.05 | $ ___ | ⬜ ✅ ⬜ ❌ |

### 最終結論

⬜ **✅ 驗證通過**：所有 P0 測試項目通過，可進入設計階段
⬜ **⚠️ 部分通過**：存在 P1 問題，需記錄但不阻塞設計
⬜ **❌ 驗證失敗**：存在 P0 問題，需修復後重測

### 下一步行動

- ⬜ 進入設計階段（`/kiro:spec-design backtest-knowledge-refinement -y`）
- ⬜ 修復發現的問題後重測
- ⬜ 擴展到 500 題測試
- ⬜ 其他：__________

---

**測試完成時間**：________
**測試人員簽名**：________
