# 🔍 SOP 類型分析與觸發模式設計

**日期**: 2026-01-22
**問題**: 並非所有 SOP 都需要「排查步驟」，如何優雅地支援不同類型的 SOP？

---

## 📊 實際 SOP 場景分析

### 類型 1：排查型 SOP（需要用戶先自行排查）

**特徵：**
- 問題可能是簡單故障，用戶自己能解決
- 需要提供排查步驟
- 排查無效後才觸發後續動作（表單/API）

**範例：**

#### 冷氣不冷
```
【排查步驟】
1️⃣ 檢查溫度設定（建議 24-26°C）
2️⃣ 檢查濾網是否堵塞
3️⃣ 確認室外機運轉
4️⃣ 等待 10-15 分鐘

若排查後仍不冷，請提交維修請求。
```
→ 用戶說「試過了，還是不冷」→ 觸發維修表單

#### 網路不通
```
【排查步驟】
1️⃣ 檢查路由器電源
2️⃣ 重啟路由器（拔插頭等 30 秒）
3️⃣ 檢查網路線是否鬆脫
4️⃣ 測試其他設備是否能連網

若仍無法連接，請提交報修。
```
→ 用戶說「還是不行」→ 觸發維修表單

---

### 類型 2：行動型 SOP（直接引導執行動作）

**特徵：**
- 內容是「如何做某事」的說明
- 用戶看完 SOP 後，可能想立即執行
- 不需要等關鍵詞，直接詢問是否要繼續

**範例：**

#### 租金繳納流程
```
【繳納方式】
1️⃣ 每月 5 日前繳納
2️⃣ 轉帳到指定帳戶
   銀行：XX銀行
   帳號：1234-5678-9012
3️⃣ 轉帳後請截圖傳送給管理員

📋 是否要登記本月租金繳納記錄？
```
→ **不需要等關鍵詞**，直接問「是否要登記？」
→ 用戶說「要」→ 觸發繳租登記表單

#### 訪客登記
```
【訪客登記規定】
1️⃣ 訪客需登記姓名、電話
2️⃣ 訪客時間：8:00-22:00
3️⃣ 過夜訪客需提前通知

📋 是否要登記訪客資訊？
```
→ 直接問「是否要登記？」
→ 用戶說「是」→ 觸發訪客登記表單

#### 提前退租流程
```
【提前退租須知】
1️⃣ 需提前 30 天通知
2️⃣ 違約金：1 個月租金
3️⃣ 押金扣除標準：...

📋 是否要提交退租申請？
```
→ 直接問「是否要提交？」
→ 用戶說「要」→ 觸發退租申請表單

---

### 類型 3：資訊型 SOP（純資訊，無後續動作）

**特徵：**
- 純粹提供資訊或規範
- 用戶看完就結束，不需要任何動作
- 無需觸發表單或 API

**範例：**

#### 垃圾收取規範
```
【垃圾收取時間】
🗑️ 一般垃圾：週一、三、五 19:00-20:00
♻️ 資源回收：週二、四 19:00-20:00
📦 大型垃圾：需預約（請聯絡管理員）

【注意事項】
- 請做好分類
- 請使用專用垃圾袋
- 逾時不收
```
→ 純資訊，無需後續動作

#### 公共設施使用規定
```
【健身房使用規定】
⏰ 開放時間：6:00-22:00
👕 請穿著運動服裝
🧹 使用後請擦拭器材
📵 禁止大聲喧嘩

【游泳池使用規定】
⏰ 開放時間：7:00-21:00
🏊 需戴泳帽
🚫 禁止跳水
```
→ 純資訊，無需後續動作

---

### 類型 4：緊急型 SOP（立即觸發，無需確認）

**特徵：**
- 緊急危險情況
- 返回 SOP 的同時，自動觸發緊急報修
- 無需等用戶確認

**範例：**

#### 天花板漏水
```
🚨 這是緊急狀況！請立即採取措施：

【緊急處理】
1️⃣ 使用容器收集漏水
2️⃣ 關閉附近電源
3️⃣ 移開貴重物品
4️⃣ 拍照記錄

⚡ 我已自動為您提交緊急維修請求，維修人員會在 1 小時內聯絡您。
工單編號：MT20260122001
```
→ **不需要任何確認**，自動觸發緊急維修 API

#### 瓦斯外洩
```
⛔ 危險！請立即執行：

1️⃣ 關閉瓦斯總開關
2️⃣ 打開所有門窗
3️⃣ 不要開關電器
4️⃣ 立即離開現場
5️⃣ 撥打 119

⚡ 我已通知管理人員，請務必遵循上述步驟。
緊急聯絡電話：0912-345-678
```
→ **自動發送緊急通知**，無需等待

---

## 🎯 解決方案：trigger_mode 欄位

### 新增欄位設計

```sql
ALTER TABLE vendor_sop_items
ADD COLUMN trigger_mode VARCHAR(20) DEFAULT 'none';

-- 約束
ALTER TABLE vendor_sop_items
ADD CONSTRAINT check_trigger_mode
CHECK (trigger_mode IN ('none', 'manual', 'immediate', 'auto'));
```

### trigger_mode 類型說明

| trigger_mode | 說明 | 適用場景 | 行為 |
|--------------|------|----------|------|
| **none** | 無後續動作 | 資訊型 SOP | 只返回 SOP 內容，結束 |
| **manual** | 手動觸發 | 排查型 SOP | 返回 SOP → 等用戶說關鍵詞 → 觸發 |
| **immediate** | 立即詢問 | 行動型 SOP | 返回 SOP → 立即問「是否要執行？」→ 觸發 |
| **auto** | 自動觸發 | 緊急型 SOP | 返回 SOP → 同時自動觸發 API/表單 |

---

## 💬 對話流程對比

### 場景 A：排查型（trigger_mode = 'manual'）

```
用戶：「冷氣不冷」
  ↓
系統：【排查步驟】
      1️⃣ 檢查溫度設定...
      若排查後仍不冷，請提交維修請求。
  ↓
（等待用戶回覆）
  ↓
用戶：「試過了，還是不冷」← 包含關鍵詞
  ↓
系統：好的，我來協助您提交維修請求。
      請說明問題發生的具體位置？
```

---

### 場景 B：行動型（trigger_mode = 'immediate'）

```
用戶：「如何繳租金」
  ↓
系統：【繳納方式】
      1️⃣ 每月 5 日前繳納
      2️⃣ 轉帳到指定帳戶...

      📋 是否要登記本月租金繳納記錄？
      （回覆「是」或「要」即可開始登記）
  ↓
用戶：「要」
  ↓
系統：好的，我來協助您登記繳租記錄。
      請提供繳納日期？
```

**關鍵差異：**
- ✅ 不需要配置 `trigger_keywords`
- ✅ 系統主動問「是否要執行？」
- ✅ 用戶只需簡單回答「是/要/好」

---

### 場景 C：資訊型（trigger_mode = 'none'）

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

---

### 場景 D：緊急型（trigger_mode = 'auto'）

```
用戶：「天花板漏水」
  ↓
系統：🚨 這是緊急狀況！請立即採取措施：
      1️⃣ 使用容器收集漏水...

      ⚡ 我已自動為您提交緊急維修請求。
      工單編號：MT20260122001
      維修人員會在 1 小時內聯絡您。
  ↓
（同時後台已自動調用 API，創建緊急工單）
```

---

## 🗄️ 完整資料庫設計

```sql
ALTER TABLE vendor_sop_items
-- 基本欄位（已有）
-- id, item_name, content, category_id, group_id, vendor_id, is_active...

-- 後續動作配置
ADD COLUMN IF NOT EXISTS next_action VARCHAR(50) DEFAULT 'none',
ADD COLUMN IF NOT EXISTS next_form_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS next_api_config JSONB,
ADD COLUMN IF NOT EXISTS followup_prompt TEXT,

-- 觸發模式（新增）
ADD COLUMN IF NOT EXISTS trigger_mode VARCHAR(20) DEFAULT 'none',
ADD COLUMN IF NOT EXISTS trigger_keywords TEXT[],           -- 僅 manual 模式需要
ADD COLUMN IF NOT EXISTS immediate_prompt TEXT,             -- 僅 immediate 模式需要

-- 約束
ADD CONSTRAINT check_next_action
CHECK (next_action IN ('none', 'form_fill', 'api_call', 'form_then_api')),

ADD CONSTRAINT check_trigger_mode
CHECK (trigger_mode IN ('none', 'manual', 'immediate', 'auto'));
```

### 欄位使用場景

| trigger_mode | trigger_keywords | immediate_prompt | followup_prompt |
|--------------|------------------|------------------|-----------------|
| **none** | ❌ 不需要 | ❌ 不需要 | ❌ 不需要 |
| **manual** | ✅ 必須 | ❌ 不需要 | ✅ 必須 |
| **immediate** | ❌ 不需要 | ✅ 必須 | ✅ 必須 |
| **auto** | ❌ 不需要 | ❌ 不需要 | ✅ 可選 |

### 範例配置

#### 範例 1：排查型（manual）
```sql
INSERT INTO vendor_sop_items (
    item_name,
    content,
    trigger_mode,
    next_action,
    next_form_id,
    trigger_keywords,
    followup_prompt
) VALUES (
    '冷氣不冷',
    '【排查步驟】\n1️⃣ 檢查溫度...\n若排查後仍不冷，請提交維修請求。',
    'manual',  -- 等用戶說關鍵詞
    'form_then_api',
    'maintenance_troubleshooting',
    ARRAY['還是不冷', '試過了', '需要維修'],
    '好的，我來協助您提交維修請求。'
);
```

#### 範例 2：行動型（immediate）
```sql
INSERT INTO vendor_sop_items (
    item_name,
    content,
    trigger_mode,
    next_action,
    next_form_id,
    immediate_prompt,
    followup_prompt
) VALUES (
    '租金繳納流程',
    '【繳納方式】\n1️⃣ 每月 5 日前繳納...',
    'immediate',  -- 立即詢問
    'form_fill',
    'rent_payment_registration',
    '📋 是否要登記本月租金繳納記錄？\n（回覆「是」或「要」即可開始登記）',
    '好的，我來協助您登記繳租記錄。'
);
```

#### 範例 3：資訊型（none）
```sql
INSERT INTO vendor_sop_items (
    item_name,
    content,
    trigger_mode,
    next_action
) VALUES (
    '垃圾收取規範',
    '【垃圾收取時間】\n🗑️ 一般垃圾：週一、三、五...',
    'none',  -- 無後續動作
    'none'
);
```

#### 範例 4：緊急型（auto）
```sql
INSERT INTO vendor_sop_items (
    item_name,
    content,
    trigger_mode,
    next_action,
    next_api_config,
    followup_prompt
) VALUES (
    '天花板漏水',
    '🚨 這是緊急狀況！\n【緊急處理】\n1️⃣ 使用容器收集漏水...',
    'auto',  -- 自動觸發
    'api_call',
    '{
        "endpoint": "maintenance_request",
        "params": {
            "problem_category": "water_leak",
            "specific_problem": "ceiling_leak",
            "urgency_level": "critical",
            "auto_dispatch": true
        }
    }'::jsonb,
    '⚡ 我已自動為您提交緊急維修請求。'
);
```

---

## 💻 實現邏輯

### chat.py - _build_sop_response 修改

```python
async def _build_sop_response(..., sop_items):
    """構建 SOP 回應"""
    sop_item = sop_items[0]
    trigger_mode = sop_item.get('trigger_mode', 'none')

    # 1. 格式化 SOP 內容
    raw_answer = _format_sop_answer(sop_items, group_name)
    final_answer = _clean_answer(raw_answer, vendor_id)

    # 2. 根據 trigger_mode 處理
    if trigger_mode == 'none':
        # 純資訊，直接返回
        return VendorChatResponse(answer=final_answer, ...)

    elif trigger_mode == 'manual':
        # 排查型：記錄 context，等關鍵詞
        await save_sop_context(
            session_id=request.session_id,
            user_id=request.user_id,
            sop_item_id=sop_item['id'],
            trigger_mode='manual',
            trigger_keywords=sop_item['trigger_keywords'],
            next_action=sop_item['next_action'],
            next_form_id=sop_item.get('next_form_id'),
            next_api_config=sop_item.get('next_api_config'),
            followup_prompt=sop_item.get('followup_prompt')
        )
        return VendorChatResponse(answer=final_answer, ...)

    elif trigger_mode == 'immediate':
        # 行動型：附加詢問提示
        immediate_prompt = sop_item.get('immediate_prompt', '是否要繼續？')
        combined_answer = f"{final_answer}\n\n{immediate_prompt}"

        # 記錄 context（等用戶說「是/要/好」）
        await save_sop_context(
            session_id=request.session_id,
            user_id=request.user_id,
            sop_item_id=sop_item['id'],
            trigger_mode='immediate',
            trigger_keywords=['是', '要', '好', '可以', '需要'],  # 通用肯定詞
            next_action=sop_item['next_action'],
            next_form_id=sop_item.get('next_form_id'),
            next_api_config=sop_item.get('next_api_config'),
            followup_prompt=sop_item.get('followup_prompt')
        )
        return VendorChatResponse(answer=combined_answer, ...)

    elif trigger_mode == 'auto':
        # 緊急型：立即觸發
        if sop_item['next_action'] == 'api_call':
            api_result = await execute_api_call_immediately(
                api_config=sop_item['next_api_config'],
                session_data={...}
            )

            # 附加 API 結果到回應
            followup = sop_item.get('followup_prompt', '')
            if api_result.get('success'):
                ticket_number = api_result.get('ticket_number')
                combined_answer = f"{final_answer}\n\n{followup}\n工單編號：{ticket_number}"
            else:
                combined_answer = f"{final_answer}\n\n{followup}"

            return VendorChatResponse(answer=combined_answer, ...)

        elif sop_item['next_action'] in ['form_fill', 'form_then_api']:
            # 自動啟動表單（罕見，但支援）
            return await trigger_form_from_sop(request, sop_item)
```

---

## 🎨 UI 設計調整

### 編輯 SOP Modal - 新增觸發模式選擇

```html
<div class="form-group">
  <label>🔄 後續動作觸發模式</label>
  <p class="hint">選擇何時觸發後續動作</p>

  <div class="radio-group">
    <label class="radio-option">
      <input type="radio" v-model="editingForm.trigger_mode" value="none" />
      <div class="radio-content">
        <strong>無後續動作</strong>
        <p>純資訊 SOP，看完就結束（例如：垃圾收取規範）</p>
      </div>
    </label>

    <label class="radio-option">
      <input type="radio" v-model="editingForm.trigger_mode" value="manual" />
      <div class="radio-content">
        <strong>⏸️ 等待用戶確認後觸發</strong>
        <p>適合排查型 SOP，用戶排查無效後說關鍵詞才觸發（例如：冷氣不冷）</p>
      </div>
    </label>

    <label class="radio-option recommended">
      <input type="radio" v-model="editingForm.trigger_mode" value="immediate" />
      <div class="radio-content">
        <strong>▶️ 立即詢問是否執行</strong>
        <span class="badge badge-primary">推薦</span>
        <p>適合行動型 SOP，看完後立即問是否要執行（例如：租金繳納）</p>
      </div>
    </label>

    <label class="radio-option warning">
      <input type="radio" v-model="editingForm.trigger_mode" value="auto" />
      <div class="radio-content">
        <strong>⚡ 自動觸發（緊急）</strong>
        <span class="badge badge-danger">謹慎使用</span>
        <p>適合緊急型 SOP，返回 SOP 的同時自動觸發（例如：天花板漏水）</p>
      </div>
    </label>
  </div>
</div>

<!-- 根據 trigger_mode 動態顯示不同欄位 -->

<!-- trigger_mode = 'manual' 時顯示 -->
<div v-if="editingForm.trigger_mode === 'manual'" class="form-group">
  <label>🔑 觸發關鍵詞 *</label>
  <textarea
    v-model="triggerKeywordsText"
    rows="4"
    placeholder="還是不行&#10;試過了&#10;需要維修"
  ></textarea>
  <p class="hint">用戶說出這些詞後才觸發</p>
</div>

<!-- trigger_mode = 'immediate' 時顯示 -->
<div v-if="editingForm.trigger_mode === 'immediate'" class="form-group">
  <label>💬 詢問提示語 *</label>
  <textarea
    v-model="editingForm.immediate_prompt"
    rows="2"
    placeholder="📋 是否要登記本月租金繳納記錄？&#10;（回覆「是」或「要」即可開始登記）"
  ></textarea>
  <p class="hint">附加在 SOP 內容後面，詢問用戶是否要執行</p>
</div>

<!-- trigger_mode != 'none' 時都顯示 -->
<div v-if="editingForm.trigger_mode !== 'none'" class="form-group">
  <label>📋 要觸發的動作 *</label>
  <select v-model="editingForm.next_action">
    <option value="form_fill">填寫表單</option>
    <option value="api_call">調用 API</option>
    <option value="form_then_api">填寫表單後調用 API</option>
  </select>
</div>
```

---

## 📊 對比總結

| 項目 | none | manual | immediate | auto |
|------|------|--------|-----------|------|
| **用途** | 純資訊 | 排查後報修 | 直接行動 | 緊急處理 |
| **範例** | 垃圾規範 | 冷氣不冷 | 繳租登記 | 天花板漏水 |
| **觸發時機** | 無 | 用戶說關鍵詞 | SOP 返回時 | SOP 返回時 |
| **關鍵詞** | ❌ | ✅ 自定義 | ✅ 通用（是/要） | ❌ |
| **詢問提示** | ❌ | ❌ | ✅ 自定義 | ❌ |
| **用戶確認** | ❌ | ✅ | ✅ | ❌ 自動執行 |

---

## ✅ 推薦實施方案

### 最小化調整（推薦）

1. **新增欄位**：
   - `trigger_mode` VARCHAR(20) DEFAULT 'manual'
   - `immediate_prompt` TEXT

2. **保持現有欄位**：
   - `trigger_keywords` - manual 和 immediate 都用（immediate 用通用詞）
   - `followup_prompt` - 觸發後的引導語

3. **邏輯調整**：
   - `trigger_mode = 'none'` → 直接返回，不記錄 context
   - `trigger_mode = 'manual'` → 記錄 context，用自定義關鍵詞
   - `trigger_mode = 'immediate'` → 附加詢問提示 + 記錄 context，用通用關鍵詞
   - `trigger_mode = 'auto'` → 立即執行 API/表單

---

**文檔版本**: 1.0
**最後更新**: 2026-01-22
