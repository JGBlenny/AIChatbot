# R-e discovery：結果 — **結局 C**

> 2026-08-24｜語言 zh-TW｜依 `re-mapping-discovery-frozen.md`（RE1–RE6＋搜尋範圍，凍結於 `3e83ed5`）執行
> 唯讀。未改任何檔、未進 seam、未產測資、未動 ruler、未重跑 cohort。
> 證據身份：`blind = false`｜`prior_exposure = declared`｜`qualification_rule_pre_frozen = true`

## 判定

```text
既有 qualified R-e mapping        不存在（5 個候選全部 REJECTED）
可由既有 machine authority 機械導出  否
→ **結局 C**
```

依協議事前寫定，結局 C 授權寫下這條 architecture requirement：

> **在 audited architecture 中，R1 所需的 facet-specific applicability information
> 沒有現成 authoritative source；下一個 admissible design MUST 新增一個
> first-class responsibility authority。**

⚠️ **承載方式仍未決定**——本檔**不**主張新增某張表／某個 registry。
⚠️ N1／N2／N3 是該新 authority 未來可**消費**的已證成 runtime evidence，**不是** authority 本身。

---

## 決定性的結構事實：**平台層根本沒有 Face 這個概念**

```text
jgb2（master 5eaebb7f0a）全 app/ 與 routes/ 中，
routing Face／面向 概念的出現次數 = 0
（唯一 grep 命中 app/Http/Controllers/BillController.php:12565 為
 「驗證三面向」＝表單驗證的三個層面，與 routing Face 無關）
```

**推論**：唯一具 runtime authority 的那一層（平台）**不可能**提供 `facts → Face` 的箭頭，
因為它不知道 Face 存在。因此任何既有 R-e 只可能落在對話層，而對話層的候選全部
不是 config、就是 LLM 判斷——這正是下面五個 REJECTED 的來源。

---

## 候選逐條（RE1–RE6）

### B1｜code-level Face → fact-builder 註冊表

```text
source   services/jgb/bills.py:275-282 BILL_FACE_BUILDERS
         （同形態另有 contracts.py:616 FACE_BUILDERS、estates.py:96 ESTATE_FACE_BUILDERS、
           accounts.py:198 ACCOUNT_FACE_BUILDERS）
surface  S-a Face ↔ executable capability
prior_exposed  true（凍結時已揭露我知道有 face → fact-set 分派點）
```

| | 判定 | 依據 |
|---|---|---|
| **RE1** Face-specific | ✅ | 註冊表逐一列出共享同一組 bill proof 的面向：`條件診斷：帳單`／`帳單異常`／`繳費金流排障`／`發票`／`滯納金` |
| **RE2** runtime-authoritative | ✅ | 是**程式碼**中的 dict，非散文；未命中即回 `None` 走原路（`bills.py:291-293`） |
| **RE3** query-decision relevant | ❌ **不成立** | **箭頭方向相反**：`face` 是這張表的**輸入**，不是輸出。它回答「給定面向 X，要組哪些 facts」，**不回答**「這些 facts 指向哪個面向」。表的內容每次部署恆定 |
| RE4／RE5／RE6 | — | RE3 已不成立，不續判 |

**disposition：REJECTED（RE3）**

⚠️ **是否可機械反轉成 `facts → Face`？否。** builder 是**命令式**程式碼，欄位取用內嵌於邏輯中
（如 `build_bill_anomaly_facts` 直接取 `date_start`／`rate`／`details`，`bills.py:134-143`），
**沒有宣告式的欄位需求規格**可供比對；且 `build_bill_diagnosis_facts` 內另有
`_DIAG_KEYWORDS` 的**詞彙分支**（`bills.py:248,265`）——反轉它等於重新實作它，
且會把 lexical 判斷再帶回 authority 路徑。

### B2｜進場面向 ＝ 知識分類（現行 production 的 `facts → Face` 箭頭之一）

```text
source   _domain_key(config)：topic_scope.mode=='category' → topic_scope.category
         （services/conversational_engine.py:166-175）
         ＋ by_category 索引（services/conversational_config.py:161-167）
surface  S-d Face ↔ machine-consumable routing responsibility
prior_exposed  true
```

| | 判定 | 依據 |
|---|---|---|
| **RE1** | ✅ | 不同 category 對到不同面向 |
| **RE2** runtime-authoritative | ❌ **不成立** | 輸入是**檢索到的知識的 KB category**——RE2 明文排除 KB category |
| **RE3** | ❌ | 與 R1 §1.2 已 REFUTED 的形態相同：category membership 的重新編碼，**不是新增 applicability information** |

**disposition：REJECTED（RE2／RE3）**

⚠️ 這一項很重要：**production 現在確實有一條 `facts → Face` 箭頭，
但它的「fact」就是 similarity＋category** ——即 R1 一開始就宣告不足的那個東西。

### B3｜中途換面向 ＝ LLM 判定＋範圍守衛

```text
source   face = step.get("face")；face_key = face if (face and face in faces) else entry_key
         （services/conversational_engine.py:693-694）
         faces 由 _domain_faces() 自設定／分類衍生（:178-186）
surface  S-d
prior_exposed  false
```

| | 判定 | 依據 |
|---|---|---|
| **RE1** Face-specific | ✅ | 就是在共享同一領域的面向之間做選擇 |
| **RE3** query-decision relevant | ✅ | **逐 query 變動**——這是所有候選中唯一同時滿足 RE1＋RE3 的 |
| **RE2** runtime-authoritative | ❌ **不成立** | 面向由 **LLM（brain）在 `conversational_step` 中生成**。被 enforce 的只有**值域**（`face in faces`，越界或空即退回進入面向），**不是正確性**。值域守衛 ≠ authority |
| RE4／RE5／RE6 | — | RE2 已不成立，不續判 |

**disposition：REJECTED（RE2）**

⚠️ **這一項正是「系統缺的不是另一個 classifier」的實證**：production 已經有一個
per-query 變動、面向專屬的選擇器了——它是個 LLM，而它的判斷**沒有任何 runtime authority 背書**，
只有一道範圍檢查。再加一個同形態的 classifier 不會改變 authority 結構。

### B4｜Face ↔ API／action binding 宣告

```text
source   grounding_scope.endpoint／params／search_params（services/conversational_engine.py:864-870）
surface  S-b Face ↔ API／action contract
prior_exposed  true（inventory 已以 N6 判過）
```

| | 判定 | 依據 |
|---|---|---|
| **RE2** | ❌ | 宣告存在**後台可編的設定值**中，無 enforcement（inventory N6 已判 E1 不成立） |
| **RE5** executable／enforceable | ❌ | 完全依賴「新增 Face 時記得寫對」——正是 R4 已 CONFIRMED 的制度失敗形態 |

**disposition：REJECTED（RE2／RE5）**

### B5｜Face 宣告的身分前置條件（唯一具 enforcement 的 Face-側宣告）

```text
source   身分參數保底：掃設定模板取 {session.<key>} 需求鍵，缺值 → **禁打 API、誠實降級**
         （services/conversational_engine.py:880-891）
surface  S-c Face ↔ enforced prerequisite
prior_exposed  false
```

| | 判定 | 依據 |
|---|---|---|
| **RE5** enforceable | ✅ | **確實 enforce**：缺必要身分鍵就不打 API，不是提醒而是阻斷 |
| **RE1** Face-specific | ❌ **不成立** | 它區分的是「身分參數夠不夠」，**不區分**共享同一 entity proof 的兩個面向——`條件診斷：帳單` 與 `帳單異常` 的身分需求相同 |

**disposition：REJECTED（RE1）**

⚠️ 記錄它的價值在於：它證明**「Face 宣告 ＋ 程式 enforce」這個組合在本系統中是做得到的**
（B4 做不到、B5 做得到，差別在於有沒有消費端強制）。這對結局 C 的**承載方式**是有用的前例——
但**本檔不據以設計**。

---

## 為何判「不能機械導出」（結局 B 被排除的理由）

```text
① 唯一 runtime-authoritative 的層（平台）**沒有 Face 概念** → 無法供給箭頭
② 對話層唯一 Face-specific 的程式碼映射（B1）**方向相反**，且為命令式、無宣告式需求規格
   → 反轉＝重新實作，且會把 lexical 分支帶回 authority 路徑
③ 現存的兩條 facts → Face 箭頭：
     B2 輸入是 KB category（RE2 明文排除、R1 §1.2 已 REFUTED）
     B3 是 LLM 判斷＋值域守衛（RE2 不成立）
   兩者都不是可被「顯式化」的既有 machine binding——它們本來就不是 machine authority
```

⚠️ 依 E5／RE4 精神：以上是**在已凍結搜尋範圍內**的結論。
本檔**不**宣稱「整個 production 不可能存在」——只宣稱在
`re-mapping-discovery-frozen.md` 所凍結的 responsibility binding surface 內，
**沒有**、且**導不出**。

---

## 這條線第一次得到的具體設計結論

```text
系統缺的不是另一個 classifier
      —— B3 證明 production 早就有一個 per-query、面向專屬的 LLM 選擇器，
         它缺的是背書，不是存在。

它缺的是一個把 runtime applicability facts 與 Face responsibility 連起來的
**first-class authority source**。
```

對照這條線先前的位置：這比 H1／H2／H3（先前 INSUFFICIENT_EVIDENCE 的三個 root-cause 假說）
**更具體**，且是第一個由實測證據鏈支撐的架構結論：

```text
R1 說：不得僅以 similarity＋category 作為 applicability authority
inventory 說：runtime-binding 的 applicability facts **存在**（N1／N2／N3）
semantic-role review 說：那些 facts **不含** facet discrimination
本輪說：facts → Face 的 authoritative 箭頭 **不存在且導不出**
→ 所以 R1 的下限目前**無法**由既有元件滿足
```

## 本檔**未**回答／未做

```text
❌ 未主張承載方式（不說「新增某表／某 registry」）
❌ 未設計 member，未開 D1／D3／D4，D2 仍 deferred
❌ 未改 family disposition（D1／D3 皆維持 INSUFFICIENT_EVIDENCE）
❌ 未把 B5 的前例升格為設計方案
❌ 未宣稱「整個 production 不存在 R-e」——僅限已凍結的搜尋範圍
```
