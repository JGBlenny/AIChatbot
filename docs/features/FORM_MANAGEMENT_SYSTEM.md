# 📋 動態表單收集系統

## 概述

動態表單收集系統允許 AI 聊天機器人在對話過程中自動觸發表單填寫流程，收集結構化數據，並將表單答案與知識庫回答整合，提供無縫的用戶體驗。

**實作時間**：2025-01-10
**版本**：1.0
**狀態**：✅ 已完成並驗證

---

## 🎯 業務需求

### 問題背景

在實際業務場景中，AI 客服系統需要收集結構化數據：

- **「我想租房子」** → 需要收集姓名、地址、電話等資訊
- **「我要報修」** → 需要收集報修項目、描述、聯絡方式
- **「我想退租」** → 需要收集退租原因、預計日期、聯絡方式

傳統做法是跳轉到外部表單頁面，但這會：
1. 中斷對話流程
2. 降低用戶體驗
3. 增加用戶流失率

### 解決方案

實作對話式表單收集系統：
- **無縫整合**：在對話中自動觸發表單
- **多欄位驗證**：支援多種欄位類型（文字、數字、選項、日期等）
- **離題處理**：允許用戶在填表時提問
- **知識整合**：表單完成後顯示知識庫答案

---

## 🏗️ 系統架構

### 核心組件

```
┌─────────────────────────────────────────────────────────────┐
│                      用戶問題                                │
│                   「我想租房子」                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           Knowledge Retrieval (知識檢索)                     │
│  - 檢索到知識 ID: 123                                        │
│  - 知識類型: form (表單類型)                                  │
│  - 關聯表單: rental_application                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           Form Manager (trigger_form_by_knowledge)           │
│  - 創建表單會話 (session_id, vendor_id, form_id)             │
│  - 儲存觸發問題: "我想租房子"                                 │
│  - 儲存知識 ID: 123                                          │
│  - 狀態: COLLECTING                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  表單填寫流程                                │
│                                                              │
│  系統: 請提供您的姓名                                         │
│  用戶: 陳慶煌                      ← 收集第一個欄位            │
│                                                              │
│  系統: 請提供您的地址                                         │
│  用戶: 帳單怎麼繳？                ← 離題提問                  │
│                                                              │
│  系統: 💡 您的租屋申請表還未完成，需要繼續填寫嗎？             │
│       • 輸入「繼續」恢復填寫                                  │
│       • 輸入「回答」回答您的問題                              │
│       • 輸入「取消」結束                                      │
│                                                              │
│  用戶: 回答                        ← 選擇回答問題              │
│  系統: [回答帳單問題...]                                      │
│  狀態: CANCELLED (表單取消)                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              表單完成流程 (knowledge_id 整合)                 │
│                                                              │
│  系統: 請提供您的姓名                                         │
│  用戶: 陳慶煌                                                │
│                                                              │
│  系統: 請提供您的地址                                         │
│  用戶: 新北市樹林區                                           │
│                                                              │
│  系統: 請提供您的聯絡電話                                     │
│  用戶: 0911111111                                            │
│                                                              │
│  ✅ 表單填寫完成！                                            │
│                                                              │
│  [從知識庫讀取答案，知識 ID: 123]                             │
│  感謝您提交租屋申請！我們會在 3 個工作天內與您聯繫...          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄️ 資料庫設計

### 表單結構表 (form_schemas)

儲存表單定義和欄位配置。

```sql
CREATE TABLE form_schemas (
    id SERIAL PRIMARY KEY,
    form_id VARCHAR(100) UNIQUE NOT NULL,              -- 表單唯一ID
    form_name VARCHAR(200) NOT NULL,                   -- 表單名稱
    description TEXT,                                  -- 表單描述
    default_intro TEXT,                                -- 預設引導語
    fields JSONB NOT NULL,                             -- 表單欄位定義
    vendor_id INTEGER REFERENCES vendors(id),          -- 業者ID (NULL=全局)
    is_active BOOLEAN DEFAULT true,                    -- 是否啟用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_form_schemas_vendor ON form_schemas(vendor_id);
CREATE INDEX idx_form_schemas_active ON form_schemas(is_active);
```

#### 欄位定義 (fields JSONB)

```json
[
  {
    "field_name": "name",
    "field_label": "姓名",
    "field_type": "text",
    "prompt": "請提供您的姓名",
    "required": true,
    "validation_type": "taiwan_name",
    "max_length": 50
  },
  {
    "field_name": "address",
    "field_label": "地址",
    "field_type": "text",
    "prompt": "請提供您的地址",
    "required": true,
    "validation_type": "address",
    "max_length": 200
  },
  {
    "field_name": "phone",
    "field_label": "聯絡電話",
    "field_type": "text",
    "prompt": "請提供您的聯絡電話",
    "required": true,
    "validation_type": "phone",
    "max_length": 20
  }
]
```

**支援的欄位類型**：
- `text` - 單行文字
- `textarea` - 多行文字
- `select` - 單選選項
- `multiselect` - 多選選項
- `number` - 數字
- `email` - Email
- `date` - 日期

**驗證類型**：
- `taiwan_name` - 台灣姓名格式
- `taiwan_id` - 台灣身分證字號
- `phone` - 電話號碼
- `email` - Email 格式
- `address` - 地址格式
- `none` - 無驗證

---

### 表單會話表 (form_sessions)

追蹤用戶表單填寫進度和狀態。

```sql
CREATE TABLE form_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,                  -- 會話ID (UUID)
    user_id VARCHAR(100) NOT NULL,                     -- 用戶ID
    vendor_id INTEGER REFERENCES vendors(id),          -- 業者ID
    form_id VARCHAR(100) REFERENCES form_schemas(form_id), -- 表單ID
    state VARCHAR(20) NOT NULL,                        -- 狀態: COLLECTING/DIGRESSION/COMPLETED/CANCELLED
    current_field_index INTEGER DEFAULT 0,             -- 當前欄位索引
    collected_data JSONB DEFAULT '{}',                 -- 已收集的資料
    trigger_question TEXT,                             -- 觸發表單的問題
    pending_question TEXT,                             -- 待處理的離題問題
    knowledge_id INTEGER,                              -- 關聯的知識ID
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_form_sessions_session ON form_sessions(session_id);
CREATE INDEX idx_form_sessions_state ON form_sessions(state);
CREATE INDEX idx_form_sessions_user ON form_sessions(user_id);
```

**狀態說明**：
- `COLLECTING` - 收集中（正在填表）
- `DIGRESSION` - 離題中（用戶提問）
- `COMPLETED` - 已完成
- `CANCELLED` - 已取消

---

### 表單提交記錄表 (form_submissions)

儲存已完成的表單提交資料。

```sql
CREATE TABLE form_submissions (
    id SERIAL PRIMARY KEY,
    form_session_id INTEGER REFERENCES form_sessions(id), -- 關聯的會話ID
    form_id VARCHAR(100) NOT NULL,                     -- 表單ID
    user_id VARCHAR(100) NOT NULL,                     -- 用戶ID
    vendor_id INTEGER REFERENCES vendors(id),          -- 業者ID
    submitted_data JSONB NOT NULL,                     -- 提交的資料
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_form_submissions_form ON form_submissions(form_id);
CREATE INDEX idx_form_submissions_user ON form_submissions(user_id);
CREATE INDEX idx_form_submissions_vendor ON form_submissions(vendor_id);
CREATE INDEX idx_form_submissions_session ON form_submissions(form_session_id);
```

---

## 🔧 核心功能實作

### 1. 表單觸發 (trigger_form_by_knowledge)

**檔案**：`rag-orchestrator/services/form_manager.py`

當知識檢索發現知識關聯到表單時，自動觸發表單收集流程。

```python
async def trigger_form_by_knowledge(
    self,
    knowledge_id: int,
    form_id: str,
    intro_message: str,
    session_id: str,
    user_id: str,
    vendor_id: int,
    trigger_question: str = None,  # 新增：觸發問題
    knowledge_id: int = None       # 新增：知識ID
) -> Dict:
    """
    根據知識觸發表單

    Returns:
        {
            "answer": "引導語 + 第一個欄位提示",
            "form_triggered": True,
            "form_id": "rental_application",
            "current_field": "name"
        }
    """
    # 1. 取得表單結構
    form_schema = await self.get_form_schema(form_id, vendor_id)
    if not form_schema:
        return {"answer": "找不到表單定義", "error": True}

    # 2. 檢查是否已存在進行中的會話（避免重複創建）
    existing_session = await self.get_session_state(session_id)
    if existing_session and existing_session['state'] in ['COLLECTING', 'DIGRESSION']:
        session_state = existing_session
    else:
        # 3. 創建新的表單會話
        session_state = await self.create_form_session(
            session_id=session_id,
            user_id=user_id,
            vendor_id=vendor_id,
            form_id=form_id,
            trigger_question=trigger_question,  # 儲存觸發問題
            knowledge_id=knowledge_id           # 儲存知識ID
        )

    # 4. 獲取第一個欄位
    first_field = form_schema['fields'][0]

    # 5. 返回引導語 + 第一個欄位提示
    return {
        "answer": f"{intro_message}\n\n{first_field['prompt']}",
        "form_triggered": True,
        "form_id": form_id,
        "current_field": first_field['field_name']
    }
```

**重要修改**：
1. 新增 `trigger_question` 參數 - 儲存觸發表單的原始問題
2. 新增 `knowledge_id` 參數 - 儲存關聯的知識ID，用於完成時顯示答案
3. 新增重複創建檢查 - 避免同一 session_id 創建多個表單會話

---

### 2. 表單欄位收集 (collect_form_field)

**檔案**：`rag-orchestrator/services/form_manager.py`

逐一收集表單欄位，處理驗證、離題問題。

```python
async def collect_form_field(
    self,
    session_id: str,
    user_message: str,
    vendor_id: int
) -> Dict:
    """
    收集表單欄位

    Returns:
        {
            "answer": "下一個欄位提示 / 完成訊息",
            "form_completed": False/True,
            "current_field": "address",
            "collected_data": {...}
        }
    """
    # 1. 獲取會話狀態
    session_state = await self.get_session_state(session_id)
    if not session_state:
        return {"answer": "找不到表單會話", "error": True}

    # 2. 獲取表單結構
    form_schema = await self.get_form_schema(
        session_state['form_id'],
        vendor_id
    )

    # 3. 檢查離題情況
    digression_type = await self._detect_digression(user_message, form_schema)
    if digression_type:
        return await self._handle_digression(
            session_state,
            user_message,
            digression_type,
            form_schema
        )

    # 4. 驗證欄位
    current_field = form_schema['fields'][session_state['current_field_index']]
    is_valid, error_message = await self._validate_field(
        user_message,
        current_field
    )

    if not is_valid:
        return {
            "answer": f"❌ {error_message}\n\n{current_field['prompt']}",
            "validation_failed": True
        }

    # 5. 儲存欄位值
    collected_data = session_state.get('collected_data', {})
    collected_data[current_field['field_name']] = user_message

    # 6. 移動到下一個欄位
    next_index = session_state['current_field_index'] + 1

    if next_index >= len(form_schema['fields']):
        # 表單完成
        return await self._complete_form(session_state, form_schema, collected_data)
    else:
        # 繼續下一個欄位
        await self.update_session_state(
            session_id=session_id,
            current_field_index=next_index,
            collected_data=collected_data
        )

        next_field = form_schema['fields'][next_index]
        return {
            "answer": next_field['prompt'],
            "form_completed": False,
            "current_field": next_field['field_name']
        }
```

---

### 3. 離題處理 (Digression Handling)

**檔案**：`rag-orchestrator/services/form_manager.py`

當用戶在填表過程中提問時，提供三個選項：繼續、回答、取消。

```python
async def _handle_digression(
    self,
    session_state: Dict,
    user_message: str,
    digression_type: str,
    form_schema: Dict
) -> Dict:
    """
    處理離題情況

    離題類型:
    - "cancel": 用戶要取消表單
    - "question": 用戶問問題
    """
    session_id = session_state['session_id']

    # 1. 處理取消請求
    if digression_type == "cancel":
        await self.update_session_state(
            session_id=session_id,
            state=FormState.CANCELLED
        )

        # 檢查是否有待處理的問題
        pending_question = await asyncio.to_thread(
            self._get_pending_question_sync,
            session_id
        )

        if pending_question:
            return {
                "answer": "",
                "answer_pending_question": True,
                "pending_question": pending_question,
                "form_cancelled": True
            }
        else:
            return {
                "answer": "✅ 已取消表單填寫。"
            }

    # 2. 處理問題（離題）
    elif digression_type == "question":
        # 儲存待處理的問題
        await asyncio.to_thread(
            self._save_pending_question_sync,
            session_id,
            user_message
        )

        # 更新狀態為離題
        await self.update_session_state(
            session_id=session_id,
            state=FormState.DIGRESSION
        )

        # 提供三個選項
        return {
            "answer": f"💡 您的**{form_schema['form_name']}**還未完成，需要繼續填寫嗎？\n"
                     f"• 輸入「**繼續**」恢復填寫\n"
                     f"• 輸入「**回答**」回答您的問題\n"
                     f"• 輸入「**取消**」結束",
            "allow_resume": True,
            "pending_question": user_message
        }
```

#### 處理用戶選擇

```python
# 在 collect_form_field 函數開頭檢查狀態
if session_state['state'] == FormState.DIGRESSION:
    user_choice = user_message.strip()

    if user_choice in ["繼續", "continue"]:
        # 恢復填寫
        await self.update_session_state(
            session_id=session_id,
            state=FormState.COLLECTING
        )

        current_field = form_schema['fields'][session_state['current_field_index']]
        return {
            "answer": f"✅ 繼續填寫表單\n\n{current_field['prompt']}",
            "form_resumed": True
        }

    elif user_choice in ["回答", "回答問題", "answer"]:
        # 取消表單並回答問題
        pending_question = await asyncio.to_thread(
            self._get_pending_question_sync,
            session_id
        )

        await self.update_session_state(
            session_id=session_id,
            state=FormState.CANCELLED
        )

        if pending_question:
            return {
                "answer": "",
                "answer_pending_question": True,
                "pending_question": pending_question,
                "form_cancelled": True
            }

    elif user_choice in ["取消", "cancel"]:
        # 取消表單
        # ... 同上 cancel 處理
```

---

### 4. 表單完成與知識整合

**檔案**：`rag-orchestrator/services/form_manager.py`

表單完成後，從知識庫讀取答案並顯示。

```python
async def _complete_form(
    self,
    session_state: Dict,
    form_schema: Dict,
    collected_data: Dict
) -> Dict:
    """
    完成表單填寫
    """
    # 1. 更新會話狀態為已完成
    await self.update_session_state(
        session_id=session_state['session_id'],
        state=FormState.COMPLETED,
        collected_data=collected_data
    )

    # 2. 保存表單提交記錄
    submission_id = await self.save_form_submission(
        session_id=session_state['id'],
        form_id=session_state['form_id'],
        user_id=session_state['user_id'],
        vendor_id=session_state['vendor_id'],
        submitted_data=collected_data
    )

    # 3. 取得完成訊息（從知識庫讀取）
    completion_message = "✅ **表單填寫完成！**\n\n感謝您完成表單！我們會儘快處理您的資料。"

    knowledge_id = session_state.get('knowledge_id')
    if knowledge_id:
        # 從知識庫讀取答案
        knowledge_answer = await asyncio.to_thread(
            self._get_knowledge_answer_sync,
            knowledge_id
        )

        if knowledge_answer:
            completion_message = f"✅ **表單填寫完成！**\n\n{knowledge_answer}"

    return {
        "answer": completion_message,
        "form_completed": True,
        "submission_id": submission_id,
        "collected_data": collected_data
    }
```

**知識答案讀取**：

```python
def _get_knowledge_answer_sync(self, knowledge_id: int) -> Optional[str]:
    """從資料庫取得知識答案（同步）"""
    try:
        with get_db_cursor(dict_cursor=True) as cursor:
            cursor.execute("""
                SELECT answer
                FROM knowledge_base
                WHERE id = %s
            """, (knowledge_id,))
            result = cursor.fetchone()
            return result['answer'] if result else None
    except Exception as e:
        print(f"❌ 取得知識答案失敗: {e}")
        return None
```

---

### 5. Chat API 整合

**檔案**：`rag-orchestrator/routers/chat.py`

在主對話流程中整合表單處理。

#### 觸發表單

```python
# 在 _build_knowledge_response 函數中
if best_knowledge.get('form_id'):
    # 觸發表單
    form_intro = best_knowledge.get('form_intro') or \
                 f"我需要收集一些資料來幫助您。"

    form_result = await form_manager.trigger_form_by_knowledge(
        knowledge_id=best_knowledge['id'],
        form_id=best_knowledge['form_id'],
        intro_message=form_intro,
        session_id=request.session_id,
        user_id=request.user_id,
        vendor_id=request.vendor_id,
        trigger_question=request.message  # 儲存觸發問題
    )

    return _convert_form_result_to_response(form_result, request)
```

#### 處理表單取消與待處理問題

```python
# 在 vendor_chat_message 函數中
if form_result.get('form_cancelled'):
    pending_question = form_result.get('pending_question')

    if pending_question:
        # 替換 request.message 為待處理的問題
        request.message = pending_question
        # 繼續往下走正常流程（知識檢索）
    else:
        # 沒有待處理的問題，直接返回取消訊息
        return _convert_form_result_to_response(form_result, request)
else:
    # 表單未取消，返回表單結果
    return _convert_form_result_to_response(form_result, request)
```

---

## 📊 API 端點

### 1. 表單管理 API

#### 列出所有表單

```http
GET /rag-api/v1/forms?vendor_id=1&is_active=true
```

**Response**:
```json
[
  {
    "id": 1,
    "form_id": "rental_application",
    "form_name": "租屋申請表",
    "description": "用於收集租客租屋申請資料",
    "default_intro": "我需要收集一些資料來協助您租屋。",
    "fields": [...],
    "vendor_id": 1,
    "is_active": true,
    "created_at": "2025-01-10T10:00:00Z",
    "updated_at": "2025-01-10T10:00:00Z"
  }
]
```

#### 取得單一表單

```http
GET /rag-api/v1/forms/{form_id}
```

#### 創建表單

```http
POST /rag-api/v1/forms
Content-Type: application/json

{
  "form_id": "repair_request",
  "form_name": "維修申請表",
  "description": "用於收集維修申請資料",
  "default_intro": "請提供維修相關資訊",
  "fields": [
    {
      "field_name": "name",
      "field_label": "姓名",
      "field_type": "text",
      "prompt": "請提供您的姓名",
      "required": true,
      "validation_type": "taiwan_name",
      "max_length": 50
    },
    {
      "field_name": "issue",
      "field_label": "維修項目",
      "field_type": "select",
      "prompt": "請選擇維修項目（回覆編號）：\n1. 水電\n2. 門窗\n3. 其他",
      "required": true,
      "options": ["水電", "門窗", "其他"]
    }
  ],
  "vendor_id": 1,
  "is_active": true
}
```

#### 更新表單

```http
PUT /rag-api/v1/forms/{form_id}
Content-Type: application/json

{
  "form_name": "更新後的表單名稱",
  "is_active": false
}
```

#### 刪除表單

```http
DELETE /rag-api/v1/forms/{form_id}
```

---

### 2. 表單提交記錄 API

#### 查詢提交記錄

```http
GET /rag-api/v1/form-submissions?form_id=rental_application&vendor_id=1&limit=50&offset=0
```

**Response**:
```json
{
  "items": [
    {
      "id": 123,
      "form_id": "rental_application",
      "form_name": "租屋申請表",
      "user_id": "user_001",
      "vendor_id": 1,
      "vendor_name": "業者A",
      "submitted_data": {
        "name": "陳慶煌",
        "address": "新北市樹林區",
        "phone": "0911111111"
      },
      "submitted_at": "2025-01-10T14:30:00Z",
      "trigger_question": "我想租房子"
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

---

## 🎨 前端實作

### 表單提交記錄頁面

**檔案**：`knowledge-admin/frontend/src/views/FormSubmissionsView.vue`

#### 主要功能

1. **過濾器**：按表單、業者過濾
2. **列表顯示**：顯示提交記錄（含觸發問題）
3. **分頁**：支援大量資料分頁
4. **詳情 Modal**：查看完整提交資料

#### 關鍵代碼

```vue
<template>
  <div>
    <h2>📋 表單提交記錄</h2>

    <!-- 過濾器 -->
    <div class="toolbar">
      <div class="filters">
        <select v-model="filterFormId" @change="loadSubmissions">
          <option value="">全部表單</option>
          <option v-for="form in availableForms" :key="form.form_id" :value="form.form_id">
            {{ form.form_name }}
          </option>
        </select>

        <select v-model="filterVendorId" @change="loadSubmissions">
          <option value="">全部業者</option>
          <option v-for="vendor in availableVendors" :key="vendor.id" :value="vendor.id">
            {{ vendor.name }}
          </option>
        </select>
      </div>
    </div>

    <!-- 提交記錄列表 -->
    <div class="submissions-list">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>表單名稱</th>
            <th>業者</th>
            <th>用戶ID</th>
            <th>觸發問題</th>  <!-- 新增欄位 -->
            <th>提交資料</th>
            <th>提交時間</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in submissions" :key="item.id">
            <td>{{ item.id }}</td>
            <td>{{ item.form_name }}</td>
            <td>{{ item.vendor_name || '全域' }}</td>
            <td>{{ item.user_id }}</td>
            <td>
              <div class="trigger-question">
                {{ item.trigger_question || '-' }}  <!-- 顯示觸發問題 -->
              </div>
            </td>
            <td>
              <div class="submitted-data">
                <span v-for="(value, key) in item.submitted_data" :key="key">
                  <strong>{{ getFieldLabel(item.form_id, key) }}:</strong> {{ value }}
                </span>
              </div>
            </td>
            <td>{{ formatDate(item.submitted_at) }}</td>
            <td>
              <button @click="viewDetails(item)">詳情</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      submissions: [],
      availableForms: [],
      availableVendors: [],
      filterFormId: '',
      filterVendorId: '',
      formSchemas: {}
    };
  },
  async mounted() {
    await this.loadForms();
    await this.loadVendors();
    await this.loadSubmissions();
  },
  methods: {
    async loadSubmissions() {
      const params = {
        limit: 50,
        offset: 0
      };

      if (this.filterFormId) params.form_id = this.filterFormId;
      if (this.filterVendorId) params.vendor_id = this.filterVendorId;

      const response = await axios.get('/rag-api/v1/form-submissions', { params });
      this.submissions = response.data.items.map(item => ({
        ...item,
        submitted_data: typeof item.submitted_data === 'string'
          ? JSON.parse(item.submitted_data)
          : item.submitted_data
      }));
    },

    getFieldLabel(formId, fieldName) {
      const schema = this.formSchemas[formId];
      if (!schema?.fields) return fieldName;

      const field = schema.fields.find(f => f.field_name === fieldName);
      return field ? field.field_label : fieldName;
    }
  }
};
</script>
```

---

## 🧪 測試驗證

### 測試場景 1：完整表單流程

**用戶輸入**：
```
用戶: 我想租房子
系統: 我需要收集一些資料來協助您租屋。請提供您的姓名

用戶: 陳慶煌
系統: 請提供您的地址

用戶: 新北市樹林區
系統: 請提供您的聯絡電話

用戶: 0911111111
系統: ✅ 表單填寫完成！
      感謝您提交租屋申請！我們會在 3 個工作天內與您聯繫...
```

**驗證結果**：
- ✅ 表單正確觸發
- ✅ 所有欄位正確收集
- ✅ 表單完成訊息顯示知識庫答案
- ✅ 提交記錄正確儲存，包含觸發問題 "我想租房子"

---

### 測試場景 2：離題處理 - 回答問題

**用戶輸入**：
```
用戶: 我想租房子
系統: 我需要收集一些資料來協助您租屋。請提供您的姓名

用戶: 陳慶煌
系統: 請提供您的地址

用戶: 帳單怎麼繳？
系統: 💡 您的租屋申請表還未完成，需要繼續填寫嗎？
      • 輸入「繼續」恢復填寫
      • 輸入「回答」回答您的問題
      • 輸入「取消」結束

用戶: 回答
系統: [顯示帳單繳費相關答案...]
```

**驗證結果**：
- ✅ 離題偵測正確
- ✅ 三個選項顯示正確
- ✅ 選擇「回答」後取消表單
- ✅ 正確回答待處理問題

---

### 測試場景 3：離題處理 - 繼續填寫

**用戶輸入**：
```
用戶: 我想租房子
系統: 我需要收集一些資料來協助您租屋。請提供您的姓名

用戶: 陳慶煌
系統: 請提供您的地址

用戶: 帳單怎麼繳？
系統: 💡 您的租屋申請表還未完成，需要繼續填寫嗎？
      • 輸入「繼續」恢復填寫
      • 輸入「回答」回答您的問題
      • 輸入「取消」結束

用戶: 繼續
系統: ✅ 繼續填寫表單

      請提供您的地址

用戶: 新北市樹林區
系統: 請提供您的聯絡電話

用戶: 0911111111
系統: ✅ 表單填寫完成！...
```

**驗證結果**：
- ✅ 離題偵測正確
- ✅ 選擇「繼續」後恢復表單
- ✅ 欄位索引正確（回到地址欄位）
- ✅ 表單正常完成

---

## 🐛 常見問題與修復

### 問題 1：AttributeError - 'VendorChatRequest' object has no attribute 'question'

**錯誤訊息**：
```
AttributeError: 'VendorChatRequest' object has no attribute 'question'
```

**原因**：VendorChatRequest 模型使用 `message` 欄位，不是 `question`

**修復**：
```python
# ❌ 錯誤
trigger_question=request.question

# ✅ 正確
trigger_question=request.message
```

**檔案**：`rag-orchestrator/routers/chat.py:1155`

---

### 問題 2：表單收集中斷（第二個欄位後無法繼續）

**症狀**：
- 第一個欄位正常收集
- 第二、三個欄位輸入後系統回到知識檢索，沒有繼續表單流程

**原因**：
1. 資料庫中存在多個 `session_id` 相同的記錄
2. `_get_session_state_sync()` 使用 `ORDER BY last_activity_at DESC`
3. 當多個記錄的 `last_activity_at` 相同時，可能返回已取消的會話

**修復**：

**修復 1：變更排序欄位**
```python
# ❌ 錯誤（可能返回錯誤的記錄）
ORDER BY last_activity_at DESC

# ✅ 正確（返回最新的記錄）
ORDER BY id DESC
```

**修復 2：避免重複創建會話**
```python
# 在 trigger_form_by_knowledge 中新增檢查
existing_session = await self.get_session_state(session_id)
if existing_session and existing_session['state'] in ['COLLECTING', 'DIGRESSION']:
    # 已有進行中的表單會話，不重複創建
    session_state = existing_session
else:
    # 創建新的表單會話
    session_state = await self.create_form_session(...)
```

**修復 3：清理舊會話**
```sql
UPDATE form_sessions
SET state = 'CANCELLED', cancelled_at = NOW()
WHERE state IN ('COLLECTING', 'DIGRESSION');
```

**檔案**：`rag-orchestrator/services/form_manager.py:127-142, 418-436`

---

## 📈 效能考量

### 1. Session 查詢優化

**問題**：每次用戶輸入都要查詢 `form_sessions` 表

**優化**：
- 使用 `ORDER BY id DESC LIMIT 1` 提升查詢速度
- 建立索引：`CREATE INDEX idx_form_sessions_session ON form_sessions(session_id)`

### 2. Redis Cache

**建議**：將表單會話狀態快取到 Redis

```python
# 快取表單會話狀態
await redis_client.setex(
    f"form_session:{session_id}",
    3600,  # 1小時過期
    json.dumps(session_state)
)

# 讀取快取
cached = await redis_client.get(f"form_session:{session_id}")
if cached:
    session_state = json.loads(cached)
```

### 3. 表單結構快取

**建議**：表單結構不常變動，應該快取

```python
# 快取表單結構
await redis_client.setex(
    f"form_schema:{form_id}",
    86400,  # 24小時過期
    json.dumps(form_schema)
)
```

---

## 🚀 未來擴展

### 1. 更多欄位類型

- [ ] `checkbox` - 多選框
- [ ] `radio` - 單選框
- [ ] `file` - 檔案上傳
- [ ] `rating` - 評分
- [ ] `slider` - 滑桿

### 2. 條件邏輯

根據前一個欄位的答案，決定是否顯示下一個欄位。

```json
{
  "field_name": "pet_type",
  "field_label": "寵物類型",
  "field_type": "select",
  "prompt": "請選擇寵物類型",
  "options": ["貓", "狗", "其他"],
  "condition": {
    "field": "has_pet",
    "value": "是"
  }
}
```

### 3. 表單模板

提供常用表單模板，快速創建。

- 租屋申請表
- 維修申請表
- 退租申請表
- 訪客登記表

### 4. 表單版本控制

追蹤表單結構變更歷史。

```sql
CREATE TABLE form_schema_versions (
    id SERIAL PRIMARY KEY,
    form_id VARCHAR(100),
    version INTEGER,
    fields JSONB,
    created_at TIMESTAMP
);
```

### 5. Email 通知

表單提交後自動發送 Email 通知。

### 6. Webhook 整合

表單提交後呼叫外部 API。

---

## 📚 相關文件

- [知識管理系統](./KNOWLEDGE_IMPORT_FEATURE.md)
- [多意圖分類](./MULTI_INTENT_CLASSIFICATION.md)
- [API 參考文件](../api/API_REFERENCE_PHASE1.md)
- [系統架構](../architecture/SYSTEM_ARCHITECTURE.md)

---

**建立日期**: 2025-01-10
**最後更新**: 2025-01-10
**版本**: 1.0
**維護者**: Development Team
