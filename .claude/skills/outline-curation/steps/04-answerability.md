# 步 4：answerability

**輸入**：`phrasing-map.json`。
**輸出 schema**：`../schemas/answerability.json`。
**形態**：腳本直打 Messages API（1.6；`../scripts/answerability_judge.py`）——每格 2 判者、不一致加第 3，每判者獨立請求（互不可見）、structured outputs 鎖 schema、rubric＋候選當共用快取前綴、journal jsonl 續跑；`deterministic=false`。Workflow 版（`../../../workflows/outline-curation.js`，1.4）**留參考**：8 GB 機器跑不動、且判者間不共享快取（44 格 $15.84），業主 2026-09-06 裁改。
**出口條件**：`needs_rubric_revision=false`（為 `true` 時 Stop hook 擋）；成本落在步 4 上限（≤180 代理／$3）內。

## 實作對應（1.4）

- **rubric 正本**：[`../schemas/answerability-rubric.md`](../schemas/answerability-rubric.md)（四值定義，⛔ 不寫例子；跑前凍結 sha、業主核可後才進 readiness）。
- **args 組裝**：`../scripts/answerability_args.py`——讀缺口地圖（55 格）＋21 列 prospect kb rows＋18 筆草稿＋rubric → Workflow `args` JSON（候選＝程式列舉的臨時細目集合 `tmp:kb:<id>`／`tmp:draft:<n>`，共 39 筆，kb 依 id 升冪、draft 依原序；每格 `judgePrompt`＝rubric 全文＋代表問句＋全部候選，白名單投影，⛔ 不含分數／排序／系統判定欄位）。支援 `--cell-ids` 子集乾跑。
- **判者（現行）**：`../scripts/answerability_judge.py --args <slim args> --journal <jsonl> --out <result>`——system＝`promptHead+candidatesBlock`（`cache_control`）、user＝`cellBlock+cellTail`，system+user 逐位元＝`build_judge_prompt`；Reconcile 與 JS 等價、`<0.80` ⇒ `needs_rubric_revision=true`（門檻 0.80，業主 2026-09-06 裁）。憑證：SDK 零參數解析，腳本 ⛔ 不讀 .env。
- **Workflow（參考）**：[`../../../workflows/outline-curation.js`](../../../workflows/outline-curation.js)（`step:'answerability'`）——`pipeline(cells, judge1, judge2, 不一致才 judge3)`；args >20 KB 要用 wrapper `workflow({scriptPath}, ARGS)` 委派；同 schema、同 Reconcile。
- **收尾**：`../scripts/finalize_answerability.py`——把 Workflow 回傳包成 StepEnvelope（過 `../schemas/answerability.json`）、寫 journal 檔、更新狀態檔 `answerability` 鍵；`needs_rubric_revision=true` 時仍寫檔但 exit 2。
