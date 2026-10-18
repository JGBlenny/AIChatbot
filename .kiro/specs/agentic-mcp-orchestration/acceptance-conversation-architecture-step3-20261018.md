# 驗收清單（業主 2026-10-18 核可，已凍結）：主線第 3 步「對話整體架構」A 片＋M 片（2026-10-18 r1）

計畫：`plan-conversation-architecture-step3-20261018.md`
業主原話（出處；判定依下方規則 R1～R8）：
- 「需通用方式修改 而非 特規補丁」「像整體邏輯應該 有一個整體脈絡 而不是一個一個調整吧」
- 「像是確認卡 應該是此系統出格式 接的系統呈現吧」「要調整吧 ?」（C 片，本清單不含）
- DSP-085「但是需要通用處理 不能局部補丁」；HANDOFF-20261018 §1.1「確保 回應品質都能符合 有效的回應」

## 規則（與計畫 §1.1 同文；原話只當出處，判定一律依本節，業主核可時與清單一併凍結）

| 規則 | 內容（可檢查） | 出處 |
|---|---|---|
| R1 不分動作寫死 | 修法只放在全部寫入動作共用的流程層（草稿、確認、更正、候選、回話）；⛔ 以動作名、欄位名、題目用字、詞表做條件分支。檢查：新增一個假動作，只加動作專屬登錄——`write_forms.FORMS` 一項（含 A6 預檢宣告時，宣告在 `WriteForm` 上）、`confirm_card.CONFIRM_ACTIONS` 一項、`confirm_card._RENDERERS` 一項、所需的 `confirm_card.CONFIRM_FIELD_ATTRS`、測試自建的工具登錄表上註冊一支假的 `jgb2.action.<假動作>`（假執行器）——由測試自身註冊或 patch 加入；⛔ patch 或修改流程程式（`runtime.py`、`tools/confirm.py`、`confirm_card.render()` 的共用部分）；流程層一律在呼叫當下讀 `confirm_card.CONFIRM_ACTIONS` 這一份（A8），因此上列登錄即足以走完「收欄位→出卡（`confirm_request`→`_begin_pending_confirm`）→更正→送出（`_run_confirm_segment`→`registry.call`）／取消」。**讀法註記（業主 2026-10-18 裁定）**：動作專屬登錄（表單、卡片排版、送出規格）屬動作資料，不算流程程式 | 「需通用方式修改 而非 特規補丁」、DSP-085「不能局部補丁」 |
| R2 不只改提示詞 | 每項修法必須是程式行為改變；只改提示詞或樣板措辭不算修好 | DSP-085（⛔ 只加提示詞）、「而非 特規補丁」 |
| R3 一個脈絡 | 每項修法必須掛在三條原則之一：P1 寫入全程（建立到送出／取消）由程式持有；P2 說出口的狀態（確認、完成、請按確認）只由程式依實際狀態產生；P3 給模型的資料與給人看的呈現分開。掛不上的不做。**讀法註記（放大）**：「三條原則即整體脈絡」與「掛不上的不做」是本計畫的推導，依據第 2 步報告 §4 缺陷表的歸類與 §2.1、§2.7；原話只說應有一個整體脈絡 | 「像整體邏輯應該 有一個整體脈絡 而不是一個一個調整吧」 |
| R4 卡由本系統出結構、接入方呈現 | 本系統回傳確認卡的結構化資料（欄位、動作）；外觀由接入方決定；文字版只當備援。**讀法註記**：把問句「要調整吧 ?」讀成「要做」（本片只列 C 概要、不實作）；「文字版只當備援」是放大，依據 §2.6（MCP「SHOULD also return the serialized JSON in a TextContent block」、Adaptive Cards fallbackText） | 「像是確認卡 應該是此系統出格式 接的系統呈現吧」「要調整吧 ?」 |
| R5 有效回應以實測判 | 以第 2 步同一量尺（模擬客人多輪＋程式前判＋盲判）在本機常駐服務量；不以單元測試或人工看幾句代替 | HANDOFF §1.1「確保 回應品質都能符合 有效的回應」 |
| R6 先確認 mock | 每次會呼叫 JGB 的測試（實打、E2a、E2b、整合）執行前，HANDOFF §2.3 mock 檢查輸出 `True`；不是 `True` 就不跑 | 原始要求「任何會呼叫 JGB 的測試前，先照 §2.3 確認本機是 mock」 |
| R7 參考業界做法 | A 片每項做法標出所依的 §2 目標形態段落；查無業界對應者寫明第一原理推導與「查無業界對應」。**讀法註記**：「某些部分」讀為本計畫改動的部分 | HANDOFF §1.1「並把某些部分邏輯參考業界做法去調整」 |
| R8 不弱化寫入授權 | 任何改動後，確認 token 綁定（`pending_id`＋`session_id`＋未兌現＋未過期）、範圍閘、可見性檢查不得放寬；同 session 可兌現卡 ≤ 1；開關關閉時安全強化仍在。**出處註記**：非本次業主原話，是本計畫加的約束，來自全域安全路由（寫入授權屬 security-sensitive）與 §7 security-reviewer F1～F9、安全複核；業主核可時一併確認 | 非業主原話（見出處註記） |

原話對照（每句原話對到規則或非目標）：「需通用方式修改 而非 特規補丁」→ R1、R2；「像整體邏輯應該 有一個整體脈絡…」→ R3；「像是確認卡…」「要調整吧 ?」→ R4（本片非目標：C）；「確保 回應品質都能符合 有效的回應」→ R5（不設門檻為非目標，DSP-087）；「任何會呼叫 JGB 的測試前…」→ R6；「並把某些部分邏輯參考業界做法去調整」→ R7；「把本地替換 oss」→ 非目標：已於第 1 步 commit `2892a183` 完成，本片在同一 gpt-oss 接線上量測、不改模型接線；DSP-085「不能局部補丁」「程式掌握流程」→ R1、R2；原始要求「照 §2.4 開始寫主線第 1 步…的計畫」→ 非目標：第 1 步已完成（`2892a183`），本計畫為主線第 3 步；「交我核可後才實作」→ 核可閘：本計畫狀態行「核可前 ⛔ 動程式」，A 片程式改動只在業主核可後開始。

業主裁定（2026-10-18 核可時）：R3 讀法「對，照這樣」；R4 讀法「對，要做且留文字備援」；R8「納入」；R1 讀法見 R1 註記。以上規則自此凍結，後續驗收、verifier、挑戰者一律依本節判定。

## 清單

觀察點：本機常駐 `aichatbot-rag-orchestrator`（8100，A 片 commit 版本、業主重建容器後），mock JGB（每批實打前 mock 檢查 `True`），eval-harness 打真實 `/mcp` `agent.turn`；原文 repo 外 `~/jgb-archive/`。

| # | 業主字句 | 宣稱 | 觀察點 | 證據 | 通過條件 |
|---|---|---|---|---|---|
| 0 | R6 | 每批實打前、及任何會呼叫 JGB 的整合測試前是 mock | `run.py` 內建檢查；整合測試前手動跑 §2.3 指令 | 指令輸出 | 每批 `True` |
| M1 | R5（量尺前提） | 修繕真值含急迫程度；角色指令要求核對卡上全部欄位 | `~/jgb-archive/eval-harness` 任務檔 | 檔案 grep | W-R 每題真值有急迫程度；角色指令含「全部欄位」 |
| M2 | R5 | 判分對話稿印出 `no_button` 列 | harness 輸出 | 單元測試＋第 2 步 W-R4 k2 紀錄重產判分稿 | 該稿含 `no_button` 列 |
| M3 | R5 | 每場起始寫入狀態一致 | mock 狀態或帳單分配 | 第二場起讀回（或每場帳單互不重複的分配表） | 起始狀態等於初始狀態，或帳單互不重複 |
| M4 | R5 | W-D1、W-D2、W-D3、W-D5 改用未過期帳單；過期專題存在 | 任務檔＋mock 資料 | 到期日比對 | 改寫題帳單到期日不早於量測日；W-D4 未改 |
| M0 | R5（前置順序） | M1～M4 通過後才跑 M 後基線 | 執行紀錄時間 | 時間戳 | M 後基線晚於 M1～M4 證據 |
| 1 | R1、R3（A0） | A0 W-D1 送出失敗根因有程式證據 | 實跑重現＋程式路徑 | 重現指令與輸出 | 根因指到可 grep 符號；A6 依此定案並回報 |
| 2 | R1、R2、R3、R7 | A0～A4、A6、A7、A8 不以動作名／欄位名／詞表分支、不只改提示詞、每項掛 P1～P3 | diff＋假動作測試 | `git diff`；單元測試：只有表單定義的假動作走完收欄位→出卡→更正→送出／取消 | 假動作測試過，且測試只以自身註冊或 patch 加入 R1 所列動作專屬登錄（⛔ patch 流程函式；靜態檢查該測試檔的 patch／註冊目標只含 `write_forms.FORMS`、`confirm_card.CONFIRM_ACTIONS`、`confirm_card._RENDERERS`、`confirm_card.CONFIRM_FIELD_ATTRS`、測試自建登錄表的 `register`）；A8：`runtime.py`、`tools/confirm.py`、`write_forms.py` 的 `from … confirm_card import` 不含 `CONFIRM_ACTIONS`（正對照：`confirm_card.py` 仍定義 `CONFIRM_ACTIONS: Final`），現有 5 動作的單元／golden 測試結果不變；假動作測不到範圍閘（對未知動作回 None），範圍閘由 9m、9r 涵蓋（假動作含一個宣告了預檢的假表單）；流程層（`runtime.py`、`tools/confirm.py` 中非表單宣告註冊的部分）新增行無動作名字面比較（`git diff` 新增行 grep `== "`＋動作名、`_ACTION` 比較 0 筆；正對照：既有 `if action != BILL_DUE_EXTEND_ACTION` 在 `tools/confirm.py` 命中）；動作專屬知識只出現在表單宣告及其註冊的函式；每項修法標明原則（R3）與 §2 段落（R7） |
| 3 | R5、R3 P1（A2 改欄位） | 卡後更正任一欄位 ⇒ 新卡反映新值、舊 token 失效 | `/mcp` 實打＋單元測試 | 對話紀錄、舊 token 兌現回應 | 每個寫入動作 ≥1 案通過；舊 token 兌現 0 次成功 |
| 4 | R5、R3 P1（A3 修改按鈕） | 按「修改」⇒ 保留草稿、問改哪項 | 實打 | 紀錄 | 不出現 `CANCELLED_TEXT`；改完可出新卡 |
| 5 | R3 P1、R8（A1 草稿生命週期，§7 Q4） | 草稿出卡後保留，送出／取消／逾時才清 | 單元測試（必要時加 DB） | 測試名稱與輸出 | (a) 出卡後草稿仍在；(b) 按取消 ⇒ 草稿清空；(c) 任一 receipt 寫入（送出成功）⇒ 草稿清空；(d) 確認待決期間連續 `DRAFT_IDLE_LIMIT` 個非寫入相關文字回合 ⇒ 草稿清空；(e) 按「修改」⇒ `idle_turns`＝0；(f) 按鈕回合不累加 idle；(g) idle 清草稿後綁定卡的兌現行為與現行相同 |
| 6 | R1、R2、R3 P1（A4） | enum 由程式依表單把標籤轉代碼 | 單元測試＋E2b W-R2 | 測試輸出、紀錄 | schema 對 enum 只收標籤；標籤→代碼正確；非標籤值視為缺值並追問；W-R2 k1 型（「不急」）卡上為「非緊急」 |
| 7 | R5「有效的回應」（端到端） | M 後基線（現行容器）與 A 後同量尺、同題組重測 | E2b 模擬客人＋程式前判＋盲判 | 報告 | 列 Intercom／嚴格率＋CI 與 M 後基線並列；W-R2 k1、W-R3 k1、W-R4 k1 三型在 M 後基線未解決者逐場轉成解決或附根因（W-D2 型歸 A-2）；M5「歸 A」組（卡後改欄位、按修改）逐題解決或附根因；「歸 A-2」「只記錄」組列現況；W-D 依 A0 結論判 |
| 8 | R5、R8（回歸） | 既有行為不退步 | E2a R／D／C／T／RS／DS；K 題；unit＋golden；`make audit` | 輸出 | E2a 各 2/2 不低於第 2 步；K 20/20；測試全過；audit PASS |
| 9 | R8（計畫 §7 security-reviewer） | 確認 token 綁定不弱化 | 單元測試＋DB `agent_confirmation_tokens.redeemed`＋mock 寫入計數；`/mcp` 實打 | 測試名稱與輸出、DB 查詢、計數 | 下列 9a～9aa（9j、9o 已移至 A-2）逐條通過 |
| 9a | R8：S1 唯一有效卡 | 三條出卡路徑各出兩張卡，送第一張 ⇒ `CONFIRMATION_REQUIRED_TEXT`、`outcome.state=failed`、寫入 0 次、DB `redeemed=true` | 單元＋DB | | 通過 |
| 9b | R8：安全複核 A7-1（9b′） | 模型自呼／程式觸發：INSERT 前注入例外 ⇒ 交易回滾、舊 pid 仍可兌現、無新 pending；A2：綁定卡經 `redeem_pending()` 燒掉後，`confirm_request` 任一早退（缺欄、render 失敗、NO_MATCH、候選、日期早於今天）或例外 ⇒ 舊 pid 兌現失敗、無新 pending、寫入 0 | 單元＋DB | | 通過 |
| 9c | R8：S3 燒不到不重出卡 | A2 回合前先兌現舊 pid ⇒ 無新 pending、寫入總計 1 次 | 單元 | | 通過 |
| 9d | R8：S4 值相同不重出卡 | 卡後只重複原值 ⇒ 無新 pending、原 pid 可送出 | 單元＋實打 | | 通過 |
| 9e | R8：S5 重出卡只走 `confirm_request` | pending payload 中非使用者原話的值不進新草稿／新卡；diff 無寫入 `pending["payload"]` | 單元＋靜態 | | 通過 |
| 9f | R8：S6 更正不會變成送出 | 自由文字「好，送出」⇒ 寫入 0 次、`redeemed=false` | 單元 | | 通過 |
| 9g | R8：S7 已送出不可更正 | 送出成功後打更正 ⇒ 無新卡、寫入 1 次 | 單元 | | 通過 |
| 9h | R8：S8 修改照燒 token | `confirm_edit` ⇒ `redeemed=true`、草稿保留；再送 `confirm_submit:<同 pid>` ⇒ `outcome.state≠confirmed`；三種按鈕交叉重送逐一斷言 | 單元 | | 通過 |
| 9i | R8：S9 守門順序不變 | `readonly_view=True` 同句 ⇒ token 表與 `agent_state` 不變 | 單元 | | 通過 |
| 9k | R8：S11 預檢唯讀不洩露 | 別戶帳單編號回答與不存在逐字相同；寫入端點計數 0；有編號延期卡原到期日＝viewer 讀到值 | 單元＋實打 | | 通過 |
| 9l | R8：S12 開關回退 | 開關 off 時 9a 仍通過 | 單元 | | 通過 |
| 9m | R8：plan-verifier r1 B1 | 範圍閘擋下那一回合後：舊卡 pid 與新 token 皆無法兌現（`jgb2.action.*` 0 次） | 單元＋DB | | 通過 |
| 9n | R8：A7 位置 | 燒舊 token 與 INSERT 新 token 在 `confirm_request` 同一交易（`conn.transaction()`）；`confirm_request` 在 INSERT 前早退時不燒（9t） | 單元＋程式 | | 通過 |
| 9p | R8：安全複核 A7-3 | 同 session 兩回合交錯出卡（barrier 讓兩邊燒卡都在對方 commit 前）⇒ 最終可兌現 pid ≤ 1；逐一送出所有 pid，寫入 ≤ 1 | 單元（真 PG） | | 通過 |
| 9q | R8：安全複核 A7-2 | 另一 session 有相同 `pending_id` 的列 ⇒ A2 燒綁定卡後該列 `redeemed` 不變 | 整合＋DB | | 通過 |
| 9r | R8：範圍閘 | 擋下後從 DB 取新 token 的 `pending_id` 送 `confirm_submit:<pid>` ⇒ violation `confirm_unknown_pending_id`、寫入 0 | 單元＋DB | | 通過 |
| 9s | R8：無旁路 | 正式碼 `redeem_token(` 呼叫點 0（正對照 `redeem_pending(` ≥1）；`INSERT INTO agent_confirmation_tokens` 只在 `tools/confirm.py`（正對照同檔 `UPDATE agent_confirmation_tokens` 命中） | 靜態 grep | | 通過 |
| 9t | R8：早退不燒 | 回候選或缺欄的 `confirm.request` ⇒ 舊卡仍可兌現 | 單元＋DB | | 通過 |
| 9aa | R8：安全複核 A7-6 | 清單點選作廢舊卡時 DB 同步燒；模擬他回合以舊狀態存檔 ⇒ 舊 pid 仍兌現失敗 | 單元＋DB | | 通過 |
| 10 | R1～R8 | 獨立驗證 | fresh verifier | 報告 | CONFIRMED |

收窄（非目標，附理由）：
- A-2（候選選擇，原 A5）、B（回話層閘）、C（結構化卡）、D（知識捏造）：分片，A 驗收後各出計畫；A-2 帶入安全複核 A5-1～A5-5。
- 不設門檻（DSP-087）。
- 「把本地替換 oss」：第 1 步 commit `2892a183` 已完成，本片不改模型接線。
- 正式機、preview 不碰；JGB 端改動不在本片。
