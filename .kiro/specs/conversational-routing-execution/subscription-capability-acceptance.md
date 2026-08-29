# Subscription capability restoration — 收案紀錄（2026-08-29）

## 結案語（⚠️ 兩層，⛔ 不得互相代替）

> **2026-07 面向化遷移造成的 subscription execution-capability gap 已修復，
> 並完成真實唯讀 API acceptance；subscription Face 的 responsibility authority
> 尚未評估，兩者不得互相代替。**

```text
Subscription migration capability restoration  ✅ ACCEPTED within tested read-only scope
Subscription responsibility authority          ⚪ NOT EVALUATED
```

## 為什麼 authority 不能一起收

`subscription_diag` **不在** `PREENTRY_ROUTABILITY_FACETS`（allowlist 仍為
bill_diagnosis／billing_anomaly／contract_closeout），所以 resolver 直接回
`FACE_UNEVALUATED`，現行 commit 的本質是：

```text
retrieval / category nomination → first eligible Face commit      ← 現況
                        ⛔ 不是
nomination → responsibility resolver → authoritative commit
```

⚠️ **未來讀 telemetry 時的陷阱**：看到 `committed = subscription_diag`
**不等於** `responsibility_confirmed = true`。實測 authority 值就是 `unevaluated`。

## 證據鏈（真 API、唯讀、零寫入）

```text
env        USE_MOCK_JGB_API=false｜JGB_API_BASE_URL=https://www.jgbsmart.com
唯讀確認   get_subscription → _request → _send("GET", /api/external/v1/roles/{id}/subscription)
           subscription_diag 無 execute_endpoint、無 secondary ⇒ 單一 GET

Q「我的物件為什麼突然全部下架」
 top1 3506 sim=0.996
 → categories ['條件診斷：訂閱','條件診斷：物件','物件操作引導']（訂閱在首位）
 → nomination ['subscription_diag','estate_guide']
 → committed  subscription_diag（estate_guide 提名了但 first-commit-wins 下未觸及）
 → endpoint   jgb_subscription → success=True
 → branch     _diagnose_estates_delisted（E02）
三筆同式：3505→E01、3509→S01，皆 committed subscription_diag。
```

## 五項判準

| 判準 | 結果 |
|---|---|
| A nomination／responsibility | ✅ subscription_diag 先 commit，estate_guide 不再吃掉 |
| B API capability | ✅ 真實 GET success=True |
| C payload contract | ✅ **零 drift**（7 欄 ＋ estate_usage 三個子欄全存在） |
| D diagnostic reachability | ⚠️ **NOT EXERCISED**（非 FAIL）——見下 |
| E answer fidelity | ✅ 只用 payload 事實，無捏造 |

### D 的 claim ceiling

三個 diagnosis entry point 都 reachable 且在真實 payload 上產出事實；
但線上 role 是**健康**狀態（`is_subscribed=1`、`remain=134`／`limit=200`），
自然不會進入 `is_subscribed=0`／`remain<=0` 的 failure branch。

```text
✅ 判為 NOT EXERCISED         ⛔ 不判 PARTIAL FAIL
⛔ **未**修改 production 資料去製造失敗狀態
   失敗 branch 由 deterministic fixture 覆蓋（unit 層）
```

## 兩筆債，分開登（皆不擋收案）

```text
ONLINE_FAILURE_STATE_COVERAGE
  ・健康 production payload 已驗
  ・subscription failure-state 尚無真實線上樣本
  ・「方案失效時答得對」目前是**本地邏輯**保證，不是線上證據
  ・不影響本次 capability restoration acceptance

SUBSCRIPTION_PRESENTATION_FIDELITY
  ・services/jgb/subscription.py:103 硬編 `NT$`，忽略 payload 的 plan_currency='TWD'
    （今天相符是巧合，不是契約）
  ・plan_cycle 原樣輸出成 "/year"（英文混進中文答案）
  ・屬呈現／adapter fidelity debt，**不屬本次 migration authorization**
  ⛔ 業主明示不要順手修——混進來會污染這輪乾淨的 acceptance boundary
```

## 主線狀態更新

```text
Invariant 9                          ✅ PASS
21-row diagnostic census             ✅ COMPLETE
billing_invoice capability restore   ✅
billing_flow capability restore      ✅
subscription capability restore      ✅ ACCEPTED, read-only runtime smoke
subscription authority               ⚪ NOT EVALUATED
instance gate authorization          ⏸ PAUSED
3.4                                  ⏸ PAUSED
known migration capability gaps
  covered by this decision set       ✅ CLOSED
```

⚠️ 本次 smoke **不是**把 `subscription_diag` 加進 `PREENTRY_ROUTABILITY_FACETS`
的授權證據。是否納入 Stage-1 authority scope 是另一個決策與驗證問題。
