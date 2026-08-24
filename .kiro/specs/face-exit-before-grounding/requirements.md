# face-exit-before-grounding — Requirements（discovery，第一版）

> 2026-08-25｜語言 zh-TW｜phase：**discovery**｜status：**active**｜outcome：**unset**
> 來源：`conversational-routing-execution` 6.3 簽核（C4b NOT PASSED、gate CLOSED）
> 依賴：`routing-authority-model` **conditional，現在不 blocking**

## Core question（本 spec 要回答的唯一問題）

> **為什麼一個已成功進入 `bill_diagnosis`、且產品上屬於該 Face 的 query，
> production brain 會在 grounding 前產生 `scope=switch`？
> 這是 execution／contract defect，還是兩套既有 authority contract 的真實衝突？**

⚠️ **不得**改寫成「修正 `bill_diagnosis` 的 scope 判斷」——那會把題目降格成優化一句 prompt。

### ⚠️ 前提修正（業主 2026-08-25 定調，**先釘死**）

core question 寫的是「**已成功進入**且**產品上屬於**該 Face」——目前證據顯示
這句話混了**兩個不同命題**：

```text
成功進場   mechanism-level commitment（有人指定，或 retrieval 提議了這個 Face）
責任已成立 responsibility contract 認領了這個 query
```

`c4a-case-set-frozen.md` 明文 `execution_face` **不是** routing ownership label，
故「產品上屬於 `bill_diagnosis`」目前**無 production artifact 支持**（見 research.md F-3）。
本 spec 因此**不得**把「成功進場」當成「責任已成立」的證據；
兩者的關係正是 R3 contract map 要查清楚的東西。

### Escalation question（**不是**本 spec 要回答的問題）

> 當已成立的 Face entry 與 in-Face `scope` 判斷衝突時，什麼 authority 有權推翻 entry？

它只在本線得到 `AUTHORITY_CONFLICT_CONFIRMED` 後，成為送往 `routing-authority-model` 的
decision input。本 spec **SHALL NOT** 回答它。

---

## R1 重現機制，但不重跑 C4b acceptance

**WHEN** 需要觀察 `face_exit_before_grounding`，
**THEN** 本 spec **SHALL** 建立最小、低成本（可能為 deterministic）的 reproduction，
證明鏈為：

```text
Face entry → scope=switch → session close → reroute → Face entry → scope=switch → fallback
```

**AND** C4b 的 evidence **SHALL** 僅作 provenance 引用，
**SHALL NOT** 把本線的測試偽裝成原 C4b 的 acceptance 重跑。

## R2 找出 `scope=switch` 的真正 producer 與 inputs

**THEN** 本 spec **SHALL** 追到實際 production code，逐項記錄：
誰組 prompt／誰載入 rules／誰呼叫 model／Face config・state・query・history 各餵了什麼／
輸出在哪裡被 consume。

**SHALL NOT** 停在「brain 說 switch」這種層級的結論。

## R3 entry authority 與 in-Face scope authority 的 contract map

**THEN** 本 spec **SHALL** 產出對照表，且**只記錄、不裁決**：

```text
entry producer ／ entry evidence ／ entry authority
scope producer ／ scope inputs ／ scope contract ／ scope consumer
irreversible effect
```

**目的**：回答兩邊究竟是在看同一個 responsibility contract，
還是根本是兩套不同語義。

## R4 逐項 falsify deterministic defect candidates

**THEN** 本 spec **SHALL** 對下列候選逐一證偽或證實，
且此工作 **SHALL NOT** 需要先決定誰有最終 authority：

```text
載錯 rules ／ rules・context 被截斷 ／ Face identity・state 不一致 ／
reroute 後殘留狀態 ／ responsibility context 未傳入 ／
producer 與 consumer 的 contract mismatch
```

## R5 唯一的分流裁決

**THEN** 本 spec 的結論 **SHALL** 落在且僅落在下列五者之一：

```text
IMPLEMENTATION_DEFECT_CONFIRMED
CONTRACT_DEFECT_CONFIRMED
AUTHORITY_CONFLICT_CONFIRMED
RESPONSIBILITY_GAP_CONFIRMED     ← 業主 2026-08-25 新增（**其後由 B″ 反證**）
OWNER_EXISTS_BUT_NOT_PROPOSED    ← 業主 2026-08-25 新增（第六類）
INSUFFICIENT_EVIDENCE
```

### `OWNER_EXISTS_BUT_NOT_PROPOSED`（業主定義，逐字）

> 已找到至少一個 Face，在其 authoritative、production-equivalent in-session context 下
> **穩定接受**該 query；但實際 entry-routing path 在**已觀測的重現**中未提出該 Face，
> 而提出其他會拒絕該 query 的 Face。

三條護欄：

```text
❌ 不等於 contract_closeout 應取得更高 routing priority
❌ 不等於目前 routing implementation 一定有 bug
❌ 不等於已證明 contract_closeout 在架構上 unreachable
```

⚠️ **保留但現在不得使用**的更強子結論：若後續 static tracing 證明現行 entry mechanism
**根本沒有任何 production path** 能從本 query 提出 `contract_closeout`，才可升級為
`OWNER_UNREACHABLE_BY_CURRENT_ENTRY_CONTRACT`。

**目前 outcome（2026-08-25，業主裁定）**：

```text
RESPONSIBILITY_GAP_CONFIRMED    **REFUTED**（B″：contract_closeout 3/3 stay）
OWNER_EXISTS_BUT_NOT_PROPOSED   **CONFIRMED**
```

⚠️ 不再是 `INSUFFICIENT_EVIDENCE`——現在不是「不知道發生什麼」，
而是原分類空間漏了一個已被實驗辨識出的形狀。

### `RESPONSIBILITY_GAP_CONFIRMED`（**操作化定義**，2026-08-25 第二版）

> 在本 query 的 **runtime delegation closure 已被追至終點**，
> 且所有被 authoritative responsibility evaluation **實際提出為候選 owner** 的 Face，
> 在其 **production-equivalent in-session context** 下均不接受責任，
> 並且**不存在尚未檢驗的新 delegation target**。

⚠️ 第一版措辭為「未被**任何候選 Face** 接受為自身責任／形成 mutual delegation
／no-owner 狀態」。B′ 實測發現 candidate set **不是封閉的兩元素集合**
（runtime 指名了第三個 Face），故將「任何候選 Face」**操作化**為上述 closure 條件。
**這不是改結論救測試**，而是把原本模糊的量詞定死；三條護欄不變。

三條護欄：

```text
❌ 不等於「diag-01 應該屬於 bill_diagnosis」
❌ 不等於「billing_anomaly 的規則寫錯」
❌ 不等於「選一邊改到測試變綠」
✅ 只允許證明：現有 authoritative contracts 的**聯集**沒有形成完整 responsibility coverage
```

⚠️ **為何不硬塞既有兩類**：`AUTHORITY_CONFLICT_CONFIRMED` 的語義是「兩套契約各自正確卻
給出**相反**決定」，此處是「兩邊都說**不是我**」——no-owner／mutual-delegation，不是 winner conflict。
`CONTRACT_DEFECT_CONFIRMED` 已刻意定窄為**傳遞／一致性**問題，而 F-2 顯示規則載對、
brain 也照規則走；若把「規則內容彼此留下責任洞」也叫 contract defect，
就會把 **contract implementation defect** 與 **responsibility allocation defect** 混成一類。

### `CONTRACT_DEFECT_CONFIRMED` 的窄定義（**不得放寬**）

```text
✅ consumer 實際收到的 contract 與既有 authoritative Face responsibility 不一致
✅ contract 在轉換／傳遞過程中丟失語義
❌ **不得**用來表示「我們覺得 scope contract 應該改成另一套產品規則」
   ——後者已是 normative decision，屬 routing-authority-model
```

## R6 停止條件（自 snapshot 原封升格）

**IF** 確認 entry authority 與 scope authority **各自依其現有 authoritative contract
正確運作**，但對同一合法 query 得出相反 routing decision，
**THEN** 本 spec **SHALL** 停止於 `AUTHORITY_CONFLICT_CONFIRMED`；

```text
SHALL NOT 選擇 winner
SHALL NOT 修改任一 authority contract 以求測試變綠
→ 後續交由 routing-authority-model / Responsibility Governance Decision Record
→ 升級方式＝產生新的 escalation artifact，**不是**改對方的歷史快照或狀態
```

### R6.2 第二條停止條件（責任洞）

**IF** R1／R3／R4 共同支持下列全部：

```text
correct rules loaded
＋ correct Face identity／state
＋ no context truncation
＋ no reroute contamination
＋ no producer／consumer mismatch
＋ reproducible mutual rejection
```

**THEN** 本 spec **SHALL** 停止於 `RESPONSIBILITY_GAP_CONFIRMED`，
且 **SHALL NOT** 自行指定 owner；同樣以新 escalation artifact 升級至
`Responsibility Governance Decision Record`。

## R7 反假綠：「讓 `diag-01` 不再退出」**不是** acceptance criterion

**THE** acceptance of this spec **SHALL** be
「證據足以歸因 failure mechanism」，
**NOT**「`diag-01` 留在 Face 裡」。

⚠️ 明文封死這條捷徑：

```text
改一句 scope prompt → diag-01 留下來 → 綠 → 宣稱找到 root cause    ← **禁止**
```

修復若要發生，是**歸因之後的獨立階段**，不在本 spec 的 discovery 範圍內。

## R8 不得越界的清單

```text
❌ 選 authority winner（discovery 可做，選 winner 不行）
❌ 合併兩線，或改動 routing-authority-model 現有的 BLOCKED 狀態
❌ 以「scope prompt 太嚴」之類假說直接當修法
❌ 回頭改 conversational-routing-execution 的 ruler／案例／fixture／凍結參數
❌ 把本線的發現回填 6.2／6.3 的結果
❌ 一邊修 production 行為、一邊改變要量的東西
```

## R9 candidate set 的界定（**descriptive discovery rule**）

**THE** candidate set for this query **SHALL NOT** be bounded by researcher-selected Faces;
it **SHALL** be bounded by the Face delegation closure explicitly produced by
runtime authoritative scope evaluation.

```text
初始已觀測候選   bill_diagnosis
runtime 明確 delegate → billing_anomaly → contract_closeout → （續）

終止條件（任一）
A. 某 Face stable stay（接受責任）
B. delegation 回到已測 Face → cycle
C. Face switch 但沒有可辨識的新 owner
D. 指向不存在／disabled／非 Face 的 destination
```

⚠️ 這是**描述性**規則，**不**替 governance 決定誰「應該」負責。
