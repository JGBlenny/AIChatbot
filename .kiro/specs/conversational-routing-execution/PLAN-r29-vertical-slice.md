> ✅ **已完成並封存（2026-09-01）**——R-29 authority handoff 三輪走通（commit 6382c93）。
> ⛔ **責任架構就此停止橫向擴張**，⛔ 不接 R-28／R-31／其餘 27 條。
> ⚠️ 現行主線計畫是 `PLAN-retrieval-coverage.md`（v2），⛔ 不是本檔。

# PLAN：R-29 facet → responsibility commit vertical slice

> 狀態：**APPROVED（2026-09-01）**，D2 經業主改寫。⛔ S2 前須先完成 R2 packaging。
> 依據：F-C26（FACET MAY IMPLEMENT, BUT MAY NOT OWN）＋ `_production_path_ruling_2026_09_01`
> 診斷來源：`_r29_slice_readonly_diagnostics_2026_09_01`（Q1/Q2/Q3 ＋ 負對照 PASS）

---

## 1. 目標與驗收（業主已定，⛔ 不改）

```text
同一 session 兩輪
  turn 1「這張帳單的收據金額多少」→ facet routing → nominate R-29 → commit R-29 → 收 bill ref
  turn 2「759304」            → resume SAME R-29 → receipt.actual_amount.v1 → FINAL_TEXT

證據
  billing_anomaly grounding direct-answer call count = 0
  R-29 binding execution call count = 1
```

## 2. 範圍

```text
IN   R-29 一條 vertical wiring：nomination → commit → responsibility session → resume → execute
OUT  ⛔ 24 個 proposed bindings   ⛔ 補 4640 answer   ⛔ 改 routing threshold
     ⛔ 註冊任何新 binding        ⛔ 動 registry-v2   ⛔ 動 R10P 已封存產物
     ⛔ push／deploy（SEC-01 仍 OPEN）
```

## 3. 現況（實測，非推斷）

```text
上游 已在線   facet routing → resolver → commit facet（PREENTRY_ROUTABILITY_GATE=true）
中段 未接線   responsibility_collapse 整個模組            production 呼叫者 0
              build_responsibility_session()              production 呼叫者 0
下游 已在線   form_manager._complete_form（authority dispatcher，讀 session_authority_mode）
              → complete_responsibility_form → _resolve_input → fr.execute
              → FINAL_TEXT ／ GROUNDING_FACTS→present()
runtime DB    session_authority_mode／responsibility_id／fulfillment_binding_id／
              input_contract_id 四欄皆存在且 nullable（T4-B2 已套用）
```

## 4. ⚠️ 一個 UX 可見的架構後果（必須先知道再批）

responsibility 路徑掛在 **form transport**（`form_sessions` ＋ `_complete_form`），
⛔ **不是** conversational engine。所以 R-29 一旦改走 responsibility：

```text
現況（facet）  turn 1 由 LLM 生成追問句：「請提供帳單編號或合約編號/物件名稱…」
改後（resp.）  turn 1 由 **form schema 的 prompt** 產生追問句
```

⇒ 追問語氣會從「模型即時生成」變成「表單欄位提示」。這是 T4 設計的必然結果
（`complete_responsibility_form` 簽名刻意不收 user_question／face／category，
no-reroute 由結構保證），⛔ 不是缺陷，但**使用者感受得到**。

---

## 5. 需要業主逐項裁定（⛔ 未裁不動工）

### D1 nomination 插入點

```text
建議：chat.py 內、facet 進場判定「同一位置」，且在 `_drop_empty_answer_rows` **之前**
理由：Q1 實測 4640 為過濾前 top-1；過濾只影響單發答題候選
```
裁定：`[ ] 採建議` `[ ] 其他：__________`

### D2 同輪多個具 binding 的 nomination 如何選

```text
實測：同一輪 nominated = ['R-29'(rows=[4640], vec 0.887), 'R-31'(rows=[4657], vec 0.559)]
選項
  a) 取 select_nominated 既有排序的第一名（keyword 桶優先，其次 vector 分數遞減）
  b) 僅當 top-1 nomination 與 top-1 retrieval row 同源時才 commit，否則不 commit
  c) 有 >1 個具 binding 的 nomination 時一律不 commit（保守，落回 legacy facet）
建議：**b**——與既有「面向進場靠 top-1 分類」的裁定一致，且天然排除同分亂序風險
```
裁定：`[ ] a` `[ ] b（建議）` `[ ] c` `[ ] 其他：__________`

### D3 committed facet 與 responsibility 是否需一致

```text
實測衝突：resolver commit `billing_anomaly`；registry-v2 中 R-29 的 facet=null，
          owner_contract 僅 prose 提及 `bill_diagnosis`
選項
  a) 不設約束——nomination 本就 facet-independent（select_nominated 不吃 facet）
  b) 設約束並以 registry 的 owner_contract 為準（需先把 prose 落成 machine 欄位）
  c) 設約束並以 resolver 實際 commit 的 facet 為準
建議：**a（本刀）＋ 另案處理 b**——本刀不引入未經審查的 facet↔responsibility 約束；
      但把「registry facet 欄位為 null」列為獨立待辦，⛔ 不在此刀順手填
```
裁定：`[ ] a（建議）` `[ ] b` `[ ] c` `[ ] 其他：__________`

### D4 `legacy_facet` 這一輪要不要導入

```text
現況：VALID_MODES = ('legacy_row','responsibility')；`legacy_facet` 非合法值
      導入須同時改 responsibility_session.VALID_MODES ＋ form_manager 接受清單
      （現行未知值一律大聲失敗，該設計是防 authority 靜默降級，⛔ 不可繞過）
選項
  a) 本刀導入：facet 路徑寫 session_authority_mode='legacy_facet'
  b) 本刀不導入：facet 路徑維持 NULL（現行語義即 legacy），另案處理
建議：**b**——本刀只證 R-29 一條線；改動 2042 列現存 session 的語義屬另一個風險面，
      且 Track B 標記在沒有第二條線之前無實際消費者
```
裁定：`[ ] a` `[ ] b（建議）` `[ ] 其他：__________`

### D5 commit R-29 後，facet 對話引擎是否完全略過

```text
F-C26 對 Track A 的要求：responsibility commit ⇒ 必須走 binding，⛔ facet 不得搶答
建議：commit R-29 時**不進** `_enter_diagnosis_facet`，直接建 responsibility session
      （這正是驗收條件「billing_anomaly direct-answer call count = 0」的實作面）
```
裁定：`[ ] 採建議` `[ ] 其他：__________`

---

## 6. 實作切片（批准後才動；每片可獨立回復）

```text
S1 讀取路徑接線（無行為改變）
   在 chat.py 進場判定處載入 registry-v2 mapping 並呼叫 select_nominated
   ⚠️ 只計算與記錄（telemetry），⛔ 不改變任何回應
   驗收：既有 baseline oracle 無 NEW_REGRESSION；日誌可見 nomination 結果

S2 commit 與 session 建立
   nomination 通過 D2 規則且該 responsibility 有已註冊 binding
   → build_responsibility_session(...) → 持久化到 form_sessions
   ⚠️ 僅對 R-29 生效（allowlist），⛔ 不對其他 responsibility 生效
   驗收：turn 1 建出 session_authority_mode='responsibility' 的列

S3 turn 2 resume 驗證
   form transport → _complete_form → complete_responsibility_form
   → bill.by_ref.v1 → receipt.actual_amount.v1 → FINAL_TEXT
   驗收：D1-R1 Stage 1 已證的同一條鏈，這次由真入口驅動

S4 驗收證據
   call counts：billing_anomaly direct-answer = 0 ／ R-29 binding execution = 1
   ground truth 逐項對帳（⚠️ 重抓，⛔ 不沿用 2026-08-31 快照）
```

## 7. 回復

```text
S1/S2 皆由單一 allowlist 常數控制（僅 R-29）——移除即完全回到現況
⛔ 不新增 migration、⛔ 不改既有 2042 列
DB 層：新建的 responsibility session 列可直接刪除，無 schema 變更
```

## 8. 風險與已知限制

```text
R1 追問語氣改變（§4）——UX 可見，需業主接受
R2 registry-v2 mapping 的載入方式未定（檔案 vs DB）；本刀若走檔案讀取，
   部署面需確認該檔在容器內可得 ⚠️ 目前容器內**沒有**該檔（本輪是手動 docker cp 進去的）
R3 baseline oracle 只覆蓋 103 個 integration case，⛔ 不保證涵蓋 R-29 路徑
R4 SEC-01／PUB-01 仍 OPEN ⇒ 本刀完成後仍 ⛔ 不得 push
```

## 9. 完成後可以宣稱什麼／不可以宣稱什麼

```text
可以   R-29 的 production-shaped responsibility fulfillment = 第一次成立
       ⇒ 才有資格開始討論 R-29 的 APPROVED_CAPABILITY
⛔ 不可 其他 29 筆的任何 verdict 變化
⛔ 不可 RESPONSIBILITY_AUTHORITY 全面 CONFIRMED（只證了一條線）
⛔ 不可 EXTERNAL_VALIDATION 對其餘 9 筆的解除
```


---

# 附錄 A：業主批准與 D2 改寫（2026-09-01）

```text
D1 YES —— nomination 插在 pre-drop rows 取得後、_drop_empty_answer_rows 之前
D2 **改寫**（⛔ 不採原建議 b）
D3 YES —— 本刀不設 facet-responsibility 約束
          FACET_RESPONSIBILITY_COMPATIBILITY_CONTRACT = NOT_ESTABLISHED（另案）
D4 YES —— ⛔ 不導入 legacy_facet persisted mode
D5 YES —— commit 成功後完全 bypass facet answer
R2 **裁定**：Registry V2 仍是 authority source，⛔ 不改由 DB 供應 mapping
```

## D2（業主改寫版，取代原建議）

```text
⛔ 不得用「top-1 nomination 必須與 top-1 retrieval row 同源」決定 authority
   —— 那等於把 row relevance score 升格成 semantic authority，繞過已完成的 C2 canonical scoring

正式規則
  pre-drop rows → row→responsibility mapping → collapse
  → canonical responsibility semantic scoring → single semantic winner

順序鐵則
  先選 semantic winner → 再看 winner 是否有 registered binding
  ⛔ 不得先只留有 binding 的 responsibilities 再選
```

## R2（業主裁定）：sealed artifacts 必須進 image

```text
⛔ 不得 fallback DB mapping、⛔ 不得 fallback row id 猜 responsibility
required artifacts（S1 實測確認）
  registry-v2.json                       sha256 2071b7f5c8cca5d9…（＝交接檔封存值）
  derived/canonical-embeddings.json      sha256 75dab05d1392dc81…（30 筆／dim 1536）
  derived/canonical-embeddings-manifest.json  sha256 224bf80641df3b0f…
fail-loud guard（必須實作）
  artifact 缺漏          → hard fail responsibility path
  registry digest 不符    → hard fail
  embedding/registry epoch 不符 → hard fail
⚠️ S2 production behavior change 前，container 必須在 **clean recreate 後自然取得** artifact，
   ⛔ 不得再靠 docker cp。
```

## fail-open 政策（業主追加）

```text
artifact missing／mapping malformed／canonical scorer failure
⛔ 第一版不得靜默當成「沒有 responsibility winner」讓 facet 繼續回答
   —— 那會讓新架構壞掉時完全看不見
至少對已啟用 migration allowlist 的 R-29 slice：必須有明確 telemetry/error
user-facing 是否允許 legacy fail-open 另列 policy，但**測試不得把它算成功**
```

## S2 allowlist 的合法邊界（業主明示）

```text
allowlist 只能控制「winner == R-29 → 是否啟用 responsibility handoff」
⛔ 不得先過濾成 allowlisted responsibilities 再選 winner
例：semantic winner = R-31 且 R-29 在 allowlist
    ⇒ 結果必須是 legacy facet path，⛔ 不得偷偷改選 R-29
```

## S4 追加驗收（業主）

```text
session round-trip DB persistence = CONFIRMED
⛔ 不得只在同一 process memory 內完成兩輪
```

---

# 附錄 B：S1 關鍵 acceptance —— **已於接線前唯讀證成（PASS）**

```text
執行日 2026-09-01｜⛔ 本次零程式碼變更｜artifacts 以 docker cp 暫置（S2 前須改為進 image）

① PRE-DROP ROWS   [(4640,0.739), (4657,0.559), (3407,0.619), (4637,0.604)]
② NOMINATED       ['R-29','R-31']            ← 真實 production-shaped 競爭集合
③ CANONICAL SCORING（VECTOR_WEIGHT 0.1／RERANK_WEIGHT 0.9）
     R-29  final=0.9619  vec=0.6222  rerank=0.9996
     R-31  final=0.8305  vec=0.5499  rerank=0.8616
   canonical_winner = **R-29**

SET_IS_R29_R31 = True｜WINNER_IS_R29 = True｜VERDICT = **PASS**
```

## 量尺鑑別力對照（⚠️ 沒有這一步，上面的 PASS 不可採信）

```text
query「我要查這張帳單的收據實際收了多少錢」 → winner R-29 ✅ [R-29=0.9619 R-31=0.8305]
query「這份合約的點退帳單金額是多少」       → winner R-31 ✅ [R-29=0.4096 R-31=0.9547]
SCORER_IS_DISCRIMINATING = True
⇒ 尺會隨語義翻轉，R-29 勝出**不是**「永遠選提名分高者」的假象

canonical text（registry-v2 逐字）
  R-29 查詢特定收據的實際收款金額。
  R-31 依指定合約找出其點退帳單，並查詢該筆點退帳單的實際金額與目前狀態。
```

## S1 尚未完成的部分

```text
[ ] chat.py telemetry-only 接線（behavior change = 0／session write = 0）
[ ] R2 packaging：三個 artifact 進 image ＋ fail-loud guard
[ ] baseline oracle 回歸確認（Baseline Epoch 1 集合式判準，⛔ 不看總數）
```
