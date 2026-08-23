# Post-mortem 01：REFUTED candidate 的失敗解剖

> 2026-08-24｜語言 zh-TW｜_Requirements: 2.4, 9.1_
> **身分**：REFUTED candidate 的 post-mortem。**不是**「再分析一下看要不要判 REFUTED」。
> 用途：決定**下一版該研究什麼**；**不產出推薦方案**。

## 中心命題（開放，未預設答案）

> **A（lexical coverage 不足）與 B（Level-A authority 過窄）是兩個獨立缺口，
> 還是同一個更深結構問題的兩個表徵——內容型 KB 同時承載 answer evidence 與
> Routing Hint，導致系統必須在 query side 額外猜測「這個 Hint 這次到底該不該生效」？**

---

# 第一層：已證實事實（不含任何「因此架構應該…」）

```text
Task 5   frozen／known cases 可通過（bilateral 8/8、robustness 4/40、blast 6/6）
Task 6   unseen holdout 上 gate ON == OFF，**50/50 逐筆相同**

A        abstain 32/50（64%）→ lexical evidence coverage 不足
B        block 11 → effective suppression 0；需要修正的 misroute 落在 rollout scope 外

cross-face  未見 rule 問句被 **8 個不同 Face** 吸走，橫跨 3 個 family：
            帳務 7（條件診斷：帳單 ×2、滯納金 ×2、帳單設定引導、繳費金流排障、發票）
            合約 2（退租收尾、建約引導）｜物件 1（物件操作引導）
```

## rule 側 10 筆失敗的逐筆歸因

| # | 問句 | 落點 Face | 是否在 Level A | gate verdict | 歸因 |
|---|---|---|---|---|---|
| 8 | 點退完之後的費用是系統幫我算… | 條件診斷：帳單 | **A 內** | abstain | **A** |
| 43 | 這個月總共收了多少，哪裡看得到 | 條件診斷：帳單 | **A 內** | abstain | **A** |
| 10 | 滯納金到底是用什麼方式在計算的？ | 滯納金 | A 外 | abstain | A |
| 20 | 逾期要幾天以後才開始算滯那金 | 滯納金 | A 外 | abstain | A |
| 18 | 超商代碼繳費金額有沒有上限啊 | 繳費金流排障 | A 外 | abstain | A |
| 31 | 發票能不能改成開公司抬頭 | 發票 | A 外 | abstain | A |
| 34 | 代收的水電費要另外開一張… | 建約引導 | A 外 | abstain | A |
| 11 | 已經發給房客的帳單還能改金額嗎 | 物件操作引導 | A 外 | **block** | **B** |
| 30 | 押金退還也需要開一張帳單嗎 | 退租收尾 | A 外 | **block** | **B** |
| 4 | 刷卡繳的話手續費是誰要吸收 | 帳單設定引導 | A 外 | allow | 其他 |

```text
A 覆蓋不足 7｜B 權限不及 2｜其他 1
```

⚠️ **#4 是第三種失敗形態**，不屬 A 也不屬 B——**正向特徵誤命中**（false positive）。
實測 span 逐字如下：

```text
utterance : 刷卡繳的話手續費是誰要吸收
pattern   : problem_report = 為什麼|怎麼會|怪怪的|失敗|不了|不出|卡
matched   : 「卡」          ← 來自「刷**卡**」（信用卡），非「**卡**住」
verdict   : allow（有正向、無反向）→ 不抑制
```

`卡` 作為「卡住」的問題徵候被寫進正向特徵，卻在「刷卡」中命中——
**字面規則沒有詞義邊界**。此形態在 holdout 僅 1 筆，
但它證明 lexical 特徵**兩個方向都會錯**：不只覆蓋不足（漏判），也會誤判。
⚠️ 這一筆同時說明：把單字加進 pattern 表的做法，**每加一條就同時擴大漏判與誤判的風險面**。

## instance 側 3 筆未命中

```text
#3  我上禮拜排好的那張怎麼到現在都還沒寄出去 → billing_anomaly（期望 bill_diagnosis）
#22 為什麼我按了發送之後完全沒反應          → single（期望 bill_diagnosis）
#35 狀態一直卡在待發送，是不是哪裡出問題      → billing_flow（期望 bill_diagnosis）
```

三筆的 gate verdict 皆非 block（abstain／allow／allow），
**gate 未參與這三次錯誤**——屬既有 retrieval／facet 選擇行為。

---

# 第二層：A／B 可分離性（反事實問法）

**反事實 1：假設 extractor 完美，rollout scope 維持現況——問題是否仍存在？**

**會。** 直接證據：#11、#30 的 gate **已經判對了 `block`**，
但落點 Face 在 Level A 之外 → `gate_applies_to=False` → 未抑制。
```text
∴ A 修好不足以解 B（實測反證，非推論）
```

**反事實 2：假設 authority 擴到所有需要抑制的 Face，extractor 維持現況——問題是否仍存在？**

**會。** 直接證據：#8、#43 的落點 **本來就在 Level A 內**（`bill_diagnosis`），
authority 完備，卻因 `abstain` 而未抑制。
```text
∴ B 修好不足以解 A（實測反證，非推論）
```

⚠️ **這兩組是 holdout 內建的自然對照**：同一批資料同時出現
「有權限但無訊號」與「有訊號但無權限」，兩個方向各自被實測釘住。

```text
CONFIRMED：A 與 B 在機制上可分離；任一單獨修復皆不足。
```

**但這只回答「兩者都要修」，未回答「為什麼系統同時需要這兩種補丁」。**

---

# 第三層：共同上游原因——三個競爭假說

## H1：KB-level Routing Hint overloading 是共同上游

```text
content KB 命中 → categories 同時提出 Face Hint
→ Hint 本身不帶「這次是 rule 還是 instance」的資訊
→ query side 被迫額外做 applicability 判斷 → lexical coverage 成為瓶頸（A）
→ 而 Hint 可來自任何 Face → 又必須另外定義 suppress authority（B）
```

**支持證據**：本 holdout 的 8 個落點 Face 分屬 3 個 family，
其 Hint 全部來自「內容型 KB 的 categories」這一條路徑。
**反面**：本文件無法排除 H2／H3；且 gap 階段已判 L2 `INSUFFICIENT_EVIDENCE`。

## H2：缺少 first-class query intent representation

也可能 Hint 掛在 KB 上本身不是錯的，而是系統缺少
`rule／instance／action／lookup` 這類**第一級 query semantics**，
使**任何** Routing Hint 都無法被正確消費。

**支持證據**：本案 candidate 正是在補一個臨時的、字面的 intent representation，
而它在未見分布上 64% 無法判定——這與「缺少正式表示法」的預期一致。
**這會重新打開 L3，而非直接推向 L2／L6。**

## H3：Face taxonomy／responsibility boundary 不完整

rule 問句跑進 8 個不同 Face，也可能表示
**Face 的 applicability contract 本身沒有定義「哪些 query 類型可以進」**。

**支持證據**：erratum 01 已被迫回答「哪些 Hint 屬同一 instance-routing responsibility」，
當時就發現 Level A 白名單與產品責任邊界不相容；holdout 把同一問題放大到跨 family。
**若 H3 成立**，即使把 Routing Hint 與 KB 拆開，仍不知道 Hint 何時有效。
**這會重新打開 L4／C 層，而不只是資料 hygiene。**

---

# 第四層：每個假說的 falsifier

| 假說 | 什麼觀察會推翻它 |
|---|---|
| **H1** | 把 Routing Hint 自 content KB 分離後，**取不到 lexical extractor 原本沒有的新資訊**。⚠️ 若分離後只是「另一張 routing-only KB ＋ 再做一次 semantic similarity」，那就是 **3.4 anchor 問題換皮**，H1 並未成立。H1 要真正成立，須指出一個**不同的 authority source**（explicit intent／operation contract、Face applicability contract、structured action metadata、transaction／query semantics 之一），而非把同一段 routing metadata 搬到另一張表 |
| **H2** | 導入 first-class intent representation 後，rule／instance 的判定仍需回到表層措辭，或其覆蓋率同樣在未見分布上崩塌 |
| **H3** | 為每個 Face 補齊 applicability contract 後，跨 family 誤吸仍持續——代表問題不在 Face 契約層 |

---

# 結論分級

```text
CONFIRMED
- A／B 可分離；任一單獨修復不足（holdout 內建雙向對照：#11/#30 vs #8/#43）
- failure 已跨越 bill_diagnosis 單一 Face：8 個 Face、3 個 family
- deterministic lexical representation 對 unseen wording 覆蓋不足（abstain 64%）
- lexical 特徵**雙向皆會錯**：除覆蓋不足外，另有 1 筆正向特徵誤命中
  （#4：`problem_report` 的 `卡` 命中「刷**卡**」，字面規則無詞義邊界）
- gate 未參與 instance 側 3 筆 facet 錯誤（屬既有 retrieval 行為）

SUPPORTED HYPOTHESIS
- H1 KB Hint overloading 可能是共同上游原因（未排除 H2／H3）

INSUFFICIENT EVIDENCE
- L2／L3／L4／L6 哪一層應成為 v2 的主責任層
```

⚠️ **144 exposure surface 的定性更新（但不越界）**：
holdout 提供了比 gap 階段更強的證據——**cross-face manifestation CONFIRMED**，
問題不只出現在原三筆 billing regression。
但 144 **仍是 exposure population，不是 confirmed defects**；
**SHALL NOT** 寫成「144 筆全部有 defect」。

## 本文件不產出推薦方案

是否開啟 v2 discovery、以及哪一層擔任主責任層，**須另行決定**——
本 post-mortem 只把「下一版該研究什麼」的選項與各自的 falsifier 攤開。
