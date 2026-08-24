# R-e discovery：資格條件與搜尋範圍（**凍結於查核之前**）

> 2026-08-24｜語言 zh-TW｜業主裁定：走 **(c)**——不重開 D1、不只走 D3，
> 做**最後一個窄 discovery**。
> 前置：`qualified-source-semantic-role-review.md`（`b4b2b90`）

## 唯一問題

> **Does an authoritative R-e mapping already exist,
> or can it be mechanically derived from existing runtime bindings?**

R-e ＝ 從**已驗證的 runtime facts** 到 **responsible Face** 的那條箭頭：

```text
query
 ↓
N1／N2／N3  →  entity exists／belongs／active｜instance cardinality｜viewer visibility
 ↓                       ────────── 已有 runtime-binding proof（inventory 已證）
 ↓
responsible Face X       ────────── **這條箭頭目前沒有 qualified authority**
```

⚠️ **本輪不得直接寫「必須新增新表／registry」**。
先判斷「authority source 是否必須新增」，**再**決定承載方式。

## 在本問題回答之前，全部凍結

```text
D1  不開 member-2
D3  不開 member-next
D4  不開
D2  仍 deferred
```

---

## 為何 N1／N2 不足以直接重開 D1（記錄理由，避免下輪重問）

N1／N2 確實避開了 Round 1 的 F1——不再讓 generic evaluator 判「這句到底有沒有指涉某一筆」，
改由平台事實證明。但 D1 原本要服務的是 `query × candidate Face applicability`。若直接做成：

```text
candidate Face = retrieval Hint 給的 X
＋ N1／N2 = 這是某一筆真實帳單
→ allow Face X
```

那只是把「這是 instance」**偷換**成「所以 retrieval 提出的 Face X 是對的」——
**重演 v1 的核心錯誤**，只是 authority 從 lexical evidence 換成 API proof。

```text
N1／N2 證明「這句確實指向 bill #123」
但仍無法區分 bill_diagnosis ／ billing_anomaly ／ billing_flow
→ N1／N2 是 D1 新 member 的**必要**輸入，**尚非充分**輸入
```

## 為何也不只走 D3

若 D3 下一版做成「Face X 宣告我需要 N1＋N2 → runtime facts 符合 → Face X applicable」，
關鍵問題仍在：**誰授權 Face X 有資格把 N1／N2 解讀成自己的 applicability proof？**

```text
若答案仍是 Face 自己的後台散文／metadata：
  runtime-binding fact ＋ **non-binding** responsibility mapping
  → 整體 authority **仍未閉合**
```

（inventory 的 N6 已判：`grounding_scope.endpoint／params` 是**宣告**，E1 不成立。）

---

## RE1–RE6：合格 R-e mapping 的資格條件（**凍結**）

### RE1｜Face-specific

> MUST 能區分**至少兩個共享相同 entity proof** 的 Faces。

⚠️ 這是本輪的鑑別力底線：三個診斷面向共享同一組 bill proof，分不開就等於沒有 R-e。

### RE2｜Runtime-authoritative

> MUST NOT 是 Face 自述、KB category、散文 handles。

### RE3｜Query-decision relevant

> MUST 對**這次** routing decision 可變。
> 每個 query 都固定不變的 metadata ＝ **impostor**（inventory 的 N4／P3／P6 即此形態）。

### RE4｜Composable with qualified facts

> MUST 能消費 N1／N2／N3 類 proof；
> 且 **absence of proof 仍保持 UNKNOWN**（E5 不因本輪而放寬）。

### RE5｜Executable ／ enforceable

> MUST NOT 只靠「新增 Face 時記得寫對」。
> ⚠️ 這正是 R4 已 CONFIRMED 的制度失敗形態（無 enforcement 的人工流程約束）。

### RE6｜Open-Face compatible

> 新 Face 可加入，而**不要求預先封閉所有 Face semantic space**。

⚠️ RE6 是 G1 新增的限制：Face 集合後台可增已是既成事實，
任何要求「先知道全部 Face」的 mapping **當場不合格**。

---

## 搜尋範圍（**凍結**）：只掃 responsibility binding surface

**不再掃 entity facts**——semantic-role review 已證明那只會堆在箭頭左側。

```text
S-a  Face ↔ executable capability
S-b  Face ↔ API／action contract
S-c  Face ↔ enforced prerequisite
S-d  Face ↔ machine-consumable routing responsibility
```

⚠️ **禁止事後解讀**：不得「看到某個 endpoint 就把它硬解讀成 responsibility」。
一個 binding 要算數，MUST 指出**誰 enforce 它**、以及**不遵守會發生什麼**。

### 明確在範圍外

```text
✗ 再找新的 entity-side proof（箭頭左邊，已充分）
✗ 知識內容／Face RULES 散文（RE2 當場不合格）
✗ 前端／後台 UI
✗ 尚未上線的分支功能（遇到須標為 out-of-scope）
```

---

## ⚠️ Prior-exposure declaration（同樣**不能宣稱 blind**）

本輪同樣在已讀過部分程式的情況下撰寫。除 inventory 已列的曝光清單外，另須揭露：

```text
執行 inventory 時，我已看到 conversational_engine 於呼叫 API 時會傳遞
`face=state.get("face") or _domain_key(config)` 給 formatter
（services/conversational_engine.py:900-903 附近），註解自陳
「決定性 formatter 選 fact 集」。

⚠️ 這使我**已經知道**存在某種 face → fact-set 的分派點。
   本輪 MUST 對它逐條套用 RE1–RE6，且**不得**因為它是唯一想得到的候選就從寬。
```

**防護**：已曝光項目**不得**因此取得優先地位，其 disposition MUST 標記 `prior_exposed=true`。

---

## 三種結局（**事前寫定，不看到結果再選**）

```text
結局 A｜找到既有 qualified R-e
  → 再看 provenance：
     routing-owned        → D1 可能取得完整新 shape
     Face-owned executable → D3 可能取得新 shape
     中立 registry／capability binding → 可能 D1+D3，或日後 D4

結局 B｜沒有既有 R-e，但可由既有 machine authority **機械導出**
  → 可能不需新增語義 authority，只需**顯式化既有 binding**
  ⚠️ MUST 是真的 machine-derived；**不得**又從 Face RULES 轉譯（那是 RE2 不合格）

結局 C｜既沒有，也不能機械導出
  → 才有足夠證據寫下這條新 architecture requirement：
    **在 audited architecture 中，R1 所需的 facet-specific applicability information
      沒有現成 authoritative source；下一個 admissible design MUST 新增一個
      first-class responsibility authority。**
  → 且 N1／N2／N3 成為該新 authority 未來可**消費**的已證成 runtime evidence，
    **不是** authority 本身
```

## 輸出限制

```text
只輸出：responsibility binding surface 的 inventory ＋ 逐條 RE1–RE6 disposition ＋ 結局判定

❌ 不設計 member、不開 D1／D3／D4
❌ 不宣稱「必須新增新表／registry」——承載方式是**之後**的決定
❌ 不改 family disposition
❌ 不動 production；不產測資；ruler 0.058928 仍凍結未用
❌ 不重跑 Round 1 cohort（burned）
```
