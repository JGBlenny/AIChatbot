# 🤖 RAG 系統實作計畫

## 📋 專案概述

本文件規劃 AIChatbot 的增強型 RAG (Retrieval-Augmented Generation) 系統，包含意圖識別、信心度評估、答案優化、外部 API 整合等功能。

---

## 🎯 系統目標

1. **智能問答**: 自動回答使用者問題，提供準確的答案
2. **動態路由**: 根據問題類型，決定走知識檢索或 API 呼叫
3. **品質保證**: 評估答案信心度，低信心度問題記錄並轉人工
4. **持續學習**: 收集對話數據，持續優化知識庫
5. **系統整合**: 與現有系統 API 整合，提供實時資料查詢

---

## 📊 整體架構

```
使用者問題
    ↓
┌─────────────────────────────────────────┐
│  RAG Orchestrator (協調器)               │
│  Port: 8100                             │
└─────────────────────────────────────────┘
    ↓
┌───────────────────┐
│ 1. 意圖識別 & 路由 │
└─────────┬─────────┘
          ↓
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────┐     ┌──────┐
│ RAG │     │ API  │
│檢索 │     │呼叫  │
└──┬──┘     └───┬──┘
   │            │
   └─────┬──────┘
         ↓
┌──────────────────┐
│ 2. 信心度評估     │
└─────────┬────────┘
          ↓
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌──────┐   ┌────────┐
│直接  │   │優化/   │
│回覆  │   │記錄    │
└──────┘   └────────┘
```

---

## 🗓️ 實作階段規劃

### ✅ Phase 1: 基礎架構 (已完成)

**狀態**: ✅ 已完成

**內容**:
- ✅ Embedding API (Port 5001)
- ✅ 知識管理系統 (Port 8000, 8080)
- ✅ PostgreSQL + pgvector
- ✅ Redis 快取
- ✅ Docker Compose 部署

---

### 🚀 Phase 2: 增強 RAG 核心功能 (進行中)

**狀態**: 🚀 實作中

**目標**: 建立基礎的意圖分類、信心度評估和問題記錄系統

#### 2.1 RAG Orchestrator 服務

**功能**:
- 統一的對話入口
- 整合意圖分類、RAG 檢索、信心度評估
- RESTful API

**技術棧**:
- Python 3.11 + FastAPI
- OpenAI API (GPT-4o-mini)
- PostgreSQL (對話記錄)

**API 端點**:
```
POST /api/v1/chat              # 對話入口
GET  /api/v1/conversations     # 對話記錄
GET  /api/v1/unclear-questions # 未釐清問題
POST /api/v1/feedback          # 使用者反饋
GET  /api/v1/health            # 健康檢查
GET  /api/v1/stats             # 統計資訊
```

#### 2.2 意圖分類系統

**功能**:
- 自動識別問題類型 (知識查詢/資料查詢/操作執行/混合)
- 提取關鍵字和子類別
- 決定處理路徑

**實作方式**:
- 使用 OpenAI Function Calling
- 配置檔案定義意圖類型
- 支援自定義規則

**輸出範例**:
```json
{
  "intent_type": "knowledge",
  "sub_category": "退租流程",
  "keywords": ["退租", "流程", "申請"],
  "requires_api": false,
  "confidence": 0.92
}
```

#### 2.3 信心度評估系統

**功能**:
- 評估檢索結果品質
- 多維度評分 (相似度、數量、完整性)
- 決策邏輯 (直接回覆/優化/記錄)

**評估維度**:
1. **向量相似度分數** (0-1)
   - \> 0.85: 高信心度
   - 0.70-0.85: 中等信心度
   - < 0.70: 低信心度

2. **檢索結果數量**
   - 3+ 個相關結果: 高信心
   - 1-2 個結果: 中等信心
   - 0 個結果: 低信心

3. **關鍵字匹配度**
   - 問題關鍵字出現在結果中的比例

4. **語義完整性**
   - LLM 評估結果是否完整回答問題

**決策邏輯**:
```python
if similarity_score > 0.85 and results_count >= 2:
    → 直接回覆
elif 0.70 <= similarity_score <= 0.85:
    → 需要優化 (Phase 3)
elif similarity_score < 0.70:
    → 記錄未釐清問題 + 轉人工
```

#### 2.4 未釐清問題記錄

**功能**:
- 記錄低信心度問題
- 統計問題頻率
- 提供管理介面

**資料庫結構**:
```sql
CREATE TABLE unclear_questions (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    user_id VARCHAR(100),
    intent_type VARCHAR(50),

    -- 檢索結果
    similarity_score FLOAT,
    retrieved_docs JSONB,

    -- 統計
    frequency INTEGER DEFAULT 1,
    first_asked_at TIMESTAMP DEFAULT NOW(),
    last_asked_at TIMESTAMP DEFAULT NOW(),

    -- 處理狀態
    status VARCHAR(20) DEFAULT 'pending',
    assigned_to VARCHAR(100),
    resolved_at TIMESTAMP,
    resolution_note TEXT,

    -- 建議答案
    suggested_answers TEXT[],

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_unclear_status ON unclear_questions(status);
CREATE INDEX idx_unclear_frequency ON unclear_questions(frequency DESC);
```

#### 2.5 對話記錄系統

**資料庫結構**:
```sql
CREATE TABLE conversation_logs (
    id SERIAL PRIMARY KEY,
    conversation_id UUID DEFAULT gen_random_uuid(),
    user_id VARCHAR(100),

    -- 問題
    question TEXT NOT NULL,
    intent_type VARCHAR(50),
    sub_category VARCHAR(100),
    keywords TEXT[],

    -- 檢索結果
    retrieved_docs JSONB,
    similarity_scores FLOAT[],
    confidence_score FLOAT,

    -- 答案
    final_answer TEXT,
    answer_source VARCHAR(50), -- 'knowledge', 'api', 'llm_enhanced', 'unclear'
    processing_time_ms INTEGER,

    -- 反饋
    user_rating INTEGER, -- 1-5
    user_feedback TEXT,
    is_resolved BOOLEAN DEFAULT true,
    escalated_to_human BOOLEAN DEFAULT false,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_conv_user ON conversation_logs(user_id);
CREATE INDEX idx_conv_intent ON conversation_logs(intent_type);
CREATE INDEX idx_conv_created ON conversation_logs(created_at DESC);
```

#### 2.6 配置檔案

**intents.yaml** - 意圖定義:
```yaml
intents:
  - name: "退租流程"
    type: "knowledge"
    keywords: ["退租", "解約", "搬離", "終止合約"]
    confidence_threshold: 0.80

  - name: "租約查詢"
    type: "data_query"
    keywords: ["租約", "合約", "到期", "期限"]
    api_required: true
    api_endpoint: "lease_system"
    confidence_threshold: 0.75

  - name: "帳務查詢"
    type: "data_query"
    keywords: ["帳單", "費用", "繳費", "金額", "收據"]
    api_required: true
    api_endpoint: "billing_system"
    confidence_threshold: 0.75

  - name: "設備報修"
    type: "action"
    keywords: ["報修", "壞了", "故障", "維修", "不能用"]
    api_required: true
    api_endpoint: "maintenance_system"
    confidence_threshold: 0.80
```

**交付物**:
- ✅ RAG Orchestrator 服務 (FastAPI)
- ✅ 意圖分類 API
- ✅ 信心度評估邏輯
- ✅ 未釐清問題記錄功能
- ✅ 對話記錄資料庫
- ✅ 配置檔案系統
- ✅ API 文件

**預計完成時間**: 2-3 天

---

### 📝 Phase 3: LLM 答案優化 (規劃中)

**狀態**: 📋 規劃待執行

**目標**: 使用 LLM 將檢索結果重組成更好的答案

#### 3.1 答案生成引擎

**功能**:
- 整合多個檢索結果
- 使用 LLM 重組答案
- 保持一致的語氣和格式

**實作方式**:
```python
# Prompt 範本
prompt_template = """
你是 JGB 包租代管的專業客服助理。

使用者問題：{question}

相關知識庫內容：
{retrieved_knowledge}

請根據以上資訊回答使用者的問題。

要求：
1. 答案要完整、準確
2. 使用友善、專業的語氣
3. 如果需要步驟，請條列清楚
4. 如果有相關文件或連結，請提供
5. 如果資訊不足，請誠實說明並建議下一步
"""
```

**優化策略**:
1. **簡單問題**: 直接返回檢索結果，不經過 LLM
2. **複雜問題**: 使用 LLM 整合多個來源
3. **混合問題**: 結合 API 數據 + 知識庫

#### 3.2 答案品質評估

**功能**:
- 評估生成答案的品質
- 檢查答案完整性和準確性
- 自動標記需要人工審核的答案

**評估指標**:
- 答案長度合理性
- 是否包含關鍵資訊
- 語氣是否一致
- 是否有幻覺 (hallucination)

#### 3.3 Prompt 工程與優化

**功能**:
- A/B 測試不同 Prompt
- 追蹤 Prompt 效果
- 版本管理

**Prompt 庫**:
```yaml
prompts:
  - id: "customer_service_v1"
    name: "客服回答 v1"
    template: "..."
    metrics:
      avg_rating: 4.2
      usage_count: 1500

  - id: "customer_service_v2"
    name: "客服回答 v2 (更友善)"
    template: "..."
    metrics:
      avg_rating: 4.5
      usage_count: 800
```

#### 3.4 多輪對話支援

**功能**:
- 記住對話上下文
- 處理追問和澄清
- 多輪對話狀態管理

**實作**:
```python
# 對話狀態
{
  "conversation_id": "uuid",
  "user_id": "user123",
  "turns": [
    {
      "question": "我想退租",
      "answer": "退租流程...",
      "intent": "退租流程"
    },
    {
      "question": "需要提前多久通知？",  # 追問
      "context": ["退租流程"],
      "answer": "需要提前 30 天通知..."
    }
  ]
}
```

**交付物**:
- 答案生成引擎
- Prompt 管理系統
- 答案品質評估
- 多輪對話支援
- A/B 測試框架

**預計開始時間**: Phase 2 完成後
**預計完成時間**: 3-4 天

---

### 🔌 Phase 4: 外部系統整合 (規劃中)

**狀態**: 📋 規劃待執行

**目標**: 與現有系統 API 整合，提供實時資料查詢和操作

#### 4.1 API 呼叫框架

**功能**:
- 統一的 API 呼叫介面
- 錯誤處理和重試機制
- 超時控制
- 結果快取

**API 配置**:
```yaml
apis:
  lease_system:
    base_url: "https://api.jgb.com/lease"
    endpoints:
      get_contract:
        path: "/contracts/{user_id}"
        method: "GET"
        timeout: 5000
        cache_ttl: 300

  billing_system:
    base_url: "https://api.jgb.com/billing"
    endpoints:
      get_invoice:
        path: "/invoices/{user_id}"
        method: "GET"

  maintenance_system:
    base_url: "https://api.jgb.com/maintenance"
    endpoints:
      create_ticket:
        path: "/tickets"
        method: "POST"
```

#### 4.2 工作流引擎

**功能**:
- 定義複雜的業務流程
- 條件式分支
- 並行處理
- 錯誤回滾

**工作流範例**:
```yaml
workflows:
  - name: "early_termination_check"
    description: "提前退租檢查"
    trigger:
      intent: "退租流程"
      keywords: ["提前"]

    steps:
      - id: "step1"
        action: "call_api"
        api: "lease_system.get_contract"
        params:
          user_id: "{user_id}"
        output: "contract_info"

      - id: "step2"
        action: "conditional_branch"
        condition: "contract_info.contract_type"
        branches:
          monthly:
            next: "step3_monthly"
          yearly:
            next: "step3_yearly"

      - id: "step3_monthly"
        action: "rag_retrieve"
        query: "月租退租流程"

      - id: "step3_yearly"
        action: "conditional_check"
        condition: "contract_info.early_termination_allowed"
        branches:
          true:
            action: "rag_retrieve"
            query: "年租提前解約流程"
          false:
            action: "rag_retrieve"
            query: "年租正常到期流程"
```

#### 4.3 資料整合與轉換

**功能**:
- API 回應格式轉換
- 資料驗證
- 敏感資訊脫敏

**範例**:
```python
# API 回應
api_response = {
  "contract_id": "CT20250001",
  "start_date": "2024-01-01",
  "end_date": "2025-12-31",
  "monthly_rent": 25000,
  "tenant_name": "王小明",
  "phone": "0912345678"
}

# 轉換後整合到答案
formatted_data = """
您的租約資訊：
- 合約編號：CT20250001
- 租期：2024-01-01 至 2025-12-31
- 月租金：NT$ 25,000
- 承租人：王小明
"""
```

#### 4.4 錯誤處理與降級

**策略**:
1. **API 呼叫失敗**:
   - 重試 3 次
   - 失敗後降級使用知識庫通用答案

2. **超時處理**:
   - 設定 5 秒超時
   - 超時返回「系統忙碌，請稍後再試」

3. **資料缺失**:
   - 返回部分資訊
   - 標記哪些資訊無法取得

**交付物**:
- API 呼叫框架
- 工作流引擎
- API 配置系統
- 錯誤處理機制
- 整合測試

**預計開始時間**: Phase 3 完成後
**預計完成時間**: 4-5 天

---

### 🎨 Phase 5: 管理平台與監控 (規劃中)

**狀態**: 📋 規劃待執行

**目標**: 提供管理後台，方便人工審核和系統監控

#### 5.1 未釐清問題管理後台

**功能**:
- 問題列表與篩選
- 問題詳情查看
- 處理動作 (新增知識/調整內容/標記已解決)
- 批次處理

**介面設計**:
```
┌─────────────────────────────────────────────────┐
│ 未釐清問題管理                                    │
├─────────────────────────────────────────────────┤
│ 篩選: [全部▼] [待處理▼] [日期範圍]  搜尋: [___]  │
├──────┬────────────────┬──────┬─────┬──────┬─────┤
│ 頻率 │ 問題            │ 類別  │ 信心 │ 狀態  │ 操作 │
├──────┼────────────────┼──────┼─────┼──────┼─────┤
│  15  │ IOT門鎖一直嗶...│ 設備  │ 0.62│ 待處理│[詳情]│
│   8  │ 提前退租違約金..│ 合約  │ 0.68│ 待處理│[詳情]│
│   5  │ 代收包裹服務... │ 服務  │ 0.71│ 處理中│[詳情]│
└──────┴────────────────┴──────┴─────┴──────┴─────┘
```

**處理流程**:
```
1. 點擊「詳情」查看問題
   ↓
2. 查看檢索結果和建議答案
   ↓
3. 選擇處理方式：
   ├─ 新增知識到知識庫
   ├─ 調整現有知識內容
   ├─ 標記為已解決
   └─ 標記為誤判
   ↓
4. 相同問題自動更新答案
```

#### 5.2 對話記錄與分析

**功能**:
- 對話記錄查詢
- 統計分析圖表
- 使用者反饋追蹤

**統計指標**:
- 每日問題數量
- 問題類型分布
- 平均信心度
- 平均回應時間
- 使用者滿意度 (評分)
- 轉人工比例

**圖表範例**:
```
問題類型分布 (本週)
┌─────────────────────┐
│ 知識查詢    45%  ████│
│ 資料查詢    30%  ███ │
│ 操作執行    15%  ██  │
│ 未釐清      10%  █   │
└─────────────────────┘

信心度分布
┌─────────────────────┐
│ 高 (>0.85)  60%  ████│
│ 中 (0.7-0.85) 25% ██ │
│ 低 (<0.7)   15%  █   │
└─────────────────────┘
```

#### 5.3 監控儀表板

**功能**:
- 實時系統狀態
- API 健康檢查
- 效能監控
- 錯誤追蹤

**監控項目**:
1. **服務健康**:
   - RAG Orchestrator 狀態
   - Embedding API 狀態
   - 資料庫連線狀態
   - Redis 狀態

2. **效能指標**:
   - 平均回應時間
   - P95 回應時間
   - QPS (每秒查詢數)
   - 快取命中率

3. **錯誤監控**:
   - API 錯誤率
   - 超時次數
   - 異常日誌

#### 5.4 知識庫品質追蹤

**功能**:
- 知識使用頻率
- 知識效果評估
- 知識更新建議

**追蹤指標**:
```sql
-- 知識效果統計
SELECT
    kb.title,
    COUNT(cl.id) as usage_count,
    AVG(cl.user_rating) as avg_rating,
    AVG(cl.confidence_score) as avg_confidence
FROM knowledge_base kb
JOIN conversation_logs cl ON cl.retrieved_docs::jsonb @> jsonb_build_array(kb.id)
WHERE cl.created_at > NOW() - INTERVAL '30 days'
GROUP BY kb.id, kb.title
ORDER BY usage_count DESC;
```

#### 5.5 A/B 測試平台

**功能**:
- 不同策略的 A/B 測試
- 效果對比分析
- 自動選擇最佳策略

**測試項目**:
- 不同 Prompt 模板
- 不同信心度閾值
- 不同檢索策略

**交付物**:
- 管理後台 (Vue.js)
- 監控儀表板
- 統計分析 API
- A/B 測試框架
- 使用者手冊

**預計開始時間**: Phase 4 完成後
**預計完成時間**: 5-6 天

---

## 📊 各階段依賴關係

```
Phase 1 (已完成)
    ↓
Phase 2 (進行中)
    ├─→ Phase 3 (LLM 優化)
    └─→ Phase 4 (API 整合)
            ↓
        Phase 5 (管理平台)
```

**說明**:
- Phase 2 是核心，必須先完成
- Phase 3 和 4 可以並行開發
- Phase 5 依賴 Phase 2, 3, 4 的資料

---

## 🎯 成功指標 (KPI)

### Phase 2 目標:
- ✅ 意圖分類準確率 > 90%
- ✅ 高信心度問題占比 > 60%
- ✅ 未釐清問題完整記錄率 = 100%
- ✅ API 回應時間 < 2 秒

### Phase 3 目標:
- 答案品質評分 > 4.0/5.0
- 使用者滿意度 > 80%
- LLM 優化後提升率 > 20%

### Phase 4 目標:
- API 整合成功率 > 95%
- 混合問題處理準確率 > 85%
- 工作流執行成功率 > 98%

### Phase 5 目標:
- 未釐清問題處理時間 < 24 小時
- 知識庫更新頻率 > 每週 5 條
- 系統可用性 > 99.5%

---

## 🔧 技術棧總覽

### RAG Orchestrator
- **語言**: Python 3.11
- **框架**: FastAPI
- **AI**: OpenAI API (GPT-4o-mini)
- **資料庫**: PostgreSQL 16
- **快取**: Redis 7

### 管理後台 (Phase 5)
- **框架**: Vue.js 3
- **UI**: Element Plus
- **圖表**: ECharts
- **HTTP**: Axios

### 基礎設施
- **容器化**: Docker Compose
- **監控**: Prometheus + Grafana (可選)
- **日誌**: ELK Stack (可選)

---

## 📁 專案結構 (完整版)

```
AIChatbot/
├── rag-orchestrator/              # Phase 2-4
│   ├── app.py                     # 主服務
│   ├── requirements.txt
│   ├── Dockerfile
│   │
│   ├── routers/                   # API 路由
│   │   ├── __init__.py
│   │   ├── chat.py               # 對話 API
│   │   ├── conversations.py      # 對話記錄
│   │   ├── unclear_questions.py  # 未釐清問題
│   │   ├── feedback.py           # 反饋 API
│   │   └── admin.py              # 管理 API
│   │
│   ├── services/                  # 核心服務
│   │   ├── __init__.py
│   │   ├── intent_classifier.py  # 意圖分類 (Phase 2)
│   │   ├── rag_engine.py         # RAG 檢索 (Phase 2)
│   │   ├── confidence_evaluator.py # 信心度評估 (Phase 2)
│   │   ├── llm_enhancer.py       # LLM 優化 (Phase 3)
│   │   ├── api_caller.py         # API 呼叫 (Phase 4)
│   │   └── workflow_engine.py    # 工作流 (Phase 4)
│   │
│   ├── models/                    # 資料模型
│   │   ├── __init__.py
│   │   ├── conversation.py
│   │   ├── unclear_question.py
│   │   └── workflow.py
│   │
│   ├── config/                    # 配置檔案
│   │   ├── intents.yaml          # 意圖定義
│   │   ├── prompts.yaml          # Prompt 模板
│   │   ├── workflows.yaml        # 工作流定義
│   │   └── api_endpoints.yaml    # API 端點
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       └── metrics.py
│
├── rag-admin/                     # Phase 5
│   ├── backend/
│   │   ├── app.py
│   │   └── requirements.txt
│   │
│   └── frontend/
│       ├── src/
│       │   ├── views/
│       │   │   ├── UnclearQuestions.vue
│       │   │   ├── Conversations.vue
│       │   │   ├── Analytics.vue
│       │   │   └── Monitor.vue
│       │   └── App.vue
│       └── package.json
│
├── docs/
│   └── rag-system/
│       ├── RAG_IMPLEMENTATION_PLAN.md  # 本文件
│       ├── PHASE2_GUIDE.md             # Phase 2 詳細指南
│       ├── PHASE3_GUIDE.md             # Phase 3 詳細指南
│       ├── PHASE4_GUIDE.md             # Phase 4 詳細指南
│       ├── PHASE5_GUIDE.md             # Phase 5 詳細指南
│       └── API_REFERENCE.md            # API 參考文件
│
└── docker-compose.yml             # 更新加入 RAG Orchestrator
```

---

## 📚 相關文件

- [系統架構文件](../architecture/SYSTEM_ARCHITECTURE.md)
- [快速開始指南](../../QUICKSTART.md)
- [API 使用文件](../API_USAGE.md)

---

## 🤝 開發流程

### 1. Phase 2 開發流程

```bash
# 1. 建立 rag-orchestrator 服務
cd AIChatbot
mkdir -p rag-orchestrator/{routers,services,models,config,utils}

# 2. 實作核心功能
# - 意圖分類
# - 信心度評估
# - 未釐清問題記錄

# 3. 測試
pytest rag-orchestrator/tests/

# 4. 整合到 docker-compose
docker-compose up -d rag-orchestrator

# 5. 驗證
curl http://localhost:8100/api/v1/health
```

### 2. 後續 Phase 開發

每個 Phase 開發完成後：
1. ✅ 功能測試
2. ✅ 整合測試
3. ✅ 效能測試
4. ✅ 文件更新
5. ✅ Git commit & push
6. ✅ 部署到生產環境

---

## 📅 時間規劃

| Phase | 內容 | 預計時間 | 狀態 |
|-------|------|---------|------|
| Phase 1 | 基礎架構 | - | ✅ 已完成 |
| Phase 2 | 增強 RAG | 2-3 天 | 🚀 進行中 |
| Phase 3 | LLM 優化 | 3-4 天 | 📋 待執行 |
| Phase 4 | API 整合 | 4-5 天 | 📋 待執行 |
| Phase 5 | 管理平台 | 5-6 天 | 📋 待執行 |
| **總計** | | **14-18 天** | |

---

## ✅ 檢查清單

### Phase 2 完成條件:
- [ ] RAG Orchestrator 服務啟動成功
- [ ] 意圖分類 API 測試通過
- [ ] 信心度評估邏輯正確
- [ ] 未釐清問題記錄功能正常
- [ ] 對話記錄資料庫建立
- [ ] 配置檔案系統運作正常
- [ ] API 文件完整
- [ ] 單元測試覆蓋率 > 80%
- [ ] 整合測試通過
- [ ] 效能測試達標 (< 2 秒)

### Phase 3-5 待執行項目:
- [ ] Phase 3: LLM 答案優化
- [ ] Phase 4: 外部 API 整合
- [ ] Phase 5: 管理平台開發

---

## 📝 變更記錄

| 日期 | 版本 | 說明 | 作者 |
|------|------|------|------|
| 2025-10-09 | 1.0 | 初始版本，完整規劃 Phase 1-5 | Claude Code |

---

**維護者**: Claude Code
**最後更新**: 2025-10-09
**下次審查**: Phase 2 完成後

---

## 🔗 相關連結

- [GitHub Repository](https://github.com/JGBlenny/AIChatbot)
- [系統架構圖](../architecture/SYSTEM_ARCHITECTURE.md)
- [OpenAI Function Calling 文件](https://platform.openai.com/docs/guides/function-calling)
- [pgvector 文件](https://github.com/pgvector/pgvector)
