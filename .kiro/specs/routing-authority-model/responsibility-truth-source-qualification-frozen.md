# Responsibility Truth Source Qualification（O1–O6）：**凍結於查核之前**

> 2026-08-24｜語言 zh-TW｜業主裁定：封口 A／B／C carrier comparison（ADMISSIBLE = 0）；
> 下一步研究 **authority origin ／ responsibility governance**，
> **不是**再發明 carrier 或 classifier。
> 前置：`carrier-comparison-result.md`（CLOSED，`36b6d85`）

## 唯一核心問題

> **在這個產品中，什麼來源有資格制定
> 「Face X 對情境 Y 負責」這種 normative responsibility claim？**

⚠️ 本輪研究的**不再是**「系統能不能從資料推導出 Face」。
前三輪的結果已強烈顯示兩種資訊性質不同：

```text
platform fact        = **descriptive truth**「現在世界是什麼狀態」
                       bill exists／viewer can see bill／payment pending

Face responsibility  = **normative product truth**「產品決定由誰處理這種狀態」
                       「這種情況應由 billing_flow 而不是 bill_diagnosis 處理」
```

> **Hypothesis（尚未升為結論）**：
> R-e 之所以一直找不到，可能**不是**因為它是遺失的 runtime fact，
> 而是因為它根本是一個**尚未 first-class 化的產品規範**。

⚠️ 本檔**不得**把上述 hypothesis 當成已證結論使用；它是本輪要驗的對象。

## 這輪先找 **authority origin 的資格**，不是 authority owner 的名字

```text
❌ 不要一開始就問「是不是 product owner？」——那是太快選答案
✅ 先定資格（O1–O6），再看有沒有來源符合
```

---

## O1–O6：合格 responsibility truth source 的資格條件（**凍結**）

### O1｜Normative legitimacy

> 該來源 MUST 真的有資格**決定產品責任**，
> 而不是**描述目前程式怎麼跑**。

⚠️ 「現行程式這樣分流」不是責任正當性，只是現況描述——
B1／B2／B3 全部落在這一類（描述現況，非制定責任）。

### O2｜Independence from candidate

> Face **MUST NOT** 單方面產生自己的責任權限。

⚠️ 沿用 G-d 與 carrier B 的反證：self-enrollment 不成立。

### O3｜Explicit responsibility semantics

> MUST 能**直接**支持「Face X 對條件 Y 有／沒有責任」，
> **不得**只靠人事後解讀。

⚠️ 這一條淘汰「散文式 RULES」——需要人讀懂才知道責任邊界者，不算 explicit。

### O4｜Versionability

> 責任變更 MUST 可知：**誰改、何時改、哪個版本生效**。

### O5｜Enrollment authority

> 新 Face 的 responsibility claim MUST 經過某個**合法的 admission process**；
> **不得**新增一個 DB row 就取得權力。

⚠️ 直接對應 carrier B 的 X-2／X-5 FAIL。

### O6｜Executable handoff

> authority truth MUST 最終能被轉成
> **Responsibility Authority Contract 可消費的 binding**；
> **不得**永遠只活在人腦／會議紀錄。

### ⚠️ O6 的重要區別（**不得誤讀**）

```text
O6 **不代表** 原始 authority 必須是**機器產生**的。
```

產品責任本來就可能需要**人做 normative judgment**。
R4 反證的是：

```text
人工規約 **不能是 correctness 的唯一 enforcement**
```

它**沒有**證明：

```text
所有 responsibility truth 都必須由機器自行發現
```

故下列路徑**不違反 R4**：

```text
authorized product decision
        ↓
versioned responsibility specification
        ↓
machine validation ／ enrollment
        ↓
carrier
        ↓
runtime enforcement
```

---

## 事前綁定的三種結局（**不看到結果再選**）

```text
結局 A｜已有既存 normative authority，只是尚未 first-class ／ executable
        → 可以設計 certification ＋ carrier

結局 B｜**有人實際在做** responsibility adjudication，
        但只存在於隱性流程／seed prose
        → governance exists, **authority representation missing**

結局 C｜根本沒有明確 responsibility owner ／ admission rule
        → 下一個 design **不只**需要新增 technical authority source，
          **還需要產品先建立 responsibility governance**
        ⚠️ 若為 C，這是整條線非常重要的答案：
           **這不是 routing implementation 可以單方面修好的問題。**
```

## 為何**現在不新增 R7**

R6 已經夠強（MUST 新增 first-class responsibility authority）。
只有在本輪**真的證明** responsibility truth 是 normative product decision、
且目前無 governing source 時，才有資格再導出例如：

> responsibility authority MUST originate from an explicitly authorized,
> versioned product-governance source.

⚠️ **現在還早一步。不得預先寫入。**

## 輸出限制

```text
只輸出：候選 truth source 的 inventory ＋ 逐條 O1–O6 disposition ＋ 結局判定

❌ 不設計 carrier（A／B／C 已 CLOSED，不得復活、不得發明第四種）
❌ 不新增 classifier
❌ 不新增 R7
❌ 不設計 governance 流程（本輪只判「有沒有、合不合格」）
❌ 不改已凍結的 Contract／ruler／R6
❌ 不改 family disposition；不開 member；D2 仍 deferred
❌ 不動 production；不產測資；ruler 0.058928 仍凍結未用
```

## ⚠️ 本輪的一個結構性限制（**執行前先聲明**）

```text
前三輪的查核對象都在 **repo 內**（程式、設定、DB schema、API 契約）。
本輪的對象**部分不在 repo 內**——「誰有資格決定產品責任」可能存在於
組織流程、業主決策、會議與規格文件中。

→ repo 側可查：是否存在責任裁決的**產物**（版本化規格、審批痕跡、
  責任變更記錄、seed prose 的作者與時點）
→ repo 側**查不到**：實際的決策權歸屬

⚠️ 故本輪的 repo-side inventory **可以**區分結局 B 與 C 的部分證據，
   但**不能**單獨判定結局；**判定需要業主提供 repo 外的事實**。
   此限制寫在執行之前，避免事後把「查不到」誤報成「不存在」（E5／§5 的同一紀律）。
```
