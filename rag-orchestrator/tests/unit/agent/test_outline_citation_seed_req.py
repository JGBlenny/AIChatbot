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
from services.agent.provenance_units import provenance_units, resolve_citations
from services.agent.output_schema import AgentOutput, VerifierVerdict
from services.agent.runtime import OUTLINE_TOOL_CALL_ID, _seed_outline_provenance
from services.agent.tools.registry import ToolResult
from services.agent.verifier import OutputVerifier
from services.agent.verifier import VerifierRules
from services.conversational_config import effective_handoff_message
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


def _final_with_citation(unit: int = 0, tool_call_id: str = OUTLINE_TOOL_CALL_ID,
                         source: str = "outline:lease"):
    """DSP-029：模型只填 `(tool_call_id, source, unit)`，⛔ 不再抄引文。

    `_SECTION_TEXT` 的片段：0＝「金箍棒支援線上電子簽約，…完成簽署。」、
    1＝「合約目前不支援批次匯入。」"""
    payload = {
        "kind": "answer",
        "sentences": [{"text": "可以線上電子簽約。", "kind": "fact", "cite": [0]}],
        "citations": [{"tool_call_id": tool_call_id, "source": source, "unit": unit}],
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
    provider = FakeProvider([_final_with_citation()])
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
            _final_with_citation(),
        ]
    )
    registry = FakeRegistry(call_results=[ToolResult(ok=True, data={"id": 3600}, text_for_model="別的東西")])
    verifier = FakeVerifier()
    runtime = _runtime(provider=provider, registry=registry, verifier=verifier)

    result = await runtime.run_turn(_identity(), "q", {"agent": {"outline": _outline()}})

    seen = verifier.calls[0]["tool_results"]
    assert seen[OUTLINE_TOOL_CALL_ID].provenance[0].source == "outline:lease"   # 種子沒被蓋
    assert "tool_call_id_collides_with_outline" in result.trace.violations


def _verify(verifier, out, tool_results, msg="q", handoff=None):
    """DSP-029：引用解析由 `resolve_citations` 產生後另傳 Verifier
    （⛔ 不從 `out` 取、⛔ 不在測試裡另寫一套解析）。"""
    resolved, resolve_errors = resolve_citations(out, tool_results)
    return verifier.verify(out, tool_results, msg, handoff,
                           resolved=resolved, resolve_errors=resolve_errors)


def test_real_verifier_accepts_outline_unit_citation_and_rejects_non_citable():
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    seeded = _seed_outline_provenance(_outline())
    tool_results = {OUTLINE_TOOL_CALL_ID: seeded}

    ok_out = AgentOutput(
        kind="answer",
        sentences=[{"text": "可以線上電子簽約。", "kind": "fact", "cite": [0]}],
        citations=[{"tool_call_id": OUTLINE_TOOL_CALL_ID, "source": "outline:lease", "unit": 0}],
        fact_class="feature",
        handoff_reason=None,
    )
    assert _verify(verifier, ok_out, tool_results, "可以線上簽約嗎").ok

    def _variant(**upd):   # model_copy 不驗證 dict ⇒ 走 model_validate
        return AgentOutput.model_validate({**ok_out.model_dump(), **upd})

    # DSP-029：指到同一章節**別的片段**（1＝批次匯入）⇒ 覆蓋不過。
    wrong_unit = _variant(citations=[
        {"tool_call_id": OUTLINE_TOOL_CALL_ID, "source": "outline:lease", "unit": 1}])
    assert _verify(verifier, wrong_unit, tool_results).reason == "QUOTE_NOT_COVERING"

    # 編號越界 ⇒ SCHEMA(unit_out_of_range)（該章節只有 2 個片段）。
    oob = _variant(citations=[
        {"tool_call_id": OUTLINE_TOOL_CALL_ID, "source": "outline:lease", "unit": 9}])
    oob_verdict = _verify(verifier, oob, tool_results)
    assert oob_verdict.reason == "SCHEMA" and oob_verdict.schema_cause == "unit_out_of_range"

    toc = _variant(sentences=[{"text": "這一節只做導航用途，不能當成答案引用。",
                               "kind": "fact", "cite": [0]}], citations=[
        {"tool_call_id": OUTLINE_TOOL_CALL_ID, "source": "outline:toc", "unit": 0}])
    assert _verify(verifier, toc, tool_results).reason == "SOURCE_NOT_CITABLE"


def test_outline_units_are_the_same_on_both_sides():
    """r13 F-B 兩側對齊：`_seed_outline_provenance`（解析側）與 `PromptAssembler.build`
    （編號側）吃的是**同一份 `section.text`**，切法也只有一個函式。

    正對照：先確認這份章節真的切出 >1 個片段，否則「對齊」是巧合不是證據。"""
    seeded = _seed_outline_provenance(_outline())
    units = provenance_units(seeded.provenance[0].text)
    assert len(units) == 2, units
    assert units == provenance_units(_SECTION_TEXT)


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


def test_citation_schema_is_tool_call_id_source_unit_only():
    """DSP-029 F-A：模型端的 `Citation` **只有** `(tool_call_id, source, unit)`。

    `quote` 一旦還在 schema 裡，解析後的原文就有地方可以被寫回去，也就會跟著
    `decision_snapshot`／trace 外流——這條是結構上的保證，不是靠自律。"""
    schema = _agent_output_response_format()["json_schema"]["schema"]
    citation = schema["$defs"]["Citation"]
    assert set(citation["properties"]) == {"tool_call_id", "source", "unit"}
    assert set(citation["required"]) == {"tool_call_id", "source", "unit"}
    assert citation["additionalProperties"] is False
    assert "quote" not in json.dumps(schema)


def test_contract_wording_lives_in_schema_descriptions_not_only_in_prose():
    """DSP-029 P1-2：契約說明放 `Field(description=…)`（結構化、非特例）。

    六處都要有實際文字——正對照：先確認這六個鍵真的都在 schema 裡，
    少一個就是路徑寫錯，⛔ 不是「描述剛好是空的」。"""
    schema = _agent_output_response_format()["json_schema"]["schema"]
    props = schema["properties"]
    for key in ("kind", "sentences", "citations", "fact_class", "handoff_reason"):
        assert key in props, key
        assert (props[key].get("description") or "").strip(), key
    unit = schema["$defs"]["Citation"]["properties"]["unit"]
    assert (unit.get("description") or "").strip()


def _handoff_response(fact_class="pricing", reason="sensitive_no_grounding", sentences=None):
    payload = {
        "kind": "handoff",
        "sentences": sentences if sentences is not None else [],
        "citations": [],
        "fact_class": fact_class,
        "handoff_reason": reason,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


def test_real_verifier_passes_model_handoff_with_sensitive_fact_class_and_empty_sentences():
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    out = AgentOutput(kind="handoff", sentences=[], citations=[],
                      fact_class="pricing", handoff_reason="sensitive_no_grounding")
    assert _verify(verifier, out, {}, "一個月多少錢", {"reason": "sensitive_no_grounding"}).ok
    # DSP-028：handoff 帶**捏造** sentences 也放行（文字不外流，Runtime 換固定句）
    fabricated = AgentOutput.model_validate({**out.model_dump(), "sentences": [
        {"text": "我們的月費是 3000 元，保證業界最低。", "kind": "fact", "cite": []}]})
    assert _verify(verifier, fabricated, {}, "一個月多少錢", {"reason": "sensitive_no_grounding"}).ok
    # 非 handoff 的敏感 fact_class 仍拒（牆不變）
    ans = AgentOutput.model_validate({**out.model_dump(), "kind": "answer", "handoff_reason": None,
                                      "sentences": [{"text": "報價要由專人說明。",
                                                     "kind": "fact", "cite": []}]})
    assert _verify(verifier, ans, {}, "q").reason == "SENSITIVE_TOPIC"


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
    assert result.answer == effective_handoff_message(None)


@pytest.mark.asyncio
async def test_runtime_uses_fixed_sentence_even_when_handoff_carries_fabricated_sentences():
    """DSP-028／F-f：handoff 的 `sentences` 是捏造的價格句也不外流——
    Verifier 對 handoff 不跑②～⑦（那段字不會送出），把關的是 Runtime 換固定句這一步。
    這條測的是「**使用者實際看到的字**」，⛔ 不是 Verifier 的 verdict。"""
    fabricated = [{"text": "我們的月費是 3000 元，保證業界最低。", "kind": "fact", "cite": []}]
    provider = FakeProvider([_handoff_response(sentences=fabricated)])
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    runtime = _runtime(provider=provider, registry=FakeRegistry(call_results=[]), verifier=verifier)

    result = await runtime.run_turn(_identity(), "一個月多少錢", {"agent": {"outline": _outline()}})

    assert result.kind == "handoff"
    assert result.answer == effective_handoff_message(None)
    assert "3000" not in result.answer and "保證" not in result.answer


# ---------------------------------------------------------------------------
# DSP-021：大綱引用 source 的機械正規化（去標題、補前綴；不碰 quote／其他 tool_call_id）
# ---------------------------------------------------------------------------

from services.agent.runtime import _canonicalize_outline_sources


def _out_with_sources(*pairs):
    return AgentOutput.model_validate({
        "kind": "answer", "fact_class": "feature", "handoff_reason": None,
        "citations": [{"tool_call_id": tid, "source": src, "unit": 0} for tid, src in pairs],
        "sentences": [{"text": "x。", "kind": "fact", "cite": list(range(len(pairs)))}],
    })


def test_canonicalize_adds_prefix_and_strips_title_only_for_outline_citations():
    out = _out_with_sources(("outline", "positioning"), ("outline", "outline:listing 房源"),
                            ("outline", "outline:lease"), ("call_1", "positioning"))
    fixed = _canonicalize_outline_sources(out)
    assert [c.source for c in fixed.citations] == [
        "outline:positioning", "outline:listing", "outline:lease", "positioning"]   # 最後一筆非大綱，不動
    assert [c.unit for c in fixed.citations] == [c.unit for c in out.citations]   # unit 不碰


def test_canonicalize_is_identity_when_nothing_to_fix():
    out = _out_with_sources(("outline", "outline:lease"), ("call_9", "kb:3600"))
    assert _canonicalize_outline_sources(out) is out


@pytest.mark.asyncio
async def test_runtime_verifies_prefixless_outline_source_against_seeded_provenance():
    """真線路 2026-09-05：source 寫 `lease`（缺前綴）⇒ 正規化補回後解析得到片段，應放行。

    ⚠️ DSP-029 之後這條更要緊：`source` 是定址的一部分，沒有正規化就是
    SCHEMA(source_not_found)，⛔ 不再有「引文逐字仍放行」的補救。"""
    provider = FakeProvider([_final_with_citation(source="lease")])
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
    provider = FakeProvider([_final_with_citation()])
    runtime = _runtime(provider=provider, registry=FakeRegistry(call_results=[]), verifier=FakeVerifier())

    await runtime.run_turn(_identity(), "可以線上簽約嗎", {"agent": {"outline": _outline()}})

    sent = provider.calls[0]["messages"]
    assert sent[-1] == {"role": "user", "content": "可以線上簽約嗎"}
    assert sent[0]["role"] == "system"


@pytest.mark.asyncio
async def test_turn_writes_user_and_assistant_into_dialog_and_next_turn_replays_it():
    provider = FakeProvider([_final_with_citation(),
                             _final_with_citation()])
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
    provider = FakeProvider([_final_with_citation()])
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

def _final_with_out_of_range_cite():
    """DSP-028：句數不等已不再是 SCHEMA；新契約下的 SCHEMA 之一 = cite 索引越界。"""
    payload = {
        "kind": "answer",
        "sentences": [{"text": "可以線上簽約。", "kind": "fact", "cite": [0]},
                      {"text": "這樣很方便。", "kind": "fact", "cite": [3]}],   # 只有 1 筆 citation
        "citations": [{"tool_call_id": "outline", "source": "outline:lease", "unit": 0}],
        "fact_class": "feature", "handoff_reason": None,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


def _final_with_empty_sentences():
    payload = {
        "kind": "answer", "sentences": [], "citations": [],
        "fact_class": "feature", "handoff_reason": None,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


def _final_with_blank_text():
    payload = {
        "kind": "answer",
        "sentences": [{"text": "   ", "kind": "greeting", "cite": []}],
        "citations": [], "fact_class": "feature", "handoff_reason": None,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "first_response,expected_snippet",
    [
        (_final_with_empty_sentences, "`sentences` 是空陣列"),
        (_final_with_blank_text, "第 0 筆"),
        (_final_with_out_of_range_cite, "超出 `citations` 範圍"),
    ],
    ids=["empty_array", "blank_text", "cite_out_of_range"],
)
async def test_schema_reject_feedback_names_the_actual_cause(first_response, expected_snippet):
    """DSP-028：SCHEMA 回饋改成指出三種成因；⛔ 不再回報「系統把你的 answer 切成 N 句」。"""
    provider = FakeProvider([first_response(), _final_with_citation()])
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    runtime = _runtime(provider=provider, registry=FakeRegistry(call_results=[]), verifier=verifier)

    result = await runtime.run_turn(_identity(), "可以線上簽約嗎", {"agent": {"outline": _outline()}})

    assert result.trace.verifier[0].reason == "SCHEMA"
    feedback = provider.calls[1]["messages"][-1]
    assert feedback["role"] == "user"
    assert expected_snippet in feedback["content"]
    assert "切成" not in feedback["content"]                      # 舊提示已刪，⛔ 不得復活
    assert "支援線上電子簽約" not in feedback["content"]          # 不含任何來源原文


# ---------------------------------------------------------------------------
# 拒因回饋要教「怎麼修那一筆」並禁止以轉人逃逸（2026-09-05 DSP-028 重跑：116/127 no_grounding 是第一次就轉人）
# ---------------------------------------------------------------------------

def _final_sentences(sentences, citations):
    payload = {"kind": "answer", "sentences": sentences, "citations": citations,
               "fact_class": "feature", "handoff_reason": None}
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


@pytest.mark.asyncio
async def test_coverage_reject_feedback_tells_model_to_fix_unit_not_to_handoff():
    """DSP-029：`QUOTE_NOT_VERBATIM` 在模型端已不可達（引文由系統解析），
    這條改由「指錯片段」的 `QUOTE_NOT_COVERING` 承接同一個回歸：
    回饋要教「改 `unit`」，並明說 ⛔ 不要因為被拒就改轉人。"""
    bad = _final_sentences(
        [{"text": "可以線上電子簽約。", "kind": "fact", "cite": [0]}],
        [{"tool_call_id": "outline", "source": "outline:lease", "unit": 1}])   # 指到批次匯入那句
    good = _final_sentences(
        [{"text": "可以線上電子簽約。", "kind": "fact", "cite": [0]}],
        [{"tool_call_id": "outline", "source": "outline:lease", "unit": 0}])
    provider = FakeProvider([bad, good])
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    runtime = _runtime(provider=provider, registry=FakeRegistry(call_results=[]), verifier=verifier)

    result = await runtime.run_turn(_identity(), "可以線上簽約嗎", {"agent": {"outline": _outline()}})

    assert result.kind == "answer"
    fb = provider.calls[1]["messages"][-1]["content"]
    assert "QUOTE_NOT_COVERING" in fb and "`unit`" in fb and "第 0 筆" in fb
    assert "不要因為被拒就改成 `kind=handoff`" in fb
    # ⛔ 無原文：來源片段與被拒的回答都不得出現在回饋裡
    assert "支援線上電子簽約" not in fb and "合約目前不支援批次匯入" not in fb


def test_agent_rules_make_handoff_non_default_and_name_outline_evidence():
    from services.agent import agent_rules
    text = agent_rules._POLICY_TEXT
    # 2026-09-05 diag_variants 實測：政策文越長 mini 越傾向先轉人 ⇒ 回 R1 版＋一行 sentences 說明
    assert "回覆放在 `sentences`" in text and "sentence_map" not in text
    assert "不必費力措辭" not in text and "轉人不是預設出口" not in text
