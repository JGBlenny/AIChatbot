"""unit：`scripts/diff_report.py`（knowledge-outline-and-intent-architecture 任務 1.3｜design 元件 1）。

驗：缺 --id-map exit 2；同輸入兩次逐位元相等；輸出通過 schema；
replacements 三種 how（content／merged_into／phrasing_only）各一案；
狀態檔 diff_report.inputs_sha.canon ＝ new-canon 實算 sha256。
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
_SCRIPT = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts", "diff_report.py")
_SCHEMA_DIR = os.path.join(_REPO, ".claude", "skills", "outline-curation", "schemas")

_NEW_CANON = """## 粗目 A {#a}
內容

### 細目 A1 {#a1}
內容

### 細目 A2 {#a2}
新內容
"""

_OLD_CANON = """## 粗目 A {#a}
內容

### 細目 A1 舊名 {#a1}
內容

### 細目 A0 {#a0}
將被刪除
"""

_ID_MAP = [
    {"old_kb_id": "kb-1", "fine_id": "a1", "op": "keep"},
    {"old_kb_id": "kb-2", "fine_id": "a1", "op": "merge"},
    {"old_kb_id": "kb-3", "fine_id": "a2", "op": "new", "source": "phrasing"},
]


def _skip_if_missing():
    if not os.path.isfile(_SCRIPT):
        pytest.skip(f"[env] 找不到 {_SCRIPT}——容器需掛 repo 根 .claude/，宿主直跑本檔")


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.fixture
def canons(tmp_path):
    new_canon = tmp_path / "new.md"
    old_canon = tmp_path / "old.md"
    id_map = tmp_path / "id_map.json"
    new_canon.write_text(_NEW_CANON, encoding="utf-8")
    old_canon.write_text(_OLD_CANON, encoding="utf-8")
    id_map.write_text(json.dumps(_ID_MAP, ensure_ascii=False), encoding="utf-8")
    return str(new_canon), str(old_canon), str(id_map)


def _run(tmp_path, new_canon, old_canon, id_map, out, extra=None):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    cmd = [sys.executable, _SCRIPT, "--new-canon", new_canon, "--old-canon", old_canon,
           "--id-map", id_map, "--out", out, "--frozen-at", "2026-09-06T00:00:00Z"]
    if extra:
        cmd += extra
    return subprocess.run(cmd, env=env, capture_output=True, text=True)


def test_help_runs():
    _skip_if_missing()
    r = subprocess.run([sys.executable, _SCRIPT, "--help"], capture_output=True, text=True)
    assert r.returncode == 0


def test_missing_id_map_exits_2(tmp_path, canons):
    _skip_if_missing()
    new_canon, old_canon, _ = canons
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    r = subprocess.run(
        [sys.executable, _SCRIPT, "--new-canon", new_canon, "--old-canon", old_canon,
         "--id-map", str(tmp_path / "does-not-exist.json"),
         "--out", str(tmp_path / "out.json"), "--frozen-at", "2026-09-06T00:00:00Z"],
        env=env, capture_output=True, text=True,
    )
    assert r.returncode == 2


def test_deterministic_byte_identical(tmp_path, canons):
    _skip_if_missing()
    new_canon, old_canon, id_map = canons
    out1 = tmp_path / "out1.json"
    out2 = tmp_path / "out2.json"
    r1 = _run(tmp_path, new_canon, old_canon, id_map, str(out1))
    assert r1.returncode == 0, r1.stderr
    r2 = _run(tmp_path, new_canon, old_canon, id_map, str(out2))
    assert r2.returncode == 0, r2.stderr
    assert out1.read_bytes() == out2.read_bytes()


def test_output_passes_schema(tmp_path, canons):
    _skip_if_missing()
    sys.path.insert(0, os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts"))
    import importlib
    envelope = importlib.import_module("_envelope")

    new_canon, old_canon, id_map = canons
    out = tmp_path / "out.json"
    r = _run(tmp_path, new_canon, old_canon, id_map, str(out))
    assert r.returncode == 0, r.stderr
    envelope.validate_file(str(out), os.path.join(_SCHEMA_DIR, "diff-report.json"))


def test_replacements_three_how_kinds(tmp_path, canons):
    _skip_if_missing()
    new_canon, old_canon, id_map = canons
    out = tmp_path / "out.json"
    r = _run(tmp_path, new_canon, old_canon, id_map, str(out))
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    hows = {rep["how"] for rep in data["payload"]["replacements"]}
    assert hows == {"content", "merged_into", "phrasing_only"}


def test_structure_diff_added_and_removed(tmp_path, canons):
    _skip_if_missing()
    new_canon, old_canon, id_map = canons
    out = tmp_path / "out.json"
    r = _run(tmp_path, new_canon, old_canon, id_map, str(out))
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    diff = data["payload"]["structure_diff"]
    added_ids = {h["id"] for h in diff["headings_added"]}
    removed_ids = {h["id"] for h in diff["headings_removed"]}
    assert "a2" in added_ids
    assert "a0" in removed_ids


def test_state_file_diff_report_sha_matches_actual(tmp_path, canons):
    _skip_if_missing()
    new_canon, old_canon, id_map = canons
    out = tmp_path / "out.json"
    r = _run(tmp_path, new_canon, old_canon, id_map, str(out))
    assert r.returncode == 0, r.stderr
    state_path = os.path.join(str(tmp_path), ".claude", "hooks", "state", "outline-gate", "session.json")
    assert os.path.isfile(state_path), "diff_report.py 應寫入狀態檔"
    state = json.loads(open(state_path, encoding="utf-8").read())
    assert state["diff_report"]["inputs_sha"]["canon"] == _sha(new_canon)
