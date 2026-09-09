"""unit：T1 追問契約 `ask_target`（Plan
`inputs/plan-walkthrough-fixes-batch2-20260909.md` §2）。

守的五件事：
1. **契約**：`ASK_TARGETS` 逐字等於 Plan 的凍結元組；`AgentOutput.ask_target`
   是選填欄位；strict schema 產得出來且 `ask_target` 走 `anyOf[封閉列舉, null]`
   覆寫（⛔ 不是把它從 `required` 拿掉——OpenAI strict 不收）。
2. **Verifier**：`kind=ask` 缺／值域外 ⇒ `SCHEMA/ask_target_invalid`；
   `_SCHEMA_CAUSE_HINTS` 有對應修法句（鍵集合等式由 `test_runtime_req.py` 守）。
3. **出口閘**：`_apply_ask_target_gate` 真值表（含「值域內 ⇒ 逐字不動」正對照）。
4. **載體**：`agent_state["last_ask_target"]` 的**三個寫點**——`_finalize`
   （`kind=ask` 寫值、否則 None）、`_finish_confirm_turn`（含各早退一律 None）、
   `handoff_cache` 重播出口（None）。
5. **對外契約不變**：`/mcp` `agent.turn` 仍七鍵，`ask_target` ⛔ 不對外。

⛔ 不接真 OpenAI、不接真 DB（沿用 `test_runtime_req.py` 的假件）。
"""
from __future__ import annotations

import json

import pytest

from services.agent import agent_rules
from services.agent.budget import Budget
from services.agent.identity import Identity
from services.agent.output_schema import ASK_TARGETS, AgentOutput, VerifierRules, VerifierVerdict
from services.agent.runtime import (
    ASK_TARGET_TEXT,
    LAST_ASK_TARGET_KEY,
    PENDING_CONFIRM_KEY,
    TurnResult,
    TurnTrace,
    _agent_output_response_format,
    _apply_ask_target_gate,
)
from services.agent.verifier import OutputVerifier
from services.presales_gate import FactClass

from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeClock,
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    _empty_provider,
    _fake_message,
    _fake_response,
)
from tests.unit.agent.test_verifier_req import _RULES_PATH

pytestmark = pytest.mark.unit

_REQ = "knowledge-outline-and-intent-architecture:T1"


# ---------------------------------------------------------------------------
# 1. 契約：值域凍結、欄位選填、strict schema 產得出來
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_ask_targets_is_the_frozen_plan_tuple_verbatim():
    """Plan §2 的凍結元組——⛔ 程式不得多、不得少、不得改順序。"""
    assert ASK_TARGETS == (
        "estate",
        "community",
        "address",
        "bill_id",
        "repair_id",
        "contract_id",
        "meter",
        "date",
        "description",
        "urgency",
        "confirm_intent",
        "choice",
    )
    assert len(set(ASK_TARGETS)) == len(ASK_TARGETS)  # 無重複


@pytest.mark.req(_REQ)
def test_ask_target_field_is_optional_and_not_a_closed_literal():
    """欄位型別刻意是 `Optional[str]`（同 `fact_class` 的理由）：型別若收成封閉
    列舉，非法值在建構 `AgentOutput` 就 raise，Verifier 永遠看不到「填錯」，
    `ask_target_invalid` 這條 fail-closed 分支也就測不到。"""
    out = AgentOutput.model_validate(
        {"kind": "answer", "sentences": [], "fact_class": "feature", "handoff_reason": None}
    )
    assert out.ask_target is None
    # 正對照：值域外的字串**建得起來**（由 Verifier／出口閘接手，⛔ 不在型別擋）
    bad = AgentOutput.model_validate(
        {
            "kind": "ask",
            "sentences": [{"text": "問一句。", "kind": "question", "refs": []}],
            "fact_class": "feature",
            "handoff_reason": None,
            "ask_target": "religion",
        }
    )
    assert bad.ask_target == "religion"
    # 反對照：**型別**這一層仍然擋非字串（`Optional[str]`），所以「填錯」只有
    # 「值域外的字串」這一種形狀會走到 Verifier。
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AgentOutput.model_validate(
            {"kind": "ask", "sentences": [], "fact_class": "feature",
             "handoff_reason": None, "ask_target": 123}
        )


@pytest.mark.req(_REQ)
def test_strict_schema_builds_with_anyof_enum_null_override():
    """`strict_json_schema` 把每一層 `required` 設成全部 properties——`ask_target`
    因此必須以 `anyOf[封閉列舉, null]` 表達「選填」，比照 `handoff_reason`。"""
    schema = _agent_output_response_format()["json_schema"]["schema"]
    assert schema["properties"]["ask_target"]["anyOf"] == [
        {"type": "string", "enum": list(ASK_TARGETS)},
        {"type": "null"},
    ]
    assert "ask_target" in schema["required"]
    assert schema["additionalProperties"] is False
    # 正對照：同一層的 `handoff_reason` 是同一種覆寫形狀（證明不是特例寫法）
    assert schema["properties"]["handoff_reason"]["anyOf"][1] == {"type": "null"}
    # strict schema 必須可序列化成 JSON（真線路是這樣送出去的）
    assert json.loads(json.dumps(schema)) == schema


# ---------------------------------------------------------------------------
# 2. Verifier：SCHEMA/ask_target_invalid
# ---------------------------------------------------------------------------
def _verifier() -> OutputVerifier:
    return OutputVerifier(VerifierRules.load(_RULES_PATH))


def _ask(ask_target, *, fact_class: str = FactClass.feature.value) -> AgentOutput:
    payload = {
        "kind": "ask",
        "sentences": [{"text": "請問是哪一戶？", "kind": "question", "refs": []}],
        "fact_class": fact_class,
        "handoff_reason": None,
    }
    if ask_target is not _MISSING:
        payload["ask_target"] = ask_target
    return AgentOutput.model_validate(payload)


_MISSING = object()


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("value", [_MISSING, None, "", "religion", "ESTATE", "estate "])
def test_verifier_rejects_ask_without_in_domain_target(value):
    """缺、None、空字串、值域外、大小寫不符、帶空白——全部同一個成因。

    （非字串在 pydantic 那一層就擋掉，見上一個測試的反對照。）"""
    verdict = _verifier().verify(
        _ask(value), {}, "信仰", None, resolved={}, resolve_errors={}
    )
    assert verdict.ok is False
    assert verdict.reason == "SCHEMA"
    assert verdict.schema_cause == "ask_target_invalid"


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("target", list(ASK_TARGETS))
def test_verifier_accepts_every_in_domain_target(target):
    """正對照：值域內的每一項都放行（證明上面那組拒絕不是恆真）。"""
    verdict = _verifier().verify(
        _ask(target), {}, "查一下", None, resolved={}, resolve_errors={}
    )
    assert verdict.ok is True, verdict.model_dump()


@pytest.mark.req(_REQ)
def test_sensitive_ask_still_reports_sensitive_topic_not_schema():
    """順序：敏感三關排在 `ask_target` 之前——敏感題就算 `ask_target` 也填錯，
    回的仍是 `SENSITIVE_TOPIC`。⛔ 不得用一個格式問題蓋掉一個內容問題。"""
    verdict = _verifier().verify(
        _ask(_MISSING, fact_class=FactClass.pricing.value),
        {}, "多少錢", None, resolved={}, resolve_errors={},
    )
    assert verdict.ok is False
    assert verdict.reason == "SENSITIVE_TOPIC"


@pytest.mark.req(_REQ)
def test_non_ask_kinds_are_untouched_by_the_new_check():
    """`kind != ask` ⇒ 這條檢查完全不參與（`ask_target` 填不填都一樣）。"""
    v = _verifier()
    payload = {
        "kind": "answer",
        "sentences": [{"text": "您好。", "kind": "greeting", "refs": []}],
        "fact_class": "other",
        "handoff_reason": None,
    }
    assert v.verify(AgentOutput.model_validate(payload), {}, "嗨", None,
                    resolved={}, resolve_errors={}).ok is True
    payload["ask_target"] = "religion"          # 值域外，但 kind 不是 ask
    assert v.verify(AgentOutput.model_validate(payload), {}, "嗨", None,
                    resolved={}, resolve_errors={}).ok is True


@pytest.mark.req(_REQ)
def test_schema_cause_hint_is_the_plan_sentence():
    """成因要有對應修法句，否則模型只會拿到保底句、永遠不知道要改哪裡。
    （鍵集合等式由 `test_runtime_req.py::…schema_cause…` 守，這裡釘逐字內容。）"""
    from services.agent.runtime import _SCHEMA_CAUSE_HINTS, _schema_reject_hint

    assert _SCHEMA_CAUSE_HINTS["ask_target_invalid"] == (
        "`kind=ask` 時 `ask_target` 必填且必須是值域內的項目，請改填。"
    )
    hint = _schema_reject_hint(
        VerifierVerdict(ok=False, reason="SCHEMA", schema_cause="ask_target_invalid")
    )
    assert "ask_target" in hint
    # ⛔ 回饋只有結構詞，不得夾帶原文（同 2.6 security review P2 的紀律）
    assert "信仰" not in hint


# ---------------------------------------------------------------------------
# 3. 出口閘真值表
# ---------------------------------------------------------------------------
def _ask_result(ask_target, *, kind: str = "ask") -> TurnResult:
    return TurnResult(
        kind=kind,
        answer="您信什麼宗教？",
        handoff=None,
        quick_replies=[],
        trace=TurnTrace(trace_id="t-1", final_kind=kind),
        ask_target=ask_target,
    )


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("value", [None, "", "religion", "ESTATE"])
def test_gate_replaces_ask_with_out_of_domain_target(value):
    out = _apply_ask_target_gate(_ask_result(value))
    assert out.answer == ASK_TARGET_TEXT
    assert out.outcome["state"] == "clarifying"
    assert out.outcome["expects"] == "text"
    assert "ask_target_invalid" in out.trace.violations
    # 值域外的字串 ⛔ 不得留在載體上（否則會被 `_finalize` 寫進 session 狀態）
    assert out.ask_target is None
    # ⛔ 不改 `kind`：這一回合仍然是在追問
    assert out.kind == "ask"


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("target", list(ASK_TARGETS))
def test_gate_leaves_in_domain_ask_verbatim(target):
    """正對照：值域內 ⇒ 逐字不動（證明上面那組替換不是恆真）。"""
    result = _ask_result(target)
    out = _apply_ask_target_gate(result)
    assert out.answer == "您信什麼宗教？"
    assert out.ask_target == target
    assert out.outcome is None
    assert out.trace.violations == []


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("kind", ["answer", "recommend", "handoff"])
def test_gate_never_touches_non_ask_kinds(kind):
    result = _ask_result(None, kind=kind)
    out = _apply_ask_target_gate(result)
    assert out.answer == "您信什麼宗教？"
    assert out.trace.violations == []


# ---------------------------------------------------------------------------
# 4. 載體：三個寫點
# ---------------------------------------------------------------------------
def _identity(**overrides) -> Identity:
    base = dict(
        vendor_id=1, target_user="property_manager", mode="b2b",
        api_key_id=1, session_id="mcp:1:1:s1", entry="mcp",
    )
    base.update(overrides)
    return Identity(**base)


def _runtime(*, provider=None, registry=None, verifier=None, budget=None, pool=None):
    from services.agent.runtime import AgentRuntime

    return AgentRuntime(
        provider or _empty_provider(),
        registry or FakeRegistry(),
        verifier or FakeVerifier(),
        FakeAssembler(),
        budget or Budget(),
        stage="M1",
        clock=FakeClock(),
        db_pool=pool,
    )


def _model_ask(ask_target, *, answer: str = "請問是哪一戶？"):
    payload = {
        "kind": "ask",
        "sentences": [{"text": answer, "kind": "question", "refs": []}],
        "fact_class": "feature",
        "handoff_reason": None,
        "ask_target": ask_target,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


@pytest.mark.req(_REQ)
async def test_finalize_writes_the_value_on_an_ask_turn():
    """寫點一：`kind=ask` ⇒ 寫模型填的那個值。"""
    state: dict = {}
    result = await _runtime(provider=FakeProvider([_model_ask("address")])).run_turn(
        _identity(), "信仰", state
    )
    assert result.kind == "ask"
    assert result.ask_target == "address"
    assert state["agent"][LAST_ASK_TARGET_KEY] == "address"


@pytest.mark.req(_REQ)
async def test_finalize_writes_none_on_a_non_ask_turn():
    """寫點一（反面）：非 ask 回合一律寫 `None`——⛔ 舊授權訊號不得殘留。"""
    from tests.unit.agent.test_runtime_req import _final_response

    state: dict = {"agent": {LAST_ASK_TARGET_KEY: "confirm_intent"}}
    result = await _runtime(provider=FakeProvider([_final_response(answer="好的。")])).run_turn(
        _identity(), "謝謝", state
    )
    assert result.kind == "answer"
    assert state["agent"][LAST_ASK_TARGET_KEY] is None


@pytest.mark.req(_REQ)
async def test_finalize_writes_none_when_the_gate_fires():
    """閘門命中（值域外）⇒ 載體歸零，⛔ 不把模型塞的字串寫進 session 狀態。"""
    state: dict = {"agent": {LAST_ASK_TARGET_KEY: "confirm_intent"}}
    result = await _runtime(provider=FakeProvider([_model_ask("religion")])).run_turn(
        _identity(), "信仰", state
    )
    assert result.answer == ASK_TARGET_TEXT
    assert state["agent"][LAST_ASK_TARGET_KEY] is None
    assert "ask_target_invalid" in result.trace.violations


@pytest.mark.req(_REQ)
async def test_confirm_segment_turn_writes_none_including_early_exits():
    """寫點二：確認段各出口一律寫 `None`——這條路徑 ⛔ 不經 `_finalize`。

    早退用「`pending_id` 不在狀態裡」那一格（`redeem_pending` 找不到 ⇒ 固定句），
    正對照組是同一份狀態換一句非機器值訊息 ⇒ 照常進模型。
    """
    from services.agent.tools.confirm import pending_id_for

    pid = pending_id_for("tok-not-in-state-0123456789")
    state: dict = {"agent": {LAST_ASK_TARGET_KEY: "confirm_intent", PENDING_CONFIRM_KEY: {}}}
    result = await _runtime().run_turn(_identity(), f"confirm_submit:{pid}", state)
    assert result.kind == "answer"
    assert state["agent"][LAST_ASK_TARGET_KEY] is None


@pytest.mark.req(_REQ)
async def test_select_segment_turn_writes_none():
    """寫點二（同一支收尾）：清單點選段也走 `_finish_confirm_turn`。"""
    state: dict = {"agent": {LAST_ASK_TARGET_KEY: "confirm_intent"}}
    result = await _runtime(registry=FakeRegistry()).run_turn(
        _identity(), "select:bill:900001", state
    )
    assert result.trace.select_type == "bill"
    assert state["agent"][LAST_ASK_TARGET_KEY] is None


@pytest.mark.req(_REQ)
async def test_handoff_cache_replay_exit_writes_none():
    """寫點三：快取重播出口既不經 `_finalize` 也不經 `_finish_confirm_turn`
    （plan-verifier r3 #1）——⛔ 不寫就會讓追問對象跨過一個完整回合殘留。"""
    budget = Budget(max_rewrites=0)
    state: dict = {}
    first = await _runtime(
        provider=FakeProvider([_model_ask("address")]),
        verifier=FakeVerifier([VerifierVerdict(ok=False, reason="UNCITED_ASSERTION")]),
        budget=budget,
    ).run_turn(_identity(), "這題會轉人嗎？", state)
    assert first.kind == "handoff"          # 落固定句 ⇒ 進 handoff_cache

    # 人為把載體塞成舊值，證明重播出口真的會把它清掉
    state["agent"][LAST_ASK_TARGET_KEY] = "confirm_intent"
    replay = await _runtime(budget=budget).run_turn(_identity(), "這題會轉人嗎？", state)
    assert replay.trace.llm_calls == 0      # 正對照：真的走了重播那條路
    assert state["agent"][LAST_ASK_TARGET_KEY] is None


# ---------------------------------------------------------------------------
# 5. 對外契約不變：`agent.turn` 仍七鍵
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
async def test_agent_turn_output_keys_unchanged_on_an_ask_turn():
    """`ask_target` 是**內部欄位**：即使這一回合真的是追問，`/mcp` 輸出仍七鍵。"""
    from services.agent import mcp_facade as F
    from tests.unit.agent.test_agent_turn_unit_req import (
        FakeEngine,
        _app,
        _deps,
        _identity as _facade_identity,
        _registry_with_agent_turn,
    )

    engine = FakeEngine()
    runtime = _runtime(provider=FakeProvider([_model_ask("bill_id")]))
    deps = _deps(_app(runtime=runtime, engine=engine))
    result = await _registry_with_agent_turn(deps).call(
        _facade_identity(session_id="s-ask"), F.AGENT_TURN_NAME,
        {"message": "帳單"}, 30.0, stage="M1",
    )
    assert result.ok is True, result.error
    assert set(result.data) == {
        "answer", "kind", "handoff", "quick_replies", "trace_id", "session_expired", "outcome",
    }
    assert result.data["kind"] == "ask"
    assert "ask_target" not in json.dumps(result.data, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 6. 政策定義句（⛔ 不舉例）
# ---------------------------------------------------------------------------
_POLICY_SENTENCES = (
    "只有名稱或編號、沒有動詞的一句話，先當物件、社區、帳單編號或修繕單號去查；查到就答，查無才追問。",
    "追問只能要 `ask_target` 值域內的東西，⛔ 不引入系統範圍外的主題。",
    "要資料或要選擇的句子用 `kind=ask`，⛔ 不用 `kind=answer` 提問。",
)

#: 與 `test_agent_rules_definitions_req.py` 同一組標記（⛔ 不另立第二把尺）。
_EXAMPLE_MARKERS = ("（如", "(如", "例如", "例：", "像是")


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("sentence", _POLICY_SENTENCES)
def test_policy_sentence_is_in_non_prospect_policy_only(sentence):
    """三句只加在 `_POLICY_TEXT_NON_PROSPECT`；`_POLICY_TEXT`（prospect，5.1 凍結）
    ⛔ 不動。"""
    assert sentence in agent_rules._POLICY_TEXT_NON_PROSPECT
    assert sentence not in agent_rules._POLICY_TEXT


@pytest.mark.req(_REQ)
@pytest.mark.parametrize("sentence", _POLICY_SENTENCES)
def test_policy_sentence_carries_no_example_marker(sentence):
    for marker in _EXAMPLE_MARKERS:
        assert marker not in sentence


@pytest.mark.req(_REQ)
def test_example_marker_ruler_is_not_a_no_op():
    """正對照：把「例如」塞進同一句，同一組標記必須抓得到。"""
    planted = _POLICY_SENTENCES[0] + "例如信仰。"
    assert any(marker in planted for marker in _EXAMPLE_MARKERS)


@pytest.mark.req(_REQ)
def test_prospect_policy_text_is_byte_identical_to_before_t1():
    """`_POLICY_TEXT` 逐字不動的另一面：三句都不在裡面（上面已驗）＋ 長度與
    `⛔` 計數仍在 5.1 的上限內（同 `test_agent_rules_definitions_req.py`）。"""
    assert len(agent_rules._POLICY_TEXT) <= 1584
    assert agent_rules._POLICY_TEXT.count("⛔") <= 8
