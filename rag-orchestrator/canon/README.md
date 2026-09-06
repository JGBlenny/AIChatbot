# canon/ — 知識正本目錄

路徑約定：本目錄 `rag-orchestrator/canon/`（映像內 `/app/canon`）是受眾正本（`<audience>.md`）的唯一位置，⛔ 與 Python 套件 `services/agent/canon/` 不同物。正本只在 git、走 code review；DB 為衍生物（R2.9／DSP-012）。

## 檔案

| 檔 | 身分 | 誰產生 |
|---|---|---|
| `<audience>.md` | **正本**（人審、可引用內容的唯一來源） | 人（或 skill 步 2 `apply_proposal.py` 產草稿後人改） |
| `<audience>.json` | 衍生物＝`export_json(parse_canon("<audience>.md"))` | 程式；⛔ 不手改 |

CI unit `tests/unit/agent/test_canon_export_sync_req.py` 逐位元比對兩者；不一致（含忘了重導出）必紅。重導出：

```bash
cd rag-orchestrator && python3 -c "from services.agent.canon.canon_parser import parse_canon, export_json; export_json(parse_canon('canon/prospect.md'), 'canon/prospect.json')"
```

格式與解析規則見 `services/agent/canon/canon_parser.py` 檔頭（front matter 七鍵、`## 標題 {#X}`、`### 標題 {#<audience>/<X>/<slug>}`、屬性區塊、一行一句）。編輯時 repo hook `.claude/hooks/outline_gate.py` 會做結構與識別碼粗篩；parser 是完整判準。

## 審核流程（R2.9）

1. **寫入權＝PR review**：任何人可開 PR 改正本；合併需至少一位 reviewer 核可。⛔ 不直接推 main。
2. **reviewer 名進 front matter**：核可時把 reviewer 加進 `reviewers: […]`，並在被改的細目加 `- reviewed: {by: <reviewer>, at: YYYY-MM-DD}`；沒有 reviewed 的細目視為草稿（`content_reviewed_predicate` 不放行入庫）。
3. **講法規則**：`- phrasings:` 只收人改寫過的短主題詞；`source: traffic:*` 者 ≤20 字且不含 ≥4 位數字串（parser 強制）；真流量原句只在 `.claude/skills/outline-curation/raw/`（gitignored，90 天刪）。
4. **內容變更＝新 `content_sha256`**：依賴該細目的講法與測試題進待審（步 3／步 5 工具計算），⛔ 不得靜默沿用。
5. **入庫**：只有正本 commit 後，才由 `tools/canon/export_batch.py` → `import_facet_knowledge.py` 寫 DB（需業主授權 D1）；DB 不是來源。

## Review checklist（PR 模板 `.github/PULL_REQUEST_TEMPLATE.md` 同步）

- [ ] `<audience>.json` 已重導出且 CI 同源測試綠
- [ ] 新增／變更細目都有 `sources`、`instance_applicability`；變更者有 `reviewed`
- [ ] 沒有講法出現在內容行（parser `phrasing_leaks` 為空）；沒有識別碼（hook／`test_pii_scan_req.py`）
- [ ] **高風險 diff**：`.claude/settings.json`、`.claude/hooks/`——這兩處改動＝改閘門本身，必須第二位 reviewer，並在 PR 描述說明為何要改閘門
