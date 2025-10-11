# 回測系統品質增強整合方案

**目標：** 將 `test_scoring_quality.py` 的進階評估功能整合到現有的 `/backtest` 回測系統中

---

## 📋 現狀分析

### 現有回測系統

**位置：** `scripts/knowledge_extraction/backtest_framework.py`

**評估方式：**
```python
def evaluate_answer(self, test_scenario, system_response):
    # 1. 分類匹配檢查 (0.3分)
    category_match = (expected_category == actual_intent)

    # 2. 關鍵字覆蓋率 (0.4分)
    keyword_ratio = matched_keywords / total_keywords

    # 3. 信心度檢查 (0.3分)
    confidence >= 0.7

    # 總分 >= 0.6 視為通過
```

**優點：**
- ✅ 快速執行
- ✅ 不需要額外 API 呼叫
- ✅ 支援多意圖檢測
- ✅ 有直觀的優化建議

**限制：**
- ⚠️ 無法評估答案真實品質
- ⚠️ 關鍵字匹配過於簡單
- ⚠️ 無法評估完整性
- ⚠️ 無法評估排序品質 (NDCG)

---

### 新建品質測試系統

**位置：** `test_scoring_quality.py`

**評估方式：**
```python
async def evaluate_answer_quality_with_llm(
    self, question, answer, expected_intent
):
    # 使用 GPT-4o-mini 評估：
    # 1. 相關性 (Relevance): 1-5
    # 2. 完整性 (Completeness): 1-5
    # 3. 準確性 (Accuracy): 1-5
    # 4. 意圖匹配 (Intent Match): 1-5
    # 5. 綜合評分 (Overall): 1-5

# NDCG 排序品質評估
ndcg = calculate_ndcg(results, relevance_scores, k=3)
```

**優點：**
- ✅ 真實評估答案品質
- ✅ 提供詳細理由
- ✅ 計算 NDCG 排序指標
- ✅ 識別「排序悖論」問題

**限制：**
- ⚠️ 需要 OpenAI API 費用
- ⚠️ 執行時間較長
- ⚠️ 需要控制速率限制

---

## 🎯 整合方案

### **方案 A：雙模式回測（推薦）**

在現有回測中新增**詳細模式**選項：

```python
class BacktestFramework:
    def __init__(
        self,
        base_url: str = "http://localhost:8100",
        vendor_id: int = 1,
        quality_mode: str = "basic"  # ← 新增參數
    ):
        self.quality_mode = quality_mode
        # basic: 現有評估
        # detailed: LLM 品質評估
        # hybrid: 兩者結合
```

#### 執行流程

```
┌─────────────────────────────────────┐
│ 回測開始                             │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│ 基礎評估 (Basic)                     │
│ • 分類匹配                           │
│ • 關鍵字覆蓋                          │
│ • 信心度檢查                          │
│ • 執行速度快                          │
└─────────────────────────────────────┘
                 ↓
      [質量模式選擇]
                 ↓
        ┌───────┴───────┐
        │               │
        ↓               ↓
┌──────────────┐  ┌─────────────────┐
│ Basic Mode   │  │ Detailed Mode   │
│ 完成         │  │ 繼續 LLM 評估    │
└──────────────┘  └─────────────────┘
                         ↓
              ┌─────────────────────┐
              │ LLM 品質評估         │
              │ • 相關性 (1-5)       │
              │ • 完整性 (1-5)       │
              │ • 準確性 (1-5)       │
              │ • 意圖匹配 (1-5)     │
              │ • NDCG 計算         │
              └─────────────────────┘
                         ↓
              ┌─────────────────────┐
              │ 完整報告             │
              └─────────────────────┘
```

---

### **實施細節**

#### 1. 擴展 `backtest_framework.py`

```python
# 新增方法
async def evaluate_answer_quality_detailed(
    self,
    test_scenario: Dict,
    system_response: Dict
) -> Dict:
    """使用 LLM 進行詳細品質評估"""

    # 1. 執行基礎評估（保持向後相容）
    basic_eval = self.evaluate_answer(test_scenario, system_response)

    # 2. 如果是 detailed 或 hybrid 模式，執行 LLM 評估
    if self.quality_mode in ['detailed', 'hybrid']:
        question = test_scenario.get('test_question', '')
        answer = system_response.get('answer', '')
        expected_intent = test_scenario.get('expected_category', '')

        # 呼叫 LLM 評估
        quality_eval = await self.llm_evaluate_answer(
            question, answer, expected_intent
        )

        # 3. 整合評估結果
        return {
            'basic_eval': basic_eval,
            'quality_eval': quality_eval,
            'overall_score': self._calculate_hybrid_score(basic_eval, quality_eval),
            'passed': self._determine_pass_status(basic_eval, quality_eval)
        }

    return {'basic_eval': basic_eval, 'passed': basic_eval['passed']}

async def llm_evaluate_answer(
    self,
    question: str,
    answer: str,
    expected_intent: str
) -> Dict:
    """使用 LLM 評估答案品質"""

    prompt = f"""請評估以下問答的品質（1-5分，5分最佳）：

問題：{question}
預期意圖：{expected_intent}
答案：{answer}

請從以下維度評分：
1. 相關性 (Relevance): 答案是否直接回答問題？
2. 完整性 (Completeness): 答案是否完整涵蓋問題所問？
3. 準確性 (Accuracy): 答案內容是否準確可靠？
4. 意圖匹配 (Intent Match): 答案是否符合預期意圖？

請以 JSON 格式回覆：
{{
    "relevance": <1-5>,
    "completeness": <1-5>,
    "accuracy": <1-5>,
    "intent_match": <1-5>,
    "overall": <1-5>,
    "reasoning": "簡短說明評分理由"
}}"""

    try:
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️  LLM 評估失敗: {e}")
        return {
            'relevance': 0,
            'completeness': 0,
            'accuracy': 0,
            'intent_match': 0,
            'overall': 0,
            'reasoning': f"評估失敗: {str(e)}"
        }

def _calculate_hybrid_score(self, basic_eval: Dict, quality_eval: Dict) -> float:
    """計算混合評分"""
    # 權重：基礎評分 40%，LLM 評分 60%
    basic_score = basic_eval['score']
    quality_score = quality_eval['overall'] / 5.0  # 標準化到 0-1

    return 0.4 * basic_score + 0.6 * quality_score

def _determine_pass_status(self, basic_eval: Dict, quality_eval: Dict) -> bool:
    """判定是否通過"""
    hybrid_score = self._calculate_hybrid_score(basic_eval, quality_eval)

    # 混合模式：任一方式通過即可，但綜合分數低於 0.5 則失敗
    if self.quality_mode == 'hybrid':
        return (basic_eval['passed'] or quality_eval['overall'] >= 3) and hybrid_score >= 0.5

    # 詳細模式：以 LLM 評估為準
    if self.quality_mode == 'detailed':
        return quality_eval['overall'] >= 3 and quality_eval['completeness'] >= 3

    # 基礎模式：現有邏輯
    return basic_eval['passed']
```

#### 2. 新增 NDCG 計算

```python
def calculate_ndcg_for_results(self, results: List[Dict]) -> Dict:
    """計算所有測試的平均 NDCG"""

    import math

    def calculate_ndcg(relevance_scores: List[float], k: int = 3) -> float:
        """計算單個測試的 NDCG@K"""
        if not relevance_scores or len(relevance_scores) == 0:
            return 0.0

        # DCG
        dcg = 0.0
        for i, score in enumerate(relevance_scores[:k], 1):
            dcg += (2 ** score - 1) / math.log2(i + 1)

        # IDCG
        ideal_scores = sorted(relevance_scores, reverse=True)[:k]
        idcg = 0.0
        for i, score in enumerate(ideal_scores, 1):
            idcg += (2 ** score - 1) / math.log2(i + 1)

        return dcg / idcg if idcg > 0 else 0.0

    # 計算每個測試的 NDCG
    ndcg_scores = []
    for result in results:
        if 'quality_eval' in result:
            # 使用 LLM 評估的相關性分數
            relevance = result['quality_eval'].get('relevance', 0)
            ndcg_scores.append(relevance)

    if ndcg_scores:
        avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) / 5.0  # 標準化到 0-1
        return {
            'avg_ndcg': avg_ndcg,
            'count': len(ndcg_scores)
        }

    return {'avg_ndcg': 0.0, 'count': 0}
```

#### 3. 更新報告生成

```python
def generate_report(self, results: List[Dict], output_path: str):
    """生成增強版回測報告"""

    # ... 現有統計 ...

    # 如果有 LLM 評估，計算額外指標
    has_quality_eval = any('quality_eval' in r for r in results)

    if has_quality_eval:
        # 計算品質分數
        quality_scores = [
            r['quality_eval'] for r in results
            if 'quality_eval' in r
        ]

        avg_relevance = sum(q['relevance'] for q in quality_scores) / len(quality_scores)
        avg_completeness = sum(q['completeness'] for q in quality_scores) / len(quality_scores)
        avg_accuracy = sum(q['accuracy'] for q in quality_scores) / len(quality_scores)
        avg_intent_match = sum(q['intent_match'] for q in quality_scores) / len(quality_scores)
        avg_overall = sum(q['overall'] for q in quality_scores) / len(quality_scores)

        # 計算 NDCG
        ndcg_stats = self.calculate_ndcg_for_results(results)

        # 輸出到報告
        f.write("\n" + "="*60 + "\n")
        f.write("品質評估統計 (LLM)\n")
        f.write("="*60 + "\n")
        f.write(f"平均相關性：{avg_relevance:.2f}/5\n")
        f.write(f"平均完整性：{avg_completeness:.2f}/5\n")
        f.write(f"平均準確性：{avg_accuracy:.2f}/5\n")
        f.write(f"平均意圖匹配：{avg_intent_match:.2f}/5\n")
        f.write(f"平均綜合評分：{avg_overall:.2f}/5\n")
        f.write(f"平均 NDCG：{ndcg_stats['avg_ndcg']:.3f}\n\n")
```

---

### **前端整合**

#### 更新 `BacktestView.vue`

```vue
<!-- 新增品質分數顯示 -->
<div v-if="statistics.quality_enabled" class="quality-stats">
  <h3>📊 答案品質統計</h3>
  <div class="quality-grid">
    <div class="quality-item">
      <span class="label">相關性</span>
      <span class="value">{{ statistics.avg_relevance }}/5</span>
    </div>
    <div class="quality-item">
      <span class="label">完整性</span>
      <span class="value">{{ statistics.avg_completeness }}/5</span>
    </div>
    <div class="quality-item">
      <span class="label">準確性</span>
      <span class="value">{{ statistics.avg_accuracy }}/5</span>
    </div>
    <div class="quality-item">
      <span class="label">NDCG</span>
      <span class="value">{{ statistics.avg_ndcg }}</span>
    </div>
  </div>
</div>

<!-- 在詳情 Modal 中顯示品質評分 -->
<div v-if="selectedResult.quality_eval" class="detail-section quality-section">
  <h3>🎯 LLM 品質評估</h3>
  <table class="quality-table">
    <tr>
      <td>相關性 (Relevance)</td>
      <td>
        <span class="score-stars">{{ getStars(selectedResult.quality_eval.relevance) }}</span>
        {{ selectedResult.quality_eval.relevance }}/5
      </td>
    </tr>
    <tr>
      <td>完整性 (Completeness)</td>
      <td>
        <span class="score-stars">{{ getStars(selectedResult.quality_eval.completeness) }}</span>
        {{ selectedResult.quality_eval.completeness }}/5
      </td>
    </tr>
    <tr>
      <td>準確性 (Accuracy)</td>
      <td>
        <span class="score-stars">{{ getStars(selectedResult.quality_eval.accuracy) }}</span>
        {{ selectedResult.quality_eval.accuracy }}/5
      </td>
    </tr>
    <tr>
      <td>意圖匹配 (Intent Match)</td>
      <td>
        <span class="score-stars">{{ getStars(selectedResult.quality_eval.intent_match) }}</span>
        {{ selectedResult.quality_eval.intent_match }}/5
      </td>
    </tr>
  </table>
  <div class="quality-reasoning">
    <strong>評分理由：</strong>
    <p>{{ selectedResult.quality_eval.reasoning }}</p>
  </div>
</div>
```

```javascript
methods: {
  getStars(score) {
    const fullStars = Math.floor(score);
    const halfStar = score % 1 >= 0.5 ? 1 : 0;
    const emptyStars = 5 - fullStars - halfStar;

    return '★'.repeat(fullStars) +
           (halfStar ? '☆' : '') +
           '☆'.repeat(emptyStars);
  }
}
```

---

## 🚀 實施步驟

### 階段 1：後端整合（1-2 天）

1. ✅ 在 `backtest_framework.py` 中新增 `quality_mode` 參數
2. ✅ 實作 `llm_evaluate_answer()` 方法
3. ✅ 實作 `calculate_ndcg()` 方法
4. ✅ 更新 `generate_report()` 輸出品質指標
5. ✅ 新增環境變數控制：
   ```bash
   BACKTEST_QUALITY_MODE=hybrid  # basic, detailed, hybrid
   ```

### 階段 2：API 擴展（半天）

在 `knowledge-admin/backend/app.py` 中：

```python
@app.get("/api/backtest/results")
async def get_backtest_results(
    status_filter: str = "all",
    limit: int = 50,
    offset: int = 0
):
    # ... 現有邏輯 ...

    # 新增品質統計
    if has_quality_data:
        statistics['quality_enabled'] = True
        statistics['avg_relevance'] = calculate_avg('relevance')
        statistics['avg_completeness'] = calculate_avg('completeness')
        statistics['avg_accuracy'] = calculate_avg('accuracy')
        statistics['avg_ndcg'] = calculate_ndcg()

    return {
        'results': results,
        'total': total,
        'statistics': statistics
    }
```

### 階段 3：前端更新（1 天）

1. ✅ 更新 `BacktestView.vue` 顯示品質統計卡片
2. ✅ 在測試詳情 Modal 中顯示 LLM 評分
3. ✅ 新增星級評分顯示
4. ✅ 新增品質趨勢圖表（可選）

### 階段 4：測試與優化（半天）

1. ✅ 執行小規模測試（10-20 條）
2. ✅ 驗證評分準確性
3. ✅ 調整權重和閾值
4. ✅ 優化執行速度（批次處理）

---

## 📈 預期效果

### 基礎模式 (Basic)
- **執行時間：** 50 條測試 ~3-5 分鐘
- **成本：** $0
- **適用場景：** 日常回測、CI/CD

### 詳細模式 (Detailed)
- **執行時間：** 50 條測試 ~10-15 分鐘
- **成本：** ~$0.50-1.00 (使用 GPT-4o-mini)
- **適用場景：** 深度分析、系統優化

### 混合模式 (Hybrid) - **推薦**
- **執行時間：** 50 條測試 ~8-12 分鐘
- **成本：** ~$0.50-1.00
- **適用場景：** 平衡速度和品質

---

## 💰 成本估算

**使用 GPT-4o-mini**：
- 輸入：~300 tokens/問題
- 輸出：~150 tokens/回答
- 單次評估：~$0.0006 (300 × 0.15 + 150 × 0.6) / 1M
- 100 條測試：~$0.06
- 500 條測試：~$0.30

**非常划算！** ✅

---

## 🎯 關鍵優勢

1. **向後相容** - 現有回測仍可正常運作
2. **漸進式採用** - 可選擇啟用詳細評估
3. **成本可控** - 只在需要時使用 LLM
4. **深度洞察** - 真實評估答案品質
5. **可操作** - 提供明確的優化方向

---

## 📚 相關文檔

- [評分品質分析報告](./SCORING_QUALITY_ANALYSIS.md)
- [回測框架原始碼](../scripts/knowledge_extraction/backtest_framework.py)
- [前端回測介面](../knowledge-admin/frontend/src/views/BacktestView.vue)

---

**下一步：** 實施階段 1 - 後端整合

**預計完成時間：** 2-3 天
