# 回測品質評估系統實施完成報告

**實施日期：** 2025-10-11
**狀態：** 階段 1-2 完成，階段 3-4 進行中

---

## 📋 實施概覽

根據《RAG 評分品質深度分析與改善方案》，本次實施將 LLM 品質評估整合至現有回測系統，實現三種評估模式：

- **basic**: 快速評估（關鍵字、分類、信心度）
- **detailed**: LLM 深度品質評估（5 維度評分）
- **hybrid**: 混合模式（40% basic + 60% LLM，推薦）

---

## ✅ 階段 1: 後端框架擴展（已完成）

### 檔案修改：`scripts/knowledge_extraction/backtest_framework.py`

#### 1. 新增品質評估模式支援

```python
def __init__(
    self,
    base_url: str = "http://localhost:8100",
    vendor_id: int = 1,
    quality_mode: str = "basic"  # 新增參數
):
    self.quality_mode = quality_mode

    # 初始化 OpenAI 客戶端（detailed/hybrid 模式）
    if quality_mode in ['detailed', 'hybrid']:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️  警告：未設定 OPENAI_API_KEY，將降級為 basic 模式")
            self.quality_mode = 'basic'
        else:
            self.openai_client = OpenAI(api_key=api_key)
```

#### 2. 新增 LLM 評估方法

```python
def llm_evaluate_answer(
    self, question: str, answer: str, expected_intent: str
) -> Dict:
    """使用 LLM 評估答案品質

    Returns:
        {
            'relevance': 1-5,      # 相關性
            'completeness': 1-5,   # 完整性
            'accuracy': 1-5,       # 準確性
            'intent_match': 1-5,   # 意圖匹配
            'overall': 1-5,        # 綜合評分
            'reasoning': str       # 評分理由
        }
    """
```

**使用模型：** GPT-4o-mini
**評估成本：** ~$0.0006 per test
**評估時間：** ~2-3 秒 per test

#### 3. 新增混合評估方法

```python
def evaluate_answer_with_quality(
    self, test_scenario: Dict, system_response: Dict
) -> Dict:
    """整合基礎評估和 LLM 品質評估

    Returns:
        {
            'basic_eval': Dict,      # 基礎評估結果
            'quality_eval': Dict,    # LLM 品質評估（如啟用）
            'overall_score': float,  # 混合評分
            'passed': bool          # 通過判定
        }
    """
```

**混合評分公式：**
```python
if quality_mode == 'hybrid':
    score = 0.4 * basic_score + 0.6 * (llm_overall / 5.0)
elif quality_mode == 'detailed':
    score = llm_overall / 5.0
else:  # basic
    score = basic_score
```

#### 4. 新增 NDCG 排序品質計算

```python
def calculate_ndcg(self, results: List[Dict], k: int = 3) -> Dict:
    """計算所有測試的平均 NDCG@K

    NDCG (Normalized Discounted Cumulative Gain) 衡量排序品質
    """
```

**NDCG 公式：**
```
DCG = Σ (2^relevance - 1) / log2(i + 1)
IDCG = DCG of ideal ranking
NDCG = DCG / IDCG
```

#### 5. 更新報告生成

**新增品質統計區塊：**
- 評估測試數
- 平均相關性 (Relevance)
- 平均完整性 (Completeness)
- 平均準確性 (Accuracy)
- 平均意圖匹配 (Intent Match)
- 平均綜合評分 (Overall)
- NDCG@3 (排序品質)

**品質評級系統：**
- 🎉 優秀: ≥ 4.0
- ✅ 良好: ≥ 3.5
- ⚠️  中等: ≥ 3.0
- ❌ 需改善: < 3.0

#### 6. 環境變數支援

```bash
export BACKTEST_QUALITY_MODE="hybrid"  # basic, detailed, hybrid
export OPENAI_API_KEY="sk-..."         # LLM API key
```

---

## ✅ 階段 2: API 端點擴展（已完成）

### 檔案修改：`knowledge-admin/backend/app.py`

#### 1. 擴展 `/api/backtest/results` 端點

**新增品質資料回傳：**
```json
{
  "results": [
    {
      "test_id": 1,
      "test_question": "...",
      "score": 0.85,
      "passed": true,
      "quality": {  // 新增
        "relevance": 4.5,
        "completeness": 3.8,
        "accuracy": 4.2,
        "intent_match": 4.0,
        "quality_overall": 4.0,
        "overall_score": 0.88,
        "quality_reasoning": "..."
      }
    }
  ],
  "statistics": {
    "total_tests": 10,
    "passed_tests": 8,
    "pass_rate": 80.0,
    "avg_score": 0.75,
    "avg_confidence": 0.82,
    "quality": {  // 新增
      "count": 10,
      "avg_relevance": 3.95,
      "avg_completeness": 3.42,
      "avg_accuracy": 4.18,
      "avg_intent_match": 3.88,
      "avg_quality_overall": 3.85,
      "avg_overall_score": 0.78
    }
  }
}
```

#### 2. 新增回測執行請求模型

```python
class BacktestRunRequest(BaseModel):
    """回測執行請求模型"""
    quality_mode: Optional[str] = "basic"  # basic, detailed, hybrid
    test_type: Optional[str] = "smoke"     # smoke, full
```

#### 3. 更新 `/api/backtest/run` 端點

**支援參數：**
- `quality_mode`: 品質評估模式
- `test_type`: 測試類型

**範例請求：**
```bash
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{"quality_mode": "hybrid", "test_type": "smoke"}'
```

**回應：**
```json
{
  "success": true,
  "message": "回測已開始執行（hybrid 模式），請稍後刷新頁面查看結果",
  "quality_mode": "hybrid",
  "test_type": "smoke",
  "estimated_time": "約需 4-7 分鐘（混合評估）"
}
```

**時間估計：**
- basic: 2-3 分鐘
- hybrid: 4-7 分鐘
- detailed: 5-10 分鐘

---

## 🚧 階段 3: 前端顯示更新（進行中）

### 目標檔案：`knowledge-admin/frontend/src/views/BacktestView.vue`

### 計畫更新：

#### 1. 新增品質統計卡片

```vue
<div class="stats-container">
  <!-- 現有統計卡片 -->
  <div class="stat-card">...</div>

  <!-- 新增：品質評估統計 -->
  <div class="stat-card quality-stats" v-if="statistics.quality">
    <h3>🎯 LLM 品質評估</h3>
    <div class="quality-metrics">
      <div class="metric">
        <label>相關性</label>
        <div class="score-display">
          <span class="score">{{ statistics.quality.avg_relevance }}</span>
          <span class="rating">{{ getRating(statistics.quality.avg_relevance) }}</span>
        </div>
      </div>
      <div class="metric">
        <label>完整性</label>
        <div class="score-display">
          <span class="score">{{ statistics.quality.avg_completeness }}</span>
          <span class="rating">{{ getRating(statistics.quality.avg_completeness) }}</span>
        </div>
      </div>
      <!-- ... 其他維度 -->
    </div>
  </div>
</div>
```

#### 2. 更新詳細資訊 Modal

**顯示 5 維度品質評分：**
- 星級評分顯示（1-5 星）
- 評分理由（quality_reasoning）
- 視覺化指標（進度條）

#### 3. 新增回測配置選項

```vue
<div class="backtest-config">
  <label>品質評估模式</label>
  <select v-model="backtestConfig.quality_mode">
    <option value="basic">Basic - 快速評估</option>
    <option value="hybrid">Hybrid - 混合評估（推薦）</option>
    <option value="detailed">Detailed - LLM 深度評估</option>
  </select>

  <label>測試類型</label>
  <select v-model="backtestConfig.test_type">
    <option value="smoke">Smoke - 快速測試</option>
    <option value="full">Full - 完整測試</option>
  </select>
</div>
```

---

## 🚧 階段 4: 整合測試（待執行）

### 測試計畫：

#### 1. 單元測試
- [ ] basic 模式回測
- [ ] detailed 模式回測
- [ ] hybrid 模式回測
- [ ] NDCG 計算正確性
- [ ] 品質評分範圍驗證

#### 2. 整合測試
- [ ] API 端點回應格式
- [ ] 前端顯示正確性
- [ ] 品質統計計算準確性

#### 3. 效能測試
- [ ] 10 個測試案例執行時間
- [ ] LLM API 成本估算
- [ ] 記憶體使用量

#### 4. 用戶驗收測試
- [ ] 前端介面易用性
- [ ] 品質指標解讀清晰度
- [ ] 錯誤處理完整性

---

## 📊 預期成效

根據《評分品質分析報告》，實施後預期改善：

| 指標 | 當前 | 階段 1 | 階段 2 | 目標 |
|------|------|--------|--------|------|
| NDCG@3 | 0.958 | 0.950 | 0.960 | >0.95 |
| 相關性 | 3.83 | 4.0 | 4.1 | >4.0 |
| **完整性** | **2.92** | **3.4** | **3.7** | **>3.8** |
| 準確性 | 4.17 | 4.2 | 4.3 | >4.0 |
| 意圖匹配 | 3.83 | 3.9 | 4.0 | >4.0 |
| **綜合評分** | **3.42** | **3.7** | **3.9** | **>4.0** |

---

## 💰 成本分析

### LLM 評估成本（GPT-4o-mini）

**價格：**
- Input: $0.150 / 1M tokens
- Output: $0.600 / 1M tokens

**每次評估：**
- Input tokens: ~300
- Output tokens: ~100
- 成本: ~$0.0006

**100 次測試：**
- 成本: ~$0.06
- 時間: ~5-7 分鐘（hybrid 模式）

### 建議使用場景

| 模式 | 適用場景 | 成本 | 時間 |
|------|----------|------|------|
| **basic** | 快速驗證、開發測試 | $0 | 2-3 分 |
| **hybrid** | 日常品質監控（推薦） | $0.06 | 4-7 分 |
| **detailed** | 深度品質分析、報告 | $0.06 | 5-10 分 |

---

## 🔧 使用方式

### 1. 設定環境變數

```bash
export OPENAI_API_KEY="sk-..."
export BACKTEST_QUALITY_MODE="hybrid"  # 可選: basic, detailed, hybrid
export BACKTEST_TYPE="smoke"           # 可選: smoke, full
```

### 2. 命令列執行

```bash
# Basic 模式（預設）
python3 scripts/knowledge_extraction/backtest_framework.py

# Hybrid 模式
BACKTEST_QUALITY_MODE=hybrid python3 scripts/knowledge_extraction/backtest_framework.py

# Detailed 模式 + 完整測試
BACKTEST_QUALITY_MODE=detailed BACKTEST_TYPE=full python3 scripts/knowledge_extraction/backtest_framework.py
```

### 3. API 執行

```bash
# Basic 模式
curl -X POST http://localhost:8000/api/backtest/run

# Hybrid 模式
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{"quality_mode": "hybrid", "test_type": "smoke"}'
```

### 4. 前端執行

訪問 http://localhost:8080/#/backtest：
1. 選擇品質評估模式
2. 選擇測試類型
3. 點擊「開始回測」
4. 等待執行完成
5. 查看品質統計與詳細結果

---

## 📝 變更紀錄

### 2025-10-11
- ✅ 完成 backtest_framework.py 擴展
  - 新增三種評估模式
  - 新增 LLM 評估方法
  - 新增 NDCG 計算
  - 更新報告生成
- ✅ 完成 API 端點擴展
  - `/api/backtest/results` 支援品質資料
  - `/api/backtest/run` 支援模式選擇
  - 新增品質統計計算
- 🚧 進行中：前端顯示更新
- ⏸️  待執行：整合測試

---

## 🔗 相關文檔

- [RAG 評分品質深度分析](./SCORING_QUALITY_ANALYSIS.md)
- [回測品質整合計畫](./BACKTEST_QUALITY_INTEGRATION.md)
- [系統架構文檔](./architecture/SYSTEM_ARCHITECTURE.md)

---

**最後更新：** 2025-10-11
**實施進度：** 50% (階段 2/4 完成)
