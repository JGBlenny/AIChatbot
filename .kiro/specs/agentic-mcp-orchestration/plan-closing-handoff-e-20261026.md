# E 片計畫：收尾與明確要真人由程式決定（r3，2026-10-26 業主核可）

規則與凍結清單：`acceptance-closing-handoff-e-20261026.md`（r3；規則 E-R1～E-R12、清單 E1～E13、非目標、## 廣度）。原則 P7。上線最低範圍內（DSP-115）。r1、r2 審查發現與處置見 §10。

## 0. 先答三題、終點指標、斷路器

**廣度**（全域「驗收廣度」第 7 條）：
1. 每項幾組資料 × 幾種輸入 × 重複幾次：E1 明確要真人 6 組情境 × 8 輸入 × 1 次；E2 道謝收尾 8 組（知識主題 5／10 抽樣＋寫入完成 3／5 抽樣）× 8 × 1；E3 未決不收尾 4 組 × 5 × 1；E4 不誤觸發 6 組情境 × 8 × 1；E5 W2 道謝題組 10 主題 × 1 句 × 2 輪（機制項）；E6 M0 題組 29 題 56 場 × 1；E13 E2a 6 組 × 6 腳本 × 2 輪。
2. 輸入誰寫：E1～E4 由不讀程式的 fresh 代理依配額撰寫、跑前凍結；E5、E6、E13 為既有題組（E13 為實作方所寫，只當不退步證據，§8 Q-E4）。
3. 跟改前比：E1～E6、E13 全部在改前程式（W2 收案程式）與改後程式同輸入各跑一次並列。

**終點指標**（目標文件＝目標正本 `architecture-target-20261018.md` §1「每片怎樣算完成」的全部量法；本片的凍結清單是本片自己的收案門檻、不是目標文件）。受測物＝常駐 `aichatbot-rag-orchestrator`，`runtime.py` md5 `c37bf5024fc4135597adc27c0890f701`（W2 收案程式，HEAD `720f0bf7`＋未提交改動）。「前兩片」＝計畫點名目標正本為目標文件的最近兩片：選對紀錄片（`plan-pick-right-record-20261021.md` 終點指標以 M0 鎖定類別「系統換成別張帳單」計，PV2-3 引目標正本 §1「測試全過」）與第 3 步整體驗收 OV（`plan-overall-acceptance-step3-20261021.md` 引目標正本 §1「怎麼量」、P5 跑 M0 題組）。之後的 F12（含 r4～r6）與選定後指令式片，計畫點名的目標文件是 F12 計畫（`plan-post-pick-commands-20261024.md`「終點指標（目標文件＝`plan-name-lenient-f12-20261022.md` §1 終點表…」；`f12/report-f12-close.md`「終點指標（目標文件＝r5 計畫 §1 終點表…」），目標正本只當上位驗收方式，不計入；W2 的計畫與清單沒點名目標正本（`grep -c "architecture-target\|目標正本"` 兩檔皆 0；正對照本檔 ≥1），不計入。以下路徑除另註外在 `~/jgb-archive/arch-step3-20261018/`。

| 量法（目標正本 §1） | 門檻 | 現值（來源） | 本片預期 | 前兩片實際變化（來源） |
|---|---|---|---|---|
| M0 題組判分場解決數，各列 W、W-D、A、K、全部（Intercom 式／嚴格） | 改後 ≥ 改前 | **現值未量**；業主 2026-10-26 選「核可後、改程式前量 (Recommended)」——X2 在改前程式量，同批即改前對照（E6）。最近一次是選對紀錄片程式 44/52（`pick-right/report-pick.md`），⛔ 當現值 | 0（每列 ±0；本片只動「要真人／道謝」回合，M0 這類回合只有 K 組收尾句） | 選對紀錄片：判分場解決 45/52 → 44/52（−1，`pick-right/report-pick.md`「判分場 44 < 45」）；OV：A 後 35/52 → 51/52（+16，`overall/report-ov.md` V5／V6 表，同一真值 DSP-102） |
| 鎖定缺陷「道謝後轉真人」（M0 場數） | 0 | 未量（同上）；最近 OV 0 場（`overall/report-ov.md`） | 0（維持） | OV：K3_k2、K4_k2、K8_k2 三場在 A 後已 3/3 解決 → 現在 3/3，變化 0（`overall/p5_v5_table.md`「道謝後轉真人」列：M0 0/3、A 後 3/3、現在 3/3）；選對紀錄片：報告無此列、計 0 |
| 既有回歸題組 E2a 六組 | 每組改後 ≥ 改前 | **現值未量**（最近 W2 C5 是 r2 shim 映像，⛔ 當現值）；X1 在改前程式量——要業主明示接受（§8 Q-B） | 0（每組 ±0；本片改寫入意圖呼叫的 schema 與系統句，E13 驗） | 選對紀錄片：R、C、T 2/2，RS 1/2，DS 經補跑 2/2（`pick-right/report-pick.md` V8，照字面不過、判非本片退步）；OV：六組皆 2/2＝B 片（`overall/report-ov.md` V8），變化 0 |
| 單元測試全過 | 全過 | 9 failed、6601 passed，失敗集合＝OV 基準（`w2/unit-close-c7.txt`，2026-10-26 10:33:56，md5 c37bf502）——**未達字面** | 0（9 筆不變；新測試全過） | OV：失敗集合與 A-2a 收案基線相同（`overall/report-ov.md` V8 標題）；選對紀錄片：照字面報（PV2-3） |
| `make audit` | PASS | PASS（`w2/invariants-after-noshim-rebuild.txt`「OVERALL: PASS（2026-10-26）」，10:31:58，md5 c37bf502） | 0 | 選對紀錄片：PASS（`pick-right/report-pick.md` V8「audit PASS」）；OV：PASS（`overall/report-ov.md` V8） |

本片在目標文件全部量法上的預期變化都是 0：鎖定缺陷在 OV 已經是 0，本片的使用者價值在 M0 題組沒涵蓋的「明確要真人」（探針 16/16 被降成追問、轉人 0，§3），以及 W2 殘餘的道謝截斷轉人（W2 r2 1/20、C7 1/13），由本片清單 E1～E5 量。依全域「終點指標」，預期 0 的片要業主明示同意（§8 Q-B）。

**斷路器**：前兩片的實際變化為選對紀錄片 M0 −1、OV M0 +16，不全為 0 ⇒ **不觸發**。本片若收案時目標文件量法仍全為 0，下一片點名目標正本時即計為第一個 0。

## 1. 目標

使用者道謝就收尾、不被轉真人；明說要真人時直接被轉過去（業主原話與規則見規則檔一節）。實際事件：M0 道謝後轉真人 3 場（K3_k2、K4_k2、K8_k2）；W2 r2 道謝 1/20、C7 新輸入「謝謝 辛苦了🙏」1/13 被轉人（主模型截斷 18.3 秒 ⇒ `budget_exhausted`，回「這題我這邊沒有可靠資料，幫您轉專人」）；探針明確要真人 16/16 未轉。

## 2. 目標形態（業界原頁渲染檔；逐字）

- 理解標「要真人」、流程決定怎麼轉：Rasa「The user wants to speak to a human」（`~/jgb-archive/devflow-20261018/sources-repair/rasa-dialogue-understanding.txt`）；Intercom「Escalation Rules and Guidance decide when escalation happens. Workflows decide what happens next.」（`devflow-20261018/sources-arch/intercom-fin-escalation.txt`）；Salesforce「Tells the agent to escalate to a human service rep.」（`~/jgb-archive/arch-step3-20261018/e/sources/salesforce-ascript-ref-utils.txt`，2026-10-26 渲染）。
- 客人要真人 ⇒ 轉：Intercom「If the customer clearly requests human support, Fin escalates directly.」（`sources-arch/intercom-conversational-fin.txt`）；Zendesk「The AI agent escalates to a human agent when the customer requests it, when a procedure specifies it, or when the AI agent cannot confidently resolve the request in one response.」（`e/sources/zendesk-email-agentic.txt`）；Salesforce「When a customer or employee wants to chat with a person or the conversation becomes complex or sensitive, the agent launches the Escalation subagent.」（`e/sources/salesforce-service-agent-channels.txt`）。不同做法：Rasa 文件範例先確認再轉（`collect: confirm_human_handoff`，`sources-repair/rasa-patterns.txt`）；Intercom Guidance 可設先詢問（`sources-arch/intercom-fin-escalation.txt`）。本片採直接轉（P7、O6）。
- 道謝當已解決 ⇒ 收尾：Intercom「Indicate that Fin has answered their question by responding positively (e.g., “That helped,” “Yes,” or “OK, thanks”).」，並自述風險「Some phrases can be interpreted as a positive response even when the customer still needs help.」（`sources-arch/intercom-conversational-fin.txt`）——對應 E-R3；Salesforce「Use utils.end_session when the agent should terminate the session, for example after completing a task or when a specific condition is met.」（`e/sources/salesforce-ascript-ref-utils.txt`）；Zendesk「Small talk recognition. The AI agent recognizes small talk and responds appropriately…」（`e/sources/zendesk-email-agentic.txt`）。主動詢問型：Rasa `pattern_completed`「Flow that asks if the user needs more help after completing their initiated use cases」（`sources-repair/rasa-patterns.txt`）——業主選不做（RE-1 甲）。
- 逐家有據的說法：三家（Intercom、Zendesk、Salesforce）原文有「客人要真人 ⇒ 轉」；「道謝＝已解決」只有 Intercom 逐字，Salesforce 是「任務完成可結束 session」、Zendesk 是「閒聊照常回應」。
- 轉人句是系統預設回覆：Zendesk 系統回覆表「Escalation reply	What the AI agent should say when escalating a conversation to a human agent.」（`sources-arch/zendesk-system-replies.txt`）。同表的「Collect BSAT reply	What the AI agent should say at the end of a conversation to collect feedback from a customer about their experience.」是對話結束時收集滿意度，不是收尾致意句。
- 收尾句由程式樣板出：**第一原理推導、查無業界對應**——所列渲染頁中沒找到「收尾致意句」的系統回覆設定（Zendesk 系統回覆表只有 BSAT、轉人、預設、錯誤等列）；推導依據是 DSP-091 帶狀態句歸程式（收尾＝對話已結束的狀態），以及 W2 實測主模型生成收尾句時會截斷、灌空白（§3）。

完整研究（含反例、相關但不在範圍）：`~/jgb-archive/arch-step3-20261018/next/target-e.md`。

## 3. 差距（對碼＋實跑；可重跑）

| 環節 | 現況 | 查證 |
|---|---|---|
| 明確要真人 | 主模型自報 `kind=handoff`（主輸出 schema 與 `handoff.request` 工具 enum＝`HandoffReason` 全部 6 值；系統句只指引 `no_grounding`／`sensitive_no_grounding`），零查詢 ⇒ `_apply_handoff_without_lookup` 降成 `ASK_TARGET_TEXT`「想處理哪一件事？講名稱或編號就可以。」。**探針 16/16 降成追問、轉人 0**（兩種身分 × 4 說法 × 開場／知識答後；violations 16/16 含 `handoff_without_lookup`，知識答 8 回合 0） | `grep -n "def _apply_handoff_without_lookup" -A45 rag-orchestrator/services/agent/exit_gates.py`；`grep -n '"enum": \[r.value for r in HandoffReason\]' rag-orchestrator/services/agent/runtime.py`；`grep -n "HANDOFF_REASONS: Final" rag-orchestrator/services/agent/tools/handoff.py`；`~/jgb-archive/arch-step3-20261018/e/probe/SUMMARY.txt`（指令 `python3 probe_gap.py run1`） |
| 引導語 | 狀態句閘無據時回 `HANDOFF_OFFER_TEXT`「需要真人客服的話，請直接說「找真人客服」。」——照說會被降成追問（同上探針第 1 句） | `grep -n "HANDOFF_OFFER_TEXT" rag-orchestrator/services/agent/write_forms.py` |
| 道謝收尾 | 只有給主模型的提示規則（`agent_rules.py`「使用者說結束、好了、謝謝等收尾語，簡短收尾即可」）；收尾句由主模型生成；主模型截斷晚發生 ⇒ `budget_exhausted` 轉人（W2 殘餘、C7 F1）；W2 灌空白 5 次全在道謝收尾句 | `grep -n "收尾語" rag-orchestrator/services/agent/agent_rules.py`；`w2/report-w2-close.md` §3 |
| AI 理解標籤 | 意圖判斷呼叫（`_start_write_intent_call`）在 `acc.write_draft` 非 None（開關 on、非影子、非 `select:` 釘住範圍）、非文件回合、看得到 `jgb2.action.*` 時建立；schema 只有寫入動作＋`none`；無「要真人／已解決」。r2 實錄 168 次：p50 0.58 秒、p95 1.46 秒、最長 7.85 秒；主模型 p50 1.15、p95 2.83 秒 | `grep -n "def _start_write_intent_call" -A15 rag-orchestrator/services/agent/runtime.py`；`w2/r2/calls/calls.jsonl`（`max_tokens==800` 的非主呼叫） |
| 程式優先入口 | `_write_draft_program_first` 在主模型迴圈前等意圖判斷（有草稿 3 秒、無草稿 1 秒），未完成就交主模型；`wd is None`、`wd.triggered`、`wd.frozen`（程式追問後的問句）、當句命中 `question_sensitive` 時先 return、**不等待** | `grep -n "async def _write_draft_program_first" -A30 rag-orchestrator/services/agent/runtime.py` |
| 迴圈前程式出口 | 重送、卡仍有效、剛送出三個出口（`_write_draft_reissue_exit`／`_write_draft_card_still_valid_exit`／`_write_draft_submitted_exit`）與候選按鈕回合，在主模型迴圈之前回、不叫主模型 | `grep -n "reissue_exit = (self._write_draft_reissue_exit" -A8 rag-orchestrator/services/agent/runtime.py` |
| 轉人原因值域 | `HandoffReason` 無「使用者要求」；B 片測試兩處用了不在值域的 `handoff_reason="user_request"` 當模擬模型輸出 | `grep -n "class HandoffReason" -A12 rag-orchestrator/services/presales_gate.py`；改前（commit `720f0bf7`）`git show 720f0bf7:rag-orchestrator/tests/unit/agent/test_b_write_replies_program_req.py | grep -n user_request` |
| 接入方契約 | `kind=handoff` ⇒ 前端顯示「找真人」；`handoff.reason` 不在契約；`outcome.state` 已有 `handoff`、`answered` | `grep -n "handoff" docs/api/jgb2-web-assistant-integration.md` |
| 分工登記 | KD-5「轉人由模型輸出決定，出口閘只在模型選了轉人後介入；無收尾規則」 | `grep -n "KD-5" rag-orchestrator/tests/unit/agent/dsp091_known_deviations.py` |
| 卡住 | 無；`fixed_streak` 有寫無讀（非目標） | `grep -rn "fixed_streak" rag-orchestrator/services/agent/ --include='*.py'` |

## 4. 路徑

### 4.1 做法

1. **AI 理解：對話動作標籤**（r5，§6 第 9 點）。每個使用者文字回合另建一次只含 `dialog_act ∈ {wants_human, resolved, none}` 的標籤呼叫（`_DialogActCall`，存 `acc.dialog_act_call`；同模型、同 `max_completion_tokens` 800、同 dialog 輸入），建立時點同 `_start_write_intent_call`，與主模型、寫入意圖呼叫並行；寫入意圖呼叫的 schema 與系統句不帶 `dialog_act`（與改前相同）。系統句說明：`wants_human`＝使用者要求現在由真人客服接手；`resolved`＝只道謝或表示已解決、同句沒有新請求；其餘 `none`（含「問怎麼聯絡客服」、轉述客服說過的話）。文件回合不跑（非目標）。
2. **程式規則**（新函式 `_dialog_act_exit`；E-R1～E-R4）：
   - `wants_human` ⇒ 程式轉人：`kind=handoff`、`handoff.reason=user_request`、回覆 `USER_REQUEST_HANDOFF_TEXT`；不經 `_apply_handoff_without_lookup`。當句命中 `question_sensitive` ⇒ 不走本出口、照現行敏感路徑（E-R6）。
   - `resolved` 且無未決狀態（`pending_confirm` 無未兌現卡、寫入草稿無進行中欄位、候選集未開）⇒ 程式收尾：`kind=answer`、`outcome=answered/text`、回覆 `CLOSING_TEXT`。有未決狀態 ⇒ 照現行（E-R3）。
   - 其他 ⇒ 照現行。
   - **值域隔離（E-R4）**：`HandoffReason` 加 `user_request`；主模型可見的兩處值域改用排除 `user_request` 的子集——主輸出 schema（`_agent_output_response_format` 的 `handoff_reason` enum）與 `handoff.request` 工具 enum（`tools/handoff.py` `HANDOFF_REASONS`）。兩處排除不受開關影響，所以這兩份定義與改前逐位元組相同（E8）。工具路徑：registry 依 `input_schema.enum` 擋，子集已排除 `user_request`。主輸出路徑（`out.handoff_reason` 直接進 `"reason": out.handoff_reason or "no_grounding"`，不經 `parse_handoff_reason`；主模型不一定守 enum，正式站 Verifier 為觀察模式不擋）另加一道決定性檢查：開關 on 時，主模型輸出的 `handoff_reason` 不在模型可見值域 ⇒ 視同自報 `no_grounding`，走現行降級閘（`_apply_handoff_without_lookup` 等）；開關 off ⇒ 不加這道、與改前相同。`verifier.py` 的值域檢查改用模型可見子集（＝改前的 6 值，行為不變）；程式轉人結果以程式來源標記（例：`acc` 上程式出口自己設的旗標）辨識，若 `exit_gates.finalize` 對它套 handoff 原因檢查，依該標記放行，⛔ 以 reason 字串放行。B 片兩處 `handoff_reason="user_request"` 的模擬輸出依該測試原意改：測轉人流程的改合法值；不改語意的保留，並驗「開關 on ⇒ 降級、off ⇒ 同改前」。
3. **時序（三個決定點，不新增迴圈前等待）**：
   - (a) 迴圈前：標籤已完成 ⇒ 直接依 2. 決定。現行 `_write_draft_program_first` 有等待的回合，等待期間完成的標籤同樣可用；程式優先入口已等滿逾時 ⇒ 不再多等。迴圈前程式出口（重送、卡仍有效、剛送出）要回之前，或程式優先入口已備好程式訊息（這一輪不叫主模型、程式回話可能直接結束回合，例：候選清單重問）時，標籤未完成 ⇒ 至多等 1 秒（有草稿 3 秒，同現行分級），讓「有卡、有候選清單也直接轉」（E-R1）成立；候選按鈕回合沒有使用者文字，不等。
   - (b) 迴圈中：主模型串流與標籤呼叫競速；標籤先完成且結果為 `wants_human`，或為 `resolved` 且無未決狀態 ⇒ 取消進行中的主模型呼叫（沿用 W2 的期限中斷與估算計量 `llm_usage_estimated`），改回程式結果，trace 記 `dialog_act_late`。W2 的期限中斷是同一 task 內 `asyncio.timeout(remaining)` 丟 `_ModelCallDeadline`、`_run_model_loop` 接住走 `budget_exhausted`；標籤搶先的取消另用自己的例外或旗標分流，⛔ 落入 `budget_exhausted`（E7 測）。這條也涵蓋 `wd.frozen`（追問中的問句）、無草稿、看不到寫入動作的回合。
   - (c) 迴圈出口：主模型最終輸出要進 `_write_draft_after_output` 與出口閘之前，標籤未完成 ⇒ 至多再等 1 秒；仍未完成 ⇒ 用主模型輸出，記 `dialog_act_fallback`（後備，KD-5 (3)）。
   - 延遲成本：不觸發的回合只在 (c) 主模型先結束時多等，上限 1 秒；r2 實錄標籤 p50 0.58 秒，比主模型 p50 1.15 秒快，所以多數回合不多等。E4 量改前改後耗時（p50 差 ≤ 1.0 秒）。
4. **樣板**（預設文字，業主可改，見 §8 Q-E1）：`USER_REQUEST_HANDOFF_TEXT`＝「好的，幫您轉真人客服，請點下方的『找真人』。」；`CLOSING_TEXT`＝「不客氣，有需要再找我。」。
5. **開關** `AGENT_CLOSING_HANDOFF`（未設＝on；off ⇒ 不加欄、不建呼叫、不走 2.／3.，行為同改前）。
6. **分工登記**：KD-5 改寫為剩下的三項偏離——(1) 卡住先詢問、不連發未實作；(2) 知識查無的轉人仍由模型自報（歸 D、KD-6）；(3) 意圖判斷呼叫逾時或未完成的回合，要真人與收尾由主模型輸出決定（後備）。接手片：(1)(3) 改「E 續（上線後）」，(2) 維持 D。E-R1、E-R2 寫進 `test_dsp091_division_contract_req.py` 必過契約；目標正本 §3 P7 列與 §3.1 同步。

7. **道謝不填欄**（r4，§6 第 8 點）：寫入草稿正在追問欄位時，該句 `dialog_act` 為 `resolved` 或 `wants_human` ⇒ 程式不把該句當欄位答覆填入，草稿原樣保留（含「正在追問哪一欄」，下一句照現行整句填入）；`wants_human` 依 2. 轉人，`resolved` 回現行缺欄追問。寫入意圖抽出的值與主模型的欄位提議同樣不合併（修正 8）。`resolved` 先另發一次同輸入的標籤確認呼叫（至多等 3 秒，以回合剩餘期限為界），確認為 `none` ⇒ 是欄位答覆、照現行填入（r6，§6 第 11 點）。判斷前標籤未完成 ⇒ 至多再等 1 秒（以回合剩餘期限為界，r5）；仍未完成、或確認呼叫未完成 ⇒ 不填、程式重問缺欄（r6，§6 第 10 點）；開關 off 同改前。

### 4.2 改動檔（預估）

`rag-orchestrator/services/agent/runtime.py`（標籤呼叫、三個決定點、`_agent_output_response_format` 值域子集、主輸出值域檢查）、`exit_gates.py`（若需：程式轉人標記放行）、`write_forms.py`（schema 與系統句、樣板常數）、`rag-orchestrator/services/presales_gate.py`（`HandoffReason.user_request`）、`services/agent/tools/handoff.py`（`HANDOFF_REASONS` 改用子集）、`verifier.py`（handoff 原因值域）、`tests/unit/agent/test_closing_handoff_e_req.py`（新）、`test_b_write_replies_program_req.py`（兩處模擬輸出）、`dsp091_known_deviations.py`、`test_dsp091_division_contract_req.py`；文件：目標正本 §3、§3.1、§4 E 列、`docs/architecture/AGENTIC_MCP_ARCHITECTURE.md` §4b、HANDOFF。`agent_rules.py` 的收尾提示規則保留（後備路徑仍用）。⛔ 他窗 4 份檔。寫入意圖呼叫的 schema 與系統句不改（r5），但追問中的整句填入改看標籤 ⇒ 寫入路徑可能受影響，由 E13（E2a）與 E6 W 組驗。

### 4.3 偏離目標形態的取捨

- 不做「卡住先詢問、不連發」：業主裁延後（O6）；M0／OV／W2 無事件。
- 不做完成後主動詢問：業主裁（RE-1 甲）。
- 標籤逾時的回合由主模型決定（後備，KD-5 (3)）：後備路徑上明確要真人仍可能被降成追問；E1 未過的場會落在這裡，逐場附根因。理由：要讓程式在每一回合都等到標籤，等待上限就得拉到標籤最長耗時（r2 實錄最長 7.85 秒），所有知識回合都會變慢；現行 1 秒上限是 W1c 為知識回合延遲訂的。這條偏離 DSP-091「轉人規則歸程式」，登記在 KD-5 (3)，接手片「E 續」。追問欄位中的回合例外：標籤未完成 ⇒ 程式重問缺欄（r6），因為照現行整句填入會出錯筆卡。

## 5. 驗收

見規則檔 §二（E1～E13）、§三非目標、## 廣度。

## 6. 業主裁示（2026-10-26，AskUserQuestion；問題原文照錄）

1. 「E 片範圍：P7 有三件事——道謝即收尾、明確要真人直接轉、卡住先詢問且不連發。M0／OV／W2 都沒有「卡住」的實際缺陷場，而且「卡住」怎麼定義（數輪數或由 AI 判斷）、連發後怎麼處理，Intercom 兩頁說法不同。上線前要做哪些？」⇒「道謝＋要真人，卡住延後 (Recommended)」
2. 「道謝收尾的時機（RE-1）：只在客人道謝或說已解決時，由程式回收尾句；還是任務完成後也由程式主動問「還需要其他協助嗎」？」⇒「只在客人道謝時收尾 (Recommended)」
3. 「道謝碰上未決狀態（RE-4）：例如確認卡已經出了、客人還沒按就說「謝謝」，或說「謝謝，那延期呢」。要怎麼處理？」⇒「有未決卡或帶新請求就不收尾 (Recommended)」
4. 「終點指標現值：W2 之後的版本還沒量過 M0 題組（56 場，最新完整值是 OV 版本 d1ddc084 的 51/52）。這組量測要用模擬客人分批跑、會重啟容器，規模跟 OV 的 P5 一樣。何時量？」⇒「核可後、改程式前量 (Recommended)」
   - **更正**（主會話問題文字有誤；核可時已當面告知）：M0 最新完整值是選對紀錄片改後 44/52（`pick-right/report-pick.md`），不是 OV 51/52；同版 `d1ddc084` 選對紀錄片改前也量到 45/52。本題業主裁的是量測時機，不受影響。

核可（2026-10-26，AskUserQuestion；選項原文）：

5. 「E 片計畫 r3（plan-closing-handoff-e-20261026.md）要核可嗎？…」⇒「核可 (Recommended)」
6. Q-B「本片在目標正本的量法上（M0 各列、E2a、單元、audit）預期變化都是 0，使用者價值由 E1～E4 量；E2a 現值核可前未量，改程式前（X1）量。同意嗎？」⇒「同意兩者、續做 E (Recommended)」
7. Q-E4「E2a 六組每組只有 1 筆資料，腳本是實作方寫的，不符驗收廣度下限。要怎麼處理？」⇒「照原樣，只證不退步 (Recommended)」

r4 增補（2026-10-26，核可後、改前量測中發現；AskUserQuestion，問題原文照錄）：

8. 「改前量測發現：客人填修繕單填到一半（系統正在問「問題描述」），只回一句道謝，例如「好喔謝謝」，系統就把這句當成問題描述，出一張「問題描述：好喔謝謝」的確認卡。5 場重現 5 場（標記 write_draft_answer_filled）。物件是對的，錯的是欄位內容；客人按下確認就會寫進一筆內容錯的修繕單。DSP-115 第 3 點規定寫錯資料不得後補，但這不在已核可的 E 片範圍內（E-R3 只要求「不收尾、草稿仍在」，兩項改前都已 5/5）。要怎麼處理？」⇒「併進 E 片 (Recommended)」（選項說明原文：「AI 標成「已解決」或「要真人」的那句不拿來填欄位，草稿保留並重問缺的欄位（程式依 AI 標籤決定，不用詞表）。清單加一項：填欄中組道謝被填進欄位 0/5，改前 5/5 並列。計畫與凍結清單補一節 r4 附錄，由這次裁示核可；不另送 plan-verifier，由最後的 fresh verifier 一起驗。」）
   - 證據：`~/jgb-archive/arch-step3-20261018/e/before/E3/records.jsonl` 填欄中組 5 場 test 回合 violations 皆含 `write_draft_answer_filled`、卡上「問題描述」＝使用者那句道謝；彙總 `e/before/analysis.json`。
   - 做法（§4.1 第 7 點）：寫入草稿正在追問欄位（程式持有的「缺欄」狀態）時，該句 `dialog_act` 為 `resolved` 或 `wants_human` ⇒ 程式不把該句當欄位答覆填入（不產生 `write_draft_answer_filled`），草稿原樣保留；`wants_human` 另依 E-R1 轉人；`resolved` 依 E-R3 不收尾，回現行的缺欄追問（重問缺的欄位）。標籤未完成（後備）⇒ 照現行，登記在 KD-5 (3)。開關 off ⇒ 同改前。
   - 驗收：清單 E-R13、E14；廣度 3 組資料（修繕缺問題描述、手開帳單缺帳單項目、建物件缺物件名稱）× U3a 5 句，改前改後同批；改前在 M0 改前跑完後、重建前量。

r5 增補（2026-10-26，改後量測中發現；AskUserQuestion，問題原文照錄）：

9. 「E 片「要真人」判斷要改機制，偏離已核可計畫 §4.1「寫入回合沿用同一次呼叫（不加呼叫）」。實測同一句「上次真人客服說退租的話要」：合併在寫入意圖呼叫裡 8 次有 4～5 次誤判成要真人；改用單獨的標籤呼叫，同樣 6 種情境 48 次只錯 1 次（「專人」在填欄中 7/8 對、「3Q」8/8、「冷氣不冷」8/8）。我已試過 3 版提示詞措辭與「規則放最前面」，都壓不住或讓「專人」退步。改法＝每個使用者文字回合都另發一次只判標籤的呼叫（與主模型、寫入意圖並行），寫入意圖呼叫回到改前系統句。代價：有寫入意圖的回合多一次模型呼叫（約 1～2 千 token），延遲不增加（並行）。要怎麼做？」⇒「改用單獨標籤呼叫 (Recommended)」（選項說明原文：「寫入回合也另發標籤專用呼叫並以它為準；寫入意圖系統句回到改前。計畫與凍結清單補 r5 附錄記這次裁示，之後全量重跑 E1～E5、E14、E13，由最後的 fresh verifier 一起驗。」）
   - 證據：改後第一輪（合併呼叫）E4 程式轉人 4/48、修正 2 定向 12/12、修正 3 定向 12/12，皆為 U4-5；容器內直接打兩種呼叫（`~/jgb-archive/arch-step3-20261018/e/probe_label/probe_variants.py`、`probe_sep.py`）：合併呼叫 U4-5 開場 4/8、填欄中 5/8 判 `wants_human`，標籤專用呼叫 0/8、0/8；改後定向（`e/probe4/`）U4-5 0/12、U1-3 11/12。
   - 做法：§4.1 第 1 點、第 3 點 (a)、第 7 點（r5 已改正文）；凍結清單 E-R1～E-R13 與 E1～E14 的判準不變，E11 的 KD-5 (3) 讀作「標籤呼叫逾時或未完成」。

r6 增補（2026-10-26，X7 verifier REFUTED 後修正 8 的重查與全量重跑中發現；AskUserQuestion，問題原文照錄）：

10. 「標籤呼叫逾時（約 1%）時，程式目前照改前做法，把客人那句整句填進欄位。本批量測出了 2 張錯卡：「ok thx」被填成物件名稱、「我想找真人客」被填成問題描述。要改成逾時就重問缺欄嗎？」⇒「改成重問缺欄 (Recommended)」（選項說明原文：「標籤逾時時不整句填入，程式重問缺的那一欄。錯卡歸 0；代價是逾時那約 1% 的回合，真正的欄位答覆也要客人再講一次。」）
    - 證據：`~/jgb-archive/arch-step3-20261018/e/fix8/recheck/records.jsonl`（fill1_estate「ok thx」rep 1：`dialog_act_fallback`、`dialog_act_call_cancelled`、卡上「物件名稱：ok thx」）；`e/after8/E1/records.jsonl`（filling U1-6「我想找真人客」：同兩標記、卡上「問題描述：我想找真人客」）。
11. 「修正 8 擋住了「3q 被填進欄位」的錯卡，但 AI 偶爾會把真正的欄位答覆標成道謝，程式就跳過、重問一次：道謝後補答 5/35、E13 建合約完整答覆 1/2。要怎麼處理？」⇒「再問一次標籤確認 (Recommended)」（選項說明原文：「只在追問欄位時、標籤是道謝或要真人的回合，多發一次標籤呼叫；兩次一致才跳過。誤判預期大幅下降，只有這類回合多約 0.5～1 秒；仍由 AI 判斷，不用詞表。」）
    - 實作讀法：確認呼叫只用在第一次標籤為 `resolved` 的回合；`wants_human` 仍一次即轉人（E-R1，轉人回合不填欄）。確認為 `none` ⇒ 是答覆；其餘或未完成 ⇒ 不填、重問（同第 10 點）。
    - 證據：`e/fix8/recheck` post_fill 誤跳 4/11、`e/fix8/recheck-obs`（帶 `dialog_act_field_label` 觀測標記）1/24，標籤確為 `resolved`；E13 C 組 `e/e2a/after8/C` rnd 0 第 3 回合；離線同輸入 `e/probe8/`。
12. 「E4（轉述客服的話不該轉人）這批 1/48 被程式轉人：在候選清單情境，半句「上次真人客服說退租的話要」被 AI 標成要真人，凍結門檻是 0/48；修正 6 後是 0/48、修正 5 是 2/48，屬 AI 標籤本身的變異。要怎麼處理？」⇒「列已知偏離、後補 (Recommended)」（選項說明原文：「誤轉人不會寫錯資料，依 DSP-115 可以後補。收案時照實寫 1/48，附根因與修正 5、6 的對照。」）

r7 增補（2026-10-27，X8 verifier REFUTED 後；AskUserQuestion，問題原文照錄）：

13. 「客人在追問欄位時「答覆＋道謝」（例：好的 項目是管理費 謝謝）被 AI 標成已解決、被要求重講。這算 AI 標錯要修，還是接受？」⇒「算標錯，修正 10 (Recommended)」（選項說明原文：「標籤規則補一句語義：「正在追問欄位時，句子帶有該欄的資料，即使同時道謝也標 none」（不是詞表，符合 E-R5）；重跑主要驗收約 20 分鐘＋X8 退步組（3 組 × ≥6 句 × 3 次），再派新驗證員 X9。」）
    - 證據：X8 `scratchpad/x8/run_reg/records.jsonl`、`x8/rep/run_reg/records.jsonl`：5 句 × 3 組，14/15 為 `dialog_act_field_label:resolved`＋`dialog_act_field_confirm:resolved`＋`dialog_act_fill_skipped`；`DIALOG_ACT_RULE` 只寫「道謝的同時又提出新的請求或問題」⇒ none，未涵蓋「道謝的同時回答追問的資料」。
14. 「E3 原卡兌現 4/5（寫入意圖從「好 謝」多抽出欄位、重出新卡；與改前逐字相同、無錯筆）。怎麼處理？」⇒「列已知偏離、後補 (Recommended)」（選項說明原文：「照 DSP-115：不錯筆、不擋上線；寫進後補清單（寫入意圖抽取），收案報告照實寫 4/5、未達字面。」）
15. 「E3 新請求組：要不要先重跑盲判再決定？如果結果仍低於 5/5，而且根因是既有的降級閘（改前就有），怎麼算？」⇒「重跑盲判，既有根因列偏離 (Recommended)」（選項說明原文：「跟著修正 10（或現況）的重跑，對新請求那 5 場重跑盲判；未達 5/5 而且根因是 handoff_without_lookup ⇒ 列已知偏離（歸 D／KD-6），照實報。」）
16. 「分兩句講的情況（先單獨送「謝啦」，下一句才提新請求），第一句被程式收尾。這算合規嗎？」⇒「算合規 (Recommended)」（選項說明原文：「依 E-R2、E-R3 字面「同句沒有新請求」，單獨一句道謝就收尾；下一句新請求照常處理。E3 收尾 0/20 的算法維持只看最後一個 test 回合。」）

r8 增補（2026-10-27，修正 10 兩版實跑後；AskUserQuestion，問題原文照錄）：

17. 「修正 10 v2 把「答覆＋道謝」修好了（18/18 填上卡，改前 1/15），但出了錯筆卡：追問物件名稱時回「OK 3q」，8 次裡有 3 次出了「物件名稱：3q」的卡（F1 不過 3/24，改前 0/24）。另外 E4 多了 1 次誤轉真人：「你們客服有 LINE 嗎」，程式轉人 2/48，改前 0/48。第一版錯 8/24、第二版錯 3/24，都是同一個取捨：AI 有時會把「3q」讀成名稱。接下來怎麼做？」⇒「退回修正 9，答覆＋道謝列偏離 (Recommended)」（選項說明原文：「拿掉修正 10。錯筆卡回到 0/24，E4 程式轉人回到 0/48（after9 實測）。代價是「好 名稱叫 X 謝謝」這類句子會被程式重問一次，使用者要再講一遍，但不會錯卡。這條列已知偏離、後補。可以用 after9 的整批結果，不用重跑，直接送 X9。」）
    - 修正 10 做法：追問欄位時，標籤呼叫的系統句附上程式持有的「正在追問哪些欄」。第一版只寫「含有這項資料就標 none」；第二版加「整句只有道謝、肯定、寒暄或表情就不是這項資料」。
    - 證據：第一版 `~/jgb-archive/arch-step3-20261018/e/fix10/first/`（F1 8/24）；第二版 `e/after10/`、`e/fix10/recheck.log`（不過 3/24：estate「OK 3q」第一次標籤 none 2/8、確認呼叫 none 1/6）、`e/fix10/x8reg/r1～r3`（答覆＋道謝 18/18 第一次標籤 none）、`e/after10/E4`（U4-5、U4-6 程式轉人）；離線探針 `e/probe9/`。
    - 退回後的受測物：runtime、write_forms 去 docstring 後 AST 與 after9 相同（after9 runtime md5 `dc7d6a5f24aa8bd6659be47b0aaa38e6`，以容器版逆向重建逐字吻合）；`e/after9/` 的整批結果適用。

r9 增補（2026-10-27，收案 verifier X9 判 REFUTED 後；AskUserQuestion，問題原文照錄）：

18. 「X9 判 REFUTED，而且推翻的是我上一題給你的前提，是我的錯：我說「退回修正 9 不會錯卡」，但只量過純道謝（OK 3q），沒量「答覆＋3q」。我逐場核過 X9 的紀錄：17 場裡有 11 場錯卡。例如「水電費 3q」被整句填成帳單項目；也有 AI 從 3q 抽出「金額：3 元」，把原本的 1,200 蓋掉，或抽出「面積：3」。這是改前就有的填欄機制：程式整句填入，加上寫入意圖抽值。E 片沒有引入它，E 自己的規則 E1～E14 也都重算過關。但 DSP-115 第 3 點規定錯筆卡不得後補。怎麼處理？」⇒「E 收案，緊接開一片修，上線前必修 (Recommended)」（選項說明原文：「E 照實收案，宣稱縮小到「標籤與出口」，報告寫明這個既有缺陷。收案後馬上開「填欄值不含道謝、不從道謝衍生別欄、不蓋掉已填的欄」一片，照「目標→目標形態→差距→路徑」起計畫，列為第 4 步切正式機前的擋點。修正 10 的取捨在那片重新比較。」）
19. 「X9 問了一個讀法題，會決定下一片怎樣算驗收通過：「答覆＋道謝」照填時，欄位應該填什麼？」⇒「只填答覆部分，衍生值算錯卡 (Recommended)」（選項說明原文：「例：「水電費 3q」只能填「水電費」。卡上出現道謝字，或出現從道謝衍生的別欄值（金額 3、面積 3），都算錯筆卡。」）
    - 證據：X9 `~/jgb-archive/arch-step3-20261018/e/x9-verifier/rep/run_r8/records.jsonl`（11 場）與 `x9-verifier/run_r8/records.jsonl`（6 場）。這 17 場中：第一次標籤為 `none` 的，照現行填入（`write_draft_answer_filled` 整句填入，或寫入意圖抽值），出現「帳單項目：水電費 3q」×3、「金額：3 元」×1（原 1,200）、「帳單項目：網路費 3Q」×2、「面積：3」×1、「空間類型：3q」×1、「問題描述：門鎖壞了 3q」×2、「問題描述：馬桶堵住了，感謝🙏」×1，共 11 場；標籤為 `resolved` 的走重問，沒有錯筆。改前同一機制：`e/before/E14/records.jsonl` 15/15 把道謝句整句填入（例「帳單項目：3Q」）。
    - 處置：E 片宣稱收窄為「標籤與出口」（E-R1～E-R13 照凍結清單判）；E-R13 範圍是標籤為「已解決」或「要真人」的回合，標籤為 `none` 時的填欄機制不屬本片。這個缺陷由下一片處理，排在第 4 步切換正式機前（DSP-117）。

## 7. 執行與測試選擇（全域「測試選擇」）

每回合耗時來源：探針 `e/probe/run1/probe.jsonl` 的 `sec` 欄，24 回合平均 2.62 秒、最長 5.0 秒（以下記為「每回合 2.6 秒」）；費用來源：探針 24 回合 US$0.0572（`usage_events.est_cost_usd`），約每回合 US$0.0024。

| # | 執行 | 回答的決定 | 會改變下一步的結果 | 規模與理由 | 跑前成本估計（來源） |
|---|---|---|---|---|---|
| X0 | 產 E1～E4 輸入（fresh 代理，不讀程式）並凍結 | 輸入廣度合格才能量 | 配額任一類缺 ⇒ 退回重寫 | 8＋8＋5＋8＝29 句，依情境展開成 48＋64＋20＋48 場 | 1 位代理約 15 萬 token（OV 產題 143,209，`overall/report-ov.md` 用量段） |
| X1 | 改前：E1～E5、E13 在現行程式 | 改前對照（E-R8）；E13 不退步的改前基線 | E1 改前若已 ≥46/48 ⇒ 交業主重看 E-R1 範圍；E4 改前已有程式轉人或收尾 ⇒ 先查量尺 | 全量：終點量測時機（E13）與改前對照 | E1～E5 量測 200 回合＋情境鋪陳約 255 回合 ≈ 455 回合 × 每回合 2.6 秒 ≈ 20 分，約 US$1.1；E13 88 回合（44 × 2）約 4 分（OV `overall/e2a/run_all.log` 建立 16:25:15、最後寫入 16:29:14），約 US$0.2 |
| X2 | 改前：E6 M0 題組 | 終點 M0 表現值＋改前 | 現值 < 40/52（低於同版已知最低值 44～45 再 5 場以上；同版 `d1ddc084` 量過 51 與 45，差異未查明）⇒ 先查量尺再動程式 | 全量：終點量測時機 | 56 場 × 每場約 15 秒（OV `overall/p5_driver.log` 16:30:33～16:44:34 跑完 56 場，約 14 分；不含判分）；模擬客人約 60 萬 token（OV P5 8 位 605,434）＋盲判約 40 萬（OV 盲判 417,392） |
| X3 | 單元與 `make audit`（每次改動） | 機制項 E7～E11 | 失敗集合≠基準 ⇒ 修 | 便宜決定性，全套 | 單元約 4 分 12 秒（`w2/unit-close-c7.txt`「252.07s」）；audit ≤ 2 分（`w2/invariants-after-noshim-rebuild.txt` 檔首 10:31:58 開跑，同一輪單元 `w2/unit-close-c7.txt` 檔首 10:33:56 開跑） |
| X4 | 改後：E1～E5、E13 | E1～E5、E13 過不過 | 未過 ⇒ 依 §8 停點 | 全量：終點量測（收案重量） | 同 X1 |
| X5 | 改後：E6 M0 題組 | 鎖定缺陷與不退步 | 任一列 < 改前 ⇒ 查根因（根因在本片 ⇒ 停） | 全量：終點量測 | 同 X2 |
| X6 | 開關 off：U1、U2 各 5 句 | E8 回復手段 | 與改前不同 ⇒ 修 | 5＋5 句足以涵蓋轉人與收尾兩條分支 | 10 回合 × 每回合 2.6 秒 ≈ 0.5 分，約 US$0.03 |
| X7 | fresh verifier（E12） | 收案 | REFUTED ⇒ 依 DSP-115 分流 | ≥10 新輸入 | 約 30 回合 × 每回合 2.6 秒 ≈ 1.5 分；約 20 萬 token（W2 C7 197,623） |
| X8 | 修正後重跑（若有） | 修正有效 | 修正場仍未過 ⇒ 計入同一阻擋發現的修正輪數 | 只跑先前沒過的、改動碰到的、新加的 | 每回合 2.6 秒、每 M0 場 15 秒 × 實際場數；每回合約 US$0.0024 |

## 8. 停點、回復、待業主

- 停點：寫錯資料或資安（DSP-115 第 3 點）⇒ 停；E4 程式誤轉人或誤收尾 ≥1 ⇒ 停、交業主；E6 或 E13 低於改前且根因在本片 ⇒ 停；同一阻擋發現修 5 輪仍未過 ⇒ `PAUSED_VERIFICATION`。
- 回復：開關 off（E8）；改動前檔案備份 `~/jgb-archive/arch-step3-20261018/e/baseline/`（SHA256SUMS）；不 commit、不 push。
- 用量：收案報告寫子代理 token 加總與 Bedrock 費用（`usage_events.est_cost_usd`）。
- **核可時請業主裁（擋核可）**：
  - **Q-B 預期 0 與 E2a 未量**：本片在目標正本量法上預期全為 0（§0），使用者價值由 E1～E4 量；E2a 現值核可前未量，X1 在改前程式量（同 M0 的處理）。選項：(a) 同意兩者、續做 E（建議）；(b) 先在核可前量 E2a（約 4 分）再核可；(c) 不同意預期 0：改題或停線。
  - **Q-E4 E2a 廣度偏離**：E2a 每組 1 筆資料、實作方寫的固定腳本，不符「驗收廣度」第 3、4 條。選項：(a) 照原樣跑，只當不退步證據、不宣稱廣度或成效（同業主 2026-10-21 對 OV Q4 的裁示；建議）；(b) 另擴充到下限（需另立題組，另估用量）。
- **待業主（不擋核可，未答照預設做）**：
  - **Q-E1** 樣板文字：「好的，幫您轉真人客服，請點下方的『找真人』。」／「不客氣，有需要再找我。」——我先這樣定了，要改請說。
  - **Q-E2** 受眾：harness 只有 b2b property_manager，租客等受眾未量（W2 C7 同一題）。

## 9. 後補清單（DSP-115）

- 本片起草時所見：無新增（W2 後補清單見 `~/jgb-archive/arch-step3-20261018/w2/report-w2-close.md` §4，其中第 9 項 `user_request` 由本片處理）。
- 量測中所見（改前就有、不在本片規則內；收案報告逐條附證據）：物件名稱被截短（E3 草稿、E13 RS 組）；候選清單未選時道謝那句被丟；單筆候選清單固定腳本未按（E13 D 組，F12 既有）；修繕分類沒問就歸「其他」；插問未答；追問欄位中、未被標為已解決或要真人的非答覆句（例：轉述客服的話）仍被整句填入欄位（E4 填欄中組，改前同樣）；`write_forms` 寫入意圖函式的 `dialog_act` 參數 r5 後已無呼叫端。
- 收案時所見（§6 第 12 點業主裁後補）：E4 候選清單情境半句「上次真人客服說退租的話要」AI 標籤誤標要真人、程式轉人 1/48（`e/after8/E4`；修正 5 為 2/48、修正 6 為 0/48）。

## 10. 審查紀錄

r1 plan-verifier（2026-10-26）回 REVISE 10 條，皆經主會話對碼後處置為 FIX：

| # | 發現 | 對碼 | 處置（r2） |
|---|---|---|---|
| 1 | `HandoffReason` 加值會進主模型 schema 與工具 enum，模型可自報 `user_request` 繞過降級；E8 逐位元組不成立 | 成立：`_agent_output_response_format` enum 取 `HandoffReason` 全值、`tools/handoff.py` `HANDOFF_REASONS` 同 | §4.1-2 值域隔離；E-R4、E-R10、E4、E7、E8 改寫；§3 改實際值域 |
| 2 | 上位驗收方式漏 E2a；「不動寫入路徑」與改 schema 矛盾 | 成立：目標正本 §1「既有回歸題組不低於前一基線」；OV-R3 讀法含 E2a 六組 | 加 E13、終點表 E2a 列、X1／X4 含 E2a；§4.2 如實寫寫入路徑受影響 |
| 3 | E6「−1 容差」、E10「＝基準」比目標正本寬 | 成立 | 改回字面判（E-R12），未達照實報（同選對紀錄片 PV2-3 處置） |
| 4 | 預期 0 沒有業主明示同意 | 成立 | §8 Q-B |
| 5 | 前兩片不照定義挑 | 成立；重算後前兩片為 F12 與指令式片（審查員列的選對紀錄片早於兩者），且 E2a 有上下、被判變異，斷路器讀法有歧義 | §0 依定義重寫、附斷路器報告，交業主裁（Q-B） |
| 6 | E4 只用身分、E1 漏候選清單情境 | 成立 | E1、E4 皆 6／6 情境 |
| 7 | 測試選擇缺每場時間來源 | 成立 | §7 每列附來源 |
| 8 | Zendesk BSAT 引文截斷、不支持「收尾句是系統回覆」 | 成立：原文為「…to collect feedback from a customer about their experience」 | §2 完整引用並如實描述；轉人句改引 Escalation reply；收尾句標「第一原理、查無業界對應」 |
| 9 | 後備路徑的偏離沒登記 | 成立 | KD-5 (3)、E11、§4.3 |
| 10 | E10 無規則 ID；O4 兩句無規則 | 成立 | 加 E-R11、E-R12 |
| 待查 | 程式優先入口在 `wd is None`／`frozen`／`triggered`／敏感時不等待 | 成立：`_write_draft_program_first` 開頭三個 return | §4.1-3 改為三個決定點：(b) 競速涵蓋這些回合；E4 量延遲 |

r2 plan-verifier（2026-10-26）回 REVISE 5 條（第 2 次自動 REVISE；下一次為唯一的收尾審查），主會話對碼後全部 FIX：

| # | 發現 | 對碼 | 處置（r3） |
|---|---|---|---|
| B1 | 主輸出路徑沒有值域隔離：`parse_handoff_reason` 會判 `user_request` 合法、主輸出也不經它；verifier 放寬讓 off 行為改變 | 成立：`return HandoffReason(value)`；`"reason": out.handoff_reason or "no_grounding"`；`verifier.py` `if out.handoff_reason not in {r.value for r in HandoffReason}` | §4.1-2 改為主輸出決定性檢查（on 才加、off 同改前）、verifier 用模型可見子集、程式轉人以來源標記辨識；E-R4、E7、E8 同步 |
| B2 | 前兩片不符定義：F12、指令式片點名的目標文件是 F12 計畫 | 成立：`plan-post-pick-commands-20261024.md`、`f12/report-f12-close.md` 終點指標句 | §0 改為選對紀錄片（−1）、OV（+16）；斷路器不觸發；刪掉 r2 的斷路器報告與讀法題 |
| B3 | E2a 未量沒有業主接受 | 成立：§6 第 4 題只問 M0 | 併入 §8 Q-B |
| B4 | E3 漏「寫入填欄中」 | 成立 | E3 改 4／4 情境、0/20；§7 場數同步 |
| B5 | E-R3 放寬「未決卡」沒註明 | 成立 | 讀法欄註明 |
| P3 | X2 判準會被已知變異觸發；§6 第 4 題文字與事實不符；E1、E2 沒查 `outcome.state`；(b) 取消要和 `budget_exhausted` 分流 | 成立 | X2 判準改 < 40/52；§6 第 4 題加更正；E1、E2 加 `outcome.state`；§4.1-3 (b) 寫明分流、E7 測 |

r3 收尾審查（fresh plan-verifier，2026-10-26）回 **READY**（本 session transcript 第 2182 行，該代理回報全文為「READY」）；業主隨後核可（§6 第 5～7 點）。
