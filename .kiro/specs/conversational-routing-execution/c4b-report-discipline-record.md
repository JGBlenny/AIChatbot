# 6.4 報告紀律落實紀錄

> 2026-08-25｜語言 zh-TW｜依據：業主 6.3 簽核（`c4b-release-gate-report.md`）
> 本檔**未呼叫任何 OpenAI API**，未跑任何測試以外的東西。

## 唯一合規表述

> **執行鏈閉環已證實，最終答案能力尚未放行。**

**SHALL NOT** 表述為「最終答案能力已證實」。

## 可引用的正式結算（唯一版本）

```text
2 cases machine-confirmed 3/3；
1 case substantively accepted after a predeclared 6.3 ruler-false-red adjudication；
1 case remains unaccepted.
```

| case | 裁決 |
|---|---|
| `c4b-diag-02` | ACCEPTED — machine 3/3 ＋ human direction accepted |
| `c4b-anom-02` | ACCEPTED — machine 3/3 |
| `c4b-anom-01` | ACCEPTED after 6.3 adjudication — 原 machine `value_not_used` 保留；正式歸類 `ruler_false_red` |
| `c4b-diag-01` | NOT ACCEPTED — first execution `INDETERMINATE / HARNESS_EVIDENCE_LOSS`；replay 證實 `face_exit_before_grounding` |

```text
C4a                      CONFIRMED
C4b                      NOT PASSED
production-facing gate   CLOSED（任務 4.6／8／9 維持不得上線；9.4 前置未滿足）
```

⚠️ **不得**表述為「3/4 cases passed」——`diag-01` 第一次沒有有效 outcome，
而 diagnostic replay 不是 acceptance rerun。

## 紀律不是靠自律：已落成機器檢查

`tests/unit/_meta/test_c4b_report_discipline_req.py`（3 passed）

```text
① 掃本 spec 目錄所有 Markdown：禁用表述只能以「被禁止」的身分出現
   （同一行須有 SHALL NOT／不得／❌／禁止／不可），否則紅
② 簽署版報告必須明載唯一合規表述
③ spec.json 的 release_gate.blocked_until_released 必須仍含 4.6／8／9
```

⚠️ 若日後 C4b 真的通過並經業主放行，應**明確刪除或改寫**該檔，
不得讓它默默失效——那會讓「紀律還在」變成無法查證的宣稱。

## 證據與 provenance（固定，不再變動）

```text
evidence/c4b-first-execution.json                 第一次 6.2；external_calls 遺失（估 19–20）
evidence/c4b-diag01-diagnostic-replay.json        replay；external_calls 精確 5
evidence/c4b-diag01-diagnostic-replay-stdout.log  完整 stdout（兩行 scope=switch 在內）

53b513c  harness 落地（hard-cap 在委派前檢查，第一次執行時即存在）
75cfed7  evidence instrumentation 修補——**早於** replay 結果
8d160bd  diagnostic replay 發現 face_exit_before_grounding
fdc9019  6.3 報告草稿
```

## 已知且保留的缺口（不修飾）

```text
① 第一次執行的 external_calls 精確值**永久遺失**（估 19–20）。
   「無法證明精確用了幾次」≠「無法證明沒超過 30」——hard-cap 機制當時確實存在。
② spy 掛共用 provider，call_log 會計入非 C4b 元件的呼叫 → 上限為**保守**方向，
   但「呼叫數＝C4b 呼叫數」不成立。
③ diag-01 第一次執行的失敗原文**不存在**，且不得以 replay 回填。
④ face_exit_before_grounding 的 **root cause 未 adjudicated** → 另立工作線。
```

## 本工作線的收束

```text
6.1 ✅ 尺（v1 凍結未執行 → 執行前 audit 反證 → v2）
6.2 ✅ harness 實作並執行一次（真 OpenAI）；**結果 NOT PASSED**
6.3 ✅ 報告產出並經**業主簽核**：gate CLOSED
6.4 ✅ 報告紀律落實（本檔 ＋ 機器檢查）

→ 本線在 C4b 這一段**到此收束**：不再跑模型、不修 scope、不補 diag-01。
→ face_exit_before_grounding 交新工作線，問題重新定義為：
   「為什麼一個產品上應由 bill_diagnosis 處理、且 execution plumbing 已證實可閉環的
     query，production brain 會在 grounding 前兩度判 scope=switch？」
```
