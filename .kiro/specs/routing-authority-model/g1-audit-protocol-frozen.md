# G1 audit protocol（**凍結於讀取任何 source 內容之前**）

> 2026-08-24｜語言 zh-TW｜業主裁定：representation proposal **APPROVED**；
> 本協議 **APPROVE WITH 1 MUST-FIX（已套用）**：S3 須附 authoritative binding argument；
> ＋ §3 可執行性註解、§2 衝突適用範圍 wording guard。§3 導出順序經業主裁定**保留**。
> B／C **仍未通過 G1**，不得 freeze member-2；**先凍結 G1 查核程序，再唯讀執行 G1**。
> 前置：`d3-representation-proposal.md`（v2，`68f53ed`）

## ⚠️ Freeze attestation

> **本檔撰寫時，尚未為了導出任何 dimension／value 而讀取任何 source 的內容。**
> 下列六項規則是**先驗**寫定的准入程序，不是看過素材後回頭合理化的判準。
> 本檔所列的 source class 以**性質**定義（是否具備全集語義），
> **不是**「已經去翻過、確認存在」的清單——某一 class 在本專案是否真有實例，
> 正是 G1 執行時要回答的事。

本協議要防的事後適配形態：

```text
先翻 API／state machine／seed
→ 看見有哪些東西
→ 再決定哪些算 authoritative
→ 再決定如何把它們歸成 dimension／value
→ 最後宣布 closed          ← 這不叫封閉性證明，這叫把搜尋結果改名
```

---

## 1. Authoritative source inventory（哪些 source class 合法）

合法性由**性質**決定，不由方便程度決定。一個 source 要能支持 **domain closure**，
必須具備 **totality semantics（全集語義）**：

> **它不只是「一份含有這些值的清單」，
> 而是「不在其中的值在系統中無法存在／無法執行」的那個機制本身。**

### 合法 source class

| class | 定義 | 為何具備全集語義 |
|---|---|---|
| **S1 executable enumeration** | 程式碼中的 Enum／DB enum type／state machine transition table／constant registry | 全集由建構決定：不在其中的值無法被實例化 |
| **S2 dispatch registry** | API operation contract／route registry／command registry | 全集由分派機制決定：**不在其中的 operation 無法被執行** |
| **S3 binding exhaustive specification** | 明文宣告「本清單即全集」，**且能證明該規格對本次 audited system／version 具 authoritative binding**，使規格外的值無法成為合法系統狀態／操作 | 全集由規格＋其 enforcement 共同保證 |

⚠️ **S2 的資格條件**：它必須**就是**分派機制。若某 registry 只是「文件裡的一份 API 列表」，
而系統實際上可繞過它執行 operation，則 S2 不成立，降為 S4。

⚠️ **S3 的資格條件（binding argument，業主 must-fix）**：
單靠「規格寫了這是全集」**不足以**推出「runtime 中不可能存在規格外的值」。

```text
spec：operation ∈ {A, B, C}
runtime：其實接受任意字串
→ 該 spec 雖明文宣告全集，仍**不**滿足 §4 的 totality argument
```

故 S3 **MUST** 另附一段 **binding argument**：說明該規格憑什麼對本次 audited
system／version 具強制力（enforcement 機制何在／規格外值為何無法成為合法狀態）。
若僅有文件寫「目前支援 A／B／C」而 runtime 無 enforcement、亦無其他機制保證集合封閉：

```text
S3 qualification = FAIL  →  該 domain NOT PROVEN
```

⚠️ **不得**因為文件用了「僅／全部／共三種」這類措辭就直接過關。
此條使 S1／S2／S3 服從**同一個**資格原則，S3 不得成為文字版後門。

### **非法** source class（列出來是為了不得事後追認）

```text
S4 observed-values list  ── 任何「目前搜到這些」的清單（含程式碼中散落的字串常數）
S5 seed KB 內容／Face RULES 文本
S6 Round 1 cohort／blind labels／experiment rows／failure exhibits
S7 本工作線自己先前產出的文件（含 proposal v1／v2 的例示值）
S8 LLM 生成的候選清單
```

⚠️ **S6 的禁用是 M1 的核心**：dimension 與 value 的導出
**MUST NOT** 由 Round 1 exhibits 決定。
若「延期」「存檔」最終出現在 `operation_class`，必須指得出它在 S1／S2／S3 中的位置，
**而不是因為我們看過 `bd-09-a`／`bd-10-a`**。

---

## 2. Source precedence（多來源衝突時誰優先）

```text
S1 executable enumeration  >  S2 dispatch registry  >  S3 binding exhaustive specification
```

⚠️ **但衝突不得被 precedence 靜靜吃掉**：

> 當 S1 與 S2／S3 對同一 domain 給出**不同的全集**時，
> precedence 只決定**採用哪一份值集繼續作業**，
> **不**消除該衝突——該衝突 MUST 逐筆記錄，且**計入不利於 closure 的證據**。
> 若衝突影響到某 domain 的邊界，該 domain 判 **NOT PROVEN**。

理由：兩個都自稱全集的來源互相矛盾，本身就是「該系統沒有單一權威全集」的證據。

⚠️ **衝突的適用範圍（wording guard）**：本條只適用於
**對同一 audited scope／version 都已通過資格認定**的全集來源之間的矛盾。

```text
❌ 不算 conflict：舊版 spec vs 現行 registry／dead code vs 生效路徑／非 binding 文件
   → 這些應在 **source qualification 階段就被淘汰**，不得混進 conflict 記錄稀釋判定
✅ 算 conflict：兩個對同一 audited scope／version 都被認定 authoritative 的全集來源互相矛盾
```

---

## 3. Derivation rule（什麼條件下可以宣告一個 dimension／value）

### 宣告一個 **dimension**

```text
MUST 指名一個 S1／S2／S3 來源，該來源**本身**把這個維度當成一個獨立的分類軸
MUST 說明該維度與其他已宣告維度的關係（正交／從屬／重疊）
MUST NOT 因為「某個案例需要它」而宣告        ← M1 禁令
```

### 宣告一個 **value**

```text
MUST 出現在該 dimension 所指名來源的**枚舉之中**
MUST 附逐值來源引用（可 grep 的符號／檔案位置）
MUST NOT 為了涵蓋某個 exhibit 而追加
```

### 導出順序（防污染）

```text
① 指名 candidate authoritative source
② **只**查核它的 authority／totality semantics
   → 它為什麼有資格定義全集？（S1／S2／S3 資格條件、§4 totality argument）
③ totality argument 成立後
④ 才從該 source 導出 dimensions／values
⑤ freeze
⑥ **最後**才與 F2 exhibits 對照
```

⚠️ **本條不是「盲讀 source」**（那不可執行）。為了判斷
「這是不是 executable enum／真 dispatch registry／binding exhaustive spec？」
**可以**讀該 source。

> **禁止的是**：在 totality qualification 完成之前，
> **利用從該 source 看到的具體 values 去塑造 schema**。

⚠️ **步驟 ⑥ 只用於觀察**，不得回頭修改 ①–⑤。
**導出後才追加、且僅由 exhibit 動機支持的值 → 不得計入封閉性證據。**

---

## 4. Completeness criterion（「有限」≠「目前列得完」）★

這是本協議最重要的一條。

```text
closed domain   ── 來源具備全集語義：不在其中的值**在系統中無法存在／無法執行**
observed values ── 來源只是「我們查到的東西剛好有這些」
```

**判定要求**：每一個 domain MUST 附一段明文的 **totality argument**，回答：

> **「為什麼不在這份清單裡的值，在這個系統中不可能出現？」**

寫得出 → 可判 `PROVEN`。寫不出 → **`NOT PROVEN`**，不論該清單看起來多完整。

範例對照：

```text
✅ 可支持 closure：operation 由 command registry 分派，不在 registry 者無法執行
                  → 「registry 之外的 operation 不可能發生」成立

❌ 不可支持 closure：「seed 裡目前提到：修改、刪除、重發、延期……」
                  → 這是 observed values，證明不了任何邊界
```

### 對 `problem_state` 的特別嚴格條款（業主明令）

> `problem_state` 是候選 schema 中最弱的一格（`d3-representation-proposal.md` 已自陳
> 其候選 authority「目前無法指名」）。
> **不得因為查了幾份文件只看到 N 種狀態，就宣稱該 domain 有限。**
> **若不存在能給出全集語義的獨立 authority → 該 domain 判 `NOT PROVEN`，G1 即失敗。**

⚠️ 這**不是**壞結果。它直接回答了 proposal 現在最重要的問題：

> **B 是否只是把 open enumeration 往下搬一層？**

`problem_state` 若封不起來，答案就是「是」——而那是本輪最有價值的產出之一。

---

## 5. Absence semantics（來源沒寫，不等於不存在）

```text
source 未提及某事物  →  **MUST NOT** 自動推論為「該事物不存在」
```

沉默只有在一種情況下能支持 closure：

> 該來源已依 §4 證明具備**全集語義**——此時「不在其中」才等於「不存在」。

否則沉默一律導向 **`INSUFFICIENT`**，不得導向 `PROVEN`。

⚠️ 反面應用同樣有效：不得因為某來源沒寫「不支援 X」，就推論「X 屬於責任範圍」。

---

## 6. Failure consequence（失敗時會發生什麼，事前寫定）

```text
schema closure 無法證明        → G1 FAIL
任一 domain closure 無法證明   → G1 FAIL
證據不足以判定                 → G1 INSUFFICIENT（等同不得准入）

FAIL／INSUFFICIENT 之後：
  ❌ MUST NOT 補上 dimension／value 後繼續走 member-2
  ❌ MUST NOT 放寬 §4 的 totality 要求重判
  ✅ B／C 退場，D3 回到 member-shape discovery（與 D1 同狀態）
  ✅ 「哪一層封不起來」本身作為結論記錄下來
```

⚠️ **family disposition 不因 G1 失敗而改變**：D3 family 仍為 `INSUFFICIENT_EVIDENCE`（M1）。
G1 失敗淘汰的是 **B／C 這個 representation**，**不是** Face-owned contract family。

---

## Negative controls（G1 自身的鑑別力測試）

### NC-1｜undeclared dimension（standing control）

> `d3-representation-proposal.md` v1 在 C 範例中使用的 `target`，
> 是 predicate 中一個**未宣告的維度**。
> **一個正確實作的 G1 必須把它判為 FAIL。**
> G1 若放它過關，是 **G1 本身失效**，該次查核結果作廢。

### NC-2｜case-induced addition（業主指定，本協議新增）

情境：查核完成、closure 宣稱成立之後，出現一個合理的新產品案例，
它需要新增 dimension 或 value 才能表達。

```text
❌ 系統 MUST NOT：自動 append 到 schema／domain，然後仍宣稱原 G1 PASS
✅ 正確結果：原 closure claim **被反證**
              → representation version bump
              → **G1 重做**
```

⚠️ 沒有這條，「closed-world」只是**每次發現新例外就擴表**——
那與 A 的枚舉在結構上沒有差別，只是擴表頻率較低。

---

## G1 的輸出**限制**（只回答這些）

```text
schema closure          PROVEN ／ NOT PROVEN ／ INSUFFICIENT
each domain closure     PROVEN ／ NOT PROVEN ／ INSUFFICIENT
                        （entity_scope／operation_class／problem_state／其他已宣告維度）
supporting provenance   逐項來源引用（可 grep 的符號／檔案位置）＋ 每個 domain 的 totality argument
conflicts               §2 記錄的來源衝突
```

### 本輪**不得**順帶回答（越界即為協議違反）

```text
❌ D3-member-2 會不會準
❌ query → dimension 能不能可靠映射       （已依 M3 降為 hypothesis，非 admission 條件）
❌ 哪些 Round 1 cases 可以被修好
❌ B 比 A 好多少
```

理由：以上皆非 G1。混進來會讓「封閉性是否成立」這個唯一問題再次被表現數字蓋過去。

---

## 執行邊界

```text
✅ 唯讀查核（Read／Glob／Grep）
❌ 不改任何檔
❌ 不進 production seam、不動 Face config schema／enable flag／manifest
❌ 不產生新測資、不改 matching ruler（0.058928 仍凍結未用）
❌ 不重跑 Round 1 cohort（burned；本協議全程不需要它）
```
