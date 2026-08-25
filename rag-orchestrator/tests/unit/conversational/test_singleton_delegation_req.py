"""unit：singleton delegation resolution（業主 2026-08-26 裁定｜P3 實測後新增）。

## 為什麼有這條規則

P3 第 1 次付費執行（gpt-4o-mini，3/3）：模型**穩定判對** `scope=switch`，
卻把 `delegate_facet_key` 回成**空字串**——它知道「不該由我接」，
但沒有把**唯一合法的 machine key 再複述一次**。

分工因此改成：

```text
是否離開目前 Face      → 模型決定（語義）
離開後合法目標有哪些    → responsibility contract 決定
合法目標**只有一個**   → 程式決定性解析（不勞模型複述）
```

## 規則刻意很窄——三條同時成立才補

```text
verdict == 'switch' ∧ delegate_drop_reason == 'missing' ∧ len(allowed) == 1
```

以下**一律不補**，且各自語義必須保留：
  · 白名單多個 → 不得選第一個（那是替模型做選擇）
  · 模型填了不合法目標（not_allowed）→ 不得改成唯一值（那是替錯誤決定背書）
  · stay → 不轉交
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.conversational_config import ConversationalConfig
from services.llm_answer_optimizer import StepResult
from services.responsibility import evaluate_responsibility

pytestmark = pytest.mark.unit


def _cfg(key="seed", delegates=()):
    return ConversationalConfig(
        key=key, persona_role=f"pm_{key}", enabled=True,
        topic_scope={"mode": "category", "category": f"cat_{key}"},
        responsibility={"delegates": [{"target": t} for t in delegates]})


def _brain(scope, raw_delegate, allowed):
    """以**真解析層**產出 StepResult——不手刻，避免測到假的正規化。"""
    from services.llm_answer_optimizer import LLMAnswerOptimizer
    payload = {"action": "ask", "next_question": "q", "scope": scope}
    if raw_delegate is not None:
        payload["delegate_facet_key"] = raw_delegate
    result = LLMAnswerOptimizer._parse_conversational_step(payload, list(allowed))
    brain = MagicMock()
    brain.conversational_step_result = AsyncMock(return_value=result)
    return brain, result


async def _decide(scope, raw_delegate, delegates):
    brain, result = _brain(scope, raw_delegate, delegates)
    with patch("services.conversational_rules.load_rules", new=AsyncMock(return_value="R")), \
         patch("services.system_context.get_system_context", new=AsyncMock(return_value="C")):
        d = await evaluate_responsibility(MagicMock(), _cfg(delegates=delegates),
                                          "幫我查點退帳單金額", optimizer=brain)
    return d, result


# ── 補：模型沒填 ＋ 唯一合法目標 ─────────────────────────────────────────

@pytest.mark.req("conversational-routing-execution:5.2")
@pytest.mark.parametrize("raw", [None, "", "   "])
async def test_switch_missing_delegate_with_single_allowed_uses_contract(raw):
    """缺鍵／空字串／全空白 → 皆屬 `missing`，由契約決定性補上。

    ⚠️ 空字串正是 P3 實測 mini 的真實輸出（3/3）。
    """
    d, result = await _decide("switch", raw, ("billing_anomaly",))
    assert result.delegate_drop_reason == "missing"
    assert not d.stay and d.delegate_to == "billing_anomaly"
    assert d.delegate_source == "contract_singleton"


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_model_supplied_valid_target_wins():
    d, result = await _decide("switch", "billing_anomaly", ("billing_anomaly",))
    assert result.delegate_drop_reason is None
    assert d.delegate_to == "billing_anomaly" and d.delegate_source == "model_delegate"


# ── 不補：四種必須保留原語義的情形 ──────────────────────────────────────

@pytest.mark.req("conversational-routing-execution:5.2")
async def test_invalid_target_is_not_rewritten_to_the_singleton():
    """模型**填了**不合法目標 ≠ 沒填。不得自動改成唯一值——那是替錯誤決定背書。"""
    d, result = await _decide("switch", "self_invented_face", ("billing_anomaly",))
    assert result.delegate_drop_reason == "not_allowed"
    assert d.delegate_to is None and d.delegate_source is None


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_two_allowed_delegates_never_auto_picks():
    d, _ = await _decide("switch", "", ("billing_anomaly", "contract_closeout"))
    assert d.delegate_to is None and d.delegate_source is None


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_zero_allowed_delegates_never_delegates():
    d, _ = await _decide("switch", "", ())
    assert d.delegate_to is None and d.delegate_source is None


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_stay_never_delegates_even_with_single_allowed():
    d, _ = await _decide("stay", "", ("billing_anomaly",))
    assert d.stay and d.delegate_to is None and d.delegate_source is None


@pytest.mark.req("conversational-routing-execution:5.2")
async def test_stay_with_model_supplied_target_still_does_not_delegate():
    """stay 時模型即使填了合法目標也不轉交（正規化本來就會丟，語義記為 scope_not_switch）。"""
    d, result = await _decide("stay", "billing_anomaly", ("billing_anomaly",))
    assert result.delegate_drop_reason == "scope_not_switch"
    assert d.stay and d.delegate_to is None and d.delegate_source is None
