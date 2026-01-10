# 表單填寫式對話架構設計（Form-filling Dialog）

## 📌 需求背景

某些知識不是一問一答，而是需要取得必要資訊（例如：身分證、電話、住址等）。
系統需要能夠：
1. **逐步收集**必要資訊（多輪對話）
2. **檢測用戶離題**（不相關回答或問其他問題）
3. **自動跳出**收集流程（回到正常對話模式）

---

## 🎯 設計目標

| 目標 | 說明 |
|------|------|
| **結構化收集** | 按照預定義的欄位順序收集資訊 |
| **靈活中斷** | 用戶可隨時離題或跳出 |
| **上下文保持** | 跳出後可選擇性恢復表單填寫 |
| **驗證機制** | 驗證每個欄位的格式和合法性 |
| **友好提示** | 提供清晰的填寫進度和提示 |

---

## 🏗️ 架構設計

### 1. 核心概念

```
┌─────────────────────────────────────────────────────────────┐
│                    對話狀態機（State Machine）                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  NORMAL_CHAT ──┬──> FORM_FILLING ──┬──> FORM_COMPLETED     │
│      ↑         │         ↓          │          │            │
│      │         │    COLLECTING      │          │            │
│      │         │    (逐欄收集)       │          │            │
│      │         │         ↓          │          │            │
│      └─────────┴─── DIGRESSION ─────┴──────────┘            │
│                    (用戶離題)                                 │
└─────────────────────────────────────────────────────────────┘
```

### 2. 狀態定義

| 狀態 | 說明 | 可能轉移 |
|------|------|----------|
| **NORMAL_CHAT** | 正常對話模式 | → FORM_FILLING |
| **FORM_FILLING** | 表單填寫模式 | → COLLECTING / DIGRESSION / FORM_COMPLETED |
| **COLLECTING** | 正在收集特定欄位 | → COLLECTING (下一欄) / DIGRESSION |
| **DIGRESSION** | 用戶離題/打斷 | → NORMAL_CHAT / COLLECTING (恢復) |
| **FORM_COMPLETED** | 表單完成 | → NORMAL_CHAT |

---

## 📊 資料結構設計

### 1. 表單定義（Form Schema）

```python
{
    "form_id": "rental_application",
    "form_name": "租屋申請表",
    "description": "收集租客申請租屋的基本資料",
    "trigger_intents": ["租屋申請", "我要租房子", "申請租約"],
    "fields": [
        {
            "field_name": "full_name",
            "display_name": "姓名",
            "field_type": "text",
            "required": true,
            "prompt": "請問您的全名是？",
            "validation": {
                "pattern": "^[\u4e00-\u9fa5]{2,10}$",
                "error_message": "請輸入2-10個中文字的真實姓名"
            },
            "examples": ["王小明", "李美玲"]
        },
        {
            "field_name": "phone",
            "display_name": "聯絡電話",
            "field_type": "phone",
            "required": true,
            "prompt": "請提供您的聯絡電話（手機或市話）",
            "validation": {
                "pattern": "^09\\d{8}$|^0\\d{1,2}-\\d{6,8}$",
                "error_message": "請輸入正確的台灣電話號碼格式（如：0912345678 或 02-12345678）"
            },
            "examples": ["0912345678", "02-12345678"]
        },
        {
            "field_name": "id_number",
            "display_name": "身分證字號",
            "field_type": "text",
            "required": true,
            "prompt": "請提供您的身分證字號（用於身份驗證）",
            "validation": {
                "pattern": "^[A-Z][12]\\d{8}$",
                "error_message": "請輸入正確的身分證字號格式（如：A123456789）"
            },
            "examples": ["A123456789"]
        },
        {
            "field_name": "address",
            "display_name": "通訊地址",
            "field_type": "text",
            "required": true,
            "prompt": "請提供您的通訊地址",
            "validation": {
                "min_length": 10,
                "error_message": "請輸入完整的地址（至少10個字）"
            }
        }
    ],
    "completion_message": "感謝您完成租屋申請表！我們會儘快審核您的資料並與您聯繫。",
    "cancellation_message": "已取消表單填寫。如需重新申請，請隨時告訴我！"
}
```

### 2. 會話狀態（Session State）

```python
{
    "session_id": "sess_20250108_123456",
    "user_id": "user_001",
    "vendor_id": 1,
    "state": "COLLECTING",  # 當前狀態
    "form_context": {
        "form_id": "rental_application",
        "started_at": "2025-01-08T10:30:00Z",
        "current_field_index": 1,  # 正在收集第幾個欄位（0-based）
        "collected_data": {
            "full_name": "王小明",
            "phone": null,  # 待填
            "id_number": null,
            "address": null
        },
        "validation_attempts": {
            "phone": 0  # 驗證失敗次數
        },
        "last_prompt": "請提供您的聯絡電話（手機或市話）"
    },
    "digression_count": 0,  # 離題次數統計
    "allow_resume": true,  # 是否允許恢復表單
    "previous_state": "NORMAL_CHAT"  # 前一個狀態（用於恢復）
}
```

---

## 🔄 核心流程

### 流程 1：觸發表單填寫

```
用戶輸入 → 意圖分類 → 匹配到表單觸發意圖 → 進入 FORM_FILLING 狀態
                                           ↓
                              顯示表單說明 + 第一個欄位提示
```

**程式碼示意**：
```python
async def trigger_form_filling(intent_name: str, session_id: str):
    # 1. 查找匹配的表單定義
    form_schema = get_form_by_intent(intent_name)

    # 2. 初始化會話狀態
    session_state = {
        "state": "FORM_FILLING",
        "form_context": {
            "form_id": form_schema["form_id"],
            "current_field_index": 0,
            "collected_data": {},
            "started_at": datetime.utcnow().isoformat()
        }
    }
    save_session_state(session_id, session_state)

    # 3. 返回第一個欄位的提示
    first_field = form_schema["fields"][0]
    return {
        "answer": f"好的，我來協助您填寫{form_schema['form_name']}。\n\n{first_field['prompt']}",
        "state": "COLLECTING"
    }
```

---

### 流程 2：收集欄位資料

```
用戶回覆 → 提取資料 → 驗證格式 → 通過？
                                    ↓ 是
                           儲存 + 下一欄位提示
                                    ↓ 否
                           顯示錯誤訊息 + 重新詢問
```

**程式碼示意**：
```python
async def collect_field_data(user_message: str, session_state: dict):
    form_context = session_state["form_context"]
    form_schema = get_form_schema(form_context["form_id"])
    current_field = form_schema["fields"][form_context["current_field_index"]]

    # 1. 驗證資料格式
    is_valid, extracted_value = validate_field(
        field_config=current_field,
        user_input=user_message
    )

    if not is_valid:
        # 記錄失敗次數
        attempts = form_context.get("validation_attempts", {})
        field_name = current_field["field_name"]
        attempts[field_name] = attempts.get(field_name, 0) + 1

        # 超過3次失敗 → 提供跳過選項
        if attempts[field_name] >= 3:
            return {
                "answer": f"看起來{current_field['display_name']}的格式有些困難。\n\n您可以：\n1. 繼續嘗試輸入\n2. 跳過此欄位\n3. 取消填寫\n\n請選擇（輸入 1/2/3）",
                "state": "COLLECTING"
            }

        return {
            "answer": f"{current_field['validation']['error_message']}\n\n{current_field['prompt']}",
            "state": "COLLECTING"
        }

    # 2. 儲存資料
    form_context["collected_data"][current_field["field_name"]] = extracted_value
    form_context["current_field_index"] += 1

    # 3. 檢查是否完成所有欄位
    if form_context["current_field_index"] >= len(form_schema["fields"]):
        return await complete_form(session_state)

    # 4. 提示下一個欄位
    next_field = form_schema["fields"][form_context["current_field_index"]]
    return {
        "answer": f"✅ {current_field['display_name']}已記錄！\n\n{next_field['prompt']}",
        "state": "COLLECTING"
    }
```

---

### 流程 3：偵測離題（Digression Detection）

**策略組合**：

| 檢測方法 | 條件 | 優先級 |
|---------|------|--------|
| **明確關鍵字** | 用戶輸入包含「取消」、「不填了」、「問題」等 | 高 |
| **意圖轉移** | 意圖分類結果 ≠ 當前表單相關意圖 | 中 |
| **不相關回答** | 語義相似度 < 0.3（與當前欄位提示） | 低 |
| **連續無效輸入** | 連續3次驗證失敗 | 中 |

**程式碼示意**：
```python
async def detect_digression(user_message: str, session_state: dict):
    """
    偵測用戶是否離題或想跳出表單

    Returns:
        (is_digression: bool, digression_type: str, confidence: float)
    """
    # 1. 明確關鍵字檢測（優先級最高）
    exit_keywords = ["取消", "不填了", "算了", "不想填", "exit", "cancel"]
    if any(keyword in user_message for keyword in exit_keywords):
        return (True, "explicit_exit", 1.0)

    question_keywords = ["為什麼", "如何", "什麼", "哪裡", "?", "？"]
    if any(keyword in user_message for keyword in question_keywords):
        return (True, "question", 0.8)

    # 2. 意圖分類檢測
    intent_result = intent_classifier.classify(user_message)
    form_context = session_state["form_context"]
    form_schema = get_form_schema(form_context["form_id"])

    if intent_result["intent_name"] not in form_schema["trigger_intents"]:
        # 檢查是否為高置信度的不相關意圖
        if intent_result["confidence"] > 0.7:
            return (True, "intent_shift", intent_result["confidence"])

    # 3. 語義相似度檢測（與當前欄位提示的相關性）
    current_field = form_schema["fields"][form_context["current_field_index"]]
    semantic_similarity = calculate_similarity(
        user_message,
        current_field["prompt"]
    )

    if semantic_similarity < 0.3:
        return (True, "irrelevant_response", 0.6)

    # 4. 沒有離題
    return (False, None, 0.0)
```

---

### 流程 4：處理離題

```
偵測到離題 → 判斷類型 → 明確退出？
                          ↓ 是
                     取消表單 → NORMAL_CHAT
                          ↓ 否
                     回答問題 → 詢問是否繼續
```

**策略選擇**：

| 離題類型 | 處理策略 | 範例回應 |
|---------|---------|---------|
| **explicit_exit** | 立即取消 | "已取消表單填寫。如需重新申請，請隨時告訴我！" |
| **question** | 回答問題 + 提供選項 | "[回答問題]\n\n您想要：\n1. 繼續填寫表單\n2. 稍後再填" |
| **intent_shift** | 處理新意圖 + 詢問 | "[處理新請求]\n\n剛剛的表單還沒完成，需要繼續嗎？" |
| **irrelevant_response** | 提示重新輸入 | "抱歉，我沒聽懂。請提供您的[欄位名稱]，或輸入「取消」結束填寫。" |

**程式碼示意**：
```python
async def handle_digression(
    user_message: str,
    digression_type: str,
    session_state: dict
):
    if digression_type == "explicit_exit":
        # 明確退出 → 取消表單
        clear_form_context(session_state["session_id"])
        return {
            "answer": "已取消表單填寫。如需重新申請，請隨時告訴我！",
            "state": "NORMAL_CHAT"
        }

    elif digression_type == "question":
        # 用戶問問題 → 回答 + 提供繼續選項
        answer = await handle_user_question(user_message)
        return {
            "answer": f"{answer}\n\n──────\n💡 您的表單還未完成，需要繼續填寫嗎？\n• 輸入「繼續」恢復填寫\n• 輸入「取消」結束",
            "state": "DIGRESSION",
            "allow_commands": ["繼續", "取消"]
        }

    elif digression_type == "intent_shift":
        # 意圖轉移 → 處理新意圖 + 詢問
        answer = await handle_normal_chat(user_message)
        return {
            "answer": f"{answer}\n\n──────\n💡 剛剛的{get_form_name(session_state)}還沒完成，需要繼續嗎？（是/否）",
            "state": "DIGRESSION"
        }

    else:  # irrelevant_response
        # 不相關回答 → 重新提示
        current_field = get_current_field(session_state)
        return {
            "answer": f"抱歉，我沒聽懂您的回覆。\n\n{current_field['prompt']}\n\n（或輸入「取消」結束填寫）",
            "state": "COLLECTING"
        }
```

---

### 流程 5：恢復表單填寫

```
DIGRESSION 狀態 → 用戶選擇「繼續」 → 恢復到 COLLECTING
                                   ↓
                          提示當前未完成的欄位
```

**程式碼示意**：
```python
async def resume_form_filling(session_state: dict):
    form_context = session_state["form_context"]
    form_schema = get_form_schema(form_context["form_id"])
    current_field = form_schema["fields"][form_context["current_field_index"]]

    # 統計進度
    total_fields = len(form_schema["fields"])
    completed = form_context["current_field_index"]

    return {
        "answer": f"好的，繼續填寫！\n\n📊 進度：{completed}/{total_fields}\n\n{current_field['prompt']}",
        "state": "COLLECTING"
    }
```

---

## 🛡️ 安全性與驗證

### 1. 欄位驗證器

```python
FIELD_VALIDATORS = {
    "phone": {
        "pattern": r"^09\d{8}$|^0\d{1,2}-\d{6,8}$",
        "validator": lambda x: bool(re.match(r"^09\d{8}$|^0\d{1,2}-\d{6,8}$", x))
    },
    "id_number": {
        "pattern": r"^[A-Z][12]\d{8}$",
        "validator": validate_taiwan_id  # 自訂驗證函數（含檢查碼驗證）
    },
    "email": {
        "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "validator": lambda x: bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", x))
    }
}

def validate_field(field_config: dict, user_input: str) -> tuple[bool, str]:
    """
    驗證欄位資料

    Returns:
        (is_valid, extracted_value)
    """
    field_type = field_config.get("field_type", "text")

    # 1. 提取可能的值（去除多餘文字）
    extracted = extract_value_from_text(user_input, field_type)

    # 2. 執行格式驗證
    if "validation" in field_config:
        pattern = field_config["validation"].get("pattern")
        if pattern and not re.match(pattern, extracted):
            return (False, None)

    # 3. 使用自訂驗證器
    if field_type in FIELD_VALIDATORS:
        validator = FIELD_VALIDATORS[field_type]["validator"]
        if not validator(extracted):
            return (False, None)

    return (True, extracted)
```

### 2. 敏感資料處理

```python
SENSITIVE_FIELDS = ["id_number", "passport", "credit_card"]

def mask_sensitive_data(field_name: str, value: str) -> str:
    """遮罩敏感資料用於顯示"""
    if field_name in SENSITIVE_FIELDS:
        if field_name == "id_number":
            return f"{value[:3]}{'*' * 6}{value[-2:]}"  # A12****89
        elif field_name == "phone":
            return f"{value[:4]}****{value[-3:]}"  # 0912****678
    return value
```

---

## 💾 資料庫設計

### 表 1：form_schemas（表單定義）

```sql
CREATE TABLE form_schemas (
    id SERIAL PRIMARY KEY,
    form_id VARCHAR(100) UNIQUE NOT NULL,
    form_name VARCHAR(200) NOT NULL,
    description TEXT,
    trigger_intents JSONB,  -- 觸發意圖列表
    fields JSONB NOT NULL,  -- 欄位定義（JSON）
    completion_message TEXT,
    cancellation_message TEXT,
    is_active BOOLEAN DEFAULT true,
    vendor_id INTEGER REFERENCES vendors(id),  -- 業者專屬表單
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_form_trigger_intents ON form_schemas USING GIN(trigger_intents);
```

### 表 2：form_sessions（表單會話）

```sql
CREATE TABLE form_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100),
    vendor_id INTEGER REFERENCES vendors(id),
    form_id VARCHAR(100) REFERENCES form_schemas(form_id),
    state VARCHAR(50) NOT NULL,  -- COLLECTING / DIGRESSION / COMPLETED / CANCELLED
    current_field_index INTEGER DEFAULT 0,
    collected_data JSONB,  -- 已收集的資料
    validation_attempts JSONB,  -- 驗證失敗次數記錄
    digression_count INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_form_sessions_session_id ON form_sessions(session_id);
CREATE INDEX idx_form_sessions_state ON form_sessions(state);
```

### 表 3：form_submissions（已完成的表單）

```sql
CREATE TABLE form_submissions (
    id SERIAL PRIMARY KEY,
    form_session_id INTEGER REFERENCES form_sessions(id),
    form_id VARCHAR(100) REFERENCES form_schemas(form_id),
    user_id VARCHAR(100),
    vendor_id INTEGER REFERENCES vendors(id),
    submitted_data JSONB NOT NULL,  -- 完整提交資料
    submission_source VARCHAR(50),  -- 'chatbot' / 'web' / 'app'
    submitted_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_form_submissions_user_id ON form_submissions(user_id);
CREATE INDEX idx_form_submissions_vendor_id ON form_submissions(vendor_id);
```

---

## 🚀 實作步驟

### Phase 1：基礎架構（Week 1-2）

1. **資料庫設計**
   - [ ] 建立 form_schemas、form_sessions、form_submissions 表
   - [ ] 新增測試資料（租屋申請表範例）

2. **核心模組**
   - [ ] `services/form_manager.py`：表單狀態管理
   - [ ] `services/form_validator.py`：欄位驗證器
   - [ ] `services/digression_detector.py`：離題偵測

3. **API 端點**
   - [ ] POST `/api/v1/forms/trigger`：觸發表單填寫
   - [ ] POST `/api/v1/forms/collect`：收集欄位資料
   - [ ] POST `/api/v1/forms/cancel`：取消表單填寫

### Phase 2：離題處理（Week 3）

4. **離題偵測引擎**
   - [ ] 關鍵字偵測
   - [ ] 意圖轉移偵測
   - [ ] 語義相似度偵測

5. **恢復機制**
   - [ ] 暫存表單狀態
   - [ ] 提供恢復選項
   - [ ] 超時自動清理（30分鐘）

### Phase 3：進階功能（Week 4）

6. **智能提取**
   - [ ] NER（命名實體識別）提取姓名、地址
   - [ ] 正則表達式提取電話、身分證

7. **進度視覺化**
   - [ ] 進度條顯示（3/5 完成）
   - [ ] 已填欄位總結

8. **測試與優化**
   - [ ] 單元測試（驗證器、狀態轉移）
   - [ ] 整合測試（完整流程）
   - [ ] 性能優化（會話狀態快取）

---

## 📝 使用範例

### 範例 1：完整流程（無離題）

```
用戶：我要申請租房子
系統：好的，我來協助您填寫租屋申請表。

      請問您的全名是？

用戶：王小明
系統：✅ 姓名已記錄！

      請提供您的聯絡電話（手機或市話）

用戶：0912345678
系統：✅ 聯絡電話已記錄！

      請提供您的身分證字號（用於身份驗證）

用戶：A123456789
系統：✅ 身分證字號已記錄！

      請提供您的通訊地址

用戶：台北市大安區復興南路一號
系統：✅ 通訊地址已記錄！

      📋 表單填寫完成！
      感謝您完成租屋申請表！我們會儘快審核您的資料並與您聯繫。
```

### 範例 2：用戶離題（問問題）

```
用戶：我要申請租房子
系統：好的，我來協助您填寫租屋申請表。

      請問您的全名是？

用戶：王小明
系統：✅ 姓名已記錄！

      請提供您的聯絡電話（手機或市話）

用戶：請問租金多少？
系統：我們的租金範圍是每月 15,000 ~ 25,000 元，實際金額依房型而定。

      ──────
      💡 您的表單還未完成，需要繼續填寫嗎？
      • 輸入「繼續」恢復填寫
      • 輸入「取消」結束

用戶：繼續
系統：好的，繼續填寫！

      📊 進度：1/4

      請提供您的聯絡電話（手機或市話）

用戶：0912345678
系統：✅ 聯絡電話已記錄！
      ...
```

### 範例 3：用戶明確退出

```
用戶：我要申請租房子
系統：好的，我來協助您填寫租屋申請表。

      請問您的全名是？

用戶：王小明
系統：✅ 姓名已記錄！

      請提供您的聯絡電話（手機或市話）

用戶：算了，我不想填了
系統：已取消表單填寫。如需重新申請，請隨時告訴我！
```

---

## 🎛️ 配置選項

### 環境變數

```bash
# 表單填寫超時時間（分鐘）
FORM_SESSION_TIMEOUT=30

# 離題偵測閾值
DIGRESSION_SIMILARITY_THRESHOLD=0.3
DIGRESSION_CONFIDENCE_THRESHOLD=0.7

# 驗證失敗容忍次數
VALIDATION_MAX_ATTEMPTS=3

# 是否允許跳過非必填欄位
ALLOW_SKIP_OPTIONAL_FIELDS=true
```

---

## 🔍 監控指標

| 指標 | 說明 | 目標 |
|------|------|------|
| **完成率** | 完成表單數 / 開始表單數 | > 70% |
| **平均耗時** | 從開始到完成的平均時間 | < 5 分鐘 |
| **離題率** | 發生離題 / 總對話輪次 | < 20% |
| **驗證失敗率** | 驗證失敗次數 / 總提交次數 | < 10% |
| **恢復率** | 離題後恢復填寫 / 離題總次數 | > 50% |

---

## 📚 參考資料

基於網路搜尋的最佳實踐：

1. **Slot-filling Dialog Systems**
   - 使用意圖加成（Intent Boosting）提高相關欄位檢測準確度
   - 支援多輪對話的上下文傳遞

2. **Digression Handling Strategies**（Cobus Greyling, Medium）
   - 多層級打斷控制：節點級 > 對話級 > 系統級
   - 允許用戶暫停主任務，處理次要問題後恢復

3. **State Machine-Based Conversation Models**
   - Hierarchical State Machines (HSMs) 降低複雜度
   - 狀態內嵌套子狀態機處理表單內部流程

4. **Microsoft Copilot Studio Slot Filling**（2024）
   - 動態擷取多個實體（如「我想買 200 元以下的登山鞋」同時提取產品和價格）
   - 減少多輪問答，提升效率

5. **Context Management Best Practices**
   - 儲存對話歷史、用戶偏好和當前狀態
   - 跨會話保持長期記憶
