# 任務 1.2 獨立驗證與處置（2026-09-06）

> 受測物：`.claude/hooks/outline_gate.py`＠`782696cd`（1.2 合併點）。fresh verifier 以自建佈局、自組 stdin 事件實跑，⛔ 未採信實作者測試。
> claim：「五種違反在真 hook 路徑各被擋一次（exit 2）；五種合規各放行（exit 0）；非目標路徑零誤擋且零輸出。」

## 裁決：CONFIRMED（原 claim）＋ 7 條獨立發現，處置如下

| # | 發現 | 優先 | 處置 | 落點／理由 |
|---|---|---|---|---|
| F1 | 識別碼掃描套用到正本白名單時，合法內容大量假陽性：`20260906`、`budget_tokens: 12000000`、`kb 12345678` 皆以 `tax_id` 擋；`月租 1500 元，自 2026-09-06 起` 以 `amount_date` 擋；`第 12345 號公告` 以 `number_label` 擋；`GET-1234` 以 `plate` 擋 | P2（本任務引入） | **FIX（部分）**＋**DEFER（部分）** | FIX：front matter 整段不掃（只有 version／budget 數字）；`tax_id` 排除 19xx／20xx＋合法月日的 8 位數。回歸鎖 `test_f1_*` 兩條（含正對照 `12345678` 仍擋）。DEFER：`amount_date`／`number_label`／`plate` 維持 design D3 的封閉清單——售前正本依規則**不報價**、不引公告編號，實際碰到再收；若日後正本需要寫定價生效日，那是 design 層要重裁的取捨，⛔ 不在 hook 偷放寬 |
| F2 | 狀態檔固定 `session.json`，不依 `session_id` 分檔；design 寫 `<session>.json` | P3 | **DEFER（已知取捨）** | 狀態檔由 skill 腳本（Bash 執行）寫入，腳本拿不到 hook 事件的 `session_id`；分檔需另立「session 識別交握」機制。多視窗並行時兩 session 共用同一狀態檔是已知風險，1.4 前不會有並行寫正本的情境；升級時機＝M-b 首跑前 |
| F3 | 非物件 JSON（`[1,2]`）⇒ exit 1＋traceback | P3 | **FIX**（併入 F1 同一改動） | `_read_event` 非 dict 回空；回歸鎖 `test_f3_*` |
| F4 | Stop 擋回合時理由只在 stdout JSON；exit 2 時 harness 回饋模型的是 stderr | P3 | **FIX**（併入） | 理由同時寫 stderr；回歸鎖 `test_f4_*`。stdout JSON 保留 |
| F5 | 白名單正則不收含數字檔名（`prospect-2.md`／`Prospect.md`） | P4 | DEFER | 受眾檔名約定＝`<audience>.md` 小寫底線連字號，含數字的檔名本來就不該出現；若要放寬先改 design 元件 3 |
| F6 | `CLAUDE_PROJECT_DIR` 未設且 cwd 在 repo 外 ⇒ fail-open 靜默 | P4 | DEFER | 線上路徑 harness 必設該變數（1.1 實證）；fail-open 是 design 元件 3「缺檔放行」的同款原則 |
| F7 | `abc@example.com` 同時計 `email` 與 `line_id` | P4 | DEFER | 只影響訊息重複，擋的行為正確 |

## 修後重查

修改後依「任何 post-verdict 變更使 final-byte 覆蓋失效」規則：主 checkout 容器 `_meta/`＋`skills/` 118 passed；fresh verifier 第 2 輪針對 F1／F3／F4 與原 claim 回歸重查 ⇒ **CONFIRMED**（①日期／budget 放行 ②`12345678`／email／手機仍擋 ③八種壞 stdin 皆靜默 ④Stop 理由 stderr＋stdout 並存 ⑤五擋五放零誤擋不回歸），另提兩條 advisory：

| # | 發現 | verifier 級 | 主 session 處置 |
|---|---|---|---|
| A1 | 「跳過 front matter」不分路徑：`runs/` 檔以 `---` 開頭時該區段漏掃、未閉合時全檔漏掃——`runs/` 正是 D3 個資主面 | P3 | **改判 P2（本輪修法引入的隱私面回歸）→ FIX**：`check_identifiers(abs_path, skip_front_matter=is_canon)`，只有正本白名單跳 front matter；回歸鎖 `test_a1_runs_file_with_front_matter_still_scanned`（修前紅、修後綠）；容器 119 passed；第 3 輪 fresh verifier 針對 A1 重查 ⇒ **CONFIRMED**（六條全過；函式層對照證明舊 `skip=True` 對 runs/ 回空、新預設回三筆命中）|
| A2 | 統編恰好長得像日期（如 `20130411`）會被放行，隨機統編約 0.7% 命中此形狀 | P4 | DEFER：統編不是售前正本會出現的內容；`runs/` 側講法有 ≤20 字＋無 ≥4 位數字串的獨立約束（2.1 parser）兜底 |

第 3 輪另提兩條 P4，皆 DEFER：正本 front matter 未閉合時識別碼掃描整檔跳過（目前被結構檢查「未閉合必擋」遮住、不可達；若日後結構檢查改警告要先補）；`LINE_ID_RE` 對每個 email 必伴隨 `line_id` 誤報（純訊息噪音）。verifier 指出「runs/ 未閉合 front matter」原無測試鎖，已補 `test_a1_runs_file_with_unclosed_front_matter_still_scanned`（純測試、hook 不動）。

**收案**：三輪 fresh verifier 皆 CONFIRMED；容器 `_meta/`＋`skills/` 120 passed；1.2 完成。

## 給 1.4／2.x 的提醒

- 講法（`phrasings`）本來就受 design「≤20 字且不含 ≥4 位數字串」約束（2.1 parser），與本 hook 的識別碼掃描是兩層；hook 只是最後一道。
- 正本內容若需要寫日期，用 `2026-09-06`（帶連字號）不會誤判；純 8 位數日期現在也放行，但 `12345678` 這種會擋。
