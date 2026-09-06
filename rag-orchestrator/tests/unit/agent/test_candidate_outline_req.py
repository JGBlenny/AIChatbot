"""unit：任務 4.1 候選注入——`CandidateOutlineDoc`／`AgentRuntime._select_outline`
（Plan `inputs/plan-m-d-runtime-wiring-20260907.md` §2.4-1..5, 10, 11｜
knowledge-outline-and-intent-architecture:4.1）。

⚠️ 本檔不碰版控正本（`rag-orchestrator/canon/*`）——全部用合成正本
（`parse_canon_text`，樣式沿 `test_candidate_selector_req.py`）。所有標記／查詢字串
都帶 `ZZ*` 前綴，隱私那條測試就靠它們判外洩；⛔ 不得刪隱私測試的正對照組。
"""
from __future__ import annotations

import logging
import math

import pytest

from services.agent.canon.candidate_selector import K, CandidateSelector
from services.agent.canon.canon_assembler import (
    build_canon_toc,
    build_outline,
    register_canon,
    reset_canon_registry,
)
from services.agent.canon.canon_parser import parse_canon_text
from services.agent.canon.fine_index import FineIndex, register_index, reset_index_registry
from services.agent.identity import Identity
from services.agent.output_schema import AgentOutput, VerifierVerdict
from services.agent.outline import CandidateOutlineDoc
from services.agent.prompt_assembler import PromptAssembler
from services.agent.provenance_units import resolve_refs
from services.agent.runtime import OUTLINE_TOOL_CALL_ID, _seed_outline_provenance
from services.agent import runtime as runtime_mod
from services.agent.verifier import _FIXTURE_NONCE, OutputVerifier
from tests.unit.agent.test_verifier_req import _RULES_PATH

from tests.unit.agent.test_runtime_req import (  # noqa: E402
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    _final_response,
    _runtime,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:4.1"),
]


# ---------------------------------------------------------------------------
# 合成正本：6 個 prospect 可見已審細目（K=5，第 6 個分數最低、標記 ZZUNSELECTED）
# ＋ 1 個 pm-only 隱藏細目（標記 ZZHIDDEN）。
# ---------------------------------------------------------------------------

_FRONT_MATTER = """---
audience: prospect
version: 2026-09-07.candidate-outline-test
reviewers: [test]
language: zh-TW
budget_tokens: 12000
target_user: [prospect]
business_types: [system_provider]
---
## 合成粗目 {#A}
"""

QUERY = "使用者問題ZZQUERY"
_Q = [1.0, 0.0, 0.0, 0.0]


def _vec(score: float) -> list:
    """單位向量，第一分量＝`score`（沿 `test_candidate_selector_req.py` 手法）。"""
    return [score, math.sqrt(max(0.0, 1.0 - score * score)), 0.0, 0.0]


def _fine_block(slug: str, title: str, *, content: str, target_user, business_types,
                 reviewed: bool = True) -> str:
    lines = [f"### {title} {{#prospect/A/{slug}}}"]
    lines += [
        "- sources: [kb:1]",
        f"- target_user: [{', '.join(target_user)}]",
        f"- business_types: [{', '.join(business_types)}]",
    ]
    if reviewed:
        lines.append("- reviewed: {by: test, at: 2026-09-07}")
    lines += ["- instance_applicability: general", content, ""]
    return "\n".join(lines)


def _doc(*blocks: str):
    return parse_canon_text(_FRONT_MATTER + "".join(blocks))


def fid(slug: str) -> str:
    return f"prospect/A/{slug}"


_CAND_TITLES = [f"標題ZZCAND{i}" for i in range(5)]
_CAND_CONTENTS = [f"內容ZZCAND{i}" for i in range(5)]
#: ⚠️ 第 6 個（出局）細目的**標題**刻意不帶 `ZZ` 標記——`outline:toc` 依規則列出
#: **每個可見已審細目**（不分有沒有中選），它的標題本來就該出現在目錄裡；
#: 真正不該外洩的是它的**內文**（被排除在 `sections` 之外，不該進 text／provenance／
#: system prompt）。用 `_UNSELECTED_TITLE`（不含標記）與 `_UNSELECTED_CONTENT`
#: （帶標記）分開斷言，才不會把「目錄合法列出標題」誤判成外洩。
_UNSELECTED_TITLE = "第六候選標題"
_UNSELECTED_CONTENT = "內容ZZUNSELECTED"
_HIDDEN_TITLE = "標題ZZHIDDEN"
_HIDDEN_CONTENT = "內容ZZHIDDEN"


def _six_fine_blocks() -> list:
    blocks = [
        _fine_block(f"cand-{i}", _CAND_TITLES[i], content=_CAND_CONTENTS[i],
                    target_user=["prospect"], business_types=["system_provider"])
        for i in range(5)
    ]
    blocks.append(
        _fine_block("cand-unselected", _UNSELECTED_TITLE, content=_UNSELECTED_CONTENT,
                    target_user=["prospect"], business_types=["system_provider"])
    )
    return blocks


def _hidden_block(*, target_user=("property_manager",)) -> str:
    return _fine_block("hidden", _HIDDEN_TITLE, content=_HIDDEN_CONTENT,
                        target_user=list(target_user), business_types=["system_provider"])


def _vectors_for_six() -> dict:
    vectors = {QUERY: _Q}
    for i, title in enumerate(_CAND_TITLES):
        vectors[title] = _vec(0.9 - i * 0.1)  # 0.9, 0.8, 0.7, 0.6, 0.5（遞減）
    vectors[_UNSELECTED_TITLE] = _vec(0.05)   # 全場最低分 ⇒ 第 6 名，出局
    return vectors


class _FakeBackend:
    """假 embedding 後端（樣式沿 `test_candidate_selector_req.py::_FakeBackend`）。"""

    def __init__(self, vectors=None, *, raises=False):
        self.vectors = dict(vectors or {})
        self._raises = raises
        self.calls = 0

    async def embed(self, texts):
        self.calls += 1
        if self._raises:
            raise RuntimeError("後端故障（測試用）")
        return [list(self.vectors.get(t, [0.0, 0.0, 1.0, 0.0])) for t in texts]


B2B_PROSPECT = Identity(vendor_id=1, target_user="prospect", mode="b2b", session_id="s1")
B2C_PROSPECT = Identity(vendor_id=1, target_user="prospect", mode="b2c", session_id="s1")


@pytest.fixture(autouse=True)
def _reset_registries():
    reset_canon_registry()
    reset_index_registry()
    yield
    reset_canon_registry()
    reset_index_registry()


def _real_assembler() -> PromptAssembler:
    return PromptAssembler(lambda identity: "persona-x", lambda identity: "policy-x")


async def _ready_index(doc, vectors) -> FineIndex:
    index = FineIndex(_FakeBackend(vectors))
    await index.prepare(doc)
    assert index.state == "ready"
    return index


# ---------------------------------------------------------------------------
# §2.4-1：候選路徑一回合
# ---------------------------------------------------------------------------


async def test_candidate_path_selects_top_k_and_excludes_lowest_scoring_fine():
    doc = _doc(*_six_fine_blocks())
    register_canon("prospect", doc)
    full = build_outline(doc)
    index = await _ready_index(doc, _vectors_for_six())
    register_index("prospect", index)
    selector = CandidateSelector(index)

    provider = FakeProvider([_final_response(answer="候選池的答案")])
    registry = FakeRegistry()
    verifier = FakeVerifier([VerifierVerdict(ok=True)])
    runtime = _runtime(
        provider=provider, registry=registry, verifier=verifier,
        assembler=_real_assembler(), candidate_selector=selector,
    )

    result = await runtime.run_turn(
        B2B_PROSPECT, QUERY, {"agent": {"outline": full, "dialog": []}}
    )

    assert result.kind == "answer"
    assert result.trace.miss_kind == "hit"
    assert result.trace.candidate_ids == [fid(f"cand-{i}") for i in range(5)]
    assert len(result.trace.candidate_ids) == K
    assert all(v == "title" for v in result.trace.winning_key_kind.values())
    assert "candidate_fallback_full_outline" not in result.trace.violations
    assert "candidate_selector_error" not in result.trace.violations
    assert "candidate_none_visible" not in result.trace.violations

    seen = verifier.calls[0]["tool_results"][OUTLINE_TOOL_CALL_ID]
    seen_ids = [p.source for p in seen.provenance]
    assert seen_ids == [fid(f"cand-{i}") for i in range(5)] + ["outline:toc"]
    # 第六名的「內文」（未中選細目的內容）不得出現在任一段 provenance——
    # ⚠️ 它的「標題」合法出現在 toc 那一段（目錄列出全部可見已審細目），
    # 這裡只驗內文，⛔ 不驗標題（驗標題會把合法的目錄行為誤判成外洩）。
    assert not any(_UNSELECTED_CONTENT in p.text for p in seen.provenance)

    system_prompt = provider.calls[0]["messages"][0]["content"]
    assert _UNSELECTED_CONTENT not in system_prompt
    # 正對照：它的標題確實在（目錄合法列出），證明上面「內文不在」不是因為
    # 整個第六個細目都被靜默清空。
    assert _UNSELECTED_TITLE in system_prompt

    # 正對照：同一材料改走 candidate_selector=None ⇒ ZZUNSELECTED 內文會出現
    # （證明上面「不出現」的斷言看得見它，不是量尺本身瞎了）。
    provider2 = FakeProvider([_final_response(answer="整份大綱的答案")])
    runtime2 = _runtime(
        provider=provider2, registry=FakeRegistry(), verifier=FakeVerifier([VerifierVerdict(ok=True)]),
        assembler=_real_assembler(), candidate_selector=None,
    )
    result2 = await runtime2.run_turn(
        B2B_PROSPECT, QUERY, {"agent": {"outline": full, "dialog": []}}
    )
    assert result2.trace.miss_kind is None
    system_prompt2 = provider2.calls[0]["messages"][0]["content"]
    assert _UNSELECTED_CONTENT in system_prompt2


# ---------------------------------------------------------------------------
# §2.4-2：降級路徑（a／b／c）＋ 1→0 計數器正對照
# ---------------------------------------------------------------------------


async def test_degraded_path_when_index_not_ready_uses_visible_subset():
    """(a) 後端 raise ⇒ prepare 後 index 為 not_ready ⇒ selector.select 回 None。"""
    doc = _doc(*_six_fine_blocks())
    register_canon("prospect", doc)
    full = build_outline(doc)
    broken_index = FineIndex(_FakeBackend(raises=True))
    await broken_index.prepare(doc)
    assert broken_index.state == "not_ready"
    register_index("prospect", broken_index)
    selector = CandidateSelector(broken_index)

    provider = FakeProvider([_final_response(answer="降級答案")])
    runtime = _runtime(
        provider=provider, registry=FakeRegistry(), verifier=FakeVerifier([VerifierVerdict(ok=True)]),
        assembler=_real_assembler(), candidate_selector=selector,
    )
    result = await runtime.run_turn(
        B2B_PROSPECT, QUERY, {"agent": {"outline": full, "dialog": []}}
    )

    assert result.trace.miss_kind == "index_unavailable"
    assert result.trace.candidate_ids == []
    assert "candidate_fallback_full_outline" in result.trace.violations
    # 降級＝可見細目全集（6 個都可見，含第 6 個的完整內文），⛔ 不是只有候選 5 個。
    system_prompt = provider.calls[0]["messages"][0]["content"]
    assert _UNSELECTED_CONTENT in system_prompt


async def test_degraded_path_when_selector_itself_raises():
    """(b) selector 本身 raise（monkeypatch `select`）⇒ candidate_selector_error，
    且**不含** fallback 字串。"""
    doc = _doc(*_six_fine_blocks())
    register_canon("prospect", doc)
    full = build_outline(doc)
    index = await _ready_index(doc, _vectors_for_six())
    register_index("prospect", index)
    selector = CandidateSelector(index)

    async def _boom(*args, **kwargs):
        raise RuntimeError("selector 故障（測試用）")

    selector.select = _boom  # type: ignore[method-assign]

    provider = FakeProvider([_final_response(answer="降級答案")])
    runtime = _runtime(
        provider=provider, registry=FakeRegistry(), verifier=FakeVerifier([VerifierVerdict(ok=True)]),
        assembler=_real_assembler(), candidate_selector=selector,
    )
    result = await runtime.run_turn(
        B2B_PROSPECT, QUERY, {"agent": {"outline": full, "dialog": []}}
    )

    assert result.trace.miss_kind == "index_unavailable"
    assert "candidate_selector_error" in result.trace.violations
    assert "candidate_fallback_full_outline" not in result.trace.violations


async def test_no_candidate_selector_leaves_outline_unchanged():
    """(c) `candidate_selector=None`（評估基線）⇒ outline 原樣、無 violation、
    `miss_kind=None`。"""
    doc = _doc(*_six_fine_blocks())
    register_canon("prospect", doc)
    full = build_outline(doc)

    provider = FakeProvider([_final_response(answer="基線答案")])
    runtime = _runtime(
        provider=provider, registry=FakeRegistry(), verifier=FakeVerifier([VerifierVerdict(ok=True)]),
        assembler=_real_assembler(), candidate_selector=None,
    )
    result = await runtime.run_turn(
        B2B_PROSPECT, QUERY, {"agent": {"outline": full, "dialog": []}}
    )

    assert result.trace.miss_kind is None
    assert result.trace.candidate_ids == []
    assert not any(v.startswith("candidate_") for v in result.trace.violations)


async def test_violation_counter_actually_toggles_1_to_0():
    """正對照：先故障一回合（violation 記到）、再正常一回合（同一批材料、
    好的 selector）⇒ violation 1→0，證明機制真的分得出兩種情境。"""
    doc = _doc(*_six_fine_blocks())
    register_canon("prospect", doc)
    full = build_outline(doc)

    broken_index = FineIndex(_FakeBackend(raises=True))
    await broken_index.prepare(doc)
    broken_selector = CandidateSelector(broken_index)
    provider1 = FakeProvider([_final_response(answer="第一回合")])
    runtime1 = _runtime(
        provider=provider1, registry=FakeRegistry(), verifier=FakeVerifier([VerifierVerdict(ok=True)]),
        candidate_selector=broken_selector,
    )
    result1 = await runtime1.run_turn(
        B2B_PROSPECT, QUERY, {"agent": {"outline": full, "dialog": []}}
    )
    assert "candidate_fallback_full_outline" in result1.trace.violations

    good_index = await _ready_index(doc, _vectors_for_six())
    good_selector = CandidateSelector(good_index)
    provider2 = FakeProvider([_final_response(answer="第二回合")])
    runtime2 = _runtime(
        provider=provider2, registry=FakeRegistry(), verifier=FakeVerifier([VerifierVerdict(ok=True)]),
        candidate_selector=good_selector,
    )
    result2 = await runtime2.run_turn(
        B2B_PROSPECT, QUERY, {"agent": {"outline": full, "dialog": []}}
    )
    assert "candidate_fallback_full_outline" not in result2.trace.violations


# ---------------------------------------------------------------------------
# §2.4-3：同一個 outline 物件餵 `_seed_outline_provenance` 與 `build_messages`
# ---------------------------------------------------------------------------


class _RecordingAssembler:
    def __init__(self):
        self.seen_outlines: list = []

    def build_messages(self, identity, outline, slots, dialog, tool_specs, nonce):
        self.seen_outlines.append(outline)
        return [{"role": "system", "content": "x"}]


async def _run_with_identity_spy(*, candidate_selector, monkeypatch):
    doc = _doc(*_six_fine_blocks())
    register_canon("prospect", doc)
    full = build_outline(doc)

    seed_calls: list = []
    real_seed = runtime_mod._seed_outline_provenance

    def _spy_seed(outline):
        seed_calls.append(outline)
        return real_seed(outline)

    monkeypatch.setattr(runtime_mod, "_seed_outline_provenance", _spy_seed)

    assembler = _RecordingAssembler()
    provider = FakeProvider([_final_response(answer="ok")])
    runtime = _runtime(
        provider=provider, registry=FakeRegistry(), verifier=FakeVerifier([VerifierVerdict(ok=True)]),
        assembler=assembler, candidate_selector=candidate_selector,
    )
    await runtime.run_turn(B2B_PROSPECT, QUERY, {"agent": {"outline": full, "dialog": []}})
    assert len(seed_calls) == 1 and len(assembler.seen_outlines) == 1
    return seed_calls[0], assembler.seen_outlines[0]


async def test_same_outline_object_on_candidate_path(monkeypatch):
    doc = _doc(*_six_fine_blocks())
    index = await _ready_index(doc, _vectors_for_six())
    selector = CandidateSelector(index)
    seeded_arg, assembler_arg = await _run_with_identity_spy(
        candidate_selector=selector, monkeypatch=monkeypatch
    )
    assert seeded_arg is assembler_arg
    assert isinstance(seeded_arg, CandidateOutlineDoc)


async def test_same_outline_object_on_degraded_path(monkeypatch):
    doc = _doc(*_six_fine_blocks())
    broken_index = FineIndex(_FakeBackend(raises=True))
    await broken_index.prepare(doc)
    selector = CandidateSelector(broken_index)
    seeded_arg, assembler_arg = await _run_with_identity_spy(
        candidate_selector=selector, monkeypatch=monkeypatch
    )
    assert seeded_arg is assembler_arg
    assert isinstance(seeded_arg, CandidateOutlineDoc)


# ---------------------------------------------------------------------------
# §2.4-4：不可見細目內容不得進 text（候選與降級兩路徑）
# ---------------------------------------------------------------------------


async def test_invisible_fine_content_never_leaks_candidate_or_degraded_path():
    doc = _doc(*_six_fine_blocks(), _hidden_block())
    register_canon("prospect", doc)
    full = build_outline(doc)

    vectors = _vectors_for_six()
    vectors[_HIDDEN_TITLE] = [1.0, 0.0, 0.0, 0.0]  # 分數最高，仍不得出現

    # 候選路徑
    index = await _ready_index(doc, vectors)
    selector = CandidateSelector(index)
    provider = FakeProvider([_final_response(answer="候選答案")])
    runtime = _runtime(
        provider=provider, registry=FakeRegistry(), verifier=FakeVerifier([VerifierVerdict(ok=True)]),
        assembler=_real_assembler(), candidate_selector=selector,
    )
    result = await runtime.run_turn(
        B2B_PROSPECT, QUERY, {"agent": {"outline": full, "dialog": []}}
    )
    system_prompt = provider.calls[0]["messages"][0]["content"]
    assert _HIDDEN_TITLE not in system_prompt and _HIDDEN_CONTENT not in system_prompt
    assert fid("hidden") not in result.trace.candidate_ids

    # 降級路徑
    broken_index = FineIndex(_FakeBackend(raises=True))
    await broken_index.prepare(doc)
    broken_selector = CandidateSelector(broken_index)
    provider2 = FakeProvider([_final_response(answer="降級答案")])
    runtime2 = _runtime(
        provider=provider2, registry=FakeRegistry(), verifier=FakeVerifier([VerifierVerdict(ok=True)]),
        assembler=_real_assembler(), candidate_selector=broken_selector,
    )
    await runtime2.run_turn(B2B_PROSPECT, QUERY, {"agent": {"outline": full, "dialog": []}})
    system_prompt2 = provider2.calls[0]["messages"][0]["content"]
    assert _HIDDEN_TITLE not in system_prompt2 and _HIDDEN_CONTENT not in system_prompt2

    # 正對照：把該細目改成 prospect 可見 ⇒ 降級路徑 text 含它
    visible_doc = _doc(*_six_fine_blocks(), _hidden_block(target_user=["prospect"]))
    reset_canon_registry()
    reset_index_registry()
    register_canon("prospect", visible_doc)
    full_visible = build_outline(visible_doc)
    broken_index2 = FineIndex(_FakeBackend(raises=True))
    await broken_index2.prepare(visible_doc)
    broken_selector2 = CandidateSelector(broken_index2)
    provider3 = FakeProvider([_final_response(answer="降級答案（可見版）")])
    runtime3 = _runtime(
        provider=provider3, registry=FakeRegistry(), verifier=FakeVerifier([VerifierVerdict(ok=True)]),
        assembler=_real_assembler(), candidate_selector=broken_selector2,
    )
    await runtime3.run_turn(B2B_PROSPECT, QUERY, {"agent": {"outline": full_visible, "dialog": []}})
    system_prompt3 = provider3.calls[0]["messages"][0]["content"]
    assert _HIDDEN_TITLE in system_prompt3


# ---------------------------------------------------------------------------
# §2.4-5：toc 每回合依身分算、citable=False、Verifier 拒 SOURCE_NOT_CITABLE
# ---------------------------------------------------------------------------


def _ref(nonce: str, unit: int, tool_call_id: str = OUTLINE_TOOL_CALL_ID, source: str = "outline:toc") -> str:
    return f"[{nonce}:{tool_call_id}:{source}§{unit}]"


def test_toc_section_not_citable_and_real_verifier_rejects_it():
    doc = _doc(*_six_fine_blocks())
    register_canon("prospect", doc)
    full = build_outline(doc)
    toc = build_canon_toc(doc, B2B_PROSPECT, vendor_business_types=frozenset())
    assert toc.citable is False
    assert toc.text  # 有可見已審細目 ⇒ 目錄非空，下面的引用才有東西可指

    sel = {
        "candidate_ids": [fid("cand-0")],
        "winning_key_kind": {fid("cand-0"): "title"},
        "scores": {fid("cand-0"): 0.9},
        "miss_kind": "hit",
    }
    candidate_outline = CandidateOutlineDoc.from_selection(full, sel, toc)
    seeded = _seed_outline_provenance(candidate_outline)
    tool_results = {OUTLINE_TOOL_CALL_ID: seeded}

    # 覆蓋率門檻是**片段側相對值**（見 verifier.py `_check_citation`）：句子要與
    # 引到的那個片段有足夠字元重疊，才會走到 `citable` 檢查那一步——
    # 這裡直接拿目錄片段本身當句子，保證重疊 100%，測的是「就算完全照抄目錄
    # 內容，只要來源不可引用照樣拒」。
    from services.agent.provenance_units import provenance_units as _units

    toc_unit_0 = _units(toc.text)[0]

    verifier = OutputVerifier(_load_rules())
    out = AgentOutput.model_validate(
        {
            "kind": "answer",
            "sentences": [
                {"text": toc_unit_0, "kind": "fact",
                 "refs": [_ref(_FIXTURE_NONCE, 0)]}
            ],
            "fact_class": "feature",
            "handoff_reason": None,
        }
    )
    resolved, resolve_errors = resolve_refs(out, tool_results, _FIXTURE_NONCE)
    verdict = verifier.verify(
        out, tool_results, "q", None, resolved=resolved, resolve_errors=resolve_errors
    )
    assert verdict.reason == "SOURCE_NOT_CITABLE"


def _load_rules():
    from services.agent.verifier import VerifierRules

    return VerifierRules.load(_RULES_PATH)


# ---------------------------------------------------------------------------
# §2.4-10：隱私——候選與降級全流程無查詢字串、無細目文字
# ---------------------------------------------------------------------------


async def test_no_query_or_fine_text_reaches_logs_or_stdout(caplog, capsys):
    """⚠️ 正對照組先跑：先證明 `caplog`／`capsys` 兩個擷取器都活著。"""
    caplog.set_level(logging.DEBUG)
    marker = "ZZPRIVACYPROBE"
    logging.getLogger("tests.candidate_outline.probe").warning(marker)
    print(marker)
    probe_out = capsys.readouterr()
    assert marker in caplog.text, "caplog 沒抓到標記 ⇒ 日誌擷取器壞了，下面的斷言不成立"
    assert marker in probe_out.out, "capsys 沒抓到標記 ⇒ stdout 擷取器壞了，下面的斷言不成立"
    caplog.clear()

    doc = _doc(*_six_fine_blocks())
    register_canon("prospect", doc)
    full = build_outline(doc)

    # ① 候選路徑
    index = await _ready_index(doc, _vectors_for_six())
    selector = CandidateSelector(index)
    provider = FakeProvider([_final_response(answer="候選答案")])
    runtime = _runtime(
        provider=provider, registry=FakeRegistry(), verifier=FakeVerifier([VerifierVerdict(ok=True)]),
        candidate_selector=selector,
    )
    await runtime.run_turn(B2B_PROSPECT, QUERY, {"agent": {"outline": full, "dialog": []}})

    # ② selector 例外路徑
    async def _boom(*a, **k):
        raise RuntimeError("boom")

    selector2 = CandidateSelector(index)
    selector2.select = _boom  # type: ignore[method-assign]
    provider2 = FakeProvider([_final_response(answer="降級答案")])
    runtime2 = _runtime(
        provider=provider2, registry=FakeRegistry(), verifier=FakeVerifier([VerifierVerdict(ok=True)]),
        candidate_selector=selector2,
    )
    await runtime2.run_turn(B2B_PROSPECT, QUERY, {"agent": {"outline": full, "dialog": []}})

    combined_log = caplog.text
    stdout_text = capsys.readouterr().out

    assert QUERY not in combined_log and QUERY not in stdout_text
    for leak in [*_CAND_TITLES, *_CAND_CONTENTS, _UNSELECTED_TITLE, _UNSELECTED_CONTENT]:
        assert leak not in combined_log, f"{leak!r} 外洩到 log"
        assert leak not in stdout_text, f"{leak!r} 外洩到 stdout"


# ---------------------------------------------------------------------------
# §2.4-11：b2c 模式的 prospect 身分 ⇒ none_visible（過渡行為，§5-6 待裁）
# ---------------------------------------------------------------------------


async def test_b2c_prospect_yields_none_visible_and_positive_control_b2b_hits():
    doc = _doc(*_six_fine_blocks())
    register_canon("prospect", doc)
    full = build_outline(doc)
    index = await _ready_index(doc, _vectors_for_six())
    selector = CandidateSelector(index)

    provider = FakeProvider([_final_response(answer="b2c 答案")])
    runtime = _runtime(
        provider=provider, registry=FakeRegistry(), verifier=FakeVerifier([VerifierVerdict(ok=True)]),
        assembler=_real_assembler(), candidate_selector=selector,
    )
    result = await runtime.run_turn(
        B2C_PROSPECT, QUERY, {"agent": {"outline": full, "dialog": []}}
    )

    assert result.trace.miss_kind == "none_visible"
    assert result.trace.candidate_ids == []
    assert "candidate_none_visible" in result.trace.violations
    system_prompt = provider.calls[0]["messages"][0]["content"]
    for title in _CAND_TITLES:
        assert title not in system_prompt

    # 正對照：同材料改 mode="b2b" ⇒ 候選路徑正常（hit、無該 violation）。
    index2 = await _ready_index(doc, _vectors_for_six())
    selector2 = CandidateSelector(index2)
    provider2 = FakeProvider([_final_response(answer="b2b 答案")])
    runtime2 = _runtime(
        provider=provider2, registry=FakeRegistry(), verifier=FakeVerifier([VerifierVerdict(ok=True)]),
        assembler=_real_assembler(), candidate_selector=selector2,
    )
    result2 = await runtime2.run_turn(
        B2B_PROSPECT, QUERY, {"agent": {"outline": full, "dialog": []}}
    )
    assert result2.trace.miss_kind == "hit"
    assert "candidate_none_visible" not in result2.trace.violations
