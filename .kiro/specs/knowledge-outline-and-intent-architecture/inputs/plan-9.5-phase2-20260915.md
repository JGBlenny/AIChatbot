# 9.5② 補內容計畫（草案 v0，2026-09-15；待 plan-verifier 審）

## 現況（①已落地）
兩份正本已是 9 領域粗目；pm 15 細目／prospect 38。零格：pm A／B／C／H／I，prospect H。15 條拆併細目無 `reviewed`（補審前不可見）。R1 prospect 檢索通過；R2 pm 無 gold 題集。

## 目標
每個粗目對每個受眾都有「該受眾會問的細目」，講法齊、可答，且 R2 可量。

## 步驟（提案）
- ②-0 補審 15 條（業主逐條 ✅）→ 加 `reviewed`、重導出、更新 `test_canon_assembler_req` 未審清單。
- ②-1 步 5 覆蓋圖：對新正本跑 `coverage_map.py`（凍結材料 `coverage-map-v3-20260907.json` 綁舊 id ⇒ 先 `remap_ids` 重映；split／merge 格重判）→ 印每格缺什麼。
- ②-2 逐粗目補洞（先 pm A／B／C／I，再 H）：材料＝幫助中心 92 頁（`jgb-domain-map.md` §3 已按領域分：租約 23／帳務 15／金流 12／物件 8／帳號 7／團隊 3…；「房東教學 01–09」系列＝pm 內容）＋ `docs/knowledge/jgb-product-facts.md`（程式證明事實）＋ jgb2 `docs/features/core-features/`；走 outline-curation 步 1 intake（kb 列／草稿）→ 步 2（3 角度＋合成）→ 步 3 講法（人審）→ 步 4 可答性 → 步 6 diff → 寫正本；每粗目一輪業主審。
- ②-3 pm 題集（每細目 ≥3 真實問法＋gold）：等洞補完再寫，否則 A／B／C／I 沒 gold 可指。
- ③ 正式驗收（acceptance-9.5）→ ④ 部署。

## 已知疑點（自列）
1. 「H 幫助中心」當粗目是否成立——它是通路／來源，不是使用者會問的主題；先前覆蓋代理也質疑。
2. 題集是否真的要等洞補完——反向：先寫題集、gold 標 `not_available`，本身就是覆蓋圖的一種。
3. 補洞材料的來源與 `intake --kb-json` 形狀不合（幫助中心是 HTML、事實帳本是 md）——要先轉成 kb 列／草稿 JSON，這一步誰做、怎麼去識別。
4. 每粗目一輪＝3 角度＋合成＋雙判者，成本表上限 步 2 ≤6 代理／受眾、步 4 ≤180——五個零格粗目 × 兩受眾會不會超。
5. prospect 已 38 細目、售前是否真的需要 H／F／G 補厚，還是售前本來就該薄。
