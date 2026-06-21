# 實作任務：option-routing（選項層決策樹路由）

> 建立時間：2026-06-20
> 需求：requirements.md（R1–R10）｜設計：design.md｜落差：gap-analysis.md
> 標記說明：`(P)` = 可與同層其他 `(P)` 任務平行；`- [ ]*` = 可延後的測試覆蓋子任務

## 1. 選項路由解析 Helper

- [x] 1.1 實作 `FormManager._resolve_selected_route(form_schema, collected_data)`：取終端 select 欄位（`current_field_index` 為主，非 select 則取 fields 中最後一個 select，仍無回 None）；以 `collected_data[field_name]` 取被選 value；於該欄位 `options` 找相符 option；回 `{next_form_id?, answer_kb?}`，無路由/無相符回 None。純函式。
  - 需求：1.1, 1.2, 2.1, 3.1, 3.2
- [x]* 1.2 單元測試：選項含 `next_form_id`→回子樹；含 `answer_kb`→回葉答案；兩者皆有→回兩者；選項無路由→None；value 不匹配→None；終端非 select→改取最後 select / None
  - 需求：1.1, 1.2, 2.1

## 2. `_maybe_chain_next_form` 接入選項路由

- [x] 2.1 擴充 `_maybe_chain_next_form` 簽章加 `collected_data: Optional[Dict] = None`（預設保相容）；解析順序：選項路由（`_resolve_selected_route`）優先 → `next_form_id` 串接子樹（沿用既有載入/會話/深度/循環/呈現）→ `answer_kb` 葉答案（async `_handle_branch_answer`，納入 try/except，失敗回 None）→ 兩者皆有則合併 → route 為 None 時 fallback 表單層 `next_form_id`
  - 需求：2.1, 2.2, 2.3, 3.1, 3.2, 4.1, 6.1, 6.2, 6.3, 6.4
- [x]* 2.2 單元測試：選項子樹→建會話回契約；選項葉答案→branch_answer 內容；葉答案+子樹→合併；選項無路由→fallback 表單層；branch_answer 失敗→None；深度/循環防護沿用
  - 需求：2.2, 2.3, 3.1, 6.1, 6.2, 6.3

## 3. `_complete_form` 整合與葉答案覆寫

- [x] 3.1 `_complete_form` 串接呼叫改傳新鮮 `collected_data`；依 `_maybe_chain_next_form` 結果分派：子樹→合併 `answer`（葉答案?+`\n\n---\n\n`+後續第一欄）+ 串接旗標契約；純葉答案→`form_completed=True`、`answer` 以選項 `answer_kb` 知識**覆寫** `completion_message`（決策 7，不雙重回答）；未路由→與現況完全一致
  - 需求：2.4, 2.5, 3.2, 4.1, 7.1, 7.2
- [x] 3.2 整合測試（真實 DB）：選項分歧建立後續 COLLECTING 會話且 `get_session_state` 切換；葉答案覆寫不雙重回答（`on_complete_action=show_knowledge`）；終端非 select→fallback 表單層；未設選項路由之既有表單與 form-chaining 金流範例回傳不變
  - 需求：2.4, 3.2, 3.3, 7.1, 7.2

## 4. 葉出口三型：知識答案 / 動作表單 / 導向連結

- [x] 4.1 (P) 葉出口分派驗證：`answer_kb` 經 `branch_answer` 回知識（不經檢索）；CTA 動作表單（`trial_form`/`demo_form`）以選項 `next_form_id` 串接並 `call_api`；URL 葉出口＝`answer_kb` 指向內含連結（`/pricing`）之知識，連結於 `answer` 呈現
  - 需求：4.1, 4.2, 4.3, 4.4, 4.5

## 5. presales 範例資料：身分分流 + 戶數子樹

- [x] 5.1 建起手式分流表單（select：個人房東 / 公司團隊），選項帶 per-option 路由（個人→戶數子樹 `next_form_id`；團隊→團隊說明 `answer_kb` + `demo_form`）；掛 b2b（`business_types` 含 `system_provider`）
  - 需求：8.1, 8.2, 8.4, 8.6
- [x] 5.2 建個人→戶數子樹表單（select：10/20/30 戶），各選項 `answer_kb`→對應方案說明知識（不含價格）+ `next_form_id`→`trial_form`
  - 需求：8.3
- [x] 5.3 (P) 建方案說明知識（個人 10/20/30、團隊全模組+大房東報表）於 `knowledge_base`，b2b scope，**不含價格數字**（價格導 `/pricing`）
  - 需求：8.3, 8.4, 9.1

## 6. presales 範例資料：痛點分流 + 模組知識 + CTA 表單

- [x] 6.1 建痛點選單表單（select：收租對帳/合約/人多/抄表換鎖/交報表/報修），各選項路由到對應模組葉答案或 `demo_form`；IoT（抄表換鎖）選項導向專人說明（不報價）
  - 需求：8.5, 9.2
- [x] 6.2 (P) 建模組知識 C1–C6 + 大房東報表 + 修繕於 `knowledge_base`，b2b scope（IoT 知識僅「細節由專人說明」、不含價格）
  - 需求：8.5, 9.2
- [x] 6.3 (P) 建 CTA 表單 `trial_form`（`POST /api2/trial_form`）、`demo_form`（`POST /api2/demo_form`），`on_complete_action=call_api`，留資欄位對齊既有 demoForm
  - 需求：4.2, 8.3, 8.4

## 7. 合規與競品資料（非機制）

- [x] 7.1 不報價落地：價格/方案選項採導向連結（`/pricing`）；方案/IoT 知識內容審核確保不含價格數字；對話收束至明確出口
  - 需求：9.1, 9.2, 9.3
- [x] 7.2 (P) 建競品知識 E1–E3（事實對照/差異化優勢/中立準則）於 `knowledge_base`，b2b scope；走既有知識檢索（被問才回），非選項路由
  - 需求：10.1, 10.2, 10.3, 10.4

## 8. 端到端與向後相容驗證

- [ ] 8.1 端到端（b2b mode）：問「適不適合我」→ 起手式 → 個人→戶數→方案說明(不報價)→試用；團隊→demo；痛點→模組→demo / IoT→專人；問價格→`/pricing`；問競品→中立比較→收束 demo；任一層取消→結束
  - 需求：8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 10.1, 10.3, 5.1
- [ ] 8.2 向後相容回歸：未設選項路由之既有表單（查詢/申請型）流程不變；form-chaining 表單層 `next_form_id` 主幹串接（金流範例）行為不受影響
  - 需求：7.1, 7.2, 7.3
- [ ]* 8.3 取消與離題、深度上限/循環防護於決策樹多層情境沿用驗證
  - 需求：5.1, 5.2, 5.3, 6.1, 6.2

## 9. 葉答案 LLM 個人化（R11–R13 修訂｜接續新階段）

> 機制 1–4、資料 5–7 已完成驗證。本節為葉答案從「直吐知識原文」升級為「grounded LLM 合成」。**路由與選知識維持決定性，只升級措辭。**

- [x] 9.1 系統脈絡 md 資料建置 + 檢索排除：將 `00-system-context.md` 匯入 `knowledge_base`（`category='系統脈絡'`、無 embedding、`generation_metadata` 帶 version/last_verified/char_count）；retriever **vector + keyword 兩處** WHERE 加 `AND category IS DISTINCT FROM '系統脈絡'`。
  - 需求：13.1, 13.4；決策 11
- [x]* 9.2 測試：該筆**不被任何 prospect 檢索回**（vector + keyword）；載入端以分類能撈到。
  - 需求：13.4
- [x] 9.3 系統脈絡 md 載入器（元件 10）：啟動載入 + 記憶體快取 + `get_system_context()`；大小守門告警；載入失敗回內建最小合規 prompt。
  - 需求：13.1
- [x] 9.4 跨步情境累積（元件 8）：`_maybe_chain_next_form` 串接時 append `chain_context`（form_id/label/value）至 metadata；取消/完成清除；**不影響決定性路由**。
  - 需求：12.1, 12.2, 12.3, 12.4
- [x]* 9.5 單元測試：多步累積正確、取消/完成清除、路由不受情境累積影響。
  - 需求：12.3, 12.4
- [x] 9.6 擴充 `LLMAnswerOptimizer.synthesize_presales_answer`（元件 9）：輸入「選定知識 + 系統 md + 累積情境（+ 自由問答的 user_question）」；system prompt = md + 嚴格 grounding/合規指令；例外/逾時/超 token 回 None。
  - 需求：11.1, 11.2, 11.3, 13.5；決策 8
- [x]* 9.7 單元測試：grounding 不超出「知識 + md」、合規 prompt 注入、競品只用本次 E1、失敗回 None。
  - 需求：11.2, 11.3, 13.5
- [x] 9.8 葉答案接線（改元件 3/4）：`_resolve_leaf_answer`→`_synthesize_leaf_answer`（傳 `chain_context`）；合成失敗沿用 `_degrade_to_leaf` 降級**知識原文**；CTA / 表單第一欄段維持決定性、不經 LLM。
  - 需求：11.1, 11.4, 11.5
- [x] 9.9 自由問答接線（串流 stream=True 注入為已知剩項）：`chat.py` synthesize 於 `mode=b2b + target_user=prospect` 時注入系統 md（競品/功能推薦走此路徑）。
  - 需求：13.2, 13.3
- [x] 9.10 端到端真實對話前後比較驗證（**重建容器後**）：個人/團隊/痛點葉答案「前(原文) vs 後(LLM 個人化)」對比；情境融入（個人房東+戶數）；競品/功能推薦自由問答走 md 護欄；不報價 / 競品中立 / grounding 合規；**非 prospect 不受影響回歸**；合成失敗降級原文。
  - 需求：11, 12, 13, 9, 10

## 10. 對話式回答模式（R14–R19 修訂｜generic + 資料驅動 + 可擴充）

> reframe（R19）：R14–R18「AI 引導顧問」其本質為通用「對話式回答模式」；售前為第一個 conversational 設定。命名 advisor→conversational。
> cf8b8c3 已落地：brain（規則外傳）+ orchestrator 骨架（狀態/收斂）；本節接線 + 通用化（**通用引擎 + presales 設定**）+ DB 規則載入 + 命名統一 + 棄用舊表單 + 容器 e2e。
> 棄用問問題表單（presales_intro/units/pain），問問題交對話引擎自適應提問+收斂；保留 entry 快速選 + CTA 結構化 + presales 知識（供 grounding）。

- [x] 10.1 對話式回答設定層（元件 15）：定義 `ConversationalConfig`（`answer_mode` direct|conversational、入口 entry/topic、persona/rules 參照、`grounding_scope`{target_user/category/keywords}、seed）；presales 首例設定（conversational、target_user=prospect、grounding=prospect 售前知識）；未設定面向一律 direct。
  - 需求：19.1, 19.2, 19.3, 19.6
- [x] 10.2 persona/規則載入器（R19.4）：依 target_user 從 DB `category='對話規則'` 載入 `rules_text` + code 內建 fallback（`CONVERSATIONAL_RULES_BY_ROLE`，prospect 售前顧問）；查無則 fallback；新增角色＝加資料、不動程式。
  - 需求：19.4
- [x] 10.3 對話狀態（元件 11）[cf8b8c3 部分完成]：`form_sessions` 偽會話（form_id `conversational`）存 `collected_fields`{身分/規模/有無團隊/痛點/有興趣功能}/已知缺口/累積情境/提問計數；取消/結束/收斂清除；不重問已收集欄位。
  - 需求：16.1, 16.2, 16.3
- [x] 10.4 對話 brain（元件 12）[cf8b8c3 部分完成]：`conversational_step(rules_text, system_md, state, message)` 單次 structured-output LLM call → JSON `{extracted_fields, action:ask|converge, next_question?, converge_topic?}`；接規則載入器傳入 `rules_text`（補上現缺 arity）；JSON 驗證 + 收斂門檻（身分+「規模或痛點」）+ 提問上限 ≤4 + 使用者要求收斂 + 一次一題。
  - 需求：14.1, 14.2, 14.3, 14.4, 14.5, 15.1, 15.2
- [x]* 10.5 單元測試：JSON 解析/驗證、收斂門檻達成→converge、未達→ask、使用者要求→converge、提問上限、越界輸出被拒。
  - 需求：14.4, 15.1, 15.2, 17.4
- [x] 10.6 grounding 範圍 + 收斂合成（元件 13/15）：收斂依 config `grounding_scope` 限定檢索（多面向不互撈）→ 重用 `synthesize_presales_answer`（累積情境=狀態）生成推薦（方案級距不報價 + 模組 + CTA）。
  - 需求：15.3, 15.4, 19.5
- [x] 10.7 answer_mode dispatch（R19.1/19.2）：prospect 入口依設定判 conversational；未設定面向走既有 direct（不拖入迴圈）。
  - 需求：19.1, 19.2
- [x] 10.8 chat.py 接線（元件 14）：chat.py prospect 自由問答 → 進 conversational engine；`presales_entry`「適不適合/想解決問題」選項改 seed conversational topic（不再到舊表單）；續對話（進行中會話續跑）；方案費用/競品維持 D1/E1 直答；brain/合成失敗 → 降級回 `_maybe_synth_prospect_freetext` 或選單。
  - 需求：18.1, 18.2, 18.3, 17.3
- [x] 10.9 命名 advisor→conversational（R19）：`presales_advisor.py`→`conversational_engine.py`（通用引擎 + `ConversationalConfig` 參數化）、`advisor_step`→`conversational_step`、`ADVISOR_*`→`CONVERSATIONAL_*`、form_id `presales_advisor`→`conversational`。
  - 需求：19
- [x] 10.10 合規護欄 + 降級（R17）：brain/合成注入 md 鐵則；結構化輸出驗證拒越界（報價/競品斷言/越 scope 提問）；brain 或合成失敗/逾時 → 降級回自由問答合成或選單，不阻斷。
  - 需求：17.1, 17.2, 17.3, 17.4
- [x] 10.11 棄用舊問問題表單（決策 14）：`presales_intro`/`presales_individual_units`/`presales_pain_points` 設 `is_active=false`、移除 entry 觸發指向；**對應知識保留**（供 grounding）。
  - 需求：18.1
- [x] 10.12 真實口語 e2e 驗證（**重建容器後**）：口語進 conversational → 自適應提問（標準欄位+動態補問）→ 達門檻/使用者要求 → 收斂推薦（不報價/grounded）；提問上限；競品/IoT/不杜撰合規；brain 失敗降級；**非 prospect 回歸**；entry fast-path seed。
  - 需求：14, 15, 16, 17, 18, 19, 9, 10, 11

---

## 需求覆蓋對照

| 需求 | 對應任務 |
|------|---------|
| 1.1 | 1.1, 1.2 |
| 1.2 | 1.1, 1.2 |
| 1.3 | 2.1 |
| 1.4 | 2.1 |
| 2.1 | 1.1, 2.1 |
| 2.2 | 2.1, 2.2 |
| 2.3 | 2.1, 2.2 |
| 2.4 | 3.1, 3.2 |
| 2.5 | 3.1 |
| 3.1 | 1.1, 2.1, 2.2 |
| 3.2 | 1.1, 2.1, 3.1, 3.2 |
| 3.3 | 3.2 |
| 4.1 | 2.1, 3.1, 4.1 |
| 4.2 | 4.1, 6.3 |
| 4.3 | 4.1 |
| 4.4 | 4.1 |
| 4.5 | 4.1 |
| 5.1 | 8.1, 8.3 |
| 5.2 | 8.3 |
| 5.3 | 8.3 |
| 6.1 | 2.1, 2.2, 8.3 |
| 6.2 | 2.1, 2.2, 8.3 |
| 6.3 | 2.1, 2.2 |
| 6.4 | 2.1 |
| 7.1 | 3.2, 8.2 |
| 7.2 | 3.1, 3.2, 8.2 |
| 7.3 | 8.2 |
| 8.1 | 5.1, 8.1 |
| 8.2 | 5.1, 8.1 |
| 8.3 | 5.2, 5.3, 6.3, 8.1 |
| 8.4 | 5.1, 5.3, 6.3, 8.1 |
| 8.5 | 6.1, 6.2, 8.1 |
| 8.6 | 5.1 |
| 9.1 | 5.3, 7.1, 8.1 |
| 9.2 | 6.1, 6.2, 7.1, 8.1 |
| 9.3 | 7.1 |
| 10.1 | 7.2, 8.1 |
| 10.2 | 7.2 |
| 10.3 | 7.2, 8.1 |
| 10.4 | 7.2 |
| 11.1 | 9.6, 9.8, 9.10 |
| 11.2 | 9.6, 9.7 |
| 11.3 | 9.6, 9.7 |
| 11.4 | 9.8 |
| 11.5 | 9.8 |
| 12.1 | 9.4 |
| 12.2 | 9.4, 9.6 |
| 12.3 | 9.4, 9.5 |
| 12.4 | 9.4, 9.5 |
| 13.1 | 9.1, 9.3 |
| 13.2 | 9.9 |
| 13.3 | 9.9 |
| 13.4 | 9.1, 9.2 |
| 13.5 | 9.6, 9.7 |
| 14.1 | 10.4 |
| 14.2 | 10.4 |
| 14.3 | 10.4 |
| 14.4 | 10.4, 10.5 |
| 14.5 | 10.4 |
| 15.1 | 10.4, 10.5 |
| 15.2 | 10.4, 10.5 |
| 15.3 | 10.6 |
| 15.4 | 10.6 |
| 16.1 | 10.3 |
| 16.2 | 10.3 |
| 16.3 | 10.3 |
| 17.1 | 10.10 |
| 17.2 | 10.10 |
| 17.3 | 10.8, 10.10 |
| 17.4 | 10.5, 10.10 |
| 18.1 | 10.8, 10.11 |
| 18.2 | 10.8 |
| 18.3 | 10.8 |
| 19.1 | 10.1, 10.7 |
| 19.2 | 10.1, 10.7 |
| 19.3 | 10.1 |
| 19.4 | 10.2 |
| 19.5 | 10.6 |
| 19.6 | 10.1 |

## 下一步

- 審核任務清單。
- 建議**清除對話脈絡**後，逐一執行：`/kiro:spec-impl option-routing 1.1`（每個任務間清脈絡以維持專注）。
- 機制（1→2→3）為核心相依鏈；資料任務（5/6/7 多為 `(P)`）可平行建置，但端到端（8.1）需機制 + 資料皆就緒。
