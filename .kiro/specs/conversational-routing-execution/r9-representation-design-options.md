# R9：retrieval representation contract —— 設計選項比較（2026-08-29）

⛔ **設計文件**：未實作、未寫 DB、未改任何 scoring surface、未跑語料。

## 已裁的上位方向（業主 2026-08-29）

> **⛔ 不要再把 `question_summary` 同時當成人類摘要、embedding representation、
> reranker representation 的唯一契約。**

⇒ 因此本檔比較的是「**如何建立 retrieval representation contract**」，
⛔ **不是**比較「answer 要不要加回去」。

## 四案比較

| 方案 | 核心 | 能否解 3406（surface 不一致） | 能否解 4656（capability 未表示） | 主要風險 |
|---|---|---|---|---|
| **A** 擴充 `question_summary` | 要求 summary 完整表示 capability envelope | ✅ | ✅ | 人類摘要與 retrieval contract **繼續綁死**；4656 會被迫寫成又長又醜的關鍵詞串 |
| **B** 新增 `retrieval_representation` | 專門描述「這列實際能承接哪些語義」 | ✅ | ✅ | 新增資料契約與 migration；需治理規則 |
| **C** reranker 改吃 summary＋keywords | 讓 reranker 看到 embedding 已有的表示 | ✅ | ❌ | ⛔ **不能作 architecture-level closure**；keywords 可能重新帶來噪音 |
| **D** 多 surface scoring 再融合 | 各 surface 分別評分 | ✅ | ✅ | 最複雜；**直接碰 scoring policy**，最容易重開歷史 calibration 問題 |

### ⚠️ C 為何不足以收束（有實據）

```text
4656 現況：summary「查帳單 帳單編號查詢」＋ keywords「帳單／查詢／編號」
即使 keywords 全數進 reranker，仍**沒有**
  已繳／未繳・已寄出／草稿・到期・完整現況
⇒ capability semantics **根本不在任何欄位裡**，C 無從補起
```

⇒ **B 為 primary candidate，C 為局部相容候選**（⛔ 皆非批准實作）。

## 第一問：「覆蓋」如何機器可驗

```text
⛔ 不採 lexical coverage —— 會把我們拉回關鍵詞工程，
   且「已繳還是草稿」與「帳單目前狀態」語義等價、詞面不同
⛔ 不採「讓 embedding／reranker 自己當 contract checker」——
   那等於 production scoring system 自己證明自己的 representation 足夠，
   **量尺又與被測物黏在一起**（本輪已多次踩過）
```

✅ 採 **declaration ＋ deterministic governance**：機器守**契約完整性**，
⛔ **不憑 absence 自行推 semantic truth**（同 `instance_applicability=general` 的紀律）。

機器**可以**驗的五件事：

```text
1. Level-A row 必須有 declaration
2. declaration 不得為空
3. representation 必須由**指定的唯一欄位**產生
4. embedding 與 reranker 使用同一 contract；若不同，**必須明示各自 surface**
5. fixture 不得比 production representation 多語義（延續不變量 11 的紀律）
```

⚠️ 機器**不能**驗的：「自然語言語義已完整覆蓋 responsibility」
⇒ 那一段仍需 **reviewed product declaration**，⛔ 不假裝可自動化。

## 第二問：keywords 不進 reranker

⛔ **不裁成「keywords 必須進 reranker」**。應建立的是設計要求：

> **任何 scoring stage 若使用不同 semantic surface，
> 差異必須是明示 contract，而非歷史實作偶然。**

```text
未來合法允許 embedding_surface ≠ reranker_surface，但必須說明：
  ・哪一段語義刻意只給 embedding
  ・為什麼 reranker 不需要
  ・validation 如何證明不造成 semantic loss
目前**沒有**這份 contract ⇒ 這就是 gap 本身
```

## 第三問：是否推翻「answer 稀釋 intent」

**採 B 則不需要推翻。**

```text
⛔ 不從 summary-only 直接跳到 summary＋full answer
✅ 建立**為 retrieval 特別撰寫、經 review** 的 responsibility representation
   —— 比 summary 完整，比 answer 精煉
⇒ 歷史結論保留為**設計約束**，⛔ 而非被推翻
⚠️ R6 只證明「summary-only 在 3406 某些 query 會丟掉必要語義」，
   ⛔ **未**證明 full answer 是正確的 universal replacement
```

---

# Design-only migration simulation（本檔的實質新工作）

對 frozen Level-A 10 rows 試寫 responsibility atoms，檢驗：
**同一份契約能否同時表達 3406 型與 4656 型的失敗，且不需把 full answer 塞進 scoring。**

```text
3402  自動產生時機｜結算項目（水電／賠償／其他）｜到期日來源｜與押金互抵
3406  下載收據的位置與方式｜收據可作繳費證明｜未繳費不可產生｜與統一發票的區別
3519  金額算法與加減項｜正負號語義（含押金扣完不足需補繳）｜明細可見性
3495  診斷**該筆**帳單為何無法發送（狀態／必填欄位）
3496  診斷**該筆**帳單為何無法取消（狀態條件）
3498  診斷**該筆**帳單的逾期費成因（公式＋該筆實值）
3499  診斷**該筆**帳單手動到帳失敗的原因
4640  查詢**該筆**收據的實際金額
4656  識別特定帳單｜查詢其**目前狀態**：已繳／未繳・已寄出／草稿・到期・完整現況
4657  查詢**該份合約**點退帳單的實際金額
```

## 模擬結果

```text
✅ 4656 型（capability 未表示）——**可被表達**
   atoms 直接寫出「已繳／未繳・已寄出／草稿」，正是 A03 中 I2 失敗 query 的語義
   且**不需要 answer**（它本來就是空的）

✅ 3406 型（surface 不一致）——**可被表達且更精煉**
   atoms 僅四項（約 50 字），⛔ 不含 answer 中的欄位清單、發票導引等細節
   ⇒ 同時避免「full answer 稀釋 intent」

❌ **B1 家族（5 筆）不被此契約解決**
   #23「後台哪裡可以匯出收據」——**匯出≈下載**是同義推廣
   #166「滯納金」≈逾期費／延遲金
   #146「跳錯誤」≈取消不了
   #42／#50 缺「點退」錨詞
   ⚠️ 這些 query 的語義**已在** representation 內，失敗在**模型的泛化**，
      ⛔ 不是 representation 缺失 ⇒ 契約再完整也救不了
```

### ⚠️ 因此可預估的作用範圍（⛔ 非承諾）

```text
R3b 23 筆中，representation contract **有機會**涵蓋：
  B2 ×3 ＋ anchors ×4 ＝ **7**
  ＋ 3406 的 surface 問題（rescued 6 已證可由 surface 解釋）
⛔ **不涵蓋** B1 ×5
⛔ B3 ×2 需另行的 model discrimination test
⇒ ⛔ 不得宣稱「建立 contract 即可修好 A03-SEMANTIC」
```

## 待業主裁的三個 decision（⛔ 本檔不裁）

```text
D1  是否建立獨立的 retrieval semantic contract？
D2  embedding 與 reranker 是否必須消費同一份 contract？
    或允許不同 surface 但必須明示且各自驗證？
D3  legacy question_summary／keywords／answer 如何 migration？
    ⛔ 不靠自動拼接直接取得 authority
```

## 候選目標形態（⛔ 未批准）

```text
Knowledge semantic responsibility
        ↓ reviewed
retrieval_representation  ──→ embedding ＋ reranker 共用
question_summary  → 回到**人類簡短題意**
answer            → 回到**回答／grounding**
keywords          → 是否保留為召回輔助另行決定，
                    ⛔ 不再偷偷承擔缺失的 semantic contract
```

## 狀態

```text
representation contract gap   CONFIRMED as structural（R8）
design options                **已比較，⛔ 未裁**
migration simulation          **完成**：3406 型與 4656 型皆可由同一契約表達，
                              ⛔ 但 B1 家族不被涵蓋
candidate invariant           仍**不落地**
⛔ 未實作、未寫 DB、未改 scoring
⏸ gate authorization／3.4／gate enable／scope expansion／release 全部 PAUSED
```
