"""v6 **post-hoc regression ruler**（spec face-exit-before-grounding）。

```text
v6 is post-hoc
derived after v5 output was observed
cannot validate v5
cannot replace v5 machine verdict
cannot be cited as independent evidence
future runs only = regression evidence
```

## 推導來源（**只有這三個**，不看 v5 的回答文字）

```text
query obligation                本 case 委派後由 contract_closeout 負責的責任範圍
contract_closeout formatter     services/jgb/contracts.build_closeout_facts
fixture 678                     services/jgb/contract_fixtures.ContractFixtureTable
```

以 formatter ＋ fixture 實跑推得的 grounding 底稿（逐字）：

```text
合約「信義區套房A」目前狀態：已點交（執行中）。
到期退租：目前尚不可點退——合約目前狀態為「已點交（執行中）」，不在可點退的階段；
合約到期日為 2026/12/31，需到期前 30 天（2026/12/01）起才可發送點退。
提前解約：尚未發起。發起路徑：…租客回簽效期預設 30 天；…帳單需封存處理。
```

對照另一筆（600）：`中山區雅房B` ／ `歷史完成（已歸檔）` ／ `date_end 20251231`。

## 三件、也只有三件事

```text
1 正確 instance 的 grounding 有進 final answer
2 沒有把其他 fixture 的值當成這一筆
3 沒有退化成與 grounding 無關的 generic answer
```

⚠️ **不要求標題**：instance identity 已由 execution chain 獨立證明
（committed=contract_closeout ＋ transport 依識別過濾至單筆 678），
不為了尺再強迫最終答案複述標題。
⚠️ **不放 `rent`**：formatter 對此 action 根本不渲染租金——那正是 v5 被誤判的原因。
⚠️ **封閉集狀態詞不做阻斷型反向字面**（避免重演 v1／v2 的假紅）：
`歷史完成`／`已歸檔` 改列 `adjudication_flags`。
"""

from typing import Any


def v6_regression_ruler() -> Any:
    """回傳凍結的 `BrainGroundingAssertion`（regression 用）。"""
    from tests.support.brain_grounding import BrainGroundingAssertion

    return BrainGroundingAssertion(
        case="c4b-v6-regression", execution_face="contract_closeout", fixture_bill_id=678,
        user_turns=("幫我查點退帳單金額", "678"),
        answer_must_contain=(
            # ① current-state：formatter 首句即渲染，且 678／600 互異（討論性辨識力）
            ("已點交（執行中）", "已點交"),
            # ② timing：同一事實的三種等價表面形式，任一即可
            ("2026/12/31", "2026/12/01", "到期前 30 天"),
        ),
        # ② 只放**別筆專屬、且不會自然出現在正確對比句**的值
        answer_must_not_contain=("中山區雅房B", "2025/12/31", "18,000", "1,200"),
        foil_provenance={
            "中山區雅房B": "contract fixture 600.title",
            "2025/12/31": "contract fixture 600.date_end",
            "18,000": "contract fixture 600.rent ／ bills fixture 900001.total",
            "1,200": "bills fixture 900002.total",
        },
        # ③ 泛用退化標記
        generic_fallback_markers=("請洽客服", "請聯繫客服", "一般來說", "通常來說",
                                  "無法查詢", "查詢不到", "NO_MATCH"),
        # 封閉集狀態詞：命中只記錄、交人工，不判紅
        adjudication_flags=("歷史完成", "已歸檔"),
        literal_provenance={
            "已點交（執行中）": "build_closeout_facts 首句 get_current_stage(fixture 678)",
            "2026/12/31": "check_can_move_out(fixture 678).blockers（date_end 20261231 推得）",
        },
        known_non_discriminating=(
            "未要求標題：instance identity 由 execution chain 獨立證明，不由本尺重複要求",),
        rationale=("post-hoc regression guard；自 query obligation ＋ formatter contract ＋ "
                   "fixture 推導，非自 v5 回答反推"),
    )
