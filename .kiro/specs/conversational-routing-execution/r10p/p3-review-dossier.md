# R10-P3 逐群待裁清單（47 群／54 列）

> **Prime directive：Proposal is allowed to reduce search cost, never to establish responsibility truth.**

```text
來源      r10p/proposal.json（PROPOSAL_DIGEST=fe6e5f3feba9b26f…，P2_PROPOSAL_FROZEN）
判準      R10P-SCHEMA-2（SCHEMA_DIGEST=b72e749e0c452f0d…）
母體      POPULATION 51c04b887a16b05f…／IDSET 00581c42771fa3b0…
本檔性質  frozen proposal ＋ DB 既有 reviewed 事實的**投影**；⛔ 本檔不裁定、不合併、不拆分、不填 authority
```

## 讀法（四條規約）

```text
① candidate_group_id 是**機械 id**（CG-ALIAS-nn ／ CG-ROW-<row_id>），⛔ 不是 responsibility_id。
   canonical responsibility_id 等 CONFIRMED_RESPONSIBILITY 之後才命名。
② `SINGLETON_NO_ALLOWED_RULE_APPLIES` 只代表 **P2 找不到合法的機械 grouping evidence**，
   ⛔ 不代表該列已被證明是一個獨立 responsibility。P3 完全可以收成 INSUFFICIENT_EVIDENCE 或 MERGE_WITH_OTHER。
③ 標 **HINT_ONLY** 的一律不得作為裁定依據，只能用來縮小搜尋範圍。
④ IDENTITY CONFIRMED ⛔ 不自動推出 APPLICABILITY 或 OWNERSHIP 已確認——後兩者必須各自引用獨立證據。
```

## 排序＝固定機械順序（⛔ 非重要性排序）

```text
Batch A  五個 ENTRY_ALIAS groups
Batch B  LEVEL_A_V2 涉及的 singleton
Batch C  其餘已有 applicability declaration 的 singleton
Batch D  historical retired
Batch E  其餘
每層內按 candidate_group_id（＝最小 row id）排序。
⚠️ 分批只影響 review 節奏，⛔ 不改 P0／P1／P2；⛔ 不得回頭重生 proposal。
   前一批揭露的 taxonomy 問題只能當**後續 group 的 P3 evidence**。
```

```text
Batch A   5 群 ／ 12 列
Batch B   9 群 ／  9 列
Batch C  32 群 ／ 32 列
Batch D   1 群 ／  1 列
Batch E   0 群 ／  0 列
合計      47 群 ／ 54 列
```

---

# Batch A —— ENTRY_ALIAS groups（5 群／12 列）

最完整的 authoring provenance（batch schema ＋ review 明文），適合作 P3 ruler calibration。

---

## `CG-ALIAS-01`

### proposal_basis
```text
ENTRY_ALIAS_REGISTRY
registry facet = 繳費金流排障（entry-alias-registry.json 明文裁定：responsibility_owner=facet）
```

### members
```text
row_id            3931
state             active
role              ENTRY_ALIAS（registry 明文）
summary           租客說繳了 錢還沒進來
categories        繳費金流排障
facet             繳費金流排障
answer            **空**
action / form     direct_answer ／ —
applicability     **undeclared**（⛔ 不得序列化成 unknown）
representation    NONE（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）
```
```text
row_id            3932
state             active
role              ENTRY_ALIAS（registry 明文）
summary           帳單卡在待對帳 狀態一直沒跳
categories        繳費金流排障
facet             繳費金流排障
answer            **空**
action / form     direct_answer ／ —
applicability     **undeclared**（⛔ 不得序列化成 unknown）
representation    NONE（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）
```
```text
row_id            3933
state             active
role              ENTRY_ALIAS（registry 明文）
summary           租客繳不了費 一直失敗
categories        繳費金流排障
facet             繳費金流排障
answer            **空**
action / form     direct_answer ／ —
applicability     **undeclared**（⛔ 不得序列化成 unknown）
representation    NONE（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）
```

### existing authority evidence
```text
AUTHORING_SPEC              billing-conversational-facets/billing-knowledge-review.md
                            「錨點（12 筆，answer 空、一種講法一筆）」
AUTHORING_SPEC              billing-conversational-facets/billing-knowledge-batch.json
                            anchors 每筆僅 facet／question／keywords ⇒ 唯一語義負載是 facet
PROVENANCE_HISTORY          entry-alias-registry.json（T3 裁定 KEEP_BOTH_AS_ENTRY_VARIANTS）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same categories  「繳費金流排障」⇒ [3361, 3366, 3931, 3932, 3933]
```

### conflicts / tensions
```text
群內有列**完全未宣告** applicability ⇒ 群層 applicability ⛔ 無法由現有證據導出
3931：representation 未寫（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）⇒ 不變量 16 TRANSITIONAL_GUARD 仍在生效
```

### evidence gaps
```text
identity       registry 明文支持「同 facet 的不同講法」，⚠️ 但 facet **⛔ 不等同** responsibility（R10-Q1 已證同一 facet 內可有多個責任）
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  缺：正面裁定（undeclared ⇒ 不得填 unknown）
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ALIAS-02`

### proposal_basis
```text
ENTRY_ALIAS_REGISTRY
registry facet = 帳單異常（entry-alias-registry.json 明文裁定：responsibility_owner=facet）
```

### members
```text
row_id            3934
state             active
role              ENTRY_ALIAS（registry 明文）
summary           帳單金額怪怪的 跟預期不一樣
categories        帳單異常
facet             帳單異常
answer            **空**
action / form     direct_answer ／ —
applicability     **undeclared**（⛔ 不得序列化成 unknown）
representation    NONE（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）
```
```text
row_id            3935
state             active
role              ENTRY_ALIAS（registry 明文）
summary           這期帳單怎麼還沒出來
categories        帳單異常
facet             帳單異常
answer            **空**
action / form     direct_answer ／ —
applicability     **undeclared**（⛔ 不得序列化成 unknown）
representation    NONE（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）
```
```text
row_id            3936
state             active
role              ENTRY_ALIAS（registry 明文）
summary           租客說看不到帳單 找不到
categories        帳單異常
facet             帳單異常
answer            **空**
action / form     direct_answer ／ —
applicability     **undeclared**（⛔ 不得序列化成 unknown）
representation    NONE（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）
```

### existing authority evidence
```text
AUTHORING_SPEC              billing-conversational-facets/billing-knowledge-review.md
                            「錨點（12 筆，answer 空、一種講法一筆）」
AUTHORING_SPEC              billing-conversational-facets/billing-knowledge-batch.json
                            anchors 每筆僅 facet／question／keywords ⇒ 唯一語義負載是 facet
PROVENANCE_HISTORY          entry-alias-registry.json（T3 裁定 KEEP_BOTH_AS_ENTRY_VARIANTS）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
（無）
```

### conflicts / tensions
```text
群內有列**完全未宣告** applicability ⇒ 群層 applicability ⛔ 無法由現有證據導出
3934：representation 未寫（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）⇒ 不變量 16 TRANSITIONAL_GUARD 仍在生效
```

### evidence gaps
```text
identity       registry 明文支持「同 facet 的不同講法」，⚠️ 但 facet **⛔ 不等同** responsibility（R10-Q1 已證同一 facet 內可有多個責任）
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  缺：正面裁定（undeclared ⇒ 不得填 unknown）
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ALIAS-03`

### proposal_basis
```text
ENTRY_ALIAS_REGISTRY
registry facet = 發票（entry-alias-registry.json 明文裁定：responsibility_owner=facet）
```

### members
```text
row_id            3937
state             active
role              ENTRY_ALIAS（registry 明文）
summary           發票怎麼還沒開 沒收到發票
categories        發票
facet             發票
answer            **空**
action / form     direct_answer ／ —
applicability     **undeclared**（⛔ 不得序列化成 unknown）
representation    NONE（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）
```
```text
row_id            3938
state             active
role              ENTRY_ALIAS（registry 明文）
summary           發票開錯了 要作廢重開
categories        發票
facet             發票
answer            **空**
action / form     direct_answer ／ —
applicability     **undeclared**（⛔ 不得序列化成 unknown）
representation    NONE（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）
```

### existing authority evidence
```text
AUTHORING_SPEC              billing-conversational-facets/billing-knowledge-review.md
                            「錨點（12 筆，answer 空、一種講法一筆）」
AUTHORING_SPEC              billing-conversational-facets/billing-knowledge-batch.json
                            anchors 每筆僅 facet／question／keywords ⇒ 唯一語義負載是 facet
PROVENANCE_HISTORY          entry-alias-registry.json（T3 裁定 KEEP_BOTH_AS_ENTRY_VARIANTS）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same categories  「發票」⇒ [3362, 3937, 3938]
```

### conflicts / tensions
```text
群內有列**完全未宣告** applicability ⇒ 群層 applicability ⛔ 無法由現有證據導出
3937：representation 未寫（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）⇒ 不變量 16 TRANSITIONAL_GUARD 仍在生效
```

### evidence gaps
```text
identity       registry 明文支持「同 facet 的不同講法」，⚠️ 但 facet **⛔ 不等同** responsibility（R10-Q1 已證同一 facet 內可有多個責任）
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  缺：正面裁定（undeclared ⇒ 不得填 unknown）
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ALIAS-04`

### proposal_basis
```text
ENTRY_ALIAS_REGISTRY
registry facet = 滯納金（entry-alias-registry.json 明文裁定：responsibility_owner=facet）
```

### members
```text
row_id            3939
state             active
role              ENTRY_ALIAS（registry 明文）
summary           滯納金怎麼收這麼多
categories        滯納金
facet             滯納金
answer            **空**
action / form     direct_answer ／ —
applicability     instance（row-level legacy declaration）
  provenance      source=reviewed_product_declaration｜ruling=滯納金域 applicability 補齊 2026-08-29（T1/T2 aftermath）｜recorded=2026-08-29
  scope           late_fee face（⛔ 不在 LEVEL_A_V2 內）
  reason          empty-answer entry anchor，責任由唯一 owner 的 late_fee face／build_late_fee_facts 決定。該能力提供的是某一筆的實際金額、實際狀態、合約設定實值、實際結算備註與付款／到帳時間——沒有特定 referent 就無法完成 intent。
representation    NONE（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）
```
```text
row_id            3940
state             active
role              ENTRY_ALIAS（registry 明文）
summary           這筆延遲金是怎麼算的
categories        滯納金
facet             滯納金
answer            **空**
action / form     direct_answer ／ —
applicability     instance（row-level legacy declaration）
  provenance      source=reviewed_product_declaration｜ruling=滯納金域 applicability 補齊 2026-08-29（T1/T2 aftermath）｜recorded=2026-08-29
  scope           late_fee face（⛔ 不在 LEVEL_A_V2 內）
  reason          empty-answer entry anchor，同上：由 build_late_fee_facts 以該筆的存值與結算備註作答。「這筆怎麼算的」必須讀該筆實際資料。
representation    NONE（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）
```

### existing authority evidence
```text
AUTHORING_SPEC              billing-conversational-facets/billing-knowledge-review.md
                            「錨點（12 筆，answer 空、一種講法一筆）」
AUTHORING_SPEC              billing-conversational-facets/billing-knowledge-batch.json
                            anchors 每筆僅 facet／question／keywords ⇒ 唯一語義負載是 facet
PROVENANCE_HISTORY          entry-alias-registry.json（T3 裁定 KEEP_BOTH_AS_ENTRY_VARIANTS）
POSITIVE_APPLICABILITY_DECLARATION  3939：instance（滯納金域 applicability 補齊 2026-08-29（T1/T2 aftermath））
POSITIVE_APPLICABILITY_DECLARATION  3940：instance（滯納金域 applicability 補齊 2026-08-29（T1/T2 aftermath））
RUNTIME_CAUSAL_EVIDENCE     T1／Step 2：late-fee instance ownership 收斂至唯一 owner
                            （B_CAPABILITY_SUPERSET=CONFIRMED；不變量 14 守住）
RUNTIME_CAUSAL_EVIDENCE     T2 mutation：3498 改回 active 後在 3 個 late-fee 查詢中
                            2 個回到 rank 1，與 3939/3940 搶排序
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same scope       late_fee face（⛔ 不在 LEVEL_A_V2 內） ⇒ [3531, 3532, 3939, 3940]
HINT_ONLY  content relation 3531／3532（general late-fee mechanism，T2 K1 承接 3498）與本群 categories 同為「滯納金」
```

### conflicts / tensions
```text
⚠️ facet 內責任分歧（R10-Q1 淘汰 B 的原始理由）：categories=滯納金 底下同時存在
   general（3531／3532）與 instance（3939／3940）兩種 authority semantics
3939：representation 未寫（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）⇒ 不變量 16 TRANSITIONAL_GUARD 仍在生效
```

### evidence gaps
```text
identity       registry 明文支持「同 facet 的不同講法」，⚠️ 但 facet **⛔ 不等同** responsibility（R10-Q1 已證同一 facet 內可有多個責任）
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ALIAS-05`

### proposal_basis
```text
ENTRY_ALIAS_REGISTRY
registry facet = 帳單設定引導（entry-alias-registry.json 明文裁定：responsibility_owner=facet）
```

### members
```text
row_id            3941
state             active
role              ENTRY_ALIAS（registry 明文）
summary           要開始收租 帳單要怎麼設定
categories        帳單設定引導
facet             帳單設定引導
answer            **空**
action / form     direct_answer ／ —
applicability     **undeclared**（⛔ 不得序列化成 unknown）
representation    NONE（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）
```
```text
row_id            3942
state             active
role              ENTRY_ALIAS（registry 明文）
summary           收款帳戶怎麼綁 金流怎麼申請
categories        帳單設定引導
facet             帳單設定引導
answer            **空**
action / form     direct_answer ／ —
applicability     **undeclared**（⛔ 不得序列化成 unknown）
representation    NONE（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）
```

### existing authority evidence
```text
AUTHORING_SPEC              billing-conversational-facets/billing-knowledge-review.md
                            「錨點（12 筆，answer 空、一種講法一筆）」
AUTHORING_SPEC              billing-conversational-facets/billing-knowledge-batch.json
                            anchors 每筆僅 facet／question／keywords ⇒ 唯一語義負載是 facet
PROVENANCE_HISTORY          entry-alias-registry.json（T3 裁定 KEEP_BOTH_AS_ENTRY_VARIANTS）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
（無）
```

### conflicts / tensions
```text
群內有列**完全未宣告** applicability ⇒ 群層 applicability ⛔ 無法由現有證據導出
3941：representation 未寫（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）⇒ 不變量 16 TRANSITIONAL_GUARD 仍在生效
```

### evidence gaps
```text
identity       registry 明文支持「同 facet 的不同講法」，⚠️ 但 facet **⛔ 不等同** responsibility（R10-Q1 已證同一 facet 內可有多個責任）
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  缺：正面裁定（undeclared ⇒ 不得填 unknown）
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

# Batch B —— LEVEL_A_V2 相關 singleton（9 群／9 列）

⚠️ 這 9 列同時是 LEVEL_A_V2 的 active routing scope，且**全數**已有 reviewed retrieval_representation。

---

## `CG-ROW-3402`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3402
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           點退帳單 自動產生 費用結算
categories        帳單管理,條件診斷：帳單
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     direct_answer ／ —
applicability     general（row-level legacy declaration）
  provenance      source=reviewed_product_declaration｜ruling=Level-A truth 逐筆裁定 2026-08-29｜recorded=2026-08-29
  scope           bill_diagnosis (LEVEL_A_INSTANCE_GATE_SCOPE)
  reason          問的是系統流程與產生機制（是否自動產生、如何結算）；正確回答不需要知道使用者是哪份合約或哪張帳單。無成對 anchor，但產品命題本身正向成立：答案取決於系統規則，不取決於當下哪張帳單的實值。
representation    點退完成後系統何時／在什麼條件下自動產生點退帳單，以及該帳單如何進入費用結算。
  provenance      source=reviewed_product_declaration｜ruling=R9 Level-A representation 逐筆裁定 2026-08-29
```

### existing authority evidence
```text
POSITIVE_APPLICABILITY_DECLARATION  3402：general（Level-A truth 逐筆裁定 2026-08-29）
CONTENT_RESPONSIBILITY_REVIEW      3402：reviewed retrieval_representation 已寫入
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same scope       bill_diagnosis (LEVEL_A_INSTANCE_GATE_SCOPE) ⇒ [3402, 3406, 3519, 4640, 4656, 4657]
HINT_ONLY  same categories  「帳單管理,條件診斷：帳單」⇒ [3402, 3406]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3406`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3406
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           帳單收據 繳費證明 PDF 下載
categories        帳單管理,條件診斷：帳單
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     direct_answer ／ —
applicability     general（row-level legacy declaration）
  provenance      source=reviewed_product_declaration｜ruling=Level-A truth 逐筆裁定 2026-08-29｜recorded=2026-08-29
  scope           bill_diagnosis (LEVEL_A_INSTANCE_GATE_SCOPE)
  reason          問的是下載機制與操作位置。即使系統可查實際收據，回答「怎麼下載 PDF」不需先讀此人的付款資料。且 4640 已另立「查實際收據金額」錨點，形成正面語義分工。
representation    如何取得帳單收據／繳費證明：下載的位置與方式、收據可作為繳費證明、未繳費的帳單無法產生收據，以及收據與統一發票的區別。
  provenance      source=reviewed_product_declaration｜ruling=R9 Level-A representation 逐筆裁定 2026-08-29
```

### existing authority evidence
```text
POSITIVE_APPLICABILITY_DECLARATION  3406：general（Level-A truth 逐筆裁定 2026-08-29）
CONTENT_RESPONSIBILITY_REVIEW      3406：reviewed retrieval_representation 已寫入
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same scope       bill_diagnosis (LEVEL_A_INSTANCE_GATE_SCOPE) ⇒ [3402, 3406, 3519, 4640, 4656, 4657]
HINT_ONLY  same categories  「帳單管理,條件診斷：帳單」⇒ [3402, 3406]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3495`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3495
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           帳單為什麼發不出去
categories        條件診斷：帳單
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_bill_diagnosis
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        services/jgb/bills.py::_diagnose_cannot_send（B01）
  evidence        form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）
representation    診斷某一筆帳單為什麼無法發送給租客，包含發送失敗、寄不出、按發送無反應等情形。
  provenance      source=reviewed_product_declaration｜ruling=R9 Level-A representation 逐筆裁定 2026-08-29
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY    3495：services/jgb/bills.py::_diagnose_cannot_send（B01）
DETERMINISTIC_CAPABILITY（form→API） 3495：form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3495：instance（P1e-1 業主裁定①）
CONTENT_RESPONSIBILITY_REVIEW      3495：reviewed retrieval_representation 已寫入
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_bill_diagnosis → jgb_bill_detail ⇒ 母體內 5 列共用：[3495, 3496, 3498, 3499, 3502]
HINT_ONLY  same module      services/jgb/bills.py ⇒ [3495, 3496]（⚠️ 函式名相異）
HINT_ONLY  same categories  「條件診斷：帳單」⇒ [3495, 3496, 3498, 3499, 4640, 4656, 4657]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3496`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3496
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           帳單為什麼取消不了
categories        條件診斷：帳單
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_bill_diagnosis
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        services/jgb/bills.py::_diagnose_cannot_cancel（B02）
  evidence        form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）
representation    診斷某一筆帳單為什麼無法取消或作廢，包含取消按鈕不可用、取消時失敗等情形，以及可取消所需的帳單狀態條件。
  provenance      source=reviewed_product_declaration｜ruling=R9 Level-A representation 逐筆裁定 2026-08-29
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY    3496：services/jgb/bills.py::_diagnose_cannot_cancel（B02）
DETERMINISTIC_CAPABILITY（form→API） 3496：form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3496：instance（P1e-1 業主裁定①）
CONTENT_RESPONSIBILITY_REVIEW      3496：reviewed retrieval_representation 已寫入
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_bill_diagnosis → jgb_bill_detail ⇒ 母體內 5 列共用：[3495, 3496, 3498, 3499, 3502]
HINT_ONLY  same module      services/jgb/bills.py ⇒ [3495, 3496]（⚠️ 函式名相異）
HINT_ONLY  same categories  「條件診斷：帳單」⇒ [3495, 3496, 3498, 3499, 4640, 4656, 4657]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3499`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3499
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           帳單手動到帳或標記已收款失敗
categories        條件診斷：帳單
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_bill_diagnosis
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）
representation    查詢／診斷特定帳單手動到帳失敗、無法完成手動入帳的原因。
  provenance      source=reviewed_product_declaration｜ruling=R9 Level-A representation 逐筆裁定 2026-08-29
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3499：form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3499：instance（P1e-1 業主裁定①）
CONTENT_RESPONSIBILITY_REVIEW      3499：reviewed retrieval_representation 已寫入
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_bill_diagnosis → jgb_bill_detail ⇒ 母體內 5 列共用：[3495, 3496, 3498, 3499, 3502]
HINT_ONLY  same categories  「條件診斷：帳單」⇒ [3495, 3496, 3498, 3499, 4640, 4656, 4657]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3519`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3519
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           點退帳單金額計算 押金結算
categories        合約管理,條件診斷：帳單
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     direct_answer ／ —
applicability     general（row-level legacy declaration）
  provenance      source=reviewed_product_declaration｜ruling=Level-A truth 逐筆裁定 2026-08-29｜recorded=2026-08-29
  scope           bill_diagnosis (LEVEL_A_INSTANCE_GATE_SCOPE)
  reason          190 字本身承載計算規則、算式與例子；不需讀某份合約即可正確解釋「怎麼算」。4657 另立實際金額查詢錨點，進一步證明 KB 有意把「規則」與「查值」拆開。
representation    點退帳單金額如何計算：加總哪些結算項目、如何扣抵押金，以及金額為正負時分別代表退款或需補繳差額。
  provenance      source=reviewed_product_declaration｜ruling=R9 Level-A representation 逐筆裁定 2026-08-29
```

### existing authority evidence
```text
POSITIVE_APPLICABILITY_DECLARATION  3519：general（Level-A truth 逐筆裁定 2026-08-29）
CONTENT_RESPONSIBILITY_REVIEW      3519：reviewed retrieval_representation 已寫入
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same scope       bill_diagnosis (LEVEL_A_INSTANCE_GATE_SCOPE) ⇒ [3402, 3406, 3519, 4640, 4656, 4657]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-4640`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            4640
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           帳單收據金額 收據多少錢
categories        條件診斷：帳單
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            **空**
action / form     direct_answer ／ —
applicability     instance（row-level legacy declaration）
  provenance      source=reviewed_product_declaration｜ruling=Level-A truth 逐筆裁定 2026-08-29｜recorded=2026-08-29
  scope           bill_diagnosis (LEVEL_A_INSTANCE_GATE_SCOPE)
  reason          問的是實際金額，不讀該帳單／收據資料無法知道「多少錢」。diagnose_bill 的 B05 確實取實值；且本列是 empty-answer Face-entry anchor，設計上就不是拿通用文字回答。
representation    查詢某一張收據的實際金額，例如某筆帳單的收據實收多少錢。
  provenance      source=reviewed_product_declaration｜ruling=R9 Level-A representation 逐筆裁定 2026-08-29
```

### existing authority evidence
```text
POSITIVE_APPLICABILITY_DECLARATION  4640：instance（Level-A truth 逐筆裁定 2026-08-29）
CONTENT_RESPONSIBILITY_REVIEW      4640：reviewed retrieval_representation 已寫入
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same scope       bill_diagnosis (LEVEL_A_INSTANCE_GATE_SCOPE) ⇒ [3402, 3406, 3519, 4640, 4656, 4657]
HINT_ONLY  same categories  「條件診斷：帳單」⇒ [3495, 3496, 3498, 3499, 4640, 4656, 4657]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-4656`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            4656
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           查帳單 帳單編號查詢
categories        條件診斷：帳單
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            **空**
action / form     direct_answer ／ —
applicability     instance（row-level legacy declaration）
  provenance      source=reviewed_product_declaration｜ruling=Level-A truth 逐筆裁定 2026-08-29｜recorded=2026-08-29
  scope           bill_diagnosis (LEVEL_A_INSTANCE_GATE_SCOPE)
  reason          要查某一筆帳單；bill_diagnosis 的 required_slots=[bill_ref]，後續走 _format_bill_status。沒有特定帳單 referent 就無法完成 intent。
representation    找出並查詢某一筆帳單目前的狀態，包括是否已繳費、是否已寄出或仍為草稿、到期情形，以及該筆帳單的現況。
  provenance      source=reviewed_product_declaration｜ruling=R9 Level-A representation 逐筆裁定 2026-08-29
```

### existing authority evidence
```text
POSITIVE_APPLICABILITY_DECLARATION  4656：instance（Level-A truth 逐筆裁定 2026-08-29）
CONTENT_RESPONSIBILITY_REVIEW      4656：reviewed retrieval_representation 已寫入
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same scope       bill_diagnosis (LEVEL_A_INSTANCE_GATE_SCOPE) ⇒ [3402, 3406, 3519, 4640, 4656, 4657]
HINT_ONLY  same categories  「條件診斷：帳單」⇒ [3495, 3496, 3498, 3499, 4640, 4656, 4657]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-4657`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            4657
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           合約的點退帳單金額 查點退金額
categories        條件診斷：帳單
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            **空**
action / form     direct_answer ／ —
applicability     instance（row-level legacy declaration）
  provenance      source=reviewed_product_declaration｜ruling=Level-A truth 逐筆裁定 2026-08-29｜recorded=2026-08-29
  scope           bill_diagnosis (LEVEL_A_INSTANCE_GATE_SCOPE)
  reason          「查點退金額」要求該份合約／帳單的實際值，不讀 runtime data 無法回答。與 3519 的規則型 row 成對，且自身是 empty-answer entry anchor。
representation    查詢某份合約的點退帳單，包含該筆點退帳單的實際金額與目前狀態。
  provenance      source=reviewed_product_declaration｜ruling=R9 Level-A representation 逐筆裁定 2026-08-29
```

### existing authority evidence
```text
POSITIVE_APPLICABILITY_DECLARATION  4657：instance（Level-A truth 逐筆裁定 2026-08-29）
CONTENT_RESPONSIBILITY_REVIEW      4657：reviewed retrieval_representation 已寫入
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same scope       bill_diagnosis (LEVEL_A_INSTANCE_GATE_SCOPE) ⇒ [3402, 3406, 3519, 4640, 4656, 4657]
HINT_ONLY  same categories  「條件診斷：帳單」⇒ [3495, 3496, 3498, 3499, 4640, 4656, 4657]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

# Batch C —— 其餘已有 applicability declaration 的 singleton

applicability 皆為 P1e-1 的 deterministic 裁定（E1 engine ／ E2 form ／ E3 action），⚠️ 但那是**列層**宣告，⛔ 不等於 responsibility-level authority。

---

## `CG-ROW-3361`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3361
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           帳單沒到帳 帳單狀態
categories        繳費金流排障
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            **空**
action / form     form_fill ／ jgb_bill_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_bill_query → jgb_bills（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3361：form=jgb_bill_query → jgb_bills（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3361：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same categories  「繳費金流排障」⇒ [3361, 3366, 3931, 3932, 3933]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3362`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3362
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           發票沒開 發票狀態
categories        發票
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            **空**
action / form     form_fill ／ jgb_invoice_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_invoice_query → jgb_invoices（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3362：form=jgb_invoice_query → jgb_invoices（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3362：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same categories  「發票」⇒ [3362, 3937, 3938]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3365`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3365
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           修繕進度 修繕查詢
categories        （無）
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            **空**
action / form     form_fill ／ jgb_repair_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_repair_query → jgb_repairs（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3365：form=jgb_repair_query → jgb_repairs（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3365：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
（無）
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3366`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3366
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           繳費成功 繳費紀錄
categories        繳費金流排障
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            **空**
action / form     form_fill ／ jgb_payment_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_payment_query → jgb_payments（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3366：form=jgb_payment_query → jgb_payments（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3366：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same categories  「繳費金流排障」⇒ [3361, 3366, 3931, 3932, 3933]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3368`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3368
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           合約簽約邀請 發送邀請 為什麼不能發送
categories        狀態判斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            **空**
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3368：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3368：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
HINT_ONLY  same categories  「狀態判斷」⇒ [3368, 3370, 3371, 3372]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3370`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3370
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           合約提前解約 可以解約嗎 提前終止
categories        狀態判斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            **空**
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3370：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3370：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
HINT_ONLY  same categories  「狀態判斷」⇒ [3368, 3370, 3371, 3372]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3371`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3371
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           合約續約 可以續約嗎 延長合約
categories        狀態判斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            **空**
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3371：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3371：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
HINT_ONLY  same categories  「狀態判斷」⇒ [3368, 3370, 3371, 3372]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3372`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3372
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           合約狀態查詢 目前狀態
categories        狀態判斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            **空**
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3372：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3372：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
HINT_ONLY  same categories  「狀態判斷」⇒ [3368, 3370, 3371, 3372]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3490`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3490
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           合約為什麼不能發送簽約邀請
categories        條件診斷：合約,狀態判斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3490：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3490：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
HINT_ONLY  same categories  「條件診斷：合約,狀態判斷」⇒ [3490, 3491, 3492, 3493, 3494, 3510, 3511, 3512, 3513, 4255]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3491`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3491
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           合約為什麼不能點交
categories        條件診斷：合約,狀態判斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3491：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3491：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
HINT_ONLY  same categories  「條件診斷：合約,狀態判斷」⇒ [3490, 3491, 3492, 3493, 3494, 3510, 3511, 3512, 3513, 4255]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3492`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3492
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           合約為什麼不能點退
categories        條件診斷：合約,狀態判斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3492：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3492：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
HINT_ONLY  same categories  「條件診斷：合約,狀態判斷」⇒ [3490, 3491, 3492, 3493, 3494, 3510, 3511, 3512, 3513, 4255]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3493`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3493
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           合約為什麼不能提前解約
categories        條件診斷：合約,狀態判斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3493：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3493：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
HINT_ONLY  same categories  「條件診斷：合約,狀態判斷」⇒ [3490, 3491, 3492, 3493, 3494, 3510, 3511, 3512, 3513, 4255]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3494`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3494
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           合約為什麼不能續約
categories        條件診斷：合約,狀態判斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3494：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3494：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
HINT_ONLY  same categories  「條件診斷：合約,狀態判斷」⇒ [3490, 3491, 3492, 3493, 3494, 3510, 3511, 3512, 3513, 4255]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3497`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3497
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           已付款但帳單狀態沒有更新
categories        條件診斷：付款,繳費金流排障
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_payment_diagnosis
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        services/jgb/payments.py::_diagnose_payment_not_reflected（P01）
  evidence        form=jgb_payment_diagnosis → jgb_payment_logs（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY    3497：services/jgb/payments.py::_diagnose_payment_not_reflected（P01）
DETERMINISTIC_CAPABILITY（form→API） 3497：form=jgb_payment_diagnosis → jgb_payment_logs（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3497：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_payment_diagnosis → jgb_payment_logs ⇒ 母體內 3 列共用：[3497, 3500, 3501]
HINT_ONLY  same module      services/jgb/payments.py ⇒ [3497, 3500]（⚠️ 函式名相異）
HINT_ONLY  same categories  「條件診斷：付款,繳費金流排障」⇒ [3497, 3500, 3501, 3502]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3500`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3500
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           信用卡付款失敗
categories        條件診斷：付款,繳費金流排障
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_payment_diagnosis
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        services/jgb/payments.py::_diagnose_credit_card_failure（P02）
  evidence        form=jgb_payment_diagnosis → jgb_payment_logs（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY    3500：services/jgb/payments.py::_diagnose_credit_card_failure（P02）
DETERMINISTIC_CAPABILITY（form→API） 3500：form=jgb_payment_diagnosis → jgb_payment_logs（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3500：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_payment_diagnosis → jgb_payment_logs ⇒ 母體內 3 列共用：[3497, 3500, 3501]
HINT_ONLY  same module      services/jgb/payments.py ⇒ [3497, 3500]（⚠️ 函式名相異）
HINT_ONLY  same categories  「條件診斷：付款,繳費金流排障」⇒ [3497, 3500, 3501, 3502]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3501`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3501
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           信用卡自動扣款失敗
categories        條件診斷：付款,繳費金流排障
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_payment_diagnosis
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_payment_diagnosis → jgb_payment_logs（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3501：form=jgb_payment_diagnosis → jgb_payment_logs（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3501：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_payment_diagnosis → jgb_payment_logs ⇒ 母體內 3 列共用：[3497, 3500, 3501]
HINT_ONLY  same categories  「條件診斷：付款,繳費金流排障」⇒ [3497, 3500, 3501, 3502]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3502`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3502
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           虛擬帳號過期或轉帳失敗
categories        條件診斷：付款,繳費金流排障
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_bill_diagnosis
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3502：form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3502：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_bill_diagnosis → jgb_bill_detail ⇒ 母體內 5 列共用：[3495, 3496, 3498, 3499, 3502]
HINT_ONLY  same categories  「條件診斷：付款,繳費金流排障」⇒ [3497, 3500, 3501, 3502]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3503`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3503
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           發票為什麼沒有開出來
categories        條件診斷：發票,發票
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_invoice_diagnosis
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        services/jgb/invoices.py::_diagnose_issue_failure（I01）
  evidence        form=jgb_invoice_diagnosis → jgb_invoice_logs（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY    3503：services/jgb/invoices.py::_diagnose_issue_failure（I01）
DETERMINISTIC_CAPABILITY（form→API） 3503：form=jgb_invoice_diagnosis → jgb_invoice_logs（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3503：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_invoice_diagnosis → jgb_invoice_logs ⇒ 母體內 2 列共用：[3503, 3504]
HINT_ONLY  same module      services/jgb/invoices.py ⇒ [3503, 3504]（⚠️ 函式名相異）
HINT_ONLY  same categories  「條件診斷：發票,發票」⇒ [3503, 3504]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3504`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3504
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           發票為什麼作廢不了
categories        條件診斷：發票,發票
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_invoice_diagnosis
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        services/jgb/invoices.py::_diagnose_invalid_failure（I02）
  evidence        form=jgb_invoice_diagnosis → jgb_invoice_logs（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY    3504：services/jgb/invoices.py::_diagnose_invalid_failure（I02）
DETERMINISTIC_CAPABILITY（form→API） 3504：form=jgb_invoice_diagnosis → jgb_invoice_logs（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3504：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_invoice_diagnosis → jgb_invoice_logs ⇒ 母體內 2 列共用：[3503, 3504]
HINT_ONLY  same module      services/jgb/invoices.py ⇒ [3503, 3504]（⚠️ 函式名相異）
HINT_ONLY  same categories  「條件診斷：發票,發票」⇒ [3503, 3504]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3505`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3505
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           為什麼不能新增物件
categories        條件診斷：訂閱,條件診斷：物件,物件操作引導
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_subscription_diagnosis
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        services/jgb/subscription.py::_diagnose_cannot_add_estate（E01）
  evidence        form=jgb_subscription_diagnosis → jgb_subscription（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY    3505：services/jgb/subscription.py::_diagnose_cannot_add_estate（E01）
DETERMINISTIC_CAPABILITY（form→API） 3505：form=jgb_subscription_diagnosis → jgb_subscription（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3505：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_subscription_diagnosis → jgb_subscription ⇒ 母體內 2 列共用：[3505, 3506]
HINT_ONLY  same module      services/jgb/subscription.py ⇒ [3505, 3506]（⚠️ 函式名相異）
HINT_ONLY  same categories  「條件診斷：訂閱,條件診斷：物件,物件操作引導」⇒ [3505, 3506]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3506`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3506
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           物件為什麼突然全部下架
categories        條件診斷：訂閱,條件診斷：物件,物件操作引導
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_subscription_diagnosis
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        services/jgb/subscription.py::_diagnose_estates_delisted（E02）
  evidence        form=jgb_subscription_diagnosis → jgb_subscription（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY    3506：services/jgb/subscription.py::_diagnose_estates_delisted（E02）
DETERMINISTIC_CAPABILITY（form→API） 3506：form=jgb_subscription_diagnosis → jgb_subscription（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3506：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_subscription_diagnosis → jgb_subscription ⇒ 母體內 2 列共用：[3505, 3506]
HINT_ONLY  same module      services/jgb/subscription.py ⇒ [3505, 3506]（⚠️ 函式名相異）
HINT_ONLY  same categories  「條件診斷：訂閱,條件診斷：物件,物件操作引導」⇒ [3505, 3506]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3507`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3507
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           物件為什麼不能建立合約
categories        條件診斷：物件,狀態判斷,物件現況診斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3507：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3507：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3508`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3508
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           IoT 廠商帳號綁定失敗
categories        條件診斷：IoT
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_iot_diagnosis
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_iot_diagnosis → jgb_iot_manufacturers（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3508：form=jgb_iot_diagnosis → jgb_iot_manufacturers（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3508：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
（無）
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3510`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3510
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           合約目前是什麼狀態
categories        條件診斷：合約,狀態判斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3510：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3510：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
HINT_ONLY  same categories  「條件診斷：合約,狀態判斷」⇒ [3490, 3491, 3492, 3493, 3494, 3510, 3511, 3512, 3513, 4255]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3511`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3511
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           合約的點交/點退/提前解約/續約按鈕是否可用
categories        條件診斷：合約,狀態判斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3511：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3511：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
HINT_ONLY  same categories  「條件診斷：合約,狀態判斷」⇒ [3490, 3491, 3492, 3493, 3494, 3510, 3511, 3512, 3513, 4255]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3512`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3512
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           為什麼不能取消點交或點退
categories        條件診斷：合約,狀態判斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3512：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3512：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
HINT_ONLY  same categories  「條件診斷：合約,狀態判斷」⇒ [3490, 3491, 3492, 3493, 3494, 3510, 3511, 3512, 3513, 4255]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3513`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3513
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           為什麼不能取消或作廢合約
categories        條件診斷：合約,狀態判斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3513：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3513：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
HINT_ONLY  same categories  「條件診斷：合約,狀態判斷」⇒ [3490, 3491, 3492, 3493, 3494, 3510, 3511, 3512, 3513, 4255]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3514`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3514
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           查詢租客概況 合約帳單修繕
categories        租客管理
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            **空**
action / form     form_fill ／ jgb_tenant_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_tenant_query → jgb_tenant_summary（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3514：form=jgb_tenant_query → jgb_tenant_summary（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3514：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
（無）
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3531`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3531
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           滯納金帳單產生 付款後結算規則
categories        帳單管理,滯納金
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     direct_answer ／ —
applicability     general（row-level legacy declaration）
  provenance      source=reviewed_product_declaration｜ruling=滯納金域 applicability 補齊 2026-08-29（T1/T2 aftermath）｜recorded=2026-08-29
  scope           late_fee face（⛔ 不在 LEVEL_A_V2 內）
  reason          承接的是規則／機制說明：付款後結算的延遲金機制、公式與適用條件。即使完全不知道使用者是哪份合約、哪張帳單，仍能完整正確回答「系統的滯納金怎麼運作」。⛔ 不需要 runtime data 才成立。
representation    NONE
```

### existing authority evidence
```text
POSITIVE_APPLICABILITY_DECLARATION  3531：general（滯納金域 applicability 補齊 2026-08-29（T1/T2 aftermath））
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same scope       late_fee face（⛔ 不在 LEVEL_A_V2 內） ⇒ [3531, 3532, 3939, 3940]
HINT_ONLY  same categories  「帳單管理,滯納金」⇒ [3531, 3532]
HINT_ONLY  content relation 另一列（3531／3532 的另一半）：T2 判 union(3531,3532) 承接 3498 全部有效 claim；⚠️ P2 ⛔ 未代裁
HINT_ONLY  content relation CG-ALIAS-04（3939／3940）categories 同為「滯納金」但applicability 相反（general vs instance）
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-3532`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3532
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           滯納金客製版本 固定金額階梯式
categories        帳單管理,滯納金
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     direct_answer ／ —
applicability     general（row-level legacy declaration）
  provenance      source=reviewed_product_declaration｜ruling=滯納金域 applicability 補齊 2026-08-29（T1/T2 aftermath）｜recorded=2026-08-29
  scope           late_fee face（⛔ 不在 LEVEL_A_V2 內）
  reason          承接的是不同客製版本的計算機制差異（延遲金版／階梯式版／固定金額版）。回答「各版本行為差異」不需先讀任一使用者的合約或帳單實值。
representation    NONE
```

### existing authority evidence
```text
POSITIVE_APPLICABILITY_DECLARATION  3532：general（滯納金域 applicability 補齊 2026-08-29（T1/T2 aftermath））
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same scope       late_fee face（⛔ 不在 LEVEL_A_V2 內） ⇒ [3531, 3532, 3939, 3940]
HINT_ONLY  same categories  「帳單管理,滯納金」⇒ [3531, 3532]
HINT_ONLY  content relation 另一列（3531／3532 的另一半）：T2 判 union(3531,3532) 承接 3498 全部有效 claim；⚠️ P2 ⛔ 未代裁
HINT_ONLY  content relation CG-ALIAS-04（3939／3940）categories 同為「滯納金」但applicability 相反（general vs instance）
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          已有 owner 線索（scope／engine），缺**正式** owner_contract 出處
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-4255`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            4255
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           取消點交邀請 取消點退邀請 收回邀請
categories        條件診斷：合約,狀態判斷
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            **空**
action / form     form_fill ／ jgb_contract_query
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 4255：form=jgb_contract_query → jgb_contracts（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  4255：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_contract_query → jgb_contracts ⇒ 母體內 15 列共用：[3368, 3370, 3371, 3372, 3490, 3491, 3492, 3493, 3494, 3507, 3510, 3511, 3512, 3513, 4255]
HINT_ONLY  same categories  「條件診斷：合約,狀態判斷」⇒ [3490, 3491, 3492, 3493, 3494, 3510, 3511, 3512, 3513, 4255]
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

---

## `CG-ROW-4420`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            4420
state             active
role              （尚無 role——等 P3 membership 裁定）
summary           修繕進度 報修單 修得怎樣了 處理到哪
categories        修繕報修
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     api_call ／ —
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        action=api_call → jgb_repairs
representation    NONE
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 4420：action=api_call → jgb_repairs
POSITIVE_APPLICABILITY_DECLARATION  4420：instance（P1e-1 業主裁定①）
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
（無）
```

### conflicts / tensions
```text
（無群內衝突）
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

# Batch D —— HISTORICAL RETIRED

⚠️ 失效不失憶：宣告與 provenance 保留。identity 若成立，member_role 應為 HISTORICAL_RETIRED。

---

## `CG-ROW-3498`

### proposal_basis
```text
SINGLETON_NO_ALLOWED_RULE_APPLIES
⚠️ 僅代表 P2 無合法機械 grouping evidence，⛔ 不代表已證明為獨立 responsibility
```

### members
```text
row_id            3498
state             INACTIVE ／ RETIRED
role              （尚無 role——等 P3 membership 裁定）
summary           為什麼被收逾期費（延遲金）
categories        條件診斷：帳單
facet             （DB 無 facet 欄位——⚠️ categories ⛔ 不等於 facet）
answer            非空
action / form     form_fill ／ jgb_bill_diagnosis
applicability     instance（row-level legacy declaration）
  provenance      source=deterministic｜ruling=P1e-1 業主裁定①｜recorded=2026-08-29
  evidence        form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）
representation    診斷某一筆帳單為什麼被收取逾期費、延遲金或滯納金，以及該筆費用的計算依據與金額如何得出。
  provenance      source=reviewed_product_declaration｜ruling=R9 Level-A representation 逐筆裁定 2026-08-29
retirement        {"verdict": "K1_FULLY_SUBSUMED + UNDER_QUALIFIED_DUPLICATE", "retired_at": "2026-08-29", "ruling_doc": "t2-3498-knowledge-identity.md", "not_because": "A04 retrieval performance（A04 未執行 harness）", "subsumed_by": [3531, 3532], "declarations_status": "historical retained; operationally inactive", "effective_for_routing": false, "effective_for_scoring": false, "effective_for_population": false, "ownership_consolidated_to": "late_fee face (build_late_fee_facts)"}
```

### existing authority evidence
```text
DETERMINISTIC_CAPABILITY（form→API） 3498：form=jgb_bill_diagnosis → jgb_bill_detail（收 1 個識別欄位）
POSITIVE_APPLICABILITY_DECLARATION  3498：instance（P1e-1 業主裁定①）
CONTENT_RESPONSIBILITY_REVIEW      3498：reviewed retrieval_representation 已寫入
```

### non-authoritative hints ⚠️ HINT_ONLY
```text
HINT_ONLY  same form        form=jgb_bill_diagnosis → jgb_bill_detail ⇒ 母體內 5 列共用：[3495, 3496, 3498, 3499, 3502]
HINT_ONLY  same categories  「條件診斷：帳單」⇒ [3495, 3496, 3498, 3499, 4640, 4656, 4657]
```

### conflicts / tensions
```text
該列已退役（is_active=false）但宣告與 provenance 保留＝失效不失憶
```

### evidence gaps
```text
identity       ⛔ 無任何證據說明此列**不能**與他列同屬一責任——singleton 只是 P2 無合法機械規則
membership     缺：逐列「該列是否真的落在此責任的 answer responsibility 內」的內容比對
applicability  現有僅**列層** legacy declaration；缺 responsibility-level 正面裁定
owner          ⛔ 無 owner 證據——缺 capability／Face 歸屬
```

### P3 VERDICT
```text
I.   IDENTITY        ____
II.  MEMBERSHIP      ____（逐列）
III. APPLICABILITY   ____  declaration_status=____／value=____
IV.  OWNERSHIP       ____
VERDICT              ____  ∈ {CONFIRMED_RESPONSIBILITY, SPLIT_REQUIRED, MERGE_WITH_OTHER,
                            MEMBERSHIP_REJECTED, INSUFFICIENT_EVIDENCE, HISTORICAL_ONLY}
reviewer             ____   reviewed_at ____   review_basis_digest ____
```

# Batch E —— 其餘（無 applicability declaration 且非 alias）

（若本批為空，代表母體內沒有這種列——空批**照列**，⛔ 不靜默略過。）

```text
本批 **0 群**——母體內沒有符合此層的列。⛔ 不是漏列：54 列已在其他批次全數涵蓋。
```
