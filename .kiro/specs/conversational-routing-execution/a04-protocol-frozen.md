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
   - **row 與歷史 failure 的對應關係**：
     ⛔「3406 曾經失敗」、⛔「4656 在 A03 只有 3/10」、⛔ B1／B2／B3、⛔ R6 rescue cases
```

⚠️ 為什麼連歷史 failure 也要遮蔽：即使看不到 representation，
知道「哪幾列曾經失敗」就足以讓 generator **針對那些 failure family 出題**
⇒ 語料難度分布被歷史結果污染，測到的不再是 representation 本身。

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

## 5. Neighboring negatives —— **N-A，已凍**

⚠️ 先報一個會改變設計的事實：`條件診斷：帳單` 這個 category **總共就是 Level-A 這 10 筆**，
也就是 Level-A **等於**整個 category ⇒ 「同 category 的鄰居」**不存在**。
鄰近 intent 必須取自相鄰 category。

### 為什麼選 N-A（⛔ 不選 N-B）

```text
A04 要驗的 failure mode：representation 變寬後，會不會把
**語義相鄰、但責任屬於別列**的 query 吸進 Level-A。
N-A 正對這個 failure mode，且 negative truth 乾淨：
   query 由 neighboring row 的 authoritative responsibility 生成
   expected owner = neighboring row
   Level-A 10 rows = negatives
generator 又看不到 Level-A representation ⇒ ⛔ 不存在「刻意避開新版文字」的作弊路徑。
```
N-B（真實客服逐字稿）⛔ 不進 A04——它回答的是另一個問題，且 A01 已證泛用外生 corpus
對 Level-A opportunity 太稀而得到 SOURCE_INSUFFICIENT。保留為未來的外生 observational validation。

### 選列演算法（**完全機械，⛔ 不看內容挑難易**）

```text
SEED            "A04-N"
hash(row)       md5(f"{SEED}|{row_id}") 十六進位
6 個 category   帳單管理／繳費金流排障／發票／帳單異常／滯納金／條件診斷：付款
                （母體＝該 category 內、⛔ 排除 Level-A 10 列的 active 知識）
處理順序        **母體由小到大**；同大小以 category 名稱 UTF-8 位元組序
每 category     依 hash 升冪取最多 4 列；已被前一 category 選走者跳過（先到先得）
```

⚠️ **「母體由小到大」是本輪新增的機械規則，理由是實測逼出來的**：
`條件診斷：付款` 的 **4 列全部**同時也屬於 `繳費金流排障`（實查
`{條件診斷：付款,繳費金流排障}`）。若照 category 列出順序處理（大在前），
繳費金流排障會先把其中 2 列取走 ⇒ 只選出 **22 列／92 筆**，
與凍定的「24 列／exactly 100」不符，且正好犯了業主指出的
「大 category 把小而高混淆度的 category 擠掉」。
小者優先是**直接實作該顧慮**的機械保證，⛔ 不是為了湊數字而挑。

### 凍結後的實際選列（24 列）

```text
處理順序：條件診斷：付款(4) → 滯納金(4) → 帳單異常(5) → 發票(6)
        → 繳費金流排障(11) → 帳單管理(24)
每 category 各取 4 ⇒ **24 列**
每列 4 筆 ＋ hash 全序前 4 列各 +1 ⇒ **exactly 100 筆**
```

| hash 前綴 | id | category | +1 | question_summary |
|---|---|---|---|---|
| 029f3a05 | 3923 | 繳費金流排障 | ✅ | 超商繳費 狀態沒跳 撥付時程 |
| 02d2acd7 | 3398 | 帳單管理 | ✅ | 電費計費方式 度數計算 |
| 077f3202 | 3366 | 繳費金流排障 | ✅ | 繳費成功 繳費紀錄 |
| 07f192c5 | 3407 | 帳單管理 | ✅ | 帳單統計報表 收支分析 |
| 0bd3ad05 | 3497 | 條件診斷：付款 | | 已付款但帳單狀態沒有更新 |
| 15911812 | 4637 | 帳單管理 | | 帳單總表 虛擬帳號查交易 銀行抽查入帳 |
| 180abe15 | 4647 | 帳單管理 | | 未發送帳單一次編輯 批次調整範圍 |
| 254b511c | 3502 | 條件診斷：付款 | | 虛擬帳號過期或轉帳失敗 |
| 2dd05b85 | 3934 | 帳單異常 | | 帳單金額怪怪的 跟預期不一樣 |
| 2e04d0ac | 3938 | 發票 | | 發票開錯了 要作廢重開 |
| 2e8f2f20 | 3935 | 帳單異常 | | 這期帳單怎麼還沒出來 |
| 32907fcf | 3532 | 滯納金 | | 滯納金客製版本 固定金額階梯式 |
| 32bfd11a | 3924 | 繳費金流排障 | | 租客轉帳失敗 匯款上限 資訊核對 |
| 36adca86 | 3936 | 帳單異常 | | 租客說看不到帳單 找不到 |
| 40e15441 | 3420 | 發票 | | 發票未收到 排查步驟 |
| 4ce35284 | 3937 | 發票 | | 發票怎麼還沒開 沒收到發票 |
| 57a34336 | 3932 | 繳費金流排障 | | 帳單卡在待對帳 狀態一直沒跳 |
| 624313bc | 3500 | 條件診斷：付款 | | 信用卡付款失敗 |
| 745b632e | 3940 | 滯納金 | | 這筆延遲金是怎麼算的 |
| 76f7db7b | 3362 | 發票 | | 發票沒開 發票狀態 |
| 8f9cd7f2 | 3531 | 滯納金 | | 滯納金帳單產生 付款後結算規則 |
| b20776dd | 3928 | 帳單異常 | | 帳單還沒出現 產生時點規則 |
| c3dce261 | 3501 | 條件診斷：付款 | | 信用卡自動扣款失敗 |
| c8931d05 | 3939 | 滯納金 | | 滯納金怎麼收這麼多 |

### N 層的評分**分兩層**（⛔ 不可混）

```text
N1  ownership correctness      expected neighboring row 是否正確
N2  Level-A false attraction   任一 Level-A row 是否**錯誤取代** expected neighbor
```
⚠️ **A04 representation safety 的核心是 N2**。
⛔ 不得因 neighbor-vs-neighbor 的排名錯誤（N1 失分）就誤算成 representation regression。

### N generator 的額外限制

```text
⛔ N generator **看不到 Level-A specs**
⛔ ⛔ 不得被要求「產生容易與帳單診斷混淆但其實不是的問題」
   —— 那會變成 adversarial synthetic set，測的是另一件事
✅ 它的工作只有：依 neighboring row 的 responsibility 產生**自然** query
```

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

## 10. 業主裁定（**四項已凍**，2026-08-29）

```text
① Spec        MECHANICAL / ZERO-REWRITE，依 row 類型取 authoritative source
              general  = frozen answer 原文
              instance = frozen Face responsibility 原文 ＋ 實際 deterministic capability 原始碼
              ⛔ 不另派散文作者；⛔ 不無差別為 10 列都附 formatter
② Negative    N-A（⛔ 不用 N-B）
③ N size      exactly 100；6 category stratified；每 category 最多 4 列（frozen stable hash）
              24 列 ×4 ＋ hash 前 4 列 ×1
④ Digest      本檔更新後重算；舊 e724b818… = **DRAFT_SUPERSEDED**，
              ⛔ 不得再作為 A04 evidence packet 的 protocol digest
```

### ⚠️ 唯一一處需要業主追認的實作細節

```text
業主凍的是「6 categories × 最多 4 列 ＝ 24 列」。
實測發現 `條件診斷：付款` 的 **4 列全部**同時屬於 `繳費金流排障`
⇒ 若按 category 列出順序（大在前）處理，只會得到 22 列／92 筆。
⇒ 本檔補上機械規則「**母體由小到大**處理」，還原成 24 列／exactly 100。
⚠️ 這是為了達成業主凍定的數字而補的**機械**規則，且直接實作業主自己的顧慮
   （「大 category 把小而高混淆度的 category 擠掉」），⛔ 不是內容挑選。
   若業主不採此規則，則須改凍 22 列／92 筆或其他數字，並**重算 digest**。
```

## 11. 生成順序（⛔ 不得先做一層再回頭補另一層）

```text
1 ✅ Appendix A 改為 row-type authoritative-source rule
2 ✅ N source = N-A
3 ✅ N selection = six-category stratified / exactly 100
4 ✅ selection algorithm、seed／hash rule、generator visibility、labeler visibility 全部寫入本檔
5 → 重算 PROTOCOL_DIGEST
6 → 記錄 FROZEN_AT
7 → 才允許生成 corpus：**P=200 與 N=100 同一輪封存**
```

---

# 附錄 A：10 份 **responsibility spec**（MECHANICAL / ZERO-REWRITE，業主凍結）

⚠️ 依 row 類型取 **authoritative source**，⛔ 不無差別為 10 列都附 formatter：

```text
GENERAL  row  spec = frozen answer 原文
INSTANCE row  spec = frozen Face responsibility／execution contract 原文
              ＋ 該 Face 實際 deterministic capability 的**原始碼原文**
              （必要時含 selection contract，如 4657 的 type=2 選取）
```

理由（業主定案的兩把尺）：`general → answer responsibility`、
`instance → Face／downstream capability responsibility`。
⚠️ 若讓 3519 這種 general row 也拿到 bill formatter，generator 反而會生出
**這筆 Knowledge 根本不負責**的 instance query。反之 4640／4656／4657 只靠 frozen answer
（皆為空）則**沒有足夠 truth**。

⚠️ 防止「作者手挑語義句」形成新污染的機械規則：
> **引用整個已指定的 responsibility config／function body，⛔ 不由作者手挑語義句。**
> 可去除純註解、logging、exception boilerplate，⛔ 但不得依「哪些內容比較有利於驗證」挑句。

⚠️ 本附錄**零改寫**：所有內容逐字取自 frozen answer、DB 內的 Face config、
或 repo 原始碼。⛔ 無任何本 session 撰寫的散文——`retrieval_representation` 由本
session 撰寫，若再由同一作者寫 spec，generator 拿到的就是它的改寫，
最後只會測到**自己生成自己的 paraphrase**。

## INSTANCE 列共用：frozen Face responsibility（逐字，取自 DB）

### 對話規則原文

```text
你是 JGB 智慧租賃平台的「帳單操作診斷助理」，協助管理者查「這筆帳單為什麼發不出去／取消不了／被收逾期費／手動到帳失敗」這類單筆操作問題。

【追問識別】收斂前必須取得帳單識別 bill_ref（帳單編號；沒有編號時可用合約編號或物件名稱，系統會列該合約的帳單候選）→ extracted_fields.bill_ref。只要給出編號或名稱就視為已取得，直接 action="converge"，不要再問。多筆由系統列候選處理。
【不重問現象】對方開頭已講明是哪種問題（發不出去/取消不了/逾期費/手動到帳）→ 全程記住，不再確認現象；symptom 非收斂必要條件，拿到 bill_ref 就 converge，系統會依原句判定診斷項。
【收齊→查 API】bill_ref 已有 → action="converge"、converge_kind="answer"；系統會依帳單現況判定該操作可否執行與阻擋原因（草稿才能發送/取消、明細完整性、手動到帳條件），你照系統判定作答，不自行推斷原因。
【金額紅線】金額一律引用系統提供的存值，禁止自行計算、加總或改寫數字。
【API 現值為準】一切以系統查得的現值為準；不複述內部狀態代碼，用狀態名稱講。
【本輪範疇 scope】是帳單操作可否/原因相關、或在回答你剛問的問題 → scope="stay"。帳單金額組成/看不到帳單（帳單異常）、繳費入帳（繳費金流排障）、其他領域完整新問題 → scope="switch"。不確定 → stay 並澄清。
【本輪面向 face】若有提供【本領域可用面向】，從中選最貼近這句的一個放入 face；純識別/不明確 → 省略。
每輪輸出 JSON：{"action":"ask"|"converge","converge_kind":"answer","extracted_fields":{"bill_ref":"…","symptom":"…（如有）"},"next_question":"…","scope":"stay"|"switch","face":"…（如有）","delegate_facet_key":"…（見下）"}
【delegate_facet_key 規則】scope="stay" → 必須為 ""；scope="switch" 且符合上列已宣告的轉交對象 → 必須填該對象的鍵；scope="switch" 但無法對應合法轉交對象 → ""。
```

### grounding_scope（config 原文）

```json
{
    "params": {
        "role_id": "{session.role_id}"
    },
    "select": "api",
    "endpoint": "jgb_bills",
    "search_params": [
        {
            "bill_ref": "{form.bill_ref}"
        }
    ],
    "required_slots": [
        "bill_ref"
    ],
    "result_mapping": {
        "id_field": "id",
        "list_path": "data",
        "entity_noun": "帳單",
        "label_field": "title",
        "skip_refine": true,
        "label_fields": [
            "title",
            "sub_title",
            "date_expire",
            "total"
        ],
        "refine_param": "bill_ref",
        "candidate_cap": 8,
        "label_date_fields": [
            "date_expire"
        ]
    },
    "secondary_call": {
        "params": {
            "bill_id": "{row.id}",
            "role_id": "{session.role_id}"
        },
        "endpoint": "jgb_bill_detail",
        "attach_as": "bill_detail",
        "list_path": "data"
    },
    "requires_instance_reference": true
}
```


## 3402（general）

### frozen answer（逐字，**本列 spec 的全部**）


```text
點退完成後系統自動產生點退帳單，內容包含：（1）水電等未結費用：依點退時記錄的度數結算；（2）設施損壞賠償：依點退檢查結果列出的賠償金額；（3）其他費用：房東自訂的額外費用。點退帳單的到期日依合約設定或點退當天計算。帳單金額會與押金互抵，多退少補。
```


⛔ 本列**不附** formatter——general row 的責任完全由 answer 承載。


## 3406（general）

### frozen answer（逐字，**本列 spec 的全部**）


```text
帳單繳費完成後可下載收據 PDF。下載方式：在帳單詳情頁面點選「下載收據」，系統會產生包含帳單編號、繳費日期、金額明細和付款方式等資訊的 PDF 收據。收據可供租客留存作為繳費證明。尚未繳費的帳單無法產生收據。若需要正式的統一發票，請參考發票開立功能另行處理。
```


⛔ 本列**不附** formatter——general row 的責任完全由 answer 承載。


## 3495（instance）

### frozen answer


```text
帳單無法發送時，常見原因：狀態不對、金額未填、度數未填。
```

### deterministic capability（原始碼逐字，整個 function body）


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


⚠️ Face responsibility 原文見上方「INSTANCE 列共用」一節。


## 3496（instance）

### frozen answer


```text
帳單取消需狀態為「應到帳」或「排定發送」。其他狀態的帳單不支援取消。
```

### deterministic capability（原始碼逐字，整個 function body）


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


⚠️ Face responsibility 原文見上方「INSTANCE 列共用」一節。


## 3498（instance）

### frozen answer


```text
逾期費計算公式：租金 × 遲繳天數 × 費率%。遲繳天數 = 付款日 - 到期日 - 緩衝天數。
```

### deterministic capability（原始碼逐字，整個 function body）


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


⚠️ Face responsibility 原文見上方「INSTANCE 列共用」一節。


## 3499（instance）

### frozen answer


```text
手動到帳失敗時前端會顯示錯誤訊息，常見三種。
```

### deterministic capability（原始碼逐字，整個 function body）


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


⚠️ Face responsibility 原文見上方「INSTANCE 列共用」一節。


## 3519（general）

### frozen answer（逐字，**本列 spec 的全部**）


```text
點退帳單是租客同意點退後系統自動產生的，金額算法是：水電費等結算費用，加上設備損壞賠償和違約金，再扣掉應退還的押金。帳單總額是負數就代表要退錢給租客，是正數則代表押金扣完還不夠，租客需要補繳差額。舉例：押金 20,000 元、水電結算 700 元、設備賠償 5,000 元，帳單總額就是 -14,300 元，即退還租客 14,300 元。每個項目都會列在帳單明細裡，雙方都看得到。
```


⛔ 本列**不附** formatter——general row 的責任完全由 answer 承載。


## 4640（instance）

### frozen answer


```text
（空——本列為 empty-answer Face-entry anchor，責任由下方 capability 承載）
```

### deterministic capability（原始碼逐字，整個 function body）


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


⚠️ Face responsibility 原文見上方「INSTANCE 列共用」一節。


## 4656（instance）

### frozen answer


```text
（空——本列為 empty-answer Face-entry anchor，責任由下方 capability 承載）
```

### deterministic capability（原始碼逐字，整個 function body）


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


⚠️ Face responsibility 原文見上方「INSTANCE 列共用」一節。


## 4657（instance）

### frozen answer


```text
（空——本列為 empty-answer Face-entry anchor，責任由下方 capability 承載）
```

### deterministic capability（原始碼逐字，整個 function body）


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

### selection contract（原始碼逐字）


```python
"""**點退帳單 selection contract**（業主授權 2026-08-29，scope＝`POINT_REFUND_BILL_SELECTION`）。

## 缺口的精確位置（⚠️ 前一版診斷有誤，見下）

```text
✅ 金額能力**有**      _bill_amount_due → bill["total"] → 「• 金額」
✅ 狀態能力**有**      _format_bill_status
✅ 候選列表**有**      conversational_engine 的 result_mapping／candidate_cap
                      （⚠️ 前一版誤判為「查無實作」——搜尋範圍只掃了 services/jgb/，
                        沒掃 engine 層；正對照因此也選錯層）
⛔ 缺的是 **type 的使用**：全流程從未讀 `type`（2＝點退）
   ⇒ 候選標籤不含類型、收斂後也不驗證選中的那筆真的是點退帳單
```
⇒ first causal break ＝ **辨識／選出 type=2**，⛔ 不是金額能力。

## 契約（⚠️ 只管點退，⛔ 不得泛化成通用 bill selector）

```text
合約多筆帳單 → filter type == 2
  0 筆  → NOT_FOUND：明確回報找不到點退帳單，⛔ 不得 fallback 第一筆
  1 筆  → SELECTED
  >1 筆 → CANDIDATES：列出候選，⛔ 不得任取 data[0]

直接給 bill id → 取得該 bill → verify type == 2
  ⛔ 「bill_id 存在 ＋ query 說點退」**不足以**把它稱為點退帳單
```

## grounding provenance 不可斷（業主定案的真正要求）

要求**不是**「`_format_bill_status` 必須讀 type」，而是：

```text
最後 grounding 必須能證明所回答的那一列就是 type=2，
⛔ 不可以是 selection 過程看過 type、後面 provenance 又消失。
⇒ selected bill identity ＋ selected bill type ＋ amount/status 三者不能斷。
```
本模組的做法：selection 層產生**決定性的 type label 事實行**，與 identity／
amount／status 一起進 facts。
"""
from typing import Any, Dict, List, Optional, Tuple

#: `type` 的值域（鏡射 `BillApiController:173-197`；與 JgbMockTransport.MAPPING 同源）
BILL_TYPE_LABELS: Dict[int, str] = {
    1: "一般租金", 2: "點退", 3: "新增帳單",
    4: "罰款", 5: "儲值", 6: "押金設算息",
}
#: 點退
POINT_REFUND_TYPE = 2

#: 意圖詞（⚠️ 只用來判「這句在問點退帳單」，⛔ 不作為身分證明——身分一律看 type）
POINT_REFUND_KEYWORDS = ("點退", "退租結算", "點退帳單", "點退金額")

STATE_SELECTED = "selected"
STATE_NOT_FOUND = "not_found"
STATE_CANDIDATES = "candidates"
STATE_TYPE_MISMATCH = "type_mismatch"


def is_point_refund_intent(user_question: Optional[str]) -> bool:
    """這句是否在問點退帳單。⚠️ 只決定要不要啟動本契約，⛔ 不決定身分。"""
    q = user_question or ""
    return any(k in q for k in POINT_REFUND_KEYWORDS)


def bill_type(bill: Optional[dict]) -> Optional[int]:
    """讀 `type`。⚠️ 缺值回 None（⛔ 不代 1、⛔ 不猜）——未知不得被當成「不是點退」以外的任何結論。"""
    v = (bill or {}).get("type")
    if isinstance(v, bool):        # ⚠️ bool 是 int 的子類，先擋掉
        return None
    return v if isinstance(v, int) else None


def type_label(bill: Optional[dict]) -> str:
    t = bill_type(bill)
    if t is None:
        return "（系統未記錄類型）"
    return BILL_TYPE_LABELS.get(t, f"未知類型（{t}）")


def is_point_refund(bill: Optional[dict]) -> bool:
    """身分判定——**唯一**依據是 `type`。⛔ 標題含「點退」不算、⛔ 使用者說是不算。"""
    return bill_type(bill) == POINT_REFUND_TYPE


def _label(bill: dict) -> str:
    parts = [bill.get("title"), bill.get("sub_title")]
    total = bill.get("total")
    if isinstance(total, (int, float)):
        parts.append(f"NT$ {total:,.0f}")
    ident = bill.get("id")
    head = f"編號 {ident}" if ident is not None else None
    return "｜".join(str(p) for p in ([head] + parts) if p not in (None, ""))


def select_point_refund(rows: Optional[List[dict]]) -> Tuple[str, Optional[dict], List[dict]]:
    """回傳 `(state, selected, candidates)`。

    ⚠️ ⛔ **任何情況都不得回傳 `rows[0]` 作為預設**——那正是本契約要殺掉的舊行為。
    """
    items = [r for r in (rows or []) if isinstance(r, dict)]
    matched = [r for r in items if is_point_refund(r)]
    if not matched:
        return STATE_NOT_FOUND, None, []
    if len(matched) == 1:
        return STATE_SELECTED, matched[0], matched
    return STATE_CANDIDATES, None, matched


def verify_direct_bill(bill: Optional[dict]) -> str:
    """使用者直接指定某筆帳單時的身分查核。"""
    if not bill:
        return STATE_NOT_FOUND
    return STATE_SELECTED if is_point_refund(bill) else STATE_TYPE_MISMATCH


def type_fact_line(bill: dict) -> str:
    """進 grounding 的**決定性** type 事實行（provenance 不可斷的那一段）。"""
    return f"類型：{type_label(bill)}帳單（系統依帳單 type 判定）"


def not_found_facts() -> str:
    return ("查無點退帳單：這份合約底下沒有任何類型為「點退」的帳單。"
            "⚠️ 系統不會改以其他類型的帳單代答；若已完成點退仍查無，請確認點退流程是否已產生帳單。")


def candidates_facts(candidates: List[dict]) -> str:
    lines = [f"找到 {len(candidates)} 筆點退帳單，請確認要查詢哪一筆："]
    lines += [f"{i}. {_label(c)}" for i, c in enumerate(candidates, 1)]
    lines.append("（系統未自行選定任一筆。）")
    return "\n".join(lines)


def type_mismatch_facts(bill: dict) -> str:
    return (f"這筆帳單的類型是「{type_label(bill)}」，**不是點退帳單**。"
            f"系統不會以點退帳單的身分回答這筆資料；"
            f"若要查點退帳單，請提供該筆點退帳單的編號或改以合約查詢。")

```


⚠️ Face responsibility 原文見上方「INSTANCE 列共用」一節。
