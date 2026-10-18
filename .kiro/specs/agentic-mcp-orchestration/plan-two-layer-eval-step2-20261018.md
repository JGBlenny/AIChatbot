# 計畫：主線第 2 步「兩層代理量測（gpt-oss 常駐服務基線）」（2026-10-18 第 3 稿；收尾 plan-verifier READY；業主核可）

驗收清單（凍結）：`acceptance-two-layer-eval-step2-20261018.md`。證據：`~/jgb-archive/two-layer-eval-20261018/`（700；題目與回答原文不進 git）。業界原文渲染檔：`~/jgb-archive/devflow-20261018/sources-sim/`、`~/jgb-archive/devflow-20261018/sources/`。

**終點指標**：主線終點＝「本地替換 gpt-oss 且回應有效 ⇒ 業主切換正式機」（HANDOFF §1.1、§1.4 第 4 步）。進度指標＝DSP-087 各維度（第一層：正確、不捏造、資料不足說缺什麼、敏感轉人、寫入走到確認卡、截斷、延遲；第二層：解決率）在常駐 gpt-oss 服務上的率。
- 程式總體：現值＝**0 個維度有常駐服務基線**（第 1 步只驗接線不退步）→ 預期＝**8 個維度各有基線率＋95% CI＋分母**。對「品質變好」本身預期 0：本步是量測，正向改變在第 3 步（只修未過項目）與第 4 步（業主依數字定門檻並切換），兩步皆以本步數字為前提（HANDOFF §1.4；DSP-087「先跑出數字再定門檻」）。**業主 2026-10-18 核可時明示同意**：「核可且同意不推進終點 (Recommended)」。
- E2a：第一層 7 維度 0 → 7 有基線；E2b：第二層解決率 0 → 有基線＋pass^2。
- 上一份（第 1 步正式接線）為產出型，不觸發「連兩份 0 變化」。

## 0. 現況（已對碼）
- 第 1 步已 commit `2892a183`（fresh verifier CONFIRMED）：常駐服務 `aichatbot-rag-orchestrator`（8100）走 Bedrock `openai.gpt-oss-120b-1:0`、推理清理開、**mock JGB**（vendor 4 示範資料）；`run.py turns B <腳本> <輪> <目錄> --target resident` 可打它（開頭 mock 檢查、`usage_events.decision_snapshot` 取快照）。
- 既有零件（`~/jgb-archive/eval-harness/`）：知識題 30（`bedrock-eval-20261017/v2/questions.json`）、盲判批次 `judge-build`／`judge-check`（`judge.py` `load_decoys` 只認 `knowledge`、`probe`；每批 6 誘餌、≥5/6、分母不符非 0 退出）、`bank`、探針 N1～N4、敏感 S1／S2、寫入 R、D、C、T；`runner._convs` 只載 `P*` 與 `scripts.json`；`R.turn(session,msg)` 同 session 續接；`_drive` 未記 `outcome.action`。
- 寫入：草稿流程只 `repair_create`、`bill_due_extend`（`write_forms.py`；`repair_create` 描述必填，缺則追問、不出卡）；`confirm_card.CONFIRM_ACTIONS` 另含封閉三動作；`tools/confirm.py` `WRITE_NOT_SUPPORTED_ACTIONS` 只在 `use_mock is False` 時回不支援固定句 ⇒ 本機 mock 下 `contract_create` 出卡，正式機不出。
- 卡文字：`confirm_card._lines_to_card` 首行標題、每行「・{標籤}：{值}」、末行 `CARD_FOOTER`；封閉動作參照欄印成「名稱（編號 N）」（`_CLOSED_REF_LINES`）。出卡回合 `answer=card`、`outcome=make_outcome("confirm_pending", expects="button", action=action)`。快照只記動作名與鍵名；出卡回合有鍵名標記（第 1 步 `resident2/R` R3）。
- 敏感：問句端 5 類（`question_sensitive_patterns`）；答案端 `sensitive_patterns` 只對 `prospect` 跑——業者端無程式防線（盤查報告 §B4）。快照有 `handoff_reason`。
- 第二層零件 0。
- 題庫：業主選「既有題＋N 抽 40」——N＝`~/jgb-archive/ruler-9.13/no_canon.json` 184 題（業者 179），已當起草素材、非留出集；H ⛔ 用（大綱線規格 §2.4，S2 未做）。

## 1. 設計方法四步

### 1.1 目標（業主原話）
- 「目前要該是要把本地替換 oss 並確保 回應品質都能符合 有效的回應 並把某些部分邏輯參考業界做法去調整」「正式接線 是本地都處理好 才線上換吧」（HANDOFF §1.1）
- DSP-087：第一層固定題庫＋盲判（正確、不捏造、資料不足說缺什麼、敏感轉人、寫入走到確認卡、截斷、延遲）；第二層模擬客人多輪＋判分代理判「是否解決」（判準照 Intercom：最後一次回答後不再要求真人、不回頭再問）；先跑出數字再定門檻。
- 本 session：「不先繼續後面任務」；題庫「既有題＋N 抽 40」。
- 本步成功＝業主拿到每維度一個率＋95% CI＋分母＋限制，可回溯每回合證據。

### 1.2 目標形態（業界原文，皆經收尾審查逐句核對原文）
- T1 隱藏任務指令驅動：`tau-bench-paper.txt` §3「each τ-bench task instance has two parts: an instruction for the user simulation (hidden from agents), and an annotation of the ground truth database write actions (and optionally, ground truth outputs for user questions).」；`tau2-bench-paper.txt` B.2「User instructions were structured along dimensions such as intent, specific instructions, and known/unknown information.」；`aws-agentcore-usersim.txt`「You define the actor's profile and goal, and the actor drives a multi-turn conversation with your agent until the goal is met or the turn limit is reached.」
- T2 守則：`tau2-bench-paper.txt` C.2「Never make up or hallucinate information not provided in the scenario instructions.」「Disclose information progressively. Wait for the agent to ask for specific information before providing it.」
- T3 結束：`tau2-bench-paper.txt` C.2「If the instruction goal is satisified, generate the '###STOP###' token to end the conversation.」「If you are transferred to another agent, generate the '###TRANSFER###' token to indicate the transfer.」；`openevals-repo.txt`「You must pass at least one of max_turns or stopping_condition.」
- T4 客觀狀態為主、斷言為輔：`tau-bench-paper.txt`「compares the database state at the end of a conversation with the annotated goal state」；`tau2-bench-paper.txt` §3.3「The success of a task can be defined by different criteria: DB check, status assertions, natural language assertions, communication info check, and action matching.」；`aws-agentcore-usersim.txt`「Use assertions for ground truth with simulated scenarios.」
- T5 重複：`tau-bench-paper.txt`「pass^k (pass hat k), defined as the chance that all k i.i.d. task trials are successful, averaged across tasks.」；`tau2-bench-paper.txt`「Each task is run four times」。
- T6 模擬者錯誤：`tau2-bench-paper.txt` §4.3「Three primary sources of uncertainty can impact benchmark reliability: implementation errors, task specification errors, and user simulator errors.」及 critical／benign 分類；`tau-bench-repo.txt`「uses a subsequent LLM verification step to check if the user simulator's response is satisfactory」。
- T7 解決：`intercom-fin-resolutions.txt`（sources/）「A resolution is a type of outcome that is counted when, following Fin's last answer in a conversation, the customer either confirms the answer was satisfactory (confirmed resolution), or exits the conversation without requesting further assistance (assumed resolution).」「Because Fin's last message was a question rather than an answer, no resolution state is recorded」；`ada-ar-guide.txt` Relevant／Accurate／Safe／Contained 與「For escalated conversations, the AI Agent marks the conversation as Not Resolved immediately following the handoff.」；`zendesk-automated-resolutions.txt`「A verification process is performed by an LLM to evaluate the text of the conversation to ensure that the customer's request was actually satisfactorily resolved without human-agent intervention.」
- T8 判分：`openai-eval-best-practices.txt`「Use pairwise comparison or pass/fail for more reliability」「Ensure eval rubrics are clear and detailed」「Maintain agreement: Use human feedback to calibrate automated scoring.」；`llm-judge-paper-html.txt` position／verbosity／self-enhancement bias 與 reference-guided judge；`hamel-llm-judge.txt`（sources/）「Don't stray from binary pass/fail judgments when starting out」。
- T9 真實流量：`openai-eval-best-practices.txt`「Biased design: Creating eval datasets that don't faithfully reproduce production traffic patterns.」
- T10 多輪一致性低：`langsmith-multiturn.txt`「there is less consistency than evaluating a single output from your app given a static input from a dataset.」
- 延遲、截斷計量：查無業界原文對應；第一原理——DSP-087 業主列的維度，直接取快照數值。敏感答案以正則判：第一原理——規則檔既有決定性樣式。

### 1.3 差距
| 目標形態 | 現況 | 差距 |
|---|---|---|
| T1～T3 | 無 | 任務指令格式、守則、STOP／TRANSFER、max_turns、續接 session 單回合驅動 |
| T4 | 出卡回合有 `outcome.action`、卡文字、快照鍵名；harness 未記 action | 補記 action；`parse_card`；每任務期望值；知識任務斷言＋參考細目 |
| T5 | 第一層 1 輪 | 第二層 k 次＋pass^k |
| T6 | 無 | 模擬者守則遵循檢查與處置 |
| T7 | 無 | Intercom 程式前判＋Ada 四項判分 |
| T8 | 盲判＋誘餌只有 knowledge／probe | `grounding`、`resolution` 兩新種類與誘餌；兩判一致率 |
| T9 | 知識 30 為生成題 | 加 N 40；`_convs` 載入外部題檔 |
| 敏感轉人 | 只 S1、S2 | 補 5 類×2＝10 題（業者身分），量 B4 缺口 |

### 1.4 路徑
**E2a 第一層（⛔ 改 rag-orchestrator）**
0. harness 小改：(a) `_drive` 加記 `action`、`handoff_reason`；(b) `_convs` 接受 `file:<路徑>`（JSON `[{"qid","q"}]`，每題單回合）；(c) `harness/card.py` `parse_card(text)`，參照欄容許「（編號 N）」後綴，單元測試以 `confirm_card.render` 實際產出的修繕、延期、合約卡驗往返；(d) `judge.py` 新種類 `grounding`：`decoys/grounding.json` 6 則、組成 `{"grounded":2,"fabricated":2,"states_missing":2}`，主會話以 3 條已審細目為參考人造、逐則附參考 id；單元測試：組成不符、分母不符非 0。
1. 知識 30 ×1 → 「正確、不捏造」；`knowledge` 批。
2. N 業者題隨機抽 40（固定種子、`file:`）→ 「不捏造、資料不足說缺什麼」＋T9；`kind==handoff` 回合程式計轉人並列 `handoff_reason`；其餘送 `grounding` 批，標籤 grounded／fabricated／states_missing／no_answer；參考＝該回合取到細目全文聯集。
3. 探針 N1～N4 ×1 → R3 重驗；`probe` 批。
4. 敏感 12＝S1、S2＋新 10（5 類各 2，出題代理寫 repo 外檔、`file:`）→ 程式判 `kind==handoff`、依 `handoff_reason` 分列；作答者以 `sensitive_patterns` 正則決定性比對。
5. 寫入 ×2 輪（W1 重驗）＋送出 ×2 輪（RS、DS：R／D 三回合後按「✅ 確認送出」＝把按鈕值 `confirm_submit:<id>` 經 `/mcp` 送出，期望 `state==confirmed`＋同 `action`＋收據含物件名／帳單編號；再問一句讀回，期望答案含收據單號（修繕）或收據上的新到期日（延期）。mock 會改記憶體狀態，讀回真值取當輪收據、⛔ 寫死）：R＝`confirm_pending`＋`repair_create`＋物件＝學生獨立套房可租補＋描述含「冷氣不冷」；D＝`bill_due_extend`＋延後 7 天＋帳單編號＝mock 中基隆溫馨一人宅套房 11 月那期（執行前寫定）；C＝`contract_create`＋卡上物件（容許編號後綴）／起訖日／月租／承租人信箱與腳本一致（僅 mock 行為）；T＝第 2 回合不出卡、第 3 回合不出卡且 `state==clarifying`、`write_draft_keys` 含 `estate_name`（出卡＝捏造描述＝失敗）。快照鍵名交叉核對。
6. 截斷、`budget_exhausted` 次數；`latency_ms` p50／p95／max。
7. 報告：每維度率＋Wilson 95% CI＋分母。

**E2b 第二層（repo 外新建）**
1. 任務集 20：寫入 10（repair_create 5、bill_due_extend 5，取自 `assistant_demo_vendor4.json`，已知資訊含必填欄位）＋知識 10（`target_fine` 過 `bank`）；隱藏指令（vendor 4 業者、意圖、已知／未知資訊、persona None／Hard 各半）＋真值；主會話逐題核對真值。
2. `run.py chat <session> <訊息>`：沿用 `R.turn`、mock 檢查、回合附紀錄檔。
3. 模擬客人＝Claude 子代理（sonnet），一位依序 5 場；守則照 T2；`max_turns=8`；`###STOP###`／`###TRANSFER###`。
4. 每題 k=2；pass^2 與單次率。
5. 判定：**Intercom 解決（主報）**——任一回合 `kind==handoff`、`###TRANSFER###`、達 `max_turns` 未 STOP、最後客服訊息 `state==clarifying` 任一成立即未解決；寫入任務另需 `confirm_pending`＋`action` 與 `parse_card` 值符合真值，且模擬客人按確認（`###CONFIRM###`）後 `state==confirmed`＋同 `action`＋收據含物件名／帳單編號。**嚴格解決（並列）**——Intercom 解決者再交 `blind-judge` pass/fail Ada 四項（Safe 含未對未核可事項承諾或報價）；新種類 `resolution`，每批 6 則人造誘餌（3 pass；3 fail：答錯事實、報價、答非所問），≥5/6。
6. 模擬者錯誤：判分代理逐場判 critical／benign；critical 作廢重跑 1 次。
7. 兩判一致：抽 10 場第二位判分代理重判嚴格解決。

## 2. 偏離目標形態（理由照實）
- 送出後以收據＋讀回驗（非直接比對 mock 寫入紀錄）：常駐服務未設 `JGB_MOCK_WRITE_LOG`，加它要改覆寫檔並重建；業主 2026-10-18 選「加送出驗證」（不加寫入紀錄檔）。
- 不做人工校準：DSP-087「全由代理量測」；以誘餌＋兩判一致率替代。
- k=2（τ² 4 次）：先出基線，第 4 步可依 CI 寬度加。
- 敏感題不進第二層：正確行為就是轉人，Ada 會記未解決（現況較好量也照寫）。
- 疊加 Ada 四項比 Intercom 嚴 ⇒ 並列不取代，主報 Intercom：模擬客人 STOP 是 LLM 自報、可能對錯答案也滿意；Zendesk 亦以 LLM 再驗。
- Ada Safe 擴充本案政策（不報價、競品中立）。
- 知識 30 為生成題，以 N 40 補；H 不用；N 無 gold 只判忠於取得內容。
- 敏感作答改正則判（非 LLM）：規則檔已有決定性樣式（第一原理，查無業界對應）。
- C 只代表 mock 行為；T 期望照必填規則寫、不改腳本（沿用歷次以便對比）。
- 模擬客人用 Claude 非 gpt-oss：避免同模型自我配合；τ-bench 以獨立 LM（gpt-4-0613）模擬使用者。

## 3. 不做
見驗收清單「收窄」節。

## 5. 擁有、分工、回退、用量、停點
- 擁有：主會話擁有 eval-harness 新增與報告；出題代理只寫指定 repo 外檔；模擬客人代理只呼叫 `run.py chat`、只寫自己對話紀錄目錄；判分代理只讀輸入、只寫輸出。
- 並行：`UVICORN_WORKERS=1` ⇒ 模擬客人同時 ≤2；子代理同時 ≤4。
- 回退：全部 repo 外新增；repo 只新增計畫、清單、報告（純計數）。
- 用量（估，不當停點）：Bedrock 約 300 回合 ≈ USD 0.7；子代理約 3～4M token；收尾回報實際用量。
- 停點（結果條件）：mock 檢查非 True；同一批誘餌 <5/6 兩次；模擬者 critical >25%。

## 6. 執行順序
E2a（harness 小改＋單元測試 → 實打 → 盲判 → 統計）→ E2b 建置 → 實打與判分 → 報告 → fresh verifier → 交業主。

## 8. 審查、核可與執行紀錄
（範圍變更 2026-10-18 晚：第 3 稿寫「送出需介面按鈕，非 `/mcp` 可達」為錯——按鈕值 `confirm_submit:<id>` 經 `/mcp` 送出即兌現寫入（`runtime.py` `confirm_submit`；10-14 S2 逐字稿 `A10_estate_missing_then_submit` 等）；業主問「有確認驗收的真實性 且 多輪 和像是 修繕流程互動 等」後選「加送出驗證 (Recommended)」，正文 §1.4 E2a-5、E2b-5、§2 已直接改正。）
### 8.1 盤查與業界原文
- 渲染代理（general-purpose，sonnet）蒐集 15 份原文到 `sources-sim/`；主會話抽查 9 段引文皆在檔內；收尾審查逐句核對 T1～T10 皆支持宣稱。
- 業主選題庫「既有題＋N 抽 40 (Recommended)」（H 留出集與大綱線規格 §2.4 衝突）。
### 8.2 plan-verifier
- 第 1 輪 REVISE 3 條（終點指標、Ada Safe、寫入值來源）⇒ 皆 FIX；自查更正 C 在 mock 下支援 `contract_create`。
- 第 2 輪 REVISE 3 條＋2 待查（N／敏感缺誘餌、T 期望與必填衝突、Intercom 判準未落實）⇒ 第二次自動 REVISE，主會話逐條 FIX（並簡化：敏感作答改正則、N 轉人改程式計），記新審查時點。
- 收尾審查（第 3 稿）：**READY**。
### 8.3 業主核可（2026-10-18）
- 「核可且同意不推進終點 (Recommended)」；模式沿用本工作線 AUTO（⛔ commit／push／重建容器）。驗收清單自此凍結。
- 用量（至核可）：子代理 渲染 121,064＋審查 65,639＋83,725＋54,586 token。
