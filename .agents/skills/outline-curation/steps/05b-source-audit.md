# 步 5b：source-audit（權威來源核對，交業主前）

**為什麼**（2026-09-07 業主裁）：步 5 曾把 11 格 not_available／owner_decision 直接交業主，事後對 jgb2 程式對碼有 8 格是程式證明得了的事實。**問業主是盤查窮盡後的剩餘，不是替代。**

**輸入**：`coverage-map.json`（步 5）。
**工作單**：`python3 scripts/source_audit.py worklist --coverage <cm> --out <worklist.json>` → 需核對的格＋權威來源清單（jgb2 master 程式、jgb2 docs、幫助中心、事實帳本）。
**盤查形態**：按領域派唯讀 `scout`（每題要求 `path:symbol` 證據；否定結論必帶正對照），主 session 對決策關鍵事實親自對碼一次（scout 的否定結論曾錯：只掃 Admin 就說「沒有門鎖」）。
**回填**：事實寫進 `docs/knowledge/jgb-product-facts.md`（受眾中立、附引用、錨點），`source-audit.json` 每格一筆：
- `verified_fact`＋`evidence[]`＋`ledger_anchor`（錨點必須存在）
- `verified_absent`＋`evidence[]`＋`positive_control`
- `owner_needed`＋`why_unresolvable`（說明盤查了哪些來源、為何仍定不了）——**只有這類才交業主**
- `owner_decided`＋`owner_decision`（業主已裁）
**檢查**：`python3 scripts/source_audit.py check --coverage <cm> --audit <source-audit.json>` → 狀態檔 `source_audit`；未核對 >0 ⇒ exit 2。
**出口條件**：`source_audit.unaudited==0`。Stop hook：`reweigh.needs_source_audit>0` 且已產 `diff_report` 而未核對 ⇒ 擋（⛔ 不得在未盤查下把草稿交業主）。
**schema**：`../schemas/source-audit.json`。

## 真實問句進場（Plan 9.14）

步 4 的真實問句 run（見 `04-answerability.md` 同名節）接到步 5／5b 時，所有中間檔留在 repo 外 run 目錄（含 `.text-external` 的圍欄內）：

- **步 5**：`reweigh.py --canon <正本目錄> --demand <run>/cells-<aud>.json --map <run>/map-<aud>.json --answerability <run>/answerability-<aud>.json --coverage-out <run>/coverage-map-<aud>.json --out <run>/coverage-reweigh-<aud>.json --state-file <run>/state.json`。`coverage-map.json` 的 `min_verification.phrasings` 與 envelope 的 `payload.cells` 都含問句 ⇒ 兩個輸出都受守門。
- **工作單**：`source_audit.py worklist --coverage <run>/coverage-map-<aud>.json --out <run>/worklist-<aud>.json`，**顯式**傳 `--authority`（⛔ 不用預設的 jgb2 `master`；本線正本與 drafts 釘在 `b2ee2ac382ce`，DSP-071 未裁）：
  - `--authority "code:/Users/chenqinghuang/dev/work/jgb2/dev2 (git show b2ee2ac382ce:<path>，釘住 commit)"`
  - `--authority "help:<幫助中心 HTML 目錄>"`
  - `--authority "ledger:docs/knowledge/jgb-product-facts.md"`
  worklist 的 `items[].question` 含問句 ⇒ `--out` 受守門；`_meta.text_policy` 由 coverage-map 帶進 worklist。
- **盤查**：scout 只收 worklist 切片的**檔案路徑**、以 `cell_id` 回報、⛔ 不轉述題目；jgb2 只走 `git show b2ee2ac382ce:<path>`。
- **回填帳本**：`docs/knowledge/jgb-product-facts.md` 在 repo 內且識別碼 hook 不掃 ⇒ 只寫受眾中立的產品事實、⛔ 不寫客戶措辭。
- **檢查**：`source_audit.py check --coverage <run>/coverage-map-<aud>.json --audit <run>/source-audit-<aud>.json --state-file <run>/state.json`（`--state-file` 預設＝主線 session.json；真實問句 run ⛔ 不蓋主線狀態）。
