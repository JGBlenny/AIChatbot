# Plan：line-bot 三線走查回修（H1–H4）— 2026-09-09（第 5 稿：security-reviewer r1 十條＋plan-verifier r1 四條＋r2 三條＋r3 收尾審查一條全數 FIX；r3 已對碼確認其餘六條落實。審查回合已達上限，是否再審由業主裁）

> 來源：line-bot `docs/chatai-walkthrough-findings-20260909.md`（他們 main `0c0f235`）＋ 業主 00:44 截圖（75628 查無→轉人；9/04 已過期卻答「尚未逾期」）。
> 走查方法：Playwright 開真 LIFF、後端接線上 `/mcp`，三線各 ≤14 步、37 屏；介面側三件他們已修上線。
> 本 Plan 只收 **H1–H4（P0＋三個「擋住工作」）**；H5–H7 列第二批（§9），⛔ 不在本次核可範圍。
> 紀律（業主 2026-09-09「需通用修改而不是特規」）：每一項改動都落在**契約／schema／狀態機／出口閘門／正本定義**層，⛔ 不寫「某個 action／某句話」的 if；⛔ 提示詞只寫定義不寫例子；程式一筆、文件一筆 commit；⛔ 不 push（部署由業主指示）。

## 0. 程序封套 P-WT

| 欄 | 內容 |
|---|---|
| 結果 | 走查三線劇本（scratchpad `smoke/scenarios_walkthrough.json`，由 37 屏轉成）重跑 3 輪：H1 過去日期不出卡（3/3）、H3 建單後下一句問單號答得出（3/3）、H4 送出後改描述不再叫按不存在的鈕、第二件描述開新卡（3/3）、H2 判斷／指令句在零查詢時不轉人而追問對象（3/3）；line-bot 21 案例線③ 12/12 出卡不退步；敏感題仍轉人。 |
| 非目標 | H5 確認迴圈、H6 兩出口、H7 小瑕疵（§9）；W8 (4) 催繳草稿；jgb2 側 B′7／真 `agent/v1` 的伺服器端日期驗證（§7 債）；LIFF 相片五案；替身寫入跨會話留存（替身特性）。 |
| 切片 | S1 確認卡日期有效性（security-executor）；S2 完成動作進會話記憶（executor）；S3 正本 delta5＋送出後狀態（executor；正本句先過業主）；S4 零查詢轉人的出口降級＋Verifier 敏感配對（executor）。S1、S4 各自獨立；S3 依賴 S2。 |
| 驗收 | §6：單元＋確認段測試 → smoke-rag（mock，每輪重建 fixture、凍結 `_today`）三線 3 輪 → fresh verifier → 業主決定部署 → line-bot 以 Playwright 重跑同三線。 |
| 回滾 | 各切片單一 commit，`git revert`；正本版本號回退＋`export_json`。 |
| 預算 | 4 個執行代理＋plan-verifier＋verifier；smoke 三輪 ≤ 90 回合（mock，gpt-5-mini）。 |
| 停止條件 | 任一切片讓線③出卡 < 12/12、L15 測試或敏感題轉人退步 ⇒ 該切片暫停、不併；S3 正本句業主未核 ⇒ S3 不動碼。 |

## 1. 事實（對碼，可重跑）

- **H1** `bill_due_extend` 只驗 `date_expire_before + days == date_expire_after`（`grep -n "date_expire_before + days" rag-orchestrator/services/agent/confirm_card.py`）；`confirm.request` 前置閘只有 `repair_create` 的分類（`grep -n "_is_valid_repair_category" rag-orchestrator/services/agent/tools/confirm.py`）。沒有任何「日期不得早於今天」的檢查；容器 `TZ: Asia/Taipei`（`grep -n "TZ:" docker-compose.prod.yml docker-compose.dev.yml`）；逾期天數程式算（`grep -n "已逾期" rag-orchestrator/services/jgb/bills.py`）以 `bills._today()` 為唯一時鐘。替身 `_patch_bill` 也不驗過去日（`grep -n "def _patch_bill" rag-orchestrator/services/jgb/transport.py`）；真 `agent/v1` 簽章 client 不在本切片。
- **H3** 兌現回合 `_finish_confirm_turn(... receipt_id, outcome)` 只把 receipt 放進 trace／outcome.ref，**沒有寫進 `agent_state`**（`grep -n "receipt_id=receipt_id" rag-orchestrator/services/agent/runtime.py`）；重送同一 `pending_id` 仍回 `confirmed`＋`ref`（`grep -n "def _answer_for_receipt" rag-orchestrator/services/agent/runtime.py`，R4.3）。對照：L15 的 `select_scope` 有進 `agent_state`（`grep -n "SELECT_SCOPE_KEY\] =" rag-orchestrator/services/agent/runtime.py`）。
- **H4** 正本「按『我要修改』後只重新確認被改的項目…」沒有「卡片尚在」的條件；無「送出後不能改／再描述一件＝新單」的句子（`grep -c "不能改\|新單" rag-orchestrator/canon/property_manager.md` → 0）。
- **H2** 模型自報 `kind=handoff, handoff_reason=no_grounding`；政策文只定義「資料段與工具都查無」才轉人（`grep -n "資料段與工具都查無" rag-orchestrator/services/agent/agent_rules.py`），沒有「判斷句／指令句先確定對象」的定義。Verifier 對 `kind=handoff` 只驗 `handoff_reason` 在值域，**不驗敏感 `fact_class` 必須配 `sensitive_no_grounding`**（`grep -n "handoff_reason_invalid" rag-orchestrator/services/agent/verifier.py`；security r1 F1）。範圍退出的既有降級改五個欄位（`grep -n "def _apply_scope_exit" -A 20 rag-orchestrator/services/agent/runtime.py`：`answer`／`kind`／`handoff`／`trace.final_kind`／`trace.handoff_reason`＋`outcome`；F2）。
- **截圖 75628**：`jgb2.query.bills` 查無回哨兵（`grep -n "found\": False" rag-orchestrator/services/agent/tools/jgb2.py`），出口交模型 ⇒ 模型選轉人。有做過查詢（含查無）的轉人屬 H6 第二批，本 Plan 只治「零查詢就轉人」；查無的追問靠 S4 政策句。

## 2. S1 — 確認卡的日期有效性（通用契約；security-executor）

**契約（⛔ 不是 `bill_due_extend` 的特例）**
- `confirm_card.py` **新增模組層欄位屬性表**（plan-verifier r2 #1：現碼沒有 per-action 欄位表，欄位寫死在各 `_render_*` 內）：`CONFIRM_FIELD_ATTRS: dict[str, dict[str, frozenset[str]]]`，形狀 `action → {field → {屬性…}}`，第一個屬性 **`"not_before_today"`**＝「語義上必須是今天或未來」的日期欄位。現有唯一命中：`{"bill_due_extend": {"date_expire_after": {"not_before_today"}}}`。**兩道閘只讀這張表、以屬性為條件迭代**（`for action, fields in CONFIRM_FIELD_ATTRS.items()` 形狀），⛔ 任何地方不得出現以 action 名為條件的分支。未來任何帶未來日期語義的動作只加表項、不加程式。
- 表的自洽測試（列入驗收）：(a) 表的鍵 ⊆ `CONFIRM_ACTIONS`；(b) 每個被標記的欄位都是該 action 的 render 實際解析的日期欄位——以「該欄位缺值時 `render(action, payload)` 必拋 `ConfirmCardError`、給合法日期時 render 成功」證明；(c) 屬性值 ⊆ 已知屬性集合 `{"not_before_today"}`。
- 單一判定：`confirm_card.date_not_before_today(value: str, today: date) -> bool`（純函式；`value` 走既有 `_parse_date`）。`today` 由呼叫端傳入，⛔ 不在 confirm_card 內取時鐘（保持純）。
- **兩道閘同一函式、同一時鐘**（`from services.jgb import bills` 後在呼叫點 `bills._today()`；⛔ 不 `from … import _today`，否則測試 monkeypatch 失效；F5）：
  1. `confirm.request`（`confirm.py`，`render()` **之後**——render 已保證欄位齊全且日期可解析；F6）：規格中任一 `not_before_today` 欄位早於今天 ⇒ `ToolResult(ok=False, error="INVALID_INPUT", text_for_model=DATE_BEFORE_TODAY_TEXT)`——**沿用封閉 `ToolError` 值域**（`grep -n "ToolError = Literal" rag-orchestrator/services/agent/tools/registry.py`），⛔ 不新增錯誤碼（plan-verifier r1 #2）；與 render 失敗的差別只在 `text_for_model`。⛔ 不落 pending、不出卡。單元測試實際建構該 `ToolResult`（不拋 ValidationError）。
  2. 兌現閘放在 **runtime 兌現路徑**（`_run_confirm_segment` 兌現分支，在呼叫 `jgb2.action.*` 之前；plan-verifier r1 #4——`ToolResult` 沒有 violations 通道）：對 pending payload 依規格屬性套同一純函式，早於今天 ⇒ 不呼叫動作工具、關 pending、以 `_finish_confirm_turn(... violations=["date_before_today_at_redeem"], outcome=failed)` 收尾，使用者面文字＝既有 `ACTION_FAILED_TEXT`（`grep -n "^ACTION_FAILED_TEXT" rag-orchestrator/services/agent/runtime.py`）；F9 由此可稽核。`action.py` 本身不再加第二套判定（一個判定、一個時鐘、兩個呼叫點）。
- `DATE_BEFORE_TODAY_TEXT`（工具訊息，定義不舉例、無插值）：「這個日期早於今天，不能以它出確認卡；請改問使用者要用今天以後的哪一天，再重新提出確認。」
- 工具描述（`action.py` 動作規格的日期欄位說明）補一句定義：「這個日期不得早於今天；算出來早於今天時不要送確認，先問要改到哪一天。」（⛔ 不改 `before + days == after` 的驗算契約——使用者確認的仍是絕對日期。）
- outcome：閘門回合由模型接續發問 ⇒ 既有 `clarifying/expects=text`；⛔ 不新增 outcome 狀態。
- 非目標：⛔ 不改「延 N 天以哪天為基準」（line-bot 選項一）——基準改今天會讓「原到期日在未來」的延期少算，且卡上印的原到期日對不上。

**驗收**
- 單元：`date_not_before_today` 三態（昨天／今天／明天）；`CONFIRM_FIELD_ATTRS` 自洽測試 (a)(b)(c)；表裡沒有標記的動作行為完全不變（`repair_create` 既有測試全綠）；`confirm.request` 過去日 ⇒ `ok is False and error == "INVALID_INPUT" and text_for_model == DATE_BEFORE_TODAY_TEXT`（與 render 失敗分支 `text_for_model` 為空可區分）、無 pending 列；今天／未來 ⇒ 出卡如舊；兌現路徑過去日 ⇒ 替身 `_patch_bill` 未被呼叫、答 `ACTION_FAILED_TEXT`、trace 有 `date_before_today_at_redeem`、`outcome.state=failed`。
- 情境（smoke-rag，mock，每輪重建 fixture＋凍結 `_today`；F10）：帳單到期日＝今天−5，「延三天」⇒ 無卡、回問延到哪一天；「延到（今天＋2）」⇒ 出卡且日期正確；**正對照組**：直接送 `date_expire_after`＝今天−1 的 `confirm.request` 必須被擋。3 輪 3/3。
- 環境：smoke 容器內實查 `TZ` 與 `bills._today()` 值（F5）。

## 3. S2 — 完成的動作進會話記憶（通用；executor）

**契約**
- `agent_state["completed_actions"]`：list，元素 `{action, ref_type, ref_id, estate_id, at_iso}`——**全部封閉值**（action enum、id、ISO 日期），⛔ 不放模型自填字串（`estate_name` 等；F7）。由 `_finish_confirm_turn` 在 `outcome.state == "confirmed"` 且 `outcome.ref` 存在時寫入；**依 `(ref_type, ref_id)` 去重**（重送同一 pending 不重複追加；F7）；上限 5（FIFO）；隨 `agent_state` 建立／重新開始／30 分鐘過期一起清，⛔ 不另立 TTL。
- `estate_id` 來源：兌現時的 `select_scope.estate_id`（有範圍時）或 payload 內的封閉 id 欄位；取不到 ⇒ `None`。
- 進模型（plan-verifier r1 #1：L15 的 `select_scope` 只寫 `agent_state`、不進 messages，⛔ 不能照抄）：走**影像事實那條既有的可引用資料段通道**——`call_id` **由本回合 nonce 導出**（`f"done-{nonce[:8]}"`，與影像路徑 `f"img-{nonce[:8]}"` 同法；plan-verifier r2 #3：固定常數會被模型送同名 tool_call id 覆蓋，只有 `OUTLINE_TOOL_CALL_ID` 有撞名防護——`grep -n "tool_call_id_collides_with_outline" rag-orchestrator/services/agent/runtime.py`）＋ `ToolResult(provenance=[Provenance(source=COMPLETED_ACTIONS_LABEL, text=completed_actions_line(items, scope_estate_id), citable=True)])` 放進 `tool_results_by_id[call_id]`，並以 `wrap_provenance_data(COMPLETED_ACTIONS_LABEL, call_id, …, nonce)` 同 nonce append 進 messages（對照 `grep -n "IMAGE_DATA_LABEL\|wrap_provenance_data" rag-orchestrator/services/agent/runtime.py`）。**撞名防護升格為通用保留鍵集合**（plan-verifier r3 #1 選 (a)：現碼只對 `OUTLINE_TOOL_CALL_ID` 一個保留字拒收，影像段沒有防護）：`runtime.py` 新增 `RESERVED_TOOL_CALL_IDS`（本回合程式產的資料段 id 集合：大綱常數＋影像 `img-…`＋記憶 `done-…`，後兩者在回合開始由 nonce 導出後加入），工具迴圈那一條判斷改為「`tc.id in reserved` ⇒ 拒收＋`violations.append("tool_call_id_collides_with_reserved")`」（原 `tool_call_id_collides_with_outline` 併入同一條，⛔ 不留兩條分支）。單元測試三例（正對照組）：模型送與大綱／影像／記憶段同名的 tool_call ⇒ `tool_results_by_id` 該鍵仍是程式產的 `Provenance`、trace 有撞名 violation。這是 S2 的前置子項，歸 S2 執行者所有。只有 `completed_actions` 非空才注入。`completed_actions_line` 決定性產出；**有範圍時只放同戶的項目**（F8）；輸出前剝除換行與 `_UNIT_MARKER_RE` 同形字串（F7c）。⛔ 不進 dialog 歷史。
- 引用：模型答單號時 `refs` 指向這一段（既有 refs／provenance 機制；這一段是程式產的封閉值，不是模型自產）；Verifier 對它的句子不得回 `UNCITED_ASSERTION`／`ref_source_not_found`。
- 非目標：⛔ 不把它當 L15 範圍（不影響 `_enforce_tool_scope`）。

**驗收**
- 單元：追加／去重／上限／清空／範圍過濾／session_expired 後為空；`completed_actions_line` 決定性且不含換行。
- 情境（smoke-rag）：建單 → 「剛剛那張單號多少」⇒ 答含單號、`outcome.state=answered`；重送同一確認 ⇒ 記憶仍 1 筆；「這戶還有沒有別的單」⇒ 仍走查詢工具。3/3。

## 4. S3 — 送出後的狀態（正本定義；executor；正本句先過業主）

**正本 delta5（`review-sheet-property_manager-delta5-20260909.md`，⛔ 核可前不動碼）**：兩句（「我要修改」加「確認卡尚在時」條件；新增「確認送出後不在對話裡修改、指到 JGB 修繕單頁；送出後再描述同一戶另一問題＝新單，物件不重問、仍只有按確認送出才建單」）。

**程式**：依賴 S2（記憶行讓模型知道「已送出」）；補回歸測試「兌現後同一會話再送舊 `confirm_*:` pid ⇒ `CONFIRMATION_REQUIRED_TEXT`」（既有行為）。⛔ 不加「改描述」偵測規則（開放語義，交正本定義＋記憶事實）。

**驗收**：建單完成 → 「我要改一下描述」⇒ 無卡、答含「已送出」與指路、不出現「我要修改」；「廚房抽風機不會轉 同一戶」⇒ 新確認卡，描述＝抽風機、物件同前；3/3。canon 測試全過；版本 2026-09-09.1；`export_json` 同步。

## 5. S4 — 零查詢轉人的出口降級（通用出口閘）＋ Verifier 敏感配對（executor）

**契約**
- **Verifier 通用契約（F1）**：`verifier.py` 對 `kind=handoff`：`fact_class in SENSITIVE` ⇒ `handoff_reason` 必須是 `sensitive_no_grounding`，否則 `SCHEMA/handoff_reason_mismatch`（重試一次，既有機制）。**同時**：`output_schema.py` `VerifierVerdict.schema_cause` 的 `Literal` 新增 `handoff_reason_mismatch`，`runtime.py` `_SCHEMA_CAUSE_HINTS` 新增對應修法句（定義不舉例：「`fact_class` 屬敏感五類時 `handoff_reason` 必須是 `sensitive_no_grounding`，請改填。」），`tests/unit/agent/test_runtime_req.py` 的鍵集合等值測試維持全綠（plan-verifier r1 #3）。這是把「敏感類配敏感原因」從提示詞承諾升格為 schema 驗證，對所有回合一體適用。
- 政策文（`agent_rules.py` 【判準】，定義不舉例，兩句；F3 加豁免片語）：「判斷句與指令句先確定對象：對象不明就問是哪一戶或哪一筆，⛔ 不轉人；對象明確就依資料段給建議，⛔ 不因為是判斷題而轉人；敏感五類不在此列、仍轉人。」「工具回查無時，先確認使用者給的編號或名稱是否有誤，⛔ 不直接轉人。」（非 prospect 版無長度上限、⛔ 計數只綁 prospect 版；但 `test_no_example_markers_in_policy_or_persona_texts` 綁兩版——新句 ⛔ 不得含「例如」「（如」等舉例標記；plan-verifier r1 已對碼。）
- **程式出口閘**（`runtime.py`，與 `_apply_scope_exit` 同層、在 handoff cache 與 `_append_dialog` **之前**）：條件全為封閉欄位——`kind == "handoff"` ∧ `handoff_reason == "no_grounding"` ∧ `fact_class ∉ SENSITIVE` ∧ `trace.tool_calls` 為空 ∧ `select_scope is None` ⇒ **五欄一起改**（F2）：`answer = ASK_TARGET_TEXT`、`kind = "answer"`、`handoff = None`、`trace.final_kind = "answer"`、`trace.handoff_reason = None`；`outcome = clarifying/expects=text`；`violations += ["handoff_without_lookup"]`。斷言：降級後 `result.handoff is None and trace.final_kind == "answer"`（不進 handoff cache）。
- `ASK_TARGET_TEXT`＝「想處理哪一件事？講名稱或編號就可以。」（無插值；L15-13）。
- 有做過查詢（含查無）的轉人 **不動**（H6 第二批）；`sensitive_no_grounding`／`llm_mentioned_handoff` 不動。

**驗收**
- 單元：五條件真值表（缺任一 ⇒ 不降級）；`fact_class=pricing`＋`no_grounding`＋零查詢 ⇒ 不降級且 Verifier 回 `handoff_reason_mismatch`；降級後五欄斷言。
- 情境（smoke-rag）：「要不要催他」「怎麼辦」「幫我處理」無前文 ⇒ 追問對象、`outcome.state=clarifying`；接著給 756248 ⇒ 依資料段答；「75628 這張是不是逾期了」⇒ 追問確認編號（非轉人）；價格題 ⇒ 仍 handoff。3/3。
- 回歸：線③ 21 案例 12/12 出卡；L15 全綠；敏感題轉人不退步。

## 6. 驗證順序（每切片）

1. 容器內單元＋確認段測試（`docker compose -f docker-compose.dev.yml run --rm -e USE_MOCK_JGB_API=true rag-orchestrator sh -c "pip install -q -r requirements-test.txt; python3 -m pytest …"`；⛔ host 3.9；⚠️ 路徑打錯（不存在的目錄）時 pytest 整批 0 收集但 `run-tests.sh` 仍 exit 0——看到 `passed=0` 一律視為沒跑，⛔ 不當綠）。
2. smoke-rag（`docker-compose.prod.yml run --name smoke-rag … USE_MOCK_JGB_API=true`；dev key 重發、600 檔、收工停用）跑 `scenarios_walkthrough.json` 3 輪，**每輪重建 fixture**（替身寫入會留住；F10）、凍結 `_today`、容器內實查 TZ。
3. fresh `verifier`：拿 §2–§5 驗收原句＋diff；REFUTED ⇒ 修 → 再一輪。
4. 業主決定是否部署；部署後 line-bot 以 Playwright 重跑同三線。

## 7. 安全／信任面（security-reviewer r1 處置）

| # | 發現 | 處置 |
|---|---|---|
| F1 P1 | S4 降級條件用模型自填欄位，敏感類未被保護 | FIX：條件加 `fact_class ∉ SENSITIVE`＋Verifier 通用配對（§5） |
| F2 P1 | 降級漏改 `handoff`／`final_kind` ⇒ line-bot 收到轉人訊號、進 handoff cache | FIX：五欄一起改＋斷言（§5） |
| F3 P2 | 政策句與鐵則 2 相衝 | FIX：加「敏感五類不在此列」（§5） |
| F4 P2 | 真 `agent/v1` 無伺服器端過去日驗證 | FIX（記債）：jgb2 側待辦；本 Plan 閘門是 demo 期唯一控制點 |
| F5 P2 | monkeypatch 失效／TZ 差一日 | FIX：呼叫點 `bills._today()`＋容器實查 TZ（§2） |
| F6 P2 | 閘一在 render 前日期未解析 | FIX：閘一移到 render 之後（§2） |
| F7 P2 | 記憶行是新引用面且會被重送灌爆 | FIX：封閉值、去重、剝標記（§3） |
| F8 P2 | 記憶跨越 select 範圍 | FIX：釘 `estate_id`、有範圍只放同戶（§3） |
| F9 P3 | 閘二拒絕稽核看不出 | FIX：trace violations（§2） |
| F10 P3 | 替身寫入留存 ⇒ 情境不可重現 | DEFER→驗收註記：每輪重建 fixture（§6） |

DSP-011／L15：無新增授權層；`_enforce_tool_scope`／`_scope_gate_confirm_request` 不動；兩固定句無插值。執行代理 brief：不讀 `.env`、不印金鑰、不 `git stash`、不在常駐容器跑真 API。

## 8. 風險與取捨

- S4 固定句在「對象其實在前文」時會多問一次（模型沒查卻有前文）：接受——多問一次比轉人便宜；H6 第二批分兩出口。
- S1 不改基準算法：原到期日已過時「延三天」會被追問一次；理由見 §2 非目標。
- Verifier 新配對規則可能讓「模型把普通題填成敏感類」的回合多重試一次：可觀測（`handoff_reason_mismatch` 計數），不影響最終出口。

## 9. 第二批（不在本次核可）

H5 過度確認（肯定語＝執行；空會話直說）；H6 no_data／no_judgement 兩出口＋兩題不同句（含「有查詢但查無」的追問出口）；H7 第一句描述保留、欄位名外洩、分類辨識、「嗎？。」、每輪系統聲明；`run-tests.sh` 在 pytest 路徑錯誤時 exit 0 的假綠（宜改為非 0）。
