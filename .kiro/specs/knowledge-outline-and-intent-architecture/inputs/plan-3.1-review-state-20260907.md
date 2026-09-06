# Plan 切片 KOIA-3.1：`review_state.py` 內容已審謂詞＋`kb.get` 接線＋migration＋不變量 32（2026-09-07）

> 狀態：**收案（2026-09-07）**：業主核准 (a)、§8.2 裁 (a)；security-executor 實作；fresh verifier **CONFIRMED**（unit 926／integration 150 綠、`make audit` PASS、32 印 SKIP(pending-D1)）。已知債 P3：PG `[[:space:]]` 不含 U+00A0／U+2007／U+202F／U+FEFF，`reviewed:\u00A0` 在 PG 可見而 Python 鏡像拒——現況無寫入者；D1／步 7 匯入工具寫入前用 `is_domain_value` 先擋。前史：三輪 plan-verifier 皆 REVISE、皆已 FIX 進本文。security-sensitive（agent 路徑可見性）：security-reviewer 唯讀分析已完成（findings 見 §7），核准後交 `security-executor`，完成後 fresh `verifier`。核准前 ⛔ 不寫碼。對應 tasks 3.1、design 元件 5／不變量 32、R2.7／R5.4／R8.4。

## 0. 結論先講

「內容已審」要有**唯一正向謂詞**：`outline_approved_by ~ REVIEWED_REGEX`（POSIX regex，與 DB CHECK 用同一字串常數，真值表必然相同）。agent 路徑的 `kb.get`（整數 id）拼上它，未審列一律 `NO_MATCH`；DB 加 CHECK 收值域；不變量 32 掃「字面只准出現在 `review_state.py`」。D1 前現況 29 列 `owner-20260905` **全部不可見**是預期，不是 bug。

## 1. 結果（outcome）

1. `rag-orchestrator/services/agent/canon/review_state.py`：`REVIEWED_PREFIX="reviewed:"`、`POOL_MARK_PREFIX="pool-marked-"`、`REVIEWED_REGEX = r"^reviewed:[^[:space:]]+$"`、`DOMAIN_REGEX = r"^(reviewed:[^[:space:]]+|pool-marked-[0-9]{8})$"`（CHECK 用）；`content_reviewed_predicate() -> (" AND kb.outline_approved_by ~ %s", [REVIEWED_REGEX])`（⚠️ 不用 `LIKE`：`_` 會吃空白，plan-verifier 第 1 輪）；`is_reviewed_value(v) -> bool`＝Python `re.fullmatch` 用**第二個常數** `REVIEWED_REGEX_PY = r"^reviewed:\S+$"`（Python 不支援 POSIX class，兩個常數並列、⛔ 不共用字串），對 §3 全表逐值與 DB 實查比對；unicode 空白（如 U+3000）兩邊可能分歧，測試把 U+3000 列入表並記錄實際結果，以 DB 為準。無 DB、無 I/O。
2. `services/agent/tools/kb.py::fetch_visible_row`：在 `{predicate_sql}` 後追加第二片段、params 同序延長；`build_visibility_predicate` ⛔ 不動（不變量 29 紅線）；⛔ 不包 try/except、⛔ 不依欄位存在與否切換（唯一會造成 fail-open 的寫法）。
3. migration `rag-orchestrator/database/migrations/20260907_outline_approved_by_domain.sql`（⚠️ 該目錄 `.gitignore:111` 已白名單，**不需 `git add -f`**，tasks 3.1 那句要改）：`ADD CONSTRAINT chk_outline_approved_by_domain CHECK (outline_approved_by IS NULL OR outline_approved_by ~ '<DOMAIN_REGEX>') NOT VALID`（字串由測試逐字比對 `review_state.DOMAIN_REGEX`；值域本身待 §8.2 業主裁）＋`DO $$` 冪等守衛；`VALIDATE CONSTRAINT` 另列為 D1 步驟（在業主 `UPDATE … 'pool-marked-20260905'` 之後）。執行由業主（D1），⛔ 我不跑。
4. 不變量 32 進 `scripts/audit/checks/agent_boundary.py`：**三態、放在 `CHECKS` 之外（沿 31 的寫法）**；新增 `_review_state_paths()` 只供 32（走 `services/agent/**`＋`tools/**`，排除 tests）；規則（**掃描範圍＝Python AST 字串常數**：`ast.Constant(str)` 與 f-string `JoinedStr` 的字面片段；docstring（函式／類別／模組 body 首個 `Expr(Constant)`）、識別字（dataclass 欄位名、kwarg、屬性）、註解一律不在範圍——理由：謂詞繞過只可能發生在**送進 DB 的 SQL 字串**）：含 `outline_approved_by` 的字串常數只准在 `services/agent/canon/review_state.py`；其他檔命中 ⇒ FAIL（**無豁免表**，業主裁 (a)）；`review_state` 使用命中（`content_reviewed_predicate`／`COLUMN` 被 import 或呼叫）<1 ⇒ FAIL（空跑不得綠）。DB 子檢查：`docker exec … psql` 查值域外列；psql 不可達 ⇒ **FAIL（不是 SKIP）**；僅當「衍生列（`generation_metadata->>'canon_ref'`）＝0 ∧ 值域外列全為 `owner-20260905`」⇒ 印 `SKIP(pending-D1)`；`self_test()` 用注入的假查詢函式跑正反例，⛔ 不連 DB。
5. 現樹掃描面內 11 處字面的逐處處置（`rg -n outline_approved_by rag-orchestrator/services/agent rag-orchestrator/tools` 實查：`outline.py` 3、`agent_outline_dump.py` 8），使「無豁免」與「真樹綠」同時成立：
   - `outline.py::_fetch_prospect_pool_rows` SQL 字串 → 改用 `content_reviewed_predicate()`（業主裁 (a)；**匯入前**大綱 0 列是預期——D1 把 29 列改成 `pool-marked-*` 後仍不可見，要到步 7 匯入寫入 `reviewed:` 才非空），加測試「0 列已審時 `build_prospect_outline` 不 raise、`_init_agent_runtime` 不紅；回傳 doc 的 `sections` 只剩固定兩節 `outline:deliberate-gaps`＋`outline:cta`、所有 section 的 `source_ids` 皆空」（⛔ 不是「空大綱」：兩個固定節無論資料多寡都會附）。
   - `outline.py` docstring 1 處＋註解 1 處 → 在掃描範圍外（改敘述以免誤導，非驗收條件）。
   - `agent_outline_dump.py`：SELECT 投影、`_UNMARK_SQL_TEMPLATE`（`UPDATE … SET outline_approved_by=NULL`）、輸出 f-string 3 處字串常數 → 改為 `from services.agent.canon.review_state import COLUMN` 以 `{COLUMN}` 組字串；docstring 3 處、dataclass 欄位名 `RowMeta.outline_approved_by`、kwarg 2 處 → 識別字／docstring，在掃描範圍外，不動。
   - 正對照（§5.5）：假樹在 `review_state.py` 外植入一個含字面的 SQL 字串常數必紅；植入 docstring 不紅（證明界定生效而非掃描壞掉）。

## 2. 現況事實（2026-09-07 實查）

- live DB：`outline_approved_by` NULL 1,019、`owner-20260905` 29、其他 0；衍生列（canon_ref）0；欄位 text（查證：`python3 -c "import sys;sys.path.insert(0,'scripts');import status;print(status.psql(\"SELECT COALESCE(outline_approved_by,'<NULL>'),count(*) FROM knowledge_base GROUP BY 1\"))"`）。
- `fetch_visible_row`（`services/agent/tools/kb.py`）：psycopg2 `%s` 綁參、`build_visibility_predicate` 片段以 f-string 拼接、params 同序——追加第二片段注入安全。
- 例外處理：`registry.py` 把工具例外一律轉 `NO_MATCH`（fail-closed）；欄位不存在 ⇒ `UndefinedColumn` ⇒ `NO_MATCH`。
- `agent_boundary.py` 在 `scripts/audit/checks/`；27／30 有「命中 0 ⇒ FAIL」先例；31 是唯一三態且在 `CHECKS` 之外；檔內無 DB 存取；同檔會在 pytest 容器內跑（無 docker）。

## 3. 值域與謂詞（單一真值表）

| 值 | CHECK（DOMAIN_REGEX） | 謂詞（REVIEWED_REGEX，可見） |
|---|---|---|
| `reviewed:owner`、`reviewed:王` | 允許 | 可見 |
| `reviewed:` | ⛔ 拒 | 不可見 |
| `reviewed: `、`reviewed: alice`、`reviewed:\tbob`（冒號後含空白） | ⛔ 拒 | 不可見 |
| `Reviewed:owner`、` reviewed:owner`、`REVIEWED:owner` | ⛔ 拒 | 不可見（regex 區分大小寫、`^…$` 錨定） |
| `pool-marked-20260905` | 允許 | **不可見**（池標記≠已審，design 元件 5） |
| `pool-marked-2026` | ⛔ 拒 | 不可見 |
| `owner-20260905`（現況 29 列） | ⛔ 拒（D1 改寫前用 NOT VALID 過關） | 不可見 |
| NULL | 允許 | 不可見 |

關係：**可見 ⊂ CHECK 允許**（允許集合＝可見 ∪ `pool-marked-<8 位>` ∪ NULL）；兩支 SQL regex 同住 `review_state.py`。

單一來源：`review_state.py` 放 `REVIEWED_REGEX`／`DOMAIN_REGEX`；migration SQL 與 `is_reviewed_value` 由測試逐字／逐值比對（drift 必紅）。

## 4. 非目標

- `kb.search` 不套（design F6 ACCEPT；未審 `question_summary` 仍可被模型讀到，由 Verifier 步②／④ 守——**不變量 32 不涵蓋此殘留**，Plan 明列）。
- `_fetch_toc_rows`（保留分類列，刻意在 29 之外）與 `make_outline_resolver` 不動——3.2 `canon_assembler` 取代整個 outline 建構。**⛔ 本片不得移除或改動 `outline:deliberate-gaps`（DSP-009）與 `outline:cta` 兩個固定節**（退役屬 3.2）。
- 不改 `build_visibility_predicate`、不調 K、不動 legacy `conversational_engine._grounding_by_ids`（不在 29／32 範圍）。
- migration 執行、`VALIDATE CONSTRAINT`、29 列改寫＝業主 D1 親跑。

## 5. 驗收（容器內；security-executor 做、fresh verifier 反證）

1. `content_reviewed_predicate()` 回恰一個 `%s`＋一個參數 `REVIEWED_REGEX`；對 §3 全表每值做 DB 實查（`SELECT %s ~ %s`）與 `is_reviewed_value` 逐值相等。
2. `fetch_visible_row` 正反例（用 DB 或 psycopg 假連線皆可，但至少一組走真 DB integration）：`reviewed:owner` 可見；§3 全部拒值 ⇒ `NO_MATCH`；**一列在 `build_visibility_predicate` 下可見但未審 ⇒ `NO_MATCH`**（證明第二謂詞在做事）；**一列已審但在池外 ⇒ `NO_MATCH`**（證明 29 沒被削弱）。
3. 現況 29 列 `owner-20260905` 在新謂詞下全部不可見（integration，正對照：同列改成 `reviewed:test` 後可見——用交易 rollback，⛔ 不留痕）。
4. migration 檔內 regex 字串 == `review_state.DOMAIN_REGEX`；對 §3 全表每值 DB 實查 `%s ~ DOMAIN_REGEX` 與表格一致；`REVIEWED_REGEX` 可見集合 ⊂ `DOMAIN_REGEX` 允許集合（含 `pool-marked-` 反例）。
5. 不變量 32 自測：真樹綠（正對照）；假樹零命中 ⇒ FAIL；假樹在 `review_state.py` 外出現字面 ⇒ FAIL；psql 不可達 ⇒ FAIL；值域外只有 `owner-20260905` 且衍生列 0 ⇒ SKIP(pending-D1)；值域外出現其他值或衍生列 ≥1 ⇒ FAIL。`make audit` 主流程把 32 的 SKIP 印成 ⚠️ 不計 FAIL（沿 31）。
6. migration：套兩次冪等；對含 `owner-20260905` 的表 `ADD … NOT VALID` 成功、`VALIDATE` 失敗（在測試 DB 交易內驗證，rollback）。
7. 0 列已審（真 DB integration）：`build_prospect_outline` 不 raise；`len(doc.sections)==2` 且 `{s.id for s in doc.sections}=={"outline:deliberate-gaps","outline:cta"}`；`all(not s.source_ids for s in doc.sections)`；`_init_agent_runtime` 不紅。正對照：交易內塞一列 `reviewed:test` ⇒ `len(doc.sections)==3` 且新增節 `source_ids` 長度 1（rollback、⛔ 不留痕）；`scripts/run-tests.sh unit tests/unit/agent/ tests/unit/_meta/`＋相關 integration 綠；`make audit` 不變量 27–31 不變、32 印 SKIP(pending-D1)。

## 6. 回滾／預算／停損

- 回滾：刪 `review_state.py`、還原 `kb.py` 兩行、刪 migration 檔（未執行則無 DB 影響）、還原 `agent_boundary.py`。
- 預算 $0；security-executor 一段；verifier REFUTED 兩次即停下回業主。
- 停損：若 `fetch_visible_row` 以外還發現 agent 路徑直讀 `knowledge_base` 且模型可達（§7 已列 `_fetch_prospect_pool_rows`），不擴大本片，列入 §8 裁決。

## 7. security-reviewer findings 處置

| # | 級 | 內容 | 處置 |
|---|---|---|---|
| F1 | P1 | `services/agent/outline.py::_fetch_prospect_pool_rows` 用 `IS NOT NULL`，把 29 列當已審餵售前大綱 | **業主裁 (a)（2026-09-07）**：本片改用謂詞，無豁免；步 7 匯入前大綱 0 列為預期 |
| F2 | P1 | `ADD CONSTRAINT` 會驗既有列，29 列違規 ⇒ ALTER 中止 | FIX：`NOT VALID`＋冪等守衛；`VALIDATE` 列為 D1 後置步驟 |
| F3 | P2 | `LIKE 'reviewed:%'` 放行空 reviewer；plan-verifier 再抓 `LIKE '_%'` 的 `_` 吃空白 | FIX：謂詞改 `~ REVIEWED_REGEX`，與 CHECK 同源 |
| F4 | P2 | 三態放進 `CHECKS` 會被 `main()` 當 FAIL | FIX：沿 31 寫法置於 `CHECKS` 外 |
| F5 | P1 | 檔內無 DB 存取；容器內無 docker，naive DB 檢查會靜默綠 | FIX：psql 不可達 ⇒ FAIL；self_test 注入假查詢 |
| F6 | P2 | `tools/agent_outline_dump.py` 唯讀 dump 的字面會被走訪紅 | FIX：掃描界定為 AST 字串常數；5 處 SQL／f-string 改 `{COLUMN}`，docstring／識別字在範圍外（§1.5） |
| F7 | — | tasks 3.1「`git add -f`」對 `database/migrations/` 不需要 | FIX：改 tasks 文字 |
| F8 | P2 | `kb.search` 殘留（ACCEPT） | 記入 Plan §4，不擋 |

## 8. 業主裁決

1. **已裁 (a)（2026-09-07）**：`outline.py::_fetch_prospect_pool_rows` 本片直接改用 `content_reviewed_predicate()`；線上 agent 路徑未運作（prod compose 僅設 `AGENT_STAGE=M0`、`AGENT_AUDIENCES`／`AGENT_TURN_ENABLED` 未開 ⇒ `_agent_configured()` 為假、fail-soft），無過渡期。
2. **已裁 (a)（2026-09-07）：值域收嚴並回寫 design**——原題：值域收嚴與 design 文字不一致（plan-verifier 第 1 輪 P2）。design 自己三處寫法不同：元件 5 程式塊寫 `REVIEWED_PREFIX="reviewed:"`＋CHECK `^(reviewed:|pool-marked-)`；決策 8 與資料模型段寫 `outline_approved_by ∈ {<reviewer>, "pool-marked-<date>"}`（無 `reviewed:` 前綴）。本 Plan 採 **`reviewed:<who>`（who 不含空白、非空）＋`pool-marked-<8 位日期>`**，比三處都嚴。選項：(a) **建議**：照本 Plan 收嚴，回寫 design 決策 8、資料模型段、元件 5 CHECK 字串＋1.4 變更歷史一行；(b) 照 design 原字面 `^(reviewed:|pool-marked-)`（會放行 `reviewed:` 空 reviewer 與任意日期形狀）。
3. `tools/agent_outline_dump.py`：已由 §1.5 界定處置（改常數＋範圍外），不需裁決。
4. migration 檔名依實際日期 `20260907_…`，tasks 3.1 的 `20260906_…` 與 `git add -f` 文字同步修正（`database/migrations/*.sql` 已在 `.gitignore:111` 白名單）。
