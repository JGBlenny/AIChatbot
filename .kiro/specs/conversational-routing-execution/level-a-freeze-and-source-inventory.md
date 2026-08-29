# ① Level-A population freeze ② implementation freeze ③ 來源資格盤點

日期：2026-08-29

---

## ① Level-A population — **FROZEN**

```text
scope                bill_diagnosis（LEVEL_A_INSTANCE_GATE_SCOPE）
knowledge rows       10
  instance 7   （4 deterministic ＋ 3 reviewed_product_declaration）
  general  3   （reviewed_product_declaration）
  UNKNOWN  0
population digest    57413ee8a4068f73bc4e0c2c0512967e
  （md5 of `id:value:provenance_source` 依 id 排序）
```

不變量 10 已鎖：提名 Level-A Face 的知識未明示 → FAIL，**無 legacy 豁免**。

## ② Implementation — **FROZEN**

```text
implementation SHA        c35b2e46c9b58350d6dcfa1625d7be9b16d2f40c
face requirement digest   bde00b206c9c8b7d4b1328e7440d754f
  （23 個 Face 的 key:requires_instance_reference）
gate                      **OFF**（INSTANCE_REFERENCE_GATE 未設）
LEVEL_A_INSTANCE_GATE_SCOPE  {bill_diagnosis}（未變）
routing 行為               與 P1a 之前逐位元相同（已有 equivalence 測試）
```

---

## ③ 來源資格盤點（**只看 provenance／可抽樣性，⛔ 未閱讀任何候選問句**）

| Source | 真實 | 已看過 | 曾參與 KB／classifier／routing 設計 | 有 user utterance | 可機械抽樣 | 量 | 資格 |
|---|---|---|---|---|---|---:|---|
| D1／D2／D3 語料 | 部分 | ✅ | ✅ | 部分 | — | 100+80 | **BURNED** |
| `pages-v2-released-for-kb` | 真實衍生 | 已釋出 | ✅ 指定為知識工程語料 | 有 | 有 | 1571 | **污染，不合格** |
| `assistant-reports`（S3） | 真實 | ✅ | ✅ KB engineering | 有 | 有 | — | **diagnostic only** |
| `chat_history` / `conversation_logs` | — | — | — | — | — | **0** | **本機為空** |
| `usage_events` | 真實 | — | — | **無原文**（僅 `message_len`） | — | 6010 | **不含 utterance** |
| **sealed pool 剩餘** | **真實** | **否** | **禁止** | **有** | **有** | **456** | **候選合格** |

### 唯一候選：sealed pool 的剩餘 456 句

```text
來源       JGB_口語化問法_v2.pages（衍生自真實客服逐字稿）
抽取規則   長度＋疑問句型的結構性規則 ＋ sha256 hash 分區
           ⛔ **不含任何依內容挑選的判斷**——這是該池可信的唯一理由
池 n       576（宣告值與檔內實際列數一致）
已消耗     120 ＝ D2 80 ＋ D3 40，皆依**預先登記的 sha256 升冪**取用
剩餘       **456**，明文「保留供未來輪次，本輪不得動用」
互斥       與 released 1571 為同一 hash 分區的補集，交集 0（原始驗證）
```

### ⚠️ 非污染**無法以文字比對證明**——兩把尺都是瞎的

```text
尺 1  完全相同比對      released 正對照 0/1571 → 失效
尺 2  KB 主題詞子字串   released 正對照 0/1571 → 失效
原因  KB `question_summary` 有 884/923 筆長度僅 2–19 字（短複合關鍵字），
      ⛔ 不會逐字出現在自然問句中 ⇒ 文字重疊在此**結構上測不到**
⇒ 依否定結論紀律，**不得宣稱「已驗證未污染」**。
```

### 可用的替代證據＝**process provenance**

```text
✅ 檔案 `holdout-2026Q3-D2-sealed-pool.json` 自建立起 **commit 次數 = 1**，從未被修改
✅ 協議明文禁令：「本池在 D2 授權執行前，禁止進入 KB／prompt／classifier 調整；
   亦不得用於挑題」
✅ 知識工程另有指定語料（released 1571），職責分離
⚠️ `pool_digest=1b85edb1d7e58b95` 的**計算方式未記載**，本地無法重算比對
   ⇒ 完整性靠 git 不可變性，⛔ 不靠 digest 覆核
```

---

## ⚠️ 尚未解決的風險：matching support 未知

```text
形式乾淨 ≠ 可授權。若 456 句中根本沒有「帳單診斷／查值」這一帶，
會得到一個乾淨但**無法授權**的 holdout（第四次浪費）。

⛔ 不得用「讀完句子再挑」來確認——那會讓我成為 source selector。
✅ 合法作法：把它寫成**預先登記的 coverage precondition**，
   在 protocol 凍結**之後**才量：
     對 456 句跑 production retrieval，
     計 top1 落在 Level-A 那 10 筆之內的句數 n_match
     n_match < 預先登記門檻 → 整輪 INCONCLUSIVE，⛔ 不得改抽樣規則救它
```

## 下一步

```text
5. freeze authorization protocol（source／sampling／labels／coverage precondition／
   PASS-FAIL-INCONCLUSIVE 判準）  ← 尚未做
6. 才抽樣
7. truth preparation
8. 第一次 authorization execution
⏸ 3.4 持續 PAUSED，直到新的 authorization 真正 PASS
```
