# M-b 步 2 結構提議首跑（2.4a 前段，2026-09-06）

> 形態：`structure_propose.py prepare` → 3 個 Claude Code 子代理（角度互不可見）→ `validate` → 第 4 個子代理合成 → `package` → `apply_proposal.py`。⛔ 未打模型 API（業主裁）。輸入＝21 列 prospect kb（sha `4a17038c…`）＋18 筆草稿（sha `4cc0feb8…`）＝39 項；粗目固定 A–G（`schemas/coarses-prospect.json`）。
> 產物：envelope `runs/2026-09-06T00-00-00Z/structure-proposal.json`（versioned）；原始 prompt／回覆 `raw/structure-20260906/`（gitignored）；**正本草稿** `raw/structure-20260906/prospect.draft.md`（322 行、7 粗目、37 細目、159 句；hook `check_structure` 零錯、`canon_parser` 回讀通過、兩次套用逐位元相同）。⛔ 草稿未進 `rag-orchestrator/canon/`、未 commit，等業主審。

## 1. 三角度與合成

| 角度 | 細目數 | id_map op 分佈 |
|---|---|---|
| user_question_path | 40 | {'keep': 33, 'split': 5, 'merge': 5} |
| content_boundary | 36 | {'keep': 30, 'merge': 8, 'split': 3} |
| audience_level | 28 | {'keep': 16, 'merge': 21, 'split': 4} |
| synthesis | 37 | {'keep': 29, 'merge': 8, 'split': 5} |

三份提議 id_map 都覆蓋 39 項（validate 全綠）。合成 37 細目全部來自三份提議既有 id（package 守門）。每粗目細目數：{'A': 4, 'B': 3, 'C': 21, 'D': 5, 'E': 2, 'F': 1, 'G': 1}。

## 2. 合成否決的替代切法（13 條，供業主審）

- 個人房東 10／20／30 戶各自獨立為三個細目（user_question_path）。——三筆模組組合與試用建議大幅重疊、僅戶數參數不同，同主題不應有三個細目。
- 3600 拆為五目，簽約邀請時效與社會住宅流程各自獨立（user_question_path）。——時效與社宅公證都依附建約流程脈絡才完整，單獨成目會與流程細目重複。
- 3600 只拆範本，修改規則與歷史合約（draft:10）併入租約管理一目（audience_level）。——修改規則與到期保留各自可獨立回答，併入會讓單一細目承載三個不同問法。
- 5379 整筆歸 G 現有不足（user_question_path）或整筆歸 B 適配（content_boundary）。——可匯入範圍是適配的能力問題、不支援項目是現有不足，屬不同層級，拆分互為另見比擇一歸類更符合粗目設計。
- 3599、draft:5、draft:6 合併為單一房源管理細目（audience_level）。——模組總覽與操作流程、狀態解釋是不同層級，應以另見處理而非併為一目。
- draft:11 帳單內容與 5380 帳單版面自訂合併（audience_level）。——「帳單顯示什麼」與「版面能否自訂」是兩個不同問法，兩份提議皆分開。
- draft:12 金流廠商與 draft:13 信用卡繳租合併（audience_level）。——「能刷卡嗎」是使用者直接會問的單一問題，另見金流廠商即可，不需併目。
- 3602 團隊管理與 draft:14 權限細分合併（audience_level）。——模組總覽與具體權限問題層級不同，兩份提議皆分開。
- draft:2 大房東定義併入大房東報表細目（audience_level）。——名詞定義與授權機制和報表運作是不同主題，兩份提議皆分開。
- 3611 免費試用與 draft:16 帳號註冊合併（audience_level）。——試用條件與註冊操作步驟是不同問法，兩份提議皆分開。
- 3608 為什麼選金箍棒歸 E 競品（audience_level）。——該內容不指名對手、只述自身優勢，兩份提議歸 A 產品基本盤。
- draft:8 儀表板歸 C 六大模組（content_boundary）。——儀表板跨模組，兩份提議歸 A 產品基本盤。
- draft:15 系統通知歸 A 產品基本盤（audience_level）。——通知觸發多為帳務與合約動作，兩份提議歸 C 六大模組。

## 3. 草稿的已知限制（業主審時要看的地方）

- **split 的內容沒有真的拆**：`apply_proposal.py` 對 split 只做「來源整段複製」，kb:3600 的全文出現在 3 個細目（建約流程／範本／修改）、kb:5379 出現在 2 個（可匯入範圍／不支援項目）。這是刻意的：內容切分屬人審，工具不替人決定哪句歸哪目；審稿時把不屬於該細目的句子刪掉即可，`content_sha256` 會跟著變。
- **11 個細目只有 1–2 句**（多為草稿來源），G「現有不足」只有 1 細目（來自 5379 拆出）；design 要求 G 每格一句對外說法＋出口，缺的部分要業主補內容，⛔ 工具不造句。
- 講法（phrasings）全部空：步 3（2.2 `phrasing_map.py`）未做；`see_also` 也未產（提議的 reason 提到「另見」但 schema 沒有欄位，2.2／人審補）。
- `instance_applicability` 全為 general（來源 kb 列無此欄、草稿為 general）。

## 4. 下一步

2.2（講法工具＋PII 掃描）→ 講法掛回這 37 細目 → 2.4a 交業主審草稿（`prospect.draft.md`）→ 核可後才進 2.4b（可答性判者以正本細目為候選重跑、reweigh、diff）。

## 5. 2.4a 交件（2026-09-06 晚）：講法已掛進草稿

- 步 3 首跑（`phrasing_map.py`，去識別修正後重產）：候選 1,270、掛上 **229 條**到 35 細目、待審 984（`runs/2026-09-06T00-00-00Z/phrasing-map.json` `payload.unassigned`）、凍結題排除 41、相似細目對 4（`similar-items.json`；最高分 data-migration ↔ migration-limits 0.56，⛔ 未合併）。
- `attach_phrasings.py` 把 229 條 `proposed` 講法掛進草稿 ⇒ **`raw/structure-20260906/prospect.draft.with-phrasings.md`**（hook 結構與識別碼掃描零錯；parser 回讀通過；`phrasing_leaks` 空；兩次掛載逐位元相同）。掛載報告 `raw/structure-20260906/attach-report.json`。
- 沒有講法的 2 細目：見 `attach-report.json` `fines_without_phrasings`。
- 業主審的東西（一次看完）：①37 細目結構與標題 ②split 重複句（kb:3600 三處、kb:5379 兩處）要刪 ③G 現有不足補內容 ④229 條講法留／改／刪（多為 question_summary 關鍵字與口語問法，`source` 可追） ⑤4 對相似細目要不要併 ⑥984 條 unassigned 要不要撈。
- 審完的檔案放回 `rag-orchestrator/canon/prospect.md`（hook 會在 Edit／Write 時做結構與識別碼粗篩），並跑 `export_json` 產 `prospect.json`（同源測試守），才進 2.4b。
