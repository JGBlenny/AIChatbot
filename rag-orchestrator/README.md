# 🤖 RAG Orchestrator - 智能問答協調器

RAG Orchestrator 是 AIChatbot 系統的核心智能問答引擎，負責協調意圖分類、知識檢索、信心度評估等多個服務，提供高品質的自動化客服回答。

## 📋 目錄

- [系統概述](#系統概述)
- [核心功能](#核心功能)
- [系統架構](#系統架構)
- [意圖類型](#意圖類型)
- [API 文件](#api-文件)
- [配置說明](#配置說明)
- [使用範例](#使用範例)
- [本地開發](#本地開發)

---

## 系統概述

RAG Orchestrator 是一個基於 FastAPI 的微服務，整合了以下核心能力：

1. **意圖分類**：使用 OpenAI Function Calling 自動識別使用者問題類型
2. **RAG 檢索**：基於向量相似度搜尋相關知識
3. **信心度評估**：多維度評估答案品質，決定回應策略
4. **LLM 答案優化** (Phase 3)：使用 GPT-4o-mini 優化答案，提供自然對話體驗
5. **未釐清問題管理**：記錄和追蹤低/中信心度問題

### 工作流程

```
使用者問題
    │
    ▼
┌─────────────────┐
│  意圖分類        │ ← OpenAI Function Calling
│  (11 種意圖)    │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  RAG 檢索        │ ← 向量相似度搜尋
│  (知識庫)       │    (僅對 knowledge/hybrid 類型)
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  信心度評估      │ ← 相似度 (60%) + 結果數 (20%) + 關鍵字 (20%)
│  (高/中/低)     │
└─────────────────┘
    │
    ├─► 高信心度 (≥0.70) ──► LLM 答案優化 ──► 直接回答 ✨
    │                      (GPT-4o-mini)
    │
    ├─► 中信心度 (0.50-0.70) ──► LLM 答案優化 ──► 回答 + 建議聯繫客服 + 記錄 ✨
    │                           (GPT-4o-mini)
    │
    └─► 低信心度 (<0.50) ──► 記錄未釐清問題 + 轉人工
```

---

## 核心功能

### 1. 意圖分類系統

自動識別使用者問題的意圖類型，支援 11 種意圖分類：

**知識查詢類**：
- 退租流程、租約問題、押金處理等

**資料查詢類**：
- 租約查詢、繳費記錄、帳戶資訊等

**操作執行類**：
- 租約續約、繳費操作等

**混合類**：
- 需要知識 + 資料的複雜問題

> 詳細意圖類型定義見 [config/intents.yaml](./config/intents.yaml)

### 2. RAG 檢索引擎

基於 pgvector 的向量相似度搜尋：

- **向量生成**：透過 Embedding API 生成問題向量
- **相似度搜尋**：使用餘弦距離 (`<=>`) 進行向量搜尋
- **智能過濾**：可設定相似度閾值（預設 0.65）
- **關鍵字備援**：當向量搜尋結果不足時，使用關鍵字搜尋

### 3. 信心度評估

多維度評估系統，決定最佳回應策略：

| 評估維度 | 權重 | 說明 |
|---------|------|------|
| 相似度分數 | 60% | 最高相似度結果的分數 |
| 結果數量 | 20% | 檢索到的結果數量 (歸一化) |
| 關鍵字匹配率 | 20% | 問題關鍵字與結果的匹配程度 |

**信心等級：**
- 🟢 **高信心度** (≥0.70)：LLM 優化後直接回答
- 🟡 **中信心度** (0.50-0.70)：LLM 優化後回答，附加警告並記錄
- 🔴 **低信心度** (<0.50)：記錄未釐清問題，建議轉人工

### 4. LLM 答案優化 (Phase 3) ✨

使用 GPT-4o-mini 將知識庫內容優化成自然對話：

**核心功能**：
- **自動優化**：高/中信心度答案自動經過 LLM 優化
- **Prompt Engineering**：針對不同意圖類型（知識/資料/操作）使用不同提示詞
- **Token 控制**：每次請求最多 800 tokens，避免成本失控
- **錯誤降級**：API 失敗時自動使用原始答案
- **成本追蹤**：記錄每次優化的 token 使用量

**配置選項**：
```python
{
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 800,
    "enable_optimization": True,
    "optimize_for_confidence": ["high", "medium"],
    "fallback_on_error": True
}
```

**優化效果對比**：

| 項目 | Phase 2 (原始) | Phase 3 (LLM 優化) |
|------|---------------|------------------|
| 答案來源 | 直接複製知識庫文字 | GPT-4o-mini 重組優化 |
| 語氣 | 正式、條列式 | 自然、對話式 |
| 針對性 | 顯示完整知識庫條目 | 只回答問題相關部分 |
| 用戶體驗 | ★★★☆☆ | ★★★★★ |

### 5. 未釐清問題管理

自動記錄和追蹤中/低信心度問題：

- **自動記錄**：信心度 < 0.70 時自動記錄（包含中等和低信心度）
- **頻率統計**：相同問題自動累加計數
- **狀態管理**：pending → in_progress → resolved/ignored
- **指派追蹤**：支援指派給特定人員處理
- **批次操作**：支援批次更新狀態

---

## 系統架構

### 目錄結構

```
rag-orchestrator/
├── app.py                    # FastAPI 主應用
├── requirements.txt          # Python 依賴
├── Dockerfile               # Docker 配置
│
├── routers/                 # API 路由
│   ├── chat.py              # 聊天 API
│   └── unclear_questions.py # 未釐清問題 API
│
├── services/                # 核心服務
│   ├── intent_classifier.py      # 意圖分類器
│   ├── rag_engine.py             # RAG 檢索引擎
│   ├── confidence_evaluator.py   # 信心度評估器
│   ├── llm_answer_optimizer.py   # LLM 答案優化器 (Phase 3) ✨
│   └── unclear_question_manager.py  # 未釐清問題管理器
│
├── models/                  # 資料模型
│   └── unclear_question.py  # 未釐清問題模型
│
├── config/                  # 配置檔案
│   └── intents.yaml         # 意圖定義
│
└── utils/                   # 工具函數
```

### 服務依賴

```
RAG Orchestrator (Port 8100)
    │
    ├─► PostgreSQL (Port 5432)
    │   └─ knowledge_base 表
    │   └─ conversation_logs 表
    │   └─ unclear_questions 表
    │
    ├─► Embedding API (Port 5001)
    │   └─ 向量生成服務
    │
    └─► OpenAI API
        ├─ GPT-4o-mini (意圖分類)
        └─ GPT-4o-mini (答案優化 - Phase 3) ✨
```

---

## 意圖類型

系統支援 11 種預定義意圖類型，可透過 `config/intents.yaml` 配置：

### 知識查詢類 (knowledge)

| 意圖名稱 | 關鍵字範例 | 需要 API |
|---------|-----------|---------|
| 退租流程 | 退租、解約、搬離 | ❌ |
| 租約問題 | 租約、合約、期限 | ❌ |
| 押金處理 | 押金、退還、扣除 | ❌ |
| 維修報修 | 維修、報修、壞掉 | ❌ |
| 繳費方式 | 繳費、付款、轉帳 | ❌ |
| 設施使用 | 設施、健身房、停車 | ❌ |

### 資料查詢類 (data_query)

| 意圖名稱 | 關鍵字範例 | 需要 API |
|---------|-----------|---------|
| 租約查詢 | 查租約、到期日 | ✅ lease_system |
| 繳費記錄 | 繳費記錄、付款歷史 | ✅ payment_system |
| 個人資料 | 個人資料、聯絡方式 | ✅ user_system |

### 操作執行類 (action)

| 意圖名稱 | 關鍵字範例 | 需要 API |
|---------|-----------|---------|
| 租約續約 | 續約、延長 | ✅ lease_system |

### 混合類 (hybrid)

需要結合知識查詢和資料查詢的複雜問題。

---

## API 文件

### 主要端點

| 方法 | 端點 | 說明 |
|------|------|------|
| POST | `/api/v1/message` | 多業者聊天 (推薦) |
| POST | `/api/v1/chat/stream` | 流式聊天 (即時反饋) |
| GET | `/api/v1/conversations` | 取得對話記錄列表 |
| GET | `/api/v1/conversations/{id}` | 取得特定對話詳情 |
| POST | `/api/v1/conversations/{id}/feedback` | 提交反饋 |

> ⚠️ **注意**: `/api/v1/chat` 端點已於 2025-10-21 移除。請使用 `/api/v1/message` 或 `/api/v1/chat/stream` 替代。
| GET | `/api/v1/unclear-questions` | 取得未釐清問題列表 |
| GET | `/api/v1/unclear-questions/{id}` | 取得問題詳情 |
| PUT | `/api/v1/unclear-questions/{id}` | 更新問題狀態 |
| DELETE | `/api/v1/unclear-questions/{id}` | 刪除問題 |
| GET | `/api/v1/unclear-questions-stats` | 取得統計資訊 |
| GET | `/api/v1/unclear-questions-search` | 搜尋問題 |
| POST | `/api/v1/unclear-questions-batch-update` | 批次更新 |

### 完整 API 文件

啟動服務後，存取 http://localhost:8100/docs 查看互動式 API 文件。

---

## 配置說明

### 環境變數

```bash
# OpenAI API Key (必需)
OPENAI_API_KEY=sk-proj-xxx

# 資料庫連線 (必需)
DB_HOST=postgres
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password

# Embedding API URL (必需)
EMBEDDING_API_URL=http://embedding-api:5000/api/v1/embeddings

# 服務配置 (可選)
HOST=0.0.0.0
PORT=8100
```

### 意圖配置 (intents.yaml)

可自定義意圖類型：

```yaml
intents:
  - name: "自定義意圖名稱"
    type: "knowledge"  # knowledge, data_query, action, hybrid
    keywords: ["關鍵字1", "關鍵字2"]
    confidence_threshold: 0.80
    api_required: false  # 是否需要外部 API
    api_endpoint: "endpoint_name"  # API 端點名稱
    api_action: "action_name"  # API 操作名稱
```

### 信心度閾值配置

在 `services/confidence_evaluator.py` 中可調整：

```python
config = {
    "high_confidence_threshold": 0.85,    # 高信心度閾值
    "medium_confidence_threshold": 0.70,  # 中信心度閾值
    "similarity_weight": 0.6,             # 相似度權重
    "result_count_weight": 0.2,           # 結果數權重
    "keyword_match_weight": 0.2           # 關鍵字權重
}
```

---

## 使用範例

### 1. 基本問答（含 Phase 3 LLM 優化 + 多業者支持）✨

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "退租要怎麼辦理？",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "user123"
  }'
```

**回應範例（LLM 優化後的自然對話）：**

```json
{
  "question": "退租要怎麼辦理？",
  "answer": "退租的流程如下：\n\n### 退租步驟\n\n1. **提前通知**：在預定的退租日期前30天，請以書面方式通知房東。\n2. **繳清費用**：確保所有的租金及水電費已經繳清。\n3. **房屋檢查**：與房東約定一個時間，進行房屋的檢查。\n4. **押金退還**：如果房屋狀況良好，房東應在7個工作天內退還押金。\n\n### 注意事項\n- 記得提前30天通知房東。\n- 所有費用必須繳清。\n- 房屋需恢復至原來的狀態。\n\n如果有其他問題，隨時可以詢問！\n\n⚠️ 注意：此答案信心度為中等（0.53），建議您聯繫客服人員進一步確認。\n您的問題已記錄，我們會持續改善答案品質。",
  "confidence_score": 0.53,
  "confidence_level": "medium",
  "intent": {
    "intent_type": "knowledge",
    "intent_name": "退租流程",
    "confidence": 0.9,
    "keywords": ["退租", "辦理"]
  },
  "retrieved_docs": [
    {
      "id": 2,
      "title": "退租流程說明",
      "content": "...",
      "similarity": 0.66
    }
  ],
  "processing_time_ms": 7725,
  "requires_human": true,
  "unclear_question_id": 3
}
```

**Phase 3 優化效果**：
- ✨ 答案經過 GPT-4o-mini 優化，更加自然流暢
- 🎯 自動提取關鍵資訊，避免顯示完整知識庫條目
- 💬 使用對話式語氣，提升用戶體驗
- ⚠️ 中等信心度自動附加警告訊息並記錄

### 2. 低信心度問題

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "請問這個月的電費怎麼計算？",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "user456"
  }'
```

**回應範例：**

```json
{
  "question": "請問這個月的電費怎麼計算？",
  "answer": "抱歉，我對這個問題不太確定如何回答。\n\n您的問題已經記錄下來，我們會盡快處理。\n如需立即協助，請聯繫客服人員。",
  "confidence_score": 0.45,
  "confidence_level": "low",
  "intent": {...},
  "retrieved_docs": [],
  "processing_time_ms": 180,
  "requires_human": true,
  "unclear_question_id": 123
}
```

### 3. 查詢未釐清問題

```bash
# 取得待處理問題
curl "http://localhost:8100/api/v1/unclear-questions?status=pending&order_by=frequency&limit=10"

# 更新問題狀態
curl -X PUT http://localhost:8100/api/v1/unclear-questions/123 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "resolved",
    "resolution_note": "已新增電費計算相關知識",
    "suggested_answers": ["電費採實際使用度數計算..."]
  }'

# 批次更新
curl -X POST http://localhost:8100/api/v1/unclear-questions-batch-update \
  -H "Content-Type: application/json" \
  -d '{
    "question_ids": [123, 124, 125],
    "status": "in_progress",
    "assigned_to": "admin"
  }'
```

### 4. 取得統計資訊

```bash
curl http://localhost:8100/api/v1/unclear-questions-stats
```

**回應範例：**

```json
{
  "total_unclear_questions": 45,
  "by_status": {
    "pending": 20,
    "in_progress": 15,
    "resolved": 8,
    "ignored": 2
  },
  "top_frequent_questions": [
    {
      "id": 123,
      "question": "電費怎麼計算？",
      "frequency": 12,
      "status": "in_progress"
    }
  ],
  "avg_processing_time_ms": 230
}
```

### 5. 提交反饋

```bash
curl -X POST http://localhost:8100/api/v1/conversations/789/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "rating": 5,
    "feedback": "回答很清楚，解決了我的問題"
  }'
```

---

## 本地開發

### 前置需求

- Python 3.11+
- PostgreSQL 16+ (with pgvector)
- Redis 7+ (for Embedding API)
- OpenAI API Key

### 安裝依賴

```bash
cd rag-orchestrator
pip install -r requirements.txt
```

### 設定環境變數

```bash
# 建立 .env 檔案
cat > .env << EOF
OPENAI_API_KEY=sk-proj-your-key-here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aichatbot_admin
DB_USER=aichatbot
DB_PASSWORD=aichatbot_password
EMBEDDING_API_URL=http://localhost:5001/api/v1/embeddings
EOF
```

### 啟動服務

```bash
# 確保 PostgreSQL 和 Embedding API 已啟動
docker-compose up -d postgres redis embedding-api

# 啟動 RAG Orchestrator
python app.py
```

服務將在 http://localhost:8100 啟動。

### 開發模式

使用 uvicorn 的 reload 功能：

```bash
uvicorn app:app --host 0.0.0.0 --port 8100 --reload
```

### 測試

```bash
# 健康檢查
curl http://localhost:8100/api/v1/health

# 統計資訊
curl http://localhost:8100/api/v1/stats

# 互動式 API 文件
open http://localhost:8100/docs
```

---

## 資料庫表結構

### conversation_logs 表

記錄所有對話內容和處理結果：

```sql
CREATE TABLE conversation_logs (
    id SERIAL PRIMARY KEY,
    conversation_id UUID DEFAULT gen_random_uuid(),
    user_id VARCHAR(100),
    question TEXT NOT NULL,
    intent_type VARCHAR(50),
    sub_category VARCHAR(100),
    keywords TEXT[],
    retrieved_docs JSONB,
    similarity_scores FLOAT[],
    confidence_score FLOAT,
    api_called BOOLEAN DEFAULT false,
    api_endpoints TEXT[],
    api_responses JSONB,
    final_answer TEXT,
    answer_source VARCHAR(50),
    processing_time_ms INTEGER,
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    user_feedback TEXT,
    is_resolved BOOLEAN DEFAULT true,
    escalated_to_human BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### unclear_questions 表

記錄低信心度的未釐清問題：

```sql
CREATE TABLE unclear_questions (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    user_id VARCHAR(100),
    intent_type VARCHAR(50),
    similarity_score FLOAT,
    retrieved_docs JSONB,
    frequency INTEGER DEFAULT 1,
    first_asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    assigned_to VARCHAR(100),
    resolved_at TIMESTAMP,
    resolution_note TEXT,
    suggested_answers TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 效能監控

### 關鍵指標

- **回應時間**：目標 < 500ms (含 RAG 檢索)
- **信心度分布**：高 > 70%, 中 < 20%, 低 < 10%
- **準確率**：使用者評分 >= 4 的比例 > 80%
- **轉人工率**：< 15%

### 監控端點

```bash
# 服務狀態
curl http://localhost:8100/api/v1/health

# 統計資訊
curl http://localhost:8100/api/v1/stats
```

---

## 故障排除

### 問題 1：OpenAI API 連線失敗

**症狀**：意圖分類失敗

**解決方法**：
```bash
# 檢查 API Key
echo $OPENAI_API_KEY

# 測試連線
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### 問題 2：Embedding API 連線失敗

**症狀**：RAG 檢索失敗

**解決方法**：
```bash
# 檢查 Embedding API 狀態
curl http://localhost:5001/api/v1/health

# 檢查環境變數
echo $EMBEDDING_API_URL
```

### 問題 3：資料庫連線失敗

**症狀**：啟動時報錯 "Connection refused"

**解決方法**：
```bash
# 檢查 PostgreSQL 狀態
docker-compose ps postgres

# 測試連線
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c "SELECT 1;"
```

### 問題 4：intents.yaml 載入失敗

**症狀**：啟動時報錯 "Config file not found"

**解決方法**：
```bash
# 檢查檔案是否存在
ls -la config/intents.yaml

# 檢查 YAML 格式
python -c "import yaml; yaml.safe_load(open('config/intents.yaml'))"
```

---

## 後續規劃

### ✅ Phase 3: LLM 答案優化（已完成）
- ✅ 使用 GPT-4o-mini 重新組織和優化答案
- ✅ 提供更自然的對話體驗
- ✅ Token 追蹤與成本控制
- ✅ 錯誤自動降級處理
- 📋 支援多輪對話（待實作）

### Phase 4: 外部 API 整合
- 租約系統整合
- 繳費系統整合
- 維修工單系統整合

### Phase 5: 監控儀表板
- 即時監控服務狀態
- 對話品質分析
- 知識庫覆蓋率分析

詳見 [RAG 系統實作計畫](../docs/rag-system/RAG_IMPLEMENTATION_PLAN.md)

---

## 參考文件

- [RAG 系統實作計畫](../docs/rag-system/RAG_IMPLEMENTATION_PLAN.md)
- [系統架構文件](../docs/architecture/SYSTEM_ARCHITECTURE.md)
- [API 完整文件](http://localhost:8100/docs) (啟動後存取)
- [知識管理系統說明](../knowledge-admin/README.md)

---

**維護者**: Claude Code
**最後更新**: 2025-10-10
**版本**: 1.1.0 (Phase 2 + Phase 3 LLM 優化)
