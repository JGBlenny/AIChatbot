# b2b e2e run2 執行參數（**凍結**）

> 2026-09-01｜⚠️ 跑之前寫定，⛔ 跑完不得修改

## 要驗的優化（單一變因）

```text
Reranker 從「靜默停用」恢復為「正常運作」
⛔ 未改任何知識、未改任何門檻、未改任何資料
⚠️ 唯一同期改動：semantic_reranker 自我復原（B），但本輪 reranker 全程可用，
   B 的重試路徑不會被觸發 ⇒ 對本輪結果無影響
```

## G2 六項健檢（跑之前，逐項）

```text
① 容器與 HEAD 一致        ✅ 不變量 3 PASS
② ANN vs 精確             ✅ 索引已全部 HNSW（不變量 26 PASS）
③ 門檻真的套上            ✅ 見下方實查值
④ 環境旗標實查            ✅ 見下方
⑤ 正對照題                ✅ 樣本內含已知會過的題（ts9950／ts9953／ts10152）
⑥ **Reranker 實際在跑**    ✅ 最後一次判定＝已啟用；[Finalize] rerank=5
```

## 環境（`printenv` 實查，⛔ 非 compose、⛔ 非程式預設）

```text
ENABLE_RERANKER            true
KB_SIMILARITY_THRESHOLD    0.65
HIGH_QUALITY_THRESHOLD     0.65
FORM_TRIGGER_THRESHOLD     0.75
PREENTRY_ROUTABILITY_GATE  **true**   ⚠️ 進場前責任判定是開的
FACET_SCOPE_SALVAGE        false
ENABLE_QUERY_REWRITE_B2B   false      ⇒ b2b 不做查詢改寫
RERANKER_RECHECK_INTERVAL  （未設，走程式預設 60 秒）
```

## 語料與入口

```text
樣本   b2b-batch-selection-rule.frozen.md 抽出的 35 題（⛔ 不換題不補題）
入口   POST /api/v1/message
身分   mode=b2b｜target_user=property_manager｜role_id=37305｜vendor_id=2
session 前綴 e2e-run2-（⛔ 避開 backtest_／loop_／smoke_ 內部保留字）
輪數   **3 輪**（第②層是 LLM 判定，非決定性）
```

## 對照組

```text
before  b2b-e2e-run1.json（同 35 題、同入口、同身分）
        ⚠️ **只有 1 輪**，且是在 reranker 停用期間跑的
        ⇒ 前後輪數不對稱，⛔ 報告時必須揭露
```

## Claim ceiling（⛔ 先寫，事後不得補）

```text
⛔ 不得宣稱「檢索品質改善了 X%」——命中真相尚未經業主確認，
   本輪只能報**路徑分布**與**引用知識的變化**
⛔ 不得外推到 b2c／SOP 路徑
⛔ 不得宣稱線上效果——線上尚未套用（image 未重 build、索引未重建）
⚠️ before 只有 1 輪 ⇒ 差異小於 after 三輪自身變異者，一律視為雜訊
```
