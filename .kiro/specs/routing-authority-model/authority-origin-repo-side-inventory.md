# Authority-Origin：repo-side governance-artifact inventory

> 2026-08-24｜語言 zh-TW｜依 `responsibility-truth-source-qualification-frozen.md`（O1–O6，凍結於 `aa3a4b2`）執行
> 唯讀。**任務刻意窄化：找 governance artifacts，不推 governance reality。**
> ⚠️ 本檔**不判定** A／B／C 結局——依已凍結的結構性限制，判定需要 repo 外事實。

## 判定原則（逐條遵守）

```text
✅ 可寫：not evidenced in audited repo surface
❌ 不得寫：does not exist organizationally
❌ `git blame = 某工程師` **絕不得**讀成「該工程師是 authority owner」
```

---

## 三分類彙整

```text
GOVERNANCE_ARTIFACT          2 項（皆有實質限制，見下）
IMPLEMENTATION_PROVENANCE    3 項
UNATTRIBUTED_PRODUCT_SEMANTICS  2 項
```

---

## GOVERNANCE_ARTIFACT（具責任裁決／版本／審批性質的產物）

### GA-1｜`knowledge_review_queue`：**唯一具 approver 身分的機器化審批痕跡**

```text
source   database/backups/backup_20260620_211102_pre_optionrouting.sql:3534-3559
欄位     status（預設 pending_review）／reviewed_by／reviewed_at／review_notes
         ＋ edited_question_summary／edited_answer／edit_summary（可追溯編輯前後）
```

**這是本次查核中唯一一個把「誰審、何時審、審了什麼」寫成欄位的產物。**

⚠️ 但**兩個限制使它目前無法承擔 responsibility governance**：

```text
限制一｜**沒有面向／責任欄位**
  該表的語義欄位為 recommended_intent_ids／business_types／target_user／keywords，
  **未見** category／facet／responsibility 欄位
  → 即使經過此佇列，被審的也**不是**「這筆屬於哪個 Face 的責任」

限制二｜**責任承載路徑不經過它**
  rag-orchestrator/tools/import_facet_knowledge.py 直接
  `INSERT INTO knowledge_base (question_summary, answer, categories, target_user, ...)`（:73,:92）
  與 `UPDATE knowledge_base SET answer=..., updated_by='import_script'`（:57）
  → **繞過** knowledge_review_queue
  → 而 `categories` 正是面向責任的承載欄位之一
```

> **合併判讀**：機器化審批**存在其形**，但**不覆蓋責任**，且**責任的實際寫入路徑不經過它**。
> ⚠️ 這與本線既有教訓同型：**gate exists ≠ gate covers the thing**。

### GA-2｜kiro spec 的 `approvals` 記錄 ＋ 人工確認清單

```text
source   .kiro/specs/*/spec.json 的 approvals{requirements/design/tasks:{generated,approved}}
         17 個 spec 皆有此結構；例：billing-conversational-facets 三階段皆 approved=true
         （created_at 2026-07-03T01:30Z／updated_at 03:20Z）
         ＋ .kiro/specs/billing-conversational-facets/facet-backfill-review.md
           「帳務知識面向補標——人工確認清單（任務 5.2）」
           狀態自陳：**已確認並套用（2026-07-03，本機 dev DB）**；prod 另以 SQL 套用
           內含**明文準則**（一筆一主面向互斥／模糊起手需 ground → 掛面向／教學制度 → 單發／
           form_fill 混合制）＋**逐筆理由**（19 筆提議補標）
```

**這是最接近「責任裁決產物」的東西**：它對每一筆知識指派主面向、給出準則與逐筆理由、有日期、有狀態。

⚠️ 但**三個限制**：

```text
① **無 approver 身分**：只寫「已確認」，未記錄**由誰**確認
② **approvals 只有布林**：spec.json 的 approved=true **沒有** approver、no approval timestamp
   （僅有檔案層級的 created_at／updated_at）
③ 對象是**知識列的面向歸屬**，不是 **Face 對情境的責任定義**本身
   —— 兩者相鄰但不同層（前者是把既有知識掛到既有 Face）
```

---

## IMPLEMENTATION_PROVENANCE（只證明誰把東西寫進系統）

### IP-1｜knowledge batch 的 `_meta`：**內容來源**可追溯，**決策權**不可

```text
source   scripts/knowledge-batches/*.json 的 `_meta`
欄位     spec（產出自哪個 spec 的哪個任務）／produced_at／sources
例       billing-knowledge-batch.json：
         spec="billing-conversational-facets 任務 5.3/5.4"｜date=2026-07-03
         sources="Excel 官方回覆（row18/21/27/34/36/37）＋research §一–§四 jgb2 真碼＋help 42 篇"
```

⚠️ `sources` 追溯的是**內容依據**（jgb2 file:line、官方回覆、help 中心、客服案例），
**不是**「誰有權決定責任歸屬」。依 O1，這是 descriptive provenance，非 normative legitimacy。

### IP-2｜`knowledge_base` 的 `created_by`／`updated_by`

```text
source   同 backup:2729-2730（created_by／updated_by varchar(100)）
實況     批次匯入寫入的值為字串 `'import_script'`（import_facet_knowledge.py:57）
```

⚠️ 這記錄的是**寫入者**（甚至只是腳本名），不是**核可者**。

### IP-3｜git authorship

```text
`.kiro/specs/billing-conversational-facets/` 與 `scripts/knowledge-batches/` 的 commit 作者：
  lenny（2 筆）
```

⚠️ **依本輪判定原則，這一項不得作任何 authority 推論。**
commit 作者可能是決策者、可能是代為實作者、也可能兩者皆是——**repo 無法區分**。

---

## UNATTRIBUTED_PRODUCT_SEMANTICS（有責任語句，但找不到 authority origin 痕跡）

### UP-1｜面向設定列（`category='對話規則'`）：**新增／修改無任何審批欄位或流程**

```text
source   rag-orchestrator/routers/conversational_configs.py
         POST /api/v1/conversational-configs（upsert_config，:75-76）
         DELETE /api/v1/conversational-configs/{config_id}（:114-115）
掃查     全檔 grep `approv|review|owner|audit` → **零命中**
```

⚠️ 即：**新增一個面向或改動其設定，在 repo 內查不到任何 admission process 的痕跡**
（與 G1 的既有發現一致：面向由後台資料列定義、零改程式）。
⚠️ 依 O5，這是「新增 DB row 即取得權力」的形態；但**是否存在 repo 外的核可流程，repo 無法回答**。

### UP-2｜Face responsibility 散文（seed RULES／handles／does_not_handle）

```text
承載     knowledge_base 的 `answer`（對話規則列）與各 Face 的 seed RULES 文本
掃查     未見版本欄、未見 owner／approver 欄、未見變更理由欄
         （knowledge_base 有 source_type／source_file／source_date／generation_metadata，
           但那是**內容來源**欄，非責任裁決欄）
```

⚠️ 依 O3，散文式責任語句**需要人事後解讀**才知道邊界——
這與 D3-member-1 的 F2 失敗（枚舉缺口）是同一份素材的兩種症狀。

---

## repo 能收斂到的上限（**不越界**）

```text
✅ repo 內**存在**責任裁決的**產物**：facet-backfill-review.md（準則＋逐筆理由＋狀態）
   ＋ spec 三階段 approvals 布林 ＋ 一張具 reviewed_by 的審批表
✅ repo 內**未見**：責任本身的 versioned specification、責任變更的 approver 記錄、
   新增／修改 Face 前的 executable 或 documented gate
✅ repo 內**可證**：面向責任的實際寫入路徑（批次匯入、config API）
   **不經過**唯一具 approver 欄位的審批表
```

> **repo-side 收斂結果**：
> **不是**結局 A（未見 first-class、versioned、可 enrollment 的 normative authority）。
> **repo 無法單獨區分 B 與 C**——
> `facet-backfill-review.md` 這類產物**證明有人在做責任裁決**（傾向 B 的證據），
> 但「已確認」的**主體是誰、其裁決權從何而來**，repo 無記錄。

⚠️ **不得**因為 repo 查不到 approver 就寫成「沒有 responsibility owner」（結局 C）——
那正是本輪事前禁止的 `not evidenced` → `does not exist` 誤報。

---

## 逐條 O1–O6 的 repo-side 觀察（**非最終 disposition**）

| | 條件 | repo-side 觀察 | 缺口（需 repo 外事實） |
|---|---|---|---|
| **O1** | Normative legitimacy | 現有可查者（B1／B2／B3、seed prose）皆為**描述現況**；未見自稱「產品責任裁決」的正式載體 | 是否存在 repo 外的正式產品裁決 |
| **O2** | Independence from candidate | UP-1：面向可經 config API 自行新增／修改，repo 內無外部核可 | 是否存在 repo 外的核可者 |
| **O3** | Explicit responsibility semantics | UP-2：責任以散文承載，需人解讀；GA-2 有明文準則但對象是知識掛載 | — |
| **O4** | Versionability | 未見責任的版本欄／變更記錄；spec approvals 僅布林、無 approver 與時戳 | 變更是否另有 repo 外記錄 |
| **O5** | Enrollment authority | UP-1：repo 內未見 admission process | 新增 Face 是否需 repo 外裁決 |
| **O6** | Executable handoff | GA-1 存在機器化審批**形式**，但不覆蓋責任且被繞過；批次匯入是**單向**產物（決策→資料），無回溯綁定 | — |

---

## 下一階段要問的具體問題（**填 repo 無法觀測的缺口**）

```text
Q1 這些 Face 的 responsibility 最初是誰決定的？
Q2 修改 responsibility 時，誰有最終否決權？
Q3 工程師能不能自行改，還是必須取得某角色同意？
Q4 新增 Face 是否需要正式產品裁決？
Q5 這些 seed RULES 是產品規格的正式載體，還是把口頭／會議決策實作進去的結果？
Q6 有沒有 repo 外的 approval source：ticket ／ Slack ／ 文件 ／ meeting decision？
```

⚠️ 特別對應：`facet-backfill-review.md` 自陳「**已確認**並套用」——
**由誰確認**是判定 O1／O2／O5 的關鍵，且 repo 內無此記錄。

## 本輪**未**做

```text
❌ 未判定結局 A／B／C（依凍結的結構性限制，需 repo 外事實）
❌ 未由 git 作者推論 authority owner
❌ 未設計 governance 流程、未新增 R7、未復活任何 carrier
❌ 未改已凍結的 Contract／ruler／R6／O1–O6
❌ 未動 production；未產測資；ruler 0.058928 仍凍結未用
```
