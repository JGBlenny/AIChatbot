# R10-P3 逐群待裁清單（47 群／54 列）

> **Prime directive：Proposal is allowed to reduce search cost, never to establish responsibility truth.**

```text
來源      r10p/proposal.json（PROPOSAL_DIGEST=fe6e5f3feba9b26f…，P2_PROPOSAL_FROZEN）
判準      R10P-SCHEMA-2（SCHEMA_DIGEST=b72e749e0c452f0d…）
母體      POPULATION 51c04b887a16b05f…／IDSET 00581c42771fa3b0…
本檔性質  frozen proposal ＋ DB 既有 reviewed 事實的**投影**；⛔ 本檔不代裁
裁定正本  r10p/p3-verdicts.json（P3 authority record；⛔ proposal 不得反向定義它）
已裁批次  **47／47 群全數裁定完成（2026-08-29）**——52 筆紀錄（含 5 筆補充 epoch）
          當前 epoch 統計：{'CONFIRMED_RESPONSIBILITY': 30, 'MERGE_WITH_OTHER': 5, 'INSUFFICIENT_EVIDENCE': 10, 'SPLIT_REQUIRED': 1, 'HISTORICAL_ONLY': 1}
  ⛔ 仍不得宣稱相異 responsibility 數——MERGE(5)／SPLIT(1)／HISTORICAL(1) 尚未投影成
     responsibility population，那要等 **P4 seal → P5 census**；⛔ 不得先開 A05
  P-C9  responsibility ≠ current wiring（wiring defect 必須獨立記錄，⛔ 不降格責任）
  P-C10 一列問多個已成立責任 ⇒ SPLIT_REQUIRED，⛔ 不發明 aggregate responsibility
  P-C11 capability absence ⇒ implementation gap，⛔ 不等於 MEMBERSHIP_REJECTED
  CAPABILITY_ALIGNMENT 是**正交** diagnostic 軸，⛔ 不進 frozen verdict vocabulary、
     ⛔ 不改 R10P-SCHEMA-2（schema 未定義 propositions／capability_alignment）
  P-C7  capability binding 由 **utterance** 決定，⛔ 不讀 row id ⇒ row id 不在 code ≠ capability 不存在
        ⚠️ 反面：命中 branch ≠ 責任確認；branch semantics 與宣稱責任不一致 ＝ capability mismatch
  P-C8  applicability 同 ＋ **語義等價** ＋ 落同一 branch ⇒ answer 空否／正反措辭／wiring ⛔ 不構成兩個責任
epoch 模型  同群可有多個 epoch，**最高 epoch ＝ 當前裁定**；⛔ 舊 epoch 不得覆寫
            （舊裁定在其當時 scope 下合法，⛔ 不讓後見之明抹掉 provenance）
判準先例（⛔ 後續批次不得個案推翻，全文見 p3-verdicts.json._precedents）
  P-C1  named deterministic branch ＋ reviewed instance applicability → 可建立 identity ＋ ownership
  P-C2  form unique in KB **≠** ownership proof ⇒ C-④ 六列 ⛔ 不得因『全 KB 唯一』直接綠
  P-C3  instance 列的 answer 只支持 membership，⛔ 不建立 execution ownership
        （⚠️ general 列不同：answer 可支持 ownership=Knowledge）
  P-C4  不同 row wiring（action vs form）**≠** 不同 responsibility——4420／3365 判例
  P-C1a 澄清：P-C1 第一項＝**authoritative** positive instance applicability declaration，
        ⛔ 不限定 source 必須是 reviewed_product_declaration（deterministic 也算）
  P-C5  專屬 deterministic query formatter／path 即可建立 capability，⛔ 不必叫 diagnose
  P-C6  同 builder 只建立 owner domain；builder 若 question-sensitive，
        ⛔ 同 builder 不得推出同 responsibility identity 或 alias membership
LEVEL_A_V2 期中普查  9 列 → **9 CONFIRMED**（3499 於 epoch 2 補齊）／0 unresolved
  ⛔ 仍不得宣稱「LEVEL_A_V2 = 9 unique responsibilities」——9 群各自 confirmed
     ⛔ 不等於 9 個**相異** responsibility；Batch C 仍可能提供跨群 merge evidence
  ⇒ A05 維持 PAUSED：相異責任數要等 P5 census（47 群裁完、merge 收斂後）才算得出
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
applicability authority not established
authoritative owner/capability not established
⚠️ identity ／ membership **已 CONFIRMED**（authoring provenance ＋ registry）——⛔ 不得再列為 gap，⛔ 後續讀到 INSUFFICIENT_EVIDENCE 者不得重審 alias relation。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ 同批 authoring rule「一種講法一筆」＋同 entry-alias registry ⇒ 同一 entry responsibility 的 utterance variants
II.  MEMBERSHIP      CONFIRMED（逐列：3931=ENTRY_ALIAS／3932=ENTRY_ALIAS／3933=ENTRY_ALIAS）
III. APPLICABILITY   declaration_status=undeclared／value=null
       └ ⛔ 不得填 unknown——undeclared 是「尚未建立 authority」，unknown 是「已 review 且確認無法固定」
IV.  OWNERSHIP       NOT_ESTABLISHED
VERDICT              **INSUFFICIENT_EVIDENCE**
       └ **只**不足在 APPLICABILITY／OWNERSHIP。IDENTITY 與 MEMBERSHIP 已 CONFIRMED，⛔ 後續看到 INSUFFICIENT_EVIDENCE 者不得重審 alias relation。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  b0bb97f77d5e7363ef3bb78d0266c97ad375ac57e9d325694ec5ed53c8e5f014
review_input_scope   本批裁定**只**使用 (a) 主 session 訊息中貼出的 Batch A 證據摘要、(b) 已完成的 late-fee T1／T2／H2 證據鏈。⛔ 業主未取得 r10p/p3-review-dossier.md 的 3126 行原文，故 dossier 內**未被貼出**的證據 ⛔ 不屬於本次 review basis。
```

### P3 VERDICT —— epoch 2（補充 review，⛔ 不覆寫 epoch 1）
```text
supersedes_digest    b0bb97f77d5e7363ef3bb78d0266c97ad375ac57e9d325694ec5ed53c8e5f014
superseding_axes     ['IV_OWNERSHIP']
⚠️ epoch 1 的裁定在其當時 scope 下**合法**，⛔ 不得回頭改寫或刪除。

I.   IDENTITY        CONFIRMED
       └ （承 epoch 1，未改）同批 authoring rule「一種講法一筆」＋同 entry-alias registry ⇒ 同一 entry responsibility 的 utterance variants
II.  MEMBERSHIP      CONFIRMED（3931：ENTRY_ALIAS／3932：ENTRY_ALIAS／3933：ENTRY_ALIAS）
III. APPLICABILITY   declaration_status=undeclared／value=null
IV.  OWNERSHIP       CONFIRMED　owner=繳費金流排障 Face ／ rag-orchestrator/services/jgb/bills.py::build_payment_flow_facts
VERDICT              **INSUFFICIENT_EVIDENCE**
       └ IDENTITY／MEMBERSHIP／**OWNERSHIP** 皆已 CONFIRMED；**只**差 APPLICABILITY。⛔ 不得再寫「無 owner 證據」。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  6fd8465e6e81a44f33881f2fe9e2acd5dc70db0b021c4f832243fd034ad16e69
review_input_scope   Batch A 補充 epoch：新增的是**程式面** capability 證據（BILL_FACE_BUILDERS 註冊表 ＋ 具名 builder 函式）。⚠️ 舊 epoch 的 review_input_scope／review_basis_digest／verdict **一律保留**，⛔ 本 epoch 不覆寫既有裁定，只新增 superseding axis 結論。

evidence_gaps（epoch 2）
  - applicability authority not established
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
applicability authority not established
authoritative owner/capability not established
⚠️ identity ／ membership **已 CONFIRMED**（authoring provenance ＋ registry）——⛔ 不得再列為 gap，⛔ 後續讀到 INSUFFICIENT_EVIDENCE 者不得重審 alias relation。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ 同上；⚠️ 先前把三句解讀成三個產品 intent 的說法**已被 authoring provenance 推翻**
II.  MEMBERSHIP      CONFIRMED（逐列：3934=ENTRY_ALIAS／3935=ENTRY_ALIAS／3936=ENTRY_ALIAS）
III. APPLICABILITY   declaration_status=undeclared／value=null
       └ ⛔ 不得填 unknown——undeclared 是「尚未建立 authority」，unknown 是「已 review 且確認無法固定」
IV.  OWNERSHIP       NOT_ESTABLISHED
VERDICT              **INSUFFICIENT_EVIDENCE**
       └ **只**不足在 APPLICABILITY／OWNERSHIP。IDENTITY 與 MEMBERSHIP 已 CONFIRMED，⛔ 後續看到 INSUFFICIENT_EVIDENCE 者不得重審 alias relation。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  9273d63fb64005ab1996b7cefa4d935148b9a12e59c47fcd96ba050cd612bb4d
review_input_scope   本批裁定**只**使用 (a) 主 session 訊息中貼出的 Batch A 證據摘要、(b) 已完成的 late-fee T1／T2／H2 證據鏈。⛔ 業主未取得 r10p/p3-review-dossier.md 的 3126 行原文，故 dossier 內**未被貼出**的證據 ⛔ 不屬於本次 review basis。
```

### P3 VERDICT —— epoch 2（補充 review，⛔ 不覆寫 epoch 1）
```text
supersedes_digest    9273d63fb64005ab1996b7cefa4d935148b9a12e59c47fcd96ba050cd612bb4d
superseding_axes     ['IV_OWNERSHIP']
⚠️ epoch 1 的裁定在其當時 scope 下**合法**，⛔ 不得回頭改寫或刪除。

I.   IDENTITY        CONFIRMED
       └ （承 epoch 1，未改）同上；⚠️ 先前把三句解讀成三個產品 intent 的說法**已被 authoring provenance 推翻**
II.  MEMBERSHIP      CONFIRMED（3934：ENTRY_ALIAS／3935：ENTRY_ALIAS／3936：ENTRY_ALIAS）
III. APPLICABILITY   declaration_status=undeclared／value=null
IV.  OWNERSHIP       CONFIRMED　owner=帳單異常 Face ／ rag-orchestrator/services/jgb/bills.py::build_bill_anomaly_facts
VERDICT              **INSUFFICIENT_EVIDENCE**
       └ IDENTITY／MEMBERSHIP／**OWNERSHIP** 皆已 CONFIRMED；**只**差 APPLICABILITY。⛔ 不得再寫「無 owner 證據」。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  feaa65490775a746c2684e4431579dcf6400d99b940ca23b001dd67e288d88af
review_input_scope   Batch A 補充 epoch：新增的是**程式面** capability 證據（BILL_FACE_BUILDERS 註冊表 ＋ 具名 builder 函式）。⚠️ 舊 epoch 的 review_input_scope／review_basis_digest／verdict **一律保留**，⛔ 本 epoch 不覆寫既有裁定，只新增 superseding axis 結論。

evidence_gaps（epoch 2）
  - applicability authority not established
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
applicability authority not established
authoritative owner/capability not established
⚠️ identity ／ membership **已 CONFIRMED**（authoring provenance ＋ registry）——⛔ 不得再列為 gap，⛔ 後續讀到 INSUFFICIENT_EVIDENCE 者不得重審 alias relation。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ 同一批「講法 variant」證據成立
II.  MEMBERSHIP      CONFIRMED（逐列：3937=ENTRY_ALIAS／3938=ENTRY_ALIAS）
III. APPLICABILITY   declaration_status=undeclared／value=null
       └ ⛔ 不得填 unknown——undeclared 是「尚未建立 authority」，unknown 是「已 review 且確認無法固定」
IV.  OWNERSHIP       NOT_ESTABLISHED
VERDICT              **INSUFFICIENT_EVIDENCE**
       └ **只**不足在 APPLICABILITY／OWNERSHIP。IDENTITY 與 MEMBERSHIP 已 CONFIRMED，⛔ 後續看到 INSUFFICIENT_EVIDENCE 者不得重審 alias relation。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  42e51d62288b11de04d04f1d1d149fa1fc57c67ba2f0334f51628dc8fb3ce6e5
review_input_scope   本批裁定**只**使用 (a) 主 session 訊息中貼出的 Batch A 證據摘要、(b) 已完成的 late-fee T1／T2／H2 證據鏈。⛔ 業主未取得 r10p/p3-review-dossier.md 的 3126 行原文，故 dossier 內**未被貼出**的證據 ⛔ 不屬於本次 review basis。
```

### P3 VERDICT —— epoch 2（補充 review，⛔ 不覆寫 epoch 1）
```text
supersedes_digest    42e51d62288b11de04d04f1d1d149fa1fc57c67ba2f0334f51628dc8fb3ce6e5
superseding_axes     ['IV_OWNERSHIP']
⚠️ epoch 1 的裁定在其當時 scope 下**合法**，⛔ 不得回頭改寫或刪除。

I.   IDENTITY        CONFIRMED
       └ （承 epoch 1，未改）同一批「講法 variant」證據成立
II.  MEMBERSHIP      CONFIRMED（3937：ENTRY_ALIAS／3938：ENTRY_ALIAS）
III. APPLICABILITY   declaration_status=undeclared／value=null
IV.  OWNERSHIP       CONFIRMED　owner=發票 Face ／ rag-orchestrator/services/jgb/bills.py::build_invoice_facts
VERDICT              **INSUFFICIENT_EVIDENCE**
       └ IDENTITY／MEMBERSHIP／**OWNERSHIP** 皆已 CONFIRMED；**只**差 APPLICABILITY。⛔ 不得再寫「無 owner 證據」。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  60aec8e54e21533503c6bf4441e1034b3116311537f86b2cdae25a82d28af41f
review_input_scope   Batch A 補充 epoch：新增的是**程式面** capability 證據（BILL_FACE_BUILDERS 註冊表 ＋ 具名 builder 函式）。⚠️ 舊 epoch 的 review_input_scope／review_basis_digest／verdict **一律保留**，⛔ 本 epoch 不覆寫既有裁定，只新增 superseding axis 結論。

evidence_gaps（epoch 2）
  - applicability authority not established
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
GRANULARITY_EVIDENCE  同 facet（categories=滯納金）另有 general responsibilities 3531／3532。
⚠️ 這是**粒度證據**——正是 R10-Q1 裁定 facet ≠ responsibility 的原始理由；
⛔ **不是**本 responsibility 的 unresolved conflict，⛔ 不得讓 registry 看起來像
   3939／3940 的 instance identity 仍與 3531／3532 衝突。
3939／3940：representation 未寫（NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）
⇒ 不變量 16 TRANSITIONAL_GUARD 仍在生效。
```

### evidence gaps
```text
（無）——I／II／III／IV 四項命題皆已由獨立證據各自成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ H2 VARIANTS_BY_DESIGN
II.  MEMBERSHIP      CONFIRMED（逐列：3939=ENTRY_ALIAS／3940=ENTRY_ALIAS）
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=late_fee Face ／ services/jgb/bills.py::build_late_fee_facts
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——P3 confirmation 後才命名；⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  52827904e20864fcd9a62233d4ae9f8182062cb163817a3f55e7ac1ce28741d6
review_input_scope   本批裁定**只**使用 (a) 主 session 訊息中貼出的 Batch A 證據摘要、(b) 已完成的 late-fee T1／T2／H2 證據鏈。⛔ 業主未取得 r10p/p3-review-dossier.md 的 3126 行原文，故 dossier 內**未被貼出**的證據 ⛔ 不屬於本次 review basis。
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
applicability authority not established
authoritative owner/capability not established
⚠️ identity ／ membership **已 CONFIRMED**（authoring provenance ＋ registry）——⛔ 不得再列為 gap，⛔ 後續讀到 INSUFFICIENT_EVIDENCE 者不得重審 alias relation。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ 同一 authoring rule 支持 alias identity
II.  MEMBERSHIP      CONFIRMED（逐列：3941=ENTRY_ALIAS／3942=ENTRY_ALIAS）
III. APPLICABILITY   declaration_status=undeclared／value=null
       └ ⛔ 不得填 unknown——undeclared 是「尚未建立 authority」，unknown 是「已 review 且確認無法固定」
IV.  OWNERSHIP       NOT_ESTABLISHED
VERDICT              **INSUFFICIENT_EVIDENCE**
       └ **只**不足在 APPLICABILITY／OWNERSHIP。IDENTITY 與 MEMBERSHIP 已 CONFIRMED，⛔ 後續看到 INSUFFICIENT_EVIDENCE 者不得重審 alias relation。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  2d71994bb51dbafb32e2b0dd7c1d87b50a981a45b20a3c2c8651713fad8ad345
review_input_scope   本批裁定**只**使用 (a) 主 session 訊息中貼出的 Batch A 證據摘要、(b) 已完成的 late-fee T1／T2／H2 證據鏈。⛔ 業主未取得 r10p/p3-review-dossier.md 的 3126 行原文，故 dossier 內**未被貼出**的證據 ⛔ 不屬於本次 review basis。
```

# Batch B —— LEVEL_A_V2 相關 singleton（9 群／9 列）

⚠️ 這 9 列同時是 LEVEL_A_V2 的 active routing scope，且**全數**已有 reviewed retrieval_representation。

### P3 VERDICT —— epoch 2（補充 review，⛔ 不覆寫 epoch 1）
```text
supersedes_digest    2d71994bb51dbafb32e2b0dd7c1d87b50a981a45b20a3c2c8651713fad8ad345
superseding_axes     ['IV_OWNERSHIP_EVIDENCE_QUALITY']
⚠️ epoch 1 的裁定在其當時 scope 下**合法**，⛔ 不得回頭改寫或刪除。

I.   IDENTITY        CONFIRMED
       └ 同一 authoring rule 支持 alias identity
II.  MEMBERSHIP      CONFIRMED（3941：ENTRY_ALIAS／3942：ENTRY_ALIAS）
III. APPLICABILITY   declaration_status=undeclared／value=null
IV.  OWNERSHIP       NOT_ESTABLISHED
VERDICT              **INSUFFICIENT_EVIDENCE**
       └ IDENTITY／MEMBERSHIP 已 CONFIRMED；OWNERSHIP 之「未建立」現在是**正面事實**而非缺證據。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  95d7fbc6e4cb53fbeb59808dddfe919137fa52ed2bf501452626af5386178883
review_input_scope   Batch A 補充 epoch：新增的是**程式面** capability 證據（BILL_FACE_BUILDERS 註冊表 ＋ 具名 builder 函式）。⚠️ 舊 epoch 的 review_input_scope／review_basis_digest／verdict **一律保留**，⛔ 本 epoch 不覆寫既有裁定，只新增 superseding axis 結論。

evidence_gaps（epoch 2）
  - applicability authority not established
  - semantic responsibility owner not established: current code positively identifies this facet as category-only/light guidance and provides no deterministic builder
```

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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ responsibility ＝「點退完成後何時／何條件產生帳單並進入結算」，⛔ 不是查某筆實值
II.  MEMBERSHIP      CONFIRMED（3402：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=general
IV.  OWNERSHIP       CONFIRMED　owner=Knowledge（非空 answer ＋ reviewed content responsibility 即為 authority；⛔ 不要求另有 engine）
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  df24d420de768a776dd92db0111190926071b89946e8719978b7b4ce8d8ebef5
review_input_scope   本輪 Batch B 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／runtime causal evidence；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ 與 4640 有**既有** positive semantic partition：「取得方式」≠「某張收據實際金額」
II.  MEMBERSHIP      CONFIRMED（3406：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=general
IV.  OWNERSHIP       CONFIRMED　owner=Knowledge（非空 answer ＋ reviewed content responsibility 即為 authority；⛔ 不要求另有 engine）
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  4341984adb1d3c3709adbeff80a00493ac1984cd46ef92483c070d7d8d67ba53
review_input_scope   本輪 Batch B 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／runtime causal evidence；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ 有**可區分的** deterministic sub-responsibility（具名分支 B01）
II.  MEMBERSHIP      CONFIRMED（3495：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=bill_diagnosis ／ rag-orchestrator/services/jgb/bills.py::_diagnose_cannot_send
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  41253010f10da608d1c1fe23a78a8871780701f7c0729c8ee401a8ee3ccfca01
review_input_scope   本輪 Batch B 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／runtime causal evidence；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ 有**可區分的** deterministic sub-responsibility（具名分支 B02）
II.  MEMBERSHIP      CONFIRMED（3496：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=bill_diagnosis ／ rag-orchestrator/services/jgb/bills.py::_diagnose_cannot_cancel
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  edd9d408151ecc734dc410ce040691631bd62d1b04056fa382d42dcd04c46448
review_input_scope   本輪 Batch B 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／runtime causal evidence；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
- no deterministic sub-intent capability or dispatch evidence distinguishing manual-arrival failure from sibling bill_diagnosis responsibilities
- shared form mapping establishes execution domain only, not responsibility identity or ownership
- reviewed instance applicability does not by itself establish a distinct responsibility
⚠️ 同 form 在母體內橫跨 5 列（3495／3496／3498／3499／3502）⇒ form ⛔ 無法區分它們
轉 CONFIRMED 的正向證據（任一即可）：既有具名 deterministic branch／可證明的 question→fact 分流／原始 authoring responsibility spec／runtime causal／mutation 證明它確實有獨立 execution semantics
```

### P3 VERDICT
```text
I.   IDENTITY        NOT_ESTABLISHED_AS_DISTINCT_RESPONSIBILITY
       └ 語義上看似「手動到帳失敗」，但唯一 execution evidence 是一個同時服務 5 列的 form
II.  MEMBERSHIP      NOT_YET_CONFIRMED（3499：candidate member —— 其所屬 responsibility identity 尚未建立）
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       NOT_ESTABLISHED
VERDICT              **INSUFFICIENT_EVIDENCE**
       └ APPLICABILITY 軸**已 reviewed（instance）**，但 IDENTITY／OWNERSHIP 未建立。⛔ 不得因單一 axis 已 reviewed 就把整個 responsibility 升格為 CONFIRMED。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  ebf4d0aa4c8e6fea0de1d4bcab02235491c276f415aaa62982334e1793dafc92
review_input_scope   本輪 Batch B 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／runtime causal evidence；⛔ 未貼出的 dossier evidence 不屬本次 basis。
```

### P3 VERDICT —— epoch 2（補充 review，⛔ 不覆寫 epoch 1）
```text
supersedes_digest    ebf4d0aa4c8e6fea0de1d4bcab02235491c276f415aaa62982334e1793dafc92
superseding_axes     ['I_IDENTITY', 'II_MEMBERSHIP', 'IV_OWNERSHIP', 'VERDICT']
⚠️ epoch 1 的 INSUFFICIENT_EVIDENCE 在其當時 basis 下**合法**，⛔ 不改寫、⛔ 不改 digest。新證據足以改變 I／IV 與整體 verdict ⇒ ⛔ 不得只當旁註。

I.   IDENTITY        CONFIRMED
       └ 「特定帳單手動到帳／標記已收款失敗」有**獨立 deterministic sub-intent**
II.  MEMBERSHIP      CONFIRMED（3499：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=bill_diagnosis ／ rag-orchestrator/services/jgb/bills.py:602::_diagnose_manual_complete
VERDICT              **CONFIRMED_RESPONSIBILITY**
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  6e3c8be0531b95fe1184c7ecad0cb29971bfc4d6478185951f672f4707769565
review_input_scope   本輪 C-⑤ 摘要 ＋ 其中明示引用的 production dispatch 實查（bills.py::diagnose_bill、payments.py::diagnose_payment_logs、contracts.py::_build_response 的關鍵字分流與具名 check）；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ 與 4657 的「查實際點退帳單」已有正面書面分工
II.  MEMBERSHIP      CONFIRMED（3519：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=general
IV.  OWNERSHIP       CONFIRMED　owner=Knowledge（非空 answer ＋ reviewed content responsibility 即為 authority；⛔ 不要求另有 engine）
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  74047ecbbd32d7b51c5be72a672988c88842d8e8faaae0bb924c1ffdc44f98e5
review_input_scope   本輪 Batch B 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／runtime causal evidence；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ 與 3406 的 general download responsibility 有正面分工，且 B05 取的是 runtime actual value
II.  MEMBERSHIP      CONFIRMED（4640：ANSWER_KNOWLEDGE（active；empty-answer Face-entry anchor））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=bill_diagnosis 的 receipt-amount deterministic capability（B05）
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  726146ecb2748216862bfb59cd09751f4d1e4d47f572acb72253e56878aa0e58
review_input_scope   本輪 Batch B 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／runtime causal evidence；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ identity 由 `bill_ref` referent ＋ status capability 定義
II.  MEMBERSHIP      CONFIRMED（4656：ANSWER_KNOWLEDGE（active；empty-answer Face-entry anchor））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=bill_diagnosis ／ rag-orchestrator/services/jgb/bills.py::_format_bill_status 路徑
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  752b204f140c18aebe4eae5fc8ffad270194122442dcfdfc20c2a25901a6c2f7
review_input_scope   本輪 Batch B 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／runtime causal evidence；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ defining operation 含「由合約找出 type=2 點退帳單」，⛔ 不是單純既知 bill_ref 的狀態查詢
II.  MEMBERSHIP      CONFIRMED（4657：ANSWER_KNOWLEDGE（active；empty-answer Face-entry anchor））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=POINT_REFUND_BILL_SELECTION ＋ downstream bill facts
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  c35b55a23b4e6c927ecb60e17c5c87b906e01672c3de3c1d56761622c78df149
review_input_scope   本輪 Batch B 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／runtime causal evidence；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
- responsibility identity not established despite known owner domain
- membership relation to CG-ALIAS-01 remains OPEN（⛔ 不得機械併入）
⚠️ 新合法形狀：**owner 已知，⛔ 不代表 responsibility identity 已知。**
```

### P3 VERDICT
```text
I.   IDENTITY        NOT_ESTABLISHED_AS_DISTINCT
       └ owner domain 已建立，但 build_payment_flow_facts 經 T4 判為 **QUESTION_SENSITIVE**，可在內部承接多個 sub-intent ⇒ 同一 builder ⛔ 不等於同一 responsibility（P-C6）
II.  MEMBERSHIP      NOT_YET_CONFIRMED（3361：與 CG-ALIAS-01 的 membership relation = **OPEN**——3361 ⛔ 不受「一種講法一筆」authoring rule 約束，目前無正向 alias 證據）
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED_AT_FACE_CAPABILITY_LEVEL　owner=繳費金流排障 Face ／ rag-orchestrator/services/jgb/bills.py::build_payment_flow_facts
VERDICT              **INSUFFICIENT_EVIDENCE**
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  042327ced1561e96affd8d2af7d98c363ba83b6abbcf3cdbc7ad64a14de559f5
review_input_scope   本輪 Batch C-④ 摘要 ＋ 其中明示引用的 formatter endpoint 分派實查（jgb_response_formatter.py::format_jgb_response 12 個分支全列）、具名 builder／engine、T4 question-sensitivity 稽核；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
- responsibility identity not established
- authoritative owner/capability not established
form 全 KB 唯一 ⛔ 不升格為 ownership（P-C2）
通用 _format_single ⛔ 不提供 responsibility-specific capability evidence
⚠️ 即使 CG-ALIAS-03 已知有 build_invoice_facts（CG-ALIAS-03），⛔ 不得直接把 3362 merge 過去：目前**未證明**本列實際走該 Face builder，亦無 authoring alias provenance
```

### P3 VERDICT
```text
I.   IDENTITY        NOT_ESTABLISHED
       └ 「發票沒開／發票狀態」目前只有 endpoint 與唯一 form，⛔ 無可區分的 deterministic semantics
II.  MEMBERSHIP      NOT_YET_CONFIRMED（3362：candidate member —— 所屬 responsibility identity 尚未建立）
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       NOT_ESTABLISHED　owner=jgb_invoices endpoint only
VERDICT              **INSUFFICIENT_EVIDENCE**
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  f01a6cbf34f21a6a944c4da6fa175b65f5119a04d1d87641a7cdb7c15bec8f93
review_input_scope   本輪 Batch C-④ 摘要 ＋ 其中明示引用的 formatter endpoint 分派實查（jgb_response_formatter.py::format_jgb_response 12 個分支全列）、具名 builder／engine、T4 question-sensitivity 稽核；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
⚠️ 本群的 identity ⛔ 不是靠「form 全 KB 唯一」建立（P-C2 已禁）；是靠兩種 wiring 收斂到同一 execution target ＋ 同一 downstream path
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ 3365 ＋ 4420 = same repair-progress-query responsibility——兩種不同 wiring（form vs action）對**同一 semantic operation** 收斂到同一 execution target 與同一 downstream path（P-C4）
II.  MEMBERSHIP      CONFIRMED（3365：ANSWER_KNOWLEDGE（active；answer 空）／4420：ANSWER_KNOWLEDGE（active）——經 CG-ROW-4420 的 MERGE_WITH_OTHER 併入）
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=jgb_repairs query／action capability
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ 封存併入：['CG-ROW-4420']（該群 verdict 維持 MERGE_WITH_OTHER）
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  a8eb7c15cba47da34fa75d6f31cd63540fb615bd501ff0a8c0d092f17fdae808
review_input_scope   本輪 Batch C-④ 摘要 ＋ 其中明示引用的 formatter endpoint 分派實查（jgb_response_formatter.py::format_jgb_response 12 個分支全列）、具名 builder／engine、T4 question-sensitivity 稽核；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
- responsibility identity not established
- authoritative owner/capability not established
form 全 KB 唯一 ⛔ 不升格為 ownership（P-C2）
通用 _format_single ⛔ 不提供 responsibility-specific capability evidence
```

### P3 VERDICT
```text
I.   IDENTITY        NOT_ESTABLISHED
       └ 「繳費成功／繳費紀錄」目前只有 endpoint 與唯一 form，⛔ 無可區分的 deterministic semantics
II.  MEMBERSHIP      NOT_YET_CONFIRMED（3366：candidate member —— 所屬 responsibility identity 尚未建立）
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       NOT_ESTABLISHED　owner=jgb_payments endpoint only
VERDICT              **INSUFFICIENT_EVIDENCE**
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  d560d945c80e6cb7c2e106d31968c053a82cb98927a92f87df0fe119f0489965
review_input_scope   本輪 Batch C-④ 摘要 ＋ 其中明示引用的 formatter endpoint 分派實查（jgb_response_formatter.py::format_jgb_response 12 個分支全列）、具名 builder／engine、T4 question-sensitivity 稽核；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        NOT_DISTINCT_AS_SINGLETON
       └ semantic intent 與 CG-ROW-3490 等價，且 deterministic 落同一 branch（invite）——依 P-C8，answer 空／非空 ⛔ 不是 responsibility boundary
II.  MEMBERSHIP      BELONGS_TO_SHARED_RESPONSIBILITY（3368：併入 CG-ROW-3490 的共同 responsibility（該 target 已於本輪 sealed））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       SUPPORTED_VIA_MERGE_TARGET　owner=見 CG-ROW-3490
VERDICT              **MERGE_WITH_OTHER** → CG-ROW-3490（joint_seal_pending=**False**）
       └ verdict 維持 MERGE_WITH_OTHER——⛔ 不得改寫成 CONFIRMED_RESPONSIBILITY。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  6874e56b06354f56aed6d086b473c64ad11f783f3747d7246f1b0919a6357ffd
review_input_scope   本輪 C-⑤ 摘要 ＋ 其中明示引用的 production dispatch 實查（bills.py::diagnose_bill、payments.py::diagnose_payment_logs、contracts.py::_build_response 的關鍵字分流與具名 check）；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        NOT_DISTINCT_AS_SINGLETON
       └ semantic intent 與 CG-ROW-3493 等價，且 deterministic 落同一 branch（early_termination）——依 P-C8，answer 空／非空 ⛔ 不是 responsibility boundary
II.  MEMBERSHIP      BELONGS_TO_SHARED_RESPONSIBILITY（3370：併入 CG-ROW-3493 的共同 responsibility（該 target 已於本輪 sealed））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       SUPPORTED_VIA_MERGE_TARGET　owner=見 CG-ROW-3493
VERDICT              **MERGE_WITH_OTHER** → CG-ROW-3493（joint_seal_pending=**False**）
       └ verdict 維持 MERGE_WITH_OTHER——⛔ 不得改寫成 CONFIRMED_RESPONSIBILITY。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  c3adcc9257a765cb5baea208be402e74ac0776c0bb58ece387f1e094549b7938
review_input_scope   本輪 C-⑤ 摘要 ＋ 其中明示引用的 production dispatch 實查（bills.py::diagnose_bill、payments.py::diagnose_payment_logs、contracts.py::_build_response 的關鍵字分流與具名 check）；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        NOT_DISTINCT_AS_SINGLETON
       └ semantic intent 與 CG-ROW-3494 等價，且 deterministic 落同一 branch（renew）——依 P-C8，answer 空／非空 ⛔ 不是 responsibility boundary
II.  MEMBERSHIP      BELONGS_TO_SHARED_RESPONSIBILITY（3371：併入 CG-ROW-3494 的共同 responsibility（該 target 已於本輪 sealed））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       SUPPORTED_VIA_MERGE_TARGET　owner=見 CG-ROW-3494
VERDICT              **MERGE_WITH_OTHER** → CG-ROW-3494（joint_seal_pending=**False**）
       └ verdict 維持 MERGE_WITH_OTHER——⛔ 不得改寫成 CONFIRMED_RESPONSIBILITY。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  eca903d149b0fc8fbc6c12c2c26ddb4922557dae16dae6075ee2a268912ce96a
review_input_scope   本輪 C-⑤ 摘要 ＋ 其中明示引用的 production dispatch 實查（bills.py::diagnose_bill、payments.py::diagnose_payment_logs、contracts.py::_build_response 的關鍵字分流與具名 check）；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        NOT_DISTINCT_AS_SINGLETON
       └ semantic intent 與 CG-ROW-3510 等價，且 deterministic 落同一 branch（status fallback）——依 P-C8，answer 空／非空 ⛔ 不是 responsibility boundary
II.  MEMBERSHIP      BELONGS_TO_SHARED_RESPONSIBILITY（3372：併入 CG-ROW-3510 的共同 responsibility（該 target 已於本輪 sealed））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       SUPPORTED_VIA_MERGE_TARGET　owner=見 CG-ROW-3510
VERDICT              **MERGE_WITH_OTHER** → CG-ROW-3510（joint_seal_pending=**False**）
       └ verdict 維持 MERGE_WITH_OTHER——⛔ 不得改寫成 CONFIRMED_RESPONSIBILITY。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  bbfc29d1806afbd85c6822c085f4e15fa0d0bc3fdc80557c9b83b1b7e13ec253
review_input_scope   本輪 C-⑤ 摘要 ＋ 其中明示引用的 production dispatch 實查（bills.py::diagnose_bill、payments.py::diagnose_payment_logs、contracts.py::_build_response 的關鍵字分流與具名 check）；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
⚠️ 依 P-C7：rag-orchestrator/services/jgb/contracts.py:681::_build_response（關鍵字 elif 分流） ⛔ 不讀 row id；capability binding 由 utterance 決定，⛔ 不因「code 沒出現 row id」判定 capability 不存在
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ canonical responsibility：判斷／診斷某份合約為何不能發送簽約邀請，以及目前是否符合發送條件。
II.  MEMBERSHIP      CONFIRMED（3490：ANSWER_KNOWLEDGE（active）／3368：ANSWER_KNOWLEDGE（active；answer 空）——經 CG-ROW-3368 的 MERGE 併入）
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=rag-orchestrator/services/jgb/contracts.py:128::check_can_invite
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ 封存併入：['CG-ROW-3368']（該群 verdict 維持 MERGE_WITH_OTHER）
       └ CG-ROW-3490 只是本次 P3 的 joint target（review bookkeeping）——⛔ 不代表最終 responsibility identity 綁在 3490 這一列。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  8a3cfc6a7088966e1b72e212972c61ed6eb3a0895b4d1a63fbd8adfcfeed7db2
review_input_scope   本輪 C-⑤ 摘要 ＋ 其中明示引用的 production dispatch 實查（bills.py::diagnose_bill、payments.py::diagnose_payment_logs、contracts.py::_build_response 的關鍵字分流與具名 check）；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
⚠️ ⛔ 與 3491／3492 的另一列**不** merge：雖共用同一 `_build_response` dispatcher，但進的是**不同 deterministic branch、不同 eligibility predicate**
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ canonical responsibility：判斷／診斷某份合約能否點交，以及不能的原因。
II.  MEMBERSHIP      CONFIRMED（3491：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=rag-orchestrator/services/jgb/contracts.py:161::check_can_move_in
VERDICT              **CONFIRMED_RESPONSIBILITY**
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  6aacc3816ca9dd88746a21a77b36a46b20202eed921387dfd1c8fbccafaf6fce
review_input_scope   本輪 C-⑤ 摘要 ＋ 其中明示引用的 production dispatch 實查（bills.py::diagnose_bill、payments.py::diagnose_payment_logs、contracts.py::_build_response 的關鍵字分流與具名 check）；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
⚠️ ⛔ 與 3491／3492 的另一列**不** merge：雖共用同一 `_build_response` dispatcher，但進的是**不同 deterministic branch、不同 eligibility predicate**
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ canonical responsibility：判斷／診斷某份合約能否點退，以及不能的原因。
II.  MEMBERSHIP      CONFIRMED（3492：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=rag-orchestrator/services/jgb/contracts.py:203::check_can_move_out
VERDICT              **CONFIRMED_RESPONSIBILITY**
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  92ce5906ce6a5b5a110a454e65d5eed6dcaf5ea7b7d869a2149e07a8177a0661
review_input_scope   本輪 C-⑤ 摘要 ＋ 其中明示引用的 production dispatch 實查（bills.py::diagnose_bill、payments.py::diagnose_payment_logs、contracts.py::_build_response 的關鍵字分流與具名 check）；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
⚠️ 依 P-C7：rag-orchestrator/services/jgb/contracts.py:681::_build_response（關鍵字 elif 分流） ⛔ 不讀 row id；capability binding 由 utterance 決定，⛔ 不因「code 沒出現 row id」判定 capability 不存在
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ canonical responsibility：判斷／診斷某份合約能否提前解約，以及不能的原因。⚠️「可以提前解約嗎」與「為什麼不能提前解約」是同一 eligibility responsibility 的 positive／negative phrasing。
II.  MEMBERSHIP      CONFIRMED（3493：ANSWER_KNOWLEDGE（active）／3370：ANSWER_KNOWLEDGE（active；answer 空）——經 CG-ROW-3370 的 MERGE 併入）
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=rag-orchestrator/services/jgb/contracts.py:257::check_can_early_termination
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ 封存併入：['CG-ROW-3370']（該群 verdict 維持 MERGE_WITH_OTHER）
       └ CG-ROW-3493 只是本次 P3 的 joint target（review bookkeeping）——⛔ 不代表最終 responsibility identity 綁在 3493 這一列。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  6584f2c75538c988d6674345918b17dcf2a8fafb635e5f6b3d37afcfa4e3d456
review_input_scope   本輪 C-⑤ 摘要 ＋ 其中明示引用的 production dispatch 實查（bills.py::diagnose_bill、payments.py::diagnose_payment_logs、contracts.py::_build_response 的關鍵字分流與具名 check）；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
⚠️ 依 P-C7：rag-orchestrator/services/jgb/contracts.py:681::_build_response（關鍵字 elif 分流） ⛔ 不讀 row id；capability binding 由 utterance 決定，⛔ 不因「code 沒出現 row id」判定 capability 不存在
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ canonical responsibility：判斷／診斷某份合約能否續約，以及不能的原因。
II.  MEMBERSHIP      CONFIRMED（3494：ANSWER_KNOWLEDGE（active）／3371：ANSWER_KNOWLEDGE（active；answer 空）——經 CG-ROW-3371 的 MERGE 併入）
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=rag-orchestrator/services/jgb/contracts.py:294::check_can_renew
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ 封存併入：['CG-ROW-3371']（該群 verdict 維持 MERGE_WITH_OTHER）
       └ CG-ROW-3494 只是本次 P3 的 joint target（review bookkeeping）——⛔ 不代表最終 responsibility identity 綁在 3494 這一列。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  37c6ca63ee8c6744959696a1db0d5b445cc191e330cd541220809e076377074d
review_input_scope   本輪 C-⑤ 摘要 ＋ 其中明示引用的 production dispatch 實查（bills.py::diagnose_bill、payments.py::diagnose_payment_logs、contracts.py::_build_response 的關鍵字分流與具名 check）；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ named branch 本身即**正面** identity evidence——⛔ 不是因為 row wording 看起來不同，而是 production deterministic execution **已經**把不同問項分到不同 sub-capability
II.  MEMBERSHIP      CONFIRMED（3497：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=payment_flow::_diagnose_payment_not_reflected（rag-orchestrator/services/jgb/payments.py::_diagnose_payment_not_reflected）
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  d19f194484bda9b0736af6adfd2a9ceec86fbabe3302b42025908c97f781885e
review_input_scope   本輪 Batch C-①②③ 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／answer 本文；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ named branch 本身即**正面** identity evidence——⛔ 不是因為 row wording 看起來不同，而是 production deterministic execution **已經**把不同問項分到不同 sub-capability
II.  MEMBERSHIP      CONFIRMED（3500：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=payment_flow::_diagnose_credit_card_failure（rag-orchestrator/services/jgb/payments.py::_diagnose_credit_card_failure）
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  ee03e154f6370a5b546d7b6df5b11150e77ed7b3f6a3fa142f8a5edeffe6f22f
review_input_scope   本輪 Batch C-①②③ 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／answer 本文；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ 與 C-① 六群同形：具名分支 ＋ 可達 dispatch
II.  MEMBERSHIP      CONFIRMED（3501：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=diagnose_payment_logs ／ rag-orchestrator/services/jgb/payments.py:120::_diagnose_auto_pay_failure
VERDICT              **CONFIRMED_RESPONSIBILITY**
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  74e4d294802871a01fba0969f8f7a097b348f57178f91c23d48806db7b4fbe6f
review_input_scope   本輪 C-⑤ 摘要 ＋ 其中明示引用的 production dispatch 實查（bills.py::diagnose_bill、payments.py::diagnose_payment_logs、contracts.py::_build_response 的關鍵字分流與具名 check）；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ 與 C-① 六群同形：具名分支 ＋ 可達 dispatch
II.  MEMBERSHIP      CONFIRMED（3502：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=diagnose_bill ／ rag-orchestrator/services/jgb/bills.py:625::_diagnose_atm_expired
VERDICT              **CONFIRMED_RESPONSIBILITY**
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  46218cd0a8c30d3c35fb69a0552dbf7b9e55d60f949cb223c9b519fec18e1c45
review_input_scope   本輪 C-⑤ 摘要 ＋ 其中明示引用的 production dispatch 實查（bills.py::diagnose_bill、payments.py::diagnose_payment_logs、contracts.py::_build_response 的關鍵字分流與具名 check）；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ named branch 本身即**正面** identity evidence——⛔ 不是因為 row wording 看起來不同，而是 production deterministic execution **已經**把不同問項分到不同 sub-capability
II.  MEMBERSHIP      CONFIRMED（3503：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=invoice::_diagnose_issue_failure（rag-orchestrator/services/jgb/invoices.py::_diagnose_issue_failure）
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  cb5ea81d1891024026e2ce228462f12d3f8601d5b5f7036a14f04a1c08b1bd0b
review_input_scope   本輪 Batch C-①②③ 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／answer 本文；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ named branch 本身即**正面** identity evidence——⛔ 不是因為 row wording 看起來不同，而是 production deterministic execution **已經**把不同問項分到不同 sub-capability
II.  MEMBERSHIP      CONFIRMED（3504：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=invoice::_diagnose_invalid_failure（rag-orchestrator/services/jgb/invoices.py::_diagnose_invalid_failure）
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  3e4676e4c45c9f8c40af6ba64579510246e9d55958febe2a6b3b91d347ae90ca
review_input_scope   本輪 Batch C-①②③ 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／answer 本文；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ named branch 本身即**正面** identity evidence——⛔ 不是因為 row wording 看起來不同，而是 production deterministic execution **已經**把不同問項分到不同 sub-capability
II.  MEMBERSHIP      CONFIRMED（3505：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=subscription::_diagnose_cannot_add_estate（rag-orchestrator/services/jgb/subscription.py::_diagnose_cannot_add_estate）
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  be3d4b77e6baeaac1e95a43c64cf9d81f23de414e052aa20da3e7abe350f4a5d
review_input_scope   本輪 Batch C-①②③ 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／answer 本文；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ named branch 本身即**正面** identity evidence——⛔ 不是因為 row wording 看起來不同，而是 production deterministic execution **已經**把不同問項分到不同 sub-capability
II.  MEMBERSHIP      CONFIRMED（3506：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=subscription::_diagnose_estates_delisted（rag-orchestrator/services/jgb/subscription.py::_diagnose_estates_delisted）
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  39e1430d32d65e28a6c7f8e4789d3da51da9b4306d8c1767a23fee3b5e22b5a8
review_input_scope   本輪 Batch C-①②③ 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／answer 本文；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
⚠️ 依 P-C9：wiring defect ⛔ 不得把 responsibility 降成 INSUFFICIENT。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ claimed responsibility「這個物件為什麼不能建約」有**非常直接的** deterministic capability evidence，⛔ 非推測
II.  MEMBERSHIP      CONFIRMED（3507：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=estate-status ／ rag-orchestrator/services/jgb/estates.py:33::build_estate_status_facts
VERDICT              **CONFIRMED_RESPONSIBILITY**
CAPABILITY_ALIGNMENT  ['WRONG_EXECUTION_BINDING_CONFIRMED']  ⚠️ 與 verdict **正交**的 diagnostic，⛔ 不是 verdict
       expected：endpoint jgb_estate_status ＋ face「物件現況診斷」→ build_estate_status_facts
       current ：form=jgb_contract_query → jgb_contracts → contract status fallback
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  6e76fb61c7992572f8b71ba68a68f1a65b8ae0cdfd85ff4c7d6c8b1b6556c962
review_input_scope   本輪最後六群摘要 ＋ 其中明示引用的程式面實查（estates.py::build_estate_status_facts ／ESTATE_FACE_BUILDERS ／ contracts.py 五個 check_can_* ＋ elif 分流 ／ 全 services 掃「取消點交／取消點退／收回邀請／撤回／cancel_invite」0 命中且有正對照）、answer 本文與 source_type provenance；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ 具名診斷引擎存在，符合 P-C1（deterministic applicability 是正面 authoritative declaration）
II.  MEMBERSHIP      CONFIRMED（3508：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=rag-orchestrator/services/jgb/iot.py::diagnose_iot
VERDICT              **CONFIRMED_RESPONSIBILITY**
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  9834632c18fafdcde713786cd239e23bd56aba97b5a19fbb2e290f406573e58f
review_input_scope   本輪 Batch C-④ 摘要 ＋ 其中明示引用的 formatter endpoint 分派實查（jgb_response_formatter.py::format_jgb_response 12 個分支全列）、具名 builder／engine、T4 question-sensitivity 稽核；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
⚠️ **尺度限制**：`_format_status_response` 作為 fallback **本身** ⛔ 不是 ownership proof。它在 3372／3510 足夠，是因為 claimed responsibility 與 fallback 的 semantic output 正面一致；⛔ 不得反過來替 3513（不能取消合約）或 3507（不能建立合約）背書——那兩列是**錯誤地跌進** fallback。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ canonical responsibility：查詢某份合約目前狀態。
II.  MEMBERSHIP      CONFIRMED（3510：ANSWER_KNOWLEDGE（active）／3372：ANSWER_KNOWLEDGE（active；answer 空）——經 CG-ROW-3372 的 MERGE 併入）
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=rag-orchestrator/services/jgb/contracts.py:744::_format_status_response
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ 封存併入：['CG-ROW-3372']（該群 verdict 維持 MERGE_WITH_OTHER）
       └ CG-ROW-3510 只是本次 P3 的 joint target——⛔ 不代表最終 identity 綁在 3510。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  e03e8e67470b0738f2557cd18d23b053125fa679dc1f23319a64f720f5646a80
review_input_scope   本輪 C-⑤ 摘要 ＋ 其中明示引用的 production dispatch 實查（bills.py::diagnose_bill、payments.py::diagnose_payment_logs、contracts.py::_build_response 的關鍵字分流與具名 check）；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
⚠️ 依 P-C10：⛔ 不得為了補這個 execution gap 發明第五個 aggregate responsibility。
```

### P3 VERDICT
```text
I.   IDENTITY        REJECTED_AS_SINGLE_RESPONSIBILITY
       └ row spans four already-confirmed responsibilities——answer 自己明示「**逐一**檢查各操作的前置條件」⇒ 這是 multi-responsibility request，⛔ 不是第五個獨立 semantic responsibility
II.  MEMBERSHIP      SPLIT_ACROSS（3511：拆分至 3491 move_in／3492 move_out／3493 early_termination／3494 renew）
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       NO_SINGLE_OWNER　owner=constituent owners ＝ 四個 deterministic check（check_can_move_in／move_out／early_termination／renew）
VERDICT              **SPLIT_REQUIRED**
       └ split_across：['CG-ROW-3491', 'CG-ROW-3492', 'CG-ROW-3493', 'CG-ROW-3494']
CAPABILITY_ALIGNMENT  ['COMPOSITE_EXECUTION_GAP_CONFIRMED']  ⚠️ 與 verdict **正交**的 diagnostic，⛔ 不是 verdict
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  9fd016afcc07fc566fcbfec65883c6cbfc108d07ebaf00009cc58c393f2cefe3
review_input_scope   本輪最後六群摘要 ＋ 其中明示引用的程式面實查（estates.py::build_estate_status_facts ／ESTATE_FACE_BUILDERS ／ contracts.py 五個 check_can_* ＋ elif 分流 ／ 全 services 掃「取消點交／取消點退／收回邀請／撤回／cancel_invite」0 命中且有正對照）、answer 本文與 source_type provenance；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
- authoritative responsibility identity not established
- no deterministic cancel-eligibility capability
全 services 掃「取消點交／取消點退／收回邀請／撤回／cancel_invite」＝ **0 命中**；正對照：同一掃描抓得到 bills.py 的 `_diagnose_cannot_cancel`（3 處）⇒ 掃描有效，⛔ 不是掃不到
⚠️ 依 P-C11：⛔ 不得用 MEMBERSHIP_REJECTED——我們證明的是「系統沒實作這個 capability」，⛔ 不是「產品上不應存在這個 responsibility」
```

### P3 VERDICT
```text
I.   IDENTITY        NOT_ESTABLISHED_AS_AUTHORITATIVE_RESPONSIBILITY
       └ 「能不能點交」≠「能不能**取消**點交」；現況只因含「點交」而錯落 move_in
II.  MEMBERSHIP      CONTENT_MEMBERSHIP_SUPPORTED（3512：answer 帶正面產品規則（取消點交需 status=16／取消點退需 status=64／租客已同意不能撤回）⇒ 支持 content membership，⚠️ 但**未**完全確認為 authoritative responsibility）
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       NOT_ESTABLISHED　owner=no cancel_move_in ／ cancel_move_out capability found
VERDICT              **INSUFFICIENT_EVIDENCE**
CAPABILITY_ALIGNMENT  ['CLAIMED_CAPABILITY_NOT_IMPLEMENTED_CONFIRMED']  ⚠️ 與 verdict **正交**的 diagnostic，⛔ 不是 verdict
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  5d79c9d33faa732795616be7a7b88f2082f70e652852f4cb7a9812c82ab8bc19
review_input_scope   本輪最後六群摘要 ＋ 其中明示引用的程式面實查（estates.py::build_estate_status_facts ／ESTATE_FACE_BUILDERS ／ contracts.py 五個 check_can_* ＋ elif 分流 ／ 全 services 掃「取消點交／取消點退／收回邀請／撤回／cancel_invite」0 命中且有正對照）、answer 本文與 source_type provenance；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
- authoritative responsibility identity not established
- no deterministic contract-cancel capability
全 services 掃「取消點交／取消點退／收回邀請／撤回／cancel_invite」＝ **0 命中**；正對照：同一掃描抓得到 bills.py 的 `_diagnose_cannot_cancel`（3 處）⇒ 掃描有效，⛔ 不是掃不到
⚠️ answer 指向「改用提前解約」**⛔ 不構成 merge 到 3493**——那是 remediation／action recommendation，⛔ 不是「取消合約 responsibility ＝ 提前解約 responsibility」
⚠️ ⛔ 不得引 3510 的 status fallback 判例背書：3513 是**錯誤地跌進** fallback
```

### P3 VERDICT
```text
I.   IDENTITY        NOT_ESTABLISHED_AS_AUTHORITATIVE_RESPONSIBILITY
       └ claimed「為什麼不能取消或作廢合約」；production 五個 keyword branch 全不命中 → status fallback，與 claimed responsibility **不一致**
II.  MEMBERSHIP      CONTENT_MEMBERSHIP_SUPPORTED（3513：answer 帶正面規則（status >= 8 已簽署生效不能直接取消，需改走提前解約））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       NOT_ESTABLISHED
VERDICT              **INSUFFICIENT_EVIDENCE**
CAPABILITY_ALIGNMENT  ['CLAIMED_CAPABILITY_NOT_IMPLEMENTED_CONFIRMED', 'SEMANTIC_FALLBACK_MISMATCH_CONFIRMED']  ⚠️ 與 verdict **正交**的 diagnostic，⛔ 不是 verdict
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  6173e5f5acab7d415e11360c791f08584c466b25eaa7874dca6130b7be48b4d3
review_input_scope   本輪最後六群摘要 ＋ 其中明示引用的程式面實查（estates.py::build_estate_status_facts ／ESTATE_FACE_BUILDERS ／ contracts.py 五個 check_can_* ＋ elif 分流 ／ 全 services 掃「取消點交／取消點退／收回邀請／撤回／cancel_invite」0 命中且有正對照）、answer 本文與 source_type provenance；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ 專屬 deterministic capability path 已成立——⚠️ 依 P-C5，「函式名沒有 diagnose」⛔ 不構成降格理由；要驗的是責任是否有 deterministic implementation
II.  MEMBERSHIP      CONFIRMED（3514：ANSWER_KNOWLEDGE（active；answer 空））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       CONFIRMED　owner=jgb_tenant_summary ＋ rag-orchestrator/services/jgb_response_formatter.py::_format_tenant_summary
VERDICT              **CONFIRMED_RESPONSIBILITY**
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  107298ad2c6e4f84500e7cebafd2e768e047bf3dc2c1223a335ec64ed86e16ef
review_input_scope   本輪 Batch C-④ 摘要 ＋ 其中明示引用的 formatter endpoint 分派實查（jgb_response_formatter.py::format_jgb_response 12 個分支全列）、具名 builder／engine、T4 question-sensitivity 稽核；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
GRANULARITY_EVIDENCE  同 categories=滯納金 另有 instance responsibility（3939／3940，已 CONFIRMED）。
⛔ `3498.subsumed_by=[3531,3532]` **不得**被當成 merge evidence——它只證明「3498 的過寬內容需要兩者**聯集**才完整吸收」，⛔ 不能反推 3531 = 3532。
⛔ `3498.ownership_consolidated_to = late_fee Face` 是 **3498 的 instance ownership** 收斂到 B，⛔ 不得把 3531／3532 這兩個 general Knowledge responsibility 偷轉成 Face ownership。
⛔ 兩列**不因**同 categories=滯納金 而合併——依據是正面內容分工，非 facet。
```

### evidence gaps
```text
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ canonical responsibility：付款後結算型延遲金的產生機制、適用條件與計算規則
II.  MEMBERSHIP      CONFIRMED（3531：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=general
IV.  OWNERSHIP       CONFIRMED　owner=Knowledge（非空 answer ＋ reviewed content responsibility 即為 authority）
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility（草擬，⛔ 尚未命名 id）：付款後結算型延遲金的產生機制、適用條件與計算規則
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  548de61b1a65906c05da3918601ca53e1ecd82378ba1cc1296388246e67ec5f3
review_input_scope   本輪 Batch C-①②③ 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／answer 本文；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
GRANULARITY_EVIDENCE  同 categories=滯納金 另有 instance responsibility（3939／3940，已 CONFIRMED）。
⛔ `3498.subsumed_by=[3531,3532]` **不得**被當成 merge evidence——它只證明「3498 的過寬內容需要兩者**聯集**才完整吸收」，⛔ 不能反推 3531 = 3532。
⛔ `3498.ownership_consolidated_to = late_fee Face` 是 **3498 的 instance ownership** 收斂到 B，⛔ 不得把 3531／3532 這兩個 general Knowledge responsibility 偷轉成 Face ownership。
⛔ 兩列**不因**同 categories=滯納金 而合併——依據是正面內容分工，非 facet。
```

### evidence gaps
```text
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
```

### P3 VERDICT
```text
I.   IDENTITY        CONFIRMED
       └ canonical responsibility：滯納金客製計算版本的機制差異（延遲金／階梯式／固定金額等）
II.  MEMBERSHIP      CONFIRMED（3532：ANSWER_KNOWLEDGE（active））
III. APPLICABILITY   declaration_status=reviewed／value=general
IV.  OWNERSHIP       CONFIRMED　owner=Knowledge（非空 answer ＋ reviewed content responsibility 即為 authority）
VERDICT              **CONFIRMED_RESPONSIBILITY**
       └ canonical responsibility（草擬，⛔ 尚未命名 id）：滯納金客製計算版本的機制差異（延遲金／階梯式／固定金額等）
       └ canonical responsibility_id ⛔ 尚未命名——⛔ 不回頭改 P2 candidate id。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  dddaf821e382dc3807bd7bf5dd123704678236514844cdd7f876450b8cef7a07
review_input_scope   本輪 Batch C-①②③ 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／answer 本文；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
- responsibility identity not established
- no content evidence（answer 空）
- no authoring spec
- no cancel/withdraw capability
全 services 掃「取消點交／取消點退／收回邀請／撤回／cancel_invite」＝ **0 命中**；正對照：同一掃描抓得到 bills.py 的 `_diagnose_cannot_cancel`（3 處）⇒ 掃描有效，⛔ 不是掃不到
⚠️ **證據強度低於 3512／3513**：那兩列有非空 answer 可支持 product-rule membership，4255 沒有——⛔ 不得把三者寫成同一強度
row provenance：source_type=manual、source_file=**無**、created_at=2026-07-06
```

### P3 VERDICT
```text
I.   IDENTITY        NOT_ESTABLISHED
       └ send invitation ≠ withdraw invitation；現況因含「邀請」錯落 invite
II.  MEMBERSHIP      NOT_CONFIRMED（4255：answer **空** ＋ manual provenance ＋ 無 authoring spec⇒ ⛔ 連 content membership 都無法支持）
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       NOT_ESTABLISHED
VERDICT              **INSUFFICIENT_EVIDENCE**
CAPABILITY_ALIGNMENT  ['CLAIMED_CAPABILITY_NOT_IMPLEMENTED_CONFIRMED', 'WRONG_BRANCH_CONFIRMED']  ⚠️ 與 verdict **正交**的 diagnostic，⛔ 不是 verdict
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  3bc3a6f736d729c8c2f37e934584be20e5f4de426df6d89e6848b15e4cbfa49c
review_input_scope   本輪最後六群摘要 ＋ 其中明示引用的程式面實查（estates.py::build_estate_status_facts ／ESTATE_FACE_BUILDERS ／ contracts.py 五個 check_can_* ＋ elif 分流 ／ 全 services 掃「取消點交／取消點退／收回邀請／撤回／cancel_invite」0 命中且有正對照）、answer 本文與 source_type provenance；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
✅ 已封存：joint_seal_pending=False（2026-08-29，由 CG-ROW-3365（epoch 1，batch C-4） 封存）
verdict **維持** MERGE_WITH_OTHER——⛔ 不得改寫成 CONFIRMED_RESPONSIBILITY；它的 proposal-level 歷史就是「merge into」，現在只是 target 已 sealed。
```

### P3 VERDICT
```text
I.   IDENTITY        NOT_DISTINCT_AS_SINGLETON
       └ positive evidence supports same responsibility as 3365——⛔ 不同 row wiring ≠ 不同 responsibility
II.  MEMBERSHIP      BELONGS_TO_SHARED_RESPONSIBILITY（4420：belongs to the shared repair-progress-query responsibility；3365 membership 待 CG-ROW-3365 review 時共同封存）
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       SUPPORTED_PENDING_JOINT_SEAL　owner=jgb_repairs execution path is supported；final responsibility record waits for joint 3365 review
VERDICT              **MERGE_WITH_OTHER** → CG-ROW-3365（joint_seal_pending=**False**）
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  36542591d4104ec2ee584df519c519c7e68af9b2cb4beb135595dfe1dd6ad31b
review_input_scope   本輪 Batch C-①②③ 摘要 ＋ 其中**明示引用**的既有 reviewed declaration／deterministic capability／answer 本文；⛔ 未貼出的 dossier evidence 不屬本次 basis。
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
（無）——I／II／III／IV 四項命題皆已由**各自**的證據成立。
⚠️ 失效不失憶：宣告與 provenance 保留，⛔ 不刪。
```

### P3 VERDICT
```text
I.   IDENTITY        HISTORICAL_RETIRED_RESPONSIBILITY_RECORD
       └ no active independent responsibility remains
II.  MEMBERSHIP      HISTORICAL_RETIRED_ONLY（3498：HISTORICAL_RETIRED member only（is_active=false））
III. APPLICABILITY   declaration_status=reviewed／value=instance
IV.  OWNERSHIP       SUPERSEDED　owner=historical A ownership = superseded；active late-fee instance ownership = B（late_fee face／build_late_fee_facts）；general knowledge truth = subsumed by 3531 ＋ 3532
VERDICT              **HISTORICAL_ONLY**
CAPABILITY_ALIGNMENT  ['RETIRED_NO_ACTIVE_BINDING']  ⚠️ 與 verdict **正交**的 diagnostic，⛔ 不是 verdict
       └ 這正是 schema 裡 HISTORICAL_ONLY 應該存在的案例。
reviewer             業主   reviewed_at 2026-08-29
review_basis_digest  5ef3b3f271001a01ae171bf584bcc8af3691130e40998ac175b66eaa185c08c4
review_input_scope   本輪最後六群摘要 ＋ 其中明示引用的程式面實查（estates.py::build_estate_status_facts ／ESTATE_FACE_BUILDERS ／ contracts.py 五個 check_can_* ＋ elif 分流 ／ 全 services 掃「取消點交／取消點退／收回邀請／撤回／cancel_invite」0 命中且有正對照）、answer 本文與 source_type provenance；⛔ 未貼出的 dossier evidence 不屬本次 basis。
```

# Batch E —— 其餘（無 applicability declaration 且非 alias）

（若本批為空，代表母體內沒有這種列——空批**照列**，⛔ 不靜默略過。）

```text
本批 **0 群**——母體內沒有符合此層的列。⛔ 不是漏列：54 列已在其他批次全數涵蓋。
```
