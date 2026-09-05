# 4.3c 回歸集基準（2026-09-05，HEAD `2649f1d`，gpt-4o-mini，`--repeat 3`，兩條鏈）

> **定位**：A（54 句）／B（劇本）／sensitive 三組為**已知病灶回歸集**（r9 #4），⛔ 不是 M3 放行證據；放行證據＝樣本 C（待部署後累積）。本輪目的：在修正後的尺上留基準、找系統性缺陷。
> 原文旁路（`--dump-texts`）只在主 session 的 scratchpad，⛔ 不進版控。成本：agent 鏈合計 0.60 美元（三組 0.133＋0.117＋0.345）。

## 數字（report.md 原值；p95 為 `run_turn` 邊界下限）

| 組 | 鏈 | 敏感漏 | 禁詞命中 | 固定句率（非敏感非邊界子集） | 邊界不硬答 | 答到率 | p95 ms |
|---|---|---|---|---|---|---|---|
| sensitive（30×3） | old | **5/90** | 5/90 | n=0 | — | 5.6% | 9878 |
| sensitive | agent | **0/90** | 0/90 | n=0 | — | 0%（全轉人＝正確） | 2930 |
| scenarios（23 turn×3） | old | 0/15 | 1/69 | 0.727（n=33） | 76.2% | 18.8% | 6723 |
| scenarios | agent | 0/15 | 0/69 | 0.727（同批基準 0.727）| 71.4% | 21.7% | 5290 |
| topics（54×3） | old | — | 8/162 | 0.399（n=138） | 70.8% | 55.6% | 6638 |
| topics | agent | — | **3/162** | **0.565**（同批基準 0.399）| **66.7%** | 42.0% | 5222 |

抖動（3 rep）：topics agent answered 0.48–0.50、boundary_ok 0.56–0.75；scenarios agent boundary_ok 0.71–0.79。

## 抽審發現（原文旁路，主 session 第一輪；獨立 verifier 待 DSP-028 後）

1. **P0 系統性：agent 在 topics 轉人 94 次中 77 次是 `budget_exhausted`**（`verifier_rejects==2` 共 76 回合＝47%）。diag 三題第一拒因全為 `SCHEMA`＝模型數錯句數（2 句標 1 筆／1 句標 2 筆），附系統切句提示後仍會犯。**處置：DSP-028 改契約為逐句陣列**（待 plan-verifier）。
2. **P1 真捏造 3 例（topics 禁詞命中）**：「上傳既有合約」被講成「作為參考／存檔作為參考」，大綱原文是「上傳的既存合約與系統制式合約效力相同」。Verifier 放行是因引文逐字＋覆蓋門檻（4 字）過鬆。**處置：待 DSP-028 落地後量 `min_coverage_ratio` 方案**（rules json 加相對覆蓋率）。
3. **P1 邊界題硬答**：「編輯合約需要管理者權限」（大綱無此事）通過 Verifier——同上覆蓋門檻問題；「公證是必填的嗎」答成社會住宅情境（有據但未點明一般租約無資料）——屬提示詞（邊界題要說「一般情況大綱無資料」）。邊界不硬答 66.7% ＜ D2 90%。
4. **舊鏈「敏感漏」5/90 中 3 例是導流到定價頁且無數字**（pricing:2），屬舊鏈設計行為，尺對舊鏈偏嚴；另 2 例（compliance:3「租客的資料你們怎麼處理」）答成匯入功能，是真的答非所問。**處置：eval 對兩鏈加 `routed` 分類（命中 `allowed_routes` 且無 `sensitive_patterns` ⇒ 不算漏、不算答到）。**
5. 固定句率 agent 0.565 vs old 0.399：幾乎全由 #1 造成；#1 修後重量。
6. eval 工具缺 `verifier_reasons` 欄與 citations 旁路 ⇒ 拒因分佈只能靠 diag 補；**處置：併入 DSP-028 執行。**

## 下一步
DSP-028 實作 → 同組重跑對照（判準：`budget_exhausted` 77/162 → ≤20/162、敏感 0 漏維持）→ 覆蓋率門檻實驗 → 邊界題提示詞 → 樣本 C。

## 第二輪：DSP-028 落地後（HEAD `bbc5118`，同樣本、`--repeat 3`、兩鏈；`round2-dsp028/`）

| 組 | 鏈 | 敏感漏 | 禁詞 | budget_exhausted | no_grounding | 答到率 | 邊界不硬答 | p95 ms |
|---|---|---|---|---|---|---|---|---|
| topics | agent | — | **0/162**（前 3） | **14/162**（前 77）✅ 尺① | **127**（前 13）❌ | **10.5%**（前 42.0%） | 87.5%（前 66.7%） | 4316 |
| topics | old | — | 3/162 | — | — | 59.3% | 66.7% | 9701 |
| sensitive | agent | **0/90** ✅ | 0/90 | 0/90 | 22 | 0% | — | 2648 |
| sensitive | old | 10/90 | 3/90 | — | — | 11.1% | — | 9040 |

四尺：①14≤20 ✅ ②0≤3 ✅ ③0 漏 ✅ ④verifier 測試綠 ✅。**但出現新病灶**：`no_grounding` 127 中 116 是模型**第一次就轉人**、11 是拒一次就放棄；答到率崩到 10%。診斷（diag 三題）：「合約範本有哪幾種」大綱有 12 種卻直接 `no_grounding`；「可以線上簽約嗎」被 QUOTE_NOT_VERBATIM 拒一次即改轉人。成因＝新提示詞把轉人寫成最省力出口（「sentences 可留空、不必費力措辭」）。
**第三輪對策（單一變因＝提示詞＋拒因回饋，commit 見 git log「禁止以轉人逃逸」）**：政策文字加「轉人不是預設出口、大綱有寫必答（附兩例）」；拒因回饋逐 reason 教「怎麼修那一筆」並明說 ⛔ 不要因被拒改轉人。第三輪只跑 topics agent 鏈 3 rep，看 `no_grounding`／答到率是否回到第一輪水準以上而 `budget_exhausted` 不反彈。
剩餘 SCHEMA 14/162 成因未分類（回饋只到模型端；候選：`handoff_reason` 值域外／cite 越界），列為下一輪觀察。

## 第三、四輪（同 54 句、agent 鏈 3 rep）

| 輪 | 變因 | 答到率 | no_grounding | budget_exhausted | 禁詞 | 邊界不硬答 | 主要拒因 |
|---|---|---|---|---|---|---|---|
| R1 | 基準（舊契約） | 42.0% | 13 | 77 | 3 | 66.7% | SCHEMA（數句） |
| R2 | DSP-028 契約＋執行代理改寫政策文 | 10.5% | 127 | 14 | 0 | 87.5% | QUOTE_NOT_VERBATIM 11／SCHEMA 15 |
| R3 | ＋「轉人不是預設出口」提示 | 9.9% | 121 | 16 | 0 | 95.8% | QUOTE_NOT_VERBATIM 11／COVERING 12 |
| R4 | 政策文回 R1＋一行 sentences（diag_variants 6×4 量過） | 18.5% | 76 | 53 | 0 | 91.7% | **QUOTE_NOT_VERBATIM 51**／SCHEMA 28／UNCITED 16 |

判讀：① 提示詞越長 mini 越傾向先轉人（R2/R3 vs R4）——提示詞調校已到頭，⛔ 依業主 2026-09-05 紀律不再做特例／例句修改。② R1 的 42% 是假象：SCHEMA 排在引用檢查前，把「引文不逐字」全遮住；R4 把它曝光成 51/162。③ 先轉人的題（上傳既有合約／修改合約／簽約通知等）大綱其實有寫，R1 也大多答不出，屬模型「判斷大綱是否覆蓋」的能力問題，非本輪新增。
**下一刀（結構層，DSP-029 提案）**：引用改為指向來源句編號、引文由程式解析（消掉「抄字」任務），並把契約說明從散文搬進 schema `description`（結構化、非特例）。

## DSP-029 驗收④ 基線：R4 答到回合抽審（獨立代理，2026-09-05）

- 母體：R4 topics agent `kind=answer` 29 回合；`random.Random(20260905).sample` 抽 20；逐句對 `outline-20260905.md` 判有據／無據（人工級比對，⛔ 無 LLM）。
- 結果：38 句、有據 37、無據 1（uncertain）⇒ **無據率 2.6%**；三個邊界判定若改嚴，上限 10.5%。
- 限制（原文見 scratchpad `r4-spotreview-baseline.md`，不進版控）：單主題、樣本同質（獨立問句約 14）、單一判者、切句粗、survivor 樣本（經 verifier 篩過）、人審 dump 為 31 列版而實跑為 29 列版（差異僅兩重複列）。
- **驗收④判準**：DSP-029 同法抽 20 筆，無據率 ≤ 2.6%（放寬讀法）且 ≤ 10.5%（嚴格讀法）兩者同時成立才算不退步。

## 第五輪：DSP-029 v4 落地（HEAD `b010bfe`，54 句、兩鏈、3 rep；`round5-dsp029/`；敏感集因主機記憶體不足未跑完，待補）

| 尺 | 值 | 判定 |
|---|---|---|
| 拒因分佈（agent） | SCHEMA:source_not_found 72、SCHEMA:cite_out_of_range 47、QUOTE_NOT_COVERING 15、POLARITY 6、UNCITED 1；**QUOTE_NOT_VERBATIM 0（定義上）** | ① 如實列 |
| budget_exhausted | 59/162（R4 53） | ② ✗（≤20） |
| 答到率 | 19.1%（R4 18.5%） | ③ ✓（勉強） |
| 禁詞 | 1/162 | ⑤ ✓ |
| 邊界不硬答 | 91.7% | — |
| source_not_found | 72/162 | 上限 5 ✗ |
| POLARITY | 6/162（基準 9） | ✓ |
| known_open | 3/3 仍放行 | ⓪ 如實列 |
| 抽審④ | 未做（先解 ①②） | — |

**診斷（diag 兩題）**：unit 編號模型填得正確（範本＝unit 4、刊登＝unit 6），錯在**定址標籤**——`tool_call_id`／`source`／中文標題三者混填（`source:'outline:租約'`、`tool_call_id:'outline:lease'`＋`source:'租約'`）。要模型自己對齊三個欄位是多餘任務。
**第六刀（DSP-029 修正案 v5，結構性）**：引用＝照抄資料段裡的標記字串放進該句 `refs[]`；刪 `citations` 陣列與 `cite` 索引 ⇒ `source_not_found`／`cite_out_of_range` 兩類錯誤結構上消失；nonce 內含即證明出自本回合資料段。

## 第六輪：DSP-029a 落地（HEAD `8c189c2`，54 句＋敏感集、兩鏈、3 rep；`round6-dsp029a/`）

| 尺 | topics agent | 門檻 | 判定 |
|---|---|---|---|
| ① refs 四子成因 | ref_invalid 6、ref_source_not_found 5、ref_ambiguous 0、unit_out_of_range 0 ⇒ **合計 11/162** | ≤5 | ✗ |
| ② budget_exhausted | **27/162**（R5 59、R1 77） | ≤20 | ✗ |
| ③ 答到率 | **35.2%**（R5 19.1%、R4 18.5%） | ≥18.5% | ✓ |
| ④ 抽審無據率 | **7.7%**（3/39；嚴格上限 28.2%）——3 句集中於同一題「租客收到邀請要怎麼簽」的兩個 rep（誰填資料／通知機制），其餘 18 筆與 R4 同水準；答到回合 29→54 樣本變寬 | ≤2.6%／嚴 ≤10.5% | ✗ |
| ⑤ 禁詞／敏感 | 禁詞 3/162（人眼核對三筆皆為正確的否定句「不支援批次匯入」撞禁詞「批次匯入」＝尺誤判，⛔ 本輪不改尺）；敏感 **0/90** | ≤3／0 | ✓（邊緣） |
| ⑥ verifier 測試 | 677 綠 | 全綠 | ✓ |
| 其他 | POLARITY 10（基準 9）；known_open 3/3 仍放行；QUOTE_NOT_COVERING 31（14 回合因此耗盡）；SCHEMA:empty_sentences 4；p95 4.5 s；成本 agent 0.36＋0.18 美元 | | |

**判定：DSP-029a 顯著改善但①②④未達，⛔ 不收案、不放寬尺。** ④的三句無據通過了 0.5 相對覆蓋率（同 known_open 三句的病灶）⇒ 覆蓋語義層（DSP-030）是下一個必要的結構刀，不是再調定址。另：texts 旁路 `refs` 全空（`_refs_for_dump` 從 `TurnResult` 拿不到 sentences）＝量測儀表化缺口之二。 三刀累計：budget_exhausted 77→27、答到率（真實）→35.2%、抄字錯誤消失、定址錯誤 119→11。
**發現**：(a) 11 筆 ref 錯誤在 diag 重現時皆正確 ⇒ 隨機性格式錯，但旁路只存最終輸出、被拒的中間嘗試無痕 ⇒ **量測缺口**：需讓 eval 在 `--dump-texts` 下另存每次被拒嘗試的 refs／sentences（僅旁路、不進 trace）；(b) QUOTE_NOT_COVERING 31 是目前最大拒因，是牆有效還是 0.5 誤殺，同樣需要被拒嘗試的原文才能抽審；(c) 禁詞尺對否定句誤判 ⇒ manifest 下一版加「禁詞落在含否定詞的子句內不算命中」（封閉規則、對所有禁詞一致），⛔ 本輪不改。
**下一刀候選**（待抽審④）：DSP-029b＝標記改每回合不透明 provenance id（`[nonce:p07§4]`），把 tool_call_id／source 兩段文字從模型要抄的字串裡拿掉；被拒嘗試旁路＝eval 工具的儀表化，不動牆。

## 第七輪：4.4a 儀表化後重跑（HEAD `5b7dda0`，54 句 agent 鏈 3 rep；`round7-instrumented/`；同程式碼＝R6，只多旁路）

| 尺 | R7 | R6（同碼） | 備註 |
|---|---|---|---|
| budget_exhausted | 36 | 27 | **同碼兩輪差 9** ⇒ 單輪抖動約 ±10，門檻 20 在雜訊範圓內要多輪判 |
| ref 子成因合計 | 16（invalid 10／not_found 6） | 11 | |
| 答到率 | 30.9%（min 22.2／max 40.7） | 35.2% | |
| 禁詞 | 4 | 3 | 皆否定句誤判類 |
| 邊界不硬答 | 91.7% | 83.3% | |
| POLARITY | 12 | 10 | |

**被拒嘗試分析（`tools/agent_attempts_report.py`，首次可見）**：拒因嘗試數 QUOTE_NOT_COVERING 41／POLARITY 12／ref_invalid 10／UNCITED 7／ref_source_not_found 6／empty_sentences 1；被拒過的回合最終 36 轉人、4 答、1 問。**ref_invalid 18 筆中 16 筆是「缺段」**（三段式標記漏抄一段）⇒ 支持 029b「標記縮成不透明 id」方向。QUOTE_NOT_COVERING 多為 2 句 2 refs 的正常回答 ⇒ 是否誤殺待 4.4b 標籤。
