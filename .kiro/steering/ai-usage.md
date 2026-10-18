# AI Usage Steering

> **相關文件**：技術棧請參考 [tech.md](./tech.md)

## 1. 模型選擇策略

### 模型選擇矩陣

| 任務類型 | 模型 | Temperature | 原因 |
|---------|------|-------------|------|
| **複雜推理** | gpt-4o | 0.7 | 需更強推理能力 |
| **測試題生成** | gpt-4o | 0.8 | 多樣性、創造性 |
| **文件轉換**（Chat） | gpt-4o | 0.3 | 複雜文件需強推理、高確定性 |
| **對話回合**（`AGENT_MODEL`） | 程式回退鏈 `AGENT_MODEL`→`OPENAI_MODEL`→`gpt-4o-mini`（`services/agent/runtime.py`） | — | `AgentRuntime` 的模型；另有 `AGENT_REASONING_EFFORT`。採用哪個模型是決策：見 `.claude/DECISIONS.md` DSP-075／DSP-080 |
| **圖片辨識**（`IMAGE_RECOGNITION_MODEL`） | — | — | 報修照片前處理 |
| **文件抽取**（`DOCUMENT_EXTRACTION_MODEL`） | — | — | 附件抽取 |
| **查詢改寫**（`QUERY_REWRITE_MODEL`） | gpt-4o-mini | 0 | ⚠️ 程式預設與 prod compose 皆為 **0**，非 0.3 |

🔴 **2026-09-12：「答案優化」與「意圖分類」兩列已刪**——`llm_answer_optimizer.py` 與
`intent_classifier.py` 於 2026-09-11 隨舊 REST 對話鏈刪除，`ENABLE_ANSWER_SYNTHESIS`／
`INTENT_CLASSIFIER_*` 全 repo 零程式讀者。⛔ 不要照舊表估成本或選模型。

### 模型特性

**gpt-4o-mini**（預設首選）：
- 成本：$0.15 / 1M prompt tokens，$0.60 / 1M completion tokens
- 適用：一般低成本任務
- 優勢：速度快、成本低、品質足夠

**gpt-4o**（複雜任務）：
- 成本：$2.50 / 1M prompt tokens，$10.00 / 1M completion tokens
- 適用：需更強推理能力的任務

## 2. Temperature 設定指南

### Temperature 範圍

🔴 **2026-10-18：** 原「知識完善迴圈」各任務（智能分類、聚類、SOP 生成、知識生成、分類選擇、群組選擇）的溫度表已刪——迴圈執行器已不在（`rag-orchestrator/services/knowledge_completion_loop/` 只剩 `__init__.py`、`embedding_client.py`、`create_missing_indexes.sql`）。現行各呼叫點的溫度以程式為準（例：`services/query_rewriter.py` 的 `QUERY_REWRITE_TEMPERATURE` 預設 0；`services/document_converter_service.py` 為 0.3）。

### 設定原則

| Temperature | 特性 | 適用任務 |
|------------|------|---------|
| 0.0-0.3 | 高度確定性、低隨機性 | 分類、提取、選擇 |
| 0.4-0.6 | 平衡確定性與創造性 | 摘要、重寫 |
| 0.7-0.9 | 高創造性、多樣性 | 生成、創作 |
| 1.0+ | 極高隨機性 | 不建議使用 |

## 3. 成本控制策略

### 成本追蹤

🔴 **2026-10-18：** 原 `OpenAICostTracker`／`PRICING`／`BudgetExceededError` 範例已刪——這些符號在 repo 零程式碼（`grep -rn OpenAICostTracker rag-orchestrator` 無命中）。

現行做法：
- 對話回合用量由 `services/usage_metering.py` 計價（`DEFAULT_PRICING`，可用 env `LLM_PRICING_PATH` 覆蓋）並寫入 `usage_events`。
- 圖片辨識與文件線的成本直接寫入資料表 `openai_cost_tracking`（`services/image_recognition_service.py`、`services/agent/mcp_facade.py` 內的 `INSERT INTO openai_cost_tracking`）。


**成本優化**：
- 優先使用 gpt-4o-mini
- 批次處理降低 API 調用次數
- 設定合理的批次大小限制


## 4. API 重試機制

### 重試策略

**使用 tenacity 庫**：
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),        # 最多重試 3 次
    wait=wait_exponential(min=1, max=10),  # 指數退避：1s, 2s, 4s, 8s
    reraise=True
)
def call_openai_api(...):
    # OpenAI API 調用
```

### 錯誤處理

**常見錯誤類型**：
1. **Rate Limit**：速率限制（429）→ 重試
2. **Timeout**：請求超時 → 重試
3. **Server Error**：伺服器錯誤（500-599）→ 重試
4. **Invalid API Key**：API 金鑰錯誤 → 不重試，直接失敗
5. **Invalid Request**：請求格式錯誤 → 不重試，記錄錯誤

**重試日誌**：
```python
# 記錄重試資訊
print(f"⚠️  API 調用失敗，將在 {wait_time}s 後重試（{attempt}/3）")
print(f"   錯誤類型：{error_type}")
print(f"   錯誤訊息：{error_message}")
```

## 5. Prompt 工程

🔴 **2026-10-18：** 原「智能分類／聚類／SOP 生成 Prompt」範例屬已刪的知識完善迴圈，程式碼中已無對應 prompt（`grep -rn "適度聚類\|applicable_questions" rag-orchestrator` 無命中），整段刪除。現行對話 prompt 見 `services/agent/` 與 [dialogue.md](./dialogue.md)。

## 6. 成本估算

🔴 **2026-10-18：** 原「單次迭代成本估算／預算建議」表（以知識完善迴圈為前提）已刪。實際成本以 `openai_cost_tracking` 表與 `services/usage_metering.py` 為準。


## 7. 環境變數配置

### 必需環境變數

```bash
# OpenAI API 金鑰（必需）
export OPENAI_API_KEY="sk-..."

# 資料庫配置（可選，有預設值）
export DB_HOST="postgres"
export DB_PORT="5432"
export DB_NAME="aichatbot_admin"
export DB_USER="aichatbot"
export DB_PASSWORD="aichatbot_password"

# RAG API 基礎 URL（可選；knowledge-admin/backend/app.py 預設與 docker-compose.prod.yml 皆為 http://rag-orchestrator:8100）
export RAG_API_URL="http://rag-orchestrator:8100"
```

### API 金鑰安全

**安全原則**：
- 透過環境變數傳遞，不得硬編碼
- 不記錄到日誌檔案
- 使用 `.env` 檔案管理（不納入版控）
- 生產環境透過 Docker Compose 或 K8s Secret 注入

## 核心原則總結

### 1. 成本優先，品質為本
- 優先使用 gpt-4o-mini（90% 任務）
- 批次處理降低 API 調用次數

### 2. Temperature 分層策略
- 確定性任務：0.1-0.3
- 創造性任務：0.7-0.8
- 避免極端值（0 或 1.0+）

### 3. 健全的錯誤處理
- 使用 tenacity 進行重試
- 指數退避策略
- 區分可重試與不可重試錯誤

### 4. Prompt 工程最佳實踐
- 清晰的任務定義
- 具體的範例與標準
- 結構化輸出（JSON）
- 避免模糊與歧義

### 5. 成本追蹤與透明
- 成本寫入 `openai_cost_tracking`、計價見 `services/usage_metering.py`
