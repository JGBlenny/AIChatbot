# R10：Retrieval Responsibility Identity —— **立案（⛔ 尚未實作）**

## 觸發：`ENTRY_ALIAS ≠ RESPONSIBILITY`

```text
ROW_LEVEL_REPRESENTATION_FOR_FACET_LEVEL_RESPONSIBILITY
= **CONFIRMED DESIGN MISMATCH**（至少對「一種講法一筆」這批 anchors 成立）
```

三個互相衝突的需求：

```text
entry row              希望保留不同講法 ⇒ 增加進場 recall
semantic responsibility  facet 層級，只有一份
retrieval_representation 目前卻是 **per-row**
```

於是兩條路都不對：

```text
3939 = A、3940 = A   ⇒ 兩份**幾乎完全相同**的 scoring document
3939 = A1、3940 = A2 ⇒ 發明**不存在**的 responsibility distinction
```

## 已裁的設計方向（業主 2026-08-29）

> **Entry identity 與 responsibility identity 必須分開。**

```text
row     = entry alias / utterance evidence
facet   = responsibility owner（目前）
contract = responsibility-level canonical
```
⚠️ 這是**設計方向裁定**，⛔ **不是**授權把 schema 從 per-row 改成 per-facet。

## 三案比較（primary candidate = C）

```text
A per-row（現況）
  ⛔ 對刻意重複的 anchor variants 不足；兩者皆錯（見上）

B per-facet
  ✅ 同 facet 共用一份 semantic contract
  ⚠️ 但若某 facet 未來**真的**長出兩個 responsibility，又會重演今天的粒度問題
     例：late_fee = { mechanism_explanation, instance_diagnosis }

C explicit `responsibility_id`  ← **primary candidate**
  多個 entry rows → 同一 responsibility；一個 facet 可有 1..n 個 responsibility
  responsibility_id 目前**可能剛好等於** facet，但⚠️ 未來未必永遠如此
```

C 的樣貌：

```text
responsibility_id = late_fee_instance_diagnosis
canonical retrieval_representation
  = 查詢某一筆實際滯納金的產生原因、金額、計算與相關狀態
entry aliases: 3939、3940
⇒ 兩個 utterance 都保留；semantic contract 只有一份；
  ⛔ 不製造假 sub-intent；未來同 facet 長出新責任也不必拆 facet
```

## ⚠️ 必須一併回答的 caveat（⛔ 只給 responsibility_id 還不夠）

```text
即使採 C，也**不能**讓兩個 row 共用同一 embedding 後照舊各自參與 ranking
—— 那仍留下 duplicate candidates（3498 的 mutation 已實證 ranking competition）。
```

⇒ 新設計必須明確回答：

```text
entry alias 在 retrieval 的**哪一層**使用？
canonical responsibility 在 scoring 的**哪一層**使用？
```

可能的目標形態：

```text
alias text                → recall / nomination evidence
responsibility representation → semantic scoring / authority identity
同 responsibility 的多個 alias → **scoring 前 collapse 成一個 responsibility candidate**
```

⇒ 才真正解掉「多 entry variants 保留 recall，但**不互相製造 ranking competition**」。

## 現階段狀態（⛔ 不實作）

```text
3939／3940  applicability = instance；role = ENTRY_ALIAS
            shared responsibility = late_fee facet / B
            retrieval_representation = **NOT_POPULATED_PENDING_ALIAS_GOVERNANCE**
LEVEL_A_V2  UNCHANGED = 9 rows（⛔ 不需要 V3——這是 broader authority truth，
            ⛔ 不是 Level-A expansion）
```
