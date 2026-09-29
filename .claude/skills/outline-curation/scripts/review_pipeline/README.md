# review_pipeline：細目「修正 → 先審 → 業主終審 → 寫入已審」工具組（Plan 9.16～9.19 定型）

> 從 Plan 9.19 的 scratchpad 版本複製而來，存這裡是為了跨 session 保存。
> ⚠️ 這些是**範本**，不能原地使用：每份計畫都要先把它們複製到當次的 scratchpad，改寫檔頭的變更值（前綴、commit、架、hold、PLAN 路徑），並在開工前預跑正負對照。
> 工具讀寫的資料檔都放在 `SP = dirname(__file__)`，也就是它自己所在的目錄。

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
| `edit_fine.py` | p919_edit.py | 改 drafts 單條細目（set／delete／insert_after 可含 `-1`、add/remove_sources、phrasings、evidence_add），**同步位移 evidence 句序**；限定 `ALLOWED=` 允許集合 | `TRAIL`（各架檔尾換行，實測）、roundtrip 架清單 |
| `drafts_diff.py` | p919_s1_drafts_diff.py | drafts 改前改後機械比對 (a)～(g)：修正紀錄對帳、允許集合外 0 改動、結構、evidence 越界 | `P919_DIFF_SHELVES` |
| `canon_check.py` | p919_s1_canon_check.py | 重生成後的正本區塊差異只限允許集合；客戶名掃描（`(?<!系)統上`…`愛租屋`）；「系統上」負對照 | 客戶名用詞表 |
| `review_sheet.py` | p919_s2_sheet.py | parse（raw → results，缺 id／多 id／格式錯一律大聲失敗）／sheet（產審核單，含 `[hold]`）／check（raw↔results↔審核單三段對帳＋覆蓋守門） | `CANON_COMMIT`、`SHELVES`、`PREFIX`、標題、hold 檔 |
| `approve_write.py` | p919_approved.py | derive（業主原文 → 四欄決定檔 → 審核單與 results 兩來源推導，相同才寫；排除 hold）／write（只加 reviewed 行）／verify（已審集合、其他架位元組、jgb.json 只動 reviewed_*） | results／targets／hold 路徑、PLAN、`P918_WRITE_SHELVES`、`P918_SHEET` |
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
3. **終審**：業主原文逐字記錄 → `approve_write.py derive/write/verify` → 容器重匯出 → scratch 重生成保留檢查 → 寫入前量的紅燈基準比對差集＝∅ → `make audit` → fresh outcome verifier。
