# A04：Level-A representation candidate validation —— **protocol 草案（待業主凍結）**

> 授權狀態：⑩ 已授權**開始**，目前授權的是 **protocol／source freeze**，⛔ **不是**先跑驗收。
> ⛔ freeze 前不產生新 query、⛔ 不先跑幾筆看看、⛔ 不依結果補樣。

## 0. 問題（凍結後不得改寫）

> **在 Level-A frozen 10 rows 內，reviewed `retrieval_representation` 是否修復
> representation-contract 所造成的 semantic retrieval loss，
> 同時沒有破壞原本已能正確辨識的同域 query？**

⛔ **不是**「新 representation 有沒有讓檢索變好」——那太寬，且會把「修缺口」
與「整體模型能力」混成一個分數。

## 1. Claim ceiling（一開始就寫死）

```text
可驗
  ✅ Level-A 10 rows 範圍內
  ✅ representation candidate 的 retrieval semantic correctness
  ✅ candidate vs legacy surface 的 **causal difference**
  ✅ representation migration 是否造成同域 regression

⛔ 不可驗（無論結果多好都不得宣稱）
  ⛔ B1 ×5 已解決
  ⛔ B3 ×2 已解決
  ⛔ 全域 KB retrieval 已改善
  ⛔ gate 已取得 authorization
  ⛔ production 已驗證
```

---

## 2. Generator 的可見／不可見（**隔離規格**）

```text
generator：isolated agent，**0 tools**（⛔ 不得讀 repo、⛔ 不得查 DB）

✅ 看得到
   - 該 row 的 **semantic responsibility spec**（產品語言描述「這筆負責什麼」）
   - 該 row 的 applicability（general／instance）
   - 撰寫規則與輸出格式

⛔ 看不到
   - production `question_summary`
   - `retrieval_representation`（**最關鍵**）
   - A03 queries、R6／R7 的 failure examples
   - 任何 candidate outputs、任何檢索分數
```

⚠️ **為什麼 representation 必須遮蔽**：generator 若看得到新 representation，
最省事的產法就是把它改寫一遍 ⇒ 最後測到的是「自己生成自己的 paraphrase」，
而那必然通過，卻什麼也沒證明。

⚠️ responsibility spec 與 representation **必須由不同人各自從 answer／capability 撰寫**，
⛔ 不得把 representation 換句話當成 spec 餵進去。本檔附錄 A 收錄 10 份 spec 供業主逐份核對
「這份 spec 是否等同於 representation 的改寫」——**核對通過才生成語料**。

## 3. 200 筆 positive 的一次性生成與封存

```text
量尺   10 rows × 20 = 200（沿用 A03 的 per-stratum 量尺，⛔ 不新發明）
批次   **一次生成、一次封存**；⛔ 不分批、⛔ 不看結果補樣
自然度 每筆自然表達該 row responsibility；
       ⛔ 不得要求固定出現 summary／representation 中的錨詞
       （要求錨詞＝把「模型認得同義詞」的問題偷換成「語料含錨詞」）
封存   生成後立即寫入 `a04-corpus.json` 並 commit；
       digest 記入本檔第 10 節；此後 ⛔ 不得增刪改任何一筆
```

⚠️ **3402／3519 必須留著**。它們的 representation coverage 原本就 COMPLETE，
但它們是 **migration regression controls**——⛔ 不得因為「預期不會改善」而排除。

## 4. Labeler 隔離

```text
labeler：與 generator **隔離**的 agent（不同 session、不共享 transcript）

✅ 看得到 responsibility truth（同一份 spec）
⛔ 看不到 retrieval score
⛔ 看不到任何 system output（top1／rank／candidate 或 legacy 的結果）
⛔ 看不到 generator 的產出理由

判準  L1（judgeable 判定）＋ L2（該 query 應由哪個 row 承接）
       兩位獨立 labeler，⛔ 不得互看
```

## 5. Neighboring negatives 的來源（**提案，待業主凍結**）

⚠️ 先報一個會影響設計的事實：`條件診斷：帳單` 這個 category **總共就是 10 筆**，
也就是 Level-A **等於**整個 category ⇒ 「同 category 的鄰居」**不存在**。
鄰近 intent 必須取自相鄰 category。

實查現有母體（皆為**本工作線之外**、獨立撰寫的既有知識）：

| 相鄰 category | 列數 |
|---|---|
| 帳單管理 | 26 |
| 繳費金流排障 | 11 |
| 發票 | 6 |
| 帳單異常 | 5 |
| 滯納金 | 4 |
| 條件診斷：付款 | 4 |
| 條件診斷：發票 | 2 |
| 帳單設定引導 | 2 |

### 提案 N-A（主案）：以既有相鄰列為 **expected_row**，由同一隔離 generator 產 query

```text
母體    上表 60 列中，**預先**以機械規則選出（⛔ 不看內容挑）：
        每個相鄰 category 依 id 升冪取前 k 列，湊滿 N_ROWS
量尺    每列 5 筆 → 目標約 100 筆 negatives
判準    這些 query 的正解**不是** Level-A 任何一列；
        candidate 若把它們吸進 Level-A ⇒ 記 **FALSE_ATTRACTION**
對稱性  generator 看的是**該相鄰列**的 responsibility spec，
        同樣 ⛔ 看不到任何 representation ⇒ 與 P 層同一隔離規格
```
⚠️ 這仍是「生成」語料，但**方向相反**：它測的是新 representation 有沒有變寬到
誤吸鄰居，而 generator 對 Level-A 的 representation 一無所知 ⇒ ⛔ 不可能為了通過而作弊。

### 提案 N-B（備案，需**另行授權**）：真實客服逐字稿

```text
來源  s3://jgb2-production-upload/assistant-reports/（真實使用者語句，從未用於本工作線）
優點  完全外生，⛔ 不含任何生成偏誤
成本  需存取授權＋去識別化＋人工判定正解，且 Level-A 命中率可能極稀
       （⚠️ A01 已證泛用 corpus 對 Level-A opportunity 太稀 → SOURCE_INSUFFICIENT）
```
⇒ 建議 N-A 為主案；N-B 僅在業主要求外生證據時另案啟動。

## 6. Legacy counterfactual harness（**只換 semantic surface**）

```text
⛔ **不得**把 DB 改回舊值來做 legacy——那會讓 migration state 本身變成變因，
   且 candidate 與 legacy 不再是同一批執行環境。
✅ 隔離 harness：同一次執行內，對同一 query 算兩條分數路徑
```

固定不變（兩條路徑逐項相同）：

```text
same query｜same KB rows｜same model｜same threshold｜same weights
same category／routing config｜same candidate-generation logic
```

唯一變因：

```text
CANDIDATE  embedding = embed(reviewed retrieval_representation)
           reranker  = score(query, reviewed retrieval_representation)
LEGACY     embedding = embed(frozen question_summary)
           reranker  = score(query, frozen question_summary)
```

⚠️ legacy embedding **不從 DB 讀**（DB 現值已是 candidate），改由 harness 以
frozen `question_summary` 即時編碼 ⇒ 兩條路徑的 vector 與 rerank 都來自同一模型、
同一次執行。frozen summary 原文一併寫入 corpus 檔，digest 納入第 10 節。

### 每筆至少保留

```text
expected_row
candidate:  top1 / rank / final score
legacy:     top1 / rank / final score
candidate semantic result   （PASS／FAIL）
legacy semantic result      （PASS／FAIL）
paired outcome: RESCUE / REGRESSION / SAME_PASS / SAME_FAIL
```
⇒ 只有 paired outcome 能回答「是 **intervention** 造成 rescue」，
⛔ 而不是「新版剛好過了」。

## 7. 驗收門檻（**沿用 A03，⛔ 不發明新數字**）

```text
label quality      L1 ≥ 90%；Cohen κ ≥ 0.70（κ undefined → LABELING_INCONCLUSIVE）
coverage           每 stratum judgeable ≥ 15/20
candidate 正確率   **每個 row** ≥ 80%（沿用 A03 的 80%，
                   ⛔ 不因這輪結果可能較好或較差而重選）
```

### Regression gate：用 member discipline，⛔ 不亂定新百分比

> **若某 row 出現 candidate 把 legacy 的明確正確案例系統性變錯，
> 該 row ⛔ 不得因其他 row rescue 很多而被 aggregate PASS 掩蓋。**

⇒ 最終**按 row 報**（3402 … 4657 各自的 rescue／regression／same），
⛔ 不得只報 200 筆總 accuracy。

### ⚠️ 「勝過 legacy」⛔ 不是 10 rows 的必要條件

```text
3402／3519 原本 coverage 就 COMPLETE，合理結果可能是
  legacy 19/20 ／ candidate 19/20
⇒ 這是 **stability PASS**，⛔ 不是「沒有改善所以失敗」
```

最終分三段報，⛔ 不混成一個分數：

```text
representation-gap rows   是否產生 RESCUE、多少、在哪些 row
previously-complete rows  是否維持 correctness
all Level-A               candidate absolute semantic correctness 是否過 frozen threshold
```

## 8. Frozen digests（實測值，2026-08-29）

```text
IMPLEMENTATION_SHA      19d157719fc2e390704e83da1f1eee8ca2754a7d（working tree clean）
LEVEL_A_POPULATION      98a1b8af32aa32f9ef956779b23b7db8d4586cf1b40e70dcbb2b4d0a445d756b
                        （10 列的 id｜representation｜provenance source）
EMBEDDING_SNAPSHOT      71f3a3dd31528dcdc3214b35be3289f7e133e9ccc04d66f0eaa50b6c0a2058b2
                        （10 列的 id｜md5(embedding)）
SEMANTIC_MODEL_IMAGE    sha256:8ea2a0b2e0cb15ede333050625f107c4bb9cbc12247b448d0aa1f0110deb3dcc
SEMANTIC_API_SERVER_SHA de4788b9cb1539860c47594741714e2149266ad5e8b21582b30e4c0ddd61c91a
RERANKER_MODEL          BAAI/bge-reranker-base
RAG_ORCHESTRATOR_IMAGE  sha256:5f7559d28fb39e76643ae65382702980f24f8c3a54f67f1cd400c9d45f42088b
ROUTING_PARAMS          KB_SIMILARITY_THRESHOLD=0.65
                        RERANKER_MIN_VECTOR_SIMILARITY=0.3
                        RERANKER_INPUT_LIMIT=20
PROTOCOL_DIGEST         見 a04-protocol-frozen.digest（本檔內容的 sha256）
```

⚠️ 執行時**必須**逐項複驗；任一項不符 ⇒ **中止**，⛔ 不得「差不多就跑」。

## 9. PROCESS_DEVIATION（業主已裁：記錄即可，⛔ 不判污染 ⑨）

```text
事件  `docker compose up -d --build rag-orchestrator` **連帶重建** semantic-model image
       （當時指示為「先不要重建 semantic-model」）
裁定  記為 PROCESS_DEVIATION，⛔ 不判污染 ⑨、⛔ 不需重做 ④–⑨
理由  重建當時 authoritative declaration 為 0，新舊 surface 實際等同 summary；
       且 ⑨ 事後以 A／B／C 負對照證明 production path 現在確實消費 reviewed representation
⚠️ 不得抹掉：紀錄保留於此與 r9-review-status.md
```

## 10. 尚待業主凍結的項目

```text
① 附錄 A 的 10 份 responsibility spec —— 逐份核對「是否只是 representation 的改寫」
② N 層來源：N-A（主案）或 N-B（需另行授權）
③ N-A 的 N_ROWS／每列筆數（草案：約 100 筆）
④ 本檔凍結後計算 PROTOCOL_DIGEST 並寫入 sidecar
```
⇒ **這四項凍完，才正式生成新的 holdout。**

---

# 附錄 A：10 份 **responsibility spec**（**機械組裝**，⛔ 無任何我撰寫的散文）

⚠️ 本附錄刻意**不寫**「這筆負責什麼」的散文描述。原因：
`retrieval_representation` 由本 session 撰寫，若再由同一作者寫 spec，
generator 拿到的實質上就是 representation 的改寫 ⇒ 最後只會測到
**自己生成自己的 paraphrase**。

⇒ 改採**零改寫**做法：spec ＝ **frozen answer 原文** ＋ **formatter 原始碼**，
兩者皆逐字取自凍結來源，⛔ 不經我的措辭。
generator 因此看得到「這筆實際承接什麼」，卻**看不到任何 representation 用語**。

⚠️ 仍待業主裁定：若要求 spec 為**人寫的散文**，則必須由**與 representation 不同的作者**
撰寫；本 session 已受污染 ⇒ 需業主明確要求另派隔離作者（⛔ 我不自行派工）。


## 3402

### frozen answer（逐字）

```text
點退完成後系統自動產生點退帳單，內容包含：（1）水電等未結費用：依點退時記錄的度數結算；（2）設施損壞賠償：依點退檢查結果列出的賠償金額；（3）其他費用：房東自訂的額外費用。點退帳單的到期日依合約設定或點退當天計算。帳單金額會與押金互抵，多退少補。
```

### downstream capability

```text
（無——本列為 general row，責任完全由上方 answer 承載）
```


## 3406

### frozen answer（逐字）

```text
帳單繳費完成後可下載收據 PDF。下載方式：在帳單詳情頁面點選「下載收據」，系統會產生包含帳單編號、繳費日期、金額明細和付款方式等資訊的 PDF 收據。收據可供租客留存作為繳費證明。尚未繳費的帳單無法產生收據。若需要正式的統一發票，請參考發票開立功能另行處理。
```

### downstream capability

```text
（無——本列為 general row，責任完全由上方 answer 承載）
```


## 3495

### frozen answer（逐字）

```text
帳單無法發送時，常見原因：狀態不對、金額未填、度數未填。
```

### downstream capability（原始碼逐字）


```python
def _diagnose_cannot_send(bill: dict) -> str:
    """B01：帳單為什麼發不出去"""
    title = bill.get("title", f"帳單 {bill.get('id', '?')}")
    bit_status = _bill_status(bill)
    details = bill.get("details", [])
    blockers = []

    # 條件 1：帳單必須在草稿狀態，否則直接回覆
    if bit_status != 1:
        status_label = _get_status_label(bit_status)
        return f"帳單「{title}」目前狀態為「{status_label}」，已經不在待發送階段，不需要再發送。"

    # 條件 2：帳單明細不能為空
    if not details:
        blockers.append("帳單沒有任何收費項目，請先新增費用明細")

    # 條件 3：檢查明細項目是否完整
    UNIT_TYPE_NAMES = {1: "度數類費用", 2: "日數類費用", 3: "月數類費用"}
    for idx, detail in enumerate(details, 1):
        if not detail.get("active"):
            continue
        # 費用名稱：label > item.name > unit_type 推斷
        item = detail.get("item", {}) or {}
        raw_label = detail.get("label") or item.get("name")
        label = raw_label or UNIT_TYPE_NAMES.get(detail.get("unit_type"), f"第 {idx} 項費用")
        unit_type = detail.get("unit_type")
        unit_price = detail.get("unit_price")
        measurement_before = detail.get("measurement_before")
        measurement_after = detail.get("measurement_after")

        # 費用名稱為空（label=null）：系統可能要求填寫
        if not raw_label:
            blockers.append(f"{label}（第 {idx} 項）尚未設定費用名稱")

        # 度數類（電費、水費等）需要上期/本期度數
        if unit_type == 1:  # 度
            if measurement_after is None or measurement_after == 0:
                blockers.append(f"「{label}」本期度數尚未填寫")
            elif measurement_before is not None and measurement_after < measurement_before:
                blockers.append(f"「{label}」本期度數（{measurement_after}）小於上期度數（{measurement_before}）")
        # 金額不能為 0
        if unit_price is not None and unit_price <= 0 and unit_type != 1:
            blockers.append(f"「{label}」金額為 0，請確認是否正確")

    if not blockers:
        return f"帳單「{title}」看起來沒有明顯問題。如果仍然無法發送，可能是系統端驗證未通過，建議重新整理頁面後再試。"

    reasons = "\n".join(f"• {b}" for b in blockers)
    return f"帳單「{title}」無法發送，可能原因：\n{reasons}"
```


## 3496

### frozen answer（逐字）

```text
帳單取消需狀態為「應到帳」或「排定發送」。其他狀態的帳單不支援取消。
```

### downstream capability（原始碼逐字）


```python
def _diagnose_cannot_cancel(bill: dict) -> str:
    """B02：帳單為什麼取消不了——鏡射 jgb2 Bill::canCancel：
    只有應到帳/待繳費(2)與排定發送(32)可取消（收回）；無型態限制。
    （客服回報批次20260731 R-33 勘誤：舊版「只有待發送能取消」方向相反。）"""
    title = bill.get("title", f"帳單 {bill.get('id', '?')}")
    bit_status = _bill_status(bill)
    status_label = _get_status_label(bit_status)

    if bit_status in (2, 32):
        return (f"帳單「{title}」目前狀態為「{status_label}」，可以取消（收回）——"
                "收回後帳單退回「待發送」，可修改內容後重新發送；"
                "原繳費資訊會失效，重發時會產生新的虛擬帳號／繳費代碼。"
                "如仍無法操作，請重新整理頁面後再試。")

    if bit_status == 1:
        hint = "帳單尚未發送，不需要取消——可直接編輯內容；不再需要時可將其封存"
    elif bit_status in (8, 16):
        hint = "租客款項已進入對帳／到帳流程，不能收回"
    elif bit_status == 64:
        hint = "帳單已失效，無需取消"
    else:
        hint = "此狀態不支援取消"
    return (f"帳單「{title}」無法取消，原因：\n"
            f"• 帳單目前狀態為「{status_label}」，{hint}"
            "（可取消的狀態：應到帳/待繳費、排定發送）")
```


## 3498

### frozen answer（逐字）

```text
逾期費計算公式：租金 × 遲繳天數 × 費率%。遲繳天數 = 付款日 - 到期日 - 緩衝天數。
```

### downstream capability（原始碼逐字）


```python
def _diagnose_late_fee(bill: dict) -> str:
    """B03：為什麼被收逾期費"""
    title = bill.get("title", f"帳單 {bill.get('id', '?')}")
    date_expire = bill.get("date_expire")
    complete_at = bill.get("complete_at")
    pay_at = bill.get("pay_at")

    lines = [f"關於帳單「{title}」的逾期費：\n"]

    if date_expire:
        expire_str = _format_date_int(date_expire)
        lines.append(f"• 繳費期限：{expire_str}")

    if pay_at:
        lines.append(f"• 繳費時間：{pay_at}")
    elif complete_at:
        lines.append(f"• 到帳時間：{complete_at}")

    if date_expire and (pay_at or complete_at):
        lines.append("\n逾期費會在超過繳費期限後自動計算。具體計算方式取決於合約中的逾期費設定（緩衝天數、百分比）。")
        lines.append("如需確認逾期費計算細節，請查看合約的「逾期費設定」。")
    else:
        lines.append("\n此帳單尚未繳費。若超過繳費期限仍未付款，系統會依合約設定計算逾期費。")

    return "\n".join(lines)
```


## 3499

### frozen answer（逐字）

```text
手動到帳失敗時前端會顯示錯誤訊息，常見三種。
```

### downstream capability（原始碼逐字）


```python
def _diagnose_manual_complete(bill: dict) -> str:
    """B04：手動到帳失敗"""
    title = bill.get("title", f"帳單 {bill.get('id', '?')}")
    bit_status = _bill_status(bill)
    complete_at = bill.get("complete_at")
    blockers = []

    # 已到帳
    if bit_status == 16:
        return f"帳單「{title}」已標記為已到帳（完成時間：{complete_at or '未知'}），無需再次操作。"

    # 必須在待繳費或待對帳狀態
    if bit_status not in (2, 8):
        status_label = _get_status_label(bit_status)
        blockers.append(f"帳單目前狀態為「{status_label}」，只有「待繳費」或「待對帳」狀態才能手動標記到帳")

    if not blockers:
        return f"帳單「{title}」狀態正確，應該可以手動標記到帳。如果操作時出現錯誤，可能是系統暫時忙碌，請稍後再試。"

    reasons = "\n".join(f"• {b}" for b in blockers)
    return f"帳單「{title}」無法手動到帳，原因：\n{reasons}"
```


## 3519

### frozen answer（逐字）

```text
點退帳單是租客同意點退後系統自動產生的，金額算法是：水電費等結算費用，加上設備損壞賠償和違約金，再扣掉應退還的押金。帳單總額是負數就代表要退錢給租客，是正數則代表押金扣完還不夠，租客需要補繳差額。舉例：押金 20,000 元、水電結算 700 元、設備賠償 5,000 元，帳單總額就是 -14,300 元，即退還租客 14,300 元。每個項目都會列在帳單明細裡，雙方都看得到。
```

### downstream capability

```text
（無——本列為 general row，責任完全由上方 answer 承載）
```


## 4640

### frozen answer

```text
（空——本列為 empty-answer Face-entry anchor）
```

### downstream capability（原始碼逐字）


```python
def _diagnose_receipt(bill: dict) -> str:
    """B05：收據查詢（R-31）——收據於繳費完成後產生（同 3406 知識），
    未繳費要明說「尚無收據」，不得沉默改答帳單金額。"""
    title = bill.get("title", f"帳單 {bill.get('id', '?')}")
    bit_status = _bill_status(bill)
    if bit_status == 16:
        due = _bill_amount_due(bill)
        received = _bill_amount_received(bill)
        # 收據金額＝帳單明細合計（鏡射 jgb2 收據 PDF 產生方式），不是實收欄位
        amount_str = _money(due) if due is not None else "（依帳單明細金額）"
        msg = f"帳單「{title}」已繳費，收據金額為 {amount_str}。"
        if received is not None and due is not None and abs(received - due) >= 1:
            msg += (f"另外系統記錄的實收金額為 {_money(received)}，與帳單金額不同，"
                    "請以收據明細為準。")
        return msg + "可在帳單詳情頁點選「下載收據」取得 PDF（含帳單編號、繳費日期、金額明細與付款方式）。"
    if bit_status == 8:
        return (f"帳單「{title}」租客已付款、款項待金流商確認入帳（待對帳），"
                "收據會在款項確認到帳後產生，屆時可於帳單詳情下載。")
    total = _bill_amount_due(bill)
    total_str = f"（帳單金額 {_money(total)}）" if total is not None else ""
    return (f"帳單「{title}」目前狀態為「{_get_status_label(bit_status)}」，尚未繳費，"
            f"因此還沒有收據可查{total_str}。收據會在租客完成繳費、款項到帳後產生。")
```


## 4656

### frozen answer

```text
（空——本列為 empty-answer Face-entry anchor）
```

### downstream capability（原始碼逐字）


```python
def _format_bill_status(bill: dict) -> str:
    """格式化帳單現況"""
    title = bill.get("title", f"帳單 {bill.get('id', '?')}")
    bit_status = _bill_status(bill)
    status_label = _get_status_label(bit_status)
    total = _bill_amount_due(bill)
    date_expire = bill.get("date_expire")

    lines = [f"帳單「{title}」資訊：\n"]
    lines.append(f"• 狀態：{status_label}")
    lines.append(f"• 金額：{_money(total) if total is not None else '（系統未記錄）'}")
    if date_expire:
        lines.append(f"• 繳費期限：{_format_date_int(date_expire)}")

    details = bill.get("details", [])
    UNIT_TYPE_NAMES = {1: "度數類費用", 2: "日數類費用", 3: "月數類費用"}
    if details:
        lines.append("\n收費明細：")
        for idx, d in enumerate(details, 1):
            if not d.get("active"):
                continue
            item = d.get("item", {}) or {}
            label = d.get("label") or item.get("name") or UNIT_TYPE_NAMES.get(d.get("unit_type"), f"第 {idx} 項")
            price = d.get("total_price", 0)
            lines.append(f"  - {label}：NT$ {price:,.0f}")

    return "\n".join(lines)
```


## 4657

### frozen answer

```text
（空——本列為 empty-answer Face-entry anchor）
```

### downstream capability（原始碼逐字）


```python
def _format_bill_status(bill: dict) -> str:
    """格式化帳單現況"""
    title = bill.get("title", f"帳單 {bill.get('id', '?')}")
    bit_status = _bill_status(bill)
    status_label = _get_status_label(bit_status)
    total = _bill_amount_due(bill)
    date_expire = bill.get("date_expire")

    lines = [f"帳單「{title}」資訊：\n"]
    lines.append(f"• 狀態：{status_label}")
    lines.append(f"• 金額：{_money(total) if total is not None else '（系統未記錄）'}")
    if date_expire:
        lines.append(f"• 繳費期限：{_format_date_int(date_expire)}")

    details = bill.get("details", [])
    UNIT_TYPE_NAMES = {1: "度數類費用", 2: "日數類費用", 3: "月數類費用"}
    if details:
        lines.append("\n收費明細：")
        for idx, d in enumerate(details, 1):
            if not d.get("active"):
                continue
            item = d.get("item", {}) or {}
            label = d.get("label") or item.get("name") or UNIT_TYPE_NAMES.get(d.get("unit_type"), f"第 {idx} 項")
            price = d.get("total_price", 0)
            lines.append(f"  - {label}：NT$ {price:,.0f}")

    return "\n".join(lines)
```


```text
點退帳單的選取契約：services/jgb/point_refund_selection.py
  身分唯一依據 type==2；0 筆→NOT_FOUND、1 筆→SELECTED、>1 筆→CANDIDATES；
  直接指定 bill id 時須先 verify type==2。
```
