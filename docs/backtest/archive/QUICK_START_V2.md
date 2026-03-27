# 回測系統 V2 快速入門

**版本**: V2 (2026-03-15) + Similarity Extraction 修復 (2026-03-16)
**狀態**: ✅ 核心功能完成 + Similarity Extraction 修復完成

---

## 🎯 核心變更

### ❌ 移除（舊系統）

- LLM 0-10 分制評分
- `llm_evaluate_answer()` 方法
- `relevance`, `completeness`, `accuracy`, `intent_match` 指標
- 批量 LLM 評估流程

### ✅ 新增（V2 系統）

- **confidence_score** (0-1 範圍) - 對齊生產環境
- **confidence_level** (high/medium/low) - 信心度等級
- **semantic_overlap** (0-1 範圍) - 語義相關性
- 四層評估邏輯
- **✨ Similarity Extraction** (2026-03-16) - 自動從 debug_info 提取相似度

---

## 🚀 快速使用

### 基本用法

```python
from backtest_framework_async import AsyncBacktestFramework

# 初始化框架
framework = AsyncBacktestFramework(
    base_url="http://localhost:8100",
    vendor_id=1
)

# 測試回應
test_response = {
    "answer": "租金包含水電費",
    "sources": [
        {"similarity": 0.85, "content": "租金包含水電費"}
    ]
}

# 方法 1：只計算 confidence_score
confidence_result = framework.calculate_confidence_score(
    test_response,
    "租金包含水電嗎?"
)

print(f"Confidence Score: {confidence_result['confidence_score']}")
print(f"Confidence Level: {confidence_result['confidence_level']}")
# 輸出:
# Confidence Score: 0.723
# Confidence Level: medium

# 方法 2：完整評估（推薦）
scenario = {"test_question": "租金包含水電嗎?"}

eval_result = framework.evaluate_answer_v2(scenario, test_response)

print(f"Passed: {eval_result['passed']}")
print(f"Confidence: {eval_result['confidence_level']} ({eval_result['confidence_score']})")
print(f"Semantic Overlap: {eval_result['semantic_overlap']}")
# 輸出:
# Passed: True
# Confidence: medium (0.723)
# Semantic Overlap: 0.85
```

---

## 📊 評估指標說明

### 1. confidence_score (0-1)

**計算公式**:
```python
confidence_score = (
    max_similarity * 0.7 +      # 最高相似度（70% 權重）
    (result_count / 5) * 0.2 +  # 結果數量（20% 權重）
    keyword_match_rate * 0.1    # 關鍵字匹配（10% 權重）
)
```

**組成要素**:
- **max_similarity**: 最相關文檔的相似度 (0-1)
- **result_count**: 檢索到的文檔數量（歸一化到 0-1）
- **keyword_match_rate**: 問題關鍵字在答案中的匹配率 (0-1)

**示例**:
```python
# 高信心度案例
{
    'max_similarity': 0.92,
    'result_count': 3,
    'keyword_match_rate': 0.8
}
# → confidence_score = 0.92 * 0.7 + 0.6 * 0.2 + 0.8 * 0.1 = 0.884

# 中信心度案例
{
    'max_similarity': 0.75,
    'result_count': 2,
    'keyword_match_rate': 0.5
}
# → confidence_score = 0.75 * 0.7 + 0.4 * 0.2 + 0.5 * 0.1 = 0.655

# 低信心度案例
{
    'max_similarity': 0.45,
    'result_count': 1,
    'keyword_match_rate': 0.2
}
# → confidence_score = 0.45 * 0.7 + 0.2 * 0.2 + 0.2 * 0.1 = 0.375
```

---

### 2. confidence_level (文字)

**等級判定**:
```python
if confidence_score >= 0.85 and result_count >= 2:
    level = "high"
elif confidence_score >= 0.70:
    level = "medium"
else:
    level = "low"
```

**含義**:
- **high**: 高信心度 - 系統非常確定答案正確
- **medium**: 中信心度 - 系統較有信心，但可能不完整
- **low**: 低信心度 - 系統不確定，可能需要人工介入

---

### 3. semantic_overlap (0-1)

**用途**: 檢測答非所問

**計算**: 使用 `BAAI/bge-reranker-base` 模型

**閾值**:
- `< 0.4`: 答非所問（直接失敗）
- `0.4 - 0.6`: 弱相關（需配合 confidence_score 判斷）
- `> 0.6`: 強相關

**示例**:
```python
# 答非所問案例
問題: "房租包含水電嗎？"
答案: "水電維修廠商資訊..."
semantic_overlap = 0.077  # < 0.4 → 直接失敗

# 正確答案案例
問題: "房租包含水電嗎？"
答案: "租金包含水電費"
semantic_overlap = 0.92  # > 0.6 → 強相關
```

---

## 🎯 通過標準（方案 3）

### 判定邏輯

```python
# 第 1 層：基礎檢查
if answer == "" or "沒有找到資訊" in answer:
    passed = False

# 第 2 層：語義攔截
elif semantic_overlap < 0.4:
    passed = False  # 答非所問

# 第 3 層：綜合判定
elif confidence_score >= 0.85:
    passed = True
elif confidence_score >= 0.70 and semantic_overlap >= 0.5:
    passed = True
elif confidence_score >= 0.60 and semantic_overlap >= 0.6:
    passed = True
else:
    passed = False
```

### 通過案例

| confidence_score | semantic_overlap | 結果 | 原因 |
|-----------------|------------------|------|------|
| 0.88 | 0.75 | ✅ Pass | 高信心度 |
| 0.72 | 0.55 | ✅ Pass | 中信心度 + 中等語義 |
| 0.65 | 0.70 | ✅ Pass | 低信心度 + 強語義 |
| 0.75 | 0.35 | ❌ Fail | 語義過低（答非所問）|
| 0.55 | 0.50 | ❌ Fail | 信心度不足 |
| 0.00 | N/A | ❌ Fail | 沒找到資料 |

---

## 📋 返回格式

### calculate_confidence_score()

```python
{
    'confidence_score': 0.723,      # float (0-1)
    'confidence_level': 'medium',   # str (high/medium/low)
    'max_similarity': 0.85,         # float (0-1)
    'result_count': 2,              # int
    'keyword_match_rate': 0.6       # float (0-1)
}
```

### evaluate_answer_v2()

```python
{
    'passed': True,                        # bool
    'confidence_score': 0.723,             # float (0-1)
    'confidence_level': 'medium',          # str
    'semantic_overlap': 0.75,              # float (0-1)
    'max_similarity': 0.85,                # float (0-1)
    'result_count': 2,                     # int
    'keyword_match_rate': 0.6,             # float (0-1)
    'failure_reason': '',                  # str (失敗時說明原因)
    'optimization_tips': []                # list (優化建議)
}
```

---

## 🔧 環境變數

```bash
# 回測配置
export BACKTEST_CONCURRENCY=5          # 並發數
export BACKTEST_TIMEOUT=60             # 超時時間（秒）
export BACKTEST_QUALITY_MODE=detailed  # 品質模式
export BACKTEST_LIMIT=10               # 測試數量限制（可選）

# RAG 服務
export RAG_API_URL=http://localhost:8100

# 資料庫（使用資料庫時）
export DB_HOST=aichatbot-postgres
export DB_NAME=aichatbot_admin
export DB_USER=aichatbot
export DB_PASSWORD=aichatbot_password
```

---

## 🚨 常見問題

### Q1: 為什麼移除了 LLM 評分？

**A**: LLM 評分存在以下問題：
1. 不穩定：給錯誤答案 10/10，給「沒找到資料」4-6 分
2. 與生產環境不一致：生產用 confidence_score，回測用 LLM
3. 成本高：每次評估需調用 LLM API
4. 延遲大：批量評估需要額外時間

### Q2: confidence_score 如何解讀？

**A**:
- **0.85+**: 高信心 - 答案很可能正確且完整
- **0.70-0.84**: 中信心 - 答案基本正確，可能不完整
- **0.60-0.69**: 低信心 - 答案相關性弱，需人工檢查
- **0.60-**: 極低信心 - 答案很可能不正確

### Q3: 什麼情況會直接失敗？

**A**:
1. 答案為空
2. 答案是「沒有找到資訊」
3. semantic_overlap < 0.4（答非所問）
4. confidence_score < 0.6 且 semantic_overlap < 0.6

### Q4: 如何提高通過率？

**A**:
1. **補充知識庫** - 提高 max_similarity
2. **豐富內容** - 增加相關文檔數量
3. **優化答案** - 包含問題關鍵字
4. **移除錯誤知識** - 避免答非所問

### Q5: Similarity Extraction 是什麼？為什麼需要？

**A**: Similarity Extraction 是 2026-03-16 的關鍵修復

**問題背景**:
- RAG API 的 `sources` 默認不包含 `similarity` 分數
- V2 評估邏輯依賴 `max_similarity` 計算 confidence_score
- Run 66 (100 tests) 全部失敗，因為 `max_similarity` 全部為 0.0

**修復方案**:
1. 請求 RAG API 時添加 `"include_debug_info": True`
2. 從 `debug_info.knowledge_candidates` 提取 similarity
3. 自動注入到 `sources` 對象中

**修復效果**:
- `max_similarity` 從 0.0 → 實際相似度 (0.7-0.95)
- `confidence_score` 從 ~0.130 → 合理範圍 (0.6-0.9)
- 預期通過率顯著提升

**使用者無需操作** - 框架自動處理

---

## 📚 進階主題

### 自定義閾值

```python
# 修改通過標準（不建議）
def custom_pass_criteria(confidence_score, semantic_overlap):
    if semantic_overlap < 0.3:  # 更嚴格的語義要求
        return False
    if confidence_score >= 0.80:  # 更高的信心度要求
        return True
    return False
```

### 批量測試

```bash
# 小規模測試（10條）
export BACKTEST_LIMIT=10
python3 run_backtest_db.py

# 完整測試（全部）
unset BACKTEST_LIMIT
python3 run_backtest_db.py
```

---

## 🔗 相關文檔

- [BACKTEST_ALIGNMENT_PLAN_2026-03-15.md](./BACKTEST_ALIGNMENT_PLAN_2026-03-15.md) - 完整修正計畫
- [BACKTEST_V2_IMPLEMENTATION_REPORT.md](./BACKTEST_V2_IMPLEMENTATION_REPORT.md) - 實施報告
- [SOLUTION_B_SEMANTIC_PRIORITY.md](./SOLUTION_B_SEMANTIC_PRIORITY.md) - 語義優先策略

---

**最後更新**: 2026-03-15
**維護者**: Claude
