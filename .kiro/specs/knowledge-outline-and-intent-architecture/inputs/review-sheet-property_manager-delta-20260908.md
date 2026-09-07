# pm 正本增量審核單（2026-09-08）：與 agent 工具能力衝突的四句

> 背景：W0b 後替身連貫、工具齊全（`jgb2.query.bills` 可列清單、`jgb2.query.meters` 可用名稱查、`jgb2.query.repairs` 修繕進度、`jgb2.query.estates` 物件現況），但 R-讀 實跑模型照正本回「只能看點選那一筆」「電錶要 id」「沒有修繕歷史面向」⇒ 轉人／反問（`run_read6.jsonl` S1#1、S6、S8#1–#4）。正本這四句寫的是 **LIFF 線（③④⑤）進場模型**，LINE OA 聊天路徑沒有「點選」動作。⛔ 改法只改事實與定義，不寫例子；LIFF 線的規則以「進場帶 facet_context 時」為條件保留。

| # | 細目 | 現句 | 建議改為 | 依據 | 業主 |
|---|---|---|---|---|---|
| 1 | `C/overdue-bill-followup-scope`（L122） | 針對業務點選的那一筆帳單，可回近一年逾期明細… | 可回**業務權限內任一筆帳單**（以帳單編號指定，或先列出其可見帳單再指定）的狀態、金額、到期日與近一年逾期明細…（其餘不動） | `query_bills`：ref 單筆／無 ref 列清單（可見性依 JGB） | ✅ 2026-09-08 |
| 2 | `C/followup-session-single-item-boundary`（L133） | 每筆清單項目是獨立會話，只看被點選的那一筆；問到別戶時退出… | **由清單進場（帶 facet_context）時**每筆項目是獨立會話、只看被點選那一筆、問別戶退出；**聊天直接進場時**沒有點選項目，同一業務權限內的帳單／合約／物件／修繕可依編號或名稱切換，不視為離題 | line-bot 增補 K（同戶跨類別不觸發 scope_exit）；工具跨域皆可查 | ✅ 2026-09-08 |
| 3 | `C/urgent-repair-followup-scope`（L163）＋ `F/repair-history-facet-pending`（L236） | 目前沒有修繕歷史／進度面向，只有開單面向 ／ 是否新建屬待裁；第一版不開 | 修繕**進度**可查：單號、物件、分類、狀態、急迫程度、建單時間、指派（`修繕進度` 面向）；開單仍走拍照流程。F 細目改「已建（2026-09-08，業主 R3）」或刪 | `services/jgb/repairs.py` `REPAIR_FACE_BUILDERS`、`query_repairs` | ✅ 2026-09-08 |
| 4 | `C/meter-item-followup-scope`（L174） | 項目以 id 直接進槽位，不靠關鍵字檢索。 | 電錶可依**名稱或 id** 指定；餘額、可用度數、是否供電來自 JGB；「還能用幾天」是推算須標明 | `query_meters` keyword／ref；line-bot 增補 I（推算標明） | ✅ 2026-09-08 |

核可後：改 `canon/property_manager.md` 四句（reviewed 標記 2026-09-08）→ `export_json` → `test_canon_export_sync_req`＋`test_pii_scan_req`＋`check_budget` → 重跑 R-讀 20＋W6。

**業主 2026-09-08「好」：四句全採。已改 `canon/property_manager.md`（version 2026-09-08.1，五個細目 reviewed 09-08）、重導出 JSON、canon 測試 78 綠。**
