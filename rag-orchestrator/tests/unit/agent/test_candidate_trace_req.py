"""unit：任務 4.1 trace 三鍵——白名單、形狀守門、shadow／trace_view 鏡射
（Plan `inputs/plan-m-d-runtime-wiring-20260907.md` §2.4-6｜
knowledge-outline-and-intent-architecture:4.1）。

⛔ 不直接跑完整 `run_turn` 造出「id 形狀不合」的候選——`CandidateOutlineDoc.
from_selection` 對不存在的 id 會先 raise（進降級路徑），永遠走不到形狀守門那一關。
所以本檔直接對 `_emit_agent_decision`／`TurnTrace` 下手，這正是 runtime.py 實際
呼叫的同一個函式，測的就是產線那個守門，不是另一套仿寫。
"""
from __future__ import annotations

import datetime
import json

import pytest

from services.agent import runtime as runtime_mod
from services.agent import shadow as shadow_mod
from services.agent import trace_view
from services.agent.runtime import TurnTrace, _emit_agent_decision
from services.agent.output_schema import VerifierVerdict

from tests.unit.agent.test_runtime_req import _ALLOWED_AGENT_DECISION_KEYS

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:4.1"),
]


# ---------------------------------------------------------------------------
# 白名單：21 鍵恰好相等
# ---------------------------------------------------------------------------


def test_allowed_keys_is_exactly_twentyone_and_includes_candidate_trio():
    """16 → 18 → 21：DSP-038／W3 加了 `pending_id`／`receipt_id`；
    W8 (1)／S8-6 再加 `select_type`／`has_ref`／`slot_written`
    （子 spec agent-write-tools；⛔ 皆非原文，見 `runtime.TurnTrace` 註記——
    尤其 ⛔ **沒有 `select_ref`**，點選的那筆識別碼不進計量）。"""
    assert len(_ALLOWED_AGENT_DECISION_KEYS) == 21
    assert {"candidate_ids", "winning_key_kind", "miss_kind"} <= _ALLOWED_AGENT_DECISION_KEYS
    assert {"pending_id", "receipt_id"} <= _ALLOWED_AGENT_DECISION_KEYS
    assert {"select_type", "has_ref", "slot_written"} <= _ALLOWED_AGENT_DECISION_KEYS
    # 正對照：白名單裡真的沒有 ref 原值這一鍵（尺不是恆真——上一行證明它看得見新鍵）
    assert "select_ref" not in _ALLOWED_AGENT_DECISION_KEYS


# ---------------------------------------------------------------------------
# 形狀守門：正對照（bad id 形狀）＋（長度超過 K）＋（合法值放行）
# ---------------------------------------------------------------------------


def _capture(monkeypatch):
    captured: list[dict] = []
    monkeypatch.setattr(
        runtime_mod.usage_metering, "set_agent_decision", lambda d: captured.append(d)
    )
    return captured


def test_shape_gate_rejects_malformed_candidate_id(monkeypatch):
    captured = _capture(monkeypatch)
    trace = TurnTrace(
        trace_id="t-bad-id",
        candidate_ids=["outline:bad#p1"],   # 不符 `<audience>/<字母>/<slug>` 形狀
        winning_key_kind={},
        miss_kind="hit",
    )
    _emit_agent_decision(trace)

    assert captured[-1]["candidate_ids"] == []
    assert captured[-1]["winning_key_kind"] == {}
    # 守門會就地改寫 trace 本身（同一個物件也是 TurnResult.trace）。
    assert trace.candidate_ids == []
    assert trace.winning_key_kind == {}
    assert "candidate_ids_shape_invalid" in trace.violations


def test_shape_gate_rejects_length_over_k(monkeypatch):
    from services.agent.canon.candidate_selector import K

    captured = _capture(monkeypatch)
    ids = [f"prospect/A/f{i}" for i in range(K + 1)]  # 長度 6 > K=5
    trace = TurnTrace(trace_id="t-too-long", candidate_ids=ids, winning_key_kind={}, miss_kind="hit")
    _emit_agent_decision(trace)
    assert captured[-1]["candidate_ids"] == []
    assert "candidate_ids_shape_invalid" in trace.violations


def test_shape_gate_rejects_winning_key_kind_referencing_unknown_id(monkeypatch):
    captured = _capture(monkeypatch)
    trace = TurnTrace(
        trace_id="t-bad-key",
        candidate_ids=["prospect/A/f0"],
        winning_key_kind={"prospect/A/not-a-candidate": "title"},  # 鍵不在 candidate_ids 內
        miss_kind="hit",
    )
    _emit_agent_decision(trace)
    assert captured[-1]["candidate_ids"] == []
    assert "candidate_ids_shape_invalid" in trace.violations


def test_shape_gate_rejects_unknown_key_kind_value(monkeypatch):
    captured = _capture(monkeypatch)
    trace = TurnTrace(
        trace_id="t-bad-value",
        candidate_ids=["prospect/A/f0"],
        winning_key_kind={"prospect/A/f0": "not-a-real-kind"},  # 值不在允許值域
        miss_kind="hit",
    )
    _emit_agent_decision(trace)
    assert captured[-1]["candidate_ids"] == []
    assert "candidate_ids_shape_invalid" in trace.violations


def test_shape_gate_passes_well_formed_candidates(monkeypatch):
    """正對照：合乎形狀的值不被誤傷——沒有這條，上面四個「拒絕」測試可能只是
    「這道守門把什麼都清空」的假陽性。"""
    captured = _capture(monkeypatch)
    ids = ["prospect/A/f0", "prospect/A/f1"]
    trace = TurnTrace(
        trace_id="t-ok",
        candidate_ids=list(ids),
        winning_key_kind={"prospect/A/f0": "title", "prospect/A/f1": "phrasing"},
        miss_kind="hit",
    )
    _emit_agent_decision(trace)
    assert captured[-1]["candidate_ids"] == ids
    assert captured[-1]["winning_key_kind"] == {"prospect/A/f0": "title", "prospect/A/f1": "phrasing"}
    assert "candidate_ids_shape_invalid" not in trace.violations


# ---------------------------------------------------------------------------
# shadow._trace_to_dict 鏡射三鍵
# ---------------------------------------------------------------------------


def test_shadow_trace_to_dict_mirrors_candidate_trio():
    trace = TurnTrace(
        trace_id="t-shadow",
        verifier=[VerifierVerdict(ok=True)],
        final_kind="answer",
        candidate_ids=["prospect/A/f0", "prospect/A/f1"],
        winning_key_kind={"prospect/A/f0": "title"},
        miss_kind="hit",
    )
    d = shadow_mod._trace_to_dict(trace)
    assert d["candidate_ids"] == ["prospect/A/f0", "prospect/A/f1"]
    assert d["winning_key_kind"] == {"prospect/A/f0": "title"}
    assert d["miss_kind"] == "hit"
    # 三鍵值只有 id／列舉——序列化不炸、且不含被禁字面鍵（縱深檢查）。
    blob = json.loads(json.dumps(d, ensure_ascii=False))
    assert "answer" not in blob and "quote" not in blob and "user_message" not in blob


# ---------------------------------------------------------------------------
# trace_view.render_trace 鏡射三鍵，且 `_assert_no_verbatim` 仍然綠燈
# ---------------------------------------------------------------------------


def _row_with_candidates() -> dict:
    snapshot = {
        "agent": {
            "trace_id": "t-render",
            "tool_calls": [],
            "llm_calls": 1,
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "verifier": [{"reason": None, "sent": None, "term_id": None, "quote_len": None}],
            "final_kind": "answer",
            "handoff_reason": None,
            "latency_ms": 12,
            "rules_sha": "deadbeef",
            "outline_sha": "cafebabe",
            "candidate_ids": ["prospect/A/f0", "prospect/A/f1"],
            "winning_key_kind": {"prospect/A/f0": "title", "prospect/A/f1": "content"},
            "miss_kind": "hit",
            "violations": [],
            "replayed_from": None,
        }
    }
    return {
        "ts": datetime.datetime(2026, 9, 7, 0, 0, 0, tzinfo=datetime.timezone.utc),
        "session_id": "sess-render-0123456789",
        "vendor_id": 1,
        "decision_snapshot": snapshot,
    }


def test_render_trace_mirrors_candidate_trio_and_stays_verbatim_clean():
    view = trace_view.render_trace(_row_with_candidates())  # 內部已呼叫 `_assert_no_verbatim`
    assert view["candidates"] == {
        "ids": ["prospect/A/f0", "prospect/A/f1"],
        "winning_key_kind": {"prospect/A/f0": "title", "prospect/A/f1": "content"},
        "miss_kind": "hit",
    }


def test_render_trace_candidates_absent_when_snapshot_lacks_them():
    """舊回合（4.1 前）沒有這三鍵 ⇒ 三個子鍵一律 `None`，⛔ 不猜、不補值
    （沿 `trace_view.agent_snapshot` 既有慣例）。"""
    row = _row_with_candidates()
    row["decision_snapshot"]["agent"].pop("candidate_ids")
    row["decision_snapshot"]["agent"].pop("winning_key_kind")
    row["decision_snapshot"]["agent"].pop("miss_kind")
    view = trace_view.render_trace(row)
    assert view["candidates"] == {"ids": None, "winning_key_kind": None, "miss_kind": None}


def test_top_level_key_set_still_closed_with_candidates_key():
    view = trace_view.render_trace(_row_with_candidates())
    assert set(view) == {
        "trace_id", "at", "kind", "handoff_reason", "replayed_from",
        "steps", "verifier", "counts", "session", "rules_sha", "outline_sha",
        "candidates",
    }
