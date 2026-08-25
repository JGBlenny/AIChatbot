"""unit：pre-commit responsibility resolver（slice 3）。

要鎖的命題：

> **只有判 stay 的面向能 commit；期間不建立任何 session；轉交沿契約白名單走。**

對照實測病灶：現制是「檢索提名誰就建 session，判不適合再關掉重路由」，
於是同一次請求出現兩個 transient COMPLETED session，而真正的 owner 從未被提出。
"""
import json
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

    async def conversational_step_result(self, rules, system_md, state, msg, **kw):
        """任務 8.2 後 responsibility 走 `conversational_step_result`（回 StepResult）。"""
        from services.llm_answer_optimizer import StepResult
        key = rules.split("::")[1]          # rules 由下方 patch 產生，帶 facet key
        self.calls.append((key, kw.get("delegates")))
        scope, delegate = self.table[key]
        out = {"action": "ask", "next_question": "q", "scope": scope}
        if delegate:
            out["delegate_facet_key"] = delegate
        return StepResult(payload=out, scope=scope, delegate_facet_key=delegate)


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
    # 白名單確實被傳進 evaluator（模型不能自創目標）；v2 起元素為 (target, when)
    assert [t for t, _ in brain.calls[0][1]] == ["billing_anomaly"]
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
    brain.conversational_step_result = AsyncMock(return_value=None)   # 模型連可解析內容都沒給
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
    monkeypatch.setenv("PREENTRY_ROUTABILITY_FACETS", "bill_diagnosis")  # scoped rollout
    target = _cfg("contract_closeout")

    async def fake_resolve(*_a, **_k):
        from services.responsibility import EntryResolution
        return EntryResolution("contract_closeout", target,
                               [{"facet_key": "bill_diagnosis", "verdict": "switch"}], "stay")

    monkeypatch.setattr("services.responsibility.resolve_entry_candidate", fake_resolve)
    out = await chat_mod._resolve_pre_commit_candidate(MagicMock(), _cfg("bill_diagnosis"), "問句")
    assert out is target, "resolver 判給別的面向時，進場的必須是那個面向"


# ── rollout：facet-scoped gate ＋ telemetry ──────────────────────────────────
@pytest.mark.req("face-exit-before-grounding:1")
@pytest.mark.parametrize("gate,facets,expect_resolver", [
    ("false", "bill_diagnosis", False),          # 旗標關 → 不啟用
    ("true", "", False),                          # ★ fail-safe：開了但沒指定範圍 → 停用
    ("true", "other_face", False),                # seed 不在 allowlist → 不啟用
    ("true", "bill_diagnosis", True),             # 在 allowlist → 走 resolver
    ("true", " bill_diagnosis , x ", True),       # 容忍空白
])
async def test_scoped_rollout_gate(monkeypatch, gate, facets, expect_resolver):
    from routers import chat as chat_mod
    monkeypatch.setenv("PREENTRY_ROUTABILITY_GATE", gate)
    monkeypatch.setenv("PREENTRY_ROUTABILITY_FACETS", facets)
    seed = _cfg("bill_diagnosis")
    target = _cfg("contract_closeout")
    called = {"n": 0}

    async def fake_resolve(*_a, **_k):
        from services.responsibility import EntryResolution
        called["n"] += 1
        return EntryResolution("contract_closeout", target,
                               [{"facet_key": "bill_diagnosis", "verdict": "switch",
                                 "delegate_to": "contract_closeout",
                                 "reason": "responsibility_contract"}], "stay")

    monkeypatch.setattr("services.responsibility.resolve_entry_candidate", fake_resolve)
    out = await chat_mod._resolve_pre_commit_candidate(MagicMock(), seed, "問句")
    assert (called["n"] == 1) is expect_resolver
    assert out is (target if expect_resolver else seed)


@pytest.mark.req("face-exit-before-grounding:1")
def test_resolver_telemetry_shape_supports_the_rollout_rates():
    """telemetry 必須能算出：fail_open／switch_without_delegate／hop 分布／
    resolved-to-stay／fallback／LLM calls per request／latency。且**不含聊天內容**。"""
    from routers.chat import _resolver_telemetry
    from services.responsibility import EntryResolution

    chain = [{"facet_key": "bill_diagnosis", "verdict": "switch",
              "delegate_to": "billing_anomaly", "reason": "responsibility_contract"},
             {"facet_key": "billing_anomaly", "verdict": "stay",
              "delegate_to": None, "reason": "brain_unavailable_fail_open"}]
    t = _resolver_telemetry("bill_diagnosis",
                            EntryResolution("billing_anomaly", None, chain, "stay"), 42)

    assert t["seed_facet"] == "bill_diagnosis" and t["final_committed_facet"] == "billing_anomaly"
    assert t["hop_count"] == 2 and t["resolver_latency_ms"] == 42
    assert t["fail_open"] is True                      # 第二跳是 fail-open
    assert t["hops"][0]["fail_open"] is False and t["hops"][1]["fail_open"] is True
    assert t["fallback_reason"] is None                # 有 commit → 非 fallback
    assert t["resolver_model_calls"] == 2
    blob = json.dumps(t, ensure_ascii=False)
    assert "問句" not in blob and "next_question" not in blob, "telemetry 不得含聊天內容"


@pytest.mark.req("face-exit-before-grounding:1")
def test_telemetry_records_fallback_reason_when_nothing_committed():
    from routers.chat import _resolver_telemetry
    from services.responsibility import EntryResolution

    chain = [{"facet_key": "a", "verdict": "switch", "delegate_to": None,
              "reason": "responsibility_contract"}]
    t = _resolver_telemetry("a", EntryResolution(None, None, chain, "switch_without_delegate"), 7)
    assert t["final_committed_facet"] is None
    assert t["fallback_reason"] == "switch_without_delegate"
