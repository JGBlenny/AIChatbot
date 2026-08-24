# D3 representation proposal：責任宣告能否從枚舉清單換成可泛化表示

> 2026-08-24｜語言 zh-TW｜業主裁定：先做 D3 representation proposal，D1 暫緩（見 `d1-member-shape-deferred.md`）
> 前置：`round1-failure-analysis-result.md`（F2 歸因）｜`round1-members-frozen.md`（D3-member-1 契約）
> **本檔只回答 representation 一題。** 不寫 implementation、不產新 challenge cohort、不改 ruler、
> 不碰 production Face config schema／enable flag／manifest。

## 唯一命題

> **能否把 Face responsibility 從「enumerated handles」改寫成具組合能力的 applicability
> representation，使「未列舉但語義同類」的 query 仍被正確判定？**

不合格的答案形態（事前排除）：

```text
❌ handles 從 10 條加到 50 條
❌ 加同義詞表／keyword 擴充
❌ 換 prompt 措辭要 LLM「自己泛化」
```

以上三者都不改變 representation，只是加大字典或加強祈求，**F2 的反證對它們一樣有效**。

---

## 先鎖住 representation 能改到的**上限**（避免後續冒領功勞）

Round 1 D3-member-1 的 17 筆 false reject 依 `round1-failure-analysis-result.md` 歸因：

```text
F2 枚舉缺口           約 7 筆   ← representation revision 的**唯一**標靶
F1 evaluator 誤讀指涉  約 3 筆   ← 與 D1 同型；**換 representation 治不到**
F4 label vs contract 邊界衝突  2 筆   ← 併入 N3／design-discovery，**本檔不處理**
其餘                  約 5 筆   兼具多因或歸因不足以單獨計入
```

⚠️ **事前承諾**：即使新 representation 完全解決 F2，**也不得預期 17 筆全綠**。
representation 換掉後若 F1 那 3 筆仍紅，那是**預期行為**，不得因此判 representation 失敗；
反之若聲稱 17 筆全綠，須先排除是 evaluator 換代或 prompt 變動造成（混淆變數）。

---

## 為什麼 A 一定會失敗：枚舉的是**開放集合**

這是本檔最關鍵的判準，其餘比較都由它推出：

```text
規則只能治封閉集合。
handles 枚舉的是「動作／問題的措辭」——那是開放集合（措辭無上限）。
→ 因此 A 不是「列得不夠多」，是**列舉對象選錯了層**。
```

Round 1 的 F2 exhibits 逐筆印證「同一責任、不同措辭」就掉出清單：

| item | query | contract 已列 | 落空原因 |
|---|---|---|---|
| `ba-06-a` | 這筆的期間寫 7/1-7/31，但明明應該是八月份的 | 金額不對／沒出現／看不到 | 「期間」不是列舉過的欄位名 |
| `bf-05-a` | 錢明明已經進來了，這筆一直卡在待對帳 | 帳單狀態沒動（繳費側） | 「待對帳」不是列舉過的狀態措辭 |
| `bf-08-b` | 租客這筆分兩次匯，結果只認到第一筆 | 租客說繳了但錢沒進來 | 「只認到第一筆」是同一責任的另一種說法 |
| `ba-09-b` | 這張帳單上的租客姓名還是舊房客那位 | 金額不對／沒出現／看不到 | 「姓名錯置」不在欄位列表 |
| `bd-09-a` | 這筆的到帳日我想往後延，改得了嗎 | 發不出去／取消不了／逾期費／手動到帳失敗 | 「改到帳日」不在動作列表 |
| `bd-10-a` | 改完明細之後還是存不了檔，這張是怎麼了 | 同上 | 「存檔失敗」不在動作列表 |
| `ba-08-a` | 同一個租客同一個月冒出兩張一樣的帳單 | 沒出現 | 「多出來」是「沒出現」的反向，未列 |

**共同結構**：責任歸屬其實一致，**措辭落在列舉之外**。這正是開放集合上做枚舉的必然結果。

---

## 三種 representation shape 的比較

判準只有一條：**它枚舉的對象是封閉集合，且開放的部分由規則導出**。

### A. Enumerated examples（現行形態）

```text
handles: ["某一筆帳單為什麼發不出去", "某一筆帳單為什麼取消不了", ...]
```

| | |
|---|---|
| 枚舉對象 | **問題措辭**（開放集合） |
| 泛化來源 | 無——完全依賴 evaluator 自行類推 |
| 判定 | ❌ **已被 F2 反證**。不再作為候選。 |

### B. Compositional dimensions

責任 = 若干**維度值的組合**，維度值各自來自封閉集合：

```text
entity_scope      單一 bill｜單一 contract｜單一 estate｜…｜無（不指涉任一筆）
operation_class   由平台**實際操作面**導出（發送／取消／作廢／刪除／修改／重發／
                  手動到帳／延期／存檔…）——**不是措辭清單，是能力清單**
problem_state     期望值不符｜操作被拒｜狀態未推進｜實體缺失／重複｜可見性不符
responsibility    上述組合 → 哪個 Face 負責（mapping）
```

| | |
|---|---|
| 枚舉對象 | 維度值（封閉：實體型別有限、平台操作有限、問題形態有限） |
| 泛化來源 | 未列舉的**措辭**經由維度值歸類後，落在同一組合 → 自動被同一責任覆蓋 |
| 對 F2 的預期效果 | 「待對帳」與「狀態沒動」→ 同一 `problem_state=狀態未推進`；<br>「改到帳日」「存檔失敗」→ 同一 `operation_class` 家族下的 `操作被拒` |
| **真正的風險** | **分類負擔被下移而非消除**：query → 維度值 這一步仍需判斷。<br>若這一步跟 query → Face 一樣容易錯，B **一無所得**。 |
| 判定 | ✅ 候選，但**必須先證明分類負擔下移到了更好的位置**（見下方 admissibility gate） |

### C. Predicate / rule contract

責任 = 可執行的 applicability predicates：

```text
applicable_if:
  - entity_scope == 單一 bill
    AND operation_class ∈ {發送, 取消, 作廢, 刪除, 修改, 重發, 延期, 手動到帳}
    AND problem_state == 操作被拒
not_applicable_if:
  - entity_scope == 無                       # 通則型
  - problem_state == 期望值不符 AND target == 金額組成   # → billing_anomaly
```

| | |
|---|---|
| 枚舉對象 | 與 B 相同的維度值 ＋ **它們之間的邏輯關係** |
| 相對 B 多出來的東西 | **邊界可被靜態檢查**：兩個 Face 是否宣稱同一區域（overlap）、<br>是否有無人認領的區域（gap），可在**不跑任何 query** 的情況下算出來 |
| 相對 B 的代價 | 若 predicate 的 atom 仍是自由文字，C 只是「B ＋ 更多語法」，不多任何泛化能力 |
| 判定 | ✅ 候選，但**它的價值不在泛化**（泛化來自維度），**在邊界可稽核** |

---

## 建議：**B 供詞彙，C 供邊界代數**（不是三選一）

```text
泛化能力  ← 來自 B 的封閉維度（未列舉措辭經歸類後落入同一組合）
邊界正確  ← 來自 C 的 predicate 形式（overlap／gap 可靜態檢出，不需 query）
```

理由：F2 是**泛化**問題，只有 B 治得到；但 F4 那 2 筆暴露的是**邊界**問題
（`bd-02-b`／`bf-09-a`：ground-truth 與 D3 自寫的 `self_scope_rule` 對同一句話給出不同 Face）——
邊界問題在 B 之下**仍然存在且仍然看不見**，C 的形式讓它至少**可被算出來**。

⚠️ 但依業主裁定：**F4 那 2 筆不得為了變綠而增加專用規則**。
C 在此的角色是「讓這類衝突在 freeze 前就被靜態檢出並公開記錄」，
**不是**「拿它們當新版驗收證據」。它們是 diagnostic examples，僅此而已。

---

## Admissibility gate：proposal 必須先過這一關，才准進 D3-member-2

業主已定：「若 representation proposal 回答不了『為什麼比 enumeration 多了真正的泛化能力』，
就不要進 member-2」。本檔把該問題**操作化**成一條可判定的前置檢查：

> **G1（封閉性證據）**：`operation_class` 的值集 MUST 對照平台**實際操作面**（jgb2 的
> bill 操作 API／後台動作）逐項導出，並記錄該集合為**有限且可列舉**的證據。
> 若做不到——若操作集合其實開放——則 B 的封閉性前提不成立，**B 與 C 一併退場**。

> **G2（負擔下移證據）**：MUST 說明為什麼 `query → 維度值` 比 `query → Face` 更可靠。
> 目前的**論證**（尚非證據）：維度值可對照平台實體與操作**逐項查核**，
> 而 Face handles 是散文，無外部參照物。
> ⚠️ 這一條目前只是論證。若 member-2 實測顯示維度分類錯誤率與 Face 分類相當，
> **G2 即被反證，B 應退場**——不得改寫成「維度沒錯，是 evaluator 不好」。

G1 是**唯讀查核**（讀 jgb2 的操作面），不改任何檔、不進 production seam，
是 member-2 freeze **之前**的必要步驟。G2 只能由 member-2 的實測回答，
故 G2 必須**事前寫成 falsifier**，不能事後解釋。

---

## 事前承諾的 falsifier 與 negative control（**寫在產生新測資之前**）

### F2 falsifier（正向：不得因措辭未列舉而拒絕）

> 一個 applicability case **SHALL NOT** 僅因其具體動作詞／問題措辭未出現在
> handles／examples 中即被判 `not_applicable`，只要它符合 frozen responsibility dimensions。

失敗即代表 representation 沒有真的離開枚舉。

### Negative control（反向：不得因 lexical overlap 而接受）

> query 含有某個**已列舉**的動作詞，但其 responsibility dimensions **不匹配**時，
> **SHALL NOT** 判 `applicable`。

⚠️ 這一條是必要的對稱防線：只有 F2 falsifier 而無此控制，把 representation 寫得極寬鬆
即可全過——那是把 Round 1 的**單向過度拒絕**換成**單向過度放行**，不是進步。
Round 1 的 `過度放行 0` 是目前唯一的好性質，**不得在新版丟掉**。

### 兩者同時成立才算「離開枚舉」

```text
未列舉措辭 ＋ 維度匹配   → applicable      （F2 falsifier）
已列舉措辭 ＋ 維度不匹配 → not_applicable  （negative control）
```

---

## 本檔明確不做的事

```text
❌ 不寫 implementation、不定 JSON schema 欄位名（欄位名可與本檔不同，重點是封閉性）
❌ 不產生新的 challenge cohort（Round 1 cohort 已 burned，只能作 diagnostic）
❌ 不改 matching ruler（tolerance 0.058928 仍凍結未用）
❌ 不碰 production Face config schema／enable flag／manifest
❌ 不為 F4 的 2 筆增加專用規則
❌ 不宣稱 D3 family disposition 有任何變動（仍為 INSUFFICIENT_EVIDENCE）
```

## 下一步（依業主鎖定的順序）

```text
本檔 = 步驟 1（representation proposal）
  ↓
步驟 2  review representation only
  ↓
步驟 3  若 admissible（G1 過）→ freeze D3-member-2 contract
  ↓
步驟 4  產生**新的 isolated challenge cohort** ＋ 新 blind labels
  ↓
步驟 5  Experiment A → B
```

⚠️ 步驟 3 的前提是 **G1 有封閉性證據**。G1 未過則 B／C 一併退場，
D3 也回到 member-shape discovery，與 D1 同狀態。
