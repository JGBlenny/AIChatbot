# 🐛 知識匯入質量評估過於嚴格問題

## 問題描述

**症狀**：每次匯入知識時，只有 2-3 個答案能通過，其他都被自動拒絕

**用戶觀察**：
```
匯入 10 筆知識 → 只有 2-3 筆可用
匯入 20 筆知識 → 只有 3-5 筆可用
```

## 根本原因

系統在匯入時使用 **LLM 進行質量評估**，評分標準非常嚴格：

### 評分標準

```python
"is_acceptable": 分數 >= 8 為可接受

評分參考：
- 9-10分：內容詳實、具體、有實用價值  ← 可接受
- 8分：有實用價值，包含必要細節        ← 可接受
- 6-7分：過於空泛或缺少關鍵細節        ← ❌ 拒絕
- 4-5分：基本可用，但內容空泛          ← ❌ 拒絕
- 1-3分：無實用價值，循環邏輯          ← ❌ 拒絕
```

### 問題所在

**標準過高**：
- ❌ 只有 8 分以上才接受
- ❌ 7 分以下直接拒絕
- ❌ 很多實用的 FAQ 可能只有 6-7 分

**影響範圍**：
- 所有知識匯入（CSV, Excel, TXT, JSON）
- 無論是否跳過審核

## 代碼位置

**檔案**: `rag-orchestrator/services/knowledge_import_service.py`

**關鍵代碼** (Line 986-1014):

```python
prompt = f"""請評估以下問答內容的質量。

問題：{knowledge['question_summary']}
答案：{knowledge['answer']}

評估標準：
1. 具體性：答案是否包含具體的操作步驟、細節或說明？
2. 實用性：答案是否能實際幫助使用者解決問題？
3. 完整性：答案是否完整回答了問題？
4. 非循環性：答案是否避免了循環邏輯？
5. 深度：答案是否有足夠的深度？

"is_acceptable": 是否可接受（true/false，分數 >= 8 為可接受）

⚠️ 注意：只有分數 >= 8 的知識才能進入審核佇列，7 分以下視為質量不足。
"""
```

**拒絕邏輯** (Line 1339-1351):

```python
# 決定狀態：根據質量評估結果
is_acceptable = quality_eval.get('is_acceptable', True)
if is_acceptable:
    status = 'pending_review'  # 進審核
else:
    status = 'rejected'  # 直接拒絕，不會在檢索中使用
    auto_rejected += 1
```

## 實際案例

### 案例 1: 測試匯入

```
輸入：3 筆知識
結果：
✅ 質量評估完成
   可接受: 1 條
   低質量: 2 條（將自動標記為已拒絕）

匯入知識: 3 條
實際可用: 1 條  ← 66% 被拒絕！
```

### 案例 2: 實際場景

**被拒絕的知識範例**：

```
問題：如何繳納租金？
答案：請在每月 5 號前透過超商條碼繳納。

評分：6-7 分（因為缺少「具體步驟」、「超商列表」等詳細資訊）
結果：❌ 拒絕（但這其實是有用的 FAQ！）
```

## 影響分析

### 受影響的功能
- ✅ 單檔案匯入
- ✅ 多檔案匯入
- ✅ 跳過審核的匯入
- ✅ 需要審核的匯入

### 用戶體驗問題
1. **預期與實際不符**：用戶匯入 100 筆，期待 100 筆可用，結果只有 20 筆
2. **無提示**：前端只顯示「匯入 100 筆」，不顯示「其中 80 筆被自動拒絕」
3. **不可控**：用戶無法調整質量標準或跳過評估

## 解決方案

### 方案 1: 降低評分門檻（快速修復）⭐ 推薦

**修改位置**: Line 1001

**修改前**:
```json
"is_acceptable": 是否可接受（true/false，分數 >= 8 為可接受）
```

**修改後**:
```json
"is_acceptable": 是否可接受（true/false，分數 >= 6 為可接受）
```

**優點**:
- ✅ 快速修復（1 行代碼）
- ✅ 立即生效
- ✅ 不影響其他功能

**缺點**:
- ❌ 可能接受一些質量較低的知識

---

### 方案 2: 新增「跳過質量評估」選項 ⭐ 推薦

**前端**: 新增 checkbox 選項

```vue
<label class="checkbox-option">
  <input type="checkbox" v-model="skipQualityEvaluation" />
  <span class="option-text">
    <strong>跳過質量評估</strong>
    <span class="info-text">⚠️ 不建議：所有知識將不經質量檢查直接匯入</span>
  </span>
</label>
```

**後端**: 新增參數

```python
async def upload_knowledge_file(
    ...
    skip_quality_evaluation: bool = Form(False)
):
```

**優點**:
- ✅ 給用戶選擇權
- ✅ 保留質量控制選項
- ✅ 靈活度高

**缺點**:
- ❌ 需要改動前後端（約 1 小時）

---

### 方案 3: 調整為三級制（長期方案）

**評分標準**:
- 8-10 分：自動接受
- 5-7 分：標記為「待審核（質量一般）」
- 1-4 分：自動拒絕

**優點**:
- ✅ 更合理的質量控制
- ✅ 平衡自動化與人工審核

**缺點**:
- ❌ 需要較大改動（2-3 小時）

---

## 建議行動

### 立即執行（5 分鐘）

**修改評分門檻從 8 降為 6**：

```bash
# 檔案：rag-orchestrator/services/knowledge_import_service.py
# Line 1001

修改前：
"is_acceptable": 是否可接受（true/false，分數 >= 8 為可接受）

修改後：
"is_acceptable": 是否可接受（true/false，分數 >= 6 為可接受）
```

重啟服務：
```bash
docker-compose restart rag-orchestrator
```

### 短期改進（1 小時）

實現「跳過質量評估」選項，給用戶選擇權

### 長期優化（2-3 小時）

實現三級制評分，更合理的質量控制

---

## 數據統計

### 當前狀況（門檻 = 8）

| 質量分數 | 比例 | 狀態 |
|---------|------|------|
| 9-10 分 | ~10% | ✅ 接受 |
| 8 分 | ~10% | ✅ 接受 |
| 6-7 分 | ~50% | ❌ 拒絕 |
| 4-5 分 | ~20% | ❌ 拒絕 |
| 1-3 分 | ~10% | ❌ 拒絕 |

**接受率**: ~20%（太低！）

### 修改後（門檻 = 6）

| 質量分數 | 比例 | 狀態 |
|---------|------|------|
| 9-10 分 | ~10% | ✅ 接受 |
| 8 分 | ~10% | ✅ 接受 |
| 6-7 分 | ~50% | ✅ 接受 |
| 4-5 分 | ~20% | ❌ 拒絕 |
| 1-3 分 | ~10% | ❌ 拒絕 |

**接受率**: ~70%（合理）

---

## 監控建議

匯入後檢查：

```sql
-- 檢查審核佇列中的質量分布
SELECT
    CASE
        WHEN (generation_reasoning::jsonb->>'quality_score')::int >= 8 THEN '8-10分'
        WHEN (generation_reasoning::jsonb->>'quality_score')::int >= 6 THEN '6-7分'
        ELSE '5分以下'
    END as quality_range,
    status,
    COUNT(*) as count
FROM ai_generated_knowledge_candidates
WHERE generation_reasoning IS NOT NULL
GROUP BY quality_range, status
ORDER BY quality_range DESC;
```

---

**問題建立日期**: 2025-11-18
**影響程度**: 🔴 高
**建議優先級**: P0（立即處理）
