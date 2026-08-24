# face-exit-before-grounding — Requirements（discovery，第一版）

> 2026-08-25｜語言 zh-TW｜phase：**discovery**｜status：**active**｜outcome：**unset**
> 來源：`conversational-routing-execution` 6.3 簽核（C4b NOT PASSED、gate CLOSED）
> 依賴：`routing-authority-model` **conditional，現在不 blocking**

## Core question（本 spec 要回答的唯一問題）

> **為什麼一個已成功進入 `bill_diagnosis`、且產品上屬於該 Face 的 query，
> production brain 會在 grounding 前產生 `scope=switch`？
> 這是 execution／contract defect，還是兩套既有 authority contract 的真實衝突？**

⚠️ **不得**改寫成「修正 `bill_diagnosis` 的 scope 判斷」——那會把題目降格成優化一句 prompt。

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

**THEN** 本 spec 的結論 **SHALL** 落在且僅落在下列四者之一：

```text
IMPLEMENTATION_DEFECT_CONFIRMED
CONTRACT_DEFECT_CONFIRMED
AUTHORITY_CONFLICT_CONFIRMED
INSUFFICIENT_EVIDENCE
```

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
