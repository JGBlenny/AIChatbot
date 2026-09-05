"""unit：agent health 的 NLI 欄位與降級告警（spec agentic-mcp-orchestration・DSP-033 F-10）。

量三件事：
1. `nli_ready` 是 `nli-model` `/health` 的**透傳**——⛔ 本端不重算、不載模型；
2. 探不到 ⇒ **紅**（⛔ 不得印成 `"pending"`：那會把「NLI 掛了」說成「還沒接線」）；
3. 近 5 分鐘降級比率：`> 2%` **連兩窗**、或**單窗 100% 且 turns ≥ 5** ⇒ 紅。

⛔ 離線：`get_runtime` 一律給假物件，沒有任何一條會連出去。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.agent import health as health_mod
from services.agent.health import (
    NLI_DEGRADED_RATIO_RED,
    NLI_SINGLE_WINDOW_MIN_TURNS,
    NLI_WINDOW_S,
    _check_nli,
    nli_degraded_stats,
    record_nli_turn,
    reset_nli_turns,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_window():
    reset_nli_turns()
    yield
    reset_nli_turns()


class _FakeNliHealth:
    def __init__(self, info=None, exc=None):
        self.info = info
        self.exc = exc
        self.calls = 0

    async def health(self):
        self.calls += 1
        if self.exc is not None:
            raise self.exc
        return self.info


def _runtime_with(client, *, tau=0.40):
    return SimpleNamespace(nli_client=client, nli_tau=tau)


# ---------------------------------------------------------------- 透傳與三態

async def test_nli_ready_is_passed_through_from_the_service():
    """r18 F-6：真模型自證（canary＋目錄指紋）在 `nli-model` 容器裡跑，
    orchestrator 只透傳結果。⛔ 本端不重跑一份——兩把尺會各自演化、對不上。"""
    client = _FakeNliHealth({"nli_ready": True, "model_sha": "a" * 64, "canary_ok": True})
    ready, sha, tau, red = await _check_nli(lambda: _runtime_with(client))
    assert (ready, sha, tau, red) == (True, "a" * 64, 0.40, False)
    assert client.calls == 1


async def test_service_says_not_ready_is_red():
    """canary 或指紋沒過 ⇒ 那台機器的 Verifier 正在跑降級尺 ⇒ agent health 紅。"""
    client = _FakeNliHealth({"nli_ready": False, "model_sha": "b" * 64, "canary_ok": False})
    ready, _sha, _tau, red = await _check_nli(lambda: _runtime_with(client))
    assert ready is False and red is True


@pytest.mark.parametrize("client", [
    _FakeNliHealth(None),                       # 探不到（client 自己回 None）
    _FakeNliHealth(exc=RuntimeError("boom")),   # 探針本身炸了
])
async def test_unreachable_is_red_not_pending(client):
    """🔴 探測失敗 ⇒ `False`＋紅。

    ⛔ 不得回 `"pending"`：「連不上」與「還沒接線」是兩件事，用同一個值表示
    會讓一台 NLI 掛掉的機器在健檢上看起來跟一台還沒部署的機器一樣正常。
    """
    ready, sha, _tau, red = await _check_nli(lambda: _runtime_with(client))
    assert ready is False and red is True
    assert sha == "pending"


@pytest.mark.parametrize("get_runtime", [
    None,                                        # 呼叫端沒交 getter
    lambda: None,                                # runtime 還沒建起來
    lambda: SimpleNamespace(),                   # runtime 沒有 nli_client 屬性
])
async def test_not_wired_yet_is_pending_and_not_red(get_runtime):
    """⚠️ 與 `rules_sha` 同一個慣例：「尚未建置」不是「建置後壞了」，⛔ 不算紅。"""
    ready, sha, tau, red = await _check_nli(get_runtime)
    assert ready == "pending" and sha == "pending" and red is False
    assert tau is None


async def test_getter_exception_does_not_crash_health():
    def _boom():
        raise RuntimeError("state not ready")

    ready, _sha, _tau, red = await _check_nli(_boom)
    assert ready == "pending" and red is False


# ---------------------------------------------------------------- 降級比率窗

def test_ratio_is_per_turn_not_per_attempt():
    for _ in range(9):
        record_nli_turn(False)
    record_nli_turn(True)
    stats = nli_degraded_stats()
    assert (stats["degraded"], stats["turns"]) == (1, 10)
    assert stats["ratio"] == pytest.approx(0.1)


def test_single_window_over_threshold_alone_is_not_red():
    """F-10：`> 2%` 要**連兩窗**才紅。

    ⚠️ 低流量時偶發一次降級不該告警——一個天天喊狼來了的警報等於沒有警報。
    """
    now = 1000.0
    for _ in range(97):
        record_nli_turn(False, now=now)
    for _ in range(3):                     # 3/100 = 3% > 2%
        record_nli_turn(True, now=now)
    stats = nli_degraded_stats(now=now)
    assert stats["ratio"] > NLI_DEGRADED_RATIO_RED
    assert stats["prev_turns"] == 0
    assert stats["red"] is False


def test_two_consecutive_windows_over_threshold_is_red():
    now = 1000.0
    prev = now - NLI_WINDOW_S - 1.0        # 落在前一個窗
    for _ in range(50):
        record_nli_turn(False, now=prev)
    for _ in range(5):
        record_nli_turn(True, now=prev)
    for _ in range(50):
        record_nli_turn(False, now=now)
    for _ in range(5):
        record_nli_turn(True, now=now)
    stats = nli_degraded_stats(now=now)
    assert stats["ratio"] > NLI_DEGRADED_RATIO_RED
    assert stats["prev_ratio"] > NLI_DEGRADED_RATIO_RED
    assert stats["red"] is True


def test_single_window_all_degraded_with_enough_turns_is_red():
    """F-10 第二條：**單窗 100% 且 turns ≥ 5** ⇒ 紅。

    ⚠️ 這條的用途是「NLI 根本沒接上」——那種情況流量再低也一定要響，
    不能等第二個窗（那是十分鐘）。
    """
    now = 2000.0
    for _ in range(NLI_SINGLE_WINDOW_MIN_TURNS):
        record_nli_turn(True, now=now)
    stats = nli_degraded_stats(now=now)
    assert stats["turns"] == NLI_SINGLE_WINDOW_MIN_TURNS
    assert stats["ratio"] == 1.0
    assert stats["red"] is True


def test_all_degraded_but_too_few_turns_is_not_red():
    """正對照：同樣 100%，只差在筆數不足 ⇒ 不紅。
    ⛔ 沒有這條，上一條可能只是在測「有降級就紅」。"""
    now = 2000.0
    for _ in range(NLI_SINGLE_WINDOW_MIN_TURNS - 1):
        record_nli_turn(True, now=now)
    assert nli_degraded_stats(now=now)["red"] is False


def test_empty_window_does_not_count_as_healthy():
    """🔴 `total == 0` 的窗**不參與判定**。

    ⚠️ 把沒有流量算成 0% 會讓「連兩窗超標」在流量斷斷續續時永遠湊不齊——
    也就是說，一個間歇性的服務故障永遠不會告警。
    """
    stats = nli_degraded_stats(now=3000.0)
    assert stats["turns"] == 0 and stats["ratio"] is None
    assert stats["red"] is False


def test_events_older_than_two_windows_are_dropped():
    now = 5000.0
    record_nli_turn(True, now=now - 2 * NLI_WINDOW_S - 1)
    for _ in range(3):
        record_nli_turn(False, now=now)
    stats = nli_degraded_stats(now=now)
    assert (stats["degraded"], stats["turns"]) == (0, 3)
    assert (stats["prev_degraded"], stats["prev_turns"]) == (0, 0)


# ---------------------------------------------------------------- compute_agent_health 接線

def _health_kwargs(**over):
    base = dict(
        registry=SimpleNamespace(),
        get_kb_pool=None,
        stage="M1",
        get_api_key_pool=None,
        get_runtime=None,
    )
    base.update(over)
    return base


async def _compute(monkeypatch, **over):
    """把 health 的其他四項一律打成綠，隔離出 NLI 這一格。"""
    monkeypatch.setattr(health_mod.mcp_facade, "union_specs", lambda r, s: [{"name": "kb.get"}])
    monkeypatch.setattr(health_mod.mcp_facade, "premise_stats", lambda: {})
    monkeypatch.setattr(health_mod.mcp_facade, "mcp_sdk_available", lambda: (True, ""))
    async def _kb_ok(_g):
        return True, "ok"
    async def _scope_ok(_g):
        return True, "ok"
    monkeypatch.setattr(health_mod, "_check_kb_reachable", _kb_ok)
    monkeypatch.setattr(health_mod, "_check_agent_scope_ready", _scope_ok)
    return await health_mod.compute_agent_health(**_health_kwargs(**over))


async def test_health_reports_the_three_nli_fields(monkeypatch):
    client = _FakeNliHealth({"nli_ready": True, "model_sha": "d" * 64, "canary_ok": True})
    out = await _compute(monkeypatch, get_runtime=lambda: _runtime_with(client))
    checks = out["checks"]
    assert checks["nli_ready"] is True
    assert checks["nli_model_sha"] == "d" * 64
    assert checks["nli_tau"] == 0.40
    assert checks["nli_degraded"]["window_s"] == NLI_WINDOW_S
    assert out["status"] == "ok"


async def test_health_is_red_when_nli_is_not_ready(monkeypatch):
    """正對照：同一組打綠的其他四項下，只有 NLI 這一格變紅 ⇒ 整體紅。
    這證明紅色確實來自 NLI，不是別的檢查順便失敗。"""
    ok_client = _FakeNliHealth({"nli_ready": True, "model_sha": "x", "canary_ok": True})
    assert (await _compute(monkeypatch, get_runtime=lambda: _runtime_with(ok_client)))["status"] == "ok"

    bad = _FakeNliHealth({"nli_ready": False, "model_sha": "x", "canary_ok": False})
    assert (await _compute(monkeypatch, get_runtime=lambda: _runtime_with(bad)))["status"] == "red"


async def test_health_is_red_when_degraded_ratio_trips(monkeypatch):
    client = _FakeNliHealth({"nli_ready": True, "model_sha": "x", "canary_ok": True})
    for _ in range(NLI_SINGLE_WINDOW_MIN_TURNS):
        record_nli_turn(True)
    out = await _compute(monkeypatch, get_runtime=lambda: _runtime_with(client))
    assert out["checks"]["nli_degraded"]["red"] is True
    assert out["status"] == "red", "NLI 服務說自己 ready，但這台機器每一回合都在降級"


async def test_health_not_wired_yet_stays_green(monkeypatch):
    """⚠️ 部署順序：本版上線而 `nli-model` 尚未起來時 health 會紅（刻意 fail-loud），
    但**還沒建 runtime** 的行程 ⛔ 不算紅——兩者是不同的狀態。"""
    out = await _compute(monkeypatch, get_runtime=None)
    assert out["checks"]["nli_ready"] == "pending"
    assert out["status"] == "ok"
