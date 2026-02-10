# 🏗️ AIChatbot 完整對話架構圖
**最後更新**: 2026-02-04
**版本**: 1.0
**類型**: 完整架構文件（含圖示）

---

## 📊 1. 總體對話架構流程圖

```mermaid
flowchart TB
    Start([用戶訊息輸入]) --> API[POST /api/v1/message]

    API --> Step0{Step 0: 表單會話檢查}

    Step0 -->|有表單會話| FormState{表單狀態?}
    FormState -->|REVIEWING| FormReview[確認/取消/編輯]
    FormState -->|EDITING| FormEdit[收集編輯值]
    FormState -->|COLLECTING/DIGRESSION/PAUSED| FormCollect[收集欄位]

    Step0 -->|無表單會話| Step1[Step 1-3: 基礎處理]

    Step1 --> Validate[驗證業者]
    Validate --> Cache{緩存檢查}
    Cache -->|命中| CachedResponse[返回緩存結果]
    Cache -->|未命中| Intent[意圖分類]

    Intent --> Parallel{並行檢索}

    Parallel --> SOP[SOP 檢索]
    Parallel --> Knowledge[知識庫檢索]

    SOP --> Decision{智能決策}
    Knowledge --> Decision

    Decision -->|SOP 勝出| SOPFlow[SOP 流程]
    Decision -->|知識庫勝出| KnowledgeFlow[知識庫流程]
    Decision -->|都不達標| Fallback[兜底回應]

    SOPFlow --> SOPTrigger{觸發模式?}
    SOPTrigger -->|Manual| Manual[顯示內容 + 等待關鍵詞]
    SOPTrigger -->|Immediate| Immediate[顯示內容 + 詢問確認]
    SOPTrigger -->|Auto| Auto[自動觸發後續動作]

    Manual --> WaitKeyword{等待觸發詞}
    Immediate --> WaitConfirm{等待確認}
    Auto --> NextAction{後續動作}

    WaitKeyword -->|匹配| NextAction
    WaitConfirm -->|確認| NextAction

    NextAction -->|form_fill| TriggerForm[觸發表單]
    NextAction -->|api_call| CallAPI[調用 API]
    NextAction -->|form_then_api| FormThenAPI[表單→API]

    KnowledgeFlow --> KnowledgeAction{action_type?}
    KnowledgeAction -->|direct_answer| LLMOptimize[LLM 優化答案]
    KnowledgeAction -->|form_fill| KnowledgeForm[知識庫表單觸發]
    KnowledgeAction -->|api_call| KnowledgeAPI[知識庫 API 調用]

    KnowledgeForm --> KnowledgeTrigger{觸發模式?}
    KnowledgeTrigger -->|Manual| KManual[顯示知識 + 等待關鍵詞]
    KnowledgeTrigger -->|Immediate| KImmediate[顯示知識 + 詢問確認]
    KnowledgeTrigger -->|Auto| KAuto[自動觸發表單]

    TriggerForm --> FormFlow[表單流程]
    FormThenAPI --> FormFlow
    KnowledgeForm --> FormFlow
    KAuto --> FormFlow

    FormFlow --> CollectFields[收集欄位資料]
    CollectFields --> Review[審核確認]
    Review --> Submit[提交表單]
    Submit --> OnComplete{完成後動作}

    OnComplete -->|show_knowledge| ShowKnowledge[顯示知識答案]
    OnComplete -->|call_api| ExecuteAPI[執行 API]
    OnComplete -->|both| BothActions[兩者都執行]

    LLMOptimize --> InjectParams[注入業者參數]
    InjectParams --> CacheResult[緩存結果]

    CallAPI --> APIResponse[API 回應]
    ExecuteAPI --> APIResponse
    KnowledgeAPI --> APIResponse

    CacheResult --> Response([返回回應給用戶])
    CachedResponse --> Response
    Fallback --> Response
    ShowKnowledge --> Response
    APIResponse --> Response
    BothActions --> Response

    FormReview --> Response
    FormEdit --> Response
    FormCollect --> Response

    style Start fill:#e1f5e1
    style Response fill:#e1f5e1
    style Decision fill:#fff3cd
    style SOP fill:#d1ecf1
    style Knowledge fill:#d1ecf1
    style FormFlow fill:#f8d7da
```

---

## 🔄 2. SOP 與知識庫並行檢索決策機制

```mermaid
flowchart LR
    subgraph Input[用戶輸入]
        Message[用戶訊息]
        Intent[意圖分類結果]
    end

    subgraph Parallel[並行檢索]
        SOPT[SOP Task<br/>sop_orchestrator.process_message]
        KnowledgeT[Knowledge Task<br/>_retrieve_knowledge]
    end

    Message --> SOPT
    Intent --> SOPT
    Message --> KnowledgeT
    Intent --> KnowledgeT

    subgraph Scoring[分數比較]
        SOPScore[SOP 分數<br/>閾值: 0.55]
        KnowledgeScore[知識庫分數<br/>閾值: 0.6]
        Gap[差距閾值: 0.15]
    end

    SOPT --> SOPScore
    KnowledgeT --> KnowledgeScore

    subgraph DecisionLogic[決策邏輯]
        C1[Case 1: SOP > 知識+0.15<br/>→ 使用 SOP]
        C2[Case 2: 知識 > SOP+0.15<br/>→ 使用知識庫]
        C3[Case 3: 分數接近<br/>→ 看後續動作]
        C4[Case 4: 只有 SOP 達標<br/>→ 使用 SOP]
        C5[Case 5: 只有知識達標<br/>→ 使用知識庫]
        C6[Case 6: 都不達標<br/>→ 兜底回應]
    end

    SOPScore --> DecisionLogic
    KnowledgeScore --> DecisionLogic
    Gap --> DecisionLogic

    style Parallel fill:#e3f2fd
    style Scoring fill:#fff3cd
    style DecisionLogic fill:#d4edda
```

---

## 🎯 3. SOP 觸發模式詳細流程

```mermaid
stateDiagram-v2
    [*] --> 用戶提問

    用戶提問 --> SOP檢索成功

    SOP檢索成功 --> 檢查觸發模式

    state 檢查觸發模式 {
        [*] --> Manual: trigger_mode='manual'
        [*] --> Immediate: trigger_mode='immediate'
        [*] --> NullMode: trigger_mode=null

        Manual --> 顯示SOP內容_Manual
        顯示SOP內容_Manual --> 等待關鍵詞
        等待關鍵詞 --> 檢測關鍵詞
        檢測關鍵詞 --> 匹配成功: ["還是不行", "試過了", "需要維修"]
        檢測關鍵詞 --> 無匹配: 其他詞彙
        無匹配 --> 結束對話

        Immediate --> 顯示SOP內容_Immediate
        顯示SOP內容_Immediate --> 顯示確認提示
        顯示確認提示 --> 等待用戶確認
        等待用戶確認 --> 確認: ["是", "要", "好"]
        等待用戶確認 --> 取消: ["否", "不用"]
        取消 --> 結束對話

        NullMode --> 顯示SOP內容_Null
        顯示SOP內容_Null --> 結束對話: next_action='none'
    }

    匹配成功 --> 執行後續動作
    確認 --> 執行後續動作

    state 執行後續動作 {
        [*] --> form_fill: next_action='form_fill'
        [*] --> api_call: next_action='api_call'
        [*] --> form_then_api: next_action='form_then_api'

        form_fill --> 啟動表單流程
        api_call --> 調用外部API
        form_then_api --> 表單後調用API
    }

    啟動表單流程 --> [*]
    調用外部API --> [*]
    表單後調用API --> [*]
    結束對話 --> [*]
```

---

## 📝 4. 表單生命週期狀態機

```mermaid
stateDiagram-v2
    [*] --> START: trigger_form()

    START --> COLLECTING: 開始收集

    COLLECTING --> COLLECTING: 收集欄位
    COLLECTING --> DIGRESSION: 用戶離題
    COLLECTING --> REVIEWING: 所有欄位完成

    DIGRESSION --> COLLECTING: 選擇恢復
    DIGRESSION --> PAUSED: 選擇暫停

    PAUSED --> COLLECTING: resume_form()
    PAUSED --> CANCELLED: 超時/取消

    REVIEWING --> EDITING: 用戶要求修改
    REVIEWING --> COMPLETED: 確認提交
    REVIEWING --> CANCELLED: 取消

    EDITING --> REVIEWING: 修改完成

    COMPLETED --> [*]: 表單完成
    CANCELLED --> [*]: 表單取消

    note right of COLLECTING
        狀態: 正在收集欄位
        動作: collect_field_data()
    end note

    note right of DIGRESSION
        狀態: 用戶離題
        動作: 處理其他問題
    end note

    note right of REVIEWING
        狀態: 審核確認
        動作: 顯示所有資料
    end note

    note right of EDITING
        狀態: 編輯模式
        動作: 修改特定欄位
    end note
```

---

## 🔌 5. API 調用流程

```mermaid
sequenceDiagram
    participant User as 用戶
    participant Chat as Chat API
    participant SOP as SOP/知識庫
    participant Form as 表單管理器
    participant External as 外部 API

    User->>Chat: 發送訊息
    Chat->>SOP: 檢索匹配內容

    alt SOP 有 API 調用
        SOP-->>Chat: next_action='api_call'
        Chat->>External: 直接調用 API
        External-->>Chat: API 響應
    else SOP 有表單+API
        SOP-->>Chat: next_action='form_then_api'
        Chat->>Form: 啟動表單

        loop 收集欄位
            User->>Form: 提供資料
            Form-->>User: 下一個問題
        end

        Form->>User: 審核確認
        User->>Form: 確認提交

        Form->>External: 調用 API (帶表單資料)
        External-->>Form: API 響應
        Form-->>Chat: 完成回應
    else 知識庫有 API 調用
        SOP-->>Chat: action_type='api_call'
        Chat->>External: 調用配置的 API
        External-->>Chat: API 響應
    end

    Chat-->>User: 返回結果
```

---

## 🎨 6. 知識庫表單觸發流程（2026-02-03 新增）

```mermaid
flowchart TB
    subgraph KnowledgeRetrieval[知識庫檢索]
        Query[用戶查詢]
        Search[向量搜尋 + 意圖過濾]
        Match{找到匹配?}
    end

    Query --> Search
    Search --> Match

    Match -->|是| CheckAction{檢查 action_type}
    Match -->|否| NoMatch[無結果]

    CheckAction -->|direct_answer| DirectAnswer[直接回答]
    CheckAction -->|form_fill| FormTrigger{檢查 trigger_mode}
    CheckAction -->|api_call| DirectAPI[直接調用 API]
    CheckAction -->|form_then_api| FormThenAPIFlow[表單→API]

    FormTrigger -->|NULL/auto| AutoForm[自動觸發表單]
    FormTrigger -->|manual| ManualFlow[Manual 流程]
    FormTrigger -->|immediate| ImmediateFlow[Immediate 流程]

    subgraph ManualProcess[Manual 處理]
        ManualFlow --> ShowKnowledge1[顯示知識內容]
        ShowKnowledge1 --> AddPrompt1[添加觸發提示]
        AddPrompt1 --> SaveContext1[保存 Context]
        SaveContext1 --> WaitKeyword1[等待關鍵詞]
        WaitKeyword1 -->|"是"/"要"| TriggerForm1[觸發表單]
        WaitKeyword1 -->|其他| Continue1[繼續對話]
    end

    subgraph ImmediateProcess[Immediate 處理]
        ImmediateFlow --> ShowKnowledge2[顯示知識內容]
        ShowKnowledge2 --> AskConfirm[詢問是否需要表單]
        AskConfirm --> SaveContext2[保存 Context]
        SaveContext2 --> WaitConfirm2[等待確認]
        WaitConfirm2 -->|"是"/"要"| TriggerForm2[觸發表單]
        WaitConfirm2 -->|"否"/"不用"| Continue2[結束]
    end

    AutoForm --> FormSession[創建表單會話]
    TriggerForm1 --> FormSession
    TriggerForm2 --> FormSession
    FormThenAPIFlow --> FormSession

    FormSession --> CollectData[收集表單資料]
    CollectData --> FormComplete{表單完成}

    FormComplete --> OnCompleteAction{on_complete_action?}
    OnCompleteAction -->|show_knowledge| ShowResult[顯示知識答案]
    OnCompleteAction -->|call_api| CallConfigAPI[調用配置的 API]
    OnCompleteAction -->|both| BothAction[兩者都執行]

    style ManualProcess fill:#e8f5e9
    style ImmediateProcess fill:#e3f2fd
    style FormSession fill:#fff3e0
```

---

## 🔐 7. Context 管理機制

```mermaid
flowchart LR
    subgraph ContextStorage[Context 存儲]
        Redis[(Redis Cache)]
        Memory[(內存備援)]
    end

    subgraph SOPContext[SOP Context 結構]
        SOPData["{<br/>
        sop_id: 123,<br/>
        trigger_mode: 'manual',<br/>
        state: 'MANUAL_WAITING',<br/>
        trigger_keywords: ['還是不行'],<br/>
        next_action: 'form_fill',<br/>
        created_at: '2026-02-04'<br/>
        }"]
    end

    subgraph KnowledgeContext[知識庫 Context 結構]
        KnowledgeData["{<br/>
        knowledge_id: 456,<br/>
        trigger_mode: 'immediate',<br/>
        state: 'IMMEDIATE_WAITING',<br/>
        trigger_keywords: ['是', '要'],<br/>
        form_id: 'inquiry_form',<br/>
        on_complete_action: 'call_api'<br/>
        }"]
    end

    subgraph Operations[操作]
        Save[保存 Context]
        Get[獲取 Context]
        Update[更新狀態]
        Delete[清除 Context]
    end

    Save --> Redis
    Redis -.->|Redis 不可用| Memory

    Get --> Redis
    Redis -.->|未找到| Memory

    Update --> Redis
    Update -.-> Memory

    Delete --> Redis
    Delete --> Memory

    SOPData --> Save
    KnowledgeData --> Save

    style Redis fill:#fce4ec
    style Memory fill:#e0f2f1
```

---

## 📊 8. 完整決策樹

```mermaid
flowchart TB
    Start([用戶訊息]) --> FormCheck{有表單會話?}

    FormCheck -->|是| HandleForm[處理表單狀態]
    FormCheck -->|否| CheckSOP{檢查 SOP Context}

    CheckSOP -->|有待處理| CheckKeyword{關鍵詞匹配?}
    CheckKeyword -->|是| ExecuteAction[執行後續動作]
    CheckKeyword -->|否| ContinueNormal[繼續正常流程]

    CheckSOP -->|無| ContinueNormal

    ContinueNormal --> IntentClassify[意圖分類]
    IntentClassify --> ParallelSearch[並行檢索 SOP + 知識庫]

    ParallelSearch --> Compare{分數比較}

    Compare -->|SOP 顯著高| UseSOP[使用 SOP]
    Compare -->|知識庫顯著高| UseKnowledge[使用知識庫]
    Compare -->|分數接近| CheckPriority{檢查優先級}
    Compare -->|都不達標| Fallback[兜底回應]

    CheckPriority -->|SOP 有後續動作| UseSOP
    CheckPriority -->|SOP 等待關鍵詞| UseKnowledge
    CheckPriority -->|其他| CompareScore[比較細微分數]

    UseSOP --> SOPTriggerMode{SOP 觸發模式}
    UseKnowledge --> KnowledgeActionType{知識 action_type}

    SOPTriggerMode -->|Manual| SOPManual[等待觸發詞]
    SOPTriggerMode -->|Immediate| SOPImmediate[詢問確認]
    SOPTriggerMode -->|Auto| SOPAuto[自動執行]

    KnowledgeActionType -->|direct_answer| LLMAnswer[LLM 優化答案]
    KnowledgeActionType -->|form_fill| KnowledgeFormTrigger{知識觸發模式}
    KnowledgeActionType -->|api_call| DirectAPICall[直接調用 API]

    KnowledgeFormTrigger -->|Manual| KnowledgeManual[等待觸發詞]
    KnowledgeFormTrigger -->|Immediate| KnowledgeImmediate[詢問確認]
    KnowledgeFormTrigger -->|Auto| KnowledgeAuto[自動觸發]

    style Start fill:#e1f5e1
    style Compare fill:#fff3cd
    style CheckPriority fill:#fff3cd
```

---

## 🏷️ 9. 系統角色與職責

| 組件 | 職責 | 關鍵決策點 |
|------|------|-----------|
| **Chat Router** | 主入口，協調整體流程 | 表單優先、SOP 優先、分數比較 |
| **SOP Orchestrator** | SOP 檢索與觸發管理 | 觸發模式判斷、關鍵詞匹配 |
| **Knowledge Retriever** | 知識庫檢索與過濾 | 向量相似度、意圖匹配 |
| **Form Manager** | 表單生命週期管理 | 狀態轉換、欄位驗證 |
| **Intent Classifier** | 意圖識別 | 多意圖支援、信心度評估 |
| **LLM Optimizer** | 答案優化與合成 | 合成策略、參數注入 |
| **Cache Service** | 三層緩存管理 | 緩存命中、過期策略 |
| **API Handler** | 外部 API 調用 | 重試機制、錯誤處理 |

---

## 🎯 10. 關鍵參數配置

```yaml
# 分數閾值
SOP_MIN_THRESHOLD: 0.55          # SOP 最低分數
KNOWLEDGE_MIN_THRESHOLD: 0.6     # 知識庫最低分數
SCORE_GAP_THRESHOLD: 0.15        # 顯著差距閾值

# 優化閾值
PERFECT_MATCH_THRESHOLD: 0.90    # 完美匹配閾值
SYNTHESIS_THRESHOLD: 0.80        # 答案合成閾值
HIGH_QUALITY_THRESHOLD: 0.80     # 高質量閾值

# 觸發配置
DEFAULT_TRIGGER_KEYWORDS:         # 預設觸發關鍵詞
  - "是"
  - "要"
  - "好"
  - "確認"

CANCEL_KEYWORDS:                  # 取消關鍵詞
  - "否"
  - "不用"
  - "取消"
  - "算了"

# Context 配置
CONTEXT_TTL: 3600                 # Context 存活時間（秒）
CONTEXT_STORAGE: "redis"          # 存儲方式（redis/memory）

# 表單配置
FORM_SESSION_TIMEOUT: 1800        # 表單會話超時（秒）
MAX_FORM_FIELDS: 20               # 最大欄位數
DIGRESSION_THRESHOLD: 0.7        # 離題判定閾值
```

---

## 📈 11. 性能優化點

1. **並行檢索**: SOP 和知識庫同時檢索，減少延遲
2. **三層緩存**: 問題緩存 → 向量緩存 → 結果緩存
3. **懶加載**: 服務實例按需載入
4. **Context 備援**: Redis 不可用時自動切換內存
5. **智能決策**: 根據分數和業務邏輯快速選擇路徑

---

## 🔍 12. 監控指標

```mermaid
graph LR
    subgraph Metrics[關鍵指標]
        ResponseTime[回應時間]
        CacheHitRate[緩存命中率]
        IntentAccuracy[意圖準確率]
        FormCompletionRate[表單完成率]
        APISuccessRate[API 成功率]
    end

    subgraph Alerts[告警閾值]
        RT[回應時間 > 2s]
        CHR[緩存命中率 < 60%]
        IA[意圖準確率 < 80%]
        FCR[表單完成率 < 70%]
        ASR[API 成功率 < 95%]
    end

    ResponseTime --> RT
    CacheHitRate --> CHR
    IntentAccuracy --> IA
    FormCompletionRate --> FCR
    APISuccessRate --> ASR
```

---

## 📝 總結

本架構圖完整展示了 AIChatbot 的對話處理流程，包括：

1. ✅ **10 層對話處理流程**
2. ✅ **SOP 與知識庫並行檢索**
3. ✅ **三種觸發模式（Manual/Immediate/Auto）**
4. ✅ **表單完整生命週期**
5. ✅ **API 調用機制**
6. ✅ **Context 管理與備援**
7. ✅ **智能決策樹**
8. ✅ **所有特殊情境處理**

系統設計充分考慮了性能、擴展性和用戶體驗，通過並行處理、智能決策和完善的狀態管理，提供了靈活且高效的對話服務。