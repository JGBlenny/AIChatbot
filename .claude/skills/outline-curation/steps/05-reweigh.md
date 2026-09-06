# 步 5：reweigh

**輸入**：正本 Markdown、`demand-v2.json`、`map-v2.json`（缺口地圖）、`answerability.json`。
**輸出 schema**：`../schemas/coverage-reweigh.json`。
**形態**：腳本（`reweigh.py`，呼叫 `tools/gapmap/coverage_map.py` 重量，決定性）。
**出口條件**：每格皆有去向欄；無去向格數＝0。
**下一步**：`coverage-map.json` 有 not_available／owner_decision 格 ⇒ 先走 [步 5b](05b-source-audit.md)，⛔ 不得直接交業主。

## CLI（與 `reweigh.py` argparse 逐一對應；F13）

```bash
python3 .claude/skills/outline-curation/scripts/reweigh.py \
  --canon         <正本或草稿 .md> \
  --demand        <demand-v2.json> \
  --map           <map-v2.json（缺口地圖）> \
  --answerability .claude/skills/outline-curation/runs/<run>/answerability.json \
  --coverage-out  .claude/skills/outline-curation/runs/<run>/coverage-map.json \
  --out           .claude/skills/outline-curation/runs/<run>/coverage-reweigh.json
```

exit 2 情況：`answerability.payload.needs_rubric_revision==true`（⛔ 不重量，回主 session 回修 rubric）；
`CoverageMapError`（材料不一致，見 `coverage_map.py` 檔頭）；出口未達（無去向格或無來源細目 >0）。
