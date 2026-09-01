# P0-3 知識庫覆蓋率盤查（唯讀）

> 2026-09-01｜唯讀，**未改任何資料與程式**｜計畫依據 `PLAN-retrieval-coverage.md` §2 P0-3
> 所有數字取自 `aichatbot_admin.knowledge_base`（`is_active = TRUE`），可逐條重跑。

---

## 1. 結論：適格母體 = **773**，其中未宣告 representation = **767**

```text
active                                 922
− 設定列（⛔ 不是知識，本就不該被檢索）     51   §3
− 錨點列（answer 空，⛔ 不可補造）          98   §4
  兩者交集                                0   （已驗，非重複扣除）
= 適格母體                              773
  已宣告 representation                   6   （Level-A V2 中不在 98 內者）
= **適格且未宣告 = 767**
```

⛔ **913 是毛數字，不得當分母**。913 = 922 − 9，把設定列與錨點列都算進了分母。
⚠️ 真正的覆蓋率是 **6 / 773 = 0.78%**（不是 9/922 = 1%，也不是 9/913）。

正對照（否定結論防呆）：`generation_metadata IS NOT NULL` = 477/922
⇒ 「只有 9 筆有 representation」不是查詢寫錯造成的假象。
兩種獨立寫法（`id NOT IN` 與 `COALESCE(category,'') NOT IN`）算出同一個 773。

### 適格母體 773 的組成

```text
來源    loop 445｜manual 310｜presales-kb 18
型別    direct_answer 739｜form_fill 29｜api_call 5
對象    tenant 421｜property_manager 214｜pm+tenant 71｜(空) 38｜prospect 18｜tenant+landlord+all_users 11
keywords 為空                     64   ⇒ 這 64 筆只有向量一條路進得去
無 embedding                       0   ⇒ **適格母體全部有向量**
```

---

## 2. ⛔ 計畫前提修正：P0-4「51 筆無 embedding」是**錯的任務**

計畫寫「51 筆兩條檢索路都進不去 ⇒ 絕對檢索不到，優先消滅」。
事實正好相反：**它們本來就不該被檢索到，沒有 embedding 是正確狀態。**

```text
51 筆 = category '系統脈絡' 27 ＋ '對話規則' 23 ＋ id 4253（見 §3.2）
用途   系統脈絡 → services/system_context.py 依 category 載入後注入 prompt
       對話規則 → services/conversational_rules.load_rules 載入（面向設定本體）
防護   vendor_knowledge_retriever_v2.py 的向量路徑與 keyword 路徑
       都寫死 `category IS DISTINCT FROM '系統脈絡' / '對話規則'`
```

⇒ **P0-4 應改為「不做」**。若照原文執行（給它們補 embedding），等於把
系統提示詞與面向設定文件丟進檢索候選池，會直接污染排序。

⚠️ `rag-orchestrator/tools/embed_missing.py` **已有防護**（以 question_summary 前綴排除），
今天跑它會選出 **0 筆**（正對照：`embedding IS NULL` 確實有 51 筆，查詢路徑是通的）。
⛔ 但不要因此改用「補完所有 NULL embedding」的其他寫法。

---

## 3. 51 筆設定列的成因與**一個真缺陷**

### 3.1 成因
不是「漏產 embedding」，是**設計上就不產**。這些列把 knowledge_base 當設定儲存區，
以 `category` 當命名空間，靠 retriever 的 category 排除條款隔離。

### 3.2 ⛔ 缺陷 D-1：id 4253 分類錯誤 ⇒ **帳單診斷面向的領域脈絡從未載入**

```text
4253  question_summary = 「系統脈絡：帳務領域-帳單診斷(子面向)」
      實際 category = '條件診斷：帳單'（其他 26 筆同型列都是 '系統脈絡'）
      categories = 空、target_user = {property_manager}
```

`system_context._fetch_base` 與 `_fetch_appends` **三條查詢都要求 `category='系統脈絡'`**
⇒ 4253 三條都不命中；又因無 embedding、無 keywords 而檢索不到
⇒ **這一列在系統裡是死的**。

實證（`_domain_key` → `responsibility_context_key` → `topic_scope.category`）：

```text
pm_bill_diagnosis 的 topic_scope.category = '條件診斷：帳單'
父鏈（category_config）= ['條件診斷', '條件診斷：帳單']
categories 命中 '條件診斷'      的系統脈絡列 = 0
categories 命中 '條件診斷：帳單' 的系統脈絡列 = 0
正對照 '帳單異常'                             = 1  ✅
正對照 '條件診斷：訂閱'                        = 1  ✅
⇒ appends = [] ⇒ 帳單診斷面向只拿到通用 base，**沒有領域層**
```

⚠️ 這正是 `HANDOFF-20260901` §2 收線實測所走的那個面向。
⚠️ 全 repo（.md 與 .py）**查無任何一處提過 4253**——本缺陷此前未被記錄。
   `embed_missing.py` 註解知道「category 會掛面向名」，但沒推導出領域層不載入的後果。

### 3.3 D-2：`tenant_repair`（修繕報修）同樣沒有領域脈絡層

22 個 `topic_scope.mode='category'` 面向逐一盤查，只有兩個 `own_layer = 0`：
`pm_bill_diagnosis` 與 `tenant_repair`。其餘 20 個都有。
⚠️ 差別在於 4253 是**寫了但掛錯**，修繕則是**從來沒寫**——後者是否為刻意設計，尚未查證。

---

## 4. 98 筆空 answer 錨點分型

```text
全部 98 筆：category 皆 NULL、embedding 皆有、56 筆有 keywords
direct_answer  55  面向進場錨點（含不變量 16 登記簿的 12 筆 alias，
                   以及 Level-A 的 4640／4656／4657）
api_call       27  答案由 API 於執行期產生（社區設施/費用類）
form_fill      16  進場即導表單（jgb_bill_query、jgb_contract_query 等）
```

⇒ 三型的共通點：**answer 本來就該是空的**，內容在執行期才生成。
依 representation 契約「answer 已有的可表示、缺的不可補造」，
⛔ 這 98 筆全部**不得**進 representation 母體。
⚠️ 其中 12 筆 alias 另受不變量 16 管轄（per-row representation 對它們是層級錯配）。

---

## 5. 交給下一步的東西

```text
P2-1 pilot 選 50 筆的母體 = **767**（不是 913），且應優先從 keywords 為空的 64 筆
     與 P1-3 錯誤清單交集挑（那 64 筆只有向量一條路）
P0-4 建議改判為「不做」，理由見 §2                              ← 需業主裁
D-1  4253 分類錯誤（帳單診斷缺領域脈絡）                         ← 需業主裁是否本輪修
D-2  tenant_repair 缺領域脈絡，是否刻意                          ← 需查證
```

⚠️ 本盤查**未**量任何檢索表現，⛔ 不得由本檔推論命中率或路由正確率。
