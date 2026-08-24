# Carrier comparison：A／B／C × 五軸

> 2026-08-24｜語言 zh-TW｜依 `carrier-comparison-ruler-frozen.md`（凍結於比較之前，`fa2dbb3`）執行
> 同一份 frozen Contract（`responsibility-authority-contract.md`，APPROVED／FROZEN）。
> **本輪不評實作成本、不選 winner、不邊比邊新增概念救方案。**

## 判定

```text
A  Central responsibility authority                 **INSUFFICIENT_EVIDENCE**
B  Face declaration ＋ independent enforcer          **REJECTED**（X-2／X-5 FAIL）
C  Capability-bound authority                        **INSUFFICIENT_EVIDENCE**

→ **ADMISSIBLE = 0**  → 落在 ruler 事前寫定的**結局 3**
```

⚠️ 結局 3 是**允許且有價值**的結果，非失敗。且**未**為了避開它而放寬任何一軸。

## 本輪最重要的發現：**X-1 不是 carrier shape 能回答的問題**

```text
三個 shape 在 X-1 全部拿不到 PASS，且原因同一個：
**它們提供的是 authority 的「位置」，不是 authority 的「來源」。**

A 提供一個放置點        （registry）
B 提供一個宣告端＋執行端 （Face 宣告＋enforcer）
C 提供一個機械 join      （capability × runtime facts）

沒有一個 shape **自己**回答「這條 responsibility 事實憑什麼成立」。
```

> **推論：X-1 由「誰有資格制定 responsibility 事實」決定，
> 而不是由「該事實存放在哪裡」決定。**
> 這正是 R6 所說的 first-class responsibility authority——
> 它是**制度性來源**，carrier 只是承載它。

---

## A — Central responsibility authority

### X-1 Authority origin → **INSUFFICIENT_EVIDENCE**

```text
claim      registry 可作為 responsibility 事實的 carrier
evidence   R-e discovery（63351cd）已證：audited surface 內沒有可導出的 facts → Face 映射
           → registry 內的每一列**沒有上游可搬**，只能由某人寫下
           → 若寫下者是產品人工填表／Face RULES 搬移／現行 categories 重寫
             → 觸發 ruler 的 standing failure 或 G-e
falsifier  若能指名一個**獨立於 Face、且非本 registry 自己創造**的 authoritative origin
           （其輸出由 registry 承載）→ X-1 可轉 PASS
```

⚠️ 依執行紀律，該 origin 目前是 **required but undefined dependency**——
**不當場設計它來救 A**，故判 INSUFFICIENT_EVIDENCE，非 PASS 也非 FAIL。

### X-2 Enrollment → **INSUFFICIENT_EVIDENCE**

```text
claim      registry 天然可表達「無列 → unknown」
evidence   ✅ **已滿足的子項**：M-4 要求的 default-unknown 在 registry 形態下**機器可判**
             （查無列即 unknown，不需任何額外約定）——這是 A 的實質優勢
           ❌ **未滿足**：ruler 要求 X-2 回答「由誰核可」，該問題與 X-1 同源、目前無答案
falsifier  若核可者與核可程序被獨立界定 → X-2 可轉 PASS
```

### X-3 Machine enforcement → **PASS**

```text
claim      registry verdict 可接上 pre-entry consumer，並具反事實效果
evidence   ① `_top1_relevance_gate` 證明本系統存在**真的會擋**的 consumer（Q2：0 放行錯位）
           ② B5 precedent：宣告＋consumer 強制（缺 session key → 禁打 API）可實作
           ③ Q1 已指出現行 Face Hint 在唯一 veto **之前** early-return
             → 需新增 pre-entry consumer；這是接線工作，**非 shape 缺陷**
falsifier  若該 consumer 只能 log 而 entry 照舊（R2 §2.2 形式滿足）→ X-3 FAIL
```

### X-4 Unknown fidelity → **INSUFFICIENT_EVIDENCE**

```text
claim      tri-state 可沿路保真
evidence   ⚠️ registry 形態有**固有的 miss 語義風險**：lookup miss 極易被讀成
             「no match → 不適用」，而非「unknown」
           ⚠️ 現行堆疊已有**實存的 unknown-loss point**：
             · N1 的 404 合併「不存在」與「無權存取」（BillApiController@show:230）
             · `face_bill_response` 無 builder／無資料列 → 回 `None` → 呼叫端走原路
               （services/jgb/bills.py:285-300）——unknown 靜默變成「本面向不處理」
falsifier  若能逐點列出 unknown-loss points 與各點 guard → X-4 可轉 PASS
```

### X-5 New-Face correctness → **PASS**

```text
claim      新增 Face 不會自動取得 authority；且既有 Face 的 verdict 不被動改變
evidence   ① 無列 → unknown 由建構保證（同 X-2 子項），符合 M-4 acceptance
           ② 逐 Face 一列 → 新增不改動既有列
           ③ G-a 的退化（兩列覆蓋同一區域）在集中式表達下**可靜態檢出**
             （與 Contract 的 contract-space auditability 同源）
falsifier  若 registry 允許萬用列／繼承／預設值，使新 Face 自動落入既有列 → X-5 FAIL
```

**A disposition：INSUFFICIENT_EVIDENCE**（X-1／X-2／X-4 未定；X-3／X-5 PASS）

---

## B — Face declaration ＋ independent enforcer

### X-1 Authority origin → **INSUFFICIENT_EVIDENCE（circularity 已記錄）**

```text
claim      外部 enforcer 使 Face 宣告取得 authority
evidence   ⚠️ **循環**：enforcer 要能**拒絕不合法的 responsibility 宣告**，
             必須先握有一個 facts → Face 的判準；
             而 R-e discovery 已證該判準**不存在且導不出**（63351cd）
           → 若 enforcer 只檢查形式（欄位齊備、值域合法），則本 shape ＝
             **self-attestation ＋ machine enforcement**，G-d 明文禁止
           ⚠️ B5 precedent **只能**證明 wiring 可實作，
             **不能**為 responsibility declaration 提供 correctness authority
falsifier  若存在一個**不由 Face 提供**的 admissibility standard → X-1 可轉 PASS
           ⚠️ 但該 standard 一旦被制定，**它本身就是 authority**，
             Face 宣告退化為消費端便利 → **B 退化成 A**（ruler 允許此結果）
```

### X-2 Enrollment → **FAIL**

```text
claim      Face 宣告即完成 enrollment
evidence   ❌ 決定性：面向設定是**後台資料列、零改程式**
             （services/conversational_config.py:15；G1 已據此判 Face 集合 open-world）
           → 在 B 之下，新增一列即自我 enrollment，**無外部核可**
           → 直接違反 ruler X-2「MUST NOT 依賴『新增 Face 時記得寫對』」
             與 RE5／R4 已 CONFIRMED 的制度失敗形態
falsifier  若 enrollment 由獨立 gate 核可 → X-2 可轉 PASS；但同上，那會使 B 退化成 A
```

### X-3 Machine enforcement → **PASS**

```text
claim      宣告可被 consumer 強制
evidence   B5：`{session.<key>}` 缺值 → **禁打 API、誠實降級**
           （services/conversational_engine.py:886-891）——阻斷而非提醒
falsifier  同 A 的 X-3
```

### X-4 Unknown fidelity → **INSUFFICIENT_EVIDENCE**

```text
claim      同 A
evidence   與 A 相同的 loss points；另因宣告驅動路徑普遍以 `None` 表示「不適用本面向」
           （bills.py:285-300），unknown 與 not-handled 在型別上**不可區分**
falsifier  同 A
```

### X-5 New-Face correctness → **FAIL**

```text
claim      新 Face 完成宣告即可 route
evidence   ❌ 正中 ruler 的 X-5 反例：「新 Face 加進 DB 就自然能 route → FAIL」
             ——即使它零改程式非常方便（**方便不是本軸的判準**）
           ❌ 且無機器手段判定該 enrollment 是否**符合** authority contract
             （X-1 的循環使「符合」無標準可判）
falsifier  同 X-2
```

**B disposition：REJECTED**（X-2、X-5 FAIL）

---

## C — Capability-bound authority

### X-1 Authority origin → **INSUFFICIENT_EVIDENCE（degeneration 已記錄）**

```text
claim      Face 與 machine-enforced capability 綁定，runtime facts 與 capability 需求機械 join
evidence   ✅ **左半邊確實是 authoritative**：平台的 resource／action 權限**真的會擋**
             （ExternalApiAuth:69-82，無權即 403）
           ❌ **右半邊沒有來源**：平台**根本沒有 Face 概念**（63351cd 實證：jgb2 命中 0）
           → `Face ↔ capability` 這條 binding 必須在對話層被**寫下**：
               寫在集中表   → **退化成 A**
               由 Face 宣告 → **退化成 B**
               寫在程式碼   → 仍是人為宣告，authority origin 未解（見下）
falsifier  若能指出一個**平台側或其他 runtime authority 已存在**的 Face-side 綁定 → X-1 可轉 PASS
           ⚠️ 本輪未找到，且 R-e discovery 已在凍結範圍內查過
```

⚠️ 「C 退化成 A／B」是 ruler 明文允許的合法比較結果，**不強行維持三者互斥**。

### X-2 Enrollment → **INSUFFICIENT_EVIDENCE**

```text
claim      新 Face 透過取得 capability 綁定完成 enrollment
evidence   ⚠️ 綁定的核可者＝X-1 未解的同一個問題
           ⚠️ 若採「寫在程式碼」變體：enrollment 天然由部署流程把關（新 Face 無綁定 → unknown），
             此子項**可滿足**；但其 authority origin 仍是人為宣告，未解
falsifier  同 X-1
```

### X-3 Machine enforcement → **PASS**

```text
claim      capability 檢查具反事實效果
evidence   平台側 403 是**已存在的真實阻斷**（ExternalApiAuth:69-82）
⚠️ 但注意：該權限對**每個 query 恆定**（inventory 已以 N4 判 E3 不成立）
   → 它能 enforce「能不能呼叫」，**不能** enforce「哪個 Face 有責任」
   → X-3 的 PASS **只涵蓋 enforcement 機制存在**，不涵蓋它 enforce 的是正確的東西
falsifier  若最終 enforce 的仍是 per-key 恆定權限而非 per-query 責任 → 對 G-a 無效
```

### X-4 Unknown fidelity → **INSUFFICIENT_EVIDENCE**

```text
evidence   ⚠️ capability 檢查天然是**二值**（403／通過）；
             把二值結果併入三值 algebra 時，「無權」極易被折成 not_applicable，
             但依 Contract 它可能只是 PREREQUISITE=false 或 unknown（視 role 指派，M-5 為關係性）
falsifier  若能逐點界定二值 → 三值的映射與 guard → X-4 可轉 PASS
```

### X-5 New-Face correctness → **INSUFFICIENT_EVIDENCE**

```text
evidence   ⚠️ 取決於 X-1 的變體：程式碼變體對本軸有利（無綁定 → unknown、部署把關）；
             集中表／Face 宣告變體則分別繼承 A／B 的結論
           ⚠️ 另有未解問題：新增 Face 後，兩個 Face 對映到**同一組 capability** 時，
             G-a（同一 instance proof 下能區別候選 Face）是否仍成立——本輪無證據
falsifier  同上
```

**C disposition：INSUFFICIENT_EVIDENCE**（X-3 PASS 但範圍受限；其餘未定）

---

## Required but undefined dependencies（**記錄，未設計**）

依執行紀律，比較過程中若某 carrier 需要一個尚未定義的概念，**不當場設計它來救該 carrier**：

```text
authority owner                 誰有資格制定 responsibility 事實          → A／B／C 皆需
enrollment approver             誰核可一個 Face 的 binding                → A／C 需
independent admissibility standard  enforcer 憑什麼拒絕不合法宣告          → B 需（且具循環性）
capability certification        Face ↔ capability 綁定的權威依據          → C 需
```

⚠️ 以上四者**皆未由 frozen Contract 或既有 production authority 支持**，
故一律計為 `INSUFFICIENT_EVIDENCE`，**不得**因「補一層就能過」而改判。

## 跨 carrier 的共同結論

```text
① X-1 三者皆未 PASS，且原因同一：shape 提供位置，不提供來源
② X-3 三者皆 PASS —— **enforcement 從來不是本案的瓶頸**
   （`_top1_relevance_gate` 會擋、B5 會擋、平台 403 會擋）
③ X-4 三者皆未定，且現行堆疊有**實存**的 unknown-loss point（404 合併語義、None 回退）
④ 唯一determinate 的 FAIL 集中在 B 的 X-2／X-5：
   「後台加一列即自我 enrollment」正中 ruler 寫死的反例
```

> **本輪第一次可以回答的問題**：
> R6 所要求的 first-class responsibility authority，**其困難不在承載形態，也不在強制手段**，
> 而在**制定權**——誰有資格宣告「Face X 對這類 query 負責」，且該宣告不是自述、不是分類、
> 不是未背書的判斷。

## 本輪**未**做

```text
❌ 未評實作成本／遷移成本／維護性（依 ruler，非本輪判準）
❌ 未選 winner（且本輪無 ADMISSIBLE 可選）
❌ 未設計 schema／migration／實作計畫
❌ 未新增任何概念來救任一 carrier
❌ 未改已凍結的 Contract 語義（比較過程中未發現需要改的地方）
❌ 未改 family disposition；未開 member；D2 仍 deferred
❌ 未動 production；未產測資；ruler 0.058928 仍凍結未用
```
