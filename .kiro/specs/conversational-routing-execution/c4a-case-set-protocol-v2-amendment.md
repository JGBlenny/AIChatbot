# C4a case-set protocol **v2 amendment**（凍結於產生任何 synthetic case 之前）

> 2026-08-24｜語言 zh-TW
> **provenance：`2721e85`（v1 admission result — diagnosis 1/2）**
> 前身：`c4a-case-set-protocol-frozen.md`（**v1，維持 FROZEN，一字未改**）
> **狀態：FROZEN**

## 為何需要 amendment 而不是「改一下 v1」

v1 的 admission 實跑結果證明：

> **v1 的 source policy 無法產生它自己事前要求的 `bill_diagnosis` 2 案。**

```text
這不是 implementation failure
也不是 case failure
而是 **protocol feasibility failure**
```

⚠️ 因此**不得**偷偷改 v1 的 §6 再宣稱「原 protocol 未變」。
v1 連同其 feasibility 判定完整保留；本檔以**版本化 amendment** 記錄唯一的變更。

⚠️ 附帶價值：這次 admission failure **證明 frozen protocol 真的會咬**——
它沒有「無論素材長什麼樣都能湊出四案」。

## 唯一的變更

> `bill_diagnosis` **MAY** use protocol-generated cases **only to satisfy the pre-frozen
> case-count／fixture-diversity requirement after the pre-existing candidate pool is
> exhausted by A-1～A-4.**

```text
✅ 本檔只擴張 diagnosis 的 source eligibility
❌ 不動 N=2｜不動 A-1～A-4｜不動 C-1a／C-1b／C-2／C-3
❌ 不動 §3 可看／不可看｜不動 §4（required_grounding_facts 屬 5.2）
❌ 不動 §9 claim ceiling
❌ **不擴 4.4 fixture**（見下方「為何不採 (ii)」）
```

### 為何不採 (ii) 擴 fixture 建模 `details`

`details` 確有 External 契約依據，但**現在**擴它的直接動機是「讓被 admission 排除的既有 query
重新可測」：

```text
case admission 不足 → 擴 fixture capability → 原本不能 ground 的 case 變得能 ground
```

那不是不合法的 fidelity 工作，但**不應被用來救本輪 case-set composition**。
若未來本來就要完整建模 `details`，**另立 fixture-fidelity 工作**再做，
不得與 C4a cohort admission 綁在一起。

### 為何不採 (iii) 降為 1 案

N=2 承擔的是 **case→fixture identity 的反證功能**（C-1a／C-1b）。
降成 1 案會讓該面向直接失去 constant-record falsifier——**拒絕**。

---

## D-1～D-8：synthetic case 的生成條件（**產生前鎖死**）

```text
D-1  只能使用 **frozen External projection 已存在**的 fact
D-2  該 fact **必須已存在於 frozen 4.4 fixture**
D-3  不得查看 formatter output
D-4  不得查看 adapter ／ 5.3 execution result
D-5  不得新增 fixture field
D-6  ⚠️ 不得使用被 admission 排除的需求（details composition ／ receipt amount）的
     **「簡化版」**來救回它
D-7  必須綁與既有 admitted diagnosis case **不同**的 fixture_bill_id
D-8  inclusion 不得引用目前 routing 結果
```

### ⚠️ D-6 是本 amendment 最容易被繞過的一條

否則表面走 synthetic，實際是把

```text
「金額怎麼算出來的」（已被排除：需 details composition）
```

偷偷改寫成

```text
「金額是多少」
```

再宣稱多了一個獨立案例。**那仍是 post-hoc case engineering。**

## synthetic case **不必**追求新的自然語言能力

本輪不是 generalization test。第二個 diagnosis case 的目的是：

> **用另一筆 fixture，驗相同 execution contract 不會永遠黏在第一筆資料。**

故只要依本協議從 frozen projection／fixture 找到一個可 ground 的 bill-specific request、
且綁不同 fixture，即為足夠。刻意追求語意多樣性反而不乾淨——
N=2 的事前 justification 本來就是 **constant-record falsifier**，不是語言覆蓋。

---

## 被排除的三筆：disposition（**保留，不得從紀錄消失**）

```text
disposition = NOT_ADMITTED_TO_CURRENT_C4A_COHORT
（**不是** regression，**不是** failed grounding）
```

兩類缺口性質**不同**，須分開記：

```text
【fixture 缺口】「金額怎麼算出來的」／「怎麼會是這個數字」
  External API **理論上**提供 `details`，但 frozen fixture 未建模
  → 現行 C4a cohort 測不到；屬**測資**層

【contract capability gap】「收據金額多少」
  收據金額**不在** External projection 的 33 欄內
  → 現行 External 契約**本身**就 ground 不了；屬**契約能力**層
  ⚠️ 這一筆不是 fixture 缺口——不得因本輪不納入就當它不存在
```

## 凍結後的順序（其餘沿用 v1 §8）

```text
本 amendment freeze（本檔）
  ↓
依 v1＋v2 產生**完整 4-case cohort**（diagnosis 2 ＋ anomaly 2）
  ↓
**一次** freeze 整個 case set
  ↓
5.2 required_grounding_facts
```

⚠️ **不得**分兩次凍結 case set（diagnosis 先凍、anomaly 後凍）——會造成不一致。
