# 知識缺口智能分類器 - 快速參考指南

**最後更新**：2026-03-21

---

## 🚀 快速開始

### 驗證整合是否正常

```bash
docker exec -e PYTHONPATH=/app aichatbot-rag-orchestrator \
  python3 /app/services/knowledge_completion_loop/verify_classifier_integration.py
```

**預期輸出**：
```
✅ OpenAI 分類完成：46 個問題
過濾結果：46 題 → 35 題需要生成知識
減少比例：23.9%
```

---

## 📋 核心功能

### 智能分類器做什麼？

將知識缺口分為 4 種類型，並自動過濾不需要生成靜態知識的問題：

| 分類 | 說明 | 範例 | 生成知識？ |
|------|------|------|-----------|
| `sop_knowledge` | 操作流程、標準流程 | 「如何續約」 | ✅ 是 |
| `api_query` | 即時資料查詢 | 「租金多少」 | ❌ 否 |
| `form_fill` | 需要用戶互動填表 | 「我想找房」 | ✅ 是 |
| `system_config` | 帳戶設定、技術操作 | 「可以用 Google 登入嗎」 | ✅ 是 |

### 實際效益（Loop 45 實測）

- **原本**：46 題失敗 → 46 筆知識
- **現在**：46 題失敗 → 35 筆知識（減少 24%）
- **識別出**：10 題 API 查詢類型（不應生成靜態知識）

---

## 🔧 使用方式

### 1. 獨立測試分類器

測試分類器功能（使用 Loop 45 的資料）：

```bash
docker exec -e PYTHONPATH=/app aichatbot-rag-orchestrator \
  python3 /app/services/knowledge_completion_loop/test_gap_classifier.py
```

**輸出內容**：
- 分類結果摘要
- 分類詳情（前 20 題）
- 聚類結果（如果有）
- 處理建議

### 2. 驗證整合

驗證分類器是否正確整合到主流程：

```bash
docker exec -e PYTHONPATH=/app aichatbot-rag-orchestrator \
  python3 /app/services/knowledge_completion_loop/verify_classifier_integration.py
```

**輸出內容**：
- 分類結果
- 過濾效果
- 效益分析

### 3. 執行完整迴圈

執行一次完整的知識補完迴圈（包含分類階段）：

```bash
docker exec -e PYTHONPATH=/app -e PYTHONUNBUFFERED=1 \
  aichatbot-rag-orchestrator \
  python3 -u /app/services/knowledge_completion_loop/run_first_loop.py
```

**流程**：
1. 回測（BACKTESTING）
2. 分析缺口（ANALYZING）
3. **🆕 智能分類和過濾**
4. 生成知識（GENERATING）
5. 等待審核（REVIEWING）

---

## 📁 檔案位置

### 核心程式碼

```
/rag-orchestrator/services/knowledge_completion_loop/
├── gap_classifier.py           # 分類器核心邏輯
├── coordinator.py              # 主流程（已整合分類）
├── test_gap_classifier.py      # 獨立測試
└── verify_classifier_integration.py  # 整合驗證
```

### 文檔

```
/docs/backtest/
├── GAP_CLASSIFIER_INTEGRATION.md      # 詳細整合說明
├── GAP_CLASSIFIER_FINAL_SUMMARY.md    # 完整技術總結
├── WORK_COMPLETED_2026-03-21.md       # 工作完成報告
└── QUICK_REFERENCE.md                 # 本文檔
```

### 日誌檔案

```
/tmp/
├── gap_classification_openai.log       # OpenAI 分類測試
├── gap_classification_result.json      # 分類結果（JSON）
└── verify_classifier.log               # 整合驗證日誌
```

---

## 🔍 檢查分類結果

### 查看資料庫中的分類記錄

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
SELECT
    event_type,
    event_data->>'total_gaps' as total_gaps,
    event_data->>'should_generate_count' as should_generate,
    event_data->>'api_query_count' as api_queries,
    created_at
FROM loop_execution_logs
WHERE event_type = 'gap_classification_completed'
ORDER BY created_at DESC
LIMIT 5;
"
```

### 查看完整分類結果（JSON）

```bash
cat /tmp/gap_classification_result.json | python3 -m json.tool | head -50
```

---

## ⚙️ 設定和調整

### 使用不同的 OpenAI 模型

預設使用 `gpt-4o-mini`，如需更改：

```python
# 在 coordinator.py 中
self.gap_classifier = GapClassifier(
    openai_api_key=openai_api_key,
    model="gpt-4o"  # 改用更強大的模型
)
```

### 調整分類 Prompt

編輯 `gap_classifier.py` 中的 `CLASSIFICATION_PROMPT`：

```python
CLASSIFICATION_PROMPT = """你是一個專業的知識庫管理專家...

**分類標準**：
1. **sop_knowledge**（SOP 知識）
   - 操作流程、步驟說明
   ...
"""
```

### Stub 模式（無 OpenAI API）

如果沒有設定 `OPENAI_API_KEY`，系統會自動使用 Stub 模式（關鍵字匹配）。

---

## 🐛 疑難排解

### Q: 分類結果不準確？

**A**: 調整 `CLASSIFICATION_PROMPT`，提供更多分類範例和說明。

### Q: 想要查看分類的詳細理由？

**A**: 查看完整的分類結果：

```bash
cat /tmp/gap_classification_result.json | python3 -m json.tool
```

每個問題都有 `reasoning` 欄位說明分類理由。

### Q: 如何禁用分類功能？

**A**: 在 `coordinator.py` 的 `execute_iteration()` 中，註釋掉分類邏輯：

```python
# # 階段 2.5：智能分類和過濾
# classification_result = await self.gap_classifier.classify_gaps(gaps)
# filtered_gaps = self.gap_classifier.filter_gaps_for_generation(...)

# 直接使用原始的 gaps
filtered_gaps = gaps
```

### Q: OpenAI API 呼叫失敗？

**A**: 檢查以下項目：
1. 確認 API Key 正確：`echo $OPENAI_API_KEY`
2. 檢查 API 配額是否用盡
3. 查看錯誤日誌：`/tmp/gap_classification_*.log`
4. 系統會自動 fallback 到 Stub 模式

---

## 📊 監控和分析

### 查看分類統計

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
SELECT
    COUNT(*) as total_classifications,
    AVG((event_data->>'should_generate_count')::int) as avg_should_generate,
    AVG((event_data->>'api_query_count')::int) as avg_api_queries
FROM loop_execution_logs
WHERE event_type = 'gap_classification_completed';
"
```

### 查看最近的分類效果

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "
SELECT
    loop_id,
    event_data->>'total_gaps' as total,
    event_data->>'should_generate_count' as generate,
    ROUND(
        (1 - (event_data->>'should_generate_count')::float /
        (event_data->>'total_gaps')::float) * 100,
        1
    ) as saved_percent,
    created_at
FROM loop_execution_logs
WHERE event_type = 'gap_classification_completed'
ORDER BY created_at DESC
LIMIT 10;
"
```

---

## 🔄 下一步優化

### 短期（已規劃）

1. **調整 Prompt**：根據實際使用情況優化分類準確度
2. **記錄到資料庫**：將分類結果保存到專用表
3. **人工審核機制**：允許人工修正分類結果

### 中期（待實作）

1. **啟用聚類功能**：識別相似問題，進一步減少重複
2. **動態查詢機制**：為 API 查詢類問題建立查詢流程
3. **表單庫**：為表單填寫類問題建立標準表單
4. **UI 整合**：在後台顯示分類結果

### 長期（未來規劃）

1. **訓練專用模型**：降低 API 成本
2. **回饋機制**：持續優化分類準確度
3. **A/B 測試**：比較不同策略效果

---

## 📞 需要協助？

### 查看詳細文檔

- **整合說明**：`docs/backtest/GAP_CLASSIFIER_INTEGRATION.md`
- **技術總結**：`docs/backtest/GAP_CLASSIFIER_FINAL_SUMMARY.md`
- **工作報告**：`docs/backtest/WORK_COMPLETED_2026-03-21.md`

### 查看測試日誌

```bash
# OpenAI 分類測試
cat /tmp/gap_classification_openai.log

# 整合驗證測試
cat /tmp/verify_classifier.log

# 完整分類結果（JSON）
cat /tmp/gap_classification_result.json | python3 -m json.tool
```

---

**版本**：v1.0
**最後更新**：2026-03-21
**狀態**：✅ 已完成並測試通過
