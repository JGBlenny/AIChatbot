# ⛔ P0 缺陷：向量索引 IVFFlat 參數錯誤，靜默丟棄正確答案

> 2026-09-01｜b2b 35 題實測發現｜**這是程式缺陷，不是線上組態**——DDL 在版控裡

## 一句話

`idx_kb_embedding` 是 `lists=100` 的 IVFFlat 索引，而全表只有 **992 筆**向量
⇒ 每個 list 約 10 筆，`ivfflat.probes` 預設 1 且**全 repo 從未設定**
⇒ **每次檢索只掃到全庫約 1%**，最相關的知識常常根本沒被看到。

## 缺陷在程式裡的位置

```text
database/init-legacy/02-create-knowledge-base.sql:78-81
  -- lists 參數：建議設為 sqrt(總資料筆數)，這裡預估 1000 筆，設為 100
  CREATE INDEX IF NOT EXISTS idx_kb_embedding ON knowledge_base
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

⚠️ 註解自己的算式就錯了：sqrt(1000) ≈ **31.6**，不是 100。
⚠️ 且 pgvector 對 <1M 筆的建議是 **lists ≈ 筆數/1000**（此表 ⇒ 1），
   sqrt 是 >1M 筆才用的規則。
⛔ 全 repo（*.py／*.sql）**查無任何一處** `SET ivfflat.probes`
   （DATABASE_SCHEMA.md:1370 有把它寫成可調旋鈕，但沒有任何程式真的調）
```

## 實測影響（b2b 35 題，凍結選題規則抽樣）

```text
top-20 候選池平均召回率           **31%**   ⇒ 平均漏掉 69% 應有候選
top-1 與精確掃描**不同**            16／35（46%）
ANN 回不滿 20 筆                   23／35
raw vector 概算跨越門檻 0.65 的     8／35（23%）
  ＝現行「答不出來」、精確掃描「答得出來」
  ⚠️ 實際 gate 走的是 0.1×vector＋0.9×rerank 的融合分數，此為概算，⛔ 非精確值
```

最極端的三題（同一問句、只切換索引路徑）：

```text
社區跟物件怎麼綁定          現行 kb:3127「社會住宅」0.5614 → 精確 kb:3469 **0.9238**
通知信箱的群組設定要怎麼做？  現行 kb:3435「註冊帳號」0.4568 → 精確 kb:3451 **0.8308**
怎麼去設置通知的信箱群組？    現行 kb:3448           0.4734 → 精確 kb:3451 **0.8154**
```

⚠️ **最危險的是它不會報錯**：第 2、3 題現行都回了滿滿 15 筆，
表面完全正常，只是每一筆都不是對的那筆。

## 同一缺陷的其他受害表（同為 lists=100）

```text
vendor_sop_items.primary_embedding      407 筆   ← b2c 租客的 SOP 檢索
vendor_sop_groups.group_embedding        22 筆   ← ⚠️ 22 筆配 100 個 list
ai_generated_knowledge_candidates        36 筆
knowledge_review_queue                    0 筆   （無資料，暫無影響）
loop_generated_knowledge                          HNSW，⛔ 不受此缺陷影響
```

## 這推翻了什麼

```text
⛔ 本 session 先前所有「語義召不回」「知識寫得不好」的歸因**不可信**
   ——那些題可能只是索引沒掃到
⛔ 我提名候選知識時用的詞面排名雖不受影響，但**驗證用的向量排名受影響**
⚠️ 歷來所有回測（含 69.7% 那批）都跑在這個索引上
   ⇒ ⛔ 不能說那些數字「錯」，但它們**低估了系統的真實能力**
⚠️ 「補 retrieval_representation 以提升召回」這條路線的前提要重新評估
   ——目前召回率低的主因可能不是表示法
```

## 修法（⛔ 業主自己執行，我不代跑）

### 為什麼不是「調 probes 就好」
調 probes 要改程式（每個連線 `SET ivfflat.probes`），而且 992 筆的表
本來就不需要 ANN 索引——精確掃描是毫秒級。

### 選項 A（建議）：直接移除索引，走精確掃描
```sql
DROP INDEX IF EXISTS idx_kb_embedding;
```
預期輸出：`DROP INDEX`
之後驗證：任一問句的 top1 應與本檔「精確」欄一致。
⚠️ 992 筆全掃的延遲增加在毫秒級；⛔ 若知識庫成長到數萬筆需改用 HNSW。

### 選項 B：改建 HNSW（未來可擴充）
```sql
DROP INDEX IF EXISTS idx_kb_embedding;
CREATE INDEX idx_kb_embedding ON knowledge_base
USING hnsw (embedding vector_cosine_ops);
```
⚠️ HNSW 建索引較慢、記憶體較多；召回率遠優於 IVFFlat。

### 無論選 A 或 B，都要一起修的
```text
① database/init-legacy/02-create-knowledge-base.sql:78-81 的 DDL
   ⛔ 不改它，下次重建資料庫會把缺陷帶回來
② 同樣 lists=100 的另外三張表（vendor_sop_items 407／vendor_sop_groups 22／
   ai_generated_knowledge_candidates 36），⚠️ vendor_sop_items 直接影響 b2c SOP 檢索
③ 加一條稽核不變量：向量索引的 lists ⛔ 不得大於「筆數/1000 與 1 取大者」的合理範圍
   （本專案鐵則：修一類 bug 加一條不變量）
```

### 驗證方式（改完請跑）
```sql
-- 應該回 kb:3451，sim ≈ 0.83
-- （用任一 embedding 產生工具取「通知信箱的群組設定要怎麼做？」的向量後）
```
或直接重跑本 batch 的 35 題，對照本檔的「精確」欄。
⚠️ ⛔ 別只看延遲不看結果——延遲沒變不代表召回修好了。

## ⛔ 尚未做的事

```text
⛔ 我沒有修改任何索引、資料或程式
⛔ 35 題的「該命中哪筆」仍未經業主確認 ⇒ 上面的率是診斷，不是收案證據
⛔ b2c／SOP 側的同類影響未量測
