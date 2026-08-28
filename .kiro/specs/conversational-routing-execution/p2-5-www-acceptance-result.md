# P2.5：responsibility-routing vertical slice 在 www 完成 controlled end-to-end acceptance

- 日期：2026-08-28｜邊界：`JGB_API_BASE_URL=https://www.jgbsmart.com`、`USE_MOCK_JGB_API=false`
- 業主裁定：`preview` 的 `/contracts/status-overview` 500 降格為**獨立部署債務**，
  不再阻塞 rollout 主線；`www` 是現行正式 API boundary，P2.5 直接在此驗收。

## 安全邊界（**動 production API 之前先證明**）

```text
本 slice 的三個面向 grounding_scope 只宣告讀取端點：
  billing_anomaly   jgb_bills
  bill_diagnosis    jgb_bills ＋ secondary jgb_bill_detail
  contract_closeout jgb_contracts ＋ secondary jgb_bills
三者皆**未**宣告 prefill_api／enabled_gate ⇒ `_seed_repair_facet`（修繕路徑）不可達。
`get_bills`／`get_contracts`／`get_bill_detail` 全走 `_request` ＝ **GET**。
`_post_request` 全檔**只有一個**呼叫者：`/api/external/v1/repairs`（create_repair），
不在本 slice 的可達集合內。
⇒ 這條 vertical slice **不可能**產生寫入。
```

## 執行（真入口，兩輪，唯讀）

`POST /api/v1/message`｜`vendor_id=2`／`property_manager`／`b2b`／`role_id=20151`

```text
turn 1  「幫我查點退帳單金額」
  🧭 resolver  bill_diagnosis[switch] → billing_anomaly[switch] → contract_closeout[stay]
               → commit contract_closeout
  💬 分類命中 contract_closeout → 進診斷對話
  → 「請提供合約編號或物件名稱，以便我查詢點退帳單金額。」
  telemetry：commit_source=model｜has_commit_authority=true｜responsibility_confirmed=true
             processing_path=conversational｜answer_source=contract_closeout｜llm_calls=4

turn 2  「89557」
  → 收斂到單一合約 → www 真 API grounding → grounded final answer
  telemetry：續輪由 handle_conversational_session 接手（不重跑 resolver）｜llm_calls=1
```

## 答案對帳（⚠️ **不看話術像不像，逐項對 ground truth**）

www 唯讀取回的原始欄位：

```text
id=89557｜title=台北中正-小南門單身貴族分租套房D
status=2｜bit_status=3｜date_start=20260814｜date_end=20261113
```

| 答案裡的宣稱 | 決定性依據 | 判定 |
|---|---|---|
| 名稱「台北中正-小南門單身貴族分租套房D」 | API `title` 逐字 | ✅ |
| 狀態「已發送簽約邀請（等待租客簽名）」 | `bit_status=3` = READY(1)｜INVITING(2)；`INVITING_NEXT(4)` **未**設 | ✅ |
| 「尚不可點退，合約尚未正式生效」 | `SIGNED(8)`／`MOVE_OUT(64)` 皆未設 | ✅ |
| 「到期退租需在到期前 30 天（2026/10/14）起」 | `date_end=20261113` − 30d = **2026-10-14** | ✅ |

四項可查證宣稱全部命中，**沒有**編造欄位或狀態。

## 結論

> **responsibility-routing vertical slice 已在現行 production API boundary（www）
> 完成 controlled end-to-end acceptance。**

```text
真入口 → 真 retrieval → 真 mini brain
→ bill_diagnosis[switch] → billing_anomaly[switch] → contract_closeout[stay]
→ authoritative commit（commit_source=model／has_commit_authority=true）
→ Face 問識別碼 → 識別碼 → www 真 API grounding → 收斂單一合約
→ grounded final answer（四項事實對帳全中）
```

## 收案（2026-08-28 業主裁定 P2.5 **PASS**）

| 項目 | 狀態 |
|---|---|
| authority provenance ／ telemetry | ✅ VALIDATED |
| 刀 A precedence | ✅ VALIDATED |
| 刀 A 第 3 列 real-control-flow | ✅ CONFIRMED |
| 刀 A 第 4 列 complete lifecycle | ⚠️ PARTIAL runtime ＋ unit/M5 |
| Face entry reachability | ✅ CONFIRMED |
| `www` real API grounding | ✅ CONFIRMED |
| identifier → single contract narrowing | ✅ CONFIRMED |
| grounded final answer | ✅ CONFIRMED |
| **P2.5 controlled E2E acceptance** | **✅ PASS** |
| preview | ⚠️ independent deployment debt |

### 寫入安全的 claim 邊界（**不得擴讀**）

```text
✅ 可宣稱：本次 canary 僅可達 read-only grounding path；production write path 未被觸及。
❌ 不得擴成：整個系統不可能寫 production。
   射程只有這三個 Face（bill_diagnosis／billing_anomaly／contract_closeout）
   與本 vertical slice。
```

### 單一 89557 樣本的身分：coverage ceiling，**不是** P2.5 failure

```text
P2.5 驗的命題是「這條 vertical slice 能否從真入口一路走到真 API grounding，
並產出可對帳的答案」——一個 deterministic known case 足以證明**存在性與 causal correctness**。
它**不**證明：所有 contract lifecycle states 正確／所有 bit_status 組合正確／
所有 production contract 都能收斂。
⇒ 未來若要宣稱「contract_closeout across lifecycle states 已驗證」，
   才需要另建 state matrix。**現在不為 P2.5 再加樣本。**
```

### 刀 A 第 4 列：不是 Stage-1 blocker

```text
runtime        已證明選到 compat_face 並嘗試進場
completion     尚未由真 runtime 完整跑完（注入手法限制，非刀 A 缺陷）
deterministic  M5／unit 已鎖住「candidate 不得被丟掉」
⇒ 不得宣稱「第 4 列 E2E validated」，但它**不阻塞 Stage-1**。
```

### 驗收所用組態＝Stage-1 目標組態（實測 container runtime）

```text
PREENTRY_ROUTABILITY_GATE=true
PREENTRY_ROUTABILITY_FACETS=bill_diagnosis,billing_anomaly,contract_closeout
FACET_SCOPE_SALVAGE=false
BRAIN_STRICT_SCHEMA=true
PRESALES_SYNTH_MODEL=gpt-4o-mini
（四個 routing 旗標皆由 docker-compose.prod.yml 透傳；未透傳＝production 設了也不生效）
⇒ 本次 acceptance **不是**跑在另一組組態上。
```

## 射程外／仍未涵蓋

```text
· 只驗**讀取型**：未做建立、修改、點退送出或任何 write action（也證明了不可達）。
· 單一合約樣本（89557，bit_status=3）。其他階段（已簽約／已點交／點退中）未逐一走過。
· preview 的 /contracts/status-overview 500：獨立部署債務，見 p2-4-preview-smoke-result.md。
· 刀 A 第 4 列（相容性 Face 完成進場）仍只有 unit（M5）＋「分支選擇」的 runtime 證據，
  見 routing-authority-model/face-precedence-causal-validation.md。
```
