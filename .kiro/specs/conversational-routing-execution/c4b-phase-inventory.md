# 6.x（C4b／上線 gate）phase-boundary inventory

> 2026-08-24｜語言 zh-TW｜**盤點，非執行**。未跑 6.1／6.2／6.3，未呼叫 OpenAI。
> 全文搜過：`6.1`／`6.2`／`6.3`／`C4b`／`production-brain`／`OpenAI`／`e2e`／`cost`／`budget`／
> `release`／`放行`／`不得上線`／`REFUTED`／`REJECTED`／`verifier`／`revert`／`業主裁示`／`known-red`。

## 逐項盤點

| | 6.1 | 6.2 | 6.3 | 6.4 |
|---|---|---|---|---|
| **task** | 定義 `BrainGroundingAssertion` ／ `assert_brain_uses_grounding` | 兩面向 C4b e2e 測試（真 `conversational_step`、少量案例） | 執行 C4b 並產出**上線 gate 放行報告** | 報告紀律落實 |
| **marker** | 🧠主 | ⚡F | 🧠主 **🔍V** | 🧠主 |
| **status** | 未做 | 未做 | 未做 | 未做 |
| **later history** | **無** | **無** | **無** | **無** |
| **external side effect** | 無 | **真 OpenAI ＋ 真 DB** | 同 6.2 | 無 |
| **cost frozen?** | — | ❌ **未凍結** | — | — |
| **ruler frozen?** | 形狀已定、內容未定 | 依賴 6.1 | 依賴 6.2 | — |

⚠️ **後段歷史查核結果：6.x 完全乾淨**——沒有任何 REFUTED／REJECTED／revert／verifier 裁定。
唯一相關的業主裁示是 **design.md 的 Req.3.2 歸屬定案（2026-08-23）**，且它是**現行有效**的設計裁示，
不是對 6.x 的反證（見下）。

---

## purpose：C4b 到底證哪一層

```text
C4a  production execution plumbing 能把 grounding **送到** answer stage   ← 已 PASS（5.5）
C4b  真 brain 會**使用** grounding 作答
```

⚠️ design 明文：**C4b 的驗證對象不是「檢索是否命中」**（那是 Requirement 2 的事）。

| | C4a | C4b |
|---|---|---|
| 層級 | integration | **e2e** |
| brain | 腳本化（零 OpenAI） | **真 `conversational_step`（真 LLM）** |
| jgb2 | `JGBMockTransport` | **同左**（資料仍須決定性） |
| 斷言到 | `grounding` 字串 | **最終回答文字** |
| 擋 CI | ✅ | ❌（e2e 預設略過） |

⚠️ **與既有 e2e 慣例不同**：`tests/e2e/conversational/test_billing_facets_e2e_req.py` 打的是
**真 jgb2 preview**；**C4b 必須改用 `JGBMockTransport`**，否則資料不決定性、斷言無效。

---

## ⚠️ 執行前必須先凍結的四件事（6.2 會真的花錢）

### ① model／config **未凍結**

```text
requirements 7.2   「WHEN e2e 層需真實 LLM，THEN 其規模 SHALL 受控並於文件標明預期成本量級」
design            「規模與成本量級須標明（R7.2）」
tasks 6.2         「於檔頭標明預期成本量級」
```

**三處皆為義務，無一處給出實際值**：model、temperature、prompt、tool availability
**全部未凍結** → 若看到結果後可改，6.2 的 evidence 很弱。

### ② 執行次數與成本上限 **未明定**

repo 內查無以下任一項的凍結值：

```text
cases = ?          runs_per_case = ?      model = ?
max total calls = ?    budget = ?         retry policy = ?
```

⚠️ **不得「跑到綠為止」**——重跑策略必須事前寫死。

### ③ 失敗分類 **未定義**

真 LLM 的紅有多種來源，**不得**全部算成同一種：

```text
OpenAI timeout ／ rate limit ／ tool error   ← 基礎設施
grounding 不足                              ← 應已被 C4a 擋掉（本輪 PASS）
回答未引用該筆實際值 ／ 退回泛用 KB 答案      ← 這才是 C4b 要測的
```

### ④ skip semantics：**「沒跑」不得看起來像「綠」**

```text
pytest.ini    e2e: 經 /api/v1/message 或 SSE，需整服務（CI 標示略過）
run-tests.sh  e2e 層需 RUN_E2E=1；未設即不執行
```

⚠️ 故 **`make test-unit` 全綠與 C4b 是否通過完全無關**。
6.2 的 evidence **MUST** 記錄：

```text
executed_cases = N      skipped_cases = 0      external_calls = N
```

**不得**只貼 pytest summary。

---

## release dependency：**無循環依賴**（本次盤點最重要的結論之一）

```text
design.md：放行點＝**元件 4 的完成報告**，逐面向列出 C4b 的斷言結果與實際引用字面
```

C4b 跑在 **branch e2e**（真 LLM ＋ mock jgb2 ＋ 真 DB），**不需要** production 已放行的資料。故：

```text
✅ 實際形狀   branch implementation ＋ frozen e2e evidence ＋ verifier evidence ＋ known limitations
              → 6.3 owner adjudication → release permission
❌ 不存在     release 後才取得 release 前必要 evidence 的循環
```

### gate 覆蓋範圍：兩份文件用**不同名稱指同三項**（已對帳，非矛盾）

```text
design.md  元件 3 mock 分支位置 ／ 元件 6 `FACET_SCOPE_SALVAGE` ／ 元件 8 `repair_create` 觸發知識
tasks.md   任務 4.6            ／ 任務 8（`FACET_SCOPE_SALVAGE` 於 tasks.md:859）／ 任務 9
```

⚠️ 逐項對得上；**易誤讀為兩份清單不一致**，故在此記錄對帳結果。
另注意 tasks 9.4 明訂：**通過 9.3 且通過 6.3 的上線 gate 後，始得上線**。

## authority：放行人與輸出格式**已有明確紀錄**

```text
放行人      **業主**（人工放行；**不得由測試綠燈自動視為放行**）
輸出格式    元件 4 的完成報告——**逐面向**列出 C4b 的斷言結果與**實際引用字面**
CI 阻擋     ❌ 否（C4b 用真 LLM，非決定性，不進 CI 阻擋路徑）
R3.4 降級   ❌ 否（維持「只看 C4a」）
```

---

## ⚠️ 一個尚未解除的**供裝前置條件**（會直接決定 6.2 的成本量級）

design 的「收窄候選」明文**未結論**：

```text
若能經 Step 0.4 `trigger_facet_key` 直達面向進場（production 既有路徑，非 harness 捏造），
供裝需求可由「完整 KB ＋ embedding」降為「面向配置 ＋ 系統脈絡 ＋ 規則」。

⚠️ 但 `handle_trigger_facet` 現行一律走 `_seed_repair_facet`，
   而 chat.py 的分類路由出口對「未宣告 enabled_gate／prefill_api 的診斷面向」
   走的是 `_conversational_respond`——**兩條路徑是否等價，須讀碼或實跑確認**。
   確認前，C4b 的供裝以「完整 KB ＋ embedding」估算，**不得先按樂觀值排任務**。
```

⇒ **這是 6.2 的前置工作**，且它**不需要呼叫 OpenAI** 即可完成（讀碼或以腳本化 brain 實跑）。

## claim ceiling（C4b 尚未執行，先寫下）

```text
✅ C4b PASS 可說：真 brain 在**少量 predeclared 案例**上**使用**了 grounding 作答
❌ 不可說：答案品質已達標／對一般問法穩健／routing 正確／整體上線風險已解除
⚠️ 現況（C4a 過、C4b 未跑）的**唯一合規表述**（tasks 6.4）：
   「執行鏈閉環已證實，**最終答案能力尚未放行**」
   SHALL NOT 表述為「最終答案能力已證實」。
```

---

## 建議順序（**待裁定，本檔不預選**）

```text
① 先解除供裝前置（讀碼／腳本化實跑確認 trigger_facet_key 路徑等價性）  ← 零 OpenAI 成本
② 6.1 定 ruler（含逐案 answer_must_contain／answer_must_not_contain）  ← 零 OpenAI 成本
③ **凍結** model／config／cases／runs／budget／retry／失敗分類          ← 零 OpenAI 成本
④ 才執行 6.2（真 OpenAI），並記錄 executed／skipped／external_calls
⑤ 6.3 人工放行（🔍V）
⑥ 6.4 報告紀律
```

⚠️ ①～③ **全部不需要花錢**；把它們做完再開 6.2，是本次盤點的主要結論。

---

## 修正記錄（2026-08-25）：上節的供裝前置**已解除**

上節「一個尚未解除的供裝前置條件」記為未確認，屬**盤點帳面落後**——
任務 2.5／2.4 早已各留一支測試鎖住程式側與配置側前提。
查證結果（含 DB 實查與兩支測試重跑，`skipped=0`）另立一檔，**不改寫上節原文**：

→ `c4b-entry-path-equivalence-resolved.md`

結論：等價成立，供裝可降級；但等價**限** `bill_diagnosis`／`billing_anomaly`、
**限**兩者未宣告 `enabled_gate`／`prefill_api`，且「不需 KB／embedding」的說法**須加限定**（見該檔）。
