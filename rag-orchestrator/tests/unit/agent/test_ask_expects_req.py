"""unit：#4 追問對象 `photo`／`document` → `outcome.expects` 的 `image`／`file`；
#8 `attachment_purpose="document"` 但無附件 ⇒ 視同一般回合（Plan 第六批單元 B，
`inputs/plan-walkthrough-fixes-batch6-20260910.md`）。

守的事：
1. **值域**：`OUTCOME_EXPECTS` 六值逐字凍結；`_ASK_TARGET_EXPECTS` 是「哪個追問
   對象要傳檔」的**唯一**對映（鍵 ⊆ `ASK_TARGETS`、值 ⊆ `OUTCOME_EXPECTS`）。
2. **對映**：`photo`⇒`image`、`document`⇒`file`；**正對照** `estate`⇒`text`
   （表外的對象照舊由 `quick_replies` 決定）——沒有這一條的話，一個「整支都回
   image」的壞對映也能讓上面兩條過。
3. **贏過 `quick_replies`**：這一輪要的是一個檔案，出幾顆選項鍵不改變這件事。
4. **接線**：真的跑一輪模型迴圈，`kind=ask`＋`ask_target=photo` ⇒
   `result.outcome["expects"] == "image"`（⛔ 不是只驗純函式）。
5. **接線**：`verify(..., document_turn=)` 只在**真的有文件事實進場**的回合為
   `True`（單元 E 的 ⑥' 禁詞閘靠它開關）；一般回合一律 `False`。
6. **#8**：門面收到 `attachment_purpose="document"` 卻一張照片、一份檔案都沒帶
   ⇒ `run_turn` ⛔ 不會收到 `document=`（寫入面工具因此照樣可見、trace 也不會有
   `has_document`），只在 `TurnResult.trace` 記一個 `attachment_purpose_ignored`。
   **正對照**：真的帶了檔案時 `document=` 有傳、旗標不亮。

⛔ 不接真 OpenAI、不接真 DB（沿用既有假件）。
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from services.agent import mcp_facade as F
from services.agent.budget import Budget
from services.agent.output_schema import ASK_TARGETS
from services.agent.runtime import (
    OUTCOME_EXPECTS,
    AgentRuntime,
    DocumentTurnInput,
    TurnResult,
    TurnTrace,
    _ASK_TARGET_EXPECTS,
    default_outcome,
)

from tests.unit.agent.test_agent_turn_unit_req import FakeEngine, _app, _deps
from tests.unit.agent.test_document_turn_req import (
    _OK_FILE_URL,
    _call_turn,
    _identity as _doc_identity,
    _registry_with_turn,
)
from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeClock,
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    VerifierVerdict,
    _fake_message,
    _fake_response,
    _final_response,
    _identity,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:linebot-20260910-ask-expects"),
]


# ---------------------------------------------------------------------------
# 1. 值域與對映的封閉性
# ---------------------------------------------------------------------------
def test_outcome_expects_is_the_frozen_six_value_tuple():
    """⛔ 不得多、不得少、不得改順序（呼叫端畫面按這張表分支）。"""
    assert OUTCOME_EXPECTS == ("text", "choice", "button", "image", "file", "none")
    assert len(set(OUTCOME_EXPECTS)) == len(OUTCOME_EXPECTS)


def test_ask_target_expects_is_the_single_source_of_which_targets_want_a_file():
    assert _ASK_TARGET_EXPECTS == {"photo": "image", "document": "file"}
    # 兩端都要對得上既有的封閉值域，⛔ 不得自成一套字串。
    assert set(_ASK_TARGET_EXPECTS) <= set(ASK_TARGETS)
    assert set(_ASK_TARGET_EXPECTS.values()) <= set(OUTCOME_EXPECTS)


def test_photo_and_document_are_ask_targets():
    assert "photo" in ASK_TARGETS and "document" in ASK_TARGETS


# ---------------------------------------------------------------------------
# 2. `default_outcome` 真值表（含正對照）
# ---------------------------------------------------------------------------
def _result(kind: str, *, ask_target=None, quick_replies=None) -> TurnResult:
    return TurnResult(
        kind=kind, answer="內容", handoff=None,
        quick_replies=list(quick_replies or []),
        trace=TurnTrace(trace_id="t"), ask_target=ask_target,
    )


@pytest.mark.parametrize("target,expected", [
    ("photo", "image"),
    ("document", "file"),
    ("estate", "text"),        # 正對照：表外的對象照舊
])
def test_ask_target_maps_to_expects(target, expected):
    assert default_outcome(_result("ask", ask_target=target))["expects"] == expected


def test_attachment_target_wins_over_quick_replies():
    """出幾顆選項鍵不改變「這一輪要的是一個檔案」。"""
    out = default_outcome(_result("ask", ask_target="photo", quick_replies=[{"label": "a", "value": "a"}]))
    assert out["expects"] == "image"
    # 正對照：同樣有選項鍵、但對象在表外 ⇒ 仍是 choice（證明不是整支被蓋掉）
    out2 = default_outcome(_result("ask", ask_target="estate", quick_replies=[{"label": "a", "value": "a"}]))
    assert out2["expects"] == "choice"


def test_answer_kind_also_honours_the_mapping_and_handoff_is_untouched():
    assert default_outcome(_result("answer", ask_target="document"))["expects"] == "file"
    assert default_outcome(_result("handoff"))["expects"] == "none"


def test_no_ask_target_attribute_at_all_does_not_explode():
    """`mcp_facade._outcome_of` 會拿舊的假 runtime 物件進來（沒有 `ask_target`）。"""
    stub = SimpleNamespace(kind="answer", quick_replies=[])
    assert default_outcome(stub)["expects"] == "text"


# ---------------------------------------------------------------------------
# 3. 接線：真的跑一輪模型迴圈
# ---------------------------------------------------------------------------
def _ask_response(ask_target: str, text: str = "請拍一張照片給我"):
    payload = {
        "kind": "ask",
        "sentences": [{"text": text, "kind": "greeting", "refs": []}],
        "fact_class": "feature",
        "handoff_reason": None,
        "ask_target": ask_target,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


def _runtime(provider, registry=None, verifier=None):
    return AgentRuntime(
        provider, registry or FakeRegistry(),
        verifier or FakeVerifier([VerifierVerdict(ok=True)] * 4), FakeAssembler(),
        Budget(), stage="M1", clock=FakeClock(),
    )


class _RegistryWithSpecs(FakeRegistry):
    """文件回合會問 `registry.specs_for` 算「寫入面工具」（`doc_write_face`）——
    假 registry 補上這一支。⛔ 不在正式碼加預設值：Runtime 忘了算的話應該當場炸。"""

    def specs_for(self, identity, stage, *, readonly_view=False, for_model=False):
        return [{"name": "kb.get", "scope": "read"}]


@pytest.mark.parametrize("target,expected", [
    ("photo", "image"),
    ("document", "file"),
    ("estate", "text"),        # 正對照
])
async def test_turn_outcome_expects_end_to_end(target, expected):
    rt = _runtime(FakeProvider([_ask_response(target)]))
    result = await rt.run_turn(_identity(), "牆壁裂開了", {"agent": {}})
    assert result.kind == "ask"
    assert result.ask_target == target
    assert result.outcome["state"] == "clarifying"
    assert result.outcome["expects"] == expected


# ---------------------------------------------------------------------------
# 4. #8：`attachment_purpose="document"` 但無附件 ⇒ 視同一般回合
# ---------------------------------------------------------------------------
class _SpyRuntime:
    """記下 `run_turn` 收到的具名參數；回一個形狀夠用的假結果。"""

    def __init__(self):
        self.kwargs: dict = {}
        self.result = SimpleNamespace(
            answer="ok", kind="answer", handoff=None, quick_replies=[],
            trace=SimpleNamespace(trace_id="t"), outcome=None,
        )

    async def run_turn(self, identity, message, state, **kw):
        self.kwargs = dict(kw)
        return self.result


async def test_document_purpose_without_any_attachment_runs_as_a_normal_turn():
    spy = _SpyRuntime()
    registry = _registry_with_turn(_deps(_app(runtime=spy, engine=FakeEngine())))

    out = await _call_turn(registry, _doc_identity(), "我想問租約怎麼算",
                           attachment_purpose="document")

    assert out.ok is True                       # ⛔ 不是 INVALID_INPUT
    assert "document" not in spy.kwargs         # ⛔ 不走文件回合閘
    assert "image" not in spy.kwargs            # 也不會被誤導成照片回合
    # 一般回合 ⇒ 沒有文件 trace 四鍵中的 `has_document`
    assert not getattr(spy.result.trace, "has_document", False)
    # 稽核旗標：呼叫端送了那個鍵卻沒送附件是設定錯誤，⛔ 不該是無聲的
    assert spy.result.trace.attachment_purpose_ignored is True


async def test_document_purpose_with_a_real_file_still_takes_the_document_path(monkeypatch):
    """正對照組：真的帶了檔案 ⇒ `document=` 有傳、旗標不亮。
    （少了這一條，一個「永遠不走文件線」的壞改動也能讓上面那條過。）"""
    spy = _SpyRuntime()
    prepared = DocumentTurnInput(status="ok", kind="contract", facts="租約重點：…",
                                 pages_seen=1, pages_total=1)

    async def _fake_prepare(image_urls, file_urls, *, db_pool=None, **kw):
        return prepared, 0.0

    monkeypatch.setattr(F, "prepare_document_turn", _fake_prepare)
    registry = _registry_with_turn(_deps(_app(runtime=spy, engine=FakeEngine())))

    out = await _call_turn(registry, _doc_identity(), "這份租約幫我看一下",
                           file_urls=[_OK_FILE_URL], attachment_purpose="document")

    assert out.ok is True
    assert spy.kwargs.get("document") is prepared
    assert getattr(spy.result.trace, "attachment_purpose_ignored", False) is False


async def test_trace_field_defaults_to_false():
    """`TurnTrace` 的預設值＝沒發生（⛔ 不是 None，讓下游不必判三態）。"""
    assert TurnTrace(trace_id="t").attachment_purpose_ignored is False


# ---------------------------------------------------------------------------
# 5. 接線：`verify(..., document_turn=)`（單元 E 的 ⑥' 開關）
# ---------------------------------------------------------------------------
async def test_verify_gets_document_turn_true_only_when_document_facts_are_in_play():
    """文件回合（有 `document` 且 `facts` 非空）⇒ `True`；一般回合 ⇒ `False`。

    ⚠️ 兩個條件都要：`facts` 為空的文件回合走 `_document_program_turn` 的固定句、
    Verifier 根本不跑，所以「有沒有 document 物件」不是這一格的正確判準。
    """
    doc = DocumentTurnInput(status="ok", kind="contract", facts="租約重點：押金兩個月。",
                            pages_seen=1, pages_total=1)
    v_doc = FakeVerifier([VerifierVerdict(ok=True)])
    await _runtime(FakeProvider([_final_response(answer="這份租約的重點如下")]),
                   _RegistryWithSpecs(), v_doc).run_turn(
        _identity(), "幫我看這份租約", {"agent": {}}, document=doc)
    assert v_doc.calls, "Verifier 沒被呼叫——前提不成立"
    assert v_doc.calls[0]["document_turn"] is True

    # 正對照：同一支尺、同一段話，沒有文件 ⇒ False（⛔ 不是整支恆真）
    v_plain = FakeVerifier([VerifierVerdict(ok=True)])
    await _runtime(FakeProvider([_final_response(answer="這份租約的重點如下")]),
                   FakeRegistry(), v_plain).run_turn(
        _identity(), "幫我看這份租約", {"agent": {}})
    assert v_plain.calls and v_plain.calls[0]["document_turn"] is False


async def test_empty_facts_document_turn_never_reaches_the_verifier():
    """`facts` 為空 ⇒ 固定句、⛔ 不進模型、Verifier 不跑（那一格因此無從誤判）。"""
    doc = DocumentTurnInput(status="failed", pages_seen=0, pages_total=1)
    verifier = FakeVerifier([VerifierVerdict(ok=True)])
    result = await _runtime(FakeProvider([]), _RegistryWithSpecs(), verifier).run_turn(
        _identity(), "幫我看這份租約", {"agent": {}}, document=doc)
    assert verifier.calls == []
    assert result.trace.llm_calls == 0
