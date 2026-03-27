# AI Usage Steering

> **相關文件**：技術棧請參考 [tech.md](./tech.md)

## 1. 模型選擇策略

### 模型選擇矩陣

| 任務類型 | 模型 | Temperature | 原因 |
|---------|------|-------------|------|
| **智能分類** | gpt-4o-mini | 0.3 | 確定性高、成本低 |
| **聚類** | gpt-4o-mini | 0.3 | 確定性高、成本低 |
| **SOP 生成** | gpt-4o-mini | 0.7 | 創造性、成本可控 |
| **知識生成** | gpt-4o-mini | 0.7 | 創造性、成本可控 |
| **分類選擇** | gpt-4o-mini | 0.1 | 極高確定性 |
| **群組選擇** | gpt-4o-mini | 0.1 | 極高確定性 |
| **複雜推理** | gpt-4o | 0.7 | 需更強推理能力 |
| **測試題生成** | gpt-4o | 0.8 | 多樣性、創造性 |

### 模型特性

**gpt-4o-mini**（預設首選）：
- 成本：$0.15 / 1M prompt tokens，$0.60 / 1M completion tokens
- 適用：90% 的任務（分類、聚類、生成）
- 優勢：速度快、成本低、品質足夠

**gpt-4o**（複雜任務）：
- 成本：$2.50 / 1M prompt tokens，$10.00 / 1M completion tokens
- 適用：需更強推理能力的任務
- 使用時機：知識完善迴圈中較少使用

## 2. Temperature 設定指南

### Temperature 範圍

```python
# 確定性任務（Deterministic）
temperature = 0.1  # 分類選擇、群組選擇
temperature = 0.3  # 智能分類、聚類

# 創造性任務（Creative）
temperature = 0.7  # SOP 生成、知識生成
temperature = 0.8  # 測試題生成（需更多多樣性）
```

### 設定原則

| Temperature | 特性 | 適用任務 |
|------------|------|---------|
| 0.0-0.3 | 高度確定性、低隨機性 | 分類、提取、選擇 |
| 0.4-0.6 | 平衡確定性與創造性 | 摘要、重寫 |
| 0.7-0.9 | 高創造性、多樣性 | 生成、創作 |
| 1.0+ | 極高隨機性 | 不建議使用 |

## 3. 成本控制策略

### OpenAICostTracker

**核心功能**：
```python
class OpenAICostTracker:
    PRICING = {
        "gpt-4o-mini": {
            "prompt": 0.150,      # $0.15 / 1M tokens
            "completion": 0.600   # $0.60 / 1M tokens
        },
        "gpt-4o": {
            "prompt": 2.50,       # $2.50 / 1M tokens
            "completion": 10.00   # $10.00 / 1M tokens
        }
    }
```

**成本追蹤**：
1. 記錄每次 API 調用的 token 使用量
2. 計算成本（基於最新定價表）
3. 累計迴圈總成本
4. 持久化到 `openai_cost_tracking` 表

### 預算控制

**預算限制**：
```python
tracker = OpenAICostTracker(
    loop_id=1,
    budget_limit_usd=10.0  # 設定預算上限 $10
)

# 超過預算時拋出異常
if total_cost >= budget_limit:
    raise BudgetExceededError(f"超過預算 ${budget_limit}")

# 達到 80% 時發送警告
if total_cost >= budget_limit * 0.8:
    send_budget_warning()
```

**成本優化**：
- 優先使用 gpt-4o-mini
- 批次處理降低 API 調用次數
- 設定合理的批次大小限制

### 批次處理策略

**知識生成批次大小**：
```python
# SOP 生成
batch_size = 5  # 每批 5 個 SOP

# 一般知識生成
batch_size = 5  # 每批 5 個知識

# 智能分類
batch_size = 50  # 每批 50 個問題（知識完善迴圈預設）
```

**批次處理原則**：
- 避免單次 API 調用處理過多資料
- 平衡速度與成本
- 支援中斷恢復（記錄已處理批次）

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

## 5. Prompt 工程最佳實踐

### 智能分類 Prompt

**目標**：將失敗案例分類為 4 種類型

**Prompt 結構**：
```python
system_prompt = """
你是一個專業的知識分類助手。

任務：將以下問題分類為 4 種類型之一：
1. sop_knowledge - SOP 業務流程知識
2. form_fill - 表單填寫流程
3. system_config - 系統操作與配置
4. api_query - API 動態查詢

分類標準：
- sop_knowledge：需多輪對話或固定流程（例如：退租流程、續約流程）
- form_fill：需填寫表單收集資訊（例如：我想找房、申請維修）
- system_config：可直接回答的單一問答（例如：如何切換團隊、忘記密碼）
- api_query：需即時查詢動態資料（例如：租金多少、合約何時到期）

請以 JSON 格式返回。
"""
```

**最佳實踐**：
- 提供清晰的分類定義與範例
- 要求結構化輸出（JSON）
- Temperature = 0.3（確保穩定性）

### 聚類 Prompt

**目標**：將相似問題聚類

**聚類原則**：
```python
system_prompt = """
聚類原則：
1. 適度聚類：只有可用同一 SOP/知識完整回答的問題才聚類
2. 每個聚類包含 2-5 個高度相關的問題
3. 選出一個代表性問題作為主問題
4. 生成簡潔的聚類名稱（如：「租金支付流程」）

避免：
- 過度聚類（將不同問題強行合併）
- 過於細分（每個問題都獨立）
"""
```

### SOP 生成 Prompt

**目標**：生成結構化 SOP 文檔

**Prompt 結構**：
```python
system_prompt = """
生成 SOP 要求：
1. 標題：簡潔明確（例如：「線上續約申請流程」）
2. 步驟：清晰、可執行、有序
3. 關鍵字：精準、避免過於籠統
4. 適用問題：列出可回答的具體問題

格式範例：
{
  "title": "線上續約申請流程",
  "steps": [
    {"step": 1, "description": "登入租客系統"},
    {"step": 2, "description": "進入「合約管理」頁面"}
  ],
  "keywords": ["續約", "合約延長", "租期續簽"],
  "applicable_questions": ["如何申請續約？", "續約需要什麼流程？"]
}
"""
```

**溫度設定**：
- Temperature = 0.7（平衡創造性與穩定性）

## 6. 成本估算與預算規劃

### 單次迭代成本估算

**假設場景**（50 題回測，40 題失敗）：

| 操作 | 模型 | Token 估算 | 成本 |
|------|------|-----------|------|
| 智能分類（40 題） | gpt-4o-mini | 20K prompt + 5K completion | $0.006 |
| 聚類（40 題 → 8 clusters） | gpt-4o-mini | 30K prompt + 8K completion | $0.010 |
| SOP 生成（5 個） | gpt-4o-mini | 10K prompt + 15K completion | $0.011 |
| 知識生成（3 個） | gpt-4o-mini | 5K prompt + 8K completion | $0.006 |
| **單次迭代總成本** | - | - | **~$0.03** |

**完整迴圈成本估算**（10 次迭代）：
- 單次迭代：$0.03
- 10 次迭代：$0.30
- 加上回測成本：$0.35-$0.50

### 預算建議

| 批次大小 | 預算建議 | 備註 |
|---------|---------|------|
| 50 題 | $0.50-$1.00 | 首批驗證 |
| 100 題 | $1.00-$2.00 | 中等批次 |
| 200 題 | $2.00-$4.00 | 大批次 |

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

# RAG API 基礎 URL（可選，預設 localhost:8100）
export RAG_API_URL="http://localhost:8100"

# 業者 ID（可選，預設 2）
export VENDOR_ID="2"

# 僅回測模式（可選，預設 false）
export BACKTEST_ONLY="false"
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
- 預算控制與警告機制
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
- 記錄每次 API 調用成本
- 迴圈級別成本彙總
- 提供成本估算工具
