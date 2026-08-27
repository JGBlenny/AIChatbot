# 裁定 001 ④ 的 contract 已落地：`technical_fail_open` ≠ `model stay`

- 日期：2026-08-27
- 依據：`responsibility-governance-decision-record.md` §裁定 001 ④（**實作前必補的 contract**）
- 分支：`fix/retrieval-routing-stability`
- 動到的產線檔：`rag-orchestrator/services/responsibility.py`、`rag-orchestrator/routers/chat.py`

## 為什麼這件事要先做

裁定 001 的第 ②③④ 三條，正確性都建立在「分得出 verdict 出自誰」之上：

```text
② precedence      「已通過 responsibility applicability 的 Face 優先」
                  ——前提是 applicability 真的被評估過
③ 只有真實 stay    ——前提是「真實」有辦法在程式裡被指認
④ fail-open 分開   ——前提本身
```

現行 `stay` 是布林，`model stay` 與 `technical_fail_open` 兩者的 `verdict` 都是 `"stay"`，
**布林值分不出來**。先補這一格，後面三條才有東西可依。

## 落地的形狀

`ResponsibilityDecision` 新增 `decision_source`（四值），並把 authority 寫成述詞：

```text
model               模型回了可用 payload，verdict 出自模型          → **有** commit authority
technical_fail_open 規則取不到／brain 無回應／action 越界／例外      → 相容性 fallback，無 authority
contract_salvage    FACET_SCOPE_SALVAGE 救援（只產生 switch）        → 無 authority
guard               delegation cycle／未知或停用的 delegate          → 無 authority，**且不算 fail-open**
```

```text
decision.stay                  行為述詞——這條 chain 是否停在本面向（fail-open 也是 True）
decision.has_commit_authority  authority 述詞——verdict == stay ∧ source == model
EntryResolution.commit_source / .has_commit_authority   同一組語義，帶到 commit 層
```

⚠️ `guard` 刻意不歸進 fail-open：cycle 與未知 delegate 是**設定錯誤**，
混進技術故障率會把設定問題洗成「模型服務不穩」。

## 三個刻意的方向性選擇

```text
1 `stay` 保留，但降格為行為述詞並在 docstring 標明不得用於 authority
  ——fail-open 仍須照舊進場（相容性行為不改變），那格布林確實還有用途，
    錯的是拿它裁 authority。
2 兩個 `decision_source` 預設都往**失去** authority 的方向錯
  （`ResponsibilityDecision` 預設 technical_fail_open；`EntryResolution` 預設 None）
  ——漏填會少一次進場（可回復），而不是憑空取得越權（不可回復）。
3 telemetry 不再用 `reason.startswith("responsibility_contract")` 嗅探字串
  ——改一個 reason 字面值就會靜默翻轉 fail-open 統計，那是不該留的耦合。
  新增 `commit_source`／`has_commit_authority` 兩格：fail-open 的 stay 一樣會 commit，
  不分開記的話，「技術故障率」會被記成「面向命中率」。
```

## 驗證

```text
unit  1448 passed / 0 failed（基線 1439 → +9 條新測）
integration  同一檔在**乾淨基線**上重跑得到的失敗是本次結果的超集
             （baseline 6 failed ⊃ 本次 5 failed，差的那條在兩次間翻面＝既有 flaky）
             ⇒ 本次未引入 integration 失敗
突變測試（證明新量尺看得見已知病灶）
  M1 `has_commit_authority` 回頭吃布林          → 5 條轉紅
  M2 `EntryResolution` 改成「有 commit 就有 authority」→ 3 條轉紅
```

⚠️ 未做、且**不在**本步射程：nomination evidence 保留、gate 分岔、precedence 接線。
本步只補 contract，**沒有任何 routing 行為改變**——所有既有進場路徑逐字不動。

⚠️ 不變量稽核 3（容器與本地一致）因本次改了 `chat.py` 而 FAIL，
canary 前必須 `docker compose -f docker-compose.prod.yml up -d --build`，否則驗到舊 image。
（不變量 7 的 FAIL 落在 `services/jgb/fixtures.py`，本次未動該檔，為既有狀態。）
