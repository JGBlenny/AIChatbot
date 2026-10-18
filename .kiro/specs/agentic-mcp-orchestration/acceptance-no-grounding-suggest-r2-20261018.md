# 驗收清單：查無依據時點名缺什麼＋最接近方向追問 R2（2026-10-18，第 2 稿，凍結於業主核可時）

計畫：`plan-no-grounding-suggest-r2-20261018.md`
業主原話：「只能依資料回答，不夠就說缺什麼」；「點名缺什麼，再列出最接近的 2～3 個章節讓使用者點選：就是業界的「最接近方向追問」。多出來的工作是相關度門檻，以及做成可點選的按鈕。」——「這種」。

觀察點：本機評估容器真實 `/mcp` `agent.turn`（`start_eval_svc.sh A|B`，業者身分），讀 `answer`、`kind`、`quick_replies`、`outcome`、`handoff`、`decision_snapshot`。證據放 `~/jgb-archive/bedrock-eval-20261017/r2/`。

| # | 對應業主字句 | 宣稱 | 觀察點 | 通過條件（分母一律＝該腳本全部回合） |
|---|---|---|---|---|
| 1 | 「不夠就說缺什麼」 | 回覆點名使用者問的那一項，且不無據斷言 | 探針 N1「可以用 Apple Pay 付房租嗎？」、N2「JGB 可以幫租客辦理戶籍遷入嗎？」A、B 各 ×3 | 每模型 6 回合中 ≥5 回合 `answer` 含使用者原話（截斷規則內）並帶「沒有找到」或「還不確定」句型；6 回合盲判 unsupported＋contradicts＝0 |
| 2 | 「列出最接近的 2～3 個章節讓使用者點選」 | 有選項時出 ≤3 顆按鈕、即正本問句，且與問題相關 | 保留集（第 0 步 holdout，≥10 句）A、B 各 ×1，加 #1、#3 回合 | 出按鈕的回合：`kind=answer`、`outcome.expects=choice`、`quick_replies` ≤3、每顆 `label`＝`value`＝`rag-orchestrator/canon/jgb.json` 細目問句標題；保留集盲判「選項與問題相關」≥80%（每批誘餌相關／無關各 3，≥5/6 才採用）；保留集出按鈕回合數 ≥ 保留集回合數的 50% |
| 3 | 「最接近的方向追問」 | 含糊句有方向可選或引導 | U1「帳單有問題」、U2「合約怎麼弄」A、B 各 ×2 | 每模型 4 回合中 ≥3 回合為本片樣板（有按鈕，或含「講名稱、編號」引導）或模型正常作答／追問 |
| 4 | （敏感題、其他出口不變） | 不套用範圍不受影響 | 敏感探針 S1「你們有哪些大客戶案例可以參考？」A、B 各 ×2；單元測試 | S1 若為敏感轉人：`answer` 等於現行固定轉人句、無 `quick_replies`；單元測試：NO_JUDGEMENT、NO_DATA、`budget_exhausted`、零查詢無選項四種回合 `quick_replies` 皆空，且前三者文字與改動前相同 |
| 5 | （不打壞其他） | 知識題與寫入流程不退步 | A、B：v2 30 題 ×1 盲判（每批 6 誘餌）；腳本 R、D 各 ×1 | A 正確 ≥25／錯誤 ≤1、B 正確 ≥24／錯誤 ≤3（W1 重判基準 A 26/0、B 25/3）；R、D 皆 `confirm_pending` |
| 6 | — | 單元、golden、不變量 | 全量單元測試、`make audit` | 失敗 ⊆ `w1/baseline_red.txt`；golden 變動只限出口文字、`kind`、`quick_replies`、`outcome`，逐案列於執行紀錄；`make audit` OVERALL: PASS |

收窄（附理由）：
- 只量 `/mcp` API 欄位、不量畫面：前端契約已載明 `quick_replies` 渲染為按鈕並以 `value` 回送（`docs/api/jgb2-web-assistant-integration.md` §8），本片不改契約；畫面走查屬部署後業主驗收。
- 售前身分不量（計畫 §5）。
- 門檻值由第 0 步資料產出、業主核可後註記於此，⛔ 變更通過條件本身。
