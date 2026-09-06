## 變更摘要

## Review checklist

- [ ] 測試：`scripts/run-tests.sh unit`（或 CI）綠；新行為有測試
- [ ] 若動到 `rag-orchestrator/canon/*.md`：`*.json` 已重導出、同源測試綠；細目有 `sources`／`instance_applicability`；變更者有 `reviewed`；reviewer 名進 front matter（見 `rag-orchestrator/canon/README.md`）
- [ ] **高風險 diff（需第二位 reviewer）**：`.claude/settings.json`、`.claude/hooks/`（流程閘門本身）、`rag-orchestrator/services/agent/canon/canon_parser.py`（正本判準）、DB migration
- [ ] 沒有憑證、`.env` 內容、識別碼進 diff
