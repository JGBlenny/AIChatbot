"""unit：`agent.turn` 的 `session_expired` 第六鍵與過期換列（W8 (5)／DSP-042）。

離線：記憶體版 `form_sessions`（`_FakeEngine`，**逐條對照真 SQL 的語義**）＋
假 provider。⛔ 不接觸真 DB。

守的事（Plan W8 驗收 (x)）：
- 同一個 `session_id` 隔超過 30 分鐘再進 ⇒ **先 `_close` 舊列再 `_start` 新列**，
  該把鍵下 ⛔ 不留第二列 `COLLECTING`，回應 `session_expired == true`；
- 正對照＝未過期回合 `session_expired == false`、⛔ 不 `_close`、⛔ 不 `_start`；
- 過期戳存在 state JSON（`agent_state["last_turn_at"]`），⛔ 不依賴不存在的
  `form_sessions.updated_at`（S8-7）。
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from services.agent import mcp_facade as F
from services.agent.state_store import (
    LAST_TURN_AT_KEY,
    SESSION_IDLE_TTL_S,
    NamespacedStateStore,
    is_expired,
    stamp_last_turn,
)
from services.agent.tools.registry import ToolRegistry

from tests.unit.agent.test_agent_turn_unit_req import (
    API_KEY_ID,
    SESSION,
    VENDOR_A,
    FakeProvider,
    _app,
    _deps,
    _final_response,
    _identity,
    _registry_with_agent_turn,
    _runtime,
)

pytestmark = pytest.mark.unit

_REQ = "agentic-mcp-orchestration:R3.7"

_KEY = f"mcp:{API_KEY_ID}:{VENDOR_A}:{SESSION}"


class _FakeEngine:
    """記憶體版 `form_sessions`——**逐條對照真 SQL 的語義**，⛔ 不簡化成一列。

    真表的四句 SQL（`services/conversational_engine.py`）：
      - `get_state`：`WHERE session_id=$1 AND state='COLLECTING' ORDER BY id DESC LIMIT 1`
      - `_start`：INSERT 一列 `COLLECTING`
      - `_save`：UPDATE 最新那一列 `COLLECTING`
      - `_close`：把該 `session_id` **所有** `COLLECTING` 列改成 `COMPLETED`
    「過期後留下第二列 COLLECTING」這個病灶只有在多列模型下才看得見，
    ⛔ 用 `dict[session_id] -> state` 的單列替身測等於把要抓的東西抹掉。
    """

    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.started: list[str] = []
        self.closed: list[str] = []
        self.saved: list[str] = []

    def _collecting(self, session_id):
        return [r for r in self.rows
                if r["session_id"] == session_id and r["state"] == "COLLECTING"]

    async def get_state(self, session_id):
        rows = self._collecting(session_id)
        if not rows:
            return None
        return json.loads(json.dumps(rows[-1]["collected_data"]))

    async def _start(self, session_id, user_id, vendor_id, config_key,
                     seed_topic=None, role_id=None):
        state = {"config_key": config_key, "collected_fields": {}, "asked_count": 0,
                 "session_id": session_id, "user_id": user_id,
                 "vendor_id": vendor_id, "role_id": role_id}
        self.started.append(session_id)
        self.rows.append({"session_id": session_id, "state": "COLLECTING",
                          "collected_data": json.loads(json.dumps(state))})
        return state

    async def _save(self, session_id, state):
        self.saved.append(session_id)
        rows = self._collecting(session_id)
        assert rows, "⛔ 沒有 COLLECTING 列可存——真 SQL 這時是靜默 0 列更新"
        rows[-1]["collected_data"] = json.loads(json.dumps(state))

    async def _close(self, session_id):
        self.closed.append(session_id)
        for row in self._collecting(session_id):
            row["state"] = "COMPLETED"


def _turn_deps(engine):
    runtime = _runtime(FakeProvider([_final_response(answer="先確認您的身分。")]))
    return _deps(_app(runtime=runtime, engine=engine))


async def _one_turn(engine, message="第一句"):
    deps = _turn_deps(engine)
    return await _registry_with_agent_turn(deps).call(
        _identity(), F.AGENT_TURN_NAME, {"message": message}, 30.0, stage="M1"
    )


def _shift_stamp(engine, delta_s: float) -> None:
    """把該列的過期戳往回撥 `delta_s` 秒（模擬「上一回合是那時候跑的」）。

    ⛔ 不 monkeypatch `time.time`——那會連 `stamp_last_turn` 寫進去的新值一起
    造假，測到的就不是「兩個時刻的差」了。
    """
    rows = [r for r in engine.rows
            if r["session_id"] == _KEY and r["state"] == "COLLECTING"]
    assert rows, "正對照：這一步之前必須真的有一列 COLLECTING（沒有＝上一回合沒跑）"
    agent_state = rows[-1]["collected_data"]["agent"]
    assert LAST_TURN_AT_KEY in agent_state, "⛔ 過期戳沒有落地——閘門會永遠不觸發"
    agent_state[LAST_TURN_AT_KEY] -= delta_s


# ════════════════════════════════════════════════════════════════════
# 1. state_store 的過期判定（純函式，無 I/O）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
def test_is_expired_is_thirty_minutes_and_missing_stamp_is_not_expired():
    assert SESSION_IDLE_TTL_S == 1800
    now = 1_000_000.0
    state: dict = {"agent": {}}

    # ⛔ 沒有戳＝不算過期（既有 session 列一律沒有它）
    assert is_expired(state, now) is False
    stamp_last_turn(state["agent"], now - SESSION_IDLE_TTL_S - 1)
    assert is_expired(state, now) is True                      # 剛好超過 ⇒ 過期
    stamp_last_turn(state["agent"], now - SESSION_IDLE_TTL_S)
    assert is_expired(state, now) is False                     # 正好等於 ⇒ 不過期
    stamp_last_turn(state["agent"], now - 60)
    assert is_expired(state, now) is False                     # 一分鐘前 ⇒ 不過期
    # 壞型別／時鐘回跳一律不算過期（fail-open，見 docstring）
    state["agent"][LAST_TURN_AT_KEY] = "20260908"
    assert is_expired(state, now) is False
    state["agent"][LAST_TURN_AT_KEY] = now + 10_000
    assert is_expired(state, now) is False


@pytest.mark.req(_REQ)
async def test_state_store_close_goes_through_the_engine_with_the_namespaced_key():
    """`close()` 轉呼 `engine._close`，且餵進去的是**命名空間鍵**、⛔ 不是裸值。"""
    engine = _FakeEngine()
    store = NamespacedStateStore(engine, API_KEY_ID, VENDOR_A)
    await store.close(SESSION)
    assert engine.closed == [_KEY]
    assert SESSION not in engine.closed          # 正對照：不是裸 session_id


# ════════════════════════════════════════════════════════════════════
# 2. (x) 過期回合：先 close 再 start、⛔ 不留第二列 COLLECTING
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
async def test_expired_turn_closes_old_row_starts_new_and_reports_session_expired():
    engine = _FakeEngine()

    first = await _one_turn(engine, "第一句")
    assert first.ok is True, first.error
    assert first.data["session_expired"] is False        # 正對照：第一回合不是過期
    assert engine.started == [_KEY] and engine.closed == []

    _shift_stamp(engine, SESSION_IDLE_TTL_S + 60)

    second = await _one_turn(engine, "隔了很久的第二句")
    assert second.ok is True, second.error
    assert second.data["session_expired"] is True

    # 先 close 再 start（⛔ 順序顛倒會把新列一起關掉）
    assert engine.closed == [_KEY]
    assert engine.started == [_KEY, _KEY]
    # ⛔ 該把鍵下**恰好一列** COLLECTING（沒有殘列，S8-7）
    collecting = [r for r in engine.rows
                  if r["session_id"] == _KEY and r["state"] == "COLLECTING"]
    assert len(collecting) == 1
    completed = [r for r in engine.rows
                 if r["session_id"] == _KEY and r["state"] == "COMPLETED"]
    assert len(completed) == 1                            # 舊列真的被關掉了


@pytest.mark.req(_REQ)
async def test_non_expired_turn_reuses_the_row_and_reports_false():
    """正對照組：沒超過 30 分鐘 ⇒ ⛔ 不 close、⛔ 不開新列、`session_expired` false。"""
    engine = _FakeEngine()
    await _one_turn(engine, "第一句")
    _shift_stamp(engine, 60)                              # 只隔一分鐘

    second = await _one_turn(engine, "一分鐘後的第二句")
    assert second.data["session_expired"] is False
    assert engine.closed == []
    assert engine.started == [_KEY]                       # 沒有第二次 _start
    assert len([r for r in engine.rows if r["state"] == "COLLECTING"]) == 1


@pytest.mark.req(_REQ)
async def test_expired_turn_drops_pending_confirm_with_the_old_row():
    """過期換列 ⇒ 掛在舊列上的 `pending_confirm` 讀不到了（隨舊列作廢）。"""
    engine = _FakeEngine()
    await _one_turn(engine, "第一句")
    rows = [r for r in engine.rows if r["state"] == "COLLECTING"]
    rows[-1]["collected_data"]["agent"]["pending_confirm"] = {"deadbeefdeadbeef": {"x": 1}}
    _shift_stamp(engine, SESSION_IDLE_TTL_S + 1)

    await _one_turn(engine, "隔了很久的第二句")
    live = [r for r in engine.rows
            if r["session_id"] == _KEY and r["state"] == "COLLECTING"][-1]
    assert "pending_confirm" not in live["collected_data"]["agent"]
    # 正對照：舊列上那筆確實存在過（不是因為一開始就沒寫進去才綠）
    stale = [r for r in engine.rows if r["state"] == "COMPLETED"][-1]
    assert "pending_confirm" in stale["collected_data"]["agent"]


# ════════════════════════════════════════════════════════════════════
# 3. 回應鍵序：`session_expired` 是第六鍵（DSP-042 §0b）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.req(_REQ)
def test_session_expired_is_the_sixth_key_and_defaults_to_false():
    keys = list(F.AgentTurnOutput.model_fields)
    assert keys == ["answer", "kind", "handoff", "quick_replies", "trace_id",
                    "session_expired", "outcome"]          # 第七鍵 outcome（DSP-043）
    assert keys[5] == "session_expired"
    assert F.AgentTurnOutput.model_fields["session_expired"].default is False
    dumped = F.AgentTurnOutput(answer="a", kind="answer", trace_id="t").model_dump()
    assert list(dumped) == keys and dumped["session_expired"] is False
    assert dumped["outcome"] == {"state": "answered", "expects": "text", "action": None, "ref": None}
