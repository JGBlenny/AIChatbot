# 6.3 上線 gate 放行報告（**業主已簽署**）

> 2026-08-25｜語言 zh-TW｜狀態：**APPROVED（業主簽核）**
> 簽核內容：**6.3 APPROVED；C4b NOT PASSED；production-facing gate CLOSED；可進 6.4**
> 草稿身分見 `fdc9019`；本版為簽署版（檔名去 `-draft`），內容除簽核欄位外未改。
> 撰寫本檔**未呼叫任何 OpenAI API**；所有數字與字面均取自已歸檔 evidence。
> 每一項裁決標明來源：**【業主已裁】**

```text
結論（先講）
  C4a execution-chain closure   **remains CONFIRMED**
  C4b production-brain gate     **NOT PASSED**
  production-facing gate        **CLOSED**（任務 4.6／8／9 維持不得上線）
```

---

## 1. 凍結協議與 claim 邊界

### 1.1 C4b 證什麼、不證什麼

```text
C4a  grounding 能被**送到** answer stage，且是**哪一筆**（OB-3 機器斷言 identity）
C4b  真 brain **有使用該筆 grounding 中被問到的值**
```

機器只判三件事（`c4b-ruler-v2-amendment.md` §3）：用了被問到的值／沒把明確屬於別筆的值
當本筆答案／沒退化成泛用回答。**方向語義不由機器判**。

**C4b PASS 也不可主張**：答案品質已達標／對一般問法穩健／routing 正確／上線風險已解除。

### 1.2 ruler v1 → v2：**首次付費量測前**的修訂

```text
c4b-ruler-v1  frozen but NOT executed
pre-execution audit → ruler defect confirmed（三處把非 C4b 能力寫成失敗條件）
c4b-ruler-v2  amended before first OpenAI execution
```

```text
No model output was observed before amendment.
No paid C4b call had been executed.
Amendment was based solely on ruler semantics and known C4b claim boundaries.
```

v1（`c4b-ruler-frozen.md`）**一字未改**保留。被反證的三處：要求複述帳單標題（identity
屬 C4a OB-3）／以方向性字面阻斷判紅／失敗不留回答原文。

### 1.3 凍結的執行參數

| | 第 1 輪 brain | 第 2 輪 factual 合成 |
|---|---|---|
| model | `gpt-4o` | `gpt-4o-mini` |
| temperature | 0.4 | 0.2 |
| max_tokens | 400 | 800 |

4 案 × 3 次、**三次全過才算過**（不取多數決）；名目 24 次呼叫、硬上限 30；
斷言紅**不 retry**，僅 infra 類可 retry（≤2）；jgb2 一律 `JGBMockTransport`。

⚠️ 為使 runner 與 production 同源，`docker-compose.dev.yml` 補宣告 `PRESALES_SYNTH_MODEL`
（原僅在 prod 宣告，測試容器的 brain 會落回 `gpt-4o-mini`）。

---

## 2. 第一次執行的事實（原樣，不修飾）

evidence：`evidence/c4b-first-execution.json`

| case | face | fixture | machine verdict | 實際引用字面 |
|---|---|---|---|---|
| `c4b-diag-02` | bill_diagnosis | 900001 | **3/3 PASS** | `待繳費`（三次皆命中） |
| `c4b-anom-02` | billing_anomaly | 900003 | **3/3 PASS** | `待對帳`（三次皆命中） |
| `c4b-anom-01` | billing_anomaly | 900002 | **2/3** | run1／run2：`2026/09/01` ＋ `2026/09/30`；run3：無命中 |
| `c4b-diag-01` | bill_diagnosis | 900003 | **INDETERMINATE / HARNESS_EVIDENCE_LOSS** | — |

### 2.1 `anom-01` run3 的原文（機器判 `value_not_used`）

```text
帳單編號 900002 的狀態為「已繳費」，金額為 NT$ 1,200，繳費期限是 2026 年 9 月 15 日，
計費期間為 2026 年 9 月 01 日至 2026 年 9 月 30 日。
```

v2 對該筆的可接受寫法只列 `2026/09/30`／`2026年9月30日`／`20260930`——
**帶空格、日補零**這一式未列。

### 2.2 `diag-01` 的 evidence 缺口（如實保留）

第一次執行時，harness 的 `_EVIDENCE.append` 只在 `_run_case` 正常返回後執行，
harness 斷言以 `raise` 逸出 → **該案在 evidence 裡不存在**。
這違反本輪事前定的 C 項契約（PASS／FAIL 都要留原文），已於 `75cfed7` 修補，
但**第一次執行的缺口永久存在**，不得事後補值。

### 2.3 呼叫數：兩個**不同**命題，不得混寫

```text
exact observed external_calls   **unavailable**（telemetry 缺陷，見 2.2）
estimated                        19–20（依執行結構推估）
hard-cap enforcement             **當時確實存在**——CallLedger.note() 在委派真呼叫**之前**
                                 檢查，第 31 次會在送出前 raise（見 commit 53b513c）
```

⚠️ 「無法證明精確用了幾次」≠「無法證明沒有超過 30」。

⚠️ 另一項量測揭露：spy 掛在**共用** provider 上，`call_log` 會計入其他元件的呼叫
（replay 的 5 次中有 `gpt-4o-mini@32 tokens` ×2 與 `gpt-3.5-turbo` ×1 不屬 C4b），
故上限是**保守**方向，但「呼叫數＝C4b 呼叫數」的等式不成立。

---

## 3. 6.3 人工裁決

### 3.1 `anom-01` → `ruler_false_red` → **substantive accepted**　【業主已裁】

```text
machine verdict   value_not_used（保留原樣，不修改）
human verdict     accepted / ruler_false_red
```

依據：回答已實際使用正確的 `2026-09-01 ~ 2026-09-30`；差異只在空格與日期補零的表面形式。
**不修改 ruler、不重跑**——這筆是 v2 已觀測到的 limitation，由本層 adjudicate 掉。

### 3.2 `diag-02` 的方向語義　【業主已裁】

v2 已事前縮窄：

> diag-02 machine PASS only establishes that the answer used the grounded status/value;
> it does not machine-prove the semantic correctness of the collectability conclusion.

三次回答皆為「狀態待繳費 → **可以進行收回**（退回待發送、原繳費資訊失效、重發產生新虛擬帳號）」。
對照 production contract `Bill::canCancel()`：條件為 `status ∈ {2, 32}`，
fixture 900001 的 `status = 2` → **可收回為真**。

⇒ 裁為 **human adjudication = accepted / direction correct**。

⚠️ **證據分層必須維持原樣，不得上滾**：

```text
machine-proven      grounded status/value was used
human-adjudicated   「待繳費 → 可以收回」方向正確
```

**不得**反寫成「ruler machine-proved direction correctness」——那正是 v2 amendment
之後的 claim ceiling。

### 3.3 `adjudication_flags`

四案三輪合計 **0 次命中**（`adjudication_hits` 全空）——
沒有任何一次回答落入方向性字面或別筆狀態詞的非阻斷觀測範圍。

---

## 4. `diag-01` diagnostic replay（**與第一次執行嚴格分離**）

evidence：`evidence/c4b-diag01-diagnostic-replay.json` ＋ `...-stdout.log`

### 4.1 身分與範圍

```text
身分       diagnostic replay，**不是** acceptance rerun
目的       把第一次被 harness 吃掉的**失敗層級**找回來，非再給模型一次機會
完成度     3 runs 中**只完成 run 1**——斷言紅不 retry，該案當場中止（符合凍結規則）
external_calls  **精確 5**（telemetry 修復後）
回填       **禁止**。diag-01 在第一次 6.2 的身分維持 INDETERMINATE / HARNESS_EVIDENCE_LOSS
```

### 4.2 觀測到的機制

```text
🎯 [trigger_facet_key] 'bill_diagnosis' 命中 → 直達面向
🔀 [conversational] brain 判定離題(scope=switch) → 關會話、重路由當前訊息
（落回檢索 → 分類路由再進一次面向）
🔀 [conversational] brain 判定離題(scope=switch) → 關會話、重路由當前訊息
⚠️ [conversational-diagnosis] 引擎降級 → 落回既有知識/表單處理
→ 最終回應 intent_type=None、action_type=direct_answer（通用兜底文案）
```

### 4.3 正式診斷分類（**只存在於 6.3 diagnostic taxonomy**）　【業主已裁】

**`face_exit_before_grounding`**（已由暫名升為本工作線的正式 6.3 diagnostic classification）

> Face 已成功進場，但 production brain 在 grounding 執行前以 `scope=switch`
> 判定離開該 Face，致使 grounding 未被取得、Face execution 未走到 answer stage。

**不回寫 6.2 frozen machine taxonomy。** 排除理由逐項：

```text
value_not_used     ✗ value 根本沒送到答案階段
generic_fallback   ✗ 兜底是**退出之後**的結果，不是成因
wrong_instance     ✗ 未取得任何 instance
infra              ✗ 無 timeout／rate limit／5xx
C4a plumbing 回歸  ✗ 無證據；且 C4a 用腳本化 brain，該 brain 結構上不會做此判定
```

### 4.4 兩條進場路徑**都**被同一判定退出

同一次執行內，`trigger_facet_key` 直達與其後的分類路由**各進場一次、各被判 switch 一次**。

⇒ **不得**把責任推給 `trigger_facet_key` 這個 harness shortcut。
⇒ 直達進場等價性（`c4b-entry-path-equivalence-resolved.md`）在活體上再獲一次佐證。

### 4.5 因果射程（**已簽核的三段**）

```text
SUPPORTED       真 brain 的 scope／stay-switch 行為是直接造成此次退出的 mechanism。
SUPPORTED       trigger_facet_key 不是充分原因——重新分類進場後同樣再次被 scope=switch 退出。
NOT ESTABLISHED 為什麼 brain 會判 switch。
```

### 4.6 root cause **尚未** adjudicated

`face_exit_before_grounding` 已被實例重現；**根因未定**。
至少仍有下列互斥性未排除：persona `scope` 規則本身／該 Face 的 responsibility wording／
brain 對「查某筆金額」的 applicability 判讀／stay-switch contract 的判準。

⚠️ **不得**以「scope prompt 太嚴」之類假說直接當成修法。

---

## 5. 放行決定

### 5.1 逐案結算

```text
diag-02   accepted        3/3 machine
anom-02   accepted        3/3 machine
anom-01   accepted*       2/3 machine   * 第 3 次 = ruler_false_red（6.3 裁決）
diag-01   NOT ACCEPTED
            original execution : INDETERMINATE / HARNESS_EVIDENCE_LOSS
            diagnostic replay  : run 1 = face_exit_before_grounding
                                 後續 runs 未執行（assertion red，不 retry）
```

⚠️ **不得**表述為「3/4 cases passed」——`diag-01` 第一次沒有有效 outcome，
而 replay 不是原始 acceptance rerun。合規表述為：

> **2 cases machine-confirmed 3/3; 1 case substantively accepted after a predeclared
> 6.3 ruler-false-red adjudication; 1 case remains unaccepted, with diagnostic replay
> exposing a real pre-grounding Face-exit failure.**

### 5.2 簽核（2026-08-25，業主）

| 項目 | 裁決 |
|---|---|
| `diag-02` | **ACCEPTED** — machine 3/3 ＋ human direction accepted |
| `anom-02` | **ACCEPTED** — machine 3/3 |
| `anom-01` | **ACCEPTED after 6.3 adjudication** — 原 machine `value_not_used` 保留；正式歸類 `ruler_false_red` |
| `diag-01` | **NOT ACCEPTED** — first execution 維持 `INDETERMINATE / HARNESS_EVIDENCE_LOSS`；diagnostic replay 證實 `face_exit_before_grounding` |
| C4a | **CONFIRMED** |
| C4b | **NOT PASSED** |
| production-facing gate | **CLOSED** |

### 5.3 決定　【業主已裁】

```text
C4a execution-chain closure   remains CONFIRMED
C4b production-brain gate     **NOT PASSED**
production-facing gate        **CLOSED**
  → 任務 4.6／8／9 維持「不得上線」（spec.json release_gate 不變）
  → 任務 9.4 的前置（通過 6.3 上線 gate）**未滿足**
```

### 5.4 對外表述（任務 6.4，唯一合規句）

> **執行鏈閉環已證實，最終答案能力尚未放行。**

**SHALL NOT** 表述為「最終答案能力已證實」。

### 5.5 這一輪真正的收穫

C4b 找到的不是「LLM 沒引用值」，而是腳本化 C4a **結構上看不到**的一層：

> **真 brain 可以在 grounding 之前，否決自己已經進入的 Face。**

C4a／C4b 當初拆開因此不是形式主義——C4a 只證明 grounding 能被送到 answer stage，
C4b 才驗真 brain 是否真的走完並使用它。

---

## 本檔**未**做

```text
❌ 未修改 ruler v2、未改案例／fixture／凍結參數
❌ 未回填 diag-01 的第一次結果
❌ 未對 face_exit_before_grounding 提出修法——root cause 未 adjudicated，另立工作線
❌ 簽核為 **CLOSED**，不是放行——4.6／8／9 維持不得上線
```
