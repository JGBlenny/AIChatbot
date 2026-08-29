# U1：category 是否足以承擔 nomination evidence —— 本地證據（第一刀）

- 日期：2026-08-29｜方法：全量 SQL ＋ 原始碼契約對讀，**零標註、零流量**
- 約束：release 已 BLOCKED_BY_VALIDATION_COMPLETION ⇒ ⛔ 不得以 production telemetry 為必要證據

## 把 U1 拆成三個可分別裁決的子命題

```text
(a) 歧義性   category 提名出來的候選集，是否會出現「順序決定結果」
(b) 覆蓋率   有多少 row 具備提名路徑（設定事實）
(c) 適格性   category 內部是否**同質**於「該不該由 Face 擁有」
```

---

## (a) 歧義性：**已在本地裁定 —— category 幾乎不產生歧義**

```text
0 候選（不提名）              684 筆  78.4%
1 候選（唯一 owner）          184 筆  21.1%
2 候選（**順序決定結果**）      5 筆   0.6%
```

⇒ 可提名的 189 筆中，**184 筆（97.4%）由 category 決定唯一 owner**。

⚠️ 這推翻了我先前的擔憂措辭。「MIXED categories 讓 category 太粗」若指的是
**提名歧義**，那是**錯的**——歧義率 0.6%。first-commit-wins 的順序語義
在現實設定下幾乎不被觸發。

## (b) 覆蓋率：設定事實已知，但「該不該有」無法從設定得知

```text
21.5% 的 knowledge rows 具備 category→Face nomination capability
⛔ 這是 KB configuration coverage，不是 production traffic coverage，也不是漏接率
```

## (c) 適格性：⛔ **無法從設定判定——因為那個屬性根本沒有被記錄**

### 機械訊號顯示 mapped category 內部確實異質

```text
category          rows  有 execution 的 rows
狀態判斷            19        15
物件操作引導         14         2
帳單設定引導         17         1
繳費金流排障         11         6
條件診斷：帳單       10         4
發票                 6         3
修繕報修             5         1
⇒ **每一個** mapped category 都混著有／無 execution 的 row。
```

### 但 `has_execution` 只是弱代理，而**真正的屬性沒有任何欄位承載**

```text
決定歸屬的屬性 ＝「回答這一題需不需要**使用者自己的資料**」

knowledge_base 的 49 個欄位裡：
  form_id／action_type／api_config  → 編碼的是**執行**，不是**實值依賴**
  category／categories              → 主題
  target_user                       → 角色
  ⇒ **沒有任何欄位表達「需要個別資料」**

反證：3509「訂閱扣款失敗導致功能異常」是 `direct_answer`、無 form_id，
      卻明確需要查該帳號的訂閱狀態 ⇒ has_execution 對它是 False，但它需要實值。
```

### 而且架構**曾經**為這個屬性留了位置——沒有人填

```text
services/instance_reference_gate.py
  INSTANCE_REFERENCE_KEY = "requires_instance_reference"
  is_instance_requiring_face(config)  ← 只讀 Face 的明示宣告，**明文禁止 fallback**
  缺欄位 → False（fail-closed by scope）

實查：宣告 requires_instance_reference 的 Face 數量 ＝ **0**
⇒ 條件 C 恆為 False ⇒ instance gate **在結構上不可能觸發**。
  這把先前「gate 零效果」的歸因收斂到最精確的一句：
  **不是接線問題、不是覆蓋問題——是那個契約欄位沒有任何人宣告。**
```

---

## U1 第一刀的裁定

```text
(a) 歧義性  ✅ **本地已裁定**：category 不產生實質歧義（97.4% 唯一 owner）
(b) 覆蓋率  ✅ 設定事實已知（21.5%）；「該不該更高」取決於 (c)
(c) 適格性  ⛔ **無法從設定判定** —— 目標屬性未被記錄為資料
```

⇒ **U1 不是「category 太粗」的問題，是「判準沒有落成資料」的問題。**

這與本專案既有教訓同型：**規則只能治封閉集合，開放語義要換層**；
以及 retrieval-decision-layer 記下的三缺陷之一「概念沒有落成資料」。

## 兩條可能的收束路徑（⛔ 尚未選，待裁）

```text
【P1 換層】把「是否需要個別資料」記成**資料**
   ・row 層：knowledge_base 新增屬性（或 generation_metadata 內的宣告）
   ・Face 層：補上早已定義好、卻無人宣告的 `requires_instance_reference`
   ⇒ nomination 從「用主題猜歸屬」變成「讀宣告」，
     category 退回它本來的角色（主題標籤），與裁定 001 完全相容。
   ⚠️ 這是設定工程，可在本地完成並以不變量稽核；不需要 production 流量。

【P2 標註驗證】先證明「category 與該屬性的相關性有多低」再決定
   ・需要 isolated blind labeler（走 holdout-validation skill）
   ・⚠️ 需要動用 Agent；本 session 未獲授權，故未執行
```

## 本刀**不能**回答

```text
⛔ 78.4% 未 mapping 的 row 裡，有多少「應該」進面向
   —— 那正是 (c)，而 (c) 需要的屬性不存在於資料中
⛔ 任何 production 流量分布
```
