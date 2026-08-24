# G1 audit：結果

> 2026-08-24｜語言 zh-TW｜依 `g1-audit-protocol-frozen.md`（凍結於本次查核之前，`c5941cd`）執行
> 執行方式：**唯讀**（Read／Glob／Grep）。未改任何檔、未進 production seam、未產測資、未重跑 cohort。

## 判定

```text
schema closure                    NOT PROVEN
domain closure / entity_scope     NOT PROVEN
domain closure / operation_class  NOT PROVEN
domain closure / problem_state    NOT PROVEN（無法指名任何 candidate authority）

→ G1 FAIL
```

依協議 §6：**B／C 退場**，D3 回到 member-shape discovery（與 D1 同狀態）。
⚠️ **D3 family disposition 不變**，仍為 `INSUFFICIENT_EVIDENCE`（M1）——
G1 失敗淘汰的是 **B／C 這個 representation**，不是 Face-owned contract family。

## Audited scope／version

```text
平台側   /Users/lenny/jgb/project/jgb_1/jgb2 ｜ branch master ｜ HEAD 5eaebb7f0a
         （behind origin/master by 2；工作樹有 2 個 untracked 一次性腳本，不影響本次引用）
對話側   /Users/lenny/jgb/AIChatbot ｜ rag-orchestrator（HEAD c5941cd）
```

---

## Source qualification（協議 §1／§3 步驟①②）

| candidate source | 主張的 class | 資格判定 | 理由 |
|---|---|---|---|
| Laravel route registry（`routes/web.php` 2085 行／`routes/api.php` 543 行） | S2 dispatch registry | **FAIL → 降 S4** | 它分派的是 **HTTP endpoint**，不是 operation。帳單操作經**自由 URL 片段**進入控制器內的 `switch` 分派 |
| `App\Bill` 類別常數（`app/Bill.php:40-79`） | S1 executable enumeration | **INSUFFICIENT** | PHP class constant 是**命名慣例**，非寫入端 enforcement；`bills` 建表 migration 不在本 repo（legacy 表），**無法查核 DDL 層 enum／check constraint** |
| `App\BillActivityLog`（`app/BillActivityLog.php:42-44`） | S1 | **FAIL → S4** | `action` 欄為 `string(50)`（`database/migrations/2026_06_25_000001_create_bill_activity_logs_table.php:27`），非 enum；且**自陳為部分稽核**：「專責記錄費用更新（fee_edit）、取消帳單（cancel_bill）**等**異動」 |
| `services/jgb_system_api.py`（chatbot API client，2062 行） | S2 | **out of scope** | 它界定的是**對話端能呼叫什麼**，不是**平台能執行什麼**，更不是**使用者會描述什麼問題** |
| 任何 binding exhaustive spec | S3 | **未找到** | 未找到任何對本次 audited version 具 enforcement 的全集規格；無 binding argument 可寫 |

⚠️ 依協議 §1，上述 FAIL 的來源**不得**以 S4 身分回頭充當封閉性證據；
依 §2 wording guard，它們在 **qualification 階段即被淘汰**，故本次**無 conflict 需記錄**。

---

## 逐 domain 判定（協議 §4 totality argument）

### `operation_class` → **NOT PROVEN**

要寫的 totality argument 是：「為什麼不在清單裡的帳單操作，在這個系統中不可能發生？」**寫不出來。**

決定性證據——**路由不是操作的邊界**：

```php
// routes/web.php:1198
Route::match(['get', 'post'], '/batch/{action?}', 'BillController@batch')->name('bills.batch');
// routes/web.php:1180
Route::match(['get', 'post'], '/items/{action?}', 'BillController@item')->name('bills.item');
```

```php
// app/Http/Controllers/BillController.php:7041
public function batch(Request $request, $action = '')
{
    ...
    switch ($action) {
        case 'import':
```

operation 名稱以**自由字串**從 URL 片段進入，於控制器內 `switch` 分派。
故 route registry 只界定 endpoint 集合，**不界定 operation 集合**——S2 的資格條件
（「不在其中的 operation 無法被執行」）**不成立**。

唯一具 operation 語義的枚舉 `BillActivityLog::ACTION_*` 僅三個值
（`fee_edit`／`cancel_bill`／`void_invoice`），欄位型別為 `string(50)`，
且其 docblock 自陳只涵蓋部分異動。這是協議 §4 定義的 **observed values**，不是 closed domain。

### `entity_scope` → **NOT PROVEN**

對話層實際承載「這是哪一類實體」的是 `entity_noun`——一個**自由字串設定值**，
且有 code 內建預設：

```python
# services/conversational_engine.py:941
noun = mapping.get("entity_noun", "合約")
```

其值來自 `result_mapping`（knowledge_base 的 `generation_metadata` jsonb，後台可編），
**不是枚舉**。平台側 `App\Bill::TARGET_TYPE_*`（`app/Bill.php:55-59`）雖為有界常數集，
但同樣落在上表 `App\Bill` 的 **INSUFFICIENT** 判定內（無 DDL 層 enforcement 可查），
且**無任何 artifact 把 facet 的 entity_scope 綁定到它**。

依協議 §5，「找不到別的實體型別」**不得**推論為「不存在別的實體型別」。

### `problem_state` → **NOT PROVEN**（觸發協議 §4 的特別嚴格條款）

**本次查核無法指名任何 candidate authoritative source。**
沒有 S1（無任何列舉「問題形態／失敗型態」的 enum、狀態機或 constant registry）、
沒有 S2（問題形態不是被分派的東西，無 registry 可言）、
沒有 S3（未找到宣告全集且具 binding 的規格）。

依協議 §4 特別條款：

> 若不存在能給出全集語義的獨立 authority → 該 domain 判 `NOT PROVEN`，G1 即失敗。

⚠️ **這一格單獨即足以使 G1 失敗**，且它正是 proposal 事前指認的最弱一格。

### `responsibility`（組合 → Face 的 mapping）→ **NOT PROVEN**

新發現，且對 schema closure 是決定性的：**Face 集合本身是資料驅動、後台可增的**。

```python
# services/conversational_config.py:15（模組 docstring）
# **新增一組面向/角色 = 後台加一筆「對話規則」（含上述 metadata），零改程式。**
```

面向由 `knowledge_base` 中 `category='對話規則'` 的資料列定義（`CONFIG_CATEGORY`，
`services/conversational_config.py:23`）。故該 mapping 的**值域（Face 集合）由 DB 內容決定**，
不由程式建構界定——**codomain 開放**。

---

## Schema closure → **NOT PROVEN**

兩個獨立的理由，任一皆足以判 NOT PROVEN：

```text
① 三個已宣告 domain 全部 NOT PROVEN
   → 無法主張「由這些維度組成的 schema 是封閉的」

② responsibility 的值域（Face 集合）本身開放（後台可增，零改程式）
   → 一個把開放值域當終點的維度組合，**無法由建構保證封閉**
```

⚠️ 協議 §3 要求「宣告 dimension 必須指名一個來源，該來源**本身**把這個維度當成獨立分類軸」。
本次查核**未找到任何來源**把 `entity_scope`／`operation_class`／`problem_state`
當成分類軸來使用——這三個軸目前只存在於本工作線自己的文件中（即 S7，非法來源）。

---

## Negative control

### NC-1｜`target`（undeclared dimension）→ **FAIL，如預期**

`target` 未出現在任何 S1／S2／S3 來源中，亦不在已宣告維度清單內。
G1 依 §3 判 **FAIL**。
⚠️ 本控制證明本次查核**會咬**：它沒有因為 `target` 讀起來合理就放行。

### NC-2｜case-induced addition

本次為 **FAIL**，未進入 PASS 狀態，故 NC-2（PASS 後因新案例擴表）**本輪未被觸發**。
該控制保持有效，供未來任何宣稱 closure 成立的版本使用。

---

## 依協議 §6 的後果（事前寫定，非事後決定）

```text
❌ MUST NOT 補上 dimension／value 後繼續走 member-2
❌ MUST NOT 放寬 §4 的 totality 要求重判
✅ B／C 退場，D3 回到 member-shape discovery
✅ 「哪一層封不起來」作為結論記錄：**三層全部封不起來，且 responsibility 的值域本身開放**
```

## 本次查核**未**回答（協議輸出限制，越界即為協議違反）

```text
❌ D3-member-2 會不會準
❌ query → dimension 能不能可靠映射
❌ 哪些 Round 1 cases 可以被修好
❌ B 比 A 好多少
```

---

## 這次 FAIL 回答了什麼（協議 §4 事前寫明「這不是壞結果」）

> **B 是否只是把 open enumeration 往下搬一層？**

依本次證據：**是**。

```text
A 的開放性在「問題措辭」
B 把它搬到 entity_scope × operation_class × problem_state
但這三格在本系統中**都找不到能宣稱全集的 authority**，
且組合的終點（Face 集合）**本身就是後台可增的資料**。
```

⚠️ 這**不反證** D3 family（M1），也**不反證**「組合式 representation 在別的系統中可行」。
它反證的是**在這個系統的現況下**，B／C 取得不了封閉性前提。
