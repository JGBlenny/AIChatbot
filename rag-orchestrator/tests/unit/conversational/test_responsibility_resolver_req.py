"""unit：pre-commit responsibility resolver（slice 3）。

要鎖的命題：

> **只有判 stay 的面向能 commit；期間不建立任何 session；轉交沿契約白名單走。**

對照實測病灶：現制是「檢索提名誰就建 session，判不適合再關掉重路由」，
於是同一次請求出現兩個 transient COMPLETED session，而真正的 owner 從未被提出。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.conversational_config import ConversationalConfig
from services.responsibility import (
    MAX_DELEGATION_HOPS,
    evaluate_responsibility,
    resolve_entry_candidate,
)

pytestmark = pytest.mark.unit


def _cfg(key, delegates=(), enabled=True):
    return ConversationalConfig(
        key=key, persona_role=f"pm_{key}", enabled=enabled,
        topic_scope={"mode": "category", "category": f"cat_{key}"},
        responsibility={"delegates": [{"target": t} for t in delegates]})


class _Brain:
    """腳本化 responsibility evaluator：facet_key → (scope, delegate)。"""

    def __init__(self, table):
        self.table = table
        self.calls = []

    async def conversational_step(self, rules, system_md, state, msg, **kw):
        key = rules.split("::")[1]          # rules 由下方 patch 產生，帶 facet key
        self.calls.append((key, kw.get("delegates")))
        scope, delegate = self.table[key]
        out = {"action": "ask", "next_question": "q", "scope": scope}
        if delegate:
            out["delegate_facet_key"] = delegate
        return out


def _patched(registry, brain):
    async def fake_rules(_pool, role):
        return f"RULES::{role.replace('pm_', '')}"

    async def fake_ctx(_pool, key=None):
        return f"CTX::{key}"

    async def lookup(_pool, key):
        return registry.get(key)

    return (patch("services.conversational_rules.load_rules", new=fake_rules),
            patch("services.system_context.get_system_context", new=fake_ctx),
            lookup)


async def _resolve(registry, brain, seed):
    r_patch, c_patch, lookup = _patched(registry, brain)
    with r_patch, c_patch:
        return await resolve_entry_candidate(MagicMock(), registry[seed], "問句",
                                             config_lookup=lookup, optimizer=brain)


# ── 主線：實測案例的 delegation chain ────────────────────────────────────────
@pytest.mark.req("face-exit-before-grounding:1")
async def test_delegation_chain_commits_only_the_staying_face():
    """diag-01 形狀：bill_diagnosis → billing_anomaly → contract_closeout → STAY。"""
    registry = {
        "bill_diagnosis": _cfg("bill_diagnosis", ["billing_anomaly"]),
        "billing_anomaly": _cfg("billing_anomaly", ["contract_closeout"]),
        "contract_closeout": _cfg("contract_closeout"),
    }
    brain = _Brain({"bill_diagnosis": ("switch", "billing_anomaly"),
                    "billing_anomaly": ("switch", "contract_closeout"),
                    "contract_closeout": ("stay", None)})
    res = await _resolve(registry, brain, "bill_diagnosis")

    assert res.committed_key == "contract_closeout" and res.stop_reason == "stay"
    assert [h["facet_key"] for h in res.chain] == \
        ["bill_diagnosis", "billing_anomaly", "contract_closeout"]
    # 白名單確實被傳進 evaluator（模型不能自創目標）
    assert brain.calls[0][1] == ["billing_anomaly"]
    assert brain.calls[2][1] is None            # 末端無 delegates → 不注入


@pytest.mark.req("face-exit-before-grounding:1")
async def test_seed_stays_commits_immediately_without_extra_calls():
    registry = {"bill_diagnosis": _cfg("bill_diagnosis", ["billing_anomaly"])}
    brain = _Brain({"bill_diagnosis": ("stay", None)})
    res = await _resolve(registry, brain, "bill_diagnosis")
    assert res.committed_key == "bill_diagnosis" and len(brain.calls) == 1


# ── 決定性護欄 ───────────────────────────────────────────────────────────────
@pytest.mark.req("face-exit-before-grounding:1")
async def test_delegation_cycle_stops_deterministically():
    """A → B → A：不得無限轉交。"""
    registry = {"a": _cfg("a", ["b"]), "b": _cfg("b", ["a"])}
    brain = _Brain({"a": ("switch", "b"), "b": ("switch", "a")})
    res = await _resolve(registry, brain, "a")
    assert res.committed_key is None and res.stop_reason == "delegation_cycle"


@pytest.mark.req("face-exit-before-grounding:1")
async def test_switch_without_delegate_falls_back():
    registry = {"a": _cfg("a")}
    brain = _Brain({"a": ("switch", None)})
    res = await _resolve(registry, brain, "a")
    assert res.committed_key is None and res.stop_reason == "switch_without_delegate"


@pytest.mark.req("face-exit-before-grounding:1")
@pytest.mark.parametrize("registry_extra,expected", [
    ({}, "unknown_or_disabled_delegate"),                                   # 白名單指向不存在
    ({"b": _cfg("b", enabled=False)}, "unknown_or_disabled_delegate"),      # 指向停用面向
])
async def test_invalid_or_disabled_delegate_fails_closed(registry_extra, expected):
    """設定錯誤不得靠硬進場藏起來。"""
    registry = {"a": _cfg("a", ["b"]), **registry_extra}
    brain = _Brain({"a": ("switch", "b"), "b": ("stay", None)})
    res = await _resolve(registry, brain, "a")
    assert res.committed_key is None and res.stop_reason == expected


@pytest.mark.req("face-exit-before-grounding:1")
async def test_max_hops_is_bounded():
    n = MAX_DELEGATION_HOPS + 2
    registry = {f"f{i}": _cfg(f"f{i}", [f"f{i+1}"]) for i in range(n)}
    registry[f"f{n-1}"] = _cfg(f"f{n-1}")
    brain = _Brain({f"f{i}": ("switch", f"f{i+1}") for i in range(n - 1)}
                   | {f"f{n-1}": ("stay", None)})
    res = await _resolve(registry, brain, "f0")
    assert res.committed_key is None and res.stop_reason == "max_hops_exceeded"
    assert len(brain.calls) <= MAX_DELEGATION_HOPS + 1


# ── fail-open：新機制故障不得擋掉原本會成立的進場 ─────────────────────────────
@pytest.mark.req("face-exit-before-grounding:1")
async def test_missing_rules_fails_open_to_stay():
    with patch("services.conversational_rules.load_rules", new=AsyncMock(return_value=None)):
        d = await evaluate_responsibility(MagicMock(), _cfg("a"), "問句", optimizer=MagicMock())
    assert d.stay and d.reason == "rules_unavailable_fail_open"


@pytest.mark.req("face-exit-before-grounding:1")
async def test_brain_failure_fails_open_to_stay():
    brain = MagicMock()
    brain.conversational_step = AsyncMock(return_value=None)
    with patch("services.conversational_rules.load_rules", new=AsyncMock(return_value="R")), \
         patch("services.system_context.get_system_context", new=AsyncMock(return_value="C")):
        d = await evaluate_responsibility(MagicMock(), _cfg("a"), "問句", optimizer=brain)
    assert d.stay and d.reason == "brain_unavailable_fail_open"


# ── chat.py 接線：預設不改變行為 ─────────────────────────────────────────────
@pytest.mark.req("face-exit-before-grounding:1")
async def test_chat_wiring_is_a_noop_while_gate_is_off(monkeypatch):
    from routers import chat as chat_mod
    monkeypatch.delenv("PREENTRY_ROUTABILITY_GATE", raising=False)
    cfg = _cfg("bill_diagnosis")
    assert await chat_mod._resolve_pre_commit_candidate(MagicMock(), cfg, "問句") is cfg


@pytest.mark.req("face-exit-before-grounding:1")
async def test_chat_wiring_returns_delegated_config_when_gate_on(monkeypatch):
    from routers import chat as chat_mod
    monkeypatch.setenv("PREENTRY_ROUTABILITY_GATE", "true")
    target = _cfg("contract_closeout")

    async def fake_resolve(*_a, **_k):
        from services.responsibility import EntryResolution
        return EntryResolution("contract_closeout", target,
                               [{"facet_key": "bill_diagnosis", "verdict": "switch"}], "stay")

    monkeypatch.setattr("services.responsibility.resolve_entry_candidate", fake_resolve)
    out = await chat_mod._resolve_pre_commit_candidate(MagicMock(), _cfg("bill_diagnosis"), "問句")
    assert out is target, "resolver 判給別的面向時，進場的必須是那個面向"
