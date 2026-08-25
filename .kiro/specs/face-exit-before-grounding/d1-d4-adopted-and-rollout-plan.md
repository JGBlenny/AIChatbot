# D1–D4 正式採用 ＋ 第一版 rollout 規格

> 2026-08-25｜業主裁定：**不再把 D1–D4 當 blocker**，直接採為實作規格。
> 本檔是 implementation spec，不是研究報告。

## 1. 四條產品規則（採用）

```text
D1  retrieval／categories 只有 candidate nomination 權，不代表 Face responsibility 已成立。
D2  normal classification 的 Face，在 commit session 前必須通過 responsibility applicability。
D3  responsibility.delegates 是正式 machine-readable contract：target ＋ when。
D4  第一版**只改 normal classification**；trigger_facet_key／existing session／vision／
    transaction 維持現行 authority，不在這版一起重構。
```

⚠️ 跨線關係：`routing-authority-model` 的 normative 問題**由本裁定在 v1 範圍內定案**；
本檔**未**改動該線的 spec 狀態（若要同步，另行處理）。

## 2. 已完成的實作（1–5）

```text
1 D1–D4 採用                    本檔
2 production migration          database/migrations/seed_responsibility_delegates_v1.sql
                                （＋ _rollback.sql）——**只有兩條已實測的 edge**
3 global gate → facet-scoped    PREENTRY_ROUTABILITY_GATE ＋ **PREENTRY_ROUTABILITY_FACETS**
4 normal classification 接 resolver  `_resolve_pre_commit_candidate`（只有 stay 才 commit）
5 rollout telemetry             `_resolver_telemetry`（決策形狀，**不含聊天內容**）
```

### 2.1 migration（**尚未對 production 執行**）

```text
內容  (1) responsibility.delegates 兩條
      (2) persona 規則的「每輪輸出 JSON」形狀補 delegate_facet_key ＋三條語義規則
      ⚠️ (2) 是 (1) 生效的前提——v3 實證：模型只產出宣告形狀內的欄位
冪等  兩段皆有 NOT LIKE／IS NULL 前置；測試庫實跑二次無變化
回滾  rollback 後長度回到 888／698（逐位還原）；contract_closeout 全程未被觸及
帳本  runbook §17 範式的 INSERT 已寫在檔尾註解，執行時補
```

### 2.2 facet-scoped rollout（**fail-safe**）

```text
啟用條件  PREENTRY_ROUTABILITY_GATE=true **且** seed 面向 ∈ PREENTRY_ROUTABILITY_FACETS
未設 allowlist → **停用**（並印可觀測訊號）
```

⚠️ 刻意不讓單一 global bool 直接全開——否則 normal classification 全站每候選多一次 brain 呼叫。

Stage 1 建議值：

```text
PREENTRY_ROUTABILITY_GATE=true
PREENTRY_ROUTABILITY_FACETS=bill_diagnosis,billing_anomaly,contract_closeout
```

### 2.3 telemetry（可算出的率）

```text
每輪記錄  seed_facet／final_committed_facet／hop_count／hops[候選・scope・delegate・
          decision_source・fail_open]／fallback_reason／resolver_model_calls／resolver_latency_ms
可算      fail_open 率／switch_without_delegate 率／hop 分布／resolved-to-stay 率／
          fallback 率／每 request LLM 呼叫數／延遲
不記      問句與答案（這是 rollout 觀測，不是 Task 11 的對話品質基準）
```

## 3. 第 6 步（**需要授權才動**）

```text
① 對 production 執行 migration（DB 寫入）
② staging／production-equivalent acceptance：查點退帳單金額 → contract_closeout → 真 API
③ v6 regression（**只是 regression，不改寫 v5 歷史**）
④ 限縮 rollout：Stage 1 三個面向 → 觀察 telemetry → 確認 fail_open／
   switch_without_delegate／latency・cost／fallback 皆正常 → Stage 4 才擴其他 Face
```

⚠️ 依既有紀律：**prod 操作不代執行**——需要時我提供逐條指令與預期輸出，由業主自行執行。

## 4. 第一版**不做**（V2 再議）

```text
全站補 categories ／ 調 similarity threshold ／ 全 21 Faces applicability ／
多候選 arbitration ／ 改 trigger_facet_key ／ 改 existing-session authority ／
responsibility union 全面搜尋 ／ 把所有 persona rules 一次轉成 delegates
```
