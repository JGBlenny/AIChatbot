# v6 **post-hoc regression ruler**（**FROZEN**；不執行付費回歸）

```text
v6 is post-hoc
derived after v5 output was observed
cannot validate v5
cannot replace v5 machine verdict
cannot be cited as independent evidence
future runs only = regression evidence
```

> 2026-08-25｜語言 zh-TW｜**本檔產生時未呼叫任何 OpenAI API**
> 實作 `tests/support/v6_regression_ruler.py`｜自驗 `tests/unit/api/test_v6_regression_ruler_req.py`（**7 passed**）
> ⚠️ v5 的 machine verdict（`NOT_VALIDATED／value_not_used`）**永久保留**，本檔不觸碰。

## 0. 作用域

> **只用來防止這條已實質成立的 vertical slice 日後回歸。**
> 不是新的 validation，不是用來洗掉 v5 的 machine red。

## 1. 推導來源（**只有這三個**，不從 v5 回答反推）

```text
query obligation                委派後由 contract_closeout 負責的責任範圍
contract_closeout formatter     services/jgb/contracts.build_closeout_facts
fixture 678                     services/jgb/contract_fixtures.ContractFixtureTable
```

以 formatter ＋ fixture **實跑**推得的 grounding 底稿（逐字）：

```text
合約「信義區套房A」目前狀態：已點交（執行中）。
到期退租：目前尚不可點退——合約目前狀態為「已點交（執行中）」，不在可點退的階段；
合約到期日為 2026/12/31，需到期前 30 天（2026/12/01）起才可發送點退。
提前解約：尚未發起。發起路徑：…租客回簽效期預設 30 天；…帳單需封存處理。
```

對照另一筆（600）：`中山區雅房B`／`歷史完成（已歸檔）`／`date_end 20251231`。

## 2. 機器只驗三件事

```text
1 正確 instance 的 grounding 有進 final answer
2 沒有把其他 fixture 的值當成這一筆
3 沒有退化成與 grounding 無關的 generic answer
```

## 3. 尺（凍結）

```text
answer_must_contain（AND；每組內 OR）
  ① current-state   ("已點交（執行中）", "已點交")
  ② timing          ("2026/12/31", "2026/12/01", "到期前 30 天")

answer_must_not_contain（阻斷；**只放別筆專屬、且不會自然出現在正確對比句**的值）
  中山區雅房B（600.title）／2025/12/31（600.date_end）／
  18,000（600.rent・900001.total）／1,200（900002.total）

adjudication_flags（**非阻斷**，命中只記錄交人工）
  歷史完成 ／ 已歸檔        ← 封閉集狀態詞，不做阻斷型反向字面

generic_fallback_markers
  請洽客服／請聯繫客服／一般來說／通常來說／無法查詢／查詢不到／NO_MATCH
```

### 三個刻意的取捨

```text
❌ 不要求標題    instance identity 已由 execution chain 獨立證明
                （committed=contract_closeout ＋ transport 依識別過濾至單筆 678），
                不為了尺再強迫最終答案複述標題
❌ 不放 rent     formatter 對此 action 根本不渲染租金——那正是 v5 被誤判的成因
❌ 封閉集狀態詞不阻斷  避免重演 v1／v2「對比句撞反向字面」的假紅
```

## 4. 零成本自驗（**先成立才凍結**，7 passed）

```text
fixture-grounded correct answer      → PASS
correct answer without rent          → PASS   ← v5 誤判的那一格
answer using one valid timing fact   → PASS
generic answer                       → FAIL（value_not_used）
other-fixture answer                 → FAIL（wrong_instance）
對比句提到「歷史完成」                 → PASS，且記為 adjudication hit
未複述標題                            → PASS
```

## 5. 何時跑

```text
下一次 routing／resolver／formatter／fixture 有變更時，作為 regression 再跑
⚠️ **現在不跑**——不為了補一個綠燈而花錢
```
