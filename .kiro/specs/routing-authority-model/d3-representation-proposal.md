# D3 representation proposal（v2）：責任宣告能否從枚舉清單換成可泛化表示

> 2026-08-24｜語言 zh-TW
> **v1 裁定：REVISE / MUST-FIX（業主，非 reject）**——verifier 打穿的是「B／C 已具備准入資格」
> 這個論證，**不是**把「從開放措辭枚舉改成組合式 responsibility representation」這個方向反證掉。
> 本版回應 M1／M2／M3／M4 ＋ 兩項更正。v1 見 git `d88df25`。
> **本檔只回答 representation 一題。** 不寫 implementation、不產新 challenge cohort、不改 ruler、
> 不碰 production Face config schema／enable flag／manifest。

## 本檔現在的狀態（先寫清楚，避免被讀成「補到四維就好了」）

```text
A  open-world utterance enumeration
   → REJECTED by F2 evidence

B  candidate compositional representation
   → ADMISSIBLE ONLY IF：schema closure ＋ domain closure 皆可由**獨立 authority** 證明
   → **目前兩者皆未證明**

C  B 的 executable boundary algebra
   → 只增加 **contract-space auditability**
   → **不宣稱**解決 query → dimension 的自然語言語義映射
```

> **B／C 尚未通過 G1，只是取得「可被重新論證」的資格。**
> 本版**不**宣稱 B 已成立；本版的工作是把「要證明什麼」寫成可判定的形式。

---

## 唯一命題（未變）

> **能否把 Face responsibility 從「enumerated handles」改寫成具組合能力的 applicability
> representation，使「未列舉但語義同類」的 query 仍被正確判定？**

不合格的答案形態（事前排除，本版新增第 4 條）：

```text
❌ handles 從 10 條加到 50 條
❌ 加同義詞表／keyword 擴充
❌ 換 prompt 措辭要 LLM「自己泛化」
❌ 每遇一個治不到的案例就補一條新 dimension —— 那是把「開放的措辭清單」
   換成「開放的維度清單」，不是封閉化（本版 M1 的核心禁令）
```

---

## 更正一：**不再以「F2 = 7 筆」作任何量化基礎**

v1 寫「F2 枚舉缺口 約 7 筆 ← representation revision 的**唯一**標靶」。該基數**經查不成立**：

```text
bd-10-a  在 round1-failure-analysis-result.md 中同時被列入 F2（7 筆）與 F1（3 筆）
         → 7+3+2+5=17 的加總把它算了兩次
         → 其 d3_raw 實際依據為 entity_reference_required（F1 型），非措辭未列舉

bf-05-a  v1 記為「『待對帳』不是列舉過的狀態措辭」（F2）
         → 其 d3_raw 實為：「該面向的責任範圍不包括對帳相關的問題」，
           evidence_used 標為「該面向的 does_not_handle 列表」
         → 但 billing_flow 的 does_not_handle 僅四項（帳單金額組成／帳單操作可否／
           金流商設定／平台通則），**無任何對帳條目**
         → 這是**對 contract 內容的錯誤陳述**（與 F1 同型的執行失效），不是枚舉缺口
```

**更正後的表述**：

> **Round 1 中存在 confirmed F2 exhibits，但精確基數需重新逐筆去重歸因。**
> 這批 burned cases **只作 post-mortem**，**不進入** member-2 的 acceptance denominator。

## 更正二：**「效果上限」改寫為「事前可歸因標靶」**

v1 的「**唯一**標靶」「最多只能影響 7 筆」措辭過硬。改為：

> **representation revision 的事前主要可歸因標靶是 F2 類失敗。**

若未來 F1 類也改善：只能記為 **observed collateral improvement**，
**須經 ablation 才可歸因**給 B／C。不得反向宣稱「representation 理論上碰不到 F1」。

---

## A 為何被 F2 反證：枚舉的是**開放集合**

```text
規則只能治封閉集合。
handles 枚舉的是「動作／問題的措辭」——那是開放集合（措辭無上限）。
→ 因此 A 不是「列得不夠多」，是**列舉對象選錯了層**。
```

以下 exhibits 為 **confirmed F2 型**（責任歸屬一致、措辭落在列舉之外），
**已剔除**更正一所列的兩筆誤歸因，且**不作為基數宣告**：

| item | query | contract 已列 | 落空原因（依 `d3_raw` 字面依據） |
|---|---|---|---|
| `ba-06-a` | 這筆的期間寫 7/1-7/31，但明明應該是八月份的 | 金額不對／沒出現／看不到 | 「並未明確指出某一筆帳單的金額或出現狀況」——欄位不在列舉內 |
| `bf-08-b` | 租客這筆分兩次匯，結果只認到第一筆 | 租客說繳了但錢沒進來 | 「不涉及單一帳單的狀態問題，而是匯款的處理問題」——同一責任的另一種說法 |
| `ba-09-b` | 這張帳單上的租客姓名還是舊房客那位 | 金額不對／沒出現／看不到 | 「不涉及帳單金額或帳單的顯示問題」——欄位不在列舉內 |
| `bd-09-a` | 這筆的到帳日我想往後延，改得了嗎 | 發不出去／取消不了／逾期費／手動到帳失敗 | 「詢問的是延後到帳日的可能性，而不是帳單的發送、取消或逾期費用等問題」 |
| `ba-08-a` | 同一個租客同一個月冒出兩張一樣的帳單 | 沒出現 | 「並未明確提到某一筆帳單的金額不對或某一筆帳單沒出現」——反向情形未列 |

⚠️ `bd-09-a` 的 `d3_raw` 已在 **operation-family 層級**推理（列舉了發送／取消／逾期費）
**仍判 not_applicable**——即 evaluator 早已自行做了 B 所提議的那層歸類。
**這對 B 是不利證據**：B 的增益完全取決於「延期」是否落在 G1 獨立導出的值集內，
而不是取決於「有沒有維度這個概念」。本版把它明列，不藏在腳註。

---

## B：候選 representation，**兩層封閉性皆待證**

責任 = 若干維度值的組合。但 v1 只斷言「每一維的值有限」，**未觸及維度集合本身是否封閉**。
本版把要證明的東西分成兩層（M1）：

### 第一層：Schema closure（**目前未證明**）

```text
待證：哪些 dimensions 是合法的？
待證：為什麼 dimension 集合本身不會隨案例一直長？
```

⚠️ **v1 自身已經洩漏了這個問題**：v1 第 115 行的 predicate 使用了
`target == 金額組成`，而 `target` **不在** v1 第 89–93 行宣告的維度清單內。
即 v1 在示範 C 的同一頁上，就已經長出了第四條未宣告的軸。

**`target` 的處置（依 M1，只有兩種合法做法）**：

```text
(i)  能從**獨立產品／系統 authority** 證明它是必要且有限的 dimension → 正式加入
(ii) 否則**刪除依賴它的 C 範例**，並承認目前 schema **尚不能表達那個 boundary**
```

**本版採 (ii)**：我沒有獨立 authority 證據，故已刪除該 predicate 行，
並在下方「已知無法表達的 boundary」中明記。
⚠️ **不得**因為 `ba-06-a`／`ba-09-b` 需要它就把它補進來——那正是 M1 禁止的動作。

### 第二層：Domain closure（**目前未證明**）

```text
待證：每一個 dimension 的 values 從哪個**外部有限集合**導出？
待證：為什麼不是從 failure exhibits 反向長出來？
```

⚠️ **v1 的值集確實是反讀出來的**：`operation_class` 例示中的
「延期」← `bd-09-a`、「存檔」← `bd-10-a`。`problem_state` 的五個值同樣可逐一對回
Round 1 exhibits 或 contract handles 措辭。**故 v1 的 domain closure 主張無證據力。**

目前的候選維度（**列為待證清單，非已成立的 schema**）：

```text
entity_scope     候選 authority：平台實體型別（bill／contract／estate／meter／member）
operation_class  候選 authority：平台 operation surface／command registry／API contract／
                 bill state machine —— **須逐值附來源引用**
problem_state    候選 authority：**目前無法指名**（最弱的一維）
responsibility   組合 → Face 的 mapping（依賴上述三者，不獨立）
```

⚠️ **`problem_state` 是本版最脆弱的一格**：verifier 指出 (a)「平台可執行的操作有限」
與 (b)「使用者描述問題的語義類有限」**不自動等價**。若操作有限但**失敗形態／問題描述**仍開放，
則 B 只是把開放性從 `handles` 搬進 `problem_state`。
**本版不宣稱已解決這一點**，把它列為 G1 必須裁定的對象。

### 已知目前 schema 無法表達的 boundary（誠實記錄，不補洞）

```text
`ba-06-a`（期間錯誤）／`ba-09-b`（姓名錯置）與「金額不對」
在 entity_scope × operation_class × problem_state 三維下**壓成同一組 triple**，
其區辨正好需要被刪掉的 `target` 軸。
→ 即：**目前的候選 schema 表達不了這條邊界**，這是 B 尚未准入的直接證據之一。
```

---

## C：只主張 **contract-space auditability**（M4）

```text
C 可以在**不跑任何 query** 的情況下靜態檢查：
  - predicate overlap（兩個 Face 宣稱同一區域）
  - predicate gap（無人認領的區域）
  - undeclared dimension／value（例如 v1 的 `target`）
  - contradictory contract regions

C **不能**靜態檢查：
  - query → dimension mapping 的語義歧義
```

**因此 v1 對 F4 的說法被撤回**：`bd-02-b`／`bf-09-a` 是 ground-truth label 與
`self_scope_rule` 對**某一句話**的歸屬分歧；除非該句已被映射成固定 dimension 值，
否則**不能說 C 能在「不跑 query」時抓到它**。

> **精確表述：C 提供的是 representation-space auditability，
> 不是 natural-language applicability auditability。**

### Free-text atom 禁令（M4，封住 C 的自陳失效模式）

```text
predicate atom **MUST** 只能引用 declared dimension／declared value／declared operator。
任意自然語言 atom **MUST NOT** 進入 executable predicate。
```

否則 `problem == "任何看起來怪怪的情況"` 形式上是 predicate，實質退回自由文字，
C 就只是「B ＋ 更多語法」。

### C 範例（已移除依賴未宣告維度的那一行）

```text
applicable_if:
  - entity_scope == 單一 bill
    AND operation_class ∈ {…由 G1 獨立導出後填入，不得於此先行列舉…}
    AND problem_state == 操作被拒
not_applicable_if:
  - entity_scope == 無                       # 通則型
```

⚠️ `operation_class` 的值刻意留空：v1 在此處直接列舉的動作值即是從 exhibits 反讀來的，
**先填值就已經違反 G1 的獨立性要求**。

---

## G1（v2）：覆蓋**全部** dimensions 與 domains 的 executable closure gate（M2）

verifier 指出 v1 的非後承成立：v1 第 151 行把 `operation_class` 的封閉性
當成 B 整體封閉性的充要條件，但 v1 第 98 行的封閉性主張有三支
（實體型別有限／平台操作有限／問題形態有限），G1 只驗了中間一支。

**G1 改寫為**：

> **所有參與 applicability predicate 的 dimensions 與其 value domains，
> MUST 在不使用 challenge labels／failure labels 的情況下，
> 由**事前指定的 authoritative source** 完整導出。
> 任一 dimension 或任一 domain 無法證明有限 → **B／C 不得准入。**

### 來源獨立性條款（吸收 P1-2）

```text
dimension 與 value 的導出 **MUST NOT** 由 Round 1 exhibits 決定。

若「延期」「存檔」最終出現在 operation_class，MUST 能指出它們來自
platform operation surface／command registry／API contract／bill state machine
等**獨立來源**，而不是因為我們已經看過 bd-09-a／bd-10-a。

導出後才追加、且僅由 exhibit 動機支持的值 → **不得計入封閉性證據**。
```

⚠️ 沒有這條，G1 兩種結局都不具鑑別力：導出結果含「延期／存檔」時無法區分是
平台真有該操作面還是作者已知答案；不含時 B 對其標靶案例本來就治不到。

### Machine-checkable failure（G1 的判定必須可機器執行）

```text
predicate 使用未宣告 dimension        → FAIL
predicate 使用未登錄 value            → FAIL
domain source 無法證明完整            → FAIL ／ INSUFFICIENT
dimension 集合在導出後因案例而增加     → FAIL（schema 未封閉）
```

### Negative control：`target`

> v1 於 C 範例中使用的未宣告維度 `target`，即為 G1 的 standing negative control：
> **一個正確實作的 G1 必須把它判為 FAIL。** 若 G1 放它過關，是 G1 本身失效。

---

## G2：**現版撤銷**（M3，採路 A）

v1 的 G2 要求比較「維度分類錯誤率」與「Face 分類錯誤率」。**該條不可執行，故不是 falsifier**：

```text
✗ dimension-level ground truth 不存在
   （步驟 4 只承諾 applicability label，不是逐筆維度標註）
✗ query → Face 的唯一既有量測在**已 burned** 的 Round 1 cohort 上，
   不得作為新 cohort 的比較基準
✗ B／C 實為 query → dimensions → predicate 組合 → Face 的多階段管線，
   整段對上單段 query → Face，任何結果都不可歸因
```

**處置（業主裁定：路 A）**：

> 「query → dimensions 比 query → Face 更可靠」
> **降級為 `SUPPORTED DESIGN HYPOTHESIS`，且 NOT a member-2 admission condition。**

B／C 能否進下一步，**只**取決於「representation 的 schema／domain closure 可否證明」（G1），
**不**宣稱 mapping 已較可靠。自然語言 mapper 是否勝過 direct Face classifier，
是 **concrete member 的實驗問題**，不是 representation proposal 該在此回答的。

### 若未來要把它升回 falsifier（路 B，記錄備查，本輪不做）

```text
MUST 先在新 cohort 上建立**獨立的 dimension-level blind ground truth**，並三層分開量測：
  query → dimension assignment      （representation／mapper 品質）
  dimensions → predicate result     （composition 品質）
  predicate result → Face applicability （最終 applicability 正確性）
只有三層分離，失敗才可歸因。
```

---

## 事前承諾的 falsifier 與 negative control（保留，措辭依更正二收窄）

### F2 falsifier（正向：不得因措辭未列舉而拒絕）

> 一個 applicability case **SHALL NOT** 僅因其具體動作詞／問題措辭未出現在
> handles／examples 中即被判 `not_applicable`，只要它符合 frozen responsibility dimensions。

### Negative control（反向：不得因 lexical overlap 而接受）

> query 含有某個**已登錄**的動作值，但其 responsibility dimensions **不匹配**時，
> **SHALL NOT** 判 `applicable`。

⚠️ 兩者必須同時成立。只有前者而無後者，把 representation 寫得極寬鬆即可全過——
那是把 Round 1 的**單向過度拒絕**換成**單向過度放行**。
Round 1 的 `過度放行 0` 是目前唯一的好性質，**不得在新版丟掉**。

---

## 本檔明確不做的事

```text
❌ 不寫 implementation、不定 JSON schema 欄位名
❌ 不把 `target` 補成第四維（除非有獨立 authority 證據——目前沒有）
❌ 不產生新的 challenge cohort（Round 1 cohort 已 burned，只能作 diagnostic／post-mortem）
❌ 不改 matching ruler（tolerance 0.058928 仍凍結未用）
❌ 不碰 production Face config schema／enable flag／manifest
❌ 不為 F4 的 2 筆增加專用規則，也不再宣稱 C 能靜態檢出它們
❌ 不宣稱 D3 family disposition 有任何變動（仍為 INSUFFICIENT_EVIDENCE）
❌ 不以 Round 1 的 17／7 筆數字作 member-2 的 acceptance denominator
```

## 下一步

```text
本檔 = 步驟 1 的 v2（representation proposal，已收 M1–M4）
  ↓
步驟 2  review representation only（本版待審）
  ↓
步驟 3  **G1 執行**：由獨立 authoritative source 導出 dimensions 與 domains
        （唯讀查核；不改任何檔、不進 production seam）
        → 任一層無法證明有限 → **B／C 退場**，D3 回到 member-shape discovery
  ↓
步驟 4  G1 通過才 freeze D3-member-2 contract
  ↓
步驟 5  產生**新的 isolated challenge cohort** ＋ 新 blind labels
  ↓
步驟 6  Experiment A → B
```

> **下一個真正要證明的命題**（由本次 review 提升而來）：
> **能否在不看 failure answers 的前提下，先驗地定義一個有限、且足以承載
> Face responsibility 的語義代數？**
> 這一關過不了，B 就只是更漂亮的 enumeration。
