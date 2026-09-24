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
