# 研究記錄：option-routing

> 建立時間：2026-06-20
> 發現流程：輕量（Light）—— 擴充型功能，整合導向。

## 摘要

### 調查範圍
擴充既有 form-chaining，將「後續路由」來源從表單層下放到選項層，實現依答案分歧的決策樹。聚焦整合點、選項解析、回應承載與向後相容。

### 關鍵發現
- form-chaining 引擎（`_maybe_chain_next_form` / `_present_first_field` / `_complete_form` 串接段 / `branch_answer`）可整段重用，新機制只需「換掉路由來源」。
- `_maybe_chain_next_form(form_schema, session_state)` 呼叫時**未帶 `collected_data`**（`form_manager.py:2334`）——選項值取不到，為主要整合阻點。
- `QuickReply` 僅 `text`/`value`/`style`、`VendorChatResponse` 無連結欄位 → **URL 葉出口宜以「含連結的知識答案」承載**，免新欄位。
- select 選項解析既有於 `collect_field_data`（~1187），選項僅 `label`/`value`，可在 JSONB 加路由欄位、無需 migration。

## 研究主題

### 主題 1：選項值在完成時的可得性（整合阻點）
- **發現**：`_complete_form(session_state, form_schema, collected_data)` 持有新鮮 `collected_data`，但呼叫串接時未傳入；`session_state['collected_data']` 為完成前快照不可靠。
- **結論**：`_maybe_chain_next_form` 新增可選參數 `collected_data`（預設 None 保相容）；以終端 select 欄位 `field_name` → `collected_data[field_name]` 取被選 value → 比對 `options` 取 option 路由。

### 主題 2：URL 葉出口承載
- **發現**：`QuickReply(text,value,style)` 無 URL 動作；`VendorChatResponse` 無 redirect/link 欄位（僅 `answer`/`quick_replies`/`video_url`）。
- **結論**：URL 葉出口＝一筆知識其 `answer` 內含 markdown 連結（`/pricing` 等），經 `branch_answer`(answer_kb) 回覆。免新增回應欄位與 schema 變更。若未來需專屬 CTA 連結 UI，再加回應欄位（不在本 spec）。

### 主題 3：葉答案承載——選項內嵌 vs api_config mapping
- **發現**：既有 `branch_answer` 以 `api_config.params.mapping`（value→kb_id）承載葉答案，與「選項內嵌 answer_kb」語意重疊。
- **結論**：以**選項內嵌 `answer_kb` 為新標準**（決策樹邊集中於選項、單一真相）；既有 api_config mapping 保留向後相容；兩者並存時選項層優先（與 R3 一致）。

### 主題 4：方案分級的樹表達（R8.2/8.3）
- **發現**：分流以「有無團隊」為主、戶數為輔（50 戶象徵分界、31–49 依有無團隊）。
- **結論**：起手式先問個人/團隊；「個人」分支下接「戶數」select 子樹（各戶數選項 → 方案說明知識，不含價格）。身分先決即化解 31–49 模糊；不需數值條件運算。

### 主題 5：R9/R10 屬資料非機制
- **發現**：不報價＝內容紀律 + 價格選項導向 `/pricing`（URL 葉出口）；競品＝「被問才回」走既有知識檢索與答案優化路徑。
- **結論**：兩者**不新增機制**，落在 b2b scope 知識資料與內容審核；設計明示以免機制範圍膨脹。

## 技術選型

### 選型 1：路由解析放置點
| 方案 | 優點 | 缺點 |
|------|------|------|
| A 在 `_maybe_chain_next_form` 內解析（抽 `_resolve_selected_route` helper） | 單一收斂點、最小改動、相容 | 函式職責略增 |
| B 在 `_complete_form` 先解再傳 | 取 `collected_data` 最直接 | 路由邏輯外溢 |
| C 葉答案沿用 api_config、選項只加子樹/URL | 不與 mapping 衝突 | 設定分處兩地 |
**最終選擇**：**A + C 組合**——路由解析集中於 `_resolve_selected_route`，知識葉答案可內嵌 `answer_kb` 亦相容既有 api_config。

## 現有程式碼分析

**檔案與整合點**：
- `services/form_manager.py`：`_maybe_chain_next_form`(~491)、`_present_first_field`(~455)、`_complete_form` 串接段(~2331/2334)、`collect_field_data` select 解析(~1187)、`_update_session_state_sync`(WHERE 最新 id)。
- `services/api_call_handler.py`：`_handle_branch_answer`(496)。
- `routers/chat.py`：`QuickReply`(2952)、`VendorChatResponse`(2959)、`_convert_form_result_to_response`(275 透傳旗標)。
- `form_schemas.fields`(JSONB) option 僅 `label`/`value`（無 migration 即可加欄位）。

## 風險登記

| 風險 | 影響 | 機率 | 緩解 | 狀態 |
|------|------|------|------|------|
| 改 `_maybe_chain_next_form` 簽章破壞既有 form-chaining 呼叫 | 高 | 低 | 新參數預設 None、無選項路由即 fallback 表單層 | 已緩解(設計) |
| 選項路由與表單層 next_form_id 衝突 | 中 | 低 | R3 明確 precedence（選項優先、表單層 fallback） | 已緩解(設計) |
| R9 不報價內容外洩價格 | 高(合規) | 中 | 內容紀律 + 價格選項導 /pricing；內容審核 | 開放(資料) |
| 競品中立性 | 中(合規) | 中 | KB-E 事實 + 答案優化提示；非機制 | 開放(資料) |
| 終端 select 判定在多欄位表單 | 中 | 低 | 以 `current_field_index` 終端欄位為準，非 select 即 fallback | 已緩解(設計) |

## 時間軸
| 日期 | 活動 | 結果 |
|------|------|------|
| 2026-06-20 | 輕量整合發現 | 確認阻點(collected_data)、URL 承載(知識連結)、A+C 選型 → 產出 design.md |

---
*持續更新，記錄設計階段重要調查與決策。*
