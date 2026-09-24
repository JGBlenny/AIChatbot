# canon/ — 知識正本目錄（圖書館形態）

路徑約定：本目錄 `rag-orchestrator/canon/`（映像內 `/app/canon`）是知識正本的唯一位置，⛔ 與 Python 套件 `services/agent/canon/` 不同物。正本只在 git、走 code review；DB 為衍生物（R2.9／DSP-012）。

**2026-09-15 DSP-058／計畫 9.6 起：正本只有一份**（`canon/jgb/`，九架），**受眾不再各有一份正本**。
受眾隔離改由**身分的篩選結果**承擔：`canon_assembler.build_outline(doc, audience, identity, …)` 依細目的
`target_user`＋`business_types` 兩軸篩出該身分可見的細目集合——不屬於該身分的細目
**連標題都不出現**。⛔ 不得回頭用「載入哪一份正本」當隔離機制（那份機制已經不存在）。

## 檔案

| 檔 | 身分 | 誰產生 |
|---|---|---|
| `jgb/A.md … jgb/I.md`（**九架，固定白名單**） | **正本**（人審、可引用內容的唯一來源） | 人（或 skill 步 2 產草稿後人改） |
| `jgb.json` | 衍生物＝`export_json(parse_canon_dir("canon/jgb"))` | 程式；⛔ 不手改 |
| `jgb/CATALOG.md` | 衍生物＝`export_catalog(...)`：架層兩行（`## <架> <架標題>`＋`scope:`）、每個粗目一行 `### <粗目 id> <粗目標題>`、每細目一行，⛔ 不含內容句 | 程式；⛔ 不手改 |
| `jgb/README.md`（選用，目前不存在） | 說明（非正本）；parser 的衍生物白名單是 `CATALOG.md` 與 `README.md` 兩個，放了也不會被讀成正本 | 人 |

架的白名單是 `A.md…I.md` **九架全要在**（⛔ 不 glob），衍生物另允許 `CATALOG.md`／`README.md` 兩個：**出現白名單外的 `.md`**、缺一架、任一架是符號連結
⇒ `CanonFormatError`（大聲失敗，⛔ 不靜默多讀／少讀）。

啟動時 `load_canon_or_die(resolve_canon_dir())` 對 **`jgb.json` 與 `jgb/CATALOG.md` 各做一次逐位元組
重導出比對**，任一不同即 `CanonLoadError`（⇒ agent 路徑不可用）。CI unit
`tests/unit/agent/test_canon_export_sync_req.py` 同樣逐位元比對；忘了重導出必紅。重導出指令：

```bash
cd rag-orchestrator && python3 -c "
from services.agent.canon.canon_parser import parse_canon_dir, export_json, export_catalog
doc = parse_canon_dir('canon/jgb')
export_json(doc, 'canon/jgb.json')
export_catalog(doc, 'canon/jgb/CATALOG.md')
print(doc.canon_sha256)
"
```

格式與解析規則見 `services/agent/canon/canon_parser.py` 檔頭：
- 架 front matter **恰六鍵**：`coarse, title, scope, version, reviewers, language`（⛔ 無 `budget_tokens`、
  ⛔ 無檔級 `target_user`／`business_types` 預設）；`title` 是架標題的唯一來源；`version`／`reviewers`／
  `language` 九架必須一致。
- **一架可有多個粗目**（Plan 9.10 S1 起）：`## 標題 {#<架字母>-<slug>}`，粗目 id 首字母＝檔名字母、跨架唯一；裸字母 `{#X}` **已於 S5（2026-09-24）停用**：目錄路徑一律大聲拒絕，⛔ 無相容入口（DSP-070）。細目 `### 標題 {#jgb/<X>/<slug>}`，中段＝架字母。
- 每個細目**必填** `target_user`（非空）與 `business_types`（須含 `system_provider`）——
  兩軸是可見性的鑰匙，缺一即「b2b 永不可見／b2c 不設限」的半可見資料，故 parser 直接擋。
- **目錄只列粗目**（Plan 9.10 S2 起）：`build_canon_toc` 每個「含 ≥1 條可見已審細目」的粗目一行 `<粗目 id>｜<粗目標題>｜<可見細目數>`，⛔ 不含細目 id ⇒ 模型走**兩跳**：`kb.get("outline:<粗目 id>")` 取細目清單（`citable=False`），再 `kb.get("outline:<細目 id>")` 引用。粗目存在但零可見已審細目 ⇒ 與不存在同樣回 `NO_MATCH`（⛔ 不洩漏差異）。
  ✅ **提示詞規則已於 2026-09-23（S6）改為兩跳**（`services/agent/agent_rules.py` 兩份政策文，各有一條逐字斷言）；⏳ 真回合驗收仍未跑（需支出授權）⇒ ⛔ 未進產線。細節見 `.kiro/specs/knowledge-outline-and-intent-architecture/HANDOFF-20260923.md` §5-2。
- 同一句講法（NFKC，approved／proposed）⛔ 不得掛在兩個細目上，**跨架亦然**；
  hook `.claude/hooks/outline_gate.py::check_phrasing_unique` 以整個 `jgb/` 目錄為作用域做同值粗篩。
- 啟動只量兩把尺（9.8 DSP-059 D′，DSP-059a 調高 K 上界）：`services/agent/outline.py::OUTLINE_K_TOKEN_LIMIT`
  管「任 K=5 可引用節 token 最大和」（prospect／pm／tenant 皆 12,000），
  `OUTLINE_TOC_TOKEN_LIMIT` 管「目錄 token」（皆 8,000）；env 各自只能把上限**調小**，
  ⛔ 不能調大。⛔ 不再量該身分的整份篩選結果（未審標題節不計入任一尺）。
  單條細目 >1,500 tokens 由 `tools/canon_fine_size_lint.py` 標記（不擋、建議拆），補審前先跑。

## 審核流程（R2.9）

1. **寫入權＝PR review**：任何人可開 PR 改正本；合併需至少一位 reviewer 核可。⛔ 不直接推 main。
2. **reviewer 名進 front matter**：核可時把 reviewer 加進該架的 `reviewers: […]`（九架一致），並在被改的
   細目加 `- reviewed: {by: <reviewer>, at: YYYY-MM-DD}`；沒有 `reviewed` 的細目＝草稿：
   **在該身分的篩選結果裡只出現標題**（`text` 空、`citable=False`），`kb.get("outline:<id>")` 一律 `NO_MATCH`。
3. **講法規則**：`- phrasings:` 只收人改寫過的短主題詞；`source: traffic:*` 者 ≤20 字且不含 ≥4 位數字串
   （parser 強制）；真流量原句只在 `.claude/skills/outline-curation/raw/`（gitignored，90 天刪）。
4. **內容變更＝新 `content_sha256`**：依賴該細目的講法與測試題進待審（步 3／步 5 工具計算），⛔ 不得靜默沿用。
5. **入庫**：只有正本 commit 後，才由 `tools/canon/export_batch.py` → `import_facet_knowledge.py` 寫 DB
   （需業主授權 D1）；DB 不是來源。⚠️ **這兩支的此擴充尚未實作**（任務 7.1／7.2）——目前是設計，不是可執行的腳本。

## Review checklist（PR 模板 `.github/PULL_REQUEST_TEMPLATE.md` 同步）

- [ ] `jgb.json` 與 `jgb/CATALOG.md` 已重導出且 CI 同源測試綠
- [ ] 新增／變更細目都有 `sources`、`instance_applicability`、`target_user`、`business_types`；變更者有 `reviewed`
- [ ] 沒有講法出現在內容行（parser `phrasing_leaks` 為空）；沒有識別碼（hook／`test_pii_scan_req.py`）
- [ ] 改了細目的 `target_user` ⇒ 想清楚它會從哪個身分的篩選結果消失／出現（那是**可見性**變更，不是排版）
- [ ] **高風險 diff**：`.claude/settings.json`、`.claude/hooks/`——這兩處改動＝改閘門本身，必須第二位 reviewer，並在 PR 描述說明為何要改閘門

## 沿革

- **2026-09-15 重切（DSP-047～057）**：原本依受眾各分一份的正本改為 **9 領域粗目共用脊椎**
  （A 帳號與身分／B 團隊、人員與大房東／C 社區與物件／D 租約／E 帳務／F 修繕／G 裝置／H 幫助中心／I 方案與導入）。
  舊版封存：`docs/archive/2026-09/canon-pre-recut/`（⛔ 不是現況）。
- **2026-09-15 合併為圖書館（DSP-058）**：兩份正本合併成 `canon/jgb/` 九架一份，受眾＝細目必填屬性 `target_user`，
  各身分依 `canon_visible` 從同一份正本篩出可見細目。合併前的兩份正本封存於
  `docs/archive/2026-09/canon-pre-library/{prospect,property_manager}.{md,json}`（⛔ 不是現況，
  各 `.md` 首行已加表頭；它們已掉出 hook `CANON_RE` 掃描範圍）。
  舊→新細目 id 對照：`.claude/skills/outline-curation/runs/library-20260915/id_map.json`（53 筆，全 `keep`）。
- 現行正本 **57 粗目／515 細目／1,331 內容句**（2026-09-23 由 drafts 生成，DSP-067／068／069；drafts 側 1,327 句，差 4 句為生成時再斷句）；**515 條全未審** ⇒ 目錄為空、模型看不到任何一條，補審前不可引用（R2.9）。舊 210 條（20 已審）封存於 `docs/archive/2026-09/canon-pre-dsp067/`（2026-09-23 已移出工作樹，內容在 git `c06575a9`）。
