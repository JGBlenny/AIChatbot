# review_pipeline：細目「修正 → 先審 → 業主終審 → 寫入已審」工具組（Plan 9.16～9.19 定型）

> 從 Plan 9.19 的 scratchpad 版本複製而來，存這裡是為了跨 session 保存。
> ⚠️ 這些是**範本**，不能原地使用：每份計畫都要先把它們複製到當次的 scratchpad，改寫檔頭的變更值（前綴、commit、架、hold、PLAN 路徑），並在開工前預跑正負對照。
> 工具讀寫的**中間資料檔**（targets／batches／raw／results／hold／decision／approved）都放在 `SP = dirname(__file__)`，也就是工具自己所在的目錄。
> ⚠️ **預設直接寫 repo**：`edit_fine.py` 改的是 repo 的 `runs/outline-20260920/drafts-*.json`（預跑時設 `P919_RUNS=<scratch 目錄>`）；`approve_write.py write` 改的是 repo 的 `rag-orchestrator/canon`（預跑時加 `--canon <scratch 目錄>`）。drafts 與正本都在 git 版控中，寫壞了救得回來。

## 前置：jgb2 釘住匯出（先審與核對的唯一程式來源）

```
mkdir -p <SP>/jgb2-b2ee2ac && git -C /Users/chenqinghuang/dev/work/jgb2/dev1 archive b2ee2ac382ce | tar -x -C <SP>/jgb2-b2ee2ac
```

- 這是 jgb2 master `b2ee2ac382ce` 的匯出，約 210M。
- ⛔ 代理直接讀 `/Users/chenqinghuang/dev/work/jgb2/`，一律讀匯出。

## 工具（原名 → 此處檔名）

| 檔名 | 原名 | 用途 | 要改的變更值 |
|---|---|---|---|
| `extract_verdict.py` | p916_s3_extract.py | 從代理 transcript（`tasks/<agentId>.output`）機械取出最後一份含 `jgb/…｜` 行的結論，逐字存成 raw 檔 | 無（用法：`extract_verdict.py <transcript> <raw.txt>`） |
| `edit_fine.py` | p919_edit.py | 改 drafts 單條細目：set／delete／insert_after（可用 `-1`）、add/remove_sources、phrasings、evidence_add；**同步位移 evidence 句序**。環境變數 `ALLOWED=<allowed.json 路徑>` **必填**，只准改允許集合內的細目；`P919_RUNS` 可覆寫 drafts 目錄 | `TRAIL`（各架檔尾換行，實測）、roundtrip 架清單 |
| `drafts_diff.py` | p919_s1_drafts_diff.py | drafts 改前改後機械比對 (a)～(g)：修正紀錄對帳、允許集合外 0 改動、結構、evidence 越界 | `P919_DIFF_SHELVES` |
| `canon_check.py` | p919_s1_canon_check.py | 檢查重生成後的正本區塊差異只在允許集合內；掃描客戶名（`(?<!系)統上`…`愛租屋`，命中即失敗）。「系統上」只印出次數、不會讓程式失敗，須人工確認次數是否與改前相同 | 客戶名詞表：⚠️ 目前是手列的，每次都要依記憶 `feedback_knowledge_authoring_style` 第 9 點，從程式的特殊團隊定義系統性重抽，並為每個詞備好正、負對照 |
| `review_sheet.py` | p919_s2_sheet.py | parse（raw → results，缺 id、多 id、格式錯一律大聲失敗）／sheet（產生審核單，含 `[hold]`）／check（raw、results、審核單三方對帳，加上覆蓋守門） | `CANON_COMMIT`、`SHELVES`（環境變數 `P919_SHELVES` 可覆寫）、`PREFIX`、標題、hold 檔 |
| `approve_write.py` | p919_approved.py | derive：業主原文 → 四欄決定檔 → 以審核單與 results 兩個來源各推一次，結果相同才寫，並排除 hold。write：只加 reviewed 行，預設寫 repo 正本，可用 `--canon` 改寫到別處。verify：須在**重匯出之後**跑；`--backup` 必填；檢查已審集合、其他架的位元組、jgb.json 只動了 `reviewed_*` | results／targets／hold 路徑、PLAN；環境變數 `P918_WRITE_SHELVES`（必填）、`P918_SHEET`（derive 用）、`P918_PLAN_SECTION`（預設 `### S3`） |
| `grepcheck.py` | p919_grepcheck.py | 以「路徑\t字串」清單批次 grep 釘住匯出（證據確認用） | 無 |

## 範本

- `templates/brief-prereview.txt`：先審 verifier brief（9.19 S2 版）。含：
  - 只放一份結論、逐條對照清單；
  - `doc:` 來源與衝突規則；
  - 講法要答得到、走不到的情境判 doubt、同粗目含不在本批者一併比對。
- `templates/brief-fix-verify.txt`：修正核對 verifier brief（9.19 S1 版）。

## 流程要點（細節與踩過的坑見 HANDOFF §12 與各計畫 §5／§6）

1. **改寫**：用 `edit_fine.py` → 產生修正紀錄 → 分包交 fresh verifier 核對 → 依 D1 規則修一次、再核 → `drafts_diff.py` 須 PASS → 生成器先在 scratch 試跑、再對 repo 跑 → `canon_check.py`。
2. **先審**：分批（粗目不拆、≤35 條、一次一位代理）→ `extract_verdict.py` → `review_sheet.py parse/sheet/check`（附兩個正對照）。
3. **終審**，依序：
   1. 業主原文逐字記入計畫 §6「### S3」，並寫成四欄決定檔。
   2. `approve_write.py derive`。
   3. **寫入前**：把 `rag-orchestrator/canon/` 備份到 scratch，以 `diff -r` 確認相同；確認 git 基準為空；在同一工作樹跑全套單元，把紅燈 id 集合存成基準。跑 H 留出題守護 `python3 scripts/audit/checks/goal_eval_holdout_guard.py`（主機；目標驗收規格 2026-10-04 §2.4），非 0 ⇒ ⛔ 寫入；寫入後第 8 步的 `make audit` 會對新正本再跑一次。
   4. `approve_write.py write`。
   5. 容器重匯出：
      `docker compose -f docker-compose.dev.yml run --rm -T --no-deps rag-orchestrator python -c "from services.agent.canon.canon_parser import parse_canon_dir, export_json, export_catalog; from services.agent.canon.canon_assembler import load_canon_or_die; d=parse_canon_dir('/app/canon/jgb'); export_json(d,'/app/canon/jgb.json'); export_catalog(d,'/app/canon/jgb/CATALOG.md'); load_canon_or_die('/app/canon')"`
   6. `approve_write.py verify --backup <備份>`。
   7. 重生成保留檢查：只在 scratch 跑，用 `--front-matter-from`／`--canon-root`／`--runs-out` 指到 scratch；⛔ 對 repo 跑。
   8. 紅燈與基準比對，差集須為 ∅；`make audit`；fresh outcome verifier。

   寫入後任一項不符，就用已驗證的備份還原。但先查新紅燈是不是**測試取樣綁了正本資料**（見 HANDOFF §12-3），再決定。
