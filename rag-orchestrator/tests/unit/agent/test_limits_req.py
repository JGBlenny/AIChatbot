"""unit：上限封閉表 `services/agent/limits.py`（DSP-045）。

覆蓋（brief 驗收節逐條）：
(a) `LIMITS` 欄位與預設值封閉
(b) 設了舊 env（`RATE_PER_MIN=1` 等）不再影響任何讀取處（正對照：測試鉤子能改）
(c) registry／facade／image_fetch 三處讀到的值＝`LIMITS`
(d) 健檢 `checks.limits` 內容＝`effective()`
"""
from __future__ import annotations

import dataclasses

import pytest

from services.agent import health, image_fetch
from services.agent import limits as limits_mod
from services.agent.limits import LIMITS, AgentLimits, effective
from services.agent.tools import registry as registry_mod

pytestmark = pytest.mark.unit


# ══════════════════════════════════════════════════════════════════
# (a) 欄位與預設值封閉
# ══════════════════════════════════════════════════════════════════
def test_agent_limits_fields_closed():
    field_names = {f.name for f in dataclasses.fields(AgentLimits)}
    assert field_names == {
        "turns_per_hour",
        "tool_calls_per_minute",
        "kb_get_per_hour",
        "images_per_hour",
        "files_per_hour",
    }


def test_agent_limits_defaults():
    defaults = AgentLimits()
    assert defaults.turns_per_hour == 1200
    assert defaults.tool_calls_per_minute == 600
    assert defaults.kb_get_per_hour == 3000
    assert defaults.images_per_hour == 600
    assert defaults.files_per_hour == 100


def test_agent_limits_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        LIMITS_INSTANCE = AgentLimits()
        LIMITS_INSTANCE.turns_per_hour = 1  # type: ignore[misc]


def test_effective_matches_default_when_no_override(monkeypatch):
    monkeypatch.delenv(limits_mod.AGENT_LIMITS_TEST_OVERRIDE_ENV, raising=False)
    assert effective() == {
        "turns_per_hour": 1200,
        "tool_calls_per_minute": 600,
        "kb_get_per_hour": 3000,
        "images_per_hour": 600,
        "files_per_hour": 100,
    }


# ══════════════════════════════════════════════════════════════════
# (b) 舊 env 不再生效；測試鉤子能改（正對照）
# ══════════════════════════════════════════════════════════════════
def test_legacy_env_vars_no_longer_affect_limits(monkeypatch):
    monkeypatch.delenv(limits_mod.AGENT_LIMITS_TEST_OVERRIDE_ENV, raising=False)
    monkeypatch.setenv("RATE_PER_MIN", "1")
    monkeypatch.setenv("KB_GET_CAP", "1")
    monkeypatch.setenv("AGENT_TURN_CAP", "1")
    monkeypatch.setenv("IMAGE_COUNT_CAP_PER_HOUR", "1")
    monkeypatch.setenv("FILE_COUNT_CAP_PER_HOUR", "1")
    assert LIMITS.tool_calls_per_minute == 600
    assert LIMITS.kb_get_per_hour == 3000
    assert LIMITS.turns_per_hour == 1200
    assert LIMITS.images_per_hour == 600
    assert LIMITS.files_per_hour == 100


def test_test_hook_overrides_when_pytest_current_test_present(monkeypatch):
    """正對照：不是「任何 env 都動不了它」——測試鉤子在 pytest 行程內確實生效。"""
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "fake::test")
    monkeypatch.setenv(
        limits_mod.AGENT_LIMITS_TEST_OVERRIDE_ENV,
        '{"tool_calls_per_minute": 2, "kb_get_per_hour": 3}',
    )
    assert LIMITS.tool_calls_per_minute == 2
    assert LIMITS.kb_get_per_hour == 3
    # 未覆寫的欄位仍是預設
    assert LIMITS.turns_per_hour == 1200


def test_test_hook_ignores_unknown_fields_and_bad_json(monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "fake::test")
    monkeypatch.setenv(limits_mod.AGENT_LIMITS_TEST_OVERRIDE_ENV, "{not json")
    assert LIMITS.tool_calls_per_minute == 600

    monkeypatch.setenv(
        limits_mod.AGENT_LIMITS_TEST_OVERRIDE_ENV, '{"not_a_field": 1}'
    )
    assert LIMITS.tool_calls_per_minute == 600
    assert not hasattr(LIMITS, "not_a_field")


# ══════════════════════════════════════════════════════════════════
# (c) registry／facade／image_fetch 讀到的值＝LIMITS
# ══════════════════════════════════════════════════════════════════
def test_registry_reads_limits_directly(monkeypatch):
    monkeypatch.delenv(limits_mod.AGENT_LIMITS_TEST_OVERRIDE_ENV, raising=False)
    reg = registry_mod.ToolRegistry()
    ok = True
    now = 0.0
    for _ in range(LIMITS.tool_calls_per_minute):
        ok = reg._check_and_record_rate(("k", "v"), now) and ok
    assert ok is True
    assert reg._check_and_record_rate(("k", "v"), now) is False

    reg2 = registry_mod.ToolRegistry()
    ok2 = True
    for _ in range(LIMITS.kb_get_per_hour):
        ok2 = reg2._check_and_record_kb_get_cap(("k2", "v2"), now) and ok2
    assert ok2 is True
    assert reg2._check_and_record_kb_get_cap(("k2", "v2"), now) is False


def test_mcp_facade_agent_turn_cap_reads_limits():
    from services.agent import mcp_facade as F

    assert F.agent_turn_cap() == LIMITS.turns_per_hour


def test_image_fetch_caps_read_limits():
    assert image_fetch.image_count_cap_per_hour() == LIMITS.images_per_hour
    assert image_fetch.file_count_cap_per_hour() == LIMITS.files_per_hour


# ══════════════════════════════════════════════════════════════════
# (d) 健檢 checks.limits == effective()
# ══════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_health_checks_include_limits_effective(monkeypatch):
    monkeypatch.delenv(limits_mod.AGENT_LIMITS_TEST_OVERRIDE_ENV, raising=False)

    class _FakeRegistry:
        def union_specs_stub(self):
            return []

    def _union_specs(_registry, _stage):
        return []

    monkeypatch.setattr(health.mcp_facade, "union_specs", _union_specs)
    monkeypatch.setattr(
        health.mcp_facade, "mcp_sdk_available", lambda: (True, "ok")
    )
    monkeypatch.setattr(
        health.mcp_facade, "premise_stats", lambda: {}
    )
    monkeypatch.setattr(health, "verifier_mode", lambda: "enforce")
    monkeypatch.setattr(health, "_use_mock_jgb_api", lambda: True)

    async def _fake_scope_ready(_pool):
        return True, {}

    monkeypatch.setattr(health, "_check_agent_scope_ready", _fake_scope_ready)

    async def _fake_kb_reachable(_pool):
        return True, {}

    monkeypatch.setattr(health, "_check_kb_reachable", _fake_kb_reachable)

    result = await health.compute_agent_health(
        registry=_FakeRegistry(),
        get_kb_pool=None,
        stage="M1",
    )
    assert result["checks"]["limits"] == effective()
