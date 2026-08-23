# 任務 6 步驟①：holdout 來源 provenance／contamination 稽核

> 2026-08-24｜語言 zh-TW｜_Requirements: 9.2, 9.3_
> ⚠️ 本輪**只稽核來源**：未跑 extractor、未補 regex、未抽樣。

## 結論（先講）

> **`s3://jgb2-production-upload/assistant-reports/` 全池共 37 份，
> 100% 已參與規則／知識／回測建構——clean pool ＝ 0。首選來源不可用。**

## 實查（2026-08-24）

```text
bucket 全量遞迴列表：37 份
時間範圍：2026-07-22 11:29:15 ～ 2026-07-29 16:55:45
2026-07-29 16:55:45 之後：0 份（已 26 天無新回報）
```

對照 `docs/backtest/assistant-report-regression.md` 的處理批次表：

| 批次 | 涵蓋 | 筆數 | 實查對應 | 污染方式 |
|---|---|---|---|---|
| 20260724 | ～2026-07-24 11:38 | 30 | 29 ＋ 11:38:58 那筆 ＝ 30 | **R-38a～n：客服標準答案直接轉寫為 KB 條目**（`20260803_batch24_standard_answers.sql`），含「查帳單編號」錨點（R-38o，源自 #4「查帳單ID608169」） |
| 20260731 | 2026-07-24 16:43～07-29 16:55 | 7 | 7 | **R-31～R-37 → `20260731_assistant_report_fixes.sql`**；其 §3 正是本案根因（3402／3406／3519 補掛面向分類） |
| 20260803 | 無新回報，重跑 20260724 批 | 30 | 同上 30 份 | 同上 |
| 20260810 | 無新回報，37 份**全量重播** | 37 | 全池 | 全部成為 `corpus-20260810` 回測語料（`decision_replay`） |

**37 ＝ 30 ＋ 7，無一份落在批次之外。**

## 為何「真實客服回報」在本案**不能**視為 unseen

前案已發生 authored-from-evaluation 污染，本池三種都中：

```text
① 回報 → 標準答案 → 直接成為 KB（20260803 批 14 案）
② 回報 → routing 修正 → 補掛面向分類（20260731 §3；本 spec 的根因就是它）
③ 回報 → 全量重播 → 成為回測語料與量尺基準（corpus-20260810）
```

⚠️ 尤其 **BLAST #6「我要查帳單 編號 12345」與 R-38o 的「查帳單ID608169」同型**——
那個錨點正是從回報寫進 KB 的。若拿本池當 holdout，
等於**用被 candidate 訓練過的資料驗 candidate**。

## 其他真實語句來源（本機實查）

| 來源 | 現況 | 可用性 |
|---|---|---|
| `chat_history` | **0 列**（本機 admin DB）| 不可用（production 是否有資料未知）|
| `conversation_logs` | **0 列** | 同上 |
| `usage_events` | 5948 列，但**只有 `message_len`，無問句文字** | 不可用（計量表，設計上不存原文）|

## 選項（待業主裁示；本檔不自行選）

```text
A 等新回報累積        26 天零新增；到量時間不可預期
B 既有 corpus 未參與分區  ⚠️ 只能提供 **KB rows**，提供不了 **user utterances**；
                        「抽 KB → 照 wording 改寫成問句」已被 design 明列為換形式的 overfit
C production 的 chat_history／conversation_logs   本機為空，**需業主在 production 查證**
D 隔離作者撰寫（Req.9.3 允許：生成者須與規則作者隔離）
                        ⚠️ **我不能當作者**——ruleset 是我寫的，我來寫就不是隔離
```

⚠️ **不可接受**（design／Req.9.2 已明列）：用這 37 份當 holdout；
看過 extractor 結果再挑案例；從 KB wording 人工改寫成「未見問句」。
