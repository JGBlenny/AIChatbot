# Production corpus 最小採集契約（**設計，尚未實作**）

- 日期：2026-08-29｜依據：業主裁定「A 降為 hypothesis-only，B 才作 architecture validation；
  先凍結 collection contract，再寫任何 logger」
- 目的：回答 **nomination architecture coverage**——
  「當需求確實需要個別資料／API capability 時，retrieval + category nomination
  能不能把它送到適當的 responsibility candidate？」

## 〇、先講一件會改變成本估算的事

**既有 `usage_events` 已經覆蓋你列的大部分欄位**（實查 schema）：

```text
已有  request_id｜ts／date_tpe｜session_id｜role_id／mode／user_type／target_user／vendor_id
      processing_path｜answer_source｜facet_key｜turn_number｜decision_case
      knowledge_score／sop_score｜message_len（長度，**不含原文**）
      decision_snapshot: kb_top1_final｜kb_threshold｜resolver（含 hops／candidate_facet）
                         facet_entry｜path｜config_hash｜prior｜has_sop｜incomplete
```

⇒ 真正缺的只有三類，而且**只有一類碰隱私**：

| 缺口 | 隱私敏感 | 用途 |
|---|---|---|
| retrieval `top1_knowledge_id` ＋ `top1_categories` | ❌ 否（KB 列 id 與分類標籤） | 判 nomination 為何沒產生候選 |
| `nomination_candidate_facet_keys`（提名時的完整候選集） | ❌ 否 | 現有 `facet_key` 只有**已 commit** 的那個 |
| **`user_utterance`（原句）** | ✅ **是** | Layer 0 capability 盲標唯一必需 |

## 一、分兩階段——第一階段不需要任何隱私決定

```text
Stage 1（無 PII，可立即設計實作）
  加 top1_knowledge_id／top1_categories／nomination_candidate_facet_keys
  → 立刻可量：有多少 request 完全沒有 Face candidate？
              沒有候選時 top1 是什麼、分數多少、掛哪些 categories？
              候選存在但 resolver 不 commit 的比例？
  ⚠️ 但**無法**判斷「這個需求本來就該進面向嗎」——那需要讀原句。

Stage 2（需隱私裁定）
  加 user_utterance
  → 才能做 Layer 0 capability 盲標（需要通用知識／個別資料／API grounding／追問／操作）
```

⇒ **建議先做 Stage 1**：它能把「nomination 到底在哪一步斷掉」的分布量出來，
而那正是目前只有兩句軼事證據（文山路／3樓電表）的地方。

## 二、⚠️ Stage 2 會**推翻**一個既有的凍結決定

```text
usage-metering R7：**不存原文**（`message_len` 只記長度）——這是刻意的隱私設計，
                   不是疏漏。design.md 的 UsageContext 明寫 `message_len: int = 0  # 不存原文`
⇒ 加 user_utterance ＝ 反轉該決定，必須以同等份量的裁定推翻，
  ⛔ 不得以「audit 需要」為由默默加欄位。
```

## 三、Stage 2 的隱私契約（**凍結後才准寫入**）

以下每一格都必須有明確答案，缺一格即不得實作：

```text
① 誰可讀        ____________________（DB 直讀？後台？限特定角色？）
② 保存多久      ____________________（建議 ≤ 現行 USAGE_RETENTION_MONTHS）
③ 是否加密      ____________________（欄位級加密／僅傳輸加密／不加密）
④ redact 規則   使用者原句中已知會出現的識別資訊：
                  合約編號／帳單編號／物件地址／人名／電話／email
                ⚠️ 但 architecture audit **需要保留自然語言**，
                  不能只存 feature vector ⇒ redact 必須是
                  **token 替換而非刪除**（如「合約 89557」→「合約 <ID>」），
                  否則「這句有沒有提供足夠識別資訊」這個 Layer 0 問題就答不了
⑤ session 去識別 ____________________（現行 session_id 是原值；建議 hash＋salt）
⑥ 明確禁收      ____________________（建議：assistant 回答全文、API payload、
                                        合約／帳單內容、任何附件）
⑦ 取樣率        ____________________（全量？或每 N 筆抽一？降低暴露面）
⑧ 撤回機制      ____________________（既有被遺忘權 UPDATE 是否涵蓋本欄）
```

⚠️ **④ 是設計上最微妙的一格**：redact 太狠 → Layer 0 標不了；
太鬆 → 存了個資。token 替換是唯一同時滿足兩者的形式。

## 四、Layer 0 盲標協定（**不得用 single/dialog 當 oracle**）

新 corpus 收到後，第一層標的是 capability truth，
⛔ 完全不提 `Face`／`single`／`dialog`／`category`／`0.75`／`gate`／`resolver`：

```text
需要通用知識？｜需要個別資料？｜需要 API grounding？
目前資訊是否已足夠？｜是否需要追問？｜需要執行操作？
```

然後才把 production routing 疊上去比對：

```text
需要 API／個別資料的 cases
  → retrieval 有沒有候選？
  → nomination 有沒有 candidate？
  → candidate capability 是否匹配？
  → responsibility 最後怎麼裁？
```

## 五、A（assistant-reports）的身分

```text
✅ 可用於：failure pattern／hypothesis generation／找 nomination 可能缺在哪
⛔ 不可用於：nomination coverage acceptance／production distribution claim
   理由：37 份已全量重播、其中 30 份做過知識工程 ⇒ 拿它驗 nomination
        等於用自己調過的 KB 驗自己
```

## 六、主線狀態（本裁定後）

```text
H6 numeric-id audit          ✅ CLOSED — redundancy hypothesis REFUTED
11.5 required_slots[0]       ✅ CONFIRMED（grounding prerequisite，非固定追問題目）
11.5 multi-slot／repair_create ⚠️ PARTIALLY CONFIRMED — 5 槽尚未逐 consumer 比對
instance gate authorization   ⏸️ PAUSED
3.4                           ⏸️ PAUSED
下一個上游問題                nomination architecture coverage
                              → 需新的、未污染 production corpus
```

⚠️ 「文山路那間」「3樓的電表」是**存在性證據**，
⛔ 兩句不得用來估 coverage rate。
