"""unit：`scripts/cost_ledger.py`（knowledge-outline-and-intent-architecture 任務 1.3｜design 元件 1）。

驗：110 代理假 journal（步 4 answerability）不擋（exit 0, over_budget=false）；
181 代理必擋（exit 2, over_budget=true，正對照）；整案 241 代理必擋；
同輸入兩次逐位元相等；輸出通過 schema；狀態檔 cost 鍵寫入。
"""
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:1.6")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
_SCRIPT = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts", "cost_ledger.py")
_SKILL_MD = os.path.join(_REPO, ".claude", "skills", "outline-curation", "SKILL.md")
_SCHEMA_DIR = os.path.join(_REPO, ".claude", "skills", "outline-curation", "schemas")


def _skip_if_missing():
    if not os.path.isfile(_SCRIPT):
        pytest.skip(f"[env] 找不到 {_SCRIPT}——容器需掛 repo 根 .claude/，宿主直跑本檔")
    if not os.path.isfile(_SKILL_MD):
        pytest.skip(f"[env] 找不到 {_SKILL_MD}")


def _write_journal_entry(journal_dir, name, step, n_agents, usd_each=0.01):
    agents = [{"prompt_tokens": 10, "completion_tokens": 10, "usd": usd_each} for _ in range(n_agents)]
    with open(os.path.join(journal_dir, name), "w", encoding="utf-8") as f:
        json.dump({"step": step, "run_id": name, "agents": agents, "wall_s": 1.0}, f)


def _run(tmp_path, journal_dir, out):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    cmd = [sys.executable, _SCRIPT, "--journal", journal_dir, "--skill", _SKILL_MD, "--out", out]
    return subprocess.run(cmd, env=env, capture_output=True, text=True)


def test_help_runs():
    _skip_if_missing()
    r = subprocess.run([sys.executable, _SCRIPT, "--help"], capture_output=True, text=True)
    assert r.returncode == 0


def test_110_agents_answerability_not_blocked(tmp_path):
    _skip_if_missing()
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    _write_journal_entry(str(journal_dir), "a.json", "answerability", 110, usd_each=0.001)
    out = tmp_path / "cost.json"
    r = _run(tmp_path, str(journal_dir), str(out))
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["payload"]["over_budget"] is False


def test_181_agents_answerability_is_blocked(tmp_path):
    """正對照：181 > 180 上限 ⇒ 必擋（exit 2, over_budget=true）。"""
    _skip_if_missing()
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    _write_journal_entry(str(journal_dir), "a.json", "answerability", 181, usd_each=0.001)
    out = tmp_path / "cost.json"
    r = _run(tmp_path, str(journal_dir), str(out))
    assert r.returncode == 2
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["payload"]["over_budget"] is True


def test_total_241_agents_blocked(tmp_path):
    """整案上限 240；110(answerability)+6(structure)+125(answerability again, 另一輪) 需超過 240。
    這裡直接用一筆 241 的 structure 步驟外加另一 step 名稱不受單步上限管，藉此只觸發整案上限。
    """
    _skip_if_missing()
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    # 用未在 budgets 命名的步驟名，跳過單步檢查，只測整案 total 檢查
    _write_journal_entry(str(journal_dir), "misc.json", "reweigh", 241, usd_each=0.001)
    out = tmp_path / "cost.json"
    r = _run(tmp_path, str(journal_dir), str(out))
    assert r.returncode == 2
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["payload"]["over_budget"] is True
    assert data["payload"]["total"]["agents"] == 241


def test_deterministic_byte_identical(tmp_path):
    _skip_if_missing()
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    _write_journal_entry(str(journal_dir), "a.json", "answerability", 50)
    out1 = tmp_path / "out1.json"
    out2 = tmp_path / "out2.json"
    _run(tmp_path, str(journal_dir), str(out1))
    _run(tmp_path, str(journal_dir), str(out2))
    assert out1.read_bytes() == out2.read_bytes()


def test_output_passes_schema(tmp_path):
    _skip_if_missing()
    sys.path.insert(0, os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts"))
    import importlib
    envelope = importlib.import_module("_envelope")

    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    _write_journal_entry(str(journal_dir), "a.json", "answerability", 50)
    out = tmp_path / "out.json"
    _run(tmp_path, str(journal_dir), str(out))
    envelope.validate_file(str(out), os.path.join(_SCHEMA_DIR, "cost.json"))


def test_state_file_cost_written(tmp_path):
    _skip_if_missing()
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    _write_journal_entry(str(journal_dir), "a.json", "answerability", 50)
    out = tmp_path / "out.json"
    _run(tmp_path, str(journal_dir), str(out))
    state_path = os.path.join(str(tmp_path), ".claude", "hooks", "state", "outline-gate", "session.json")
    assert os.path.isfile(state_path)
    state = json.loads(open(state_path, encoding="utf-8").read())
    assert state["cost"]["over_budget"] is False


def test_empty_journal_is_zero_and_not_blocked(tmp_path):
    """正對照：空 journal ⇒ 0 代理，不應誤判超支。"""
    _skip_if_missing()
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    out = tmp_path / "out.json"
    r = _run(tmp_path, str(journal_dir), str(out))
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["payload"]["total"]["agents"] == 0
    assert data["payload"]["over_budget"] is False


def test_load_journal_filters_by_run_id_and_prefix_and_ignores_subdirs(tmp_path):
    """業主 2026-09-07 裁 (a)：預算按每次 run。`--run-id`／`--run-prefix` 只納入命中者；不給 ⇒ 全部（正對照）；
    子目錄（m-a-archive/）永遠不讀。"""
    import importlib.util, json, os
    spec = importlib.util.spec_from_file_location("cost_ledger", _SCRIPT); cl = importlib.util.module_from_spec(spec); spec.loader.exec_module(cl)
    j = tmp_path / "journal"; (j / "m-a-archive").mkdir(parents=True)
    for name, rid in (("a.json", "answerability-x-1"), ("b.json", "answerability-y-2"), ("c.json", "structure-x-1")):
        (j / name).write_text(json.dumps({"step": "answerability", "run_id": rid, "agents": [{"usd": 1.0}], "wall_s": 0}), encoding="utf-8")
    (j / "m-a-archive" / "old.json").write_text(json.dumps({"step": "answerability", "run_id": "answerability-x-0", "agents": [{"usd": 99.0}], "wall_s": 0}), encoding="utf-8")
    assert len(cl.load_journal(str(j))) == 3                                    # 正對照：不過濾＝頂層全部、子目錄不讀
    assert [e["run_id"] for e in cl.load_journal(str(j), run_ids=["answerability-y-2"])] == ["answerability-y-2"]
    assert sorted(e["run_id"] for e in cl.load_journal(str(j), run_prefixes=["answerability-x", "structure-x"])) == ["answerability-x-1", "structure-x-1"]
    assert cl.load_journal(str(j), run_ids=["nope"]) == []
