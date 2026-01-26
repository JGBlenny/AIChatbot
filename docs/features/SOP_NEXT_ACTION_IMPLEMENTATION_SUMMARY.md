# 🚀 SOP 後續動作功能 - 完整實施總結

**日期**: 2026-01-22
**狀態**: 設計完成，待實施

---

## 📋 功能概述

為 `vendor_sop_items` 新增後續動作能力，支援 **4 種 SOP 類型**：

| 類型 | trigger_mode | 使用場景 | 範例 |
|------|--------------|----------|------|
| **資訊型** | `none` | 純資訊，無後續動作 | 垃圾收取規範 |
| **排查型** | `manual` | 先排查，無效後說關鍵詞才觸發 | 冷氣不冷 |
| **行動型** | `immediate` | 返回 SOP 後立即詢問是否執行 | 租金繳納登記 |
| **緊急型** | `auto` | 返回 SOP 的同時自動觸發 | 天花板漏水 |

---

## 🗄️ 資料庫變更

### 新增欄位（7 個）

```sql
ALTER TABLE vendor_sop_items
ADD COLUMN trigger_mode VARCHAR(20) DEFAULT 'none',
ADD COLUMN next_action VARCHAR(50) DEFAULT 'none',
ADD COLUMN next_form_id VARCHAR(100),
ADD COLUMN next_api_config JSONB,
ADD COLUMN trigger_keywords TEXT[],
ADD COLUMN immediate_prompt TEXT,
ADD COLUMN followup_prompt TEXT;
```

### 欄位說明

| 欄位 | 類型 | 預設值 | 說明 | 使用場景 |
|------|------|--------|------|----------|
| `trigger_mode` | VARCHAR(20) | 'none' | 觸發模式 | 所有類型 |
| `next_action` | VARCHAR(50) | 'none' | 後續動作類型 | manual/immediate/auto |
| `next_form_id` | VARCHAR(100) | NULL | 要觸發的表單 ID | form_fill/form_then_api |
| `next_api_config` | JSONB | NULL | API 配置 | api_call/form_then_api |
| `trigger_keywords` | TEXT[] | NULL | 觸發關鍵詞 | manual/immediate |
| `immediate_prompt` | TEXT | NULL | 立即詢問提示語 | immediate |
| `followup_prompt` | TEXT | NULL | 觸發後引導語 | manual/immediate/auto |

### Migration 文件

✅ **已準備**：`database/migrations/add_sop_next_action_fields.sql`

---

## 💬 對話流程範例

### 場景 A：排查型（manual）

```
用戶：「冷氣不冷」
  ↓
系統：【排查步驟】
      1️⃣ 檢查溫度設定...
      2️⃣ 檢查濾網...
      若排查後仍不冷，請提交維修請求。
  ↓
（記錄 SOP context，等待關鍵詞）
  ↓
用戶：「試過了，還是不冷」← 包含 trigger_keywords
  ↓
系統：好的，我來協助您提交維修請求。（followup_prompt）
      請說明問題發生的具體位置？
  ↓
（開始填寫表單 maintenance_troubleshooting）
```

**配置範例**：
```sql
trigger_mode = 'manual'
next_action = 'form_then_api'
next_form_id = 'maintenance_troubleshooting'
trigger_keywords = ARRAY['還是不冷', '試過了', '需要維修']
followup_prompt = '好的，我來協助您提交維修請求。'
next_api_config = '{"endpoint": "maintenance_request", "params": {...}}'
```

---

### 場景 B：行動型（immediate）

```
用戶：「如何繳租金」
  ↓
系統：【繳納方式】
      1️⃣ 每月 5 日前繳納...
      2️⃣ 轉帳到指定帳戶...

      📋 是否要登記本月租金繳納記錄？← immediate_prompt
      （回覆「是」或「要」即可開始登記）
  ↓
（記錄 SOP context，使用通用肯定詞）
  ↓
用戶：「要」← 包含通用 trigger_keywords
  ↓
系統：好的，我來協助您登記繳租記錄。（followup_prompt）
      請提供繳納日期？
  ↓
（開始填寫表單 rent_payment_registration）
```

**配置範例**：
```sql
trigger_mode = 'immediate'
next_action = 'form_fill'
next_form_id = 'rent_payment_registration'
trigger_keywords = ARRAY['是', '要', '好', '可以']  -- 通用肯定詞
immediate_prompt = '📋 是否要登記本月租金繳納記錄？\n（回覆「是」或「要」即可開始登記）'
followup_prompt = '好的，我來協助您登記繳租記錄。'
```

---

### 場景 C：資訊型（none）

```
用戶：「垃圾收取時間」
  ↓
系統：【垃圾收取時間】
      🗑️ 一般垃圾：週一、三、五 19:00-20:00
      ♻️ 資源回收：週二、四 19:00-20:00
      ...
  ↓
（結束，無後續動作）
```

**配置範例**：
```sql
trigger_mode = 'none'
next_action = 'none'
-- 其他欄位都是 NULL
```

---

### 場景 D：緊急型（auto）

```
用戶：「天花板漏水」
  ↓
系統：🚨 這是緊急狀況！請立即採取措施：
      1️⃣ 使用容器收集漏水...
      2️⃣ 關閉電源...

      ⚡ 我已自動為您提交緊急維修請求。（followup_prompt）
      工單編號：MT20260122001
      維修人員會在 1 小時內聯絡您。
  ↓
（同時後台自動調用 API，創建緊急工單）
```

**配置範例**：
```sql
trigger_mode = 'auto'
next_action = 'api_call'
next_api_config = '{
    "endpoint": "maintenance_request",
    "params": {
        "problem_category": "water_leak",
        "specific_problem": "ceiling_leak",
        "urgency_level": "critical",
        "auto_dispatch": true
    }
}'
followup_prompt = '⚡ 我已自動為您提交緊急維修請求。'
```

---

## 💻 後端實作要點

### 1. chat.py - _build_sop_response 修改

```python
async def _build_sop_response(..., sop_items):
    sop_item = sop_items[0]
    trigger_mode = sop_item.get('trigger_mode', 'none')

    # 格式化 SOP 內容
    final_answer = _format_and_clean_sop(sop_items)

    if trigger_mode == 'none':
        # 純資訊，直接返回
        return VendorChatResponse(answer=final_answer, ...)

    elif trigger_mode == 'manual':
        # 排查型：記錄 context，等關鍵詞
        await save_sop_context(session_id, user_id, sop_item, mode='manual')
        return VendorChatResponse(answer=final_answer, ...)

    elif trigger_mode == 'immediate':
        # 行動型：附加詢問提示
        immediate_prompt = sop_item.get('immediate_prompt', '')
        combined_answer = f"{final_answer}\n\n{immediate_prompt}"
        await save_sop_context(session_id, user_id, sop_item, mode='immediate')
        return VendorChatResponse(answer=combined_answer, ...)

    elif trigger_mode == 'auto':
        # 緊急型：立即觸發
        api_result = await execute_api_immediately(sop_item['next_api_config'], ...)
        followup = sop_item.get('followup_prompt', '')
        ticket_number = api_result.get('ticket_number', '')
        combined_answer = f"{final_answer}\n\n{followup}\n工單編號：{ticket_number}"
        return VendorChatResponse(answer=combined_answer, ...)
```

### 2. chat.py - vendor_chat 開頭檢查

```python
async def vendor_chat(request: VendorChatRequest):
    # Step 1: 檢查是否有待處理的 SOP 後續動作
    sop_context = await get_sop_context(request.session_id, request.user_id)

    if sop_context and not sop_context['is_triggered']:
        # 檢查關鍵詞
        if check_trigger_keywords(request.message, sop_context['trigger_keywords']):
            # 標記為已觸發
            await mark_sop_context_triggered(sop_context['id'])

            # 根據 next_action 執行
            if sop_context['next_action'] in ['form_fill', 'form_then_api']:
                return await trigger_form_from_sop(request, sop_context)
            elif sop_context['next_action'] == 'api_call':
                return await trigger_api_from_sop(request, sop_context)

    # 原有流程...
```

### 3. 新增函數

```python
async def save_sop_context(session_id, user_id, sop_item, mode):
    """儲存 SOP context 到 Redis/DB"""
    # 根據 mode 設定不同的 trigger_keywords
    if mode == 'immediate':
        keywords = ['是', '要', '好', '可以', '需要']  # 通用肯定詞
    else:
        keywords = sop_item.get('trigger_keywords', [])

    context = {
        'sop_item_id': sop_item['id'],
        'trigger_mode': mode,
        'next_action': sop_item['next_action'],
        'next_form_id': sop_item.get('next_form_id'),
        'next_api_config': sop_item.get('next_api_config'),
        'trigger_keywords': keywords,
        'followup_prompt': sop_item.get('followup_prompt'),
        'is_triggered': False,
        'created_at': datetime.now().isoformat()
    }

    # 儲存到 Redis（1小時過期）
    await redis_client.setex(
        f"sop_context:{session_id}:{user_id}",
        3600,
        json.dumps(context)
    )

async def trigger_form_from_sop(request, sop_context):
    """從 SOP 觸發表單"""
    # 顯示引導語
    # 啟動表單
    # 預填資料（從 next_api_config.params）
    # 如果是 form_then_api，記錄 API callback

async def trigger_api_from_sop(request, sop_context):
    """從 SOP 直接觸發 API"""
    # 調用 API
    # 返回結果
```

---

## 🎨 前端 UI 修改

### VendorSOPManager.vue - 編輯 Modal 新增

```html
<div class="form-group">
  <label>🔄 後續動作觸發模式</label>

  <div class="radio-group">
    <label class="radio-option">
      <input type="radio" v-model="editingForm.trigger_mode" value="none" />
      <div class="radio-content">
        <strong>無後續動作</strong>
        <p>純資訊 SOP（例如：垃圾規範）</p>
      </div>
    </label>

    <label class="radio-option">
      <input type="radio" v-model="editingForm.trigger_mode" value="manual" />
      <div class="radio-content">
        <strong>⏸️ 等待用戶確認後觸發</strong>
        <p>排查型 SOP（例如：冷氣不冷）</p>
      </div>
    </label>

    <label class="radio-option recommended">
      <input type="radio" v-model="editingForm.trigger_mode" value="immediate" />
      <div class="radio-content">
        <strong>▶️ 立即詢問是否執行</strong>
        <p>行動型 SOP（例如：租金繳納）</p>
      </div>
    </label>

    <label class="radio-option warning">
      <input type="radio" v-model="editingForm.trigger_mode" value="auto" />
      <div class="radio-content">
        <strong>⚡ 自動觸發（緊急）</strong>
        <p>緊急型 SOP（例如：天花板漏水）</p>
      </div>
    </label>
  </div>
</div>

<!-- 根據 trigger_mode 動態顯示 -->
<div v-if="editingForm.trigger_mode === 'manual'">
  <label>🔑 觸發關鍵詞</label>
  <textarea v-model="triggerKeywordsText" placeholder="還是不行&#10;試過了"></textarea>
</div>

<div v-if="editingForm.trigger_mode === 'immediate'">
  <label>💬 詢問提示語</label>
  <textarea v-model="editingForm.immediate_prompt"></textarea>
</div>

<div v-if="editingForm.trigger_mode !== 'none'">
  <label>📋 要觸發的動作</label>
  <select v-model="editingForm.next_action">
    <option value="form_fill">填寫表單</option>
    <option value="api_call">調用 API</option>
    <option value="form_then_api">填寫表單後調用 API</option>
  </select>
</div>
```

---

## 📁 相關文檔

| 文檔 | 路徑 | 內容 |
|------|------|------|
| **Migration 腳本** | `database/migrations/add_sop_next_action_fields.sql` | 資料庫變更（7個新欄位） |
| **SOP 範例資料** | `database/migrations/insert_maintenance_sop_examples.sql` | 4個維護 SOP 範例 |
| **對話流程設計** | `docs/features/SOP_CONVERSATION_FLOW_2026-01-22.md` | 完整對話流程與實現邏輯 |
| **UI 設計** | `docs/features/SOP_UI_DESIGN_2026-01-22.md` | 前端介面設計與實作 |
| **類型分析** | `docs/features/SOP_TYPES_ANALYSIS_2026-01-22.md` | 4種 SOP 類型詳細分析 |
| **原始規劃** | `docs/features/MAINTENANCE_REQUEST_SYSTEM_PLAN_2026-01-22.md` | 最初的維護系統規劃 |

---

## ✅ 實施步驟

### Phase 1: 資料庫準備（1 天）

- [ ] 1. 執行 migration: `add_sop_next_action_fields.sql`
- [ ] 2. 驗證欄位新增成功
- [ ] 3. （可選）執行範例資料: `insert_maintenance_sop_examples.sql`

### Phase 2: 後端實作（3-4 天）

- [ ] 4. 修改 `vendor_sop_retriever.py` - 查詢包含新欄位
- [ ] 5. 修改 `chat.py - _build_sop_response` - 根據 trigger_mode 處理
- [ ] 6. 修改 `chat.py - vendor_chat` - 開頭檢查 SOP context
- [ ] 7. 新增 `save_sop_context` 函數
- [ ] 8. 新增 `get_sop_context` 函數
- [ ] 9. 新增 `trigger_form_from_sop` 函數
- [ ] 10. 新增 `trigger_api_from_sop` 函數
- [ ] 11. 新增 `check_trigger_keywords` 函數
- [ ] 12. 修改 `form_manager.py` - 支援 API callback

### Phase 3: 前端實作（2-3 天）

- [ ] 13. 修改 `VendorSOPManager.vue` - 新增 trigger_mode 選擇
- [ ] 14. 新增 immediate_prompt 輸入欄位
- [ ] 15. 更新保存邏輯（包含新欄位）
- [ ] 16. 新增效果預覽功能
- [ ] 17. 新增快速範本功能

### Phase 4: 測試與優化（2 天）

- [ ] 18. 端到端測試：資訊型 SOP
- [ ] 19. 端到端測試：排查型 SOP
- [ ] 20. 端到端測試：行動型 SOP
- [ ] 21. 端到端測試：緊急型 SOP
- [ ] 22. 關鍵詞匹配測試（同義詞、誤判）
- [ ] 23. Session 過期測試
- [ ] 24. 優化用戶體驗

---

## 🎯 驗收標準

### 功能驗收

✅ **資訊型 SOP**
- [ ] 返回 SOP 內容後，對話結束
- [ ] 不記錄 SOP context
- [ ] 用戶繼續提問時，正常處理新問題

✅ **排查型 SOP**
- [ ] 返回 SOP 排查步驟
- [ ] 記錄 SOP context（1小時過期）
- [ ] 用戶說觸發關鍵詞時，自動觸發表單
- [ ] 預填 SOP 提供的資訊
- [ ] 表單完成後自動調用 API

✅ **行動型 SOP**
- [ ] 返回 SOP 內容 + 詢問提示語
- [ ] 記錄 SOP context（使用通用肯定詞）
- [ ] 用戶說「是/要/好」時，觸發表單
- [ ] 引導語正確顯示

✅ **緊急型 SOP**
- [ ] 返回 SOP 緊急處理步驟
- [ ] 同時自動調用 API
- [ ] 顯示工單編號
- [ ] 不需要用戶確認

### UI 驗收

- [ ] trigger_mode 選擇清楚易懂
- [ ] 根據選擇動態顯示相關欄位
- [ ] 快速插入功能正常
- [ ] 保存時正確驗證必填欄位
- [ ] 編輯時正確載入現有配置

---

## 📊 預期效果

### 用戶體驗

- ✅ **自然流暢**：排查 → 報修 無縫銜接
- ✅ **減少輸入**：SOP 預填資訊，用戶只需補充細節
- ✅ **智能引導**：不同場景使用不同觸發模式
- ✅ **緊急響應**：緊急情況自動派工，無需等待

### 業務價值

- ✅ **提升滿意度**：快速響應維修需求
- ✅ **降低成本**：自助排查減少無效報修
- ✅ **提高效率**：自動化工單創建與派工
- ✅ **數據追蹤**：完整記錄問題與處理流程

---

## ⚠️ 注意事項

### 開發注意

1. **Session 過期**：SOP context 1小時過期，避免長時間等待
2. **重複觸發防護**：同一 context 只能觸發一次
3. **關鍵詞誤判**：immediate 模式可考慮二次確認
4. **API 失敗處理**：auto 模式 API 失敗時的降級策略

### 運維注意

1. **監控 Redis**：SOP context 儲存在 Redis，需監控容量
2. **日誌記錄**：記錄觸發事件，便於分析和優化
3. **關鍵詞優化**：根據實際使用調整 trigger_keywords

---

## 🔗 相關系統

- **表單系統**：form_schemas, form_sessions, form_submissions
- **知識庫系統**：knowledge_base（參考 action_type 實現）
- **API 系統**：api_endpoints（參考 endpoint 配置）
- **SOP 系統**：vendor_sop_items, vendor_sop_categories

---

**文檔版本**: 1.0
**最後更新**: 2026-01-22
**總預估工時**: 8-10 天
**優先級**: Medium

