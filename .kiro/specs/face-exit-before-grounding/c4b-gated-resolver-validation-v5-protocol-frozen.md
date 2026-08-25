# `C4b-gated-resolver-validation` **v5**（transport-complete vertical validation）protocol（**FROZEN**）

> 2026-08-25｜語言 zh-TW｜**本檔產生時未呼叫任何 OpenAI API**
> 前史（**皆不回填**）：v1 NOT_VALIDATED／v2 NOT_VALIDATED／v3 attribution `missing` 3/3／
> v4 delegation chain **validated**、full vertical slice NOT_VALIDATED（③④ 卡替身）

## 0. v5 與 v4 的唯一差別

```text
contracts 端點自方法級 mock **遷入 JGBMockTransport**，具備 production-equivalent filtering
（contract_ids CSV／keyword 對 title・address）——`_mock_get_contracts` 不吃這兩個參數，
恆回 2 筆，把「第二次依識別重查並收斂」這段 execution 行為吃掉了。
```

⚠️ **不動**：delegates／responsibility rules／resolver／candidate cap／required_slots／ruler／
categories／threshold；production gate 仍 false。

## 1. v4 已定案、v5 不重驗的部分

```text
✅ structured delegation output contract = VALIDATED
   （把 delegate_facet_key 納入 persona 宣告的輸出形狀 → raw missing 3/3 → kept 3/3）
```

v5 驗的是**尚未成立的那一段**：execution → grounding → grounded answer。

## 2. 完整 vertical slice（全段須成立）

```text
bill_diagnosis      → switch ＋ billing_anomaly
billing_anomaly     → switch ＋ contract_closeout
contract_closeout   → stay → **只** commit contract_closeout
jgb_contracts       → 第一次查詢回候選
使用者給識別（678）  → **第二次真 adapter 呼叫** → JGBMockTransport 依 request 過濾 → 恰一筆
grounding           → 該筆真 fixture
final answer        → 使用該 fixture 專屬的值
```

⚠️ 最後一段**仍不鎖句型**：沿用 C4b v2 尺——只鎖 actual fixture value／no wrong-instance／
no generic fallback（`信義區套房A`、`25,000|25000`；foil 為別筆 bills 金額）。

## 3. 參數（同 v4，未變更）

```text
3 runs／brain gpt-4o 0.4/400／factual 合成 gpt-4o-mini 0.2/800／semantic 不 retry
target ≤30、all ≤60（委派前檢查）／gate 只在測試行程開／USE_MOCK_JGB_API=true
delegates 與規則宣告仍只寫測試庫、結束還原
```

## 4. 裁決表

| 觀測 | 裁決 |
|---|---|
| 3/3 全段成立 | **transport-complete vertical slice VALIDATED**（僅此 predeclared case） |
| chain 成立但仍未收斂單筆 | 替身過濾仍不足 → 回頭查 request contract，**不得**改 ruler |
| 收斂但答案未用該筆值 | 回到 C4b 的原命題（brain 是否使用 grounding），依 v2 尺處置 |
| 三次不同類 | 不穩定 → `INSUFFICIENT_EVIDENCE`，不得以多數決宣稱 |

## 5. claim ceiling

```text
✅ 可說：在此 predeclared case 上，delegation → execution → grounding → answer 全段成立
❌ 不可說：diag-01 已修好／routing 已正確／可開 production gate／其他 Face 亦然／
          contracts 替身已與 production 逐條等價（保真度聲明見 contract_fixtures.py）
```
