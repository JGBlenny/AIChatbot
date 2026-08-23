# Design Erratum 01：`block` 的作用域——選項分析

> 2026-08-23｜語言 zh-TW｜**狀態：OPTIONS ANALYSIS — RULING PENDING**
> 觸發：任務 1.3 的 N4 rule 側兩筆紅（`open_conflict_for_task_4_1`）
> _Requirements: 1.2, 2.5, 4.2_｜前置：任務 1.5 完成（A 22／B 8／C 0，13 突變全殺）
> ⚠️ **本文件不碰 candidate code**，且**不作裁示**——裁示權在業主。

## 命題

> **當 rule 判定成立後，哪些 Routing Hints 屬於同一個應被抑制的
> instance-routing responsibility？其 membership 的產品／架構依據是什麼？**

⚠️ N4 的紅**不是待修 bug**，而是在指出 design v1.1 少了一個
「**routing responsibility membership**」契約。先回答責任集合，才談如何表示。

## 三條不可違反的裁定原則（業主 2026-08-23）

```text
① membership SHALL NOT = bool(required_slots)
② membership SHALL NOT 因「有 bill_ref」就自動成立
   —— 共用 execution slot ≠ 共用 routing responsibility
③ 未決 Face 不得因 N4 技術需要，自動被升格為產品上應納管的 Face
```

任何方案若**必須先假定**「`billing_anomaly` 與 `bill_diagnosis` 本來就是同一
responsibility」才能成立，一律標 **BLOCKED BY PRODUCT DECISION**，不得自行補上假設。

## 分析中最關鍵的一項發現：Req.4 耦合比表面上弱

表面上的推論鏈是：

```text
N4 要過 → billing_anomaly 必須被抑制 → 所以它屬 Level A
```

依原則③這是**非法推論**。但實際檢查後，鏈條的前半段與 Req.4 **可以分離**：

```text
gate 只在「無正向證據 ＋ 有反向證據」時 block（design 決策 4，雙條件）
  ↓
Req.4 那兩筆未決問句是 **instance 側**（「**我的**收據在哪」「**我這筆**點退的錢…」，
命中 possessive 正向證據）→ 判定為 allow，**從不進入抑制路徑**
  ↓
∴ billing_anomaly 是否納入責任集合，**只改變 rule 側問句的行為**；
   那兩筆 instance 問句該去哪個 Face，**不因本 erratum 而被決定**
```

**因此要裁的產品命題不是「未決問句屬於誰」，而是這一句**：

> 「**教學／規則型問句 SHALL NOT 進入帳務診斷面向**（含 `帳單異常`）」

而這句話**已經是 Req.1.2**——本 erratum 需要的不是新的產品裁示，
而是 **Req.2.5 的 Level A 範圍宣告（任務 7.1）把「帳務診斷面向的 rule 側」寫進去**。

⚠️ **falsifier（此發現若被推翻，整份分析的耦合欄位須重評）**：
extractor 實作後，對「我的收據在哪」「我這筆點退的錢怎麼怪怪的」判出 `block`
（而非 `allow`／`abstain`）——屆時 membership 就會**真的**改動未決問句的路由，
耦合成立，全部方案的第 5 欄須改判。**該檢查 SHALL 排在任務 2 的第一輪。**

## 現行 registry（實查 22 Faces，2026-08-23）

原則①的具體代價：**13 個 Face 的 `required_slots` 非空**——
`contract_ref`×6（contract_diag／contract_change／contract_sign／contract_closeout／
contract_renew／account_login）、`bill_ref`×4、`estate_ref`、`meter_ref`、`member_ref`、
`repair_create`（五槽）。`bool(required_slots)` 會一次納管其中 13 個。

帳務側曝險（active KB 計數）：

| category | face | required_slots | KB 數 | 與主題分類共居 |
|---|---|---|---|---|
| 條件診斷：帳單 | `bill_diagnosis` | `bill_ref` | 11 | 3 |
| 帳單異常 | `billing_anomaly` | `bill_ref` | 6 | 0 |
| 發票 | `billing_invoice` | `bill_ref` | 7 | 3 |
| 繳費金流排障 | `billing_flow` | `bill_ref` | 12 | 4 |
| 滯納金 | `billing_late_fee` | `contract_ref` | 5 | 2 |
| 帳單設定引導 | `billing_setup_guide` | 無 | 18 | 11 |

---

## 選項 A：明列 Face key allowlist

1. **membership predicate**：`cfg.key ∈ LEVEL_A_INSTANCE_FACES`（程式碼內明列常數）。
2. **blast radius**：完全等於清單本身。N4 要過，清單至少須含
   `bill_diagnosis` ＋ `billing_anomaly`（36 KB 中的 11＋6）。
3. **N4 行為**：兩種 category order 皆收斂 `single`（清單判定與順序無關）；
   instance 對照仍進 `bill_diagnosis`（gate 對 instance 判 allow）。
4. **Level A isolation**：**最強**——未列入者一律不受影響，1.4 的隔離斷言自動成立。
5. **Req.4 coupling**：**中**。清單是程式碼常數，最容易被讀成「技術清單」，
   但寫進去的每一個 key 實質上都是一句產品宣稱。
   依上方發現，該宣稱為「rule 問句不得進入該面向」，**不涉及未決問句歸屬** → 不 BLOCKED，
   但 **SHALL 於 Req.2.5 範圍宣告中逐一具名**，不得只存在於程式碼。
6. **falsifier**：新增一個帳務診斷 Face 而清單未同步 → N4 靜默回歸。
   偵測方式：一條 registry drift 測試（凡 `required_slots` 含 `bill_ref` 且不在清單者即紅，
   強制做出「納入或明示豁免」的決定）。

## 選項 B：Bill-ref routing family（先定義 family，再列成員）

1. **membership predicate**：`face ∈ family("帳務 instance lookup")`，family 為**顯式宣告**，
   **不由 slot 相同推導**（原則②）。
2. **blast radius**：4 Face／36 KB（`bill_diagnosis`／`billing_anomaly`／`billing_invoice`／
   `billing_flow`）。排除 `billing_late_fee`（`contract_ref`，不同實體種類）與
   `billing_setup_guide`（無 slot）。
3. **N4 行為**：兩序皆 `single`；instance 對照不受影響。
4. **Level A isolation**：其餘 18 Face 不受影響；但 family 一旦被理解成「帳務域」，
   後續新增帳務 Face 會**自動**被納管——這是它與 A 的根本差異，也是它的風險。
5. **Req.4 coupling**：**中**，同 A。額外負擔：**須先證明 family 是真實的責任邊界**，
   而不是「這四個剛好都收 `bill_ref`」的事後歸納。
   ⚠️ 若論證只能寫出「它們都需要 `bill_ref`」，即違反原則②，該方案退化為 A 的偽裝版。
6. **falsifier**：family 中出現一個**應該**接受 rule 問句的成員
   （例如某面向的教學問句本來就該進場引導）→ family 邊界錯了。

## 選項 C：Face-level semantic contract（顯式宣告 `instance_reference_required`）

1. **membership predicate**：`cfg.grounding_scope.instance_reference_required is True`
   ——**新增的顯式宣告**，語義為「本面向只在使用者指涉某一筆實體時才該進場」；
   **不得**以 `bool(required_slots)` 推導（原則①）。
2. **blast radius**：等於宣告集合。今日**零個 Face 有此宣告** → 需為每個成員做一次資料變更。
3. **N4 行為**：宣告 ≥2 個成員即兩序皆 `single`；instance 對照不受影響。
4. **Level A isolation**：**最強且可自證**——未宣告者在型別上就不在集合內。
5. **Req.4 coupling**：**最低**。宣告本身就是「該面向的 routing responsibility」的
   產品陳述，與「未決問句屬於哪個 Face」在資料上分離，最不容易被偷換。
6. **⚠️ 與既有設計決策衝突**：design 決策 2 明訂「**不新增 KB metadata；Level A 複用既有宣告**」。
   本選項要求新增宣告欄位 → **裁定本選項即同時修訂決策 2**，須明寫。
7. **falsifier**：兩個 Face 同樣宣告 `instance_reference_required`，卻必須對 rule 問句
   有不同行為 → 宣告的粒度錯了（責任不在 Face 層）。

## 選項 D：Query-scoped suppression

1. **membership predicate**：**本選項不提供 membership**——它規定的是**套用範圍**
   （rule 判定成立後，抑制**該 query** 對責任集合內所有 Hint 的作用），
   集合本身仍須取自 A／B／C。
   ⚠️ **D 與 A／B／C 正交，不是第四個並列選項**；
   **D 若沒有 membership 來源，即退化為選項 E。**
2. **blast radius**：等於其 membership 來源。
3. **N4 行為**：兩序皆 `single`（作用域是 query 而非 category 位置，故順序無關）；
   instance 對照不受影響。
4. **Level A isolation**：取決於 membership 精確度；membership 不精確時，
   D 是**最容易滑成「整列／全部 Face 一起封」**的形態。
5. **Req.4 coupling**：同其 membership 來源。
6. **falsifier**：一筆 KB 的 categories 同時涵蓋**兩個不同責任集合**
   → 「抑制該 query 的責任集合」需回答抑制哪一個，作用域定義不完整。
   （今日語料無此形狀；L6 共居 hygiene 未做，不可假設恆真。）

## 選項 E：整筆 KB hints 全 suppression —— **預期 loser，但必須具名**

1. **membership predicate**：top-1 KB 所攜帶的**全部** Face hints，不論 Face 身分。
2. **blast radius**：**無界**——跨域。今日語料中**沒有**任何 KB 同時掛帳務與非帳務 Face
   （實查 0 筆），所以它**現在看起來很安全**。⚠️ **這正是陷阱**：
   它的安全性來自語料的偶然形狀，而非機制保證，且 L6 共居 hygiene 是 future work。
3. **N4 行為**：兩序皆 `single`——**它會讓 N4 最快變綠**。
4. **Level A isolation**：**違反**。任一 KB 一旦攜帶跨域 Face 對，隔離即破，
   而 1.4 的隔離斷言在該筆出現之前**測不到**（今日 0 筆）。
5. **Req.4 coupling**：無。
6. **falsifier**：出現任何一筆 categories 橫跨兩個域的 KB。
7. **判定建議**：**REJECTED**。列出它的唯一理由是——
   它是實作者讓 N4 快速轉綠最省事的捷徑，**不具名就無法明確禁止**。

---

## 對照總表

| | membership 依據 | 納入 Face | 涉及 KB | 需要新資料契約 | Req.4 耦合 | 隔離強度 |
|---|---|---|---|---|---|---|
| A | 程式碼明列 key | 明列 | 依清單（≥17） | 否 | 中 | 最強 |
| B | 顯式 family 宣告 | 4 | 36 | 否（設定層） | 中 | 中 |
| C | Face 層語義宣告 | 依宣告 | 依宣告 | **是**（修訂決策 2）| **最低** | 最強 |
| D | 無（正交，套用範圍）| — | — | — | 依來源 | 依來源 |
| E | 整筆 KB hints | 動態 | 無界 | 否 | 無 | **違反** |

## 尚未解決、且**不由本文件決定**的事項

1. **membership 依據擇一**（A／B／C）——業主裁示。
2. **是否採 D 作為套用範圍**——與 1 正交，可同時裁。
3. **C 若獲選 → 決策 2 須同步修訂**（不新增 KB metadata 的原則被推翻）。
4. **Req.2.5 範圍宣告（任務 7.1）須具名**每一個納入的 Face，
   不得只存在於程式碼常數。
5. **Req.4 兩筆未決問句的產品歸屬**——依上方發現，**本 erratum 不需要它先落地**；
   但若 falsifier 成立（extractor 對該二筆判 `block`），則須立即回頭補裁。
