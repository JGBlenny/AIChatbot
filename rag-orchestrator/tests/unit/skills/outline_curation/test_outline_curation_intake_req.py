"""unit：`scripts/intake.py`（knowledge-outline-and-intent-architecture 任務 1.3｜design 元件 1）。

驗：同輸入跑兩次逐位元相等（可回放）；輸出通過 `schemas/intake.json`；
inputs_sha 對每個輸入都有且等於實算 sha256（正對照：故意改一個輸入位元組必變）。
"""
import hashlib
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:1.6")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
_SCRIPT = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts", "intake.py")
_SCHEMA_DIR = os.path.join(_REPO, ".claude", "skills", "outline-curation", "schemas")


def _skip_if_missing():
    if not os.path.isfile(_SCRIPT):
        pytest.skip(f"[env] 找不到 {_SCRIPT}——容器需掛 repo 根 .claude/，宿主直跑本檔")


def _write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _run(tmp_path, kb_path, drafts_path, gapmap_path, out_path, canon_path=None):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    cmd = [
        sys.executable, _SCRIPT,
        "--kb-json", kb_path,
        "--drafts", drafts_path,
        "--gapmap", gapmap_path,
        "--out", out_path,
        "--frozen-at", "2026-09-06T00:00:00Z",
    ]
    if canon_path:
        cmd += ["--canon", canon_path]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r


@pytest.fixture
def inputs(tmp_path):
    kb = tmp_path / "kb.json"
    drafts = tmp_path / "drafts.json"
    gapmap = tmp_path / "gapmap.json"
    _write_json(kb, [{"id": "kb-1", "question_summary": "退租流程是什麼樣的完整說明超過四十字元的內容測試"}])
    _write_json(drafts, [{"id": "d-1", "summary": "草稿摘要"}])
    _write_json(gapmap, [{"cell": "a"}, {"cell": "b"}])
    return str(kb), str(drafts), str(gapmap)


def test_help_runs():
    _skip_if_missing()
    r = subprocess.run([sys.executable, _SCRIPT, "--help"], capture_output=True, text=True)
    assert r.returncode == 0


def test_deterministic_byte_identical(tmp_path, inputs):
    _skip_if_missing()
    kb, drafts, gapmap = inputs
    out1 = tmp_path / "out1.json"
    out2 = tmp_path / "out2.json"
    _run(tmp_path, kb, drafts, gapmap, str(out1))
    _run(tmp_path, kb, drafts, gapmap, str(out2))
    assert out1.read_bytes() == out2.read_bytes()


def test_inputs_sha_matches_actual(tmp_path, inputs):
    _skip_if_missing()
    kb, drafts, gapmap = inputs
    out = tmp_path / "out.json"
    _run(tmp_path, kb, drafts, gapmap, str(out))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["inputs_sha"]["kb"] == _sha(kb)
    assert data["inputs_sha"]["drafts"] == _sha(drafts)
    assert data["inputs_sha"]["gapmap"] == _sha(gapmap)


def test_inputs_sha_changes_when_input_changes(tmp_path, inputs):
    """正對照：改一個輸入位元組 ⇒ 對應 sha 必變（證明 sha 真的在算內容，不是恆定值）。"""
    _skip_if_missing()
    kb, drafts, gapmap = inputs
    out1 = tmp_path / "out1.json"
    _run(tmp_path, kb, drafts, gapmap, str(out1))
    sha_before = json.loads(out1.read_text(encoding="utf-8"))["inputs_sha"]["kb"]

    _write_json(kb, [{"id": "kb-1-changed", "question_summary": "改過的內容"}])
    out2 = tmp_path / "out2.json"
    _run(tmp_path, kb, drafts, gapmap, str(out2))
    sha_after = json.loads(out2.read_text(encoding="utf-8"))["inputs_sha"]["kb"]
    assert sha_before != sha_after


def test_output_passes_schema(tmp_path, inputs):
    _skip_if_missing()
    sys.path.insert(0, os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts"))
    import importlib
    envelope = importlib.import_module("_envelope")

    kb, drafts, gapmap = inputs
    out = tmp_path / "out.json"
    _run(tmp_path, kb, drafts, gapmap, str(out))
    envelope.validate_file(str(out), os.path.join(_SCHEMA_DIR, "intake.json"))


def test_object_under_test_skeleton_present(tmp_path, inputs):
    _skip_if_missing()
    kb, drafts, gapmap = inputs
    out = tmp_path / "out.json"
    _run(tmp_path, kb, drafts, gapmap, str(out))
    data = json.loads(out.read_text(encoding="utf-8"))
    oaut = data["payload"]["object_under_test"]
    assert oaut["approved_by"] == ""
    assert oaut["frozen_at"] == "2026-09-06T00:00:00Z"
    assert isinstance(oaut["materials"], list) and oaut["materials"]
