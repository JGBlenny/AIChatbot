# R10：Retrieval Responsibility Identity —— **三案設計比較（⛔ 不實作）**

## 0. 現行 production constraints（比較的地基，皆為實查）

```text
pipeline  _vector_search（~20 筆，SQL 端**不卡門檻**）
          → rewrite union → keyword fallback → keyword boost
          → 下限 RERANKER_MIN_VECTOR_SIMILARITY=0.3（只砍 vector 項）
          → 截斷 RERANKER_INPUT_LIMIT=20（⚠️ **重複列在此就吃掉輸入名額**）
          → reranker（評 `scoring_surface`）
          → _finalize_scores：similarity = 0.1×vector + 0.9×rerank
          → 門檻 KB_SIMILARITY_THRESHOLD=0.65 → top_k
nomination 讀 **top1 的 categories**（`_knowledge_category(best_knowledge)`）
transport `retrieval_representation` 目前是 **per-row** 投影（`_format_result`）
既有分層 `_drop_empty_answer_rows`：answer 空且無動作的列＝**只供進場**，
          落回單發答題前必須濾除 ⇒ **「entry-only」的角色分離已存在**，
          ⚠️ 但只發生在 **answer 階段**，⛔ **不在 scoring／ranking 階段**
```

⚠️ 最後一條是本案的關鍵：系統**已經**承認 alias 與 answer 是不同角色，
只是那道分離**太晚**——duplicate 早已在 recall／rerank／top-k 競爭過了。

---

## 1. 六問對照表

| | **A per-row（現況）** | **B per-facet** | **C responsibility_id** |
|---|---|---|---|
| **① Identity** | `knowledge_id` | `facet_key` | `responsibility_id` |
| **② Authoring** | 每列各寫 `retrieval_representation` | facet 上一份 canonical | responsibility 上一份 canonical |
| **③ Recall** | 各列自己的 summary／keywords | alias 仍可 recall，但無獨立身分 | alias 仍 recall，且**明示**其角色 |
| **④ Collapse** | **無** | recall 後依 facet 折疊 | 依 `responsibility_id` 折疊（C1/C2/C3 見 §3） |
| **⑤ Scoring** | 每列各自 rerank | facet canonical | responsibility canonical |
| **⑥ Output/authority** | top1 **row** → 讀其 categories → 提名 Face | facet 直接是 candidate | responsibility → 其 owner（目前為 Face） |

## 2. 逐案評估

### A — per-row（baseline，⛔ 非認真候選）

```text
F1 同 responsibility 的 alias 各寫不同 representation ⇒ 發明不存在的責任差異
F2 各寫相同 representation ⇒ duplicate semantic candidates ⇒ ranking competition／
   任意勝者；且在 RERANKER_INPUT_LIMIT=20 的截斷點就**吃掉別的 responsibility 的名額**
```
⇒ **A = REJECTED AS TARGET ARCHITECTURE**，保留為 legacy compatibility baseline。

### B — per-facet

```text
✅ 能解掉今天這批 anchors（3939/3940、3934-3936…）
⛔ 隱含假設 facet : responsibility = 1 : 1 —— **未被證明，且很可能已經是錯的**
   實證：late_fee 現在就同時存在
     late_fee_mechanism_general（3531／3532）
     late_fee_instance_diagnosis（3939／3940）
   兩者 applicability 相反（general vs instance）⇒ ⛔ 不可能共用一份 canonical contract
```
⇒ **B = VALID LOCAL MODEL，但 GRANULARITY CEILING CONFIRMED**——
⚠️ 這不是理論疑慮，本專案**這一輪就已經撞到**。

### C — explicit `responsibility_id`（primary candidate）

```sql
retrieval_responsibilities
  responsibility_id / facet_key / retrieval_representation
  / applicability / status / provenance

knowledge rows
  knowledge_id / responsibility_id / question_summary / keywords
  / role = ENTRY_ALIAS | ANSWER_KNOWLEDGE | ...
```

實例（本輪已具備全部素材）：

```text
responsibility_id  late_fee_instance_diagnosis
  facet late_fee｜applicability instance｜owner late_fee Face（B 引擎）
  aliases 3939、3940
responsibility_id  late_fee_mechanism_general
  facet late_fee｜applicability general
  knowledge 3531、3532
```
⇒ 這個模型**自然表達**了我們花很多輪才拆出來的三件事：

```text
同 facet ≠ 同 applicability ≠ 同 responsibility
```

---

## 3. Collapse 點：C1／C2／C3

### C1 — retrieval 前 collapse（只索引 responsibility）

```text
query → responsibility index → responsibility scoring
✅ 最乾淨；候選集天生無重複
⛔ 「一種講法一筆」的 recall 價值**直接消失**——alias 不再是可被 recall 的文本
⚠️ 現行 recall 高度依賴 alias：keyword fallback 與 keyword boost 都吃 row 的
   summary／keywords；改成只索引 canonical，等於同時拿掉 lexical 進場面
⇒ **不建議直接採**
```

### C2 — vector recall 後、reranker 前 collapse ← **最看好**

```text
query → alias-aware vector recall（rows）→ group by responsibility_id → collapse
      → canonical responsibility representation rerank → responsibility candidate
✅ alias 全部保留 recall 價值（3939／3940 都能把 responsibility 帶進候選集）
✅ 進 reranker 前只剩 late_fee_instance_diagnosis ×1 ⇒ ⛔ 不再互打
✅ 正好落在**現有管線已有的斷點**：keyword boost 之後、
   `RERANKER_MIN_VECTOR_SIMILARITY` 下限與 `RERANKER_INPUT_LIMIT` 截斷**之前**
   ⇒ ⚠️ 同時解掉「重複列吃掉 reranker 輸入名額」這個今天已存在的浪費
✅ 責任分工乾淨：alias = lexical/utterance recall evidence；
   canonical = semantic responsibility evidence
```

### C3 — reranker 後 collapse

```text
⛔ 太晚：duplicate competition **已經發生**
   · 佔掉 top-k slots
   · 擠掉其他 responsibility
   · 同 responsibility 多 alias 放大權重
⇒ **C3 = insufficient**，除非另加 dedup／top-k allocation 機制
```

---

## 4. alias 分數如何聚合（即使採 C2 仍必答）

```text
recall 出來可能是：3939 .82／3940 .79 ⇒ responsibility recall score = ?
候選：MAX(alias scores)／canonical representation embedding score／混合
```

**第一候選（與業主 prior 一致）**：

> **alias 只負責讓 responsibility 進 candidate set，⛔ 不取得 semantic authority。**

```text
alias hit → nominate responsibility candidate
canonical responsibility representation → authoritative semantic rerank
```

⚠️ **為什麼這條特別重要**：若讓 alias 分數直接成為 responsibility 分數，
**alias 數量就變成 voting weight**——一個 responsibility 寫了 5 個講法、
另一個只寫 1 個，就會因 **authoring density** 取得不公平優勢。
⇒ 那會把「知識工程寫了幾種講法」偷換成「這個責任比較相關」。

---

## 5. applicability 的單位也會跟著移動

```text
現況  per-Knowledge-row declaration
風險  同 responsibility 的 aliases 未來可能被寫成 3939=instance／3940=general
      ⇒ contract contradiction
C 的長期形態  applicability → **responsibility-level**
              entry alias **繼承** responsibility 的 applicability
```
⚠️ 這是 R10 的比較事項，⛔ **現在不做 migration**。
⚠️ 不變量 16 目前守的正是這個洞的 representation 版本（見 §7）。

---

## 6. 完整比較表（業主指定欄位）

| 欄位 | A per-row | B per-facet | C（+C2 collapse） |
|---|---|---|---|
| schema | 現況 | facet 上加 representation | 新表 `retrieval_responsibilities` ＋ row 加 `responsibility_id`/`role` |
| authority unit | row | facet | responsibility |
| alias role | **未定義**（alias 即 candidate） | 隱含 recall | **明示** `ENTRY_ALIAS` |
| canonical contract location | 每列 | facet | responsibility |
| collapse point | 無 | recall 後 | **vector recall 後、reranker 前** |
| embedding unit | row | facet canonical | responsibility canonical（alias 另有 recall 文本） |
| reranker unit | row | facet | responsibility |
| applicability unit | row | facet | responsibility（alias 繼承） |
| candidate identity | `knowledge_id` | `facet_key` | `responsibility_id` |
| migration impact | — | 中：facet 表加欄、collapse 層新增 | 高：新表＋回填＋collapse 層＋transport 擴充（不變量 11 需同步） |
| backward compatibility | — | row 仍存在，nomination 需改讀 facet | row 保留；nomination 由 responsibility → owner，⚠️ 現行讀 top1 categories 的路徑要改 |
| 解掉的已知 failure | 無 | F1／F2（本批 anchors） | F1／F2 ＋ facet 粒度天花板 ＋ reranker 輸入名額浪費 |
| **新引入的 failure 風險** | — | facet 內多責任被壓扁（**已實證存在**） | ⚠️ ① responsibility 切分本身成為新的人為判斷；② collapse 後**除錯可讀性下降**（使用者看到的候選不再對應單一 KB 列）；③ 回填錯誤會一次影響整個 responsibility |
| validation-unit impact | A05-9 驗 9 rows | 驗 facet 數 | ⚠️ 驗收 denominator 由 row 變 responsibility |

---

## 7. 對現有守門的影響

```text
不變量 16 = **TRANSITIONAL_GUARD**（業主 2026-08-29 明示）
  現在守：同 responsibility 的 aliases ⛔ 不得各自發明不同 semantic contract
  ⚠️ 「允許逐字相同 contract」只是避免 migration 卡死，
     ⛔ **不代表終局允許兩份相同 semantic document 各自進 ranking**
  R10 若採 responsibility-level candidate，應升級為更強版本：
     **ENTRY_ALIAS ⛔ 不得成為獨立 authoritative semantic-scoring candidate**
⇒ 現在**保留** 16，⛔ 不拿掉。
```

---

## 8. A05 暫停的正式記錄

```text
A05_STATUS = PAUSED_BEFORE_PROTOCOL_FREEZE
reason     = candidate identity unit under active architectural review
current    = row-level scoring candidate
R10 cand   = responsibility-level scoring candidate
risk       = validating row-level candidate now may validate a **superseded judgment unit**
```
⚠️ 這**不是**因 validation 困難而拖延，而是 **measurement unit 尚未穩定**。

### ⚠️ 但有一項對 A05 有利的實測，先記下來

```text
A04 兩位獨立 labeler 產生的 MULTI_OWNER 叢集**全部落在 N 層**：
  (3366,3932)×10／(3934,3935,3936)×9／(3362,3937,3938)×7／(3939,3940)×3
⛔ **沒有任何一組**落在 Level-A 的 9 rows。
且 4640（2026-07-31）、4656／4657（2026-08-03）與那 12 個錨點（2026-07-03）
**不同批**，也不在 entry-alias 登記簿內。
⇒ 目前證據指向：**LEVEL_A_V2 的 9 rows ≈ 9 個相異 responsibility**，
  A05 的 denominator 很可能不會因 R10 而改變。
⚠️ 但這是**旁證**，⛔ 不足以取代 R10 裁定後的正式重盤。
```

---

## 9. 待業主裁

```text
Q1 採 C（+C2）作為 target architecture？還是先停在 B？
Q2 alias 聚合是否凍成「alias 只提名、⛔ 不取得 semantic authority」？
Q3 applicability 是否隨之上移到 responsibility 層（alias 繼承）？
Q4 R10 若採 C，是否需要先做一次 responsibility 切分的**人工 review**
   （⚠️ 那是新的人為判斷點，本身需要 provenance 紀律）？
```
⛔ 本文件不實作、⛔ 不改 schema、⛔ 不動任何 row。
