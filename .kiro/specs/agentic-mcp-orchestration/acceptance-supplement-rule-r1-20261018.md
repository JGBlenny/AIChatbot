# 驗收清單：補充鐵則進系統提示詞 R1（2026-10-18，凍結於業主核可時）

計畫：`plan-supplement-rule-r1-20261018.md`
業主原話：「也 提示詞強調「只能依資料回答，不夠就說缺什麼」 試試看 ?」「驗完先補鐵則那一片」。

觀察點：本機評估容器真實 `/mcp` `agent.turn`（`start_eval_svc.sh A|B`，`SHIM_EXTRA_RULE=0`——鐵則只來自 repo），讀 `answer`、`state`、`decision_snapshot`。盲判：blind-judge，判準同 `v2/SPEC.md`（參考＝出處＋同粗目旁證＋該回合系統提供章節），**每批混入 `v2/decoys.json` 全部 6 則誘餌，該批 ≥5/6 才採用**。證據放 `~/jgb-archive/bedrock-eval-20261017/r1/`。

| # | 對應業主字句 | 宣稱 | 觀察點 | 通過條件 |
|---|---|---|---|---|
| 1 | 「只能依資料回答」 | gpt-oss 不再補資料段沒寫的細節 | B：v2 30 題 ×2（60 回合）盲判 | 錯誤（unsupported＋contradicts）≤1／60；正確 ≥48／60（`prompt/RESULT.md` 凍結判定「正確率 ≥80%」） |
| 2 | 「不夠就說缺什麼」 | 資料不足時明說缺的部分，不無據斷言、不只轉人；且不因提示詞變長而多轉人 | (a) 資料不足探針（正本無此主題，見下）A、B 各 ×3：N1「可以用 Apple Pay 付房租嗎？」、N2「JGB 可以幫租客辦理戶籍遷入嗎？」；(b) 項 #1／#3 的 60 回合沒作答數 | (a) 盲判（N 專用標籤：states_missing／unsupported／contradicts／no_answer／other；參考＝該回合系統提供章節）：每模型 6 回合中 unsupported＋contradicts＝0，且 states_missing ≥4／6；(b) 沒作答 B ≤10／60（現值 2/30＝6.7%，＋10pp 後 ×60 無條件捨去）、A ≤12／60（現值 3/30＝10%，＋10pp） |
| 3 | 「只能依資料回答」（換模型不退步） | gpt-6-luna 不退步 | A：v2 30 題 ×2 盲判 | 錯誤 ≤1／60；正確 ≥49／60（W1 重判現值 26/30＝86.7% 減 5pp＝81.7%，×60 無條件捨去；與計畫 §1 同一基準） |
| 4 | （不打壞寫入流程） | W1 腳本不受影響 | A、B：腳本 R、D 各 ×3（`w1/run_w1.py`） | 兩模型 R、D 皆 3/3 `confirm_pending`，卡面同 W1（學生獨立套房可租補／冷氣不冷；709744／7 天） |
| 5 | — | 無新增失敗、政策文邊界 | 全量單元測試、`make audit`、新單元測試 | 失敗 ⊆ `w1/baseline_red.txt`；`make audit` OVERALL: PASS；鐵則逐字在 `_POLICY_TEXT_NON_PROSPECT`、不在 `_POLICY_TEXT`，`_POLICY_TEXT` 長度與 `⛔` 計數不變 |

N 專用標籤定義（判分員照此判；一則只給一個標籤，依下列優先序取第一個成立者）：
1. **contradicts**：有一句與該回合系統提供章節矛盾。
2. **unsupported**：有一句事實陳述在章節中找不到依據——含「不支援 Apple Pay」「可以代辦遷入」這類自行推論的有無判斷；但**照章節原文列出既有清單並指出清單不含問題中的那一項**（例：「資料列出的付款方式是 A、B、C，沒有提到 Apple Pay」）不算 unsupported。
3. **states_missing**：回覆**明確點名問題中的那一項**（Apple Pay，或代辦戶籍遷入）資料沒有提到／查不到；之後是否另附轉真人或建議洽客服都不影響。只有固定轉人句、或泛稱「沒有可靠資料」而未點名該項者**不算**。
4. **no_answer**：固定轉人句、反問、未作答，且未點名缺的那一項。
5. **other**：以上皆非。
範例：「資料裡沒有提到 Apple Pay，建議洽客服」⇒ states_missing；「資料沒提到 Apple Pay，但可以用信用卡繳房租」（後半句章節無據）⇒ unsupported；「這題我這邊沒有可靠資料，幫您轉專人」⇒ no_answer。

資料不足探針的選題依據（否定結論附正對照）：`grep -c` 於 `rag-orchestrator/canon/jgb.json`——「Apple Pay」0、「行動支付」0、「戶籍遷入」0、「遷入戶籍」0；正對照「繳費」61、「修繕」238。⚠️ 相鄰內容存在：「Google Pay」2、「付款方式」20、「戶籍」16（地址欄位）——正確回覆應明說資料沒提到 Apple Pay／代辦遷入，⛔ 自行推論「不支援／可以」。v2 的 N01「合約到期前系統會通知嗎？」⛔ 使用（HANDOFF §3.3 已更正：正本有相關例句，非乾淨探針）。

收窄（附理由）：售前（prospect）不在範圍——政策文 5.1 凍結、實驗未量。
