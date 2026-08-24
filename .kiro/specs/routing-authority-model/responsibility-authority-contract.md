# Responsibility Authority Contract（設計層第一步：**先定語義，再比 carrier**）

> 2026-08-24｜語言 zh-TW｜業主裁定：封口 R-e discovery；下一步**不是**再掃 source、
> 也**不是**直接做 D1／D3 member，而是**先定義 first-class Responsibility Authority Contract**。
> 前置：`r6-derived-design-constraint.md`｜`re-mapping-discovery-result.md`（`63351cd`）
> **狀態：APPROVED ／ FROZEN（業主 2026-08-24）。M-1～M-5 全部 CLOSED。**
> R6 APPROVED。**Carrier comparison NOT STARTED**——比較前須先凍結 comparison ruler。
> ⚠️ 本檔凍結後，A／B／C 三個 carrier **MUST 吃同一套 input／evidence roles／composition
> algebra／三值語義**；它們能競爭的只剩 authority 從哪來、如何 enrollment、如何 machine-enforce、
> Face 新增時 correctness 如何持續成立。

## 0. 兩種 authority 必須先分開（寫在首頁，防 carrier 比較時混掉）

```text
Responsibility Authority   回答：「Face X 對這次 query 是否有責任依據？」
Final Routing Authority    回答：「在所有候選與其他 routing constraints 下，最後進哪裡？」
```

由此推出四條關係（**與 R2／R3 對齊**）：

```text
applicable      ≠  must enter
not_applicable  ⇒  candidate X **MUST NOT** irreversibly enter
unknown         ≠  applicable
unknown         ≠  not_applicable
```

⚠️ 本 Contract 治的是**前者**。**Responsibility Authority 不得自我膨脹成完整 router。**

## 為何先定 contract，而不是先選 carrier

避免這個常見倒序：

```text
❌ 先新增 responsibility_registry → 再倒推它應該放什麼
✅ 先定「新 authority 必須是什麼」 → 再比較誰來承載
```

⚠️ 本檔**不選 carrier**、**不設計 schema**、**不開任何 member**。

---

## 1. Contract semantics

### Input

```text
- candidate Face                     （被審對象；語義見 M-2）
- qualified runtime proofs           （N1／N2／N3 類；已於 1f077f6 通過 E1–E6）
- query-derived structured evidence  （僅限通過 M-3 admissibility 者；本輪尚未證成任何一項）
```

#### M-2｜candidate proposal 是 **non-evidentiary input**（must-fix）

Contract 需要 `candidate Face` 才知道**正在審誰**，但「它為什麼成為 candidate」
**MUST NOT** 回流成 applicability evidence：

```text
similarity／category 提出 Face X
        ↓
Responsibility Authority 審 Face X       ← Face X 在此**只是被審對象**
```

```text
❌ 不得因「retrieval 已經選到 X」而增加 applicable 的證據權重
❌ 不得因「LLM switch 選到 X」而增加證據權重
❌ 不得因「Face 自己說自己是 X」而增加證據權重
```

⚠️ 沒有這條隔離，B2（category→Face）／B3（LLM→Face）只是**換路徑被洗回 authority**。
G-d／G-e 接近這件事，但本條直接寫進 **input semantics**，不只依賴 gate。

#### M-3｜query-derived evidence 的 admissibility（must-fix）

原稿「必要的 query-derived evidence」**太寬**，會成為新後門：

```text
LLM(query) → 「這像 billing_anomaly」  → 叫它 query-derived evidence
→ R6 形式滿足、實質退回 B3
```

**故：任何 query-derived evidence 在能影響三值 verdict 之前，MUST 先具備**

```text
evidence type            這是什麼類型的事實
provenance               誰產生、誰擁有、runtime semantics 為何
admissibility contract   憑什麼可被 Responsibility Authority 採信
```

```text
未背書的 classifier／LLM verdict  →  最多是 **observation**，
                                   **不得**自己成為 responsibility authority
「query → Face」本身              →  **MUST NOT** 作為 query-derived evidence 餵回本 Contract
                                   （circular selection）
```

### Output（**三值語義釘死**）

```text
applicable      有 qualified evidence **正向支持這個 candidate Face 的責任條件**
                ⚠️ **不等於**「它是唯一正確的 Face」，**不等於**「立刻 enter」
                ⚠️ **多個 Face 理論上可同時 applicable**；最後選誰是 Final Routing Authority 的責任

not_applicable  MUST 來自**正向的反證**——authoritative fact 明確**違反**該 Face 的必要條件，
                或落入其 **executable exclusion**
                ❌ 不得由「proof 沒找到」「0 rows」「mapping 不完整」「score 不夠高」推出

unknown         兩邊都證不成
                ❌ **絕不得**默默 collapse 成 applicable 或 not_applicable
```

#### M-1｜這是 E5 的**完整對稱版**（must-fix）

```text
E5（原）      proof 不足 → unknown ≠ not_applicable
M-1（補全）   ＋ applicable 需**正向支持**、not_applicable 需**正向反證**
              ＋ applicable **不獨佔**、不等於 enter
```

⚠️ 這是本線連續三次 precision-first collapse 的唯一防線
（v1 大量 abstain／Q2 誤殺 44%／Round 1 過度拒絕 17 對過度放行 0）。
把 unknown 折成 not_applicable，等於用 API 版本再做一次同樣的失敗。

---

## 1-B. M-5｜Evidence roles ＋ composition／conflict algebra（**final must-fix，carrier-independent**）

### 為何這屬於 Contract，而不是 carrier 的自由設計空間

若 Responsibility Authority 自身沒有固定的 evidence composition：

```text
同一批 inputs  →  Carrier A: applicable ／ Carrier B: unknown ／ Carrier C: not_applicable
```

那就無法分辨差異來自 **authority carrier**、**responsibility representation**、
還是 **evidence precedence**——比較的其實不是 carrier，而是三種**判決哲學**。
那是新的事後自由度。**故 composition semantics 於此凍結。**

### 1. Evidence roles（欄位名可換，**角色區分不可省**）

| role | 定義 | 硬性限制 |
|---|---|---|
| **PREREQUISITE** | 該 Face 成立所必需的前置條件（如：指涉解析到實體、actor 有權存取） | 其 `unknown` **MUST NOT** 被其他 positive evidence 掩蓋 |
| **RESPONSIBILITY_SUPPORT** | **candidate-Face-specific** 的責任依據 | ⚠️ N1／N2／N3 這類**只有 entity binding／visibility** 的 proof **不得**因此自動升成 `applicable`（semantic-role review 已判它們 R-e ❌） |
| **EXCLUSION** | 正向反證：authoritative fact 違反必要條件，或落入 executable exclusion | MUST 符合 M-1 的 positive-counterevidence 標準；**不得**由 absence 推出 |
| **OBSERVATION** | 其餘一切（含未背書的 classifier／LLM verdict、M-3 未過門者） | **永遠不得直接產生 verdict** |

#### ⚠️ role **不是 source 的固有屬性**（Contract 語義解讀，隨凍結生效）

> **evidence role 是 `proof × candidate Face × responsibility binding` 之下的角色，
> 不是某個 source type 永久綁定的標籤。**

同一個 runtime fact 在不同 Face 下可能扮演不同角色，例如 `viewer_user_id` 可見性 proof：

```text
對 Face A   可能是 REQUIRED PREREQUISITE
對 Face B   可能構成某種 RESPONSIBILITY_SUPPORT
對 Face C   可能只是 OBSERVATION
```

```text
❌ 不得建立「viewer visibility proof ＝ 永遠都是 PREREQUISITE」這類固定對應
```

⚠️ 否則就是把 **entity-side fact 偷偷升格成 R-e**——正是 semantic-role review 判定不成立的那一步。
⚠️ 本節為**語義解讀**：若下文任何 wording 讀起來像「source type 固定對應 role」，
   **一律以本節為準**。

### 2. Composition rules（**事前寫死，逐條可判定**）

```text
C-1  任一必要 PREREQUISITE = unknown
     → verdict = unknown
     （不得被 RESPONSIBILITY_SUPPORT 或任何 positive evidence 掩蓋）

C-2  沒有 facet-specific RESPONSIBILITY_SUPPORT
     → **MUST NOT** applicable
     （可能是 unknown，或由 C-4／C-5 決定）

C-3  只有 evidence absence（沒找到／0 rows／mapping 不完整／score 不夠）
     → verdict = unknown
     （M-1 已凍結，此處重申於組合層同樣成立）

C-4  兩份**皆為 authoritative** 的 evidence **對同一命題**、
     或對**邏輯上不可同時成立的命題**互相矛盾
     → **carrier MUST NOT 自行選 precedence**
     → verdict = unknown，且 MUST 標記 explicit **conflict** 狀態（見下）

     ⚠️ **「SUPPORT 與 EXCLUSION 同時存在」本身不構成 C-4。**
        support =「它屬於帳單操作責任」／exclusion =「某必要 session／entity condition
        已明確不成立」——這兩者**可以同時為真**，故走 prerequisite／exclusion 邏輯，
        **不是** conflict。

C-5  存在**明確、無衝突**的 authoritative EXCLUSION
     → verdict = not_applicable
     ⚠️ C-5 與 C-4 是**兩回事**：「一份乾淨的排除證據」≠「兩份權威證據打架」
```

⚠️ **C-4 是防第四次 precision-first collapse 的關鍵**：
**不得**用「因為 precision-first，所以衝突時一律 not_applicable」把 collapse 偷帶回來。

### 3. 業主點名的四個組合情境（**逐一裁定**）

```text
① positive support ＋ exclusion 同時存在，**且兩者針對同一命題**
   （或邏輯上不可同時成立的命題）
   → **C-4 衝突** → unknown ＋ conflict
   ❌ 不得自動判 not_applicable
   ⚠️ 若兩者陳述的是**不同命題**且可同時為真 → 不是 C-4，走情境④／C-5

② positive support ＋ 必要 prerequisite = unknown
   → **C-1** → unknown
   （prerequisite 的未知不因主題吻合而被覆蓋）

③ 兩個 authoritative sources 互相矛盾
   → **C-4** → unknown ＋ conflict；precedence **不由 carrier 決定**

④ 一個 prerequisite **明確為 false**（正向確立，非 absence）
   ＋ 另一個 responsibility proof positive
   → **not_applicable**
   理由：兩者**並不矛盾**——它們陳述的是**不同命題**（「主題吻合」vs「必要前置條件被正向證否」）。
        必要條件被正向證否即滿足 M-1 的 not_applicable 標準。
   ⚠️ 這是一條**裁定**，非推導；若日後認為 ④ 應與 ① 同視為衝突，須明確改判並記錄。
   ✅ **業主已 approve 此裁定（2026-08-24）**，其形式為：

```text
support ∧ required(P) ∧ authoritative(¬P)  →  not_applicable
```

   ⚠️ 但**必須守死兩個前提**（Contract 語義解讀，隨凍結生效）：

```text
前提一  該 PREREQUISITE MUST 真的由 **authoritative responsibility binding** 宣告為必要條件。
        ❌ 不得因某個 runtime fact「看起來很重要」就臨時把它叫 prerequisite。

前提二  `false` MUST 由 qualified authoritative evidence **正向確立**。
        ❌ absence ／ 404 的歧義 ／ 0 rows 的歧義 → 仍只能 unknown（M-1、C-3）
```

   ⚠️ 若失去前提一，Contract 就會退化成「任何 entity-side fact 都能否決任何 Face」；
      若失去前提二，就是把 absence 折成拒絕——第四次 precision-first collapse。
```

### 4. Conflict 的表示方式（維持三值輸出）

```text
verdict 仍為三值：applicable ／ not_applicable ／ unknown
conflict **不是**第四個 verdict，而是 unknown 上的**必填標記**：

  verdict = unknown
  conflict = true
  conflicting_sources = [...]        ← G-f 可追溯性要求

⚠️ 標記 conflict 而非新增第四值，是為了讓 Final Routing Authority
   能區分「證據不足」與「證據打架」——兩者的 routing policy 可能不同，
   但**該差異的處置屬 routing policy，本 Contract 不決定**。
```

### 5. 評估順序（**決定性，carrier 不得變更**）

```text
① 剔除所有 OBSERVATION（不參與 verdict）
② 檢查 authoritative evidence 是否互相矛盾    → 有：C-4，止
③ 檢查必要 PREREQUISITE                      → 任一 unknown：C-1，止
                                              → 任一正向為 false：情境④，not_applicable，止
④ 檢查 EXCLUSION（明確且無衝突）              → 有：C-5，not_applicable，止
⑤ 檢查 facet-specific RESPONSIBILITY_SUPPORT → 無：C-2 → unknown
                                              → 有：applicable
```

⚠️ 順序本身是契約的一部分：**同一批 inputs 在任何 carrier 上 MUST 得到同一個 verdict**。

---

## 2. Admission gates（**R1–R5 在新發現下的具體化**）

| gate | 要求 | 對應既有 requirement／證據 |
|---|---|---|
| **G-a｜Face-specific** | 在**同一組 instance proof** 下，能真正區別候選 Face | 直接來自 semantic-role review：N1／N2／N3 皆 R-e ❌。⚠️ 分不開＝沒有 R-e |
| **G-b｜Runtime enforceable** | 結果**不是 advisory**；接上 seam 後 MUST 能**反事實改變** entry | R2（N2）＋ META-RULE：驗收不得只證元件存在 |
| **G-c｜Open-Face compatible ＋ enrollment** | 新增 Face **不要求**先封閉全世界 Face taxonomy；**且** MUST 定義新增時的行為（見 M-4） | G1 FAIL 的直接教訓：Face 集合後台可增、零改程式 |
| **G-d｜No self-attestation** | Face **不得**僅因自己宣告「我負責」即成立 | 沿用 D3-member-1 已明訂的 self-attestation 禁令；B4（`grounding_scope` 宣告無 enforcement）即反例 |
| **G-e｜No similarity laundering ＋ candidate isolation** | **不得**把 similarity／category 換名塞進 authority；**且** candidate proposal 為 non-evidentiary（M-2） | R1 §1.2（已實測 REFUTED）；B2／B3 即現行違例形態 |
| **G-f｜Traceable** | **proposer ／ evidence provider ／ responsibility authority ／ final routing authority** 四者的關係皆可追溯 | R3：三種責任（candidate proposal／applicability evidence／final enter-reject）必須可追溯 |

⚠️ **G-b 與 G-d 是一組**：只有宣告而無獨立 enforcer，兩條同時不過（B4 的形態）。
⚠️ **B5 證明這一組是做得到的**（宣告＋consumer 強制），但那是 feasibility precedent，**不是**方案。
⚠️ **G-b 的 counterfactual outcome requirement 不得弱化**：只讀 verdict／寫 log 而 entry 照舊，
形式符合、實質違反（R2 §2.2 已明列此形式滿足）。

### M-4｜Open-Face enrollment semantics（must-fix）

對 R6 所治理的 routing path：

> 新 Face **可以**被新增，但若它尚未取得一份**通過本 Contract 的 binding**，
> 它**不得**因為有 category、有 builder、有 RULES、或存在於 DB 就自動取得 `applicable`。

Contract 層最安全的語義：

```text
Face exists
＋ responsibility authority binding absent
→ responsibility verdict = **unknown**
```

⚠️ **`unknown` 之後怎麼辦（回 Knowledge／clarify／保留原路徑／其他 recovery），
本 Contract 一律不決定**——那是 **routing policy**。

⚠️ 且若某種 recovery 會造成**本來正確的 Face 被阻止**，
即正式觸發 `spec.json` 中尚未裁定的
`unresolved.routing_false_reject_cost`（PRODUCT DECISION PENDING）——
**必須先取得該裁示**，不得在此偷訂。

---

## 3. Carrier shapes（**三種並列，不預選**）

| | shape | 形態 | 必須回答的同一題 |
|---|---|---|---|
| **A** | Central responsibility authority | 獨立 registry／policy source：`facts × candidate Face → applicability` | 它新增的 authority **來自哪裡**？ |
| **B** | Face-local declaration ＋ independent executable validation | Face 宣告自己接受哪些 proof semantics，但由**外部 consumer／enforcer** 驗證 | 同上 |
| **C** | Capability-bound authority | Face 與 machine-enforced capability／action binding；runtime facts 與 capability requirements **機械 join** | 同上 |

### 三者共同的**當場失敗條件**

```text
若「它新增的 authority 來自哪裡？」的答案仍是：
    「Face RULES 寫了這樣」
→ **直接失敗**（G-d ＋ G-e）
```

⚠️ 這條寫在比較之前，是為了讓比較有可能得出「三個都不合格」這個結果。

### 各 shape 目前已知的**待答問題**（不是評分，是尚未回答的事）

```text
A  authority 的內容由誰產生、由誰維護？若仍是人工填表 → G-b 的 enforcement 從哪來？
B  外部 enforcer 憑什麼判定「Face 宣告的 proof semantics」成立？
   （B4 已證明：只有宣告端、沒有強制端 → 不成立）
C  平台**沒有 Face 概念**（63351cd 實證）→ capability binding 的 Face 那一側從何而來？
   若答案是「在對話層另建一份對應」，那它就退化成 A 或 B
```

⚠️ 以上皆為**待答**，**不構成**對任一 shape 的淘汰或推薦。

---

## 4. D1／D3 的狀態再收斂一次

**不是**兩條獨立路徑各缺一半，而是**已收斂到同一個 missing authority**：

```text
D1   runtime demand facts ✅（N1／N2）      facet responsibility authority ❌
D3   runtime prerequisite facts ✅（N1／N2／N3）  facet responsibility authority ❌
```

> **因此此刻沒必要先決定「重開 D1 還是 D3」。**

先把 responsibility authority 定義出來，**再**看它的 provenance：

```text
routing-owned                       → 更像 D1
Face-owned but independently enforced → 更像 D3
neutral／capability-owned            → 可能讓 D1／D3 這個分類**本身失去重要性**
```

⚠️ 最後一種結果是允許的，且不該被視為失敗——它會說明我們一開始的 family 切法不是關鍵軸。

---

## 5. 本檔的界線

```text
✅ 只定 contract semantics ＋ evidence composition algebra ＋ admission gates ＋ 並列 carrier shapes
❌ 不選 carrier、不設計 schema、不主張新增某張表／某個 registry
❌ 不開 D1-member-2／D3-member-next／D4；D2 仍 deferred
❌ 不改 family disposition（D1／D3 皆維持 INSUFFICIENT_EVIDENCE）
❌ 不改已凍結的 R1–R5（R6 以 derived design constraint 獨立成檔）
❌ 不動 production；不產測資；ruler 0.058928 仍凍結未用
```

## 下一步（待業主裁定，**不預選**）

```text
① ✅ 已完成：M-1～M-5 全部 CLOSED，本 Contract **APPROVED／FROZEN**
② **Carrier 比較尚不開始**。開始前 MUST 先凍結比較量尺，且該量尺至少要比較：
     - authority **真正從哪來**
     - 如何 **enrollment**（新 Face 如何取得 binding）
     - 如何 **machine-enforce**
     - **unknown 如何保真**（不被沿路折成其他兩值）
     - Face 新增時 **correctness 如何維持**
   ❌ 不得比較「哪個 carrier 比較漂亮／比較好實作」
   —— 與 G1 的教訓一致：判準要在看到候選之前定
```
