# 驗收清單：主線第 2 步「兩層代理量測（gpt-oss 常駐服務基線）」（2026-10-18 第 3 稿；收尾 plan-verifier READY；業主核可，已凍結；同日業主選「加送出驗證 (Recommended)」擴充 #5、#7）

計畫：`plan-two-layer-eval-step2-20261018.md`
業主原話：
- 「目前要該是要把本地替換 oss 並確保 回應品質都能符合 有效的回應 並把某些部分邏輯參考業界做法去調整」「正式接線 是本地都處理好 才線上換吧」（HANDOFF-20261018 §1.1）
- DSP-087（業主「代理無法驗嗎?」「先代理處理 上線後再說」）：第一層固定題庫＋盲判（正確、不捏造、資料不足說缺什麼、敏感轉人、寫入走到確認卡、截斷、延遲）；第二層模擬客人代理多輪對話＋判分代理判「是否解決」（判準照 Intercom：最後一次回答後不再要求真人、不回頭再問）；先跑出數字再定門檻。
- 本 session：「不先繼續後面任務」；題庫「既有題＋N 抽 40 (Recommended)」；核可「核可且同意不推進終點 (Recommended)」；歷次「任何會呼叫 JGB 的測試前，先照 §2.3 確認本機是 mock」。

觀察點：本機常駐服務 `aichatbot-rag-orchestrator`（8100，第 1 步 commit `2892a183` 版本，Bedrock gpt-oss、mock JGB），經 eval-harness `--target resident`／`run.py chat` 打真實 `/mcp` `agent.turn`；資料庫 `aichatbot_admin`。證據放 `~/jgb-archive/two-layer-eval-20261018/`（題目與回答原文不進 git）。

| # | 業主字句 | 宣稱 | 觀察點 | 證據 | 通過條件 |
|---|---|---|---|---|---|
| 0 | 「任何會呼叫 JGB 的測試前，先照 §2.3 確認本機是 mock」 | 每次實打前是 mock | `run.py turns`／`run.py chat` 開頭 mock 檢查 | 指令輸出 | 每批 `True`；非 True 不送回合 |
| 1 | DSP-087「正確、不捏造」 | 知識 30 標籤分布 | 常駐 `/mcp` 實打＋`knowledge` 盲判 | records、judge in/out、key | 30/30 有標籤；每批誘餌 ≥5/6、分母相符；各標籤率＋Wilson CI |
| 2 | 「不捏造、資料不足說缺什麼」＋業主選 N 40 | N 40 結果分布 | 實打＋程式計轉人＋`grounding` 盲判 | records、`decoys/grounding.json`（組成 2/2/2）、judge in/out、key、種子與 id | 40/40 有結論（轉人或標籤）；`grounding` 每批誘餌 ≥5/6、組成與分母檢查通過；fabricated 等率＋CI |
| 3 | 「資料不足說缺什麼」（R3 重驗） | N1～N4 | 實打＋`probe` 盲判 | 探針批 | 4/4 有標籤；誘餌 ≥5/6 |
| 4 | 「敏感轉人」 | 12 題轉人率；作答者是否含承諾樣式 | 實打 `kind`、`handoff_reason`；答案 × `sensitive_patterns` 正則 | records、比對輸出 | 12/12 有結果；轉人率（依原因分列）；作答者命中數與類別 |
| 5 | 「寫入走到確認卡」（W1 重驗）＋業主「修繕流程互動」 | R、D、C、T 依計畫 §1.4 E2a-5 期望；RS、DS 按確認後送出並讀回 | 實打 `outcome.action`＋卡文字 `parse_card`＋`state`；快照鍵名交叉；`confirmed` 回合收據；讀回回合答案 | records（含 action、answer、quick_replies）、parse 輸出、`parse_card` 單元測試 | R、D、C、T、RS、DS 各 2 輪逐輪通過與否；不符列出哪個值；C 標「僅 mock」 |
| 6 | 「截斷、延遲」 | 第一層全部回合 | 快照 | 腳本輸出 | 截斷、budget_exhausted 次數；latency p50／p95／max |
| 7 | DSP-087「模擬客人代理多輪對話＋判分代理判是否解決（判準照 Intercom：最後一次回答後不再要求真人、不回頭再問）」 | 20 題 ×2 的 Intercom 解決率（主）與嚴格解決率（並列）、pass^2 | 常駐 `/mcp` 多輪實打＋Intercom 程式前判（含 max_turns 未 STOP、`outcome.action`、`parse_card`、寫入任務按確認後 `confirmed`＋收據）＋`resolution` 判分 | 每場對話紀錄、前判輸出、判分 in/out、誘餌（組成 3/3）、key | 40 場皆有結論（含作廢重跑）；判分誘餌 ≥5/6；兩率＋pass^2＋CI |
| 8 | （量尺自證） | 模擬者 critical 錯誤數、兩判一致率 | 判分 out | 計數 | 數字列出（⛔ 隱匿） |
| 9 | 「先跑出數字再定門檻」 | 報告只含數字與限制 | repo 內報告（計數）；原文 repo 外 | 報告檔 | 每維度率＋CI＋分母＋限制；題目與回答原文 0 進 git |
| 10 | — | 獨立驗證 | fresh verifier | 報告 | CONFIRMED |

收窄（非目標，附理由）：
- ⛔ 改 rag-orchestrator：修法屬第 3 步。
- ⛔ 設門檻、判過／不過：DSP-087「先跑出數字再定門檻」。
- ⛔ 用 H 留出集：業主選「既有題＋N 抽 40」＋大綱線規格 §2.4「補什麼在第一次 H 量測前凍結」。
- 照片／文件回合：等視覺模型（HANDOFF §1.2）。
- 正式機、preview 不碰；上線後真實解決率：業主「上線後再說」。
- 售前身分：harness 身分固定 vendor 4 業者；N 只抽業者題。
- 送出後不直接比對 mock 寫入紀錄（`JGB_MOCK_WRITE_LOG` 未設）：以收據＋讀回替代；業主選「加送出驗證」未選加寫入紀錄檔。
- C（建合約）只代表 mock 行為：正式機 `WRITE_NOT_SUPPORTED_ACTIONS` 回不支援固定句。
- N 無 gold：只判「忠於取得內容」，不判「答對」。
- 不做人工標註校準：DSP-087「全由代理量測」；以誘餌與兩判一致率替代。
