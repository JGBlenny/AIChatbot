"""unit：`_envelope.py` 的 StepEnvelope 組裝與最小 schema 校驗
（knowledge-outline-and-intent-architecture 任務 1.3｜design 元件 1）。

驗兩件事：make_envelope 產出的外殼形狀正確；validate() 對「缺 inputs_sha」
必紅（正對照——證明校驗真的在檢查，不是恆真放行）。
"""
import importlib.util
import os

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:1.6")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
_SCRIPTS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts")
_SCHEMAS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "schemas")


def _load(name):
    if not os.path.isdir(_SCRIPTS):
        pytest.skip(f"[env] 找不到 {_SCRIPTS}——容器需掛 repo 根 .claude/，宿主直跑本檔")
    path = os.path.join(_SCRIPTS, f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_make_envelope_shape():
    env = _load("_envelope")
    e = env.make_envelope(
        step="intake",
        skill_version="0.1.0",
        inputs_sha={"kb": "abc"},
        deterministic=True,
        payload={"x": 1},
    )
    assert e["step"] == "intake"
    assert e["deterministic"] is True
    assert e["payload"] == {"x": 1}
    assert e["raw_outputs_path"] is None
    assert set(e["cost"].keys()) == {"agents", "prompt_tokens", "completion_tokens", "usd", "wall_s"}


def test_make_envelope_rejects_unknown_step():
    env = _load("_envelope")
    with pytest.raises(ValueError):
        env.make_envelope(step="bogus", skill_version="0.1.0", inputs_sha={}, deterministic=True, payload={})


def test_validate_cost_schema_missing_inputs_sha_is_red():
    """正對照：故意缺 inputs_sha ⇒ 必須被 validate() 擋下。"""
    env = _load("_envelope")
    schema = env.load_schema(os.path.join(_SCHEMAS, "cost.json"))
    instance = {
        "step": "diff",
        "skill_version": "0.1.0",
        # inputs_sha 缺
        "deterministic": True,
        "raw_outputs_path": None,
        "cost": {"agents": 0, "prompt_tokens": 0, "completion_tokens": 0, "usd": 0.0, "wall_s": 0.0},
        "payload": {"by_step": {}, "total": {}, "over_budget": False},
    }
    with pytest.raises(env.SchemaError):
        env.validate(instance, schema)


def test_validate_cost_schema_valid_instance_passes():
    env = _load("_envelope")
    schema = env.load_schema(os.path.join(_SCHEMAS, "cost.json"))
    instance = {
        "step": "diff",
        "skill_version": "0.1.0",
        "inputs_sha": {"skill": "abc"},
        "deterministic": True,
        "raw_outputs_path": None,
        "cost": {"agents": 0, "prompt_tokens": 0, "completion_tokens": 0, "usd": 0.0, "wall_s": 0.0},
        "payload": {"by_step": {}, "total": {}, "over_budget": False},
    }
    env.validate(instance, schema)  # 不得 raise


def test_update_state_merges_not_clobbers(tmp_path):
    env = _load("_envelope")
    repo_root = str(tmp_path)
    os.makedirs(os.path.join(repo_root, ".claude", "hooks", "state", "outline-gate"), exist_ok=True)
    env.update_state(repo_root, {"diff_report": {"path": "a"}})
    state = env.update_state(repo_root, {"cost": {"path": "b"}})
    assert state["diff_report"] == {"path": "a"}
    assert state["cost"] == {"path": "b"}
