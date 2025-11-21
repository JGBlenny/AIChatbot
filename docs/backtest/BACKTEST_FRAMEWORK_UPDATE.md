# 測試框架更新說明

## 📅 更新日期
2025-01-XX

## 🎯 更新目標
將測試框架完全適配 LLM 評估模式，移除對已刪除字段（expected_category, expected_keywords, expected_intent_id）的依賴。

---

## ✅ 主要變更

### 1. **默認評估模式變更**
- **舊版**: 默認使用 `basic` 模式（基於分類匹配 + 關鍵字覆蓋 + 信心度）
- **新版**: 默認使用 `detailed` 模式（100% LLM 評估）

```python
# 舊版
quality_mode: str = "basic"

# 新版
quality_mode: str = "detailed"
```

### 2. **移除 Basic 評估模式**
Basic 模式已完全移除，因為它依賴已刪除的字段：
- ❌ 移除分類匹配檢查（依賴 expected_category）
- ❌ 移除關鍵字覆蓋檢查（依賴 expected_keywords）
- ✅ 保留信心度檢查（用於 hybrid 模式）

### 3. **支援的評估模式**

| 模式 | 說明 | 評分構成 | 適用場景 |
|------|------|----------|----------|
| **detailed** | LLM 深度評估（推薦） | 100% LLM 評估（相關性、完整性、準確性、意圖理解） | 全面品質評估 |
| **hybrid** | 混合模式 | 40% 信心度 + 60% LLM 評估 | 兼顧速度與品質 |

### 4. **OPENAI_API_KEY 要求**
新版本強制要求設定 OPENAI_API_KEY：

```bash
export OPENAI_API_KEY="sk-..."
```

如果未設定，腳本會直接報錯，不再降級為 basic 模式。

---

## 📝 文件變更詳情

### backtest_framework.py

#### A. SQL 查詢更新（5 處）

**移除的字段**:
- `ts.expected_category`
- `ts.expected_keywords`

**更新的查詢**:
1. `load_test_scenarios_by_strategy()` - incremental 策略
2. `load_test_scenarios_by_strategy()` - failed_only 策略
3. `load_test_scenarios_by_strategy()` - full 策略
4. `load_test_scenarios_from_db()`
5. 移除關鍵字陣列處理邏輯

#### B. 評估邏輯重寫

**evaluate_answer() 方法**

```python
# 舊版（依賴已刪除字段）
def evaluate_answer(...):
    # 1. 檢查分類匹配 (expected_category) - 30% 權重
    # 2. 檢查關鍵字覆蓋 (expected_keywords) - 40% 權重
    # 3. 檢查信心度 - 30% 權重

# 新版（僅基於信心度）
def evaluate_answer(...):
    # 檢查信心度 - 100% 權重
    # >= 0.8: score = 1.0
    # >= 0.6: score = 0.7
    # >= 0.4: score = 0.5
    # <  0.4: score = 0.3
```

**llm_evaluate_answer() 方法**

```python
# 舊版（使用預期意圖）
def llm_evaluate_answer(question, answer, expected_intent):
    prompt = f"""
    問題：{question}
    預期意圖：{expected_intent}
    答案：{answer}
    """

# 新版（移除預期意圖）
def llm_evaluate_answer(question, answer):
    prompt = f"""
    問題：{question}
    答案：{answer}

    評估維度：
    1. 相關性
    2. 完整性
    3. 準確性
    4. 意圖理解（自動判斷）
    """
```

#### C. 結果記錄更新

**移除的字段**:
```python
result = {
    # ❌ 'expected_category': ...
    # ❌ 'category_match': ...
    # ❌ 'keyword_coverage': ...
}
```

**保留的字段**:
```python
result = {
    'test_id': i,
    'scenario_id': scenario.get('id'),
    'test_question': question,
    'actual_intent': ...,  # 保留
    'confidence': ...,      # 保留
    'score': ...,           # 基礎分數
    'overall_score': ...,   # LLM 綜合評分
    'passed': ...,
    'relevance': ...,       # LLM 評估
    'completeness': ...,    # LLM 評估
    'accuracy': ...,        # LLM 評估
    'intent_match': ...,    # LLM 評估
    ...
}
```

#### D. 報告生成更新

**失敗案例報告**:
```
# 舊版
問題：...
預期分類：...          ← 移除
實際意圖：...
分數：...

# 新版
問題：...
實際意圖：...
基礎分數：...
綜合評分：...          ← 新增
信心度：...            ← 新增
```

#### E. 資料庫儲存更新

**INSERT 語句移除字段**:
```sql
-- 移除
expected_category
category_match
keyword_coverage
```

---

## 🚀 使用指南

### 環境變數設定

```bash
# 必需
export OPENAI_API_KEY="sk-..."

# 可選（有默認值）
export BACKTEST_QUALITY_MODE="detailed"    # 或 "hybrid"
export BACKTEST_USE_DATABASE="true"         # 使用資料庫
export BACKTEST_SELECTION_STRATEGY="full"   # incremental/full/failed_only
```

### 執行測試

```bash
# 完整測試（默認 detailed 模式）
cd /Users/lenny/jgb/AIChatbot
python3 scripts/knowledge_extraction/backtest_framework.py

# 使用 hybrid 模式
BACKTEST_QUALITY_MODE=hybrid python3 scripts/knowledge_extraction/backtest_framework.py

# 增量測試（僅測試新測試 + 失敗測試）
BACKTEST_SELECTION_STRATEGY=incremental python3 scripts/knowledge_extraction/backtest_framework.py
```

---

## 📊 評估維度說明

### LLM 評估維度（1-5 分）

| 維度 | 說明 | 評分標準 |
|------|------|----------|
| **相關性** (Relevance) | 答案是否直接回答問題 | 5分: 完全相關<br>1分: 完全無關 |
| **完整性** (Completeness) | 答案是否完整涵蓋問題所問 | 5分: 非常完整<br>1分: 極度不完整 |
| **準確性** (Accuracy) | 答案內容是否準確可靠 | 5分: 完全準確<br>1分: 錯誤信息 |
| **意圖理解** (Intent Match) | 是否正確理解問題意圖並回應 | 5分: 完全理解<br>1分: 理解錯誤 |
| **綜合評分** (Overall) | LLM 給出的綜合評分 | 自動計算 |

### 通過標準

| 模式 | 通過條件 |
|------|----------|
| **detailed** | 綜合評分 >= 3.0 且 完整性 >= 3.0 |
| **hybrid** | 混合分數 >= 0.5 且 完整性 >= 2.5 |

---

## ⚠️ 兼容性說明

### 資料庫表變更

**backtest_results 表**:
- 移除列: `expected_category`, `category_match`, `keyword_coverage`
- 這些列仍存在於資料庫中（為了向後兼容），但新版腳本不再寫入數據

### Excel 輸出

Excel 輸出文件不再包含以下列：
- `expected_category`
- `category_match`
- `keyword_coverage`

---

## 🎉 優勢

### 舊版 (Basic 模式)
✅ 快速評估
❌ 依賴手動標註（expected_category, expected_keywords）
❌ 評估維度有限（僅檢查表單匹配）
❌ 無法評估答案真正的質量

### 新版 (Detailed 模式)
✅ **自動化**：無需手動標註預期分類和關鍵字
✅ **全面評估**：從相關性、完整性、準確性、意圖理解 4 個維度評估
✅ **真實質量**：測試「答案是否準確、完整、有用」而非「表單是否匹配」
✅ **詳細反饋**：LLM 提供評分理由，便於優化

---

## 📚 相關文件

- **測試框架腳本**: `/scripts/knowledge_extraction/backtest_framework.py`
- **資料庫遷移**: `/database/migrations/40-simplify-test-scenarios-for-llm-eval.sql`
- **簡化指南**: `/docs/SIMPLIFICATION_IMPLEMENTATION_GUIDE.md`

---

## 🔄 後續工作

1. ✅ 更新 backtest_framework.py（本次完成）
2. ⏳ 更新 create_test_scenarios.py（移除 expected_category/keywords）
3. ⏳ 更新 extract_knowledge_and_tests*.py（移除相關字段）
4. ⏳ 執行完整回測驗證新框架

---

## 💡 最佳實踐

### 測試策略選擇

| 策略 | 適用場景 | 測試數量 |
|------|----------|----------|
| **incremental** | 日常回歸測試 | ~100 個（新測試 + 失敗測試） |
| **full** | 重大變更後的全面測試 | 所有已批准測試 |
| **failed_only** | 針對性優化失敗案例 | 僅失敗測試 |

### 質量模式選擇

- **日常測試**: 使用 `hybrid` 模式（平衡速度與品質）
- **正式評估**: 使用 `detailed` 模式（最全面的評估）

---

**更新者**: Claude
**審核者**: Lenny
**版本**: 2.0
