# Plan 9.30 驗收清單（凍結，2026-10-05）

> 計畫：`inputs/plan-9.30-twelve-fine-redraft-20261005.md`。
> 依據：業主 2026-10-05 的兩則回覆——「A 整條刪除＋重寫 12 條 (Recommended)」「保留 id 整條重寫，重複的才刪 (Recommended)」。
> **非目標**（理由見計畫 §2）：
> - 9.24 以來整句刪掉的正確資訊重新起草；
> - 業主抽查 30 句；
> - 9.29 附帶觀察 32 項；
> - 招租店舖授權疑點。

| # | 服務的原文 | 驗收 | 觀測點 | 證據 |
|---|---|---|---|---|
| A1 | 「12 條」——全數 | 計畫 §0 表的 12 個 id，每個在 §6 都恰有一個去向：整條重寫寫入／業主裁定整條刪／業主裁定保留／寫入核對推翻後保留原文並轉下份計畫；無遺漏、無多出 | 指令比對 §6 與正本 | 輸出 |
| A2 | 「保留 id 整條重寫」 | 去向為「整條重寫寫入」的細目：id 與所屬粗目不變；`target_user` 與重寫前相同（若有更動，終審單須列出並經業主核可）；標題、全部句子、講法以新版本取代；每句都有逐字命中匯出的 evidence；講法 2～5 條、全庫 NFKC 不重複；標題、句子、講法掃描識別字與 `/` 路徑皆為 0 | 正本 `jgb.json` × drafts × 機械檢查輸出 | 輸出 |
| A3 | 重寫內容要正確 | 每條寫入細目的全部句子與標題，都有 fresh 先審判定（每次先審混 1 條誘餌，且誘餌被抓到並引用來源）；有刪句的細目另有整條複查判定；寫入 commit 附 `kind: write` 證據，該 commit 全部寫入細目逐句「成立」，`content_sha256`／`title_text` 與 commit 內正本相同（不變量 43 W 機械檢查） | 先審、複查、寫入證據＋`make audit` | 輸出 |
| A4 | 「重複的才刪」 | 被刪除的細目＝業主終審逐條核可的「建議整條刪」集合，且每條在終審單附重複對照證據；被刪細目不在正本 `jgb.json`、`jgb/*.md`、`CATALOG.md` 與 drafts 中；`drafts_diff` 的 (d) 刪除集合＝核可集合；repo 內（正本、drafts、runs、`.kiro` 以外）引用該 id 的位置為 0 或逐筆說明（附正對照） | 指令 | 輸出 |
| A5 | ⛔ 改別條 | 12 條以外的細目，`content_sha256`、標題、講法、`target_user` 與 HEAD 前全部相同；細目集合只少「核可刪除」那幾條 | 腳本比對 | 輸出 |
| A6 | 已審細目數（+0） | commit 後已審細目 pm、prospect 等於「起點 −（核可刪除中屬該身分的條數）」，分母同減，543 條（扣除刪除數）全有已審；寫入順序為 `approve_write write` → 容器重匯出 → `load_canon_or_die` → `approve_write verify`（backup＝加已審前快照）輸出 `mismatches: 0`；`drafts_diff --fix-log inputs/fix-log-9.30-20261005.md` RESULT PASS | `endpoint_progress.py`＋`approve_write` 輸出 | 輸出 |
| A7 | 業主終審 | 正本中被加回已審的細目，恰為業主終審核可、且未被寫入核對推翻的集合；業主原文逐字記在計畫 §6 | 對照業主原文與正本 | 原文＋輸出 |
| A8 | repo 公開——客戶名 | `canon_check.py` 客戶名詞表掃描正本 0 命中；本計畫新增或修改的 `.kiro` 檔、drafts 改動細目，以不分大小寫擴充掃描，命中為 0 或逐筆說明，結果記 §6 | 指令 | 輸出 |
| A9 | 工具 | 預跑結果記 §6：`remove_fine` 正對照（允許時移除成功，`drafts_diff --fix-log` (a)(d)(e) 全過、生成器記 `fine_removed`、`canon_check --remove` exit 0）與負對照 2 項（不在 REMOVE 清單 ⇒ 拒絕；混其他 ops ⇒ 拒絕）；`canon_check` 負對照 2 項（缺席細目不在 `--remove` 清單 ⇒ exit 1；不傳 `--remove` ⇒ 與現行同為 exit 1）；`rewrite_fine` 正對照（舊 evidence／否定 grep／待裁不殘留）與負對照 3 項（含 `target_user` ⇒ 拒絕；evidence 句序越界 ⇒ 拒絕；7 個欄位缺任一 ⇒ 拒絕）；修正紀錄正對照（12 條只套 11 條、重新產生後 `drafts_diff --fix-log` (a) 未記 0／多記 0、(d) 相等、RESULT PASS）與負對照（沿用 12 條版紀錄對 11 條套用的 drafts ⇒ FAIL）；`edit_fine.py`、`canon_check.py` 兩份鏡像 `cmp` 相同；`--roundtrip` 八架（A～G、I；H 除外）位元組不變 | 指令輸出 | 輸出 |
| A10 | 不碰他線、無回歸 | 他線未提交檔指紋不變；commit 前全套 unit 紅燈與基準差集＝∅；`make audit` OVERALL PASS；H 守護 PASS | 指令 | 輸出 |
| A11 | 規則 P：+0 需業主同意 | commit 內 plan-meta 的 `consent_zero` 與業主核可原文逐字一致 | `git show` | 原文＋輸出 |
| A12 | 交接正確 | HANDOFF 開頭現況已更新，§12-1 加 9.30 列 | 讀檔 | 輸出 |
