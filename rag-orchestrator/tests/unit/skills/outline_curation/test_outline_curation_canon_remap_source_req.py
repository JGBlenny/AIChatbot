"""unit：從既有正本重切——`canon_items.py`／`intake.py --canon`／`structure_propose.py prepare --canon`
（knowledge-outline-and-intent-architecture 任務 9.3⑤）。

驗：候選 id 形狀與 `candidate_from_kb_row` 一致（`tmp:kb:<fine.id>`）；`--exclude` 排除生效；
`--canon` 與既有來源旗標二擇一（同給／都不給 exit 2）；`structure_propose.py prepare --canon` 的
`manifest.json` 記錄排除清單與 sha。
"""
import importlib.util
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:9.3.5")]

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


def _run(args, cwd=None, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run([sys.executable, os.path.join(_SCRIPTS, args[0])] + args[1:],
                           capture_output=True, text=True, cwd=cwd or _REPO, env=e)


_CANON = """---
audience: prospect
version: 2026-09-01.0
reviewers: [owner]
language: zh-TW
budget_tokens: 8000
target_user: [prospect]
business_types: [system_provider]
---
## A 產品定位 {#A}
### 系統定位 {#prospect/A/positioning}
- sources: [kb:1]
- instance_applicability: general
金箍棒把物件、合約、收租集中管理。

### 已退役項目 {#prospect/A/retired-item}
- sources: [kb:2]
- instance_applicability: general
這條會被排除。
"""


@pytest.fixture
def canon_file(tmp_path):
    p = tmp_path / "canon.md"
    p.write_text(_CANON, encoding="utf-8")
    return str(p)


@pytest.fixture
def exclude_file(tmp_path):
    p = tmp_path / "exclude.json"
    p.write_text(json.dumps({"excluded": ["prospect/A/retired-item"], "why": "DSP-999 已退役"}, ensure_ascii=False),
                 encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# canon_items.py
# ---------------------------------------------------------------------------

def test_canon_items_candidate_id_shape_matches_kb_row_convention(canon_file):
    ci = _load("canon_items")
    audience, items, excluded, why = ci.canon_items(canon_file, None)
    assert audience == "prospect"
    ids = {it["id"] for it in items}
    assert ids == {"tmp:kb:prospect/A/positioning", "tmp:kb:prospect/A/retired-item"}
    assert excluded == frozenset()
    assert why == ""
    one = next(it for it in items if it["id"] == "tmp:kb:prospect/A/positioning")
    assert one["title"] == "系統定位"
    assert one["content"] == "金箍棒把物件、合約、收租集中管理。"


def test_canon_items_exclude_removes_items(canon_file, exclude_file):
    ci = _load("canon_items")
    audience, items, excluded, why = ci.canon_items(canon_file, exclude_file)
    assert {it["id"] for it in items} == {"tmp:kb:prospect/A/positioning"}
    assert excluded == frozenset({"prospect/A/retired-item"})
    assert why == "DSP-999 已退役"


# ---------------------------------------------------------------------------
# intake.py --canon
# ---------------------------------------------------------------------------

def test_intake_canon_mode_produces_kb_rows_from_fines(tmp_path, canon_file, exclude_file):
    out = tmp_path / "intake.json"
    r = _run(["intake.py", "--canon", canon_file, "--exclude", exclude_file, "--out", str(out),
              "--frozen-at", "2026-09-15T00:00:00Z"],
             env={"CLAUDE_PROJECT_DIR": str(tmp_path)})
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    ids = {row["id"] for row in data["payload"]["kb_rows"]}
    assert ids == {"prospect/A/positioning"}  # 已排除 retired-item
    assert data["inputs_sha"]["kb"] == data["inputs_sha"]["canon"]
    assert "exclude" in data["inputs_sha"]


def test_intake_kb_json_and_canon_mutually_exclusive(tmp_path, canon_file):
    kb = tmp_path / "kb.json"
    kb.write_text("[]", encoding="utf-8")
    out = tmp_path / "intake.json"
    r = _run(["intake.py", "--kb-json", str(kb), "--canon", canon_file, "--out", str(out),
              "--frozen-at", "2026-09-15T00:00:00Z"])
    assert r.returncode == 2
    assert "二擇一" in r.stderr


def test_intake_neither_kb_json_nor_canon_given_exits_2(tmp_path):
    out = tmp_path / "intake.json"
    r = _run(["intake.py", "--out", str(out), "--frozen-at", "2026-09-15T00:00:00Z"])
    assert r.returncode == 2
    assert "二擇一" in r.stderr


def test_intake_deterministic_in_canon_mode(tmp_path, canon_file, exclude_file):
    out1, out2 = tmp_path / "o1.json", tmp_path / "o2.json"
    for out in (out1, out2):
        r = _run(["intake.py", "--canon", canon_file, "--exclude", exclude_file, "--out", str(out),
                  "--frozen-at", "2026-09-15T00:00:00Z"], env={"CLAUDE_PROJECT_DIR": str(tmp_path)})
        assert r.returncode == 0, r.stderr
    assert out1.read_bytes() == out2.read_bytes()


# ---------------------------------------------------------------------------
# structure_propose.py prepare --canon
# ---------------------------------------------------------------------------

_COARSES = {"audience": "prospect", "coarses": [{"id": "A", "title": "產品定位"}]}


def test_structure_prepare_canon_mode_items_and_manifest(tmp_path, canon_file, exclude_file):
    coarses = tmp_path / "coarses.json"
    coarses.write_text(json.dumps(_COARSES, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "out"
    r = _run(["structure_propose.py", "prepare", "--canon", canon_file, "--exclude", exclude_file,
              "--coarses", str(coarses), "--out-dir", str(out_dir)])
    assert r.returncode == 0, r.stderr
    items = json.loads((out_dir / "items.json").read_text(encoding="utf-8"))
    assert {it["id"] for it in items} == {"tmp:kb:prospect/A/positioning"}
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["excluded"] == ["prospect/A/retired-item"]
    assert manifest["excluded_why"] == "DSP-999 已退役"
    assert manifest["inputs_sha"]["canon"] == manifest["inputs_sha"]["kb"]
    assert "exclude" in manifest["inputs_sha"]


def test_structure_prepare_kb_rows_and_canon_mutually_exclusive(tmp_path, canon_file):
    coarses = tmp_path / "coarses.json"
    coarses.write_text(json.dumps(_COARSES, ensure_ascii=False), encoding="utf-8")
    kb = tmp_path / "kb.json"
    kb.write_text(json.dumps({"rows": []}, ensure_ascii=False), encoding="utf-8")
    r = _run(["structure_propose.py", "prepare", "--kb-rows", str(kb), "--canon", canon_file,
              "--coarses", str(coarses), "--out-dir", str(tmp_path / "out")])
    assert r.returncode == 2
    assert "二擇一" in r.stderr


def test_structure_prepare_neither_kb_rows_nor_canon_exits_2(tmp_path):
    coarses = tmp_path / "coarses.json"
    coarses.write_text(json.dumps(_COARSES, ensure_ascii=False), encoding="utf-8")
    r = _run(["structure_propose.py", "prepare", "--coarses", str(coarses), "--out-dir", str(tmp_path / "out")])
    assert r.returncode == 2
    assert "二擇一" in r.stderr


def test_structure_prepare_exclude_without_canon_exits_2(tmp_path, exclude_file):
    coarses = tmp_path / "coarses.json"
    coarses.write_text(json.dumps(_COARSES, ensure_ascii=False), encoding="utf-8")
    kb = tmp_path / "kb.json"
    kb.write_text(json.dumps({"rows": []}, ensure_ascii=False), encoding="utf-8")
    r = _run(["structure_propose.py", "prepare", "--kb-rows", str(kb), "--exclude", exclude_file,
              "--coarses", str(coarses), "--out-dir", str(tmp_path / "out")])
    assert r.returncode == 2
