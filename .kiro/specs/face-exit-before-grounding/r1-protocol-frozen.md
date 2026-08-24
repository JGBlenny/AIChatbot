# R1 protocol（**FROZEN，執行前凍結**）

> 2026-08-25｜語言 zh-TW｜**本檔產生時未呼叫任何 OpenAI API**
> 身分：**diagnostic reproduction，不是 acceptance benchmark**
> 前置：R4-static 三項已 FALSIFIED（research.md §7）

## 0. 這一輪只回答兩件事

```text
A  bill_diagnosis 的 **reroute residue**：第二次進場的輸入是否與第一次語義等價
B  billing_anomaly 是否在 **runtime** 也拒絕同一句 query（目前只有讀規則的推論）
```

⚠️ **不回答**「誰該擁有這句 query」。⚠️ **不改 production**、**不開 pre-entry gate 當修法**、
**不改任何 Face 規則使其變成 stay**。

## 1. 凍結參數（第一次 LLM 呼叫前 commit）

```text
model            gpt-4o                （PRESALES_SYNTH_MODEL；dev compose 已鏡射 prod）
temperature      0.4                   （ADVISOR_TEMP）
max_tokens       400
response_format  {"type": "json_object"}

query（逐字）    幫我查點退帳單金額
query sha1       執行時記錄並寫入 evidence（與本檔比對）

Face keys        A: bill_diagnosis      B: billing_anomaly
persona roles    A: pm_bill_diagnosis   B: pm_billing_anomaly
rules digests    執行時由 production `load_rules()` 取得後計 sha1，寫入 evidence
empty state      {"collected_fields": {}, "asked_count": 0, "recommended": False}
                 （＝production `_preentry_routable` 內建的 pre-entry state，逐字相同）
repetition       每個判定 seam **最多 3 次**
```

### system-context digest policy（**已知分歧，事前揭露**）

```text
in-session brain   get_system_context(db, state.face or _domain_key(config))
                   → key = topic_scope.category（如「條件診斷：帳單」）
pre-entry seam     get_system_context(db, cfg.key)
                   → key = **面向鍵**（如「bill_diagnosis」）
```

⚠️ 兩個 seam **餵的不是同一份 system context**。本檔不修正此分歧（那是 production 變更），
但 evidence **MUST** 逐次記錄實際使用的 key 與該 md 的 sha1；
若 B 的結果為 `stay`，此分歧即為首要 confounder，須在結論中原樣帶出。

## 2. 兩個 seam 的執行方式

### A. reroute residue（真 HTTP 路徑）

```text
每次 repetition = 一個**全新 session** 的單一請求：
  POST /api/v1/message  message=<query>  trigger_facet_key=bill_diagnosis  stream=false
  → entry #1（直達）brain 呼叫
  → 若 scope=switch → 引擎關會話 → 落回檢索 → 分類路由 entry #2 → brain 呼叫
spy 為 **passthrough**（記錄後原樣委派、原樣回傳），不改變任何行為
```

每次 brain 呼叫逐項記錄**七欄**（缺一不可）：

```text
face_identity          （由 session row 的 config_key ＋ rules digest 對照）
rules_digest           sha1
system_context_digest  sha1 ＋ 實際使用的 key
state                  【已知欄位】/【asked_count】/【已給過推薦】＋ session row 快照
query                  【使用者最新訊息】逐字
history                【最近對話】區塊（無則記 null）
scope_result           **由回應 JSON 取原始值**（正規化前）
```

### B. billing_anomaly responsibility（production 判定 seam）

```text
直接呼叫 production `routers.chat._preentry_routable(db_pool, cfg, user_message)`
  cfg = config_for_key(db, "billing_anomaly")
  user_message = 同一句 query
  rules / state / model 皆由該函式內部以 production 方式取得（不由本 harness 代餵）
```

⚠️ 該函式開頭讀 `PREENTRY_ROUTABILITY_GATE`，預設 `false` 會**立即回 True**。
本 harness **只在自己的行程內**設該環境變數為 `true`，以觸達判定邏輯：
**這是 diagnostic invocation，不是啟用 gate**——不改 `.env`、不改任何 compose、不進 production。

## 3. 重複次數的解讀（**不取多數決當真相**）

```text
3/3 switch   stable observed rejection
2/3 switch   rejection reproduced, stability not established
1/3 switch   unstable
0/3 switch   prior hypothesis not reproduced
```

## 4. 呼叫上限與 retry（**兩個命題分開記**）

```text
target_scope_calls      brain／判定 seam 的呼叫    hard cap **12**
all_provider_calls      共用 provider 的全部呼叫    hard cap **30**
```

⚠️ 兩者分開的理由（C4b 實測）：同一個 provider 也被適用性把關（gpt-4o-mini@32）與
兜底合成（gpt-3.5-turbo）使用；把它們混進同一個數字，會讓「花了幾次」與
「量到幾次」變成同一個無法拆解的命題。

```text
兩個上限皆在**委派真呼叫之前**檢查，超過即 raise，中止本輪
infra retry   僅事前列舉的 infra 類（timeout／rate limit／5xx／連線中斷），每次呼叫 ≤2
              semantic／assertion 結果**一律不 retry**
```

## 5. 事前鎖死的裁決表（跑完不得臨場發明分類）

```text
bill_diagnosis switch ＋ billing_anomaly switch
＋ R4 alternatives falsified ＋ reroute residue falsified
  → **RESPONSIBILITY_GAP_CONFIRMED** → STOP → 不選 owner
  → escalate to Responsibility Governance Decision Record（新 artifact，不改對方狀態）

bill_diagnosis switch ＋ billing_anomaly stay
  → RESPONSIBILITY_GAP **not confirmed**
  → 改查：為什麼正常 reroute 從未選中／留在 billing_anomaly

reroute 的輸入**實質不同**
  → residue／state 假說**重新開啟**；**不得**套用 RESPONSIBILITY_GAP

LLM 結果不穩定（見 §3）
  → **INSUFFICIENT_EVIDENCE**
```

## 6. claim ceiling

```text
✅ 可說：在**這一句 predeclared query** 上，某 Face 的 runtime scope 判定為 X（穩定度見 §3）
❌ 不可說：該 Face 對「這類問題」都會 X／routing 正確與否／誰應該接手／已找到 root cause
⚠️ R1 的 acceptance 是「證據足以歸因」，**不是**「diag-01 不再退出」（requirements R7）
```
