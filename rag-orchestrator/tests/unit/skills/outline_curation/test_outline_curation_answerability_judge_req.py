"""answerability_judge.py（1.6）：直打 API 判者——請求形狀、與 Workflow 版 prompt 逐位元等價、判者隔離、續跑、Reconcile 等價、成本。
不需要 anthropic SDK：以假 client 注入。"""
import importlib.util
import json
import os
import types

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:1.6")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))  # 容器內＝/（.claude 掛在 /.claude）
_SCRIPTS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts")


def _load(name):
    path = os.path.join(_SCRIPTS, f"{name}.py")
    if not os.path.exists(path):
        pytest.skip(f"{name}.py 不在掛載路徑")
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _args(n_cells=2):
    aa = _load("answerability_args")
    cands = [{"id": "tmp:kb:1", "title": "t1", "content": "c1"}, {"id": "tmp:draft:1", "title": "t2", "content": "c2"}]
    rubric = "---\nversion: x\n---\nrubric body"
    cells = []
    for i in range(n_cells):
        cell = {"id": f"C{i+1:02d}", "questions": [f"問句{i}"], "policy": "answer"}
        parts = aa.build_prompt_parts(cell, cands, rubric)
        cells.append({"cellId": cell["id"], "question": cell["questions"][0], "policy": "answer",
                      "cellBlock": parts["cellBlock"], "cellTail": parts["cellTail"],
                      "_full": aa.build_judge_prompt(cell, cands, rubric)})
    parts0 = aa.build_prompt_parts({"id": "C01", "questions": ["問句0"], "policy": "answer"}, cands, rubric)
    return {"step": "answerability", "frozenAt": "2026-09-06T00:00:00Z", "rubricSha": "r", "inputsSha": {"a": "1"},
            "promptHead": parts0["promptHead"], "candidatesBlock": parts0["candidatesBlock"],
            "fineIdEnum": ["tmp:kb:1", "tmp:draft:1"], "cells": cells}


class FakeClient:
    """依序回放 verdict；記錄每次請求。"""

    def __init__(self, script):
        self.script = list(script)  # 每項＝dict verdict 或 "refusal"
        self.requests = []
        self.messages = types.SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.requests.append(kw)
        item = self.script.pop(0)
        usage = types.SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=100,
                                      cache_creation=types.SimpleNamespace(ephemeral_5m_input_tokens=7, ephemeral_1h_input_tokens=0))
        if item == "refusal":
            return types.SimpleNamespace(stop_reason="refusal", content=[], usage=usage)
        return types.SimpleNamespace(stop_reason="end_turn", content=[types.SimpleNamespace(type="text", text=json.dumps(item))], usage=usage)


def _v(label, cell="C01", fine="tmp:kb:1"):
    return {"cell_id": cell, "label": label, "fine_id": fine if label in ("answerable", "partial") else None,
            "evidence_unit": 1 if label in ("answerable", "partial") else None, "confidence": "high", "provisional": True}


def test_workflow_layout_is_byte_identical_to_build_judge_prompt():
    """layout=workflow：system+user 逐位元＝build_judge_prompt ⇒ 可與 1.5 的 44 格 Workflow 結果合併；且不掛快取。"""
    m = _load("answerability_judge")
    a = _args(1)
    fc = FakeClient([_v("answerable"), _v("answerable")])
    m.run(a, fc, model="claude-sonnet-5", journal=m.Journal(None), concurrency=1, layout="workflow", log=lambda s: None)
    req = fc.requests[0]
    assert req["system"][0]["text"] + req["messages"][0]["content"] == a["cells"][0]["_full"]
    assert "cache_control" not in req["system"][0]


def test_cached_layout_shares_prefix_and_request_shape():
    m = _load("answerability_judge")
    a = _args(1)
    fc = FakeClient([_v("answerable"), _v("answerable")])
    out = m.run(a, fc, model="claude-sonnet-5", journal=m.Journal(None), concurrency=1, log=lambda s: None)
    req = fc.requests[0]
    assert req["model"] == "claude-sonnet-5"
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
    system_text = req["system"][0]["text"]
    user_text = req["messages"][0]["content"]
    assert system_text == a["promptHead"] + a["candidatesBlock"]
    assert user_text == a["cells"][0]["cellBlock"] + a["cells"][0]["cellTail"]
    assert sorted(system_text + user_text) == sorted(a["cells"][0]["_full"])  # 同內容、不同順序
    fmt = req["output_config"]["format"]
    assert req["output_config"]["effort"] == "low" and fmt["type"] == "json_schema"
    assert None in fmt["schema"]["properties"]["fine_id"]["enum"] and "tmp:kb:1" in fmt["schema"]["properties"]["fine_id"]["enum"]
    assert fmt["schema"]["additionalProperties"] is False
    assert out["total"] == 1 and out["agree"] == 1 and out["needs_rubric_revision"] is False


def test_judges_isolated_and_third_only_on_disagreement():
    m = _load("answerability_judge")
    a = _args(2)
    fc = FakeClient([_v("answerable"), _v("partial"), _v("partial"),   # C01：不一致 ⇒ 第 3 判者
                     _v("no_source", "C02"), _v("no_source", "C02")])  # C02：一致 ⇒ 2 個
    out = m.run(a, fc, model="claude-sonnet-5", journal=m.Journal(None), concurrency=1, log=lambda s: None)
    assert len(fc.requests) == 5
    # 三個 C01 請求逐位元相同（判者互不可見、slot 不進 prompt）
    c01 = [r for r in fc.requests if "C01" in r["messages"][0]["content"]]
    assert len(c01) == 3 and len({json.dumps(r, sort_keys=True) for r in c01}) == 1
    by = {e["cell_id"]: e for e in out["labels"]}
    assert by["C01"]["label"] == "partial" and len(by["C01"]["verdicts"]) == 3
    assert by["C02"]["label"] == "no_source" and len(by["C02"]["verdicts"]) == 2
    assert out["agree"] == 1 and out["agentsUsed"] == 5 and out["usage"]["calls"] == 5


def test_unresolved_three_way_falls_to_no_source_and_refusal_drops_cell():
    m = _load("answerability_judge")
    a = _args(2)
    fc = FakeClient([_v("answerable"), _v("partial"), _v("no_source"),   # C01 三不同 ⇒ unresolved
                     "refusal", _v("answerable", "C02"), _v("answerable", "C02")])  # C02 judge1 refusal ⇒ v1 缺 ⇒ dropped
    out = m.run(a, fc, model="claude-sonnet-5", journal=m.Journal(None), concurrency=1, log=lambda s: None)
    by = {e["cell_id"]: e for e in out["labels"]}
    assert by["C01"]["label"] == "no_source" and by["C01"]["unresolved"] is True
    assert "C02" not in by and out["droppedCells"] == 1 and out["total"] == 1


def test_journal_resume_skips_done_judges(tmp_path):
    m = _load("answerability_judge")
    a = _args(1)
    jpath = str(tmp_path / "j.jsonl")
    fc1 = FakeClient([_v("answerable"), _v("answerable")])
    m.run(a, fc1, model="claude-sonnet-5", journal=m.Journal(jpath), concurrency=1, log=lambda s: None)
    assert len(fc1.requests) == 2
    fc2 = FakeClient([])
    out = m.run(a, fc2, model="claude-sonnet-5", journal=m.Journal(jpath), concurrency=1, log=lambda s: None)
    assert fc2.requests == [] and out["total"] == 1 and out["usage"]["calls"] == 0
    recs = [json.loads(l) for l in open(jpath, encoding="utf-8")]
    assert {r["slot"] for r in recs} == {1, 2} and all(r["key"].endswith((":1", ":2")) for r in recs)


def test_cost_from_usage_and_price_table():
    m = _load("answerability_judge")
    a = _args(1)
    fc = FakeClient([_v("answerable"), _v("answerable")])
    price = {"model": "x", "input": 2.0, "output": 10.0, "cache_read": 0.2, "cache_write_5m": 2.5, "cache_write_1h": 4.0}
    out = m.run(a, fc, model="x", journal=m.Journal(None), concurrency=1, price=price, log=lambda s: None)
    u = out["usage"]
    assert (u["input"], u["output"], u["cache_read"], u["cache_write_5m"]) == (20, 10, 200, 14)
    assert out["usd"] == pytest.approx((20 * 2 + 10 * 10 + 200 * 0.2 + 14 * 2.5) / 1e6, abs=1e-12)


def test_journal_keys_differ_between_layouts():
    """兩種版面是兩版 prompt：journal key 不同，續跑不會互相冒用。"""
    m = _load("answerability_judge")
    a = _args(1)
    k_w = m.judge_key(*m.split_prompt(a, a["cells"][0], "workflow"), 1)
    k_c = m.judge_key(*m.split_prompt(a, a["cells"][0], "cached"), 1)
    assert k_w != k_c


def test_threshold_matches_workflow_and_merge():
    m = _load("answerability_judge")
    assert m.AGREEMENT_THRESHOLD == 0.80
    js = open(os.path.join(_REPO, ".claude", "workflows", "outline-curation.js"), encoding="utf-8").read()
    assert "const AGREEMENT_THRESHOLD = 0.80" in js
