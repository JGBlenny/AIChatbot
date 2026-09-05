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
from services.agent.provenance_units import provenance_units, resolve_refs
from services.agent.output_schema import AgentOutput, VerifierVerdict
from services.agent.runtime import OUTLINE_TOOL_CALL_ID, _seed_outline_provenance
from services.agent.tools.registry import ToolResult
from services.agent.verifier import _FIXTURE_NONCE, OutputVerifier
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


class _NonceSpy:
    """記下 Runtime 這一回合實際用的 nonce（DSP-029a）。

    ⚠️ 為什麼需要它：`refs` 裡的標記必須帶**本回合**的 nonce，而 nonce 是
    `secrets.token_hex(8)` 隨機產生的。測試若改成「驗證時不比對 nonce」就等於
    把這條契約關掉；若改成讓 Runtime 收一個固定 nonce，量到的也不是產線那條路。
    這裡只**旁觀**：monkeypatch `new_nonce` 讓它照樣隨機產生，順手把值抄一份。
    """

    def __init__(self) -> None:
        self.value = "FIXTURE0000000000"


_NONCE_SPY = _NonceSpy()


@pytest.fixture(autouse=True)
def _spy_on_nonce(monkeypatch):
    """全檔自動套用：讓 `_NONCE_SPY` 跟上每一回合真正的 nonce。"""
    import services.agent.runtime as runtime_mod
    real = runtime_mod.new_nonce

    def _spy():
        _NONCE_SPY.value = real()
        return _NONCE_SPY.value

    monkeypatch.setattr(runtime_mod, "new_nonce", _spy)
    return _NONCE_SPY


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


def _ref(nonce: str, unit: int = 0, tool_call_id: str = OUTLINE_TOOL_CALL_ID,
         source: str = "outline:lease") -> str:
    """DSP-029a：模型照抄的那一串行首標記。⛔ 這裡刻意**不呼叫** `unit_marker`——
    測試要模擬的是「模型抄了什麼」，用產生器組等於預設它一定抄對。"""
    return f"[{nonce}:{tool_call_id}:{source}§{unit}]"


def _final_with_citation(unit: int = 0, tool_call_id: str = OUTLINE_TOOL_CALL_ID,
                         source: str = "outline:lease"):
    """DSP-029a：模型只照抄一串標記，⛔ 不再抄引文、⛔ 不再自己填三個定址欄位。

    ⚠️ 這裡用 `_NONCE_SPY` 取回 Runtime 這一回合實際產生的 nonce——`new_nonce()` 是
    隨機的，測試 ⛔ 不能猜；猜不到就只能放寬 nonce 檢查，那正是這條契約要守的東西。
    因此回傳的是 `FakeCompletions` 支援的 **callable 腳本項**：JSON 延到模型真的被
    呼叫的那一刻才組，⛔ 不能在 `FakeProvider([...])` 建構時就組好（那時 nonce 還沒產生）。

    `_SECTION_TEXT` 的片段：0＝「金箍棒支援線上電子簽約，…完成簽署。」、
    1＝「合約目前不支援批次匯入。」"""
    def _build():
        payload = {
            "kind": "answer",
            "sentences": [{"text": "可以線上電子簽約。", "kind": "fact",
                           "refs": [_ref(_NONCE_SPY.value, unit, tool_call_id, source)]}],
            "fact_class": "feature",
            "handoff_reason": None,
        }
        return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))
    return lambda _kwargs: _build()


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


def _verify(verifier, out, tool_results, msg="q", handoff=None, nonce=_FIXTURE_NONCE):
    """DSP-029a：引用解析由 `resolve_refs` 產生後另傳 Verifier
    （⛔ 不從 `out` 取、⛔ 不在測試裡另寫一套解析）。"""
    resolved, resolve_errors = resolve_refs(out, tool_results, nonce)
    return verifier.verify(out, tool_results, msg, handoff,
                           resolved=resolved, resolve_errors=resolve_errors)


def test_real_verifier_accepts_outline_unit_citation_and_rejects_non_citable():
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    seeded = _seed_outline_provenance(_outline())
    tool_results = {OUTLINE_TOOL_CALL_ID: seeded}

    def _out(text, ref):
        return AgentOutput.model_validate({
            "kind": "answer",
            "sentences": [{"text": text, "kind": "fact", "refs": [ref]}],
            "fact_class": "feature",
            "handoff_reason": None,
        })

    ok_out = _out("可以線上電子簽約。", _ref(_FIXTURE_NONCE, 0))
    assert _verify(verifier, ok_out, tool_results, "可以線上簽約嗎").ok

    # DSP-029：指到同一章節**別的片段**（1＝批次匯入）⇒ 覆蓋不過。
    wrong_unit = _out("可以線上電子簽約。", _ref(_FIXTURE_NONCE, 1))
    assert _verify(verifier, wrong_unit, tool_results).reason == "QUOTE_NOT_COVERING"

    # 編號越界 ⇒ SCHEMA(unit_out_of_range)（該章節只有 2 個片段）。
    oob = _out("可以線上電子簽約。", _ref(_FIXTURE_NONCE, 9))
    oob_verdict = _verify(verifier, oob, tool_results)
    assert oob_verdict.reason == "SCHEMA" and oob_verdict.schema_cause == "unit_out_of_range"

    # DSP-029a：標記的 nonce 不是本回合的 ⇒ SCHEMA(ref_invalid)
    stale = _out("可以線上電子簽約。", _ref("PREVTURN00000000", 0))
    stale_verdict = _verify(verifier, stale, tool_results)
    assert stale_verdict.reason == "SCHEMA" and stale_verdict.schema_cause == "ref_invalid"

    toc = _out("這一節只做導航用途，不能當成答案引用。",
               _ref(_FIXTURE_NONCE, 0, source="outline:toc"))
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


def test_sentence_schema_is_text_kind_refs_only():
    """DSP-029a F-A：模型端的 `Sentence` **只有** `(text, kind, refs)`，且 `$defs`
    裡 ⛔ 再無 `Citation`。

    `quote` 一旦還在 schema 裡，解析後的原文就有地方可以被寫回去，也就會跟著
    `decision_snapshot`／trace 外流——這條是結構上的保證，不是靠自律。
    `citations`／`cite` 同理：留著就會有人把索引接回來，而索引本身正是 R5 實測
    最常錯的那一欄。"""
    schema = _agent_output_response_format()["json_schema"]["schema"]
    assert set(schema["$defs"]) == {"Sentence"}
    sentence = schema["$defs"]["Sentence"]
    assert set(sentence["properties"]) == {"text", "kind", "refs"}
    assert set(sentence["required"]) == {"text", "kind", "refs"}
    assert sentence["additionalProperties"] is False
    dumped = json.dumps(schema)
    assert "quote" not in dumped
    assert "Citation" not in dumped and '"cite"' not in dumped


def test_contract_wording_lives_in_schema_descriptions_not_only_in_prose():
    """DSP-029 P1-2：契約說明放 `Field(description=…)`（結構化、非特例）。

    五處都要有實際文字——正對照：先確認這五個鍵真的都在 schema 裡，
    少一個就是路徑寫錯，⛔ 不是「描述剛好是空的」。"""
    schema = _agent_output_response_format()["json_schema"]["schema"]
    props = schema["properties"]
    for key in ("kind", "sentences", "fact_class", "handoff_reason"):
        assert key in props, key
        assert (props[key].get("description") or "").strip(), key
    refs = schema["$defs"]["Sentence"]["properties"]["refs"]
    assert (refs.get("description") or "").strip()


def _handoff_response(fact_class="pricing", reason="sensitive_no_grounding", sentences=None):
    payload = {
        "kind": "handoff",
        "sentences": sentences if sentences is not None else [],
        "fact_class": fact_class,
        "handoff_reason": reason,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


def test_real_verifier_passes_model_handoff_with_sensitive_fact_class_and_empty_sentences():
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    out = AgentOutput(kind="handoff", sentences=[],
                      fact_class="pricing", handoff_reason="sensitive_no_grounding")
    assert _verify(verifier, out, {}, "一個月多少錢", {"reason": "sensitive_no_grounding"}).ok
    # DSP-028：handoff 帶**捏造** sentences 也放行（文字不外流，Runtime 換固定句）
    fabricated = AgentOutput.model_validate({**out.model_dump(), "sentences": [
        {"text": "我們的月費是 3000 元，保證業界最低。", "kind": "fact", "refs": []}]})
    assert _verify(verifier, fabricated, {}, "一個月多少錢", {"reason": "sensitive_no_grounding"}).ok
    # 非 handoff 的敏感 fact_class 仍拒（牆不變）
    ans = AgentOutput.model_validate({**out.model_dump(), "kind": "answer", "handoff_reason": None,
                                      "sentences": [{"text": "報價要由專人說明。",
                                                     "kind": "fact", "refs": []}]})
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
    fabricated = [{"text": "我們的月費是 3000 元，保證業界最低。", "kind": "fact", "refs": []}]
    provider = FakeProvider([_handoff_response(sentences=fabricated)])
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    runtime = _runtime(provider=provider, registry=FakeRegistry(call_results=[]), verifier=verifier)

    result = await runtime.run_turn(_identity(), "一個月多少錢", {"agent": {"outline": _outline()}})

    assert result.kind == "handoff"
    assert result.answer == effective_handoff_message(None)
    assert "3000" not in result.answer and "保證" not in result.answer


# ---------------------------------------------------------------------------
# DSP-029a：大綱 source 的機械正規化已**退役**（`_canonicalize_outline_sources`）
# ---------------------------------------------------------------------------


def test_outline_source_canonicalization_is_retired_and_must_not_come_back():
    """DSP-029a：`_canonicalize_outline_sources` 連同呼叫點一併刪除。

    它做的是「把模型自己填的 `source` 標籤收斂成一種寫法」。DSP-029a 之後模型
    不再自己填 `source`——它照抄整串行首標記，標籤沒有第二種寫法可以被正規化。
    ⚠️ 復活它的危險不是多餘，是**放行**：標記被抄壞時它會把壞標記改成一個看似
    合法的來源，於是「指到別的句子」的引用會通過。

    正對照：先確認同一個模組裡**確實**還有東西可以 import（`OUTLINE_TOOL_CALL_ID`
    仍在），否則這條的「找不到」只是模組名寫錯。"""
    import services.agent.provenance_units as pu_mod
    import services.agent.runtime as rt_mod

    assert pu_mod.OUTLINE_TOOL_CALL_ID == "outline"          # 正對照組
    assert not hasattr(pu_mod, "_canonicalize_outline_sources")
    assert not hasattr(rt_mod, "_canonicalize_outline_sources")
    assert not hasattr(pu_mod, "resolve_citations")


@pytest.mark.asyncio
async def test_runtime_rejects_prefixless_outline_source_now_that_ref_is_copied_verbatim():
    """真線路 2026-09-05 的 DSP-021 案在 DSP-029a 下的**新行為**：

    模型若把標記抄成 `[nonce:outline:listing§0]`（少了 `outline:` 前綴，於是 source
    變成 `listing`），來源不存在 ⇒ SCHEMA(ref_source_not_found)，回饋教它去照抄
    資料段裡實際出現過的那一行。⛔ 不再有機械正規化把它救回來。"""
    provider = FakeProvider([_final_with_citation(source="listing"),
                             _final_with_citation()])
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    runtime = _runtime(provider=provider, registry=FakeRegistry(call_results=[]), verifier=verifier)

    result = await runtime.run_turn(_identity(), "可以線上簽約嗎", {"agent": {"outline": _outline()}})

    assert result.trace.verifier[0].reason == "SCHEMA"
    assert result.trace.verifier[0].schema_cause == "ref_source_not_found"
    assert result.kind == "answer"            # 第二次抄對就過（⛔ 不是整回合報廢）


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

def _final_with_stale_nonce_ref():
    """DSP-029a 的 SCHEMA 之一 ＝ 標記不是本回合的（`ref_invalid`）。

    取代舊的「cite 索引越界」：索引已經不存在，那個成因在新契約下不可達。"""
    def _build():
        payload = {
            "kind": "answer",
            "sentences": [{"text": "可以線上電子簽約。", "kind": "fact",
                           "refs": [_ref("PREVTURN00000000", 0)]}],
            "fact_class": "feature", "handoff_reason": None,
        }
        return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))
    return lambda _kwargs: _build()


def _final_with_empty_sentences():
    payload = {
        "kind": "answer", "sentences": [],
        "fact_class": "feature", "handoff_reason": None,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


def _final_with_blank_text():
    payload = {
        "kind": "answer",
        "sentences": [{"text": "   ", "kind": "greeting", "refs": []}],
        "fact_class": "feature", "handoff_reason": None,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "first_response,expected_snippet",
    [
        (_final_with_empty_sentences, "`sentences` 是空陣列"),
        (_final_with_blank_text, "第 0 筆"),
        (_final_with_stale_nonce_ref, "不是本回合資料段裡的標記"),
    ],
    ids=["empty_array", "blank_text", "ref_invalid"],
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

def _final_sentences(build_sentences):
    """`build_sentences(nonce)` ⇒ sentences（nonce 到回合開始才知道，見 `_LazyResponse`）。"""
    def _build():
        payload = {"kind": "answer", "sentences": build_sentences(_NONCE_SPY.value),
                   "fact_class": "feature", "handoff_reason": None}
        return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))
    return lambda _kwargs: _build()


@pytest.mark.asyncio
async def test_coverage_reject_feedback_tells_model_to_fix_unit_not_to_handoff():
    """DSP-029：`QUOTE_NOT_VERBATIM` 在模型端已不可達（引文由系統解析），
    這條改由「指錯片段」的 `QUOTE_NOT_COVERING` 承接同一個回歸：
    回饋要教「換 `refs` 的標記」，並明說 ⛔ 不要因為被拒就改轉人。"""
    bad = _final_sentences(lambda n: [   # 指到批次匯入那句
        {"text": "可以線上電子簽約。", "kind": "fact", "refs": [_ref(n, 1)]}])
    good = _final_sentences(lambda n: [
        {"text": "可以線上電子簽約。", "kind": "fact", "refs": [_ref(n, 0)]}])
    provider = FakeProvider([bad, good])
    verifier = OutputVerifier(VerifierRules.load(_RULES_PATH))
    runtime = _runtime(provider=provider, registry=FakeRegistry(call_results=[]), verifier=verifier)

    result = await runtime.run_turn(_identity(), "可以線上簽約嗎", {"agent": {"outline": _outline()}})

    assert result.kind == "answer"
    fb = provider.calls[1]["messages"][-1]["content"]
    assert "QUOTE_NOT_COVERING" in fb and "`refs`" in fb and "第 0 筆" in fb
    assert "不要因為被拒就改成 `kind=handoff`" in fb
    # ⛔ 無原文：來源片段與被拒的回答都不得出現在回饋裡
    assert "支援線上電子簽約" not in fb and "合約目前不支援批次匯入" not in fb


def test_agent_rules_make_handoff_non_default_and_name_outline_evidence():
    from services.agent import agent_rules
    text = agent_rules._POLICY_TEXT
    # 2026-09-05 diag_variants 實測：政策文越長 mini 越傾向先轉人 ⇒ 回 R1 版＋一行 sentences 說明
    assert "回覆放在 `sentences`" in text and "sentence_map" not in text
    assert "不必費力措辭" not in text and "轉人不是預設出口" not in text
