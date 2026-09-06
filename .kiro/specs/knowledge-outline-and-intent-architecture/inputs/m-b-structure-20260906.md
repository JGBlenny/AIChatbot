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

- 步 3 首跑（`phrasing_map.py`；去識別先 NFKC、question_summary 詞 ≥3 字）：候選 1,236、掛上 **202 條**到 35 細目、待審 979（`runs/2026-09-06T00-00-00Z/phrasing-map.json` `payload.unassigned`）、凍結題排除 41、相似細目對 4（`similar-items.json`；最高分 data-migration ↔ migration-limits 0.56，⛔ 未合併）。
- `attach_phrasings.py` 把 202 條 `proposed` 講法掛進草稿 ⇒ **`raw/structure-20260906/prospect.draft.with-phrasings.md`**（hook 結構與識別碼掃描零錯；parser 回讀通過；`phrasing_leaks` 空；兩次掛載逐位元相同；`canon_sha256 dda8ea42…`）。掛載報告 `raw/structure-20260906/attach-report.json`。
- 沒有講法的 2 細目：`prospect/C/role-permission-granularity`、`prospect/D/subscription-change-renewal`（來源是草稿、無 question_summary 詞，口語問法也沒配上）。
- 過程中兩個工具判斷（記入程式與測試）：①`phrasing_leaks` 守門改「整句相等，或 ≥10 字才做包含比對」——主題詞組（「大房東報表」「Bananas」）本來就在內容句裡，子字串比對恆誤判；②question_summary 的 2 字詞（「合約」「收租」）不成講法。
- 業主審的東西（一次看完）：①37 細目結構與標題 ②split 重複句（kb:3600 三處、kb:5379 兩處）要刪 ③G 現有不足補內容 ④202 條講法留／改／刪（`source` 可追：question_summary／koyu／helpcenter） ⑤4 對相似細目要不要併 ⑥979 條 unassigned 要不要撈。
- 審完的檔案放回 `rag-orchestrator/canon/prospect.md`（hook 會在 Edit／Write 時做結構與識別碼粗篩），並跑 `export_json` 產 `prospect.json`（同源測試守），才進 2.4b。
- **建議版（業主 2026-09-06 同意先做 ⑤①）**：`raw/structure-20260906/prospect.draft.review.md`＝with-phrasings 版再加 5 條 `see_also`（3600 拆出的三目互指、data-migration↔migration-limits 互指）與 23 個複合標題縮短（去掉「／」另一半，保留與 slug 對應的那句）；parser／hook 零錯。與 with-phrasings 版的 diff 只在 `###` 標題行與 `- see_also:` 行。②③④ 仍由業主親手。

## 6. 六件審點的分工結果（2026-09-07；業主問「哪三件真的需要我」）

| # | 誰做 | 結果 |
|---|---|---|
| ② 拆分重複句 | **工具／主 session 已做**：kb 3600 依原句【】段落歸屬——流程目 13 句、範本目 4 句（取草稿 9 的版本）、修改目 2 句；5379：可匯入 3 句留 B、不支援 2 句留 G | `prospect.draft.review.md` |
| ④ 202 條講法 | **主 session 已預分**：koyu 89 條中 30 條操作口吻（怎麼弄／在哪／要怎麼…）已從 review 版移除（清單 `raw/structure-20260906/koyu-removed-operation-tone.json`，可還原）；question_summary 99、helpcenter 14、koyu 其餘 59 留 | 172 條 proposed |
| ⑤ 相似細目 | 已加 see_also（不併） | 5 條 |
| ① 標題 | 已縮短 23 個 | — |
| ⑥ 979 條未掛 | 不審，等其他受眾 | — |
| ③ G 現有不足 | **只有這件真的要業主**，而且縮成兩小題：(a) 3 個沒有任何來源的問題各答一句（C22 簽約另外收費嗎、C39 私人門鎖 vs 共用門鎖差別、C53 單合約 vs 雙合約差別）；(b) 5 個「知識在庫、但不在售前池」的格（C25 差額發票 kb 3798 等、C29 儲值金回充 kb 3417、C46 多語系 kb 3798／4652、C54 發票載具 kb 3414／3423／3419）要不要把那些列開放給 prospect（可見性決定，屬 D1 範圍）或另寫售前版細目。C52「系統管理模組」是名稱問題（六大模組無此名），建議在 A 總覽加一句對照即可 | 待業主 |

⇒ 真正要業主親手的是 ③(a) 三句話與 ③(b) 一個可見性決定；其餘已做成建議版，看 diff 即可。
