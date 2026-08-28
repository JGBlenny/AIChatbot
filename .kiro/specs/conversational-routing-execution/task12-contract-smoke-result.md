# 任務 12.1／12.2：Real API contract smoke

- 日期：2026-08-28｜對象：`https://www.jgbsmart.com`（production API boundary）
- 交付：`rag-orchestrator/tests/e2e/api/test_real_api_contract_smoke_req.py`
- 需求：R4.4（真 API **僅**用於確認 mock 假設與現實 contract 是否漂移）、R7.2（成本受控）

## 設計上的三個決定

```text
1 「宣告」不另立快照——直接用 `EXTERNAL_BILL_FIELDS`／`EXTERNAL_CONTRACT_FIELDS`。
  它們**就是** mock 假設本身（檔頭明文對齊 jgb2 formatBill 的白名單投影）。
  再抄一份等於讓兩份宣告各自漂移，屆時測試綠不代表 mock 正確。
2 只比**鍵的集合**，不碰資料值。真資料每天在變，拿值當基準會因為
  「業務照常運作」而變紅——那種紅不帶資訊，只會訓練人略過整區。
3 取**多列聯集**而非首列：單列可能因該筆狀態而缺欄，那不是 contract 漂移。
```

## 閘門（預設略過，不進 CI 阻擋路徑）

```text
需 RUN_E2E=1（conftest 既有）**且** ALLOW_REAL_JGB_API=1 **且** USE_MOCK_JGB_API=false
略過理由帶 `[gate]` 前綴 ⇒ 歸 gate_skipped，不混進 env_skipped
⚠️ 第三個條件不可省：替身回的是 fixtures 自己，拿它比 fixtures **恆真＝假綠**。
實測：無旗標 → passed=2 / gate_skipped=3｜帶旗標 → passed=5 / failed=0
```

### 順手修掉的 runner 缺陷

```text
`ALLOW_REAL_JGB_API` 原本**只在 host 端**被讀（決定要不要強制注入替身），
**沒有傳進容器** ⇒ 測試自己永遠看不到它，於是「開了旗標卻仍 gate_skipped」，
而略過訊息看起來完全正常。已在 scripts/run-tests.sh 補上 `-e ALLOW_REAL_JGB_API=1`。
```

## 實跑逼出的兩個 contract 事實

```text
① `jgb_bills` 只帶 role_id 會回 **401**
   {'code': 401, 'message': '請先登入以查詢您的個人資料。'}
   它需要收窄參數；production 的 contract_closeout 正是以 contract_ids={row.id} 呼叫。
   ⇒ smoke 必須複製**真實呼叫形狀**，否則測到的是自己編的用法，不是產線契約。
② **合約要簽完才會有帳單**（實測 bit=15 → 6／2 筆；bit=1 → 0 筆）。
   照序取前 N 筆會抽到一堆剛建立的合約，然後把「取樣抽歪」誤讀成「查無帳單」。
   ⇒ 取樣以 `bit_status & ContractBit.SIGNED` 決定性收窄，不是盲目加大 N。
```

## 結果（2026-08-28，www）

| 端點 | 呼叫形狀 | 漂移 |
|---|---|---|
| `jgb_contracts` | `role_id` | **無** |
| `jgb_bills` | `role_id` ＋ `contract_ids`（取樣 89207，n=6 列聯集） | **無** |
| `jgb_bill_detail` | `bill_id`（760804）＋ `role_id` | **無**（缺欄向）；多欄向僅報告不擋 |

## 這個否定結論憑什麼可信

```text
正對照組（**永遠會跑**，不需真 API）：
  test_drift_detector_sees_both_directions —— 餵合成資料，
  必須同時抓到「宣告有、真 API 沒有」與「真 API 長出未宣告欄位」，
  且無漂移時必須乾淨（否則它只是恆紅，一樣沒有鑑別力）。
  test_row_shape_violation_fails_loudly —— envelope 形狀不符要大聲失敗，
  ⛔ 不得靜默回 [] 讓「取不到資料」偽裝成「沒有漂移」。
突變（證明**真 API 那條路徑**真的在比，不是空跑）：
  往 EXTERNAL_BILL_FIELDS 塞一個真 API 不存在的欄位 →
  jgb_bills 與 jgb_bill_detail **雙雙轉紅**，且錯誤訊息帶實證
  （contract_ids=89207／n=6 列聯集／bill_id=760804）。已還原。
```

## 射程外

```text
· 只對 role_id=20151 取樣；其他業者的資料未涵蓋。
· `jgb_bill_detail` 的**多欄向**（真 API 長出新欄位）僅報告不擋——
  上游加欄是常態，擋它會製造噪音；缺欄向照擋。
· 本檔**不得**新增寫入端點：`_post_request` 的唯一呼叫者是 `/repairs`，
  不在本檔可達集合內。
```
