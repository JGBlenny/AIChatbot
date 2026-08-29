# R10-P2 執行紀錄：proposal-only grouping（2026-08-29）

> **Prime directive：Proposal is allowed to reduce search cost, never to establish responsibility truth.**

## 一、產出

```text
r10p/proposal.json
PROPOSAL_DIGEST=fe6e5f3feba9b26ff5e98d59eb3ae4f38bdd61172e46cba7bbe5347c9e320426
R10P_STAGE=P1_SCHEMA_FROZEN → **P2_PROPOSAL_FROZEN**
結果：54 列 → **47 個 candidate group**＝ 5 個多列群 ＋ 42 個 singleton
```

## 二、執行前複驗（全部相符，⛔ 無一項重算）

```text
SCHEMA    b72e749e0c452f0d…  ✅   POPULATION 51c04b887a16b05f…  ✅
A04 PROTOCOL 01b4d49e…  ✅   CORPUS 83a79070…  ✅   MANIFEST 62d064e3…  ✅
不變量 17 實查：54 列，lines＝ids＝distinct 相符，兩個 digest 未變，聯集無漂移 ✅
```

## 三、三條允許規則的**實際**產出——兩條掛零

```text
① same explicit entry-alias registry responsibility   → 5 群／12 列
② same existing reviewed owner contract               → **0 群**
③ same deterministic mapping（同一 capability 函式）   → **0 群**
```

⚠️ ②③ 掛零是**證據結論**，不是偷懶：

```text
② provenance.scope 是「**當初 review 的範圍**」，⛔ 不是 owner contract。
   scope=bill_diagnosis 底下同時有點退帳單產生（3402）、收據 PDF（3406）、押金結算（3519）——
   顯然不是同一個責任。scope=late_fee face 更是 R10-Q1 淘汰 B 的原始理由
   （同一 scope 內已同時存在 general 與 instance 兩個責任）。
③ 母體內出現 E1_ENGINE_TITLE 的 8 列，**函式名兩兩相異**
   （_diagnose_cannot_send／_cannot_cancel／_payment_not_reflected／_credit_card_failure／
     _issue_failure／_invalid_failure／_cannot_add_estate／_estates_delisted）
   ⇒ 規則三在本母體上數學上不可能產生合併。
   ⚠️ `form=… → API` ⛔ 不予採用為規則三：form 只決定**收哪個識別欄位**，
   不決定回答哪個問題——jgb_contract_query 一個 form 底下就橫跨
   「為什麼不能點交」與「可以續約嗎」兩種明顯不同的責任。
```

⇒ **唯一產生合併的是 registry 的明文裁定**，⛔ 不是任何自動聚類。
5 個群＝繳費金流排障(3931-33)／帳單異常(3934-36)／發票(3937-38)／滯納金(3939-40)／帳單設定引導(3941-42)。

## 四、42 個 singleton 是**合法輸出**

R10-P 問的是「有多少個真正的責任」，⛔ 不是「怎麼把 54 列壓成最少群」。
凡是沒有任何允許規則連得起來的列，一律 `SINGLETON_NO_ALLOWED_RULE_APPLIES`。

## 五、被降格為「提示」而**未**用於分群的訊號

```text
shared_identifier_form    同 form 的列（最大一群 13 列走 jgb_contract_query）
shared_engine_module      同檔案不同函式（bills／invoices／payments／subscription 各 2 列）
shared_reviewed_scope     bill_diagnosis 6 列／late_fee face 4 列
content_relation_notes    3531／3532 可能同屬 general late-fee mechanism（T2 K1 證據）；
                          3498 已退役（is_active=false ＋ retirement）
```
每一條都標了 `_why_not_a_grouping_rule`，⛔ 不得升格為分群依據。

## 六、新增不變量 18（分割身分 ＋ authority 邊界）

```text
scripts/audit/checks/r10p_proposal_integrity.py（--self-test 八項全綠）
① proposed_members 是 54-row 母體的**嚴格分割**（聯集相符／兩兩不相交／無重複）
② proposal.json bytes == 凍結 PROPOSAL_DIGEST；佔位字串一律 FAIL（⛔ 不靜默跳過）
③ candidate 內 ⛔ 不得出現 responsibility_id／applicability／review／status
④ grouping reason ∈ 凍結允許集合
⑤ **多列**群必須來自 entry-alias registry，且成員與 registry 逐一相符
正對照：漏列／漏一多一（總數仍 54）／authority 偷渡／禁用規則合併／假冒 registry／
        bytes 被改／判準換版
```
⚠️ 為什麼要多這一條：17 擋的是「母體少列而不報錯」；proposal 有**第二種同形失效**——
分群後漏一列、另一列重複，`sum(len(members))` 仍然是 54 ⇒ 假綠。

## 七、claim ceiling

```text
可宣稱  已依**凍結機械規則**產出 54-row 母體的 proposal-only grouping，且其分割身分可稽核。
⛔ 不可宣稱  responsibility identity 已成立、applicability 已上移、47 就是責任數。
            47 是**搜尋起點**，P3 human review 可 SPLIT／MERGE／MEMBERSHIP_REJECTED。
```

## 八、下一步

```text
R10-P3  human responsibility review（proposal 只可索引證據，⛔ 不得定義真相）
        每筆裁定需寫 review_basis_digest＝當次**實際引用**的 evidence set
R10-P4  seal registry → REGISTRY_DIGEST
R10-P5  responsibility census（含 LEVEL_A_V2 9 rows 的相異 responsibility 數）
之後    才決定 A05 的 judgment unit / denominator
```
