# Level-A 10 rows representation —— review status（業主裁定 2026-08-29）

⚠️ `NOT_REVIEWED_BY_OWNER` **不是** UNKNOWN semantic truth，只是 review workflow 未完成。
⛔ 不得寫成資料層的 UNKNOWN。

| row | status |
|---|---|
| 3402 | `APPROVED`（收窄版） |
| 3406 | `APPROVED` |
| 3495 | `APPROVED_WITH_EVIDENCE_BOUNDARY` |
| 3496 | `APPROVED` |
| 3498 | `APPROVED_AFTER_TEXT_REVISION`（收窄） |
| 3499 | `APPROVED`（responsibility-level）＋另列 `KNOWLEDGE_CONTENT_INCOMPLETE` |
| 3519 | `APPROVED`（⛔ **不收窄**） |
| 4640 | `APPROVED` |
| 4656 | `APPROVED` |
| 4657 | ⛔ `BLOCKED_BY_CAPABILITY_CONTRACT` |

⇒ **9 筆完成 review，1 筆 capability blocker。**

---

## ⚠️ 先定案的裁量規則：**兩類 row 不能用同一把尺**

```text
general row  → representation 對齊 **Knowledge answer responsibility**
instance row → representation 對齊 **Face／downstream capability responsibility**
```

3406／3519 已裁為 **general**，其正確產品路徑本就是「由 Knowledge 本身回答」，
⛔ 不是交給 `bill_diagnosis` grounding。
⇒ **它們不該因為 `_format_bill_status` 沒有那些能力而收窄。**
這正是 P1 已拆出的 applicability 差異的下游後果。

### ⚠️ 3519 為什麼不能照 3499 的邏輯收窄（形狀不同）

```text
3519：frozen answer **明文**寫了「總額負數＝退錢給租客／正數＝需補繳差額」
     → representation 只是**表示既有 answer truth** ✅
3499：answer 說「常見三種」但**三種本身沒寫出來**
     → representation 若補齊，就是**創造 knowledge truth** ❌
```
判準是 answer 裡**有沒有**，⛔ 不是「寫得完不完整」。

---

## 逐筆定稿文字（APPROVED 9 筆）

```text
3402  點退完成後系統何時／在什麼條件下自動產生點退帳單，
      以及該帳單如何進入費用結算。

3406  如何取得帳單收據／繳費證明：下載的位置與方式、收據可作為繳費證明、
      未繳費的帳單無法產生收據，以及收據與統一發票的區別。

3495  診斷某一筆帳單為什麼無法發送給租客，包含發送失敗、寄不出、
      按發送無反應等情形。
      ⚠️ evidence boundary：發送失敗／寄不出／按發送無反應屬**同一 operational
      failure family**，可涵蓋；⛔ 不得列出 Face 尚未證明能診斷的具體原因。

3496  診斷某一筆帳單為什麼無法取消或作廢，包含取消按鈕不可用、取消時失敗等情形，
      以及可取消所需的帳單狀態條件。

3498  診斷某一筆帳單為什麼被收取逾期費、延遲金或滯納金，
      以及該筆費用的計算依據與金額如何得出。
      ⚠️ 保留同義詞「滯納金」（R7-B #166 因該詞落空）；
      ⛔ **刪除**「計費起算的日期認定與緩衝天數」——frozen answer 只證公式，
      尚不足以證 Face 對這兩項有正式責任。

3499  查詢／診斷特定帳單手動到帳失敗、無法完成手動入帳的原因。

3519  點退帳單金額如何計算：加總哪些結算項目、如何扣抵押金，
      以及金額為正負時分別代表退款或需補繳差額。
      ⚠️ ⛔ **不收窄**——正負語義是 frozen answer 明文，屬這筆 general row 的責任。

4640  查詢某一張收據的實際金額，例如某筆帳單的收據實收多少錢。

4656  找出並查詢某一筆帳單目前的狀態，包括是否已繳費、是否已寄出或仍為草稿、
      到期情形，以及該筆帳單的現況。
      ⚠️ 這正是 R7-C 證明缺失的 contract。
```

---

## 3402 —— 收窄後定稿

裁示：`retrieval_representation` 描述 **row 承接的 intent**，⛔ 不是把 answer 裡
所有相關知識濃縮進去；否則會從「representation 不足」擺到另一端＝**semantic
envelope 膨脹**。

```text
定稿：點退完成後系統何時／在什麼條件下自動產生點退帳單，
     以及該帳單如何進入費用結算。
⛔ 刪除：一般帳單繳費期限／到期日規則
```

## 3499 —— 責任層通過；⛔ 不得替 answer 發明內容

```text
定稿：查詢／診斷特定帳單手動到帳失敗、無法完成手動入帳的原因。
⛔ 不得寫成：手動到帳失敗常見原因包括 A／B／C
   （除非 A/B/C 已由 downstream capability 或其他 authoritative contract 證明）
```
⇒ 兩件事分開：
```text
3499 retrieval representation      可先獨立成立
3499 answer content completeness   另列 defect（KNOWLEDGE_CONTENT_INCOMPLETE）
```
「answer 不完整」⛔ 不能反過來阻止 retrieval 表達它真正負責的 semantic responsibility；
但 retrieval 也⛔不能替 knowledge content 發明答案。

---

## 4657 —— HOLD，且**理由與先前理解不同**

裁示：不批准它宣告「查實際點退金額」，除非先證明能力真能提供那個值。
以下為實查所得的 machine evidence。

### ✅ 可證的部分

```text
金額**有**暴露：_format_bill_status（services/jgb/bills.py）
  total = _bill_amount_due(bill) → bill["total"]
  輸出 "• 金額：NT$ …"，並逐項列出 details[].total_price
上游 payload **有** type 欄位：JgbMockTransport.MAPPING["type"] = {2: "點退", …}
  （鏡射 BillApiController:173-197）
合約入口**有**：對話規則明文「沒有編號時可用合約編號或物件名稱」
```
⇒ 「金額拿不到」**不成立**——先前把 4657 的病灶說成「無點退專用分支」，
   ⚠️ 那句話為真但**不是**binding constraint。

### ⛔ 不可證的部分（真正的 blocker：**選取**，不是金額）

```text
face_bill_response（bills.py）對多列的處理是 **row = data[0]**
  —— 註解寫明「list 正規化為第一列」
⇒ 給定合約時，系統 ground 的是**第一列**帳單，⛔ 不是「該合約的點退帳單」
⇒ _format_bill_status ⛔ **不讀 type** ⇒ 輸出從不說明「這是不是點退帳單」
⇒ 對話規則承諾的「系統會列該合約的帳單候選」，**在帳單 face 路徑上找不到實作**
```

**否定結論的三道防線**（依 2026-08-24 定案）：
```text
正對照   同一組搜尋在修繕域確實找到多候選機制
         （services/jgb/repair_prefill.py 的 candidates / _classification_candidates）
         ⇒ 搜尋形狀有效，不是工具壞了
目標搜尋 bills.py 的多列處理只有一處：`row = data[0]`
對照預期 若存在候選列表，應出現與 repair_prefill 同形狀的 candidates 結構——未出現
```

### ⚠️ 更正：前一版對 blocker 的描述有誤（2026-08-29 同日更正）

```text
❌ 前一版寫：「對話規則承諾的『列出該合約的帳單候選』**查無實作**」
✅ 實況：候選列表在 conversational_engine 有完整實作
        （result_mapping／label_fields／candidate_cap／skip_refine；
         >1 列時引擎直接回 ask 列候選）
⇒ face_bill_response 的 `data[0]` 拿到的是**已收斂的單列**，⛔ 不是「任取第一筆」
```

**誤判成因**：否定結論的搜尋只掃 `services/jgb/`，正對照（修繕域 `repair_prefill`）
也選在同一層 ⇒ 正對照通過只證明**工具能用**，⛔ 證明不了 engine 層沒有。
教訓：正對照必須跨到**被查機制真正可能存在的那一層**。

**真正的 first causal break（不變）**：

```text
全流程**從未讀 `type`**（2＝點退）
⇒ 候選標籤不含類型、收斂後也不驗證選中那筆的身分
⇒ 「某合約的**點退**帳單」只能靠使用者自己從標題認出來
```
⚠️ 業主的裁示因此**完全成立**且 scope 更小：要補的是 `type` 的辨識與選取，
⛔ 不是候選框架、⛔ 不是通用 selector。blocker 代號改為 `FACET_TYPE_SELECTION_MISSING`。

### ⇒ 4657 **正式降級為 capability blocker**（2026-08-29 業主定案）

```text
4657 semantic envelope = REFUTED / NOT ESTABLISHED AS PREVIOUSLY DECLARED
reason = FACET_PROMISE_UNIMPLEMENTED（point-refund bill selection missing）
```
⚠️ 這**不是**「representation 寫窄一點」可以解決的問題。

⛔ **不得**改寫成「查某一筆帳單的金額與狀態」來湊 10/10——
那會把 4657 變成 4656 的 duplicate responsibility，
原本的「點退帳單」intent 反而**消失**。

⇒ **4657 暫不 population `retrieval_representation`；
   Level-A representation completeness 暫為 9/10，狀態 `BLOCKED_BY_CAPABILITY_CONTRACT`。**

### ⚠️ 哪些判斷更新、哪些**不**推翻

```text
✅ 仍成立：instance_applicability = instance
          （「查實際點退金額」本質上確實需要個別資料）
❌ 不成立：該 row 對應的 **Face execution capability 能完成該 intent**
⇒ nomination／applicability truth 與 execution capability **再一次必須分開**。
```

### 待業主處理（產品／架構決策，⛔ 不得由 representation migration 偷補）

```text
A. 補 point-refund bill selection capability
B. 改／停用這個 KB anchor
C. 另有既有 owner 應承接
```

### ⇒ 4657 的處置（原始查證記錄）

```text
❌ 「查詢自己某份合約的實際點退帳單金額」   → REVIEW_BLOCKED（選取步驟不可證）
❌ 「查詢特定合約相關的點退帳單及其狀態」   → 仍 over-claim（「點退」的辨識不可證）
✅ 可證的上限只到：「查詢某一筆帳單（含點退帳單）的金額與目前狀態」
   —— 但那與 4656 幾乎重合 ⇒ 4657 的 semantic envelope 本身需要重新裁定
```
⚠️ 業主原話成立：**這代表先前對 4657 semantic envelope 的理解需要一起修正，
   而不是讓新的 representation 把舊誤解固化。**

### 由此掉出的獨立 defect（⛔ 不在本輪修）

```text
FACET_PROMISE_UNIMPLEMENTED：
  bill_diagnosis 對話規則承諾「系統會列該合約的帳單候選」，
  帳單 face 路徑實際只取 data[0]。
  ⇒ 使用者給合約編號時，得到的可能是**任意一筆**帳單，且系統不會說明是哪一種。
```

---

## 執行順序（業主定案，⚠️ 第 5 步不可漏）

```text
1. 完成 10-row product review
2. 只有 approved representation 才寫 DB ＋ provenance
3. Level-A completeness invariant 必須通過
4. 重建 semantic-model
5. **只對 Level-A 10 rows 重生 embedding**
6. 驗：DB contract → retriever transport → vector representation → reranker representation
      全部實際使用同一份 reviewed text
7. 再做 candidate validation
```
⚠️ **4 與 5 是同一個 migration step**，⛔ 不得只做 4。
只重建容器而不重生既有 embedding ＝ 製造「形式上新 contract 已接線，
但 retrieval 前半段仍吃舊 semantic surface」的**假完成**。

---

# 附錄：`POINT_REFUND_BILL_SELECTION` 實作（業主授權 2026-08-29）

## 授權射程

```text
✅ 只補「點退帳單」的 selection contract
⛔ 不得順手泛化成所有帳單類型的通用 selector
```

## 契約

```text
合約多筆帳單 → filter type == 2
  0 筆  → NOT_FOUND，明確回報找不到，⛔ 不得 fallback 第一筆
  1 筆  → SELECTED
  >1 筆 → CANDIDATES，列出候選，⛔ 不得任取 data[0]
直接給 bill id → verify type == 2；⛔ 「id 存在＋query 說點退」不足以認定身分
```

## grounding provenance

要求**不是**「`_format_bill_status` 必須讀 type」，而是
**最後 grounding 必須能證明所回答的那一列就是 type=2**。
實作：selection 層產生決定性事實行 `類型：點退帳單（系統依帳單 type 判定）`，
與 identity／amount／status 一起進 facts ⇒ 三者不斷鏈。

## 六道 guard（`tests/unit/conversational/test_point_refund_selection_req.py`，11 條全過）

```text
1 first=type1 / second=type2 → 必須選 second（專門殺掉 data[0] 舊行為）
2 單筆 type=2 → identity ＋ type ＋ amount ＋ status 同時可見
3 沒有 type=2 → NOT_FOUND，⛔ 不得改用第一筆代答
4 兩筆 type=2 → 列候選且明示「系統未自行選定任一筆」
5 直接指定但 type != 2（含 type 缺值、標題含「點退」）→ ⛔ 不得稱為點退帳單
6 mutation ×3：拿掉 type filter／改回 data[0]／拿掉 type 事實行 → 行為必須改變
  ⚠️ guard exists ≠ guard can fail
```
⚠️ 另有 scope 守門測試：非點退意圖走 legacy 路徑，行為**逐字不變**。

## ⇒ 下一步（⛔ 仍不寫 DB、不重建 semantic-model）

```text
① ✅ selection capability 完成
② ⏸ 業主重新裁 4657 semantic envelope（post-fix candidate 已擬，非 authoritative）
③ ⏸ Level-A representation review → 10/10 COMPLETE
④ ⏸ 寫入 10 筆 reviewed declarations ＋ provenance
⑤ ⏸ invariant 13 轉綠
⑥ ⏸ rebuild semantic-model
⑦ ⏸ 只跑 scripts/regenerate_level_a_embeddings.py --apply
⑧ ⏸ transport verification（DB → retriever → embedding → reranker 同一份 reviewed text）
⑨ ⏸ representation candidate validation
```

---

# 附錄：⑨ transport 驗證結果（2026-08-29，**本機驗證環境**）

## 四段全部對得上同一份 reviewed text

```text
① DB declaration      10/10，source=reviewed_product_declaration
② retriever projection 真實檢索回傳的 4656 帶 retrieval_representation ＋ source
③ embedding document   sim(stored, embed(representation)) = 1.0000 ×10
                       sim(stored, embed(question_summary)) = 0.58–0.82（**負對照**）
④ reranker payload     semantic_score 與直打 /rerank 的 representation 值逐位相同
```

## reranker 三向對照（query「那筆帳單到底繳了沒」對 4656）

```text
A surface=representation    0.9191
B surface=question_summary  0.6398
C 舊 client（不送 surface）  0.6398
✅ A≠B  ⇒ server **確實消費** scoring_surface（⛔ 不是送了被忽略）
✅ B==C ⇒ 舊 client 的 legacy 優先序**逐字保留**
```

## 真實檢索路徑

```text
4656 rank=2、score_source=rerank、semantic_score=0.9190772
     ⇒ 與 A 值**逐位相同** ⇒ 產線管線確實拿 reviewed representation 評分
     scoring_surface_source=declared_representation
```

⚠️ **第一次驗證失敗且該失敗有價值**：用 vendor_id=1 預設 b2c 跑，4656 未進前 10。
查證後為 **scope 過濾**（4656 的 `business_types={system_provider}`、
`target_user={property_manager,tenant}`）⇒ 呼叫端沒帶對 mode／target_user，
⛔ 不是檢索缺陷。腳本對「未出現」**大聲失敗**而非靜默跳過，才逼出這件事。

## ⛔ 本輪不宣稱

```text
⛔ 不宣稱檢索品質已改善——那是 ⑩ candidate validation，**尚未授權**
⛔ 不宣稱通用 selection capability 完成（只證 point-refund 這一條）
⛔ production 未動；legacy 全庫重生兩條路徑維持 divergent_pending
```

## ⚠️ 一個非授權的副作用

`docker compose up -d --build rag-orchestrator` **連帶重建了 semantic-model image**
（同一時戳），當時的指示是「先不要重建 semantic-model」。
影響：行為不變——彼時無任何 authoritative 宣告，payload 的 scoring_surface
等於 question_summary，server 取值與舊版逐字相同。
