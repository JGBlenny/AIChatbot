# R10-CANONICAL-REVIEW 章程（業主裁定 2026-08-29）

## 一、順序（⛔ 不得跳步）

```text
R10-P5                 ✅ DONE
↓
R10-CANONICAL-REVIEW   ← **NEXT**
↓
R10-C2 implementation
↓
A05
```

## 二、四項裁定

```text
① 補 canonical：**現在做，且補滿 active 30/30**——⛔ 不只補 Level-A 9
② 正式命名：**不做**。`R-01…R-31` 保留為**永久 opaque identity**
③ 16 個 unresolved：**暫不追**，⛔ 不阻塞 Level-A
④ A05：denominator 已解鎖，但等 canonical ＋ C2 implementation 後才 freeze protocol
```

### ① 為什麼補滿 30 而不是只補 9

只補 9 會留下 transitional state：

```text
responsibility A → 有 canonical，可 C2 scoring
responsibility B → reviewed_active，但 canonical=null
```

B 若在 A05 query 被 recall 到，就得**臨時決定**：fallback row scoring？不讓它進 reranker？
用 summary？用 alias max？——**每一種都會改變 A05 的競爭環境**。

⇒ 立為不變量 21：

```text
status = reviewed_active     → canonical_responsibility MUST be non-null ＋ reviewed
status = reviewed_historical → ⛔ 不要求 active scoring canonical（3498 豁免）
```

### ② 為什麼 `R-xx` 不重新命名

```text
responsibility_id = R-17
canonical_responsibility = 診斷某一筆帳單為什麼無法發送給租客……
```

比 `responsibility_id = bill_cannot_send_diagnosis` **更安全**：
canonical 未來可能精修措辭，但 **identity ⛔ 不應因此變更**。
語義放在 `canonical_responsibility`／`facet`／`owner`，⛔ 不塞進 primary key。
若未來需要 developer-friendly slug，那是另一個 display/key 欄位設計問題，
⛔ 不得為此改 frozen registry schema。

### ③ 為什麼 16 個 unresolved 現在不追

它們已被正確隔離：`reviewed population disposition = unresolved`、
`authoritative responsibility membership = none`；且 P5 已證明
**Level-A V2 與它們沒有責任共用／多重 membership** ⇒ ⛔ 不再阻塞 A05 denominator。
現在去追會把 scope 從「完成 Level-A candidate validation」擴回全治理母體。

## 三、review 規約（⛔ 不得違反）

```text
① ⛔ 不得從 row representation 自動搬：
   row.retrieval_representation → copy → responsibility.canonical → authoritative  ⛔ 禁止
   （authority unit 已從 row 換成 responsibility）
   逐字沿用**可以**，但那是 **reviewer 的裁定結果**，⛔ 不是 migration rule。
② multi-member responsibility 的 canonical 必須描述**共同責任**：
   3365+4420 要寫「查詢既有修繕案件的目前進度／狀態」這類共同 contract，
   ⛔ 不得偏向 form row 或 action row 任一邊。
   （本輪共 8 個 multi-member：R-01/02/03/04/05/08/09/28）
③ 3511 ⛔ 不產 canonical——它沒有自己的 responsibility。
④ 每筆裁定 ∈ {APPROVED, REVISE, INSUFFICIENT}，並記
   members ＋ P3 identity ruling ＋ owner/capability ＋ applicability ＋
   existing reviewed row representation（若有）作為 review basis。
```

## 四、C2 implementation 的目標管線（canonical 補滿後才做）

```text
row / alias recall
→ keyword boost
→ map row to **0..N** responsibility IDs
→ collapse
→ threshold
→ RERANKER_INPUT_LIMIT
→ canonical responsibility rerank
```

```text
alias score     = nomination evidence only
canonical score = semantic authority
```

⚠️ `map row to 0..N` 的 **0** 對應 16 個 unresolved 列，**N>1** 對應 3511——
P4 的多重 membership 投影已經先驗證了這個關係。

## 五、A05 屆時的正式寫法

```text
validation unit             = responsibility
LEVEL_A_V2 denominator      = 9
```

正向機器證據（P5 census）：

```text
LEVEL_A_V2 rows              9
unique reviewed responsibilities  9
multi-membership             0
shared responsibility        0
```

⛔ 不得沿用 A04 的 corpus／protocol／judgment unit——那是 row-level 10 strata 的**上一世代**。

## 六、現況

```text
canonical 閉合   **8 / 30**（不變量 21 紅＝**產品閘**，⛔ 非程式回歸）
待裁清單         r10p/canonical-review-dossier.md（30 群，VERDICT 全空）
已有業主陳述     8 筆（3490／3491／3492／3493／3494／3510／3531／3532 的 P3 identity ruling）
⚠️ registry.json 補完 canonical 時 bytes 會變 ⇒ 需開 **registry epoch 2**：
   REGISTRY_DIGEST 重新凍結，舊 digest 3e5bcdc6… 保留為 V1（⛔ 不覆寫）
```
