# Responsibility Governance Decision Record（**待產品決策方填寫／批准**）

> 2026-08-24｜語言 zh-TW｜狀態：**空白待填** — 由**實際產品決策方**裁定，
> **不由工程端代填、不由工程端代猜**。
> 依 `authority-origin-discovery-closure.md`（`e12874d`）登記的四項 external dependency。

## 這份文件要解決什麼

系統目前無法回答一個問題，而所有後續設計都會被迫偷偷回答它：

> **誰有資格說「Face X 就應該負責這種情境」？**

```text
✅ 這是一份**面向未來**的裁定：從現在往後，責任由誰決定、如何留存。
❌ 這**不是**追究 2026-07-31 到底誰說了算——那段歷史永久留作 unresolved，不需要補。
```

---

## 背景：為什麼是治理問題，而不是再加一個模型

這條線一開始問的是「rule／instance 怎麼可靠分開」，逐層排除後走到今天的位置。
**這個因果鏈請保持完整**——它是「不然再加一個 intent classifier？」這個提議的現成答覆：

```text
similarity ／ category            不足（R1）
lexical applicability             REFUTED（v1 holdout：routing effect 0/50）
closed responsibility taxonomy    G1 FAIL（三個 domain 皆 NOT PROVEN）
existing runtime facts            只有 prerequisite，不含 facet discrimination
existing facts → Face binding     不存在，且不可由既有 runtime binding 機械導出
carrier shape                     無法自行產生 authority（A／B／C 皆非 ADMISSIBLE）
repo governance provenance        不足以辨認 normative origin
```

> **結論一句話：classifier 可以產生 decision，但不能自行產生 decision authority。**
> （實證：production 早已有一個逐 query 選面向的 LLM，runtime 只保證它選到的 key 合法，
> **不保證**選到的是責任正確的面向。）

---

## 需要裁定的四件事

> 填寫原則：**「還沒有固定規則」「看情況」「暫時由我一人決定」都是有效答案。**
> **不需要把流程整理得比現實更正式**——寫得比實況正式，反而會讓後續設計建立在假前提上。

### 決策 1｜責任裁決權：誰／哪個角色有權做 responsibility decision？

```text
角色／人：____________________________________________

適用範圍（勾選或補述）：
  □ 新增面向時，決定它負責哪些情境
  □ 既有面向的責任邊界調整
  □ 兩個面向邊界重疊時的歸屬裁定
  □ 其他：__________________________________________

⚠️ 若答案是「沒有固定角色，誰做誰決定」→ **請照實寫**。
```

### 決策 2｜approve ／ veto 語義：誰能否決，被否決者是否必須照做？

```text
approve 者：__________________________________________
veto 權：    □ 有，持有者：______________  □ 無

被否決後（勾選）：
  □ 必須照改        □ 可再議        □ 無明確規則

⚠️ 「沒有正式 final approver，通常某某說了算」是有效且常見的答案。
```

### 決策 3｜enrollment authority：新增面向是否需要正式裁決？

```text
現況（已查證）：技術上新增一列後台資料即可新增面向，**零改程式、無審批欄位**。

今後應如何：
  □ 需事前裁決（由決策 1 的角色）    □ 事後追認即可    □ 不需要
  核可留存於：__________________________________________

⚠️ 若不需要，請一併確認：新面向在取得裁決前，系統應維持 `unknown`
   （＝不主動進入該面向），而非自動生效。 □ 同意  □ 不同意，理由：__________
```

### 決策 4｜留存形式與機器交接

```text
4-a 版本化留存：責任裁定寫在哪裡？
    □ 本檔（每次裁定新增一節，含日期與裁定者）
    □ 其他：__________________________________________
    ⚠️ 需能回答：誰改、何時改、哪個版本生效。

4-b 機器交接：經核可的裁定如何變成系統可消費的設定？
    □ 由工程端依本記錄實作，並在實作處回指本記錄的版本
    □ 其他：__________________________________________
    ⚠️ **裁定本身可以是人的判斷**（不必由機器產生）；
       要求的只是它**不能只活在口頭／會議紀錄**，必須有可回溯的版本化落點。
```

---

## 填完之後會發生什麼（讓填寫者知道代價與收益）

```text
① 技術線解除封鎖：目前所有 Responsibility Authority 的 production design 標記為
   BLOCKED BY external responsibility-governance decision
   —— **不是** design failure，也**不是** implementation incomplete

② 第一次能回答 carrier comparison 的 X-1（authority origin）
   → 才值得重新拿 A／B／C 出來
```

### ⚠️ 重新受審的規則（**現在就寫死，避免將來偷跑**）

```text
✅ 只需對 A／B／C **補上新的 X-1 evidence**，再看原有 disposition 是否改變
   —— 不必重跑整個 carrier comparison

❌ **A 不是預設答案**
   A 目前是 X-3／X-5 PASS、X-1 未解；即使治理成立，也**必須**依
   `carrier-comparison-ruler-frozen.md` 重新受審
❌ B／C 同樣重新受審——B 目前的 REJECTED 射程是**當時那個 self-enrollment shape**，
   若新治理提供外部 admission，那已是**新的 shape**，須以新版身分受審
```

#### ⚠️ 解鎖時的關鍵紀律：**治理成立是「新 evidence」，不是自動替所有 carrier 補滿 X-1**

```text
❌ 不得因為本記錄填完，就直接把 A 的 X-1 改成 PASS

✅ 正確順序：
   ① 先把填寫結果轉成一個**可引用的 authority-origin artifact**
      （有版本、有裁定者、有生效範圍）
   ② 再**逐 carrier** 問：

      A  這個 governance decision **是否真的**為 A 的 central binding 提供 X-1？
      B  它**是否改變** B 原本的 self-enrollment shape？
         若改變 → B 是**新 version**，不是舊 B 翻案
      C  它**是否足以**建立 C 的 `Face ↔ capability` **右半邊** binding？
         （左半邊平台權限本來就 authoritative，缺的一直是右半邊）
```

⚠️ 三個問題的答案**可以不同**：治理成立**可能只解鎖其中一個或兩個 carrier**，
也可能一個都不解鎖（例如裁定成立但無法版本化、或無法轉成 machine binding）。
**不得**把「治理有了」直接等同於「carrier 可以選了」。

### 若四題的答案是「目前沒有固定規則」

```text
沒有固定 authority owner ／ 沒有 final veto ／ 新增 Face 不需裁決 ／ 責任只靠討論或口頭
```

⚠️ **這不是 decision record 填失敗**，而是得到一個清楚的產品治理結論：

> **responsibility governance 本身需要先被建立。**

此時 v2 design 可正式停在 `external dependency unresolved`，
且該結論**本身**就是這條線的有效產出，不需要再由工程端補洞。

---

## 在本記錄成立之前，工程端的既定約束（**已凍結，不因等待而放寬**）

```text
authority_origin = **unresolved**
❌ 不得頂替為：engineer／Face seed／categories／LLM verdict／實作者決策
❌ 不重開 D1／D3 member、不選 A carrier、不設計 registry schema、不做新的 routing candidate
   （以上每一項都會被迫偷偷回答本記錄要裁定的問題）
✅ `facet-backfill-review.md` 的 confirmation provenance 維持 **unknown**
```

---

## 裁定記錄（**每次裁定新增一節；本節即決策 4-a 的預設落點**）

```text
版本：v1
裁定者：____________________
裁定日期：__________________
生效範圍：__________________
變更摘要：__________________
```

> ⚠️ 本檔目前**全部空白**。在填寫並由決策方確認之前，
> **不得**被任何設計文件引用為 authority origin。
