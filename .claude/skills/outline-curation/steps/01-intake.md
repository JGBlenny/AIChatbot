# 步 1：intake

**輸入**：kb 列 JSON（呼叫端先匯出，腳本不讀 DB）、草稿 JSON、缺口地圖 JSON、既有正本 Markdown（選填）。
**輸出 schema**：`../schemas/intake.json`。
**形態**：腳本（`../scripts/intake.py`，決定性）。
**出口條件**：`intake.json` 產出且各輸入 `inputs_sha` 齊全；`object_under_test` 骨架的 `materials` 非空、`approved_by` 待業主填。

⚠️ **目前為休眠閘門**：Stop hook（`.claude/hooks/outline_gate.py`）的 `object_under_test`／`materials_frozen`
檢查只在狀態檔 `evals_ran` 非空時才啟動；目前七步腳本沒有任何一支會寫入 `evals_ran`——要到
`agent_eval` 整合進來（任務 6.4／4.3）才會有腳本寫這個鍵。查證：`grep -rn evals_ran .claude/hooks/outline_gate.py`
只在 Stop 檢查那行讀，`grep -rln evals_ran .claude/skills/outline-curation/scripts/` 查無寫入。

## CLI（與 `intake.py --help` 逐一對應；F13）

```bash
python3 .claude/skills/outline-curation/scripts/intake.py \
  --kb-json    <kb 列 JSON 檔（呼叫端先匯出，⛔ 本腳本不讀 DB）> \
  [--drafts    <草稿 JSON 檔>] \
  [--gapmap    <缺口地圖 JSON 檔>] \
  [--canon     <既有正本 Markdown（選填）>] \
  --out        .claude/skills/outline-curation/runs/<run>/intake.json \
  --frozen-at  <ISO 時間戳，⛔ 不用 datetime.now()>
```
