"""步 4 子代理版 `answerability_agents.py`（業主 2026-09-06 裁：步 4 也用 Claude Code）：分組決定性、prompt 逐位元、collect 驗證與第 3 判者、Reconcile 等價。"""
import importlib.util
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:1.6")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
_SCRIPTS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts")


def _load(name):
    path = os.path.join(_SCRIPTS, f"{name}.py")
    if not os.path.exists(path):
        pytest.skip(f"{name}.py 不在掛載路徑")
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _args(n=7):
    aa = _load("answerability_args")
    cands = [{"id": "tmp:kb:1", "title": "t1", "content": "c1。"}, {"id": "tmp:draft:1", "title": "t2", "content": "c2。"}]
    rubric = "---\nversion: x\n---\nrubric body"
    cells = []
    for i in range(n):
        cell = {"id": f"C{i+1:02d}", "questions": [f"問句{i}"], "policy": "answer"}
        parts = aa.build_prompt_parts(cell, cands, rubric)
        cells.append({"cellId": cell["id"], "question": cell["questions"][0], "policy": "answer", "cellBlock": parts["cellBlock"], "cellTail": parts["cellTail"]})
    p0 = aa.build_prompt_parts({"id": "C01", "questions": ["問句0"], "policy": "answer"}, cands, rubric)
    return {"step": "answerability", "frozenAt": "2026-09-06T00:00:00Z", "rubricSha": "r", "inputsSha": {"a": "1"},
            "promptHead": p0["promptHead"], "candidatesBlock": p0["candidatesBlock"], "fineIdEnum": ["tmp:kb:1", "tmp:draft:1"], "cells": cells}


def _v(cell, label, fine="tmp:kb:1"):
    return {"cell_id": cell, "label": label, "fine_id": fine if label in ("answerable", "partial") else None,
            "evidence_unit": 1 if label in ("answerable", "partial") else None, "confidence": "high", "provisional": True}


def _run(argv):
    return subprocess.run([sys.executable, os.path.join(_SCRIPTS, "answerability_agents.py")] + argv, capture_output=True, text=True)


def test_prepare_groups_deterministically_and_slots_identical(tmp_path):
    a = tmp_path / "args.json"; a.write_text(json.dumps(_args(7), ensure_ascii=False), encoding="utf-8")
    r = _run(["prepare", "--args", str(a), "--out-dir", str(tmp_path / "o"), "--cells-per-agent", "3"])
    assert r.returncode == 0, r.stderr
    m = json.loads((tmp_path / "o" / "manifest.json").read_text(encoding="utf-8"))
    assert [g["cell_ids"] for g in m["groups"]] == [["C01", "C02", "C03"], ["C04", "C05", "C06"], ["C07"]]
    g = m["groups"][0]
    t1 = open(g["prompts"]["1"], encoding="utf-8").read(); t2 = open(g["prompts"]["2"], encoding="utf-8").read()
    assert t1 == t2 and "C01" in t1 and "C02" in t1 and "C04" not in t1 and "tmp:draft:1" in t1
    assert "score" not in t1 and "例如" not in t1
    r2 = _run(["prepare", "--args", str(a), "--out-dir", str(tmp_path / "o2"), "--cells-per-agent", "3"])
    m2 = json.loads((tmp_path / "o2" / "manifest.json").read_text(encoding="utf-8"))
    assert [g["prompt_sha256"] for g in m["groups"]] == [g["prompt_sha256"] for g in m2["groups"]]


def test_collect_reports_missing_then_third_then_reconciles(tmp_path):
    a = tmp_path / "args.json"; a.write_text(json.dumps(_args(4), ensure_ascii=False), encoding="utf-8")
    o = tmp_path / "o"
    assert _run(["prepare", "--args", str(a), "--out-dir", str(o), "--cells-per-agent", "2"]).returncode == 0
    r = _run(["collect", "--args", str(a), "--out-dir", str(o), "--out", str(tmp_path / "res.json")])
    assert r.returncode == 3 and "尚缺" in r.stderr
    v = o / "verdicts"
    # G01：C01 一致、C02 不一致；G02：C03 一致、C04 slot2 壞掉（fine_id 不在 enum ⇒ 視同缺）
    (v / "G01-s1.json").write_text(json.dumps([_v("C01", "answerable"), _v("C02", "partial")]), encoding="utf-8")
    (v / "G01-s2.json").write_text("```json\n" + json.dumps([_v("C01", "answerable"), _v("C02", "no_source")]) + "\n```", encoding="utf-8")
    (v / "G02-s1.json").write_text(json.dumps([_v("C03", "no_source"), _v("C04", "answerable")]), encoding="utf-8")
    (v / "G02-s2.json").write_text(json.dumps([_v("C03", "no_source"), dict(_v("C04", "answerable"), fine_id="tmp:kb:999")]), encoding="utf-8")
    r = _run(["collect", "--args", str(a), "--out-dir", str(o), "--out", str(tmp_path / "res.json")])
    assert r.returncode == 4 and (o / "prompts" / "third.prompt.md").exists()
    third_cells = json.loads((o / "third-cells.json").read_text(encoding="utf-8"))
    assert third_cells == ["C02", "C04"]
    tp = (o / "prompts" / "third.prompt.md").read_text(encoding="utf-8")
    assert "C02" in tp and "C04" in tp and "C01" not in tp
    (v / "third.json").write_text(json.dumps([_v("C02", "no_source"), _v("C04", "answerable")]), encoding="utf-8")
    r = _run(["collect", "--args", str(a), "--out-dir", str(o), "--out", str(tmp_path / "res.json")])
    assert r.returncode == 0, r.stderr
    res = json.loads((tmp_path / "res.json").read_text(encoding="utf-8"))
    by = {e["cell_id"]: e for e in res["labels"]}
    assert by["C01"]["label"] == "answerable" and len(by["C01"]["verdicts"]) == 2
    assert by["C02"]["label"] == "no_source" and len(by["C02"]["verdicts"]) == 3
    assert by["C03"]["label"] == "no_source"
    assert "C04" not in by and res["droppedCells"] == 1  # v2 壞 ⇒ 格丟（no silent caps）
    assert res["total"] == 3 and res["agree"] == 2 and res["usage"]["provider"] == "claude-code-subagent" and res["usd"] is None
    assert res["needs_rubric_revision"] is True  # 2/3 < 0.80


def test_threshold_same_as_merge_script():
    assert _load("answerability_agents").AGREEMENT_THRESHOLD == _load("merge_answerability_batches").AGREEMENT_THRESHOLD == 0.80
