"""unit：`scripts/finalize_answerability.py`（knowledge-outline-and-intent-architecture 任務 1.4｜design 元件 2）。

驗：假 run-result（3 格、一致率 1.0）⇒ envelope 過 `schemas/answerability.json`、journal 檔存在、
session.json `answerability.needs_rubric_revision=false`、exit 0；一致率 0.5（正對照）⇒ exit 2 且
flag true、但檔案仍寫出（不是靜默丟棄證據）。
"""
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:1.5")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
_SCRIPT = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts", "finalize_answerability.py")
_SCHEMA_DIR = os.path.join(_REPO, ".claude", "skills", "outline-curation", "schemas")


def _skip_if_missing():
    if not os.path.isfile(_SCRIPT):
        pytest.skip(f"[env] 找不到 {_SCRIPT}——容器需掛 repo 根 .claude/，宿主直跑本檔")


def _write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def _run_result(agreement_rate_labels):
    """agreement_rate_labels：list of (cell_id, v1_label, v2_label)。"""
    labels = []
    agree = 0
    for cell_id, l1, l2 in agreement_rate_labels:
        v1 = {"cell_id": cell_id, "label": l1, "fine_id": "tmp:kb:1", "evidence_unit": 0, "confidence": "high", "provisional": True}
        v2 = {"cell_id": cell_id, "label": l2, "fine_id": "tmp:kb:1", "evidence_unit": 0, "confidence": "high", "provisional": True}
        is_agree = l1 == l2
        if is_agree:
            agree += 1
        final_label = l1 if is_agree else "no_source"
        entry = {
            "cell_id": cell_id, "label": final_label, "fine_id": "tmp:kb:1" if is_agree else None,
            "evidence_unit": 0 if is_agree else None, "confidence": "high", "provisional": True,
            "verdicts": [v1, v2],
        }
        if not is_agree:
            entry["unresolved"] = True
        labels.append(entry)
    total = len(labels)
    rate = agree / total if total else 0
    return {
        "step": "answerability",
        "frozenAt": "2026-09-06T00:00:00Z",
        "rubricSha": "a" * 64,
        "inputsSha": {"cells": "b" * 64, "kbRows": "c" * 64, "drafts": "d" * 64, "rubric": "a" * 64},
        "total": total,
        "agree": agree,
        "agreementRate": rate,
        "needs_rubric_revision": rate < 0.90,
        "agentsUsed": total * 2,
        "labels": labels,
    }


def _run(tmp_path, run_result_path, out_path, journal_dir, run_id="testrun"):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    cmd = [
        sys.executable, _SCRIPT,
        "--run-result", run_result_path,
        "--out", out_path,
        "--journal-dir", journal_dir,
        "--run-id", run_id,
        "--usd", "0.3",
        "--prompt-tokens", "600",
        "--completion-tokens", "300",
        "--wall-s", "12.5",
    ]
    return subprocess.run(cmd, env=env, capture_output=True, text=True)


def test_help_runs():
    _skip_if_missing()
    r = subprocess.run([sys.executable, _SCRIPT, "--help"], capture_output=True, text=True)
    assert r.returncode == 0


def test_agreement_1_0_passes_schema_and_exit_0(tmp_path):
    _skip_if_missing()
    sys.path.insert(0, os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts"))
    import importlib
    envelope_mod = importlib.import_module("_envelope")

    run_result = _run_result([("C01", "answerable", "answerable"),
                               ("C02", "no_source", "no_source"),
                               ("C03", "partial", "partial")])
    rr_path = tmp_path / "run_result.json"
    _write_json(rr_path, run_result)

    out = tmp_path / "answerability.json"
    journal_dir = tmp_path / "journal"
    r = _run(tmp_path, str(rr_path), str(out), str(journal_dir))
    assert r.returncode == 0, r.stderr

    envelope_mod.validate_file(str(out), os.path.join(_SCHEMA_DIR, "answerability.json"))

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["payload"]["needs_rubric_revision"] is False
    assert data["deterministic"] is False
    assert data["raw_outputs_path"] is not None

    journal_path = tmp_path / "journal" / "testrun.json"
    assert journal_path.is_file()
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    assert journal["step"] == "answerability"
    assert len(journal["agents"]) == run_result["agentsUsed"]

    state_path = os.path.join(str(tmp_path), ".claude", "hooks", "state", "outline-gate", "session.json")
    assert os.path.isfile(state_path)
    state = json.loads(open(state_path, encoding="utf-8").read())
    assert state["answerability"]["needs_rubric_revision"] is False


def test_agreement_0_5_exit_2_flag_true_but_file_still_written(tmp_path):
    """正對照：一致率 0.5 <0.90 ⇒ needs_rubric_revision=true、exit 2，但檔案與 journal 仍寫出。"""
    _skip_if_missing()
    run_result = _run_result([("C01", "answerable", "answerable"),
                               ("C02", "no_source", "no_source"),
                               ("C03", "partial", "no_source"),
                               ("C04", "answerable", "no_source")])
    assert run_result["agreementRate"] == 0.5
    rr_path = tmp_path / "run_result.json"
    _write_json(rr_path, run_result)

    out = tmp_path / "answerability.json"
    journal_dir = tmp_path / "journal"
    r = _run(tmp_path, str(rr_path), str(out), str(journal_dir), run_id="testrun2")
    assert r.returncode == 2

    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["payload"]["needs_rubric_revision"] is True

    journal_path = tmp_path / "journal" / "testrun2.json"
    assert journal_path.is_file()

    state_path = os.path.join(str(tmp_path), ".claude", "hooks", "state", "outline-gate", "session.json")
    state = json.loads(open(state_path, encoding="utf-8").read())
    assert state["answerability"]["needs_rubric_revision"] is True


def test_token_and_usd_distributed_across_journal_agents(tmp_path):
    _skip_if_missing()
    run_result = _run_result([("C01", "answerable", "answerable"), ("C02", "no_source", "no_source")])
    rr_path = tmp_path / "run_result.json"
    _write_json(rr_path, run_result)
    out = tmp_path / "answerability.json"
    journal_dir = tmp_path / "journal"
    r = _run(tmp_path, str(rr_path), str(out), str(journal_dir), run_id="testrun3")
    assert r.returncode == 0, r.stderr
    journal = json.loads((journal_dir / "testrun3.json").read_text(encoding="utf-8"))
    assert sum(a["prompt_tokens"] for a in journal["agents"]) == 600
    assert sum(a["completion_tokens"] for a in journal["agents"]) == 300
    assert abs(sum(a["usd"] for a in journal["agents"]) - 0.3) < 1e-9
