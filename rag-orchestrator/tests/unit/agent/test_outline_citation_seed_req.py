"""DSP-020：大綱章節預載為 provenance（tool_call_id 保留字 `outline`）。

起因：影子 2026-09-05 第一筆真流量，模型引用大綱、Verifier 只認工具回傳 ⇒
兩次 QUOTE_NOT_VERBATIM → budget_exhausted。三個斷言各擋一個回歸：
① runtime 在回合開始就把章節放進 tool_results（不必先 kb.get）；
② 真 OutputVerifier 對 `tool_call_id="outline"` 的逐字引用放行；
③ 大綱文字裡看得到章節 id（模型才填得出 `source`）。
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit

from services.agent.outline import OutlineDoc, OutlineSection, _build_doc
from services.agent.output_schema import AgentOutput, VerifierVerdict
from services.agent.runtime import OUTLINE_TOOL_CALL_ID, _seed_outline_provenance
from services.agent.tools.registry import ToolResult
from services.agent.verifier import OutputVerifier
from services.agent.verifier import VerifierRules
from tests.unit.agent.test_verifier_req import _RULES_PATH

from tests.unit.agent.test_runtime_req import (  # noqa: E402
    FakeAssembler,
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    _fake_message,
    _fake_response,
    _identity,
    _runtime,
    _tool_call_response,
)

_SECTION_TEXT = "金箍棒支援線上電子簽約，房東與租客在平台上完成簽署。合約目前不支援批次匯入。"


def _outline() -> OutlineDoc:
    return OutlineDoc(
        audience="prospect",
        version="v",
        sha256="s",
        token_count=10,
        sections=[
            OutlineSection(id="outline:lease", title="租約", text=_SECTION_TEXT, source_ids=[3600], citable=True),
            OutlineSection(id="outline:toc", title="目錄", text="這一節只做導航用途，列出各章節標題，不能當成答案引用。", source_ids=[], citable=False),
        ],
        text="x",
    )


def _final_with_citation(quote: str, tool_call_id: str = OUTLINE_TOOL_CALL_ID, source: str = "outline:lease"):
    payload = {
        "kind": "answer",
        "answer": "可以線上電子簽約。",
        "citations": [{"tool_call_id": tool_call_id, "source": source, "quote": quote}],
        "sentence_map": [{"sent": 0, "kind": "fact", "cite": [0]}],
        "fact_class": "feature",
        "handoff_reason": None,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


def test_seed_builds_one_provenance_per_section_and_keeps_citable_flag():
    seeded = _seed_outline_provenance(_outline())
    assert seeded is not None and seeded.ok
    assert [p.source for p in seeded.provenance] == ["outline:lease", "outline:toc"]
    assert [p.citable for p in seeded.provenance] == [True, False]
    assert seeded.provenance[0].text == _SECTION_TEXT
    assert _seed_outline_provenance(None) is None
    assert _seed_outline_provenance(SimpleNamespace(sections=[])) is None


@pytest.mark.asyncio
async def test_runtime_seeds_outline_into_tool_results_before_first_model_call():
    provider = FakeProvider([_final_with_citation(quote="支援線上電子簽約")])
    registry = FakeRegistry(call_results=[])
    verifier = FakeVerifier()
    runtime = _runtime(provider=provider, registry=registry, verifier=verifier)

    result = await runtime.run_turn(_identity(), "可以線上簽約嗎", {"agent": {"outline": _outline()}})

    assert result.kind == "answer"
    assert result.trace.tool_calls == []            # 0 次工具呼叫仍可引用
    seen = verifier.calls[0]["tool_results"]
    assert OUTLINE_TOOL_CALL_ID in seen
    assert seen[OUTLINE_TOOL_CALL_ID].provenance[0].source == "outline:lease"


@pytest.mark.asyncio
async def test_model_forged_tool_call_id_outline_does_not_overwrite_seed():
    provider = FakeProvider(
        [
            _tool_call_response("kb.get", {"kb_id": "3600"}, call_id=OUTLINE_TOOL_CALL_ID),
            _final_with_citation(quote="支援線上電子簽約"),
        ]
    )
    registry = FakeRegistry(call_results=[ToolResult(ok=True, data={"id": 3600}, text_for_model="別的東西")])
    verifier = FakeVerifier()
    runtime = _runtime(provider=provider, registry=registry, verifier=verifier)

    result = await runtime.run_turn(_identity(), "q", {"agent": {"outline": _outline()}})

    seen = verifier.calls[0]["tool_results"]
    assert seen[OUTLINE_TOOL_CALL_ID].provenance[0].source == "outline:lease"   # 種子沒被蓋
    assert "tool_call_id_collides_with_outline" in result.trace.violations


def test_real_verifier_accepts_verbatim_outline_quote_and_rejects_non_citable():
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    seeded = _seed_outline_provenance(_outline())
    tool_results = {OUTLINE_TOOL_CALL_ID: seeded}

    ok_out = AgentOutput(
        kind="answer",
        answer="可以線上電子簽約。",
        citations=[{"tool_call_id": OUTLINE_TOOL_CALL_ID, "source": "outline:lease", "quote": "支援線上電子簽約"}],
        sentence_map=[{"sent": 0, "kind": "fact", "cite": [0]}],
        fact_class="feature",
        handoff_reason=None,
    )
    assert verifier.verify(ok_out, tool_results, "可以線上簽約嗎", None).ok

    def _variant(**upd):   # model_copy 不驗證 dict ⇒ 走 model_validate
        return AgentOutput.model_validate({**ok_out.model_dump(), **upd})

    bad_quote = _variant(citations=[
        {"tool_call_id": OUTLINE_TOOL_CALL_ID, "source": "outline:lease", "quote": "支援線上簽約"}])
    assert verifier.verify(bad_quote, tool_results, "q", None).reason == "QUOTE_NOT_VERBATIM"

    toc = _variant(answer="這一節只做導航用途，列出各章節標題。", citations=[
        {"tool_call_id": OUTLINE_TOOL_CALL_ID, "source": "outline:toc", "quote": "這一節只做導航用途，列出各章節標題"}])
    assert verifier.verify(toc, tool_results, "q", None).reason == "SOURCE_NOT_CITABLE"


def test_outline_text_shows_section_id_in_heading():
    doc = _build_doc(
        audience="prospect",
        sections=[OutlineSection(id="outline:lease", title="租約", text="內文", source_ids=[1], citable=True)],
        version="v",
    )
    assert "【outline:lease】租約" in doc.text   # id 單獨成組，模型 source 才不會抄到標題


# ---------------------------------------------------------------------------
# DSP-021：影子首筆真流量的另外兩個根因（fact_class 缺、handoff 被句數檢查誤殺）
# ---------------------------------------------------------------------------

from services.agent.runtime import _agent_output_response_format
from services.presales_gate import FactClass, HandoffReason


def test_response_format_constrains_fact_class_and_handoff_reason_to_closed_sets():
    schema = _agent_output_response_format()["json_schema"]["schema"]
    props = schema["properties"]
    assert props["fact_class"]["enum"] == [fc.value for fc in FactClass]
    assert "null" not in json.dumps(props["fact_class"])            # 模型不能再回 null
    reasons = [b for b in props["handoff_reason"]["anyOf"] if b.get("type") == "string"][0]["enum"]
    assert reasons == [r.value for r in HandoffReason]
    assert set(schema["required"]) >= {"fact_class", "handoff_reason"}


def _handoff_response(fact_class="pricing", reason="sensitive_no_grounding", sentence_map=None):
    payload = {
        "kind": "handoff",
        "answer": "報價要由專人說明，我幫您轉接。",
        "citations": [],
        "sentence_map": sentence_map if sentence_map is not None else [],
        "fact_class": fact_class,
        "handoff_reason": reason,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


def test_real_verifier_passes_model_handoff_with_sensitive_fact_class_and_empty_sentence_map():
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    out = AgentOutput(kind="handoff", answer="報價要由專人說明。", citations=[], sentence_map=[],
                      fact_class="pricing", handoff_reason="sensitive_no_grounding")
    assert verifier.verify(out, {}, "一個月多少錢", {"reason": "sensitive_no_grounding"}).ok
    # 非 handoff 的敏感 fact_class 仍拒（牆不變）
    ans = AgentOutput.model_validate({**out.model_dump(), "kind": "answer", "handoff_reason": None,
                                      "sentence_map": [{"sent": 0, "kind": "fact", "cite": []}]})
    assert verifier.verify(ans, {}, "q", None).reason == "SENSITIVE_TOPIC"


@pytest.mark.asyncio
async def test_runtime_replaces_model_handoff_text_with_fixed_sentence_in_one_llm_call():
    provider = FakeProvider([_handoff_response()])
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    runtime = _runtime(provider=provider, registry=FakeRegistry(call_results=[]), verifier=verifier)

    result = await runtime.run_turn(_identity(), "一個月多少錢", {"agent": {"outline": _outline()}})

    assert result.kind == "handoff"
    assert result.trace.llm_calls == 1                       # 不再兩拒耗盡
    assert result.handoff["reason"] == "sensitive_no_grounding"
    assert result.answer == result.handoff["message"]        # 固定句，不是模型文字
    assert "報價要由專人說明" not in result.answer


# ---------------------------------------------------------------------------
# DSP-021：大綱引用 source 的機械正規化（去標題、補前綴；不碰 quote／其他 tool_call_id）
# ---------------------------------------------------------------------------

from services.agent.runtime import _canonicalize_outline_sources


def _out_with_sources(*pairs):
    return AgentOutput.model_validate({
        "kind": "answer", "answer": "x。", "fact_class": "feature", "handoff_reason": None,
        "citations": [{"tool_call_id": tid, "source": src, "quote": "q" * 8} for tid, src in pairs],
        "sentence_map": [{"sent": 0, "kind": "fact", "cite": list(range(len(pairs)))}],
    })


def test_canonicalize_adds_prefix_and_strips_title_only_for_outline_citations():
    out = _out_with_sources(("outline", "positioning"), ("outline", "outline:listing 房源"),
                            ("outline", "outline:lease"), ("call_1", "positioning"))
    fixed = _canonicalize_outline_sources(out)
    assert [c.source for c in fixed.citations] == [
        "outline:positioning", "outline:listing", "outline:lease", "positioning"]   # 最後一筆非大綱，不動
    assert [c.quote for c in fixed.citations] == [c.quote for c in out.citations]   # quote 不碰


def test_canonicalize_is_identity_when_nothing_to_fix():
    out = _out_with_sources(("outline", "outline:lease"), ("call_9", "kb:3600"))
    assert _canonicalize_outline_sources(out) is out


@pytest.mark.asyncio
async def test_runtime_verifies_prefixless_outline_source_against_seeded_provenance():
    """真線路 2026-09-05：quote 逐字、source 寫 `lease` ⇒ 之前被報 QUOTE_NOT_VERBATIM；現在應放行。"""
    provider = FakeProvider([_final_with_citation(quote="支援線上電子簽約", source="lease")])
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    runtime = _runtime(provider=provider, registry=FakeRegistry(call_results=[]), verifier=verifier)

    result = await runtime.run_turn(_identity(), "可以線上簽約嗎", {"agent": {"outline": _outline()}})

    assert result.kind == "answer", result.trace.verifier
    assert result.trace.llm_calls == 1


# ---------------------------------------------------------------------------
# DSP-022：當前使用者訊息必須進 messages；回合結束寫回 dialog；下一回合帶歷史
# ---------------------------------------------------------------------------

from services.agent.runtime import DIALOG_MAX_MESSAGES


@pytest.mark.asyncio
async def test_current_user_message_is_last_message_sent_to_model():
    provider = FakeProvider([_final_with_citation(quote="支援線上電子簽約")])
    runtime = _runtime(provider=provider, registry=FakeRegistry(call_results=[]), verifier=FakeVerifier())

    await runtime.run_turn(_identity(), "可以線上簽約嗎", {"agent": {"outline": _outline()}})

    sent = provider.calls[0]["messages"]
    assert sent[-1] == {"role": "user", "content": "可以線上簽約嗎"}
    assert sent[0]["role"] == "system"


@pytest.mark.asyncio
async def test_turn_writes_user_and_assistant_into_dialog_and_next_turn_replays_it():
    provider = FakeProvider([_final_with_citation(quote="支援線上電子簽約"),
                             _final_with_citation(quote="支援線上電子簽約")])
    assembler = FakeAssembler()
    runtime = _runtime(provider=provider, registry=FakeRegistry(call_results=[]),
                       verifier=FakeVerifier(), assembler=assembler)
    state = {"agent": {"outline": _outline()}}

    r1 = await runtime.run_turn(_identity(), "第一句", state)
    assert state["agent"]["dialog"] == [
        {"role": "user", "content": "第一句"}, {"role": "assistant", "content": r1.answer}]

    await runtime.run_turn(_identity(), "第二句", state)
    # 第二回合 assembler 收到的 dialog 是第一回合的兩則；當前句仍在 messages 最後
    assert assembler.calls[1]["dialog"] == [
        {"role": "user", "content": "第一句"}, {"role": "assistant", "content": r1.answer}]
    assert provider.calls[1]["messages"][-1] == {"role": "user", "content": "第二句"}
    assert len(state["agent"]["dialog"]) == 4


@pytest.mark.asyncio
async def test_dialog_is_trimmed_to_max_messages_and_fixed_sentence_is_recorded():
    """固定句收場也要寫回（使用者確實看到了那句）；超過上限丟最舊。"""
    provider = FakeProvider([_final_with_citation(quote="支援線上電子簽約")])
    runtime = _runtime(provider=provider, registry=FakeRegistry(call_results=[]),
                       verifier=FakeVerifier([VerifierVerdict(ok=False, reason="SCHEMA")] * 3))
    old = [{"role": "user", "content": f"u{i}"} if i % 2 == 0 else {"role": "assistant", "content": f"a{i}"}
           for i in range(DIALOG_MAX_MESSAGES)]
    state = {"agent": {"outline": _outline(), "dialog": list(old)}}

    # 預算 max_rewrites=2：第一次拒後就固定句（FakeProvider 只給一則回應，第二則不該被要）
    from services.agent.budget import Budget
    runtime.budget = Budget(max_rewrites=1)
    r = await runtime.run_turn(_identity(), "新的一句", state)

    assert r.kind == "handoff" and r.handoff["reason"] == "budget_exhausted"
    dialog = state["agent"]["dialog"]
    assert len(dialog) == DIALOG_MAX_MESSAGES
    assert dialog[-2:] == [{"role": "user", "content": "新的一句"}, {"role": "assistant", "content": r.answer}]
    assert dialog[0] == old[2]                                # 最舊兩則被丟


# ---------------------------------------------------------------------------
# DSP-021：SCHEMA 拒因回饋附系統切句（模型才知道句數怎麼對）
# ---------------------------------------------------------------------------

def _final_two_sentences_one_map():
    payload = {
        "kind": "answer", "answer": "可以線上簽約。這樣很方便。",
        "citations": [{"tool_call_id": "outline", "source": "outline:lease", "quote": "支援線上電子簽約"}],
        "sentence_map": [{"sent": 0, "kind": "fact", "cite": [0]}],      # 2 句只標 1 筆
        "fact_class": "feature", "handoff_reason": None,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


@pytest.mark.asyncio
async def test_schema_reject_feedback_tells_model_the_server_side_sentence_split():
    provider = FakeProvider([_final_two_sentences_one_map(), _final_with_citation(quote="支援線上電子簽約")])
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    runtime = _runtime(provider=provider, registry=FakeRegistry(call_results=[]), verifier=verifier)

    result = await runtime.run_turn(_identity(), "可以線上簽約嗎", {"agent": {"outline": _outline()}})

    assert result.trace.verifier[0].reason == "SCHEMA"
    feedback = provider.calls[1]["messages"][-1]
    assert feedback["role"] == "user"
    assert "切成 2 句" in feedback["content"] and "sentence_map 有 1 筆" in feedback["content"]
    assert "[0]可以線上簽約。" in feedback["content"] and "[1]這樣很方便。" in feedback["content"]
    assert "支援線上電子簽約" not in feedback["content"]          # 不含任何來源原文
