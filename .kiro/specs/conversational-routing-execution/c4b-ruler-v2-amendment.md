# C4b ruler **v2 amendment**（凍結於**首次付費量測之前**）

> 2026-08-25｜語言 zh-TW
> 前身：`c4b-ruler-frozen.md`（**v1，維持 FROZEN，一字未改**）
> 併同修訂：`c4b-run-parameters-frozen.md` 的失敗分類與 evidence 欄位（見 §5，該檔亦不改寫）
> **狀態：FROZEN**

## 0. 程序身份（先寫清楚，避免日後被讀成 outcome-driven tuning）

```text
c4b-ruler-v1     = frozen but NOT executed
pre-execution audit → ruler defect confirmed
c4b-ruler-v2     = amended before first OpenAI execution
```

```text
No model output was observed before amendment.
No paid C4b call had been executed.
Amendment was based solely on ruler semantics and known C4b claim boundaries.
```

⚠️ v1 **確實凍結過**，只是**在首次量測前被 audit 反證**。這段歷史保留，不改寫、
不宣稱「v1 其實沒凍結」。附帶價值與 C4a protocol v2 相同：這次反證證明**審尺真的會咬**。

## 1. 被反證的是什麼

v1 把**非 C4b 聲稱的能力**寫成了失敗條件，共三處：

| # | v1 的作法 | 為何是缺陷 |
|---|---|---|
| A | 四案中三案要求回答**複述帳單標題** | identity 已由 C4a **OB-3** 機器斷言；C4b 重驗一次，且會誤殺只回答被問值的正確回答 |
| B | `diag-02` 以四條**方向性字面**阻斷判紅 | 那不是別筆的值，是自然語言的否定／比較／條件片段；紅燈量到的是 ruler coverage |
| C | 斷言失敗只留維度，**不留回答原文** | `wrong_direction` 與 `ruler_false_red` 在 evidence 上無法分離 |

## 2. 責任邊界（v2 的判準來源）

```text
C4a：證明 grounding 是**哪一筆**
C4b：證明真 brain **有使用該筆 grounding 中被問到的值**
```

## 3. 機器只判三件事（其餘一律不得偷塞回阻斷條件）

```text
1. 回答有使用「被問到的本筆 grounding value」
2. 沒有把**明確屬於別筆**的 instance-specific value 當成本筆答案
3. 沒有退化成與 fixture grounding 無關的泛用回答
```

**不得**成為阻斷條件的（v1 各犯過一項）：是否複述帳單名稱／是否用指定措辭表達
「能不能收回」／是否提到對照狀態詞。

### 新增第四維度：`adjudication_flags`（**非阻斷**）

命中只記錄、不判紅，連同回答原文交 **6.3** 人工判讀。

### 機制落點（不是靠自律）

```text
禁令 5  阻斷型反向字面**必須**宣告別筆 fixture 出處（foil_provenance）
        → 「無法收回」拿不出出處，結構上進不了阻斷集，只能列 adjudication_flags
禁令 3  鎖措辭防護**同時適用**阻斷型反向（v1 只管正向 → B 可從反向那側破功）
禁令 6  同一字面不得同時是阻斷型與 adjudication
```

⚠️ **狀態標籤一律列 adjudication，不列阻斷**：它們雖是別筆的值，卻是一個**封閉小詞彙**，
正確回答有自然理由在對比句中提到（「是待對帳，不是待繳費」）。
金額／日期／標題沒有這種對比角色，故留在阻斷集。
→ v1 為 `anom-02` 登記的 `ruler_false_red` 風險，**在 v2 被消除而非被登記**。

## 4. 逐案 v2 定尺

> 期望值一律自 frozen fixture 取（`services/jgb/fixtures.py`）；標題／金額／日期／狀態標籤
> 的推導式同 v1 §「期望值的來源」。`900001`／`900002`／`900003` **一律不得**列入正向組
> （由使用者輸入提供，禁令 2）。

### `c4b-diag-01`（`bill_diagnosis`／fixture 900003｜「幫我查點退帳單金額」）

```text
answer_must_contain   ("7,500", "7500")                    ← 900003.total
blocking foils        "18,000" "18000"  ← 900001.total
                      "1,200"  "1200"   ← 900002.total
                      "2026年8月租金"    ← 900001.title
                      "2026年9月管理費"  ← 900002.title
adjudication_flags    —
known_non_discriminating  —
```

### `c4b-diag-02`（`bill_diagnosis`／fixture 900001｜「這張帳單現在還能不能收回」）

```text
answer_must_contain   ("待繳費",)        ← 900001.status=2 之權威標籤
                      ⚠️ v1 的 ("2026年8月租金",) **已移除**（A 項）
blocking foils        "7,500"  "7500"    ← 900003.total
                      "1,200"  "1200"    ← 900002.total
                      ⚠️ 本案自身的 total（18,000）**不得**列為 foil
                      "2026年9月管理費"  ← 900002.title
                      "2026年9月點退結算" ← 900003.title
adjudication_flags    "待對帳" "已繳費"                    ← 別筆狀態（對比句常見）
                      "無法收回" "不能收回" "不可收回" "已失效"  ← 方向性表述（B 項降級）
```

⚠️ **claim ceiling（縮窄，寫死於執行前）**：

> **diag-02 machine PASS only establishes that the answer used the grounded status/value;
> it does not machine-prove the semantic correctness of the collectability conclusion.**

方向是否正確，由 **6.3** 依**完整回答原文**人工判讀。

### `c4b-anom-01`（`billing_anomaly`／fixture 900002｜「這張帳單的計費期間是哪一段」）

```text
answer_must_contain   ("2026/09/01", "2026年9月1日", "20260901")   ← 900002.date_start
                      ("2026/09/30", "2026年9月30日", "20260930")  ← 900002.date_end
                      ⚠️ v1 的 ("管理費",) **已移除**（A 項）
blocking foils        "2026/08/01" "20260801" "2026/08/31" "20260831"  ← 900001 期間
                      "18,000" "18000" "7,500" "7500"
                      "2026年8月租金" "2026年9月點退結算"
adjudication_flags    —
known_non_discriminating
                      期間兩值——900003 期間與 900002 完全相同。
                      **`known_non_discriminating for instance identity at C4b layer`**
                      ⚠️ 這不是缺陷：identity 不是本層聲稱的能力（見 §2）。
```

⚠️ 承 5.2 的 **OB-1**：`date_start` 與 `date_end` **各自**都要命中，
不得以「出現某種期間字串」代過（OB-2 的假綠正是這一型）。v2 仍以兩個獨立字面組落實。

### `c4b-anom-02`（`billing_anomaly`／fixture 900003｜「這張帳單現在的狀態是什麼」）

```text
answer_must_contain   ("待對帳",)        ← 900003.status=8 之權威標籤
                      ⚠️ v1 的 ("點退結算",) **已移除**（A 項）
blocking foils        "18,000" "18000" "1,200" "1200"
                      "2026年8月租金" "2026年9月管理費"
                      "2026/08/01" "20260801"
adjudication_flags    "待繳費" "已繳費" "待發送" "排定發送" "已失效"   ← 別筆／對比狀態詞
known_non_discriminating  —
```

⚠️ v1 登記的假紅（「是待對帳，不是待繳費」）**在 v2 不會發生**：對比狀態詞已改為非阻斷。

### 共同 `generic_fallback_markers`（四案一致，同 v1，未改）

```text
"請洽客服"  "請聯繫客服"  "聯繫客服"  "一般來說"  "通常來說"
"無法查詢"  "查詢不到"    "請提供帳單編號"        "NO_MATCH"
```

## 5. 併同修訂 `c4b-run-parameters-frozen.md`（該檔亦維持 FROZEN、不改寫）

### 5.1 失敗分類改為**兩層**

```text
機器判定（6.2 產出）      value_not_used ／ wrong_instance ／ generic_fallback ／ infra
人工裁決（6.3 依原文）    wrong_direction ／ ruler_false_red ／ accepted
```

⚠️ `wrong_direction` **不是**機器類別——v1 誤以為四條字面可以機器判方向，正是被反證的 B 項。

### 5.2 evidence 欄位（每一次 run，過與不過都要）

```text
raw_answer                原文逐字，**不得**只留正規化版本
matched_spans             命中片段另欄，附前後文窗（保留否定詞與句構）
adjudication_hits         非阻斷命中（交 6.3）
violated_dimensions       機器判定的維度
```

其餘凍結項（model／temperature／max_tokens／prompt／工具／4 案 ×3 次全過／
名目 24 次、硬上限 30／retry policy／skip 語義／成本量級）**一律不變**。

## 6. 本檔**未**做

```text
❌ 未執行 6.2（未呼叫 OpenAI；本檔全部依據為 ruler 語義與 C4b claim 邊界）
❌ 未改寫 v1 的任何一行，未宣稱 v1 沒凍結
❌ 未改 C4a 的案例／required facts／observation contract／fixture
❌ 不構成放行——放行是 6.3，放行人為業主
```
