"""unit：`tools/gapmap/coverage_map.py`＋`scripts/reweigh.py`（knowledge-outline-and-intent-architecture 任務 2.6｜design 元件 9｜R3.1–R3.7）。

Plan：`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-2.6-coverage-map-20260907.md` §3／§4／§7。
驗：規則表每列一案；決定性（同輸入兩次逐位元相等）；fail-loud 正對照（缺格、fine_id 不在正本、canon sha 竄改、
authority 未知形狀 ⇒ CoverageMapError／exit 2）；`needs_rubric_revision=true` ⇒ reweigh.py exit 2、false ⇒ 0；
envelope 過 schema；judge_agreement 逐格；retrieval_gap 格不得 fix_type=null。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:2.6")]

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_HERE))))       # host: <repo>/rag-orchestrator；容器：/app
_REPO = os.path.dirname(_RAG)
_SCRIPT = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts", "reweigh.py")
_SCHEMA = os.path.join(_REPO, ".claude", "skills", "outline-curation", "schemas", "coverage-reweigh.json")

sys.path.insert(0, _RAG)
from tools.gapmap import coverage_map as cm  # noqa: E402

_CANON = """---
audience: prospect
version: 2026-09-07.test
reviewers: [owner]
language: zh-TW
budget_tokens: 1000
target_user: [prospect]
business_types: [system_provider]
---
## A 測試粗目 {#A}
### 細目一 {#prospect/A/one}
- sources: [kb:1]
- see_also: [prospect/A/two]
- instance_applicability: general
第一句。
### 細目二 {#prospect/A/two}
- sources: [kb:2]
- see_also: [prospect/A/one]
- instance_applicability: general
第二句。
### 刻意不補 {#prospect/A/no}
- sources: [DECISIONS:DSP-009]
- policy: deliberate_no
- policy_ref: DECISIONS:DSP-009
- instance_applicability: general
不答。
"""


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _write(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(obj, str):
            f.write(obj)
        else:
            json.dump(obj, f, ensure_ascii=False)


def _label(cell_id, label, fine_id=None, verdict_labels=None):
    vs = [{"cell_id": cell_id, "label": l, "fine_id": fine_id if l in ("answerable", "partial") else None,
           "evidence_unit": None, "confidence": "high", "provisional": True} for l in (verdict_labels or [label, label])]
    return {"cell_id": cell_id, "label": label, "fine_id": fine_id, "evidence_unit": None,
            "confidence": "high", "provisional": True, "verdicts": vs}


#: 規則表每列一案（plan §3）。(cell, label, fine_id, cause_state, coverage, authority, policy_ref) → (disposition, fix_type, gaps)
_ROWS = [
    ("C01", "answerable", "prospect/A/one", "S_OK", "已覆蓋", "kb:1", None, "fine", None, []),
    ("C02", "answerable", "prospect/A/one", "S_OK", "未覆蓋(回答未含必含)", "kb:1", None, "fine", "add_knowledge", ["content_gap"]),
    ("C03", "answerable", "prospect/A/two", "V", "未覆蓋", "help:x", None, "fine", "add_phrasing", ["retrieval_gap"]),
    ("C04", "answerable", "prospect/A/two", "UNSTABLE['S', 'S_OK']", "已覆蓋⚠️", "kb:2", None, "fine", "add_knowledge", ["content_gap", "retrieval_gap"]),
    ("C05", "partial", "prospect/A/one", "S_OK", "已覆蓋", "kb:1", None, "fine", "add_knowledge", []),
    ("C06", "no_source", None, "V", "未覆蓋", "none（池外）", None, "owner_decision", "cross_audience_rewrite", []),
    ("C07", "no_source", None, "FALSE_HIT", "未覆蓋", "kb:5373(池外)；help:y", None, "owner_decision", "add_knowledge", []),
    ("C08", "no_source", None, "UNCLASSIFIED(待G0)", "未覆蓋", "none（G0③未找到）", None, "not_available", "list_not_available", []),
    ("C09", "no_source", None, "ADVICE", "n/a(一般建議)", "n/a（一般建議題）", None, "not_available", "list_not_available", []),
    ("C10", "deliberate_no", None, "DELIBERATE_NO", "符合(刻意不補)", "requirements 已拍板決策#2；DECISIONS", "DECISIONS:DSP-009", "deliberate_no", None, []),
    ("C11", "deliberate_no", None, "DELIBERATE_NO", "符合(刻意不補)", "requirements 已拍板決策#2；DECISIONS", None, "owner_decision", "owner_decision", []),
]


def _materials(tmp_path, rows=_ROWS, *, canon_text=_CANON, needs_rubric_revision=False, sha_override=None,
               drop_cell=None, bad_fine_id=None):
    canon = tmp_path / "canon.md"
    _write(canon, canon_text)
    demand = {"_meta": {}, "cells": [{"id": r[0], "topic": f"t{r[0]}", "questions": [f"q{r[0]}"], "policy": "answer",
                                      "policy_ref": r[6], "g0": {"authority": r[5]}} for r in rows]}
    measured = {"_meta": {}, "cells": [{"id": r[0], "cause_state": r[3], "entry_state": "answered", "coverage": r[4]} for r in rows]}
    labels = [_label(r[0], r[1], bad_fine_id if (bad_fine_id and r[0] == "C01") else r[2]) for r in rows if r[0] != drop_cell]
    ans = {"step": "answerability", "skill_version": "0.1.0", "inputs_sha": {"canon": sha_override or _sha(canon)},
           "deterministic": False, "raw_outputs_path": None, "cost": {},
           "payload": {"labels": labels, "needs_rubric_revision": needs_rubric_revision}}
    d, m, a = tmp_path / "demand.json", tmp_path / "map.json", tmp_path / "answerability.json"
    _write(d, demand); _write(m, measured); _write(a, ans)
    return str(canon), str(d), str(m), str(a)


def test_rule_table_every_row_hits_exactly_its_disposition(tmp_path):
    canon, d, m, a = _materials(tmp_path)
    cells = {c["cell_id"]: c for c in cm.build_coverage_map(canon, d, m, a)["cells"]}
    assert len(cells) == len(_ROWS)
    for r in _ROWS:
        c = cells[r[0]]
        assert (c["disposition"], c["fix_type"], c["gap_classes"]) == (r[7], r[8], r[9]), r[0]
        assert c["disposition"] in cm.DISPOSITIONS
        assert c["fix_type"] is None or c["fix_type"] in cm.FIX_TYPES
    # R3.6：跨受眾改寫只給草稿路徑，⛔ 不開放列
    assert cells["C06"]["draft_path"] and cells["C06"]["fine_id"] is None
    # retrieval_gap 格不得 fix_type=null（plan-verifier 第 2 輪）
    assert not [k for k, c in cells.items() if "retrieval_gap" in c["gap_classes"] and c["fix_type"] is None]
    assert cells["C01"]["min_verification"] == {"phrasings": ["qC01"], "expected_fine_id": "prospect/A/one"}


def test_deterministic_and_meta(tmp_path):
    canon, d, m, a = _materials(tmp_path)
    x = json.dumps(cm.build_coverage_map(canon, d, m, a), ensure_ascii=False, sort_keys=True)
    y = json.dumps(cm.build_coverage_map(canon, d, m, a), ensure_ascii=False, sort_keys=True)
    assert x == y
    meta = json.loads(x)["_meta"]
    assert meta["summary"]["cells_without_disposition"] == 0
    assert meta["fines_without_sources"] == []
    # see_also 互指且兩細目皆為正解 ⇒ 提案、⛔ 不合併
    assert meta["merge_similar_candidates"] == [{"a": "prospect/A/one", "b": "prospect/A/two", "fix_type": "merge_similar", "status": "proposed"}]


def test_judge_agreement_per_cell_from_verdicts(tmp_path):
    rows = [("C01", "answerable", "prospect/A/one", "S_OK", "已覆蓋", "kb:1", None, "fine", None, [])]
    canon, d, m, a = _materials(tmp_path, rows)
    ans = json.load(open(a, encoding="utf-8"))
    ans["payload"]["labels"][0]["verdicts"] = [
        {"label": "answerable"}, {"label": "partial"}, {"label": "answerable"}]
    _write(a, ans)
    out = cm.build_coverage_map(canon, d, m, a)
    assert out["cells"][0]["judge_agreement"] == pytest.approx(2 / 3)
    assert out["_meta"]["summary"]["judge_agreement_global"] == 0.0        # 唯一一格三票不全同
    # 正對照：verdicts 全同 ⇒ 1.0／global 1.0
    ans["payload"]["labels"][0]["verdicts"] = [{"label": "answerable"}, {"label": "answerable"}]
    _write(a, ans)
    out = cm.build_coverage_map(canon, d, m, a)
    assert out["cells"][0]["judge_agreement"] == 1.0 and out["_meta"]["summary"]["judge_agreement_global"] == 1.0


@pytest.mark.parametrize("kw,needle", [
    (dict(drop_cell="C03"), "判者裁定缺此格"),
    (dict(bad_fine_id="prospect/A/nope"), "不在正本"),
    (dict(sha_override="0" * 64), "另一版正本"),
])
def test_fail_loud_positive_controls(tmp_path, kw, needle):
    canon, d, m, a = _materials(tmp_path, **kw)
    with pytest.raises(cm.CoverageMapError, match=needle):
        cm.build_coverage_map(canon, d, m, a)


def test_authority_unknown_shape_fails_loud(tmp_path):
    rows = [("C01", "no_source", None, "S", "未覆蓋", "maybe: 某處", None, None, None, [])]
    canon, d, m, a = _materials(tmp_path, rows)
    with pytest.raises(cm.CoverageMapError, match="g0.authority 形狀未知"):
        cm.build_coverage_map(canon, d, m, a)
    # 正對照：已知哨兵
    assert cm.has_authority("kb:1") is True and cm.has_authority("help:x") is True
    assert cm.has_authority("none（…）") is False and cm.has_authority("n/a（一般建議題）") is False


def _run_script(tmp_path, a_path_args, env_root):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(env_root))
    return subprocess.run([sys.executable, _SCRIPT, *a_path_args], capture_output=True, text=True, env=env)


def _fake_repo(tmp_path):
    """reweigh.py 靠 CLAUDE_PROJECT_DIR 找 repo 根與 rag-orchestrator；用 symlink 指回真 rag-orchestrator。"""
    root = tmp_path / "repo"
    (root / ".claude").mkdir(parents=True)
    _write(root / ".claude" / "settings.json", "{}")
    os.symlink(_RAG, root / "rag-orchestrator")
    return root


def test_reweigh_script_envelope_and_state(tmp_path):
    if not os.path.isfile(_SCRIPT):
        pytest.skip(f"[env] 找不到 {_SCRIPT}——容器需掛 repo 根 .claude/")
    root = _fake_repo(tmp_path)
    canon, d, m, a = _materials(tmp_path)
    cov, out = tmp_path / "coverage-map.json", tmp_path / "coverage-reweigh.json"
    proc = _run_script(tmp_path, ["--canon", canon, "--demand", d, "--map", m, "--answerability", a,
                                  "--coverage-out", str(cov), "--out", str(out)], root)
    assert proc.returncode == 0, proc.stderr
    env = json.load(open(out, encoding="utf-8"))
    sys.path.insert(0, os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts"))
    from _envelope import load_schema, validate  # noqa: E402
    validate(env, load_schema(_SCHEMA))
    assert env["step"] == "reweigh" and env["deterministic"] is True and len(env["payload"]["cells"]) == len(_ROWS)
    assert set(env["payload"]) == {"cells"}                                   # _meta 不進 envelope
    state = json.load(open(root / ".claude" / "hooks" / "state" / "outline-gate" / "session.json", encoding="utf-8"))
    assert state["reweigh"] == {"path": os.path.relpath(out, root), "cells_without_disposition": 0, "fines_without_sources": 0}


def test_reweigh_script_needs_rubric_revision_exit2_positive_control(tmp_path):
    if not os.path.isfile(_SCRIPT):
        pytest.skip(f"[env] 找不到 {_SCRIPT}")
    root = _fake_repo(tmp_path)
    for flag, expected in ((True, 2), (False, 0)):
        canon, d, m, a = _materials(tmp_path, needs_rubric_revision=flag)
        proc = _run_script(tmp_path, ["--canon", canon, "--demand", d, "--map", m, "--answerability", a,
                                      "--coverage-out", str(tmp_path / "c.json"), "--out", str(tmp_path / "e.json")], root)
        assert proc.returncode == expected, (flag, proc.stderr)
        if flag:
            assert "needs_rubric_revision" in proc.stderr and not (tmp_path / "e.json").exists()


def test_fine_without_sources_blocks_exit(tmp_path):
    canon_text = _CANON.replace("- sources: [kb:2]\n", "- sources: []\n")
    canon, d, m, a = _materials(tmp_path, canon_text=canon_text)
    out = cm.build_coverage_map(canon, d, m, a)
    assert out["_meta"]["fines_without_sources"] == ["prospect/A/two"]
    assert cm.main(["--canon", canon, "--demand", d, "--map", m, "--answerability", a, "--out", str(tmp_path / "o.json")]) == 2
