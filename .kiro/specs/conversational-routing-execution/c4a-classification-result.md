# 5.5：C4a 執行與判型結果

> 2026-08-24｜語言 zh-TW｜依 `design.md` §「C4a 失敗判型」的 **frozen (a)/(b)/(c) 流程**判讀
> 凍結輸入：案例 `451c0d2`｜尺 `1dbf94c`｜執行證據 `e927769`（5.3）、`57269f4`（5.4）
> ⚠️ **本任務不修任何東西**（見文末「本輪未做」）。

## 判定

```text
四案皆抵達 frozen 流程圖的 **PASS 節點** → **C4a PASS**
(a) 鏈路未跑通        0/4
(b) mock 契約不保真   0/4
(c) grounding insufficiency  0/4
```

**⇒ 不觸發 Req.3.4 降級**（降級由 (a) 或 (c) 觸發；本輪兩者皆為 0）。

⚠️ **未新增第四種結果**：`PASS` 本來就是 frozen 流程圖的終點節點之一，
非為容納實測而新設；三種失敗型的定義亦一字未改。

---

## 判型依據＝**execution evidence**，不是測試總數

⚠️ `10 passed` 只是驗收摘要，**不是**判型依據。逐案的判型事實如下
（皆取自 5.3／5.4 的真 DB 執行，非從最終文字推得）：

| 案例 | ①API 呼叫且收斂單筆 | ②送達性 | ③充分性 | ④OB-3 fixture identity | ⑤secondary dispatch |
|---|---|---|---|---|---|
| `c4a-diag-01` | ✅ | ✅ `7,500` | ✅ `{amount_due}` | ✅ `{900003}` | **> 0**（期望 true） |
| `c4a-diag-02` | ✅ | ✅ `2026年8月租金` | ✅ `{cancel_determination}` | ✅ `{900001}` | **> 0**（期望 true） |
| `c4a-anom-01` | ✅ | ✅ **兩個來源值**（OB-1） | ✅ `{billing_period}` | ✅ `{900002}` | **= 0**（期望 false） |
| `c4a-anom-02` | ✅ | ✅ `待對帳` | ✅ `{bill_status}` | ✅ `{900003}` | **= 0**（期望 false） |

### 流程圖逐節點對照

```text
A「API 有被呼叫且收斂到單筆？」        → 是（四案的 transport 請求皆有紀錄且收斂單筆）
A「回傳形狀非預期？」（→(b)）          → 否（mock 依 4.5 契約回應，無形狀例外）
B「grounding_must_contain 全部命中？」 → 是（含 anom-01 的兩個來源值）
C「required_grounding_facts 全部存在？」→ 是（四案的 frozen required set 皆 ⊆ observed）
→ **PASS**
```

## 對照 invariant（本輪最重要的結構證據）

```text
diagnosis frozen cases   secondary dispatch > 0
anomaly   frozen cases   secondary dispatch = 0
```

⚠️ 該差異由 `execute_api_call` 的**派發次數**證明，**不是**由「`bill_detail` 有沒有被呼叫」推得——
後者在兩個面向**都成立**（anomaly 的 adapter 數字分支同樣會打一次 detail）。
> ⇒ 可據此宣稱：**chain closure 不依賴 `secondary_call` 才能成立。**

## 量尺會咬的反證（皆為 PASS 的必要背景）

```text
充分性反證   移除該案 required key → 紅（diagnosis 與 anomaly 各一）
OB-3 反證    期望綁到另一筆 fixture → 不相符（constant-record falsifier 有效）
OB-2 反證    抽掉 start／end 之一 → 紅；且**前置斷言證明** label 仍在、
             observer 仍觀測到 `billing_period` → 紅來自 **delivery**，非 observation 失效
```

⚠️ 若無這三組反證，「四案全綠」無法排除「尺根本不會紅」。

---

## ⚠️ 本次 PASS 的射程（**寫窄，不得升格**）

```text
✅ 只證明：4 個 protocol-frozen C4a cases
          × scope = numeric_bill_ref
          × execution_face ∈ {bill_diagnosis, billing_anomaly}
          的執行鏈閉環

❌ 非數字 bill_ref 分支已證（`get_contracts` 未遷移）
❌ 一般自然語言問法已穩健（本組為 protocol-frozen design/acceptance cohort，
   **非** blind／generalization evidence）
❌ routing ownership 正確（case inclusion 明令不得作此證據）
❌ 整個 adapter 已 closure
❌ 最終答案能力已證（C4a 只證 grounding 送達與充分；答案能力屬 C4b／6.3）
```

### ⚠️ `(c) = 0/4` 的正確讀法（verifier A-1，納入正式 claim ceiling）

> **在四個事前 admission 成功的 C4a cases 中，0/4 落入 (c)。
> 本 cohort 的 admission 本身已排除了三個「現有 contract／fixture 無法 ground」的案例，
> 因此此結果 SHALL NOT 用來估計或排除 (c) 在更廣問題空間中的發生率。**

排除案例的 provenance（`c4a-case-admission-record.md`，`2721e85`）：

```text
2 cases  External 有 `details`，但 frozen fixture 未建模   → fixture 缺口
1 case   receipt amount 不在 External projection 的 33 欄  → contract capability 缺口
```

⚠️ 這不是削弱實驗，而是把 **selection boundary 說對**：
case admission **有咬**，所以 `(c)=0` 本來就只對 **admitted cohort** 成立。
⚠️ 結構上的理由：被錄取四案的 required key 全部落在 frozen 33 欄投影內，
且兩個 observer 在鏈路成功時恆定輸出各自四鍵 → required 永遠是其子集。
**故 (c) 維度在本 cohort 內無鑑別力。**

### ⚠️ `(b) = 0/4` 的正確讀法（verifier A-2，納入正式 claim ceiling）

```text
✅ 被 machine evidence 支持
   四案在 mock execution path 上未因 response shape ／ consumer incompatibility
   產生 observable execution failure

❌ **未**被支持
   mock contract == real API contract
```

> **本 C4a cohort 未觀察到 consumer-path contract-shape failure；
> C4a 本身 SHALL NOT 用於驗證 mock↔real API fidelity——後者由
> 元件 5（Real API Contract Smoke）負責。**

⚠️ `(b)=0/4` 可保留為**本 cohort 的 observed disposition**，
但**不得**拿來證明 real-contract fidelity。
否則 4.x 建得再 production-shaped，仍會把「看起來像真 API」誤寫成「已證明等同真 API」。

## 併同記錄的既有限制（非本輪引入）

```text
· **diagnosis 臂**每次收斂呼叫 detail 端點**兩次**（adapter numeric lookup 一次 ＋ `secondary_call` 一次）；
  **anomaly 臂只有 adapter lookup 一次**——既有行為
  ⚠️ 原文誤寫為「每次收斂被呼叫兩次」（未區分兩臂），已更正（verifier A-3）
· fixture 未建模 `details`／`pay_info`／`cvs_info`；`role_id` 不做 owner 圈定；
  `user_id` 過濾未實作（4.5 已列 known-unmodelled）
· 被 admission 排除的三筆維持 `NOT_ADMITTED_TO_CURRENT_C4A_COHORT`
  （兩筆屬 fixture 缺口、一筆屬 External 契約能力缺口）
```

## 本輪**未**做（5.5 不准修東西）

```text
❌ 未修改 4.6／formatter／fixture／case／required facts／harness semantics
❌ 未重新解釋 (a)/(b)/(c)，未新增第四種結果
❌ 未因判型結果調整任何斷言
❌ 未執行 6.x；4.6 仍為 **implemented ✅／verified ✅／released ❌**（6.3 人工放行前禁止上線）
```

## 登記為 debt（**本輪不改 code／tests**）

```text
D-A4  diagnosis 臂的送達性 expected literals 目前為**手抄常數**
      （"7,500"／"2026年8月租金"／"待對帳"），anomaly 臂則自 frozen fixture ＋
      production renderer 取值 → **兩臂紀律不一致、diag 側形成第二 truth source**。
      → later: diagnosis expected delivery values should be derived from frozen fixture ／
        production renderer where semantically applicable.
      ⚠️ 現在改屬 test implementation change，須重跑相關驗收並重新取得 fresh verifier coverage。

D-A5  「收斂到單筆」目前由 **combined execution evidence** 推得
      （converge kind ＋ grounding 標頭單筆 ＋ detail id 集合 == 該案 fixture），
      **無** standalone `row_count == 1` 斷言。
      → 故本檔 SHALL NOT 宣稱「顯式證明單筆收斂」；
        single-record convergence is currently **inferred**, not independently asserted.
```

---

## 獨立驗證（🔍V）

```text
Verifier result: **CONFIRMED**（fresh verifier，2026-08-24）
covered bytes:   commit `8968986`（本檔之**修正前**版本）
```

驗證方式（摘要）：不採 `10 passed`，另注入臨時 probe 印出每案 grounding／observed keys／
transport detail ids／`execute_api_call` 派發序列，逐節點重建流程圖判斷；
並實做三組**對抗破壞**——翻轉 anomaly dispatch 期望為 `>0`（3 failed）、
OB-3 改綁他筆 fixture（1 failed）、充分性 drop key（紅）——
證明既有反證測試非恆真。改動已還原、工作樹乾淨；
`git show --stat 8968986` 確認只動兩個 spec 檔，frozen artifacts 與 `tests/support/` 未被更動。

### ⚠️ Post-verifier owner adjudication（**不冒充 fresh verifier coverage**）

```text
provenance   verifier advisories A-1 ／ A-2 ／ A-3
changes      - narrowed claim ceiling（(c) 與 (b) 的正確讀法，見上）
             - corrected factual wording（detail 呼叫次數分兩臂）
             - registered debt D-A4 ／ D-A5
implementation / test bytes   **UNCHANGED**
判型輸入 ／ test oracle        **UNCHANGED**
```

⚠️ **本次文字修正未經該 verifier 覆核**——它 CONFIRMED 的是修正前的 bytes。
因判型輸入、implementation 與 test oracle 皆未更動，**不重跑完整 verifier**；
但**不得**書寫成「新措辭亦經 verifier CONFIRMED」。

```text
implementation evidence  → verifier covered ✅
test behavior            → verifier covered ✅
原判型（PASS／不降級）    → verifier CONFIRMED ✅
修正後的文字射程          → post-verifier owner adjudication（本節）
```

---

## 封口後的有效結論（**唯一可對外引用的措辭**）

> **四個 protocol-frozen、admitted、numeric-bill-ref C4a cases 的 execution chain closure 成立；
> 這不排除 admission 外的 grounding-capability failure，
> 也不構成 mock↔real API contract fidelity 證明。**
