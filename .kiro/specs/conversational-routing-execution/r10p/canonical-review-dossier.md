# R10-CANONICAL-REVIEW 待裁清單（30 個 reviewed_active responsibility）

```text
來源      r10p/registry.json（REGISTRY_DIGEST=3e5bcdc6a8265fbf…）
目標      status=reviewed_active ⇒ canonical_responsibility MUST be non-null ＋ reviewed
排除      reviewed_historical（R-?? / 3498）⛔ 不要求 active scoring canonical
本檔性質  proposal evidence 的投影；⛔ 不裁定、⛔ 不自動升格 canonical authority
γ-1 結論  9 個 Level-A reviewed row representation **全部是有效 evidence，但只有少數適合逐字升格**
          （R-14 幾乎原樣、R-06 近乎逐字；R-07／R-11／R-29／R-30／R-31 皆需修）
          ⇒ 反證當初**沒有**直接做 migration-copy 是對的
```

## 四條規約

```text
① **⛔ 不得從 row representation 自動搬**：authority unit 已從 row 換成 responsibility。
   逐字沿用**可以**，但那必須是 reviewer 的裁定結果，⛔ 不是 migration rule。
② **multi-member responsibility 的 canonical 必須描述「共同責任」**——
   ⛔ 不得直接拿 target row 的 wording 當 responsibility truth（bookkeeping target ≠ 語義中心）。
③ responsibility_id `R-xx` 是**永久 opaque identity**（業主裁定）——
   語義放 canonical_responsibility／facet／owner，⛔ 不塞進 primary key，⛔ 不做語義重新命名。
④ 每筆裁定 ∈ {APPROVED, REVISE, INSUFFICIENT}。
⑤ ⚠️ **P3 identity 措辭 ⛔ 不等於 canonical authority**——8 筆帶 P3 文字的群一律仍是
   PENDING_CANONICAL_REVIEW，必須逐筆裁定（不變量 21 只認 canonical_review.verdict=APPROVED）。

γ 尺（2026-08-30 凍結）
  γ-C1  canonical 預設**不列舉** implementation rules／status fields／條件數／examples／
        utterance variants——問法變體留給 alias/recall surface，⛔ canonical 不兼任 synonym dictionary
  γ-C2  能區分兩個已確認 responsibilities 的必要 selection operation，要以**產品語義**寫進
        canonical；⛔ 實作欄位／函式細節不寫（R-31 正例：寫「依指定合約找出其點退帳單」⛔ 不寫 type=2）
  γ-C3  成對 responsibility 必須在 **canonical 本身**可辨識——⛔ 不能靠 applicability metadata 擦屁股

α 尺（2026-08-30 凍結，γ 一體適用）
  α-C1  eligibility responsibility canonical 描述「能否執行某操作 ＋ 不能的原因」；⛔ 不枚舉當前規則、條件數量或 UI 細節。
  α-C2  general responsibilities 可以同 facet 共存，但 canonical 必須把 semantic operation 明確分開：single-mechanism explanation ≠ cross-version comparison ≠ instance diagnosis。
  late-fee 三角：R-26 general 單一機制詳解／R-27 general 跨版本比較／R-28 instance 實際診斷

β 尺（2026-08-29 凍結，α／γ 一體適用）
  β-C1  multi-member canonical ＝ confirmed responsibility **intersection**，⛔ 非 member-text union
  β-C2  deterministic builder facts **支撐** canonical，但 capability output breadth
        ⛔ 不自動定義 responsibility breadth
```

⚠️ **8 個 multi-member responsibility 適用規約②**：R-01(3365,4420)／R-02(3368,3490)／R-03(3370,3493,3511)／R-04(3371,3494,3511)／R-05(3372,3510)／R-08(3491,3511)／R-09(3492,3511)／R-28(3939,3940)

---

## `R-01`　（sealed from CG-ROW-3365）

```text
members        3365[ANSWER_KNOWLEDGE/active], 4420[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          jgb_repairs query／action capability
P3 identity    3365 ＋ 4420 = same repair-progress-query responsibility——兩種不同 wiring（form vs action）對**同一 semantic operation** 收斂到同一 execution target 與同一 downstream path（P-C4）
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3365  summary：修繕進度 修繕查詢
           ⚠️ 無 representation、answer 空 ⇒ 本列提供不了文字證據
row 4420  summary：修繕進度 報修單 修得怎樣了 處理到哪
           answer（61 字）：為您查詢名下的報修單處理進度；若目前沒有任何報修單，代表尚未提出報修——需要的話跟我說「我要報修」，我可以直接協助您建單。
```

### ⚠️ 規約② 適用
```text
本責任有多個 member ⇒ canonical 必須描述**共同責任**，
⛔ 不得偏向任一 member（例：3365+4420 ⛔ 不得偏向 form row 或 action row 任一邊）。
```

### CANONICAL VERDICT
```text
canonical_responsibility  查詢既有修繕／報修案件目前的處理進度或狀態。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-29

review basis（此句實際依賴的證據）
  - P3 identity ruling：3365＋4420 已確認為同一 repair-progress-query responsibility
  - 3365 summary「修繕進度／修繕查詢」
  - 4420 summary「修繕進度／報修單修得怎樣了／處理到哪」
  - 4420 answer 的**第一責任句**（查詢報修單處理進度）
  - 兩列由 form／action wiring 收斂到同一 jgb_repairs execution target 且同走 _format_single——⚠️ 此證據支持**共同 capability**，⛔ 不用於擴張 canonical
  - reviewed applicability=instance ⇒ canonical 描述的是**既有案件查值**，⛔ 非 general repair mechanism

deliberate exclusions
  - ⛔ 不寫「需要的話協助建立報修單」——那是 4420 answer 的後續引導，對應另一個 jgb_create_repair 能力，⛔ 不屬於兩列已確認 responsibility 的 intersection
  - ⛔ 不寫「名下所有報修單」——「名下」只來自 4420 文案，3365 無文字證據支持此額外範圍
```

---

## `R-02`　（sealed from CG-ROW-3490）

```text
members        3368[ANSWER_KNOWLEDGE/active], 3490[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          rag-orchestrator/services/jgb/contracts.py:128::check_can_invite
P3 identity    canonical responsibility：判斷／診斷某份合約為何不能發送簽約邀請，以及目前是否符合發送條件。
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3368  summary：合約簽約邀請 發送邀請 為什麼不能發送
           ⚠️ 無 representation、answer 空 ⇒ 本列提供不了文字證據
row 3490  summary：合約為什麼不能發送簽約邀請
           answer（37 字）：合約無法發送簽約邀請時，系統會提示「欄位未填寫完整」。請依序排查以下條件。
```

### 已有業主陳述（P3 identity ruling 內明示）
```text
判斷／診斷某份合約為何不能發送簽約邀請，以及目前是否符合發送條件。
⚠️ 仍需一次確認：這句是否即為 responsibility 的 canonical contract。
```

### ⚠️ 規約② 適用
```text
本責任有多個 member ⇒ canonical 必須描述**共同責任**，
⛔ 不得偏向任一 member（例：3365+4420 ⛔ 不得偏向 form row 或 action row 任一邊）。
```

### CANONICAL VERDICT
```text
canonical_responsibility  判斷某份合約目前是否符合發送簽約邀請的條件，並診斷無法發送的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 identity ruling（本句只是語序整理，⛔ 責任未擴張）
  - check_can_invite（contracts.py:128）deterministic owner
  - 3368 summary 同時含正反兩面（發送邀請／為什麼不能發送）
  - 3490 answer 的責任句

deliberate exclusions
  - ⛔ 3490 的「欄位未填寫完整」及後續條件清單是 capability／content evidence，⛔ 不進 canonical
```

---

## `R-03`　（sealed from CG-ROW-3493）

```text
members        3370[ANSWER_KNOWLEDGE/active], 3493[ANSWER_KNOWLEDGE/active], 3511[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          rag-orchestrator/services/jgb/contracts.py:257::check_can_early_termination
P3 identity    canonical responsibility：判斷／診斷某份合約能否提前解約，以及不能的原因。⚠️「可以提前解約嗎」與「為什麼不能提前解約」是同一 eligibility responsibility 的 positive／negative phrasing。
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3370  summary：合約提前解約 可以解約嗎 提前終止
           ⚠️ 無 representation、answer 空 ⇒ 本列提供不了文字證據
row 3493  summary：合約為什麼不能提前解約
           answer（21 字）：提前解約按鈕灰色時，需判斷合約狀態和設定。
row 3511  summary：合約的點交/點退/提前解約/續約按鈕是否可用
           answer（40 字）：需查合約狀態欄位，逐一檢查各操作的前置條件。前端只顯示按鈕可不可按，不顯示原因。
```

### 已有業主陳述（P3 identity ruling 內明示）
```text
判斷／診斷某份合約能否提前解約，以及不能的原因。⚠️「可以提前解約嗎」與「為什麼不能提前解約」是同一 eligibility responsibility 的 positive／negative phrasing。
⚠️ 仍需一次確認：這句是否即為 responsibility 的 canonical contract。
```

### ⚠️ 規約② 適用
```text
本責任有多個 member ⇒ canonical 必須描述**共同責任**，
⛔ 不得偏向任一 member（例：3365+4420 ⛔ 不得偏向 form row 或 action row 任一邊）。
```

### CANONICAL VERDICT
```text
canonical_responsibility  判斷某份合約目前是否符合提前解約條件，並診斷無法提前解約的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 identity ruling
  - check_can_early_termination（contracts.py:257）deterministic owner
  - 3370「可以提前解約嗎」＋ 3493「為什麼不能」⇒ 支持同一句同時涵蓋正反問法
  - 3511 只支持涵蓋關係

deliberate exclusions
  - ⛔ P3 尾句「positive／negative phrasing 是同一 eligibility responsibility」只屬 review rationale，⛔ 不進 canonical
```

---

## `R-04`　（sealed from CG-ROW-3494）

```text
members        3371[ANSWER_KNOWLEDGE/active], 3494[ANSWER_KNOWLEDGE/active], 3511[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          rag-orchestrator/services/jgb/contracts.py:294::check_can_renew
P3 identity    canonical responsibility：判斷／診斷某份合約能否續約，以及不能的原因。
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3371  summary：合約續約 可以續約嗎 延長合約
           ⚠️ 無 representation、answer 空 ⇒ 本列提供不了文字證據
row 3494  summary：合約為什麼不能續約
           answer（20 字）：續約按鈕灰色時，需逐一排查 7 個條件。
row 3511  summary：合約的點交/點退/提前解約/續約按鈕是否可用
           answer（40 字）：需查合約狀態欄位，逐一檢查各操作的前置條件。前端只顯示按鈕可不可按，不顯示原因。
```

### 已有業主陳述（P3 identity ruling 內明示）
```text
判斷／診斷某份合約能否續約，以及不能的原因。
⚠️ 仍需一次確認：這句是否即為 responsibility 的 canonical contract。
```

### ⚠️ 規約② 適用
```text
本責任有多個 member ⇒ canonical 必須描述**共同責任**，
⛔ 不得偏向任一 member（例：3365+4420 ⛔ 不得偏向 form row 或 action row 任一邊）。
```

### CANONICAL VERDICT
```text
canonical_responsibility  判斷某份合約目前是否符合續約條件，並診斷無法續約的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 identity ruling
  - check_can_renew（contracts.py:294）deterministic owner
  - 3371「可以續約嗎」＋ 3494「為什麼不能續約」
  - 3511 只支持涵蓋關係

deliberate exclusions
  - ⛔ 3494 的「7 個條件」不進 canonical——`7` 是當前 implementation／content detail；responsibility identity ⛔ 不應因條件從 7 變 8 就得改 contract
```

---

## `R-05`　（sealed from CG-ROW-3510）

```text
members        3372[ANSWER_KNOWLEDGE/active], 3510[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          rag-orchestrator/services/jgb/contracts.py:744::_format_status_response
P3 identity    canonical responsibility：查詢某份合約目前狀態。
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3372  summary：合約狀態查詢 目前狀態
           ⚠️ 無 representation、answer 空 ⇒ 本列提供不了文字證據
row 3510  summary：合約目前是什麼狀態
           answer（22 字）：需查詢合約的 status 來判斷目前階段。
```

### 已有業主陳述（P3 identity ruling 內明示）
```text
查詢某份合約目前狀態。
⚠️ 仍需一次確認：這句是否即為 responsibility 的 canonical contract。
```

### ⚠️ 規約② 適用
```text
本責任有多個 member ⇒ canonical 必須描述**共同責任**，
⛔ 不得偏向任一 member（例：3365+4420 ⛔ 不得偏向 form row 或 action row 任一邊）。
```

### CANONICAL VERDICT
```text
canonical_responsibility  查詢某份合約目前的狀態或所處階段。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - 3372「合約狀態查詢／目前狀態」
  - 3510「合約目前是什麼狀態」
  - _format_status_response（contracts.py:744）與此 responsibility 的 semantic output **正面一致**

negative boundary
  ⚠️ 本群必須**最窄**：一寫進 eligibility 就會破壞 P3 對 fallback 的尺度限制，開始吃掉 R-02／R-03／R-04／R-08／R-09。

deliberate exclusions
  - ⛔ 不寫「判斷可執行哪些操作」
  - ⛔ 不寫「診斷為什麼不能操作」
  - ⛔ 不寫任何 eligibility
```

---

## `R-06`　（sealed from CG-ROW-3402）

```text
members        3402[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=general
owner          Knowledge（非空 answer ＋ reviewed content responsibility 即為 authority；⛔ 不要求另有 engine）
P3 identity    responsibility ＝「點退完成後何時／何條件產生帳單並進入結算」，⛔ 不是查某筆實值
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3402  summary：點退帳單 自動產生 費用結算
           reviewed row representation：點退完成後系統何時／在什麼條件下自動產生點退帳單，以及該帳單如何進入費用結算。
           answer（124 字）：點退完成後系統自動產生點退帳單，內容包含：（1）水電等未結費用：依點退時記錄的度數結算；（2）設施損壞賠償：依點退檢查結果列出的賠償金額；（3）其他費用：房東自訂的額外費用。點退帳單的到期日依合約設定或點退當天計算。帳單金額會與押金互抵，多退少補。
```

### CANONICAL VERDICT
```text
canonical_responsibility  說明點退完成後系統何時、在何種條件下自動產生點退帳單，以及該帳單如何進入費用結算。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - row-level reviewed retrieval_representation（R9 逐筆裁定）＝**高品質 evidence**，⛔ 非自動 canonical——本群幾乎逐字沿用，且沿用是**裁定結果**⛔ 非 migration rule
  - 3402 answer 提供內容佐證（費用組成／到期日／押金互抵）作為 content evidence
  - reviewed applicability=general；owner=Knowledge

negative boundary
  與 R-25 分界：R-06＝點退帳單**何時／如何產生並進入結算**；R-25＝**金額如何計算**。

deliberate exclusions
  - ⛔ 不枚舉水電／損壞賠償／自訂費用
  - ⛔ 不寫到期日細則
  - ⛔ 不寫押金多退少補細節
```

---

## `R-07`　（sealed from CG-ROW-3406）

```text
members        3406[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=general
owner          Knowledge（非空 answer ＋ reviewed content responsibility 即為 authority；⛔ 不要求另有 engine）
P3 identity    與 4640 有**既有** positive semantic partition：「取得方式」≠「某張收據實際金額」
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3406  summary：帳單收據 繳費證明 PDF 下載
           reviewed row representation：如何取得帳單收據／繳費證明：下載的位置與方式、收據可作為繳費證明、未繳費的帳單無法產生收據，以及收據與統一發票的區別。
           answer（130 字）：帳單繳費完成後可下載收據 PDF。下載方式：在帳單詳情頁面點選「下載收據」，系統會產生包含帳單編號、繳費日期、金額明細和付款方式等資訊的 PDF 收據。收據可供租客留存作為繳費證明。尚未繳費的帳單無法產生收據。若需要正式的統一發票，請參考發票開立功能另行處理。
```

### CANONICAL VERDICT
```text
canonical_responsibility  說明帳單收據／繳費證明的產生條件、取得位置與方式，以及其與統一發票的區別。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - row-level reviewed retrieval_representation（R9 逐筆裁定）＝**高品質 evidence**，⛔ 非自動 canonical——⚠️ 本群**不逐字沿用**：原句四項混了 identity 與內容明細
  - 「未繳費無法產生」上收為 **產生條件**
  - 3406 answer 提供下載方式與發票區別的內容佐證

negative boundary
  R-07 ＝ general acquisition／generation mechanism；⛔ 不查某一張收據實際收了多少錢（instance 屬 R-29）。這是 general／instance 的真正分界。

deliberate exclusions
  - ⛔ 「收據可作為繳費證明」屬內容 truth，⛔ 不逐項寫進 identity
```

---

## `R-08`　（sealed from CG-ROW-3491）

```text
members        3491[ANSWER_KNOWLEDGE/active], 3511[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          rag-orchestrator/services/jgb/contracts.py:161::check_can_move_in
P3 identity    canonical responsibility：判斷／診斷某份合約能否點交，以及不能的原因。
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3491  summary：合約為什麼不能點交
           answer（24 字）：合約點交按鈕灰色時，需查詢合約資料判斷具體原因。
row 3511  summary：合約的點交/點退/提前解約/續約按鈕是否可用
           answer（40 字）：需查合約狀態欄位，逐一檢查各操作的前置條件。前端只顯示按鈕可不可按，不顯示原因。
```

### 已有業主陳述（P3 identity ruling 內明示）
```text
判斷／診斷某份合約能否點交，以及不能的原因。
⚠️ 仍需一次確認：這句是否即為 responsibility 的 canonical contract。
```

### ⚠️ 規約② 適用
```text
本責任有多個 member ⇒ canonical 必須描述**共同責任**，
⛔ 不得偏向任一 member（例：3365+4420 ⛔ 不得偏向 form row 或 action row 任一邊）。
```

### CANONICAL VERDICT
```text
canonical_responsibility  判斷某份合約目前是否符合點交條件，並診斷無法點交的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 identity ruling
  - check_can_move_in（contracts.py:161）deterministic owner
  - 3491 answer「合約點交按鈕灰色時，需查詢合約資料判斷具體原因」
  - 3511 **只**支持它確實涵蓋此 responsibility——⛔ 不採「各操作」的 composite wording

deliberate exclusions
  - ⛔ 不寫「檢查各操作」
  - ⛔ 不寫前端按鈕是否顯示原因
```

---

## `R-09`　（sealed from CG-ROW-3492）

```text
members        3492[ANSWER_KNOWLEDGE/active], 3511[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          rag-orchestrator/services/jgb/contracts.py:203::check_can_move_out
P3 identity    canonical responsibility：判斷／診斷某份合約能否點退，以及不能的原因。
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3492  summary：合約為什麼不能點退
           answer（46 字）：合約點退按鈕灰色時，需查詢合約資料判斷原因。注意：不需先點交也可以點退；合約過期後仍可點退。
row 3511  summary：合約的點交/點退/提前解約/續約按鈕是否可用
           answer（40 字）：需查合約狀態欄位，逐一檢查各操作的前置條件。前端只顯示按鈕可不可按，不顯示原因。
```

### 已有業主陳述（P3 identity ruling 內明示）
```text
判斷／診斷某份合約能否點退，以及不能的原因。
⚠️ 仍需一次確認：這句是否即為 responsibility 的 canonical contract。
```

### ⚠️ 規約② 適用
```text
本責任有多個 member ⇒ canonical 必須描述**共同責任**，
⛔ 不得偏向任一 member（例：3365+4420 ⛔ 不得偏向 form row 或 action row 任一邊）。
```

### CANONICAL VERDICT
```text
canonical_responsibility  判斷某份合約目前是否符合點退條件，並診斷無法點退的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 identity ruling
  - check_can_move_out（contracts.py:203）deterministic owner
  - 3492 answer「合約點退按鈕灰色時，需查詢合約資料判斷原因」
  - 3511 只支持涵蓋關係，⛔ 不採 composite wording

deliberate exclusions
  - ⛔ 3492 的「不需先點交也可點退／合約過期仍可點退」是 responsibility **內**的產品規則 evidence，⛔ 不是 identity 本身——放進去會讓 canonical 從「我要解決什麼問題」退化成「目前實作有哪些規則」
```

---

## `R-10`　（sealed from CG-ROW-3495）

```text
members        3495[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          bill_diagnosis ／ rag-orchestrator/services/jgb/bills.py::_diagnose_cannot_send
P3 identity    有**可區分的** deterministic sub-responsibility（具名分支 B01）
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3495  summary：帳單為什麼發不出去
           reviewed row representation：診斷某一筆帳單為什麼無法發送給租客，包含發送失敗、寄不出、按發送無反應等情形。
           answer（28 字）：帳單無法發送時，常見原因：狀態不對、金額未填、度數未填。
```

### CANONICAL VERDICT
```text
canonical_responsibility  診斷特定帳單無法發送給租客的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - row-level reviewed retrieval_representation（R9 逐筆裁定）＝**高品質 evidence**，⛔ 非自動 canonical
  - _diagnose_cannot_send（bills.py:463）deterministic owner
  - ⚠️ 原句的「發送失敗／寄不出／按發送無反應」是 **utterance／symptom variants**，⛔ 不是規則枚舉——與 α-C1 禁止的是不同類

deliberate exclusions
  - ⛔ 不列舉問法變體——問法變體是 recall evidence，**canonical ⛔ 不需要兼任 synonym dictionary**
```

---

## `R-11`　（sealed from CG-ROW-3496）

```text
members        3496[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          bill_diagnosis ／ rag-orchestrator/services/jgb/bills.py::_diagnose_cannot_cancel
P3 identity    有**可區分的** deterministic sub-responsibility（具名分支 B02）
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3496  summary：帳單為什麼取消不了
           reviewed row representation：診斷某一筆帳單為什麼無法取消或作廢，包含取消按鈕不可用、取消時失敗等情形，以及可取消所需的帳單狀態條件。
           answer（34 字）：帳單取消需狀態為「應到帳」或「排定發送」。其他狀態的帳單不支援取消。
```

### CANONICAL VERDICT
```text
canonical_responsibility  判斷特定帳單目前是否可取消／作廢，並診斷無法取消的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - row-level reviewed retrieval_representation（R9 逐筆裁定）＝**高品質 evidence**，⛔ 非自動 canonical——⚠️ 本群**需修**：原句尾端「可取消所需的帳單狀態條件」屬 capability rule
  - _diagnose_cannot_cancel（bills.py:514）deterministic owner
  - 與 α eligibility responsibility **完全同尺**（α-C1）

deliberate exclusions
  - ⛔ 狀態條件留在 _diagnose_cannot_cancel 的 capability／content，⛔ 不進 canonical
```

---

## `R-12`　（sealed from CG-ROW-3497）

```text
members        3497[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          payment_flow::_diagnose_payment_not_reflected（rag-orchestrator/services/jgb/payments.py::_diagnose_payment_not_reflected）
P3 identity    named branch 本身即**正面** identity evidence——⛔ 不是因為 row wording 看起來不同，而是 production deterministic execution **已經**把不同問項分到不同 sub-capability
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3497  summary：已付款但帳單狀態沒有更新
           answer（34 字）：已付款但帳單未更新是最常見的客服問題。原因完全藏在後端，用戶看不到。
```

### CANONICAL VERDICT
```text
canonical_responsibility  診斷特定款項已完成支付，但帳單付款狀態尚未同步更新的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 confirmed responsibility
  - _diagnose_payment_not_reflected（payments.py:50，P01）
  - summary「已付款但帳單狀態沒有更新」
  - ⚠️ γ-C4：本群 answer 為**佔位型**，⛔ 不承擔主要證據角色；identity 由 P3 confirmed responsibility ＋ summary ＋ 具名 deterministic branch 支撐

deliberate exclusions
  - ⛔「最常見客服問題」
  - ⛔「原因藏在後端」——那些只是問題描述／調查方式
```

---

## `R-14`　（sealed from CG-ROW-3499）

```text
members        3499[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          bill_diagnosis ／ rag-orchestrator/services/jgb/bills.py:602::_diagnose_manual_complete
P3 identity    「特定帳單手動到帳／標記已收款失敗」有**獨立 deterministic sub-intent**
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3499  summary：帳單手動到帳或標記已收款失敗
           reviewed row representation：查詢／診斷特定帳單手動到帳失敗、無法完成手動入帳的原因。
           answer（22 字）：手動到帳失敗時前端會顯示錯誤訊息，常見三種。
```

### CANONICAL VERDICT
```text
canonical_responsibility  診斷特定帳單手動到帳／標記已收款失敗的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - row-level reviewed retrieval_representation（R9 逐筆裁定）＝**高品質 evidence**，⛔ 非自動 canonical——本群為 **row representation 經人工 review 後幾乎原樣批准的正例**（只做小幅去重）
  - _diagnose_manual_complete（bills.py:602）＋ 可達 dispatch
```

---

## `R-15`　（sealed from CG-ROW-3500）

```text
members        3500[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          payment_flow::_diagnose_credit_card_failure（rag-orchestrator/services/jgb/payments.py::_diagnose_credit_card_failure）
P3 identity    named branch 本身即**正面** identity evidence——⛔ 不是因為 row wording 看起來不同，而是 production deterministic execution **已經**把不同問項分到不同 sub-capability
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3500  summary：信用卡付款失敗
           answer（19 字）：信用卡付款失敗的具體原因需查後端紀錄。
```

### CANONICAL VERDICT
```text
canonical_responsibility  診斷特定信用卡單次付款失敗的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 confirmed responsibility
  - _diagnose_credit_card_failure（payments.py:85，P02）
  - ⚠️「**單次**」是與 R-16 正交的 defining boundary，⛔ 不是額外細節（γ-C5）
  - ⚠️ γ-C4：本群 answer 為**佔位型**，⛔ 不承擔主要證據角色；identity 由 P3 confirmed responsibility ＋ summary ＋ 具名 deterministic branch 支撐

negative boundary
  與 R-16 的機器可讀分界：R-15＝信用卡「單次付款」失敗；R-16＝「週期性自動扣款／自動付款」失敗。
```

---

## `R-16`　（sealed from CG-ROW-3501）

```text
members        3501[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          diagnose_payment_logs ／ rag-orchestrator/services/jgb/payments.py:120::_diagnose_auto_pay_failure
P3 identity    與 C-① 六群同形：具名分支 ＋ 可達 dispatch
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3501  summary：信用卡自動扣款失敗
           answer（35 字）：自動扣款失敗時租客會收到 email 通知。需查 DB 確認具體原因。
```

### CANONICAL VERDICT
```text
canonical_responsibility  診斷信用卡週期性自動扣款／自動付款失敗的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 confirmed responsibility
  - _diagnose_auto_pay_failure（payments.py:120）
  - ⚠️ γ-C5：與 R-15 的主要差異是**交易模式**，canonical 必須保留該模式差異

negative boundary
  ⛔ 不得與 R-15 都縮成「信用卡付款失敗」。

deliberate exclusions
  - ⛔ email notification 不進 canonical
  - ⛔ 「查 DB」不進 canonical
```

---

## `R-17`　（sealed from CG-ROW-3502）

```text
members        3502[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          diagnose_bill ／ rag-orchestrator/services/jgb/bills.py:625::_diagnose_atm_expired
P3 identity    與 C-① 六群同形：具名分支 ＋ 可達 dispatch
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3502  summary：虛擬帳號過期或轉帳失敗
           answer（232 字）：虛擬帳號無法繳納或轉帳失敗的排查順序：一、繳費資訊疑慮（帳號失效或有誤）——把帳單收回重新發送，重發會刷新繳費資訊（效期依金流商而異：國泰 ATM 無失效時限、藍新 180 天、永豐約 7 天）；二、建立一張租金 1 元的測試帳單請租客繳看看，並嘗試不同銀行——一元可繳表示通道正常；三、若一元可繳但大金額不行，可能是達
```

### CANONICAL VERDICT
```text
canonical_responsibility  診斷特定帳單的虛擬帳號失效、過期或轉帳失敗的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 confirmed responsibility
  - _diagnose_atm_expired（bills.py:625）＋ _ATM_KEYWORDS dispatch
  - 3502 answer（232 字）作為 content evidence

deliberate exclusions
  - ⛔ 國泰／藍新／永豐等金流商名稱
  - ⛔ 180 天／7 天等效期
  - ⛔ 1 元測試帳單
  - ⛔ 月收款上限、額度調整天數——全部是 γ-C1 標準排除項
  - ⛔ 不寫「提供處理方式」：目前 confirmed identity 是 **diagnosis**；answer 的 remediation 豐富 ⛔ 不代表 responsibility 要擴成 troubleshooting workflow owner
```

---

## `R-18`　（sealed from CG-ROW-3503）

```text
members        3503[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          invoice::_diagnose_issue_failure（rag-orchestrator/services/jgb/invoices.py::_diagnose_issue_failure）
P3 identity    named branch 本身即**正面** identity evidence——⛔ 不是因為 row wording 看起來不同，而是 production deterministic execution **已經**把不同問項分到不同 sub-capability
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3503  summary：發票為什麼沒有開出來
           answer（23 字）：帳單顯示「尚未開立」時，需查多層條件判斷原因。
```

### CANONICAL VERDICT
```text
canonical_responsibility  診斷特定發票未成功開立的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 confirmed responsibility
  - _diagnose_issue_failure（invoices.py，I01）
  - ⚠️ γ-C4：本群 answer 為**佔位型**，⛔ 不承擔主要證據角色；identity 由 P3 confirmed responsibility ＋ summary ＋ 具名 deterministic branch 支撐

deliberate exclusions
  - ⛔ 不寫「多層條件」——implementation／problem-solving detail
```

---

## `R-19`　（sealed from CG-ROW-3504）

```text
members        3504[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          invoice::_diagnose_invalid_failure（rag-orchestrator/services/jgb/invoices.py::_diagnose_invalid_failure）
P3 identity    named branch 本身即**正面** identity evidence——⛔ 不是因為 row wording 看起來不同，而是 production deterministic execution **已經**把不同問項分到不同 sub-capability
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3504  summary：發票為什麼作廢不了
           answer（18 字）：發票作廢需確認狀態和 API 回應。
```

### CANONICAL VERDICT
```text
canonical_responsibility  診斷特定發票無法作廢的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 confirmed responsibility
  - _diagnose_invalid_failure（invoices.py，I02）
  - ⚠️ γ-C4：本群 answer 為**佔位型**，⛔ 不承擔主要證據角色；identity 由 P3 confirmed responsibility ＋ summary ＋ 具名 deterministic branch 支撐

deliberate exclusions
  - ⛔ 不寫「狀態」「API 回應」——它們是診斷 facts，⛔ 不是責任 identity
```

---

## `R-20`　（sealed from CG-ROW-3505）

```text
members        3505[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          subscription::_diagnose_cannot_add_estate（rag-orchestrator/services/jgb/subscription.py::_diagnose_cannot_add_estate）
P3 identity    named branch 本身即**正面** identity evidence——⛔ 不是因為 row wording 看起來不同，而是 production deterministic execution **已經**把不同問項分到不同 sub-capability
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3505  summary：為什麼不能新增物件
           answer（131 字）：無法新增物件最常見兩個原因：（1）訂閱方案的物件額度已滿——系統會提示方案已滿，可升級方案、加購物件額度，或刪除/下架不再使用的物件釋放額度；目前用量可在「訂閱方案」頁查看。（2）帳號權限不足——新增物件需要對應的物件管理權限，請團隊管理者確認你的角色權限設定。
```

### CANONICAL VERDICT
```text
canonical_responsibility  診斷目前無法新增物件的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 confirmed responsibility
  - _diagnose_cannot_add_estate（subscription.py，E01）

deliberate exclusions
  - ⛔ 不寫「訂閱額度已滿」「權限不足」——那是目前 capability 的原因枚舉；未來增加第三種原因時 canonical ⛔ 不應因此改版
```

---

## `R-21`　（sealed from CG-ROW-3506）

```text
members        3506[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          subscription::_diagnose_estates_delisted（rag-orchestrator/services/jgb/subscription.py::_diagnose_estates_delisted）
P3 identity    named branch 本身即**正面** identity evidence——⛔ 不是因為 row wording 看起來不同，而是 production deterministic execution **已經**把不同問項分到不同 sub-capability
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3506  summary：物件為什麼突然全部下架
           answer（126 字）：物件突然全部下架，最常見的原因是訂閱續約扣款失敗——方案失效時系統會將物件自動下架。請到「訂閱方案」頁確認方案狀態與付款方式，完成續約後再將物件重新上架。若方案正常但個別物件被下架，多半是修改資料後必填欄位驗證失敗導致自動下架，補齊欄位後重新刊登即可。
```

### CANONICAL VERDICT
```text
canonical_responsibility  診斷既有物件突然被下架或停止刊登的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 confirmed responsibility
  - _diagnose_estates_delisted（subscription.py，E02）

deliberate exclusions
  - ⛔ 不寫訂閱續約扣款失敗／方案失效／必填欄位驗證失敗
```

---

## `R-22`　（sealed from CG-ROW-3507）

```text
members        3507[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          estate-status ／ rag-orchestrator/services/jgb/estates.py:33::build_estate_status_facts
P3 identity    claimed responsibility「這個物件為什麼不能建約」有**非常直接的** deterministic capability evidence，⛔ 非推測
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3507  summary：物件為什麼不能建立合約
           answer（147 字）：物件無法建立合約，先檢查兩個前提：（1）物件必須是「刊登中」狀態——未刊登的物件無法建約，請先完成刊登；（2）必填欄位齊備（名稱、用途、建築類型、樓層、面積、租金與地址等）——缺任何一欄都會擋建約。想知道特定物件到底卡在哪，可以直接問「這個物件為什麼不能建約」，系統會查該物件目前還缺哪些欄位。
```

### CANONICAL VERDICT
```text
canonical_responsibility  診斷特定物件目前為何不符合建立合約的條件。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 confirmed responsibility（owner = estates.py:33::build_estate_status_facts）
  - ⚠️ **P-C9 完全生效**：canonical 描述的是**已確認的 responsibility truth**，⛔ 不是目前錯接的 jgb_contract_query

negative boundary
  capability_alignment=WRONG_EXECUTION_BINDING_CONFIRMED 繼續留在**正交 diagnostic axis**，⛔ 不污染 canonical。

deliberate exclusions
  - ⛔ 不寫 jgb_contract_query
  - ⛔ 不寫目前 fallback 行為
  - ⛔ 不列舉「刊登中／必填欄位齊備」——capability rules
```

---

## `R-23`　（sealed from CG-ROW-3508）

```text
members        3508[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          rag-orchestrator/services/jgb/iot.py::diagnose_iot
P3 identity    具名診斷引擎存在，符合 P-C1（deterministic applicability 是正面 authoritative declaration）
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3508  summary：IoT 廠商帳號綁定失敗
           answer（28 字）：帳號已被綁定時，需查 DB 確認被哪個 role 綁走。
```

### CANONICAL VERDICT
```text
canonical_responsibility  診斷 IoT 廠商帳號無法完成綁定的原因。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 confirmed responsibility
  - services/jgb/iot.py::diagnose_iot（formatter 專屬分支）
  - ⚠️ γ-C4：本群 answer 為**佔位型**，⛔ 不承擔主要證據角色；identity 由 P3 confirmed responsibility ＋ summary ＋ 具名 deterministic branch 支撐

deliberate exclusions
  - ⛔ 不寫 DB、role
  - ⛔ ⛔ 不把「已被別人綁定」寫成唯一原因——目前 answer 只呈現 diagnose_iot 的其中一種 diagnosis outcome
```

---

## `R-24`　（sealed from CG-ROW-3514）

```text
members        3514[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          jgb_tenant_summary ＋ rag-orchestrator/services/jgb_response_formatter.py::_format_tenant_summary
P3 identity    專屬 deterministic capability path 已成立——⚠️ 依 P-C5，「函式名沒有 diagnose」⛔ 不構成降格理由；要驗的是責任是否有 deterministic implementation
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3514  summary：查詢租客概況 合約帳單修繕
           ⚠️ 無 representation、answer 空 ⇒ 本列提供不了文字證據
```

### CANONICAL VERDICT
```text
canonical_responsibility  查詢特定租客的整體概況，包括其合約、帳單與修繕資訊。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 confirmed responsibility
  - jgb_tenant_summary ＋ _format_tenant_summary 專屬 path
  - ⚠️ **γ-C6 第一個正例**：「合約／帳單／修繕」⛔ 不是 API 欄位枚舉、⛔ 不是 formatter status fields、⛔ 不是規則細項、⛔ 不是 example——它們就是 _format_tenant_summary 代表的**跨域摘要範圍**，即 responsibility 的 semantic coverage boundary

deliberate exclusions
  - ⛔ 不得縮成「查詢租客概況」——那會失去目前**唯一**能證明此 responsibility scope 的 semantic boundary
```

---

## `R-25`　（sealed from CG-ROW-3519）

```text
members        3519[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=general
owner          Knowledge（非空 answer ＋ reviewed content responsibility 即為 authority；⛔ 不要求另有 engine）
P3 identity    與 4657 的「查實際點退帳單」已有正面書面分工
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3519  summary：點退帳單金額計算 押金結算
           reviewed row representation：點退帳單金額如何計算：加總哪些結算項目、如何扣抵押金，以及金額為正負時分別代表退款或需補繳差額。
           answer（190 字）：點退帳單是租客同意點退後系統自動產生的，金額算法是：水電費等結算費用，加上設備損壞賠償和違約金，再扣掉應退還的押金。帳單總額是負數就代表要退錢給租客，是正數則代表押金扣完還不夠，租客需要補繳差額。舉例：押金 20,000 元、水電結算 700 元、設備賠償 5,000 元，帳單總額就是 -14,300 元，即退還租客 
```

### CANONICAL VERDICT
```text
canonical_responsibility  說明點退帳單金額與押金結算的計算規則，以及結算差額如何解讀。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - row-level reviewed retrieval_representation（R9 逐筆裁定）＝**高品質 evidence**，⛔ 非自動 canonical
  - 3519 answer（190+ 字）承載算式與正負差額解讀
  - 保留 responsibility 的兩個 defining semantic parts：①怎麼算 ②算完差額代表什麼
  - reviewed applicability=general；owner=Knowledge

negative boundary
  ⛔ 不負責點退帳單何時自動產生 → R-06；⛔ 不查某份合約實際點退多少錢 → R-31。

deliberate exclusions
  - ⛔ 不把所有結算項目逐一列進 contract
```

---

## `R-26`　（sealed from CG-ROW-3531）

```text
members        3531[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=general
owner          Knowledge（非空 answer ＋ reviewed content responsibility 即為 authority）
P3 identity    canonical responsibility：付款後結算型延遲金的產生機制、適用條件與計算規則
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3531  summary：滯納金帳單產生 付款後結算規則
           answer（231 字）：系統的滯納金有兩種機制，依團隊採用而定：（一）延遲金（付款後結算）：租客實際付款當下若逾期，以「租金 ×（實際付款日 − 繳費期限 − 緩衝天數）× 費率」結算，開立一張獨立的延遲金帳單（到期日為產生當日），帳單附完整計算過程備註；（二）排程滯納金（對逾期未付款的帳單開單）：每日排程檢查逾期帳單並依團隊設定開立滯納金帳
```

### 已有業主陳述（P3 identity ruling 內明示）
```text
付款後結算型延遲金的產生機制、適用條件與計算規則
⚠️ 仍需一次確認：這句是否即為 responsibility 的 canonical contract。
```

### CANONICAL VERDICT
```text
canonical_responsibility  說明付款後結算型延遲金的產生條件、計算方式與結算規則。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 identity ruling（「適用條件」→「產生條件」只是讓 semantic object 更明確，⛔ 未改責任）
  - 3531 answer（231 字）承載該機制的規則、公式與適用條件
  - reviewed applicability=general；owner=Knowledge

negative boundary
  不負責比較不同滯納金客製版本；版本間差異屬 R-27。
```

---

## `R-27`　（sealed from CG-ROW-3532）

```text
members        3532[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=general
owner          Knowledge（非空 answer ＋ reviewed content responsibility 即為 authority）
P3 identity    canonical responsibility：滯納金客製計算版本的機制差異（延遲金／階梯式／固定金額等）
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3532  summary：滯納金客製版本 固定金額階梯式
           answer（233 字）：滯納金的客製版本行為差異：（1）延遲金版（付款後結算）：百分比計算、帳單附三行式計算過程備註、到期日為產生當日；（2）階梯式版（排程對未付款開單）：以租金乘固定費率（不乘逾期天數），逾期超過門檻（預設 30 天）改用加重費率，每張帳單最多開兩筆，到期日為合約迄日；（3）固定金額版（排程對未付款開單）：逾期滿一定天數（如
```

### 已有業主陳述（P3 identity ruling 內明示）
```text
滯納金客製計算版本的機制差異（延遲金／階梯式／固定金額等）
⚠️ 仍需一次確認：這句是否即為 responsibility 的 canonical contract。
```

### CANONICAL VERDICT
```text
canonical_responsibility  比較滯納金不同客製計算版本，包括付款後結算延遲金、階梯式與固定金額版本的機制與計算差異。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - P3 identity ruling
  - 3532 answer（233 字）承載跨版本差異
  - reviewed applicability=general；owner=Knowledge
  - 核心動詞必須是**比較不同版本**——這樣才與 R-26 正交

negative boundary
  不承接特定帳單／合約的實際滯納金查值或診斷；instance responsibility 屬 R-28。若問題只要求付款後結算型延遲金**自身**的詳細規則、而非版本比較，責任屬 R-26。
```

---

## `R-28`　（sealed from CG-ALIAS-04）

```text
members        3939[ENTRY_ALIAS/active], 3940[ENTRY_ALIAS/active]
applicability  declaration_status=reviewed／value=instance
owner          late_fee Face ／ services/jgb/bills.py::build_late_fee_facts
facet          滯納金
P3 identity    H2 VARIANTS_BY_DESIGN
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 3939  summary：滯納金怎麼收這麼多
           ⚠️ 無 representation、answer 空 ⇒ 本列提供不了文字證據
row 3940  summary：這筆延遲金是怎麼算的
           ⚠️ 無 representation、answer 空 ⇒ 本列提供不了文字證據
```

### ⚠️ 規約② 適用
```text
本責任有多個 member ⇒ canonical 必須描述**共同責任**，
⛔ 不得偏向任一 member（例：3365+4420 ⛔ 不得偏向 form row 或 action row 任一邊）。
```

### CANONICAL VERDICT
```text
canonical_responsibility  依特定帳單或合約的實際資料，查明該筆滯納金／延遲金為何產生、實際收取金額及其計算依據。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-29

review basis（此句實際依賴的證據）
  - H2 VARIANTS_BY_DESIGN：3939／3940 是同一 facet responsibility 的不同 utterance entry variants
  - P3 identity：兩列已確認同一 responsibility
  - 兩筆 positive applicability declaration：reviewed／instance
  - sole owner：late_fee Face／services/jgb/bills.py::build_late_fee_facts
  - T1 ＋ Step 1/2：B 已成 capability superset 且 late-fee instance ownership = B ONLY
  - builder 對特定 contract／late-fee bill 取得實際設定、金額、狀態、付款時間與結算備註⇒ 支持「依實際資料查明」

negative boundary
  MUST NOT generalize to system-wide late-fee mechanism explanation; R-26 / R-27 own the general mechanism responsibilities.

deliberate exclusions
  - ⛔ 明確排除 builder 內的**一般機制文字**（兩機制並述／階梯式／固定金額版本）作為 responsibility identity evidence——那是 R-26／R-27 的 general responsibility
  - ⛔ 不把 builder 的每一項 fact（付款時間／到帳時間／目前狀態／緩衝天數／費率／結算備註）升格成 canonical wording——它們是**支撐 instance diagnosis 的 deterministic facts**
  - ⛔ 開頭的「依特定帳單或合約的實際資料」是把它鎖在 instance 的關鍵，⛔ 不得退化成「說明滯納金怎麼計算」
```

---

## `R-29`　（sealed from CG-ROW-4640）

```text
members        4640[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          bill_diagnosis 的 receipt-amount deterministic capability（B05）
P3 identity    與 3406 的 general download responsibility 有正面分工，且 B05 取的是 runtime actual value
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 4640  summary：帳單收據金額 收據多少錢
           reviewed row representation：查詢某一張收據的實際金額，例如某筆帳單的收據實收多少錢。
```

### CANONICAL VERDICT
```text
canonical_responsibility  查詢特定收據的實際收款金額。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - row-level reviewed retrieval_representation（R9 逐筆裁定）＝**高品質 evidence**，⛔ 非自動 canonical——原句尾端「例如某筆帳單的收據實收多少錢」只是 example，已剪
  - B05 receipt-amount deterministic capability
  - reviewed applicability=instance

negative boundary
  與 R-07 形成最乾淨分工：R-07＝怎麼取得／何時產生；R-29＝這一張實際多少錢。

deliberate exclusions
  - ⛔ 不留 example
```

---

## `R-30`　（sealed from CG-ROW-4656）

```text
members        4656[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          bill_diagnosis ／ rag-orchestrator/services/jgb/bills.py::_format_bill_status 路徑
P3 identity    identity 由 `bill_ref` referent ＋ status capability 定義
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 4656  summary：查帳單 帳單編號查詢
           reviewed row representation：找出並查詢某一筆帳單目前的狀態，包括是否已繳費、是否已寄出或仍為草稿、到期情形，以及該筆帳單的現況。
```

### CANONICAL VERDICT
```text
canonical_responsibility  查詢特定帳單目前的實際狀態。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - row-level reviewed retrieval_representation（R9 逐筆裁定）＝**高品質 evidence**，⛔ 非自動 canonical——⚠️ 狀態欄位枚舉全部剪掉
  - _format_bill_status（bills.py:663）
  - 理由與 R-05 完全相同：那些是 formatter 能提供的 status dimensions，⛔ 不是 responsibility identity

negative boundary
  與 R-31 分界：R-30 的**特定 bill 已確定**；R-31 以 contract 為起點，須先辨識正確的點退帳單。

deliberate exclusions
  - ⛔ 不列：是否繳費／是否寄出／草稿／到期情形
```

---

## `R-31`　（sealed from CG-ROW-4657）

```text
members        4657[ANSWER_KNOWLEDGE/active]
applicability  declaration_status=reviewed／value=instance
owner          POINT_REFUND_BILL_SELECTION ＋ downstream bill facts
P3 identity    defining operation 含「由合約找出 type=2 點退帳單」，⛔ 不是單純既知 bill_ref 的狀態查詢
```

### proposal evidence ⚠️ ⛔ 不得自動升格為 canonical authority
```text
row 4657  summary：合約的點退帳單金額 查點退金額
           reviewed row representation：查詢某份合約的點退帳單，包含該筆點退帳單的實際金額與目前狀態。
```

### CANONICAL VERDICT
```text
canonical_responsibility  依指定合約找出其點退帳單，並查詢該筆點退帳單的實際金額與目前狀態。
verdict                   **APPROVED**
status                    REVIEWED
reviewer                  業主   reviewed_at 2026-08-30

review basis（此句實際依賴的證據）
  - row-level reviewed retrieval_representation（R9 逐筆裁定）＝**高品質 evidence**，⛔ 非自動 canonical——⚠️ 原句**未寫** selection prerequisite，本群補上（產品語義形式）
  - P3 mutation 證據：select_point_refund 的 six guards ＋ guard 6（拿掉 type filter／改回 data[0] 測試必須紅）⇒ selection 是 identity 的必要差異
  - ⚠️ 拿掉前半句會把兩個已被 deterministic capability 證明不同的 responsibilities 寫得幾乎一樣

negative boundary
  與 R-30 分界：R-30 特定 bill 已確定 → 查 status；R-31 contract 是起點 → 先辨識正確的點退帳單 → 再查 amount／status。

deliberate exclusions
  - ⛔ 不寫 `type = 2` 這類**實作欄位**——寫的是**產品語義** prerequisite
```

---
