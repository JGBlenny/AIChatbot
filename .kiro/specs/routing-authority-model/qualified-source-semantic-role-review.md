# Qualified sources：semantic-role review

> 2026-08-24｜語言 zh-TW｜對象：`evidence-source-inventory.md` 的 N1／N2／N3（`1f077f6`，scope 已補完）
> **不新增 source、不補掃、不跑 candidate、不設計 member。**
> 只回答：**這三份 runtime proof 究竟能授權到哪一層 routing 判斷？**

## 五個語義角色（分類軸，事前定義）

```text
R-a entity resolution          reference → 真實存在的實體
R-b actor authorization        該 actor 有權存取該實體
R-c instance binding           query 是否收斂到**單一**實例（instance specificity）
R-d operation/state applicability  該實例當前狀態／可執行操作是否與問題相符
R-e facet discrimination       **為什麼是 Face X 而不是 Face Y**
```

⚠️ 一個 source 可屬多類，也可能只到 prerequisite 層。

## 結論（先寫，避免被下面的細節蓋過）

```text
N1  R-a ✅  R-b ✅（role 層）  R-c ✅  R-d ⚠️部分  R-e ❌
N2  R-a ✅  R-b ✅（role 層）  R-c ✅✅（本項的核心資訊）  R-d ❌  R-e ❌
N3  R-a ⚠️部分  R-b ✅（member 層）  R-c ⚠️部分  R-d ❌  R-e ❌

→ **三者皆為 prerequisite proof，沒有任何一項攜帶 facet discrimination 資訊。**
```

> **D3 仍缺一層 Face-specific applicability evidence。**
> 這本身就是本輪最重要的結果，且它**不是**「再找幾個 source 就能補上」的缺口（見下）。

---

## 逐項

### N1｜existence ／ ownership ／ active

**它證明的**：`bill_id B` 在 `role R` 下對應到一張真實、有效、由該 role 擁有的帳單。

| 角色 | 判定 | 說明 |
|---|---|---|
| R-a | ✅ | 404 即「解析不到」；解析成功即實體存在 |
| R-b | ✅（**role 層**） | `where('owner_role_id',$roleId)`——授權主體是 role，**不是**發問的個別成員 |
| R-c | ✅ | 給定單一 id 即單一實例 |
| R-d | ⚠️ **部分** | 回傳欄位含 `status`／`bit_status`／`invoice_status`／`is_auto_pay`／`online_payment_method`／各時間戳（`BillApiController@show:214-223`）——即**確實回傳了狀態**。但「該狀態對應哪一類問題」**不由本 source 給出** |
| R-e | ❌ | 回傳內容中**沒有任何**欄位指涉「哪個 Face 負責」 |

### N2｜識別條件 → 指涉基數

**它證明的**：在 `role R` 下，該組識別條件解析到 **0／1／多** 筆。

| 角色 | 判定 | 說明 |
|---|---|---|
| R-a | ✅ | ≥1 筆即存在 |
| R-b | ✅（role 層） | 同 N1 |
| R-c | ✅✅ | **這是本項的核心資訊**：能否收斂到單一實例。0=unknown、1=收斂、多=需消歧 |
| R-d | ❌ | 篩選條件雖含 `status`／`type`，但那是**輸入**；本項的輸出是筆數，不解釋問題性質 |
| R-e | ❌ | 基數與「哪個 Face」無關——同一張帳單可同時落在多個 Face 的責任描述下 |

### N3｜成員可見性探測

**它證明的**：`member M` 在 `role R` 下**看不看得到** `bill B`。

| 角色 | 判定 | 說明 |
|---|---|---|
| R-a | ⚠️ 部分 | 空結果無法區分「不存在」與「看不到」——與 N1 的 404 同型的合併語義 |
| R-b | ✅（**member 層**） | 這是三者中**唯一**下探到個別成員的授權事實，比 N1／N2 的 role 層更細 |
| R-c | ⚠️ 部分 | 需先有 `bill_id` 才能探測 |
| R-d | ❌ | 可見性不說明帳單狀態或操作可否 |
| R-e | ❌ | ⚠️ **特別注意**：`billing_anomaly` 的 handles 確實列有「租客看不到某一筆帳單」，看起來像對上了——但那個對應**來自 Face contract 的散文**，**不是**本 source 提供的。source 只說「M 看不到 B」；「所以該進 billing_anomaly」是**別處做的映射**，且該映射正是 G1 判定沒有 authority 的東西 |

⚠️ N3 的這一格是本次 review 最容易誤判的地方。**看起來對上 = 契約散文與事實碰巧同名**，
不等於 source 攜帶了 discrimination 資訊。

---

## 為什麼 R-e 的缺口是**結構性的**，不是「再找幾個 source」

三個 proof 都是**關於實體的事實**（存在／歸屬／可見／狀態）。
要從它們推出「該進 Face X」，需要一個映射：

```text
(entity state, actor, cardinality)  →  responsible Face
```

而這個映射的值域**就是 Face 集合**——G1 已查明它是**後台資料驅動、零改程式可增**
（`services/conversational_config.py:15`）。故：

```text
✗ 這個映射沒有 authoritative source 可導出（G1 FAIL 的正是這一層）
✗ 再多幾個 entity-side proof 也**不會**產生這個映射
   —— 它們全部落在箭頭**左邊**，缺的是箭頭本身
```

⚠️ 因此：**「再掃更多 source」不是補 R-e 的路徑。**
補 R-e 只有兩種可能方向（**本檔不選、不設計**）：

```text
① 讓每個 Face 自帶「我接受哪些 runtime proof、在什麼條件下成立」的**局部**宣告
   —— 即業主指出的新 D3 邊界：Face contract 不再描述世界，只指定它消費哪些外部可驗證事實
   ⚠️ 但「宣告」本身無 enforcement（inventory 的 N6 已判 E1 不成立）——
      這條路必須先解決「宣告如何取得 runtime binding」，否則重蹈 B／C

② 承認 R-e 需要一個目前不存在的 first-class authority source（新產品語義）
```

---

## 一個必須攤開、且會影響下一步方向的發現

本輪事前綁定把「Face 側 executable facts」導向 **D3**。
但 semantic-role 分析顯示：**source 在平台側，攜帶的資訊卻是 demand-side 的。**

```text
N1／N2 的核心資訊 = R-c instance binding
                  = 「這個 query 是否指涉一個特定的既存實體實例」

而這**恰好逐字**是 D1-member-1 的判準：
  d1-routing-applicability-spec-v1.json：
  「query SHALL 指涉一個**特定的既存實體實例**（自己的某一筆），而非通則」
```

且 Round 1 的 D1 失敗形態是 **F1**：evaluator 對**輸入裡已存在**的指涉證據作出與輸入矛盾的陳述
（16/17）。而 N1／N2 提供的是**用平台事實取代 evaluator 判斷**的同一個資訊。

> ⚠️ **這是一個 hypothesis，不是結論，本檔不據以行動。**
> 但它在形式上滿足 D1 的 re-entry condition——
> 「不依賴 text specification ＋ generic evaluator 的 routing-owned information shape」。

**因此下一步的方向題比事前綁定所預期的更開**，需要業主裁定：

```text
(a) 只往 D3 走：先解決「Face 局部宣告如何取得 runtime binding」（上述方向①）
(b) 以 N1／N2 作為 D1 的新 information shape 重開 D1（re-entry condition 表面已滿足）
(c) 兩者都不急著開：先確認 R-e 是否只能靠新增 first-class authority source（方向②）
```

⚠️ 我**不預選**。三條都不得在未經裁定下開工。

---

## 本檔的界線

```text
✅ 只做語義角色分類，未新增 source、未補掃、未跑 candidate
✅ E5 語義維持不變：404／0 rows／no proof 一律 unknown，**不得**視為 not_applicable
❌ 未設計任何 member（D1／D3／組合皆無）
❌ 未宣稱 positive-proof architecture 成立
❌ 未改任何 family disposition（D1／D3 皆維持 INSUFFICIENT_EVIDENCE）
❌ 未將 `incidental-observations.md` OBS-1 升格——它在本輪已以 P7 身分重新受審並 REJECTED（E1）
```
