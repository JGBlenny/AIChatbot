# 研究紀錄：conversational-diagnosis

> 建立時間：2026-06-30　功能類型：Extension（既有系統整合，light discovery）

## Summary

以既有對話引擎 + API 呼叫 + 檢索路由為底座，補「API grounding」與「分類路由進對話」兩項貫通能力。探索聚焦既有整合點與重用介面；外部相依（jgb2 合約 API）已實測可打通，無需額外研究。兩個落差阻點於探索中定案（見下）。

## Research Log

### 主題 1：對話引擎收斂與 grounding 機制
- 來源：`services/conversational_engine.py`（`prepare`:99、`_converge_grounding`:202、`_has_basic_info`:29、`_start`:59、`__init__`）
- 發現：`prepare` 以 `optimizer.conversational_step` 回 `extracted_fields`/`action(ask|converge)`/`next_question`；收斂時 `_converge_grounding` 依 `select` in {ids,category,vector} 撈知識；`_has_basic_info` 寫死 identity/scale/pain。`_start` 建 `form_id='conversational'` session 並存 `config_key`。
- 含意：新增 `select:"api"` 為第四種 grounding；`_has_basic_info` 改讀設定槽位；二者皆在 `prepare`（config 在 scope）內整合。`__init__` 需注入 `api_handler`。

### 主題 2：API 呼叫與參數解析（阻點 1 定案）
- 來源：`services/api_call_handler.py`（`execute_api_call`:~140、`_resolve_param_value`:267、`get_api_call_handler`:784）、`services/jgb_system_api.py`（`get_contracts`:151）
- 發現：`execute_api_call(api_config, session_data, form_data, user_input, knowledge_answer) -> {success, data, formatted_response}`；`_resolve_param_value` 支援 `{session.x}`/`{form.x|if_numeric|if_text}`，**無 `{slot.x}`**。`get_contracts` real 模式打 `/api/external/v1/contracts/status-overview`，已實測回真資料（含狀態 mapping + 租金/日期/地址等豐富欄位）。
- **定案**：引擎重用 `execute_api_call`，把對話 `collected_fields` 當 `form_data`、`role_id/vendor_id/session_id` 當 `session_data`；config 參數用 `{form.<slot>}`/`{session.role_id}`。→ **api_call_handler 完全不改**（R7.3 滿足）。

### 主題 3：設定載入與分類路由（阻點 2 接線）
- 來源：`services/conversational_config.py`（cache `by_key`/`by_role`、`topic_scope` 解析:74 但無人讀取）、`routers/chat.py`（`handle_conversational_entry`:575 寫死 prospect、`_build_knowledge_response` 表單觸發:~2765、`handle_conversational_session`:405 續對話）
- 發現：`topic_scope{mode:category}` 已存進設定物件但 cache 無 `by_category`、無查詢函式。售前由 `target_user` 前門進；表單由檢索觸發。續對話檢查 `form_id=='conversational'` 自動接手。
- 含意：新增 `by_category` 索引 + `config_for_category()`；分類路由整合於 `_build_knowledge_response` 表單觸發點（檢索後、分類已知）；續對話零改（`_start` 已存 config_key）。

### 主題 4：多筆/0 筆對話回饋（阻點 2 定案）
- 分析：引擎為 ask/converge 範式。API 回傳筆數分三路：1→converge（格式化為 grounding 合成）；0→ask（查無，重問識別）；N→ask（列候選反問）+ 將候選存入對話 state，下一輪以使用者選擇對應回單一 contract_id 再 converge。
- **定案**：採「state 存候選 + 下一輪確定性對應」（選甲），避免重複打 API 與非結構化反問；全程仍走既有 ask/converge，不新增狀態機。

### 主題 5：後台設定頁能力
- 來源：`knowledge-admin/frontend/src/views/ConversationalConfigView.vue`（214 行，grounding 下拉 vector/category/ids）、`routers/conversational_configs.py`（payload 收通用 `config: Dict`）
- 含意：前端加 `api` 選項 + endpoint/params/required_slots 欄位；後端 payload 不改（已收任意 config）。

## 架構模式評估
- **取向 A（既有各點原地擴充）**：採用。加性、集中對話引擎；重用最大。
- 取向 B（合約也前門進按角色）：否決（吸走全角色流量，違反 topic-gated / R7.2）。
- 取向 C（多欄位表單模擬）：否決（做不到自適應追問與意圖判斷 / R2/R4）。

## 設計決策（摘要，詳見 design.md）
1. API grounding 重用 `execute_api_call`，slot 走 `form_data` 通道，config 用 `{form.<slot>}`——api_call_handler 零改。
2. 收斂門檻改讀 `config.grounding_scope.required_slots`，售前無此鍵維持舊行為。
3. 分類路由置於 `_build_knowledge_response` 表單觸發點；續對話沿用 `handle_conversational_session`。
4. 多筆→存候選 state + 下一輪確定性對應；0 筆→重問；1 筆→收斂。
5. `select/endpoint/params/required_slots/topic_scope` 全讀設定，程式不含合約硬編（R6）。

## 風險
- 從檢索點啟動對話的回應契約（JSON/SSE）需與既有表單觸發回應一致。
- 多筆候選對應的確定性（使用者以名稱/序號選擇的解析）。
- 通用性回歸：確保無合約硬編，未來面向零改程式。

## 參考
- requirements.md（R1–R8）、gap-analysis.md
- 既有：COMPLETE_CONVERSATION_ARCHITECTURE.md、dialogue.md（steering）
