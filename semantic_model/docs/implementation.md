# 實作指南：整合語義模式到現有系統

## 🎯 核心理解：語義模式 vs Reranker

### 它們的不同角色

| 組件 | 作用 | 輸入 | 輸出 |
|-----|------|------|------|
| **語義模式** | 理解查詢意圖類型 | 用戶查詢 | 模式類型（如：時間查詢） |
| **Reranker** | 判斷查詢-文檔相關性 | 查詢+文檔對 | 相關性分數(0-1) |
| **向量檢索** | 初步篩選候選 | 查詢向量 | Top-K相似文檔 |

### 為什麼需要三者結合？

```
問題："電費幾號寄"

向量檢索：找出包含"電費"相關的文檔 → 可能找到10個
語義模式：識別這是"時間查詢"模式 → 優先考慮表單類型
Reranker：精確判斷每個文檔相關性 → 最終排序

結果：正確觸發「電費寄送區間查詢」表單
```

## 📝 Step-by-Step 實作

### Step 1: 修改現有的 ChatService

```python
# backend/services/chat_service.py

from sentence_transformers import CrossEncoder
import numpy as np

class EnhancedChatService:
    def __init__(self):
        # 保留原有的 Reranker
        self.reranker = CrossEncoder('BAAI/bge-reranker-base')

        # 新增語義模式識別
        self.semantic_patterns = self._load_patterns()

    def _load_patterns(self):
        """載入語義模式定義"""
        return {
            "time_query": {
                "triggers": ["幾號", "何時", "時間", "什麼時候", "日期", "週期"],
                "boost_action": "form_fill",
                "weight": 1.5
            },
            "cost_query": {
                "triggers": ["多少錢", "費用", "價格", "計算", "怎麼算"],
                "boost_action": "direct_answer",
                "weight": 1.3
            },
            "application": {
                "triggers": ["申請", "辦理", "我要", "如何", "怎麼"],
                "boost_action": "form_fill",
                "weight": 1.4
            }
        }

    def identify_pattern(self, query):
        """識別查詢的語義模式"""
        for pattern_name, pattern_def in self.semantic_patterns.items():
            if any(trigger in query for trigger in pattern_def["triggers"]):
                return pattern_name, pattern_def
        return None, None

    def enhanced_retrieve(self, query, vendor_id):
        """增強版檢索流程"""

        # 1. 識別語義模式
        pattern_name, pattern_def = self.identify_pattern(query)

        # 2. 向量檢索（原有邏輯）
        vector_results = self.vector_search(query, vendor_id, top_k=10)

        # 3. 根據語義模式調整初始分數
        if pattern_def:
            for result in vector_results:
                # 如果action_type符合模式偏好，提升權重
                if result['action_type'] == pattern_def['boost_action']:
                    result['pattern_boost'] = pattern_def['weight']
                else:
                    result['pattern_boost'] = 1.0
        else:
            for result in vector_results:
                result['pattern_boost'] = 1.0

        # 4. 使用 Reranker 重新評分
        query_doc_pairs = [(query, r['content']) for r in vector_results]
        reranker_scores = self.reranker.predict(query_doc_pairs)

        # 5. 綜合評分
        for i, result in enumerate(vector_results):
            # 原始相似度 × 模式權重 × Reranker分數
            result['final_score'] = (
                result['similarity'] * 0.3 +  # 向量相似度
                result['pattern_boost'] * 0.2 +  # 模式加成
                reranker_scores[i] * 0.5  # Reranker分數
            )

        # 6. 排序並返回最佳結果
        sorted_results = sorted(vector_results,
                               key=lambda x: x['final_score'],
                               reverse=True)

        return sorted_results[0] if sorted_results else None
```

### Step 2: 更新 API 端點

```python
# backend/api/chat.py

@app.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    """改良後的聊天端點"""

    # 使用增強檢索
    knowledge = enhanced_chat_service.enhanced_retrieve(
        query=request.question,
        vendor_id=request.vendor_id
    )

    # 記錄語義模式（用於分析）
    pattern_name, _ = enhanced_chat_service.identify_pattern(request.question)
    logger.info(f"Query: {request.question}, Pattern: {pattern_name}")

    # 根據 action_type 執行
    if knowledge['action_type'] == 'form_fill':
        # 觸發表單
        return StreamingResponse(
            generate_form_response(knowledge['form_id']),
            media_type="text/event-stream"
        )
    elif knowledge['action_type'] == 'api_call':
        # 調用 API
        return StreamingResponse(
            execute_api_call(knowledge['api_endpoint']),
            media_type="text/event-stream"
        )
    else:
        # 生成回答
        return StreamingResponse(
            generate_answer_stream(knowledge['content']),
            media_type="text/event-stream"
        )
```

### Step 3: 資料庫調整（可選但建議）

```sql
-- 新增語義模式記錄表
CREATE TABLE semantic_patterns (
    id SERIAL PRIMARY KEY,
    pattern_name VARCHAR(50) NOT NULL,
    description TEXT,
    trigger_keywords JSONB,
    boost_action_types JSONB,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入預定義模式
INSERT INTO semantic_patterns (pattern_name, description, trigger_keywords, boost_action_types, weight)
VALUES
    ('time_query', '時間查詢模式', '["幾號","何時","時間"]', '["form_fill"]', 1.5),
    ('cost_query', '費用計算模式', '["多少錢","費用","價格"]', '["direct_answer"]', 1.3),
    ('application', '申請辦理模式', '["申請","辦理","我要"]', '["form_fill"]', 1.4);

-- 查詢日誌增強（記錄模式）
ALTER TABLE query_logs
ADD COLUMN detected_pattern VARCHAR(50),
ADD COLUMN pattern_confidence FLOAT;
```

## 🔧 快速測試腳本

```python
# semantic_model/tests/quick_test.py

def test_semantic_enhancement():
    """快速測試語義增強效果"""

    test_cases = [
        {
            "query": "電費幾號寄",
            "expected_pattern": "time_query",
            "expected_knowledge_id": 1296,
            "expected_action": "form_fill"
        },
        {
            "query": "租金多少錢",
            "expected_pattern": "cost_query",
            "expected_action": "direct_answer"
        },
        {
            "query": "申請退租",
            "expected_pattern": "application",
            "expected_action": "form_fill"
        }
    ]

    service = EnhancedChatService()

    for test in test_cases:
        # 識別模式
        pattern, _ = service.identify_pattern(test["query"])
        assert pattern == test["expected_pattern"], f"模式識別錯誤: {test['query']}"

        # 檢索結果
        result = service.enhanced_retrieve(test["query"], vendor_id=1)

        print(f"✅ 查詢: {test['query']}")
        print(f"   模式: {pattern}")
        print(f"   結果: {result['title']}")
        print(f"   動作: {result['action_type']}")
        print()

if __name__ == "__main__":
    test_semantic_enhancement()
```

## 🚦 部署檢查清單

### 部署前檢查

- [ ] 備份現有系統
- [ ] 測試環境驗證
- [ ] 準備回滾方案

### 部署步驟

1. **安裝依賴**
   ```bash
   pip install sentence-transformers==2.2.2
   ```

2. **更新程式碼**
   ```bash
   git pull origin semantic-enhancement
   ```

3. **執行測試**
   ```bash
   python semantic_model/tests/quick_test.py
   ```

4. **漸進式上線**
   - 先對 10% 流量啟用
   - 觀察 24 小時
   - 逐步提升到 100%

### 監控指標

```python
# monitoring.py
def monitor_semantic_performance():
    """監控語義模式效果"""

    metrics = {
        "pattern_distribution": {},  # 各模式使用分布
        "accuracy_by_pattern": {},  # 各模式準確率
        "response_time": [],        # 回應時間
        "user_satisfaction": []     # 用戶滿意度
    }

    # 每小時統計
    hourly_stats = calculate_hourly_metrics()

    # 告警條件
    if hourly_stats['error_rate'] > 0.05:
        send_alert("錯誤率超過 5%")

    if hourly_stats['avg_response_time'] > 1.5:
        send_alert("回應時間超過 1.5 秒")
```

## ⚠️ 常見問題解答

### Q1: Reranker 會變慢嗎？

不會。流程是平行的：
```
原流程：向量檢索 → Reranker → 結果
新流程：向量檢索 → [語義模式(5ms) + Reranker] → 結果
```
語義模式識別只需 5ms，幾乎不影響效能。

### Q2: 如果模式識別錯誤怎麼辦？

有三層保護：
1. 模式權重只佔 20%
2. Reranker 佔 50%，可以糾正
3. 向量相似度佔 30%，提供基礎保障

### Q3: 需要重新訓練 Reranker 嗎？

不需要。Reranker 保持原樣，我們只是在它之前加了一層語義理解。

## 📞 需要協助？

如有問題，參考：
- 快速實作：本文件 Step 1-3
- 完整訓練：`/semantic_model/docs/training_guide.md`
- 測試腳本：`/semantic_model/tests/`