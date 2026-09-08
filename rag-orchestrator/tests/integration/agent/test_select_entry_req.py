"""integration：清單點選 `select:<type>:<id>` 對真 `form_sessions` 的副作用（W8 (1)）。

真 DB：`write_slot` 那句 `jsonb_set(...)` 是這一段唯一沒有純 Python 對應物的東西——
mock pool 只證明「我們傳了這些參數」，證明不了 Postgres 收得下、路徑建得對。
故此處真跑一次來回。無法連 DB → skip（非 fail）。

⚠️ **只有 DB 是真的**：`JGBSystemAPI` 一律是假身（⛔ 不打任何外部 API）；
   Verifier 是真的 `OutputVerifier`（(iii) 的出口複查要它那把尺）。

守的事：
- 有 COLLECTING 列 ⇒ 槽位 `<type>_ref` 真的落進 `collected_data.slots`，
  且 ⛔ 不蓋掉既有鍵；trace `slot_written=True`。
- 沒有 COLLECTING 列（正對照組）⇒ **仍回 facts**、trace `slot_written=False`、
  ⛔ 不建列。
- dialog 落地的是程式摘要，facts 原文 ⛔ 不進 `collected_data`（S8-3）。
"""
import json
import os
import uuid

import pytest

from services.agent.budget import Budget
from services.agent.identity import Identity
from services.agent.mcp_facade import JGB2_EXTRA_PROPERTIES, _as_tool_result, _jgb2_spec
from services.agent.output_schema import VerifierRules
from services.agent.runtime import SELECT_DIALOG_SUMMARY, SELECT_NOT_FOUND_TEXT, AgentRuntime
from services.agent.tools import jgb2
from services.agent.tools.registry import ToolRegistry
from services.agent.tools.session import read_slots
from services.agent.verifier import OutputVerifier
from services.jgb.bills import BILL_FACE_BUILDERS, build_bill_anomaly_facts

pytestmark = pytest.mark.integration

_REQ = "agentic-mcp-orchestration:R10-c"

#: 測試列一律用這個前綴（tasks.md 鐵律），清理靠它。
_SESSION_PREFIX = "backtest_session_agent_w8_"
_CONVERSATIONAL_FORM_ID = "conversational"

_BILL_ROW = {
    "id": 900001,
    "title": "2026 年 8 月租金",
    "status": 1,
    "date_expire": 20260815,
    "amount": 18000,
}


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


def _session_id() -> str:
    return _SESSION_PREFIX + uuid.uuid4().hex[:12]


@pytest.fixture
async def pool():
    import asyncpg
    try:
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    except Exception as e:
        pytest.skip(f"無法連 DB：{e}")
        return
    try:
        yield p
    finally:
        await p.execute(
            "DELETE FROM form_sessions WHERE session_id LIKE $1", _SESSION_PREFIX + "%"
        )
        await p.close()


class _FakeApi:
    """假 `JGBSystemAPI`——⛔ 不打任何外部 API。"""

    def __init__(self):
        self.calls: list[str] = []

    async def get_bills(self, **kw):
        self.calls.append("get_bills")
        ref = kw.get("bill_ref")
        rows = [_BILL_ROW] if ref and str(ref) == str(_BILL_ROW["id"]) else []
        return {"success": True, "data": rows}


@pytest.fixture
def fake_api(monkeypatch):
    api = _FakeApi()
    monkeypatch.setattr(jgb2, "_api_singleton", api)
    return api


def _identity(session_id: str) -> Identity:
    return Identity(
        vendor_id=1, target_user="property_manager", mode="b2b",
        role_id="20151", user_id="1", session_id=session_id, api_key_id=1, entry="mcp",
    )


def _registry() -> ToolRegistry:
    reg = ToolRegistry()

    async def _query(identity, args):
        return _as_tool_result(await jgb2.query_bills(identity, args))

    reg.register(
        _jgb2_spec("bills", sorted(BILL_FACE_BUILDERS.keys()),
                   extra_properties=JGB2_EXTRA_PROPERTIES.get("bills")),
        _query,
    )
    return reg


class _NoProvider:
    """模型 ⛔ 不該被叫到——被叫到就是紅。"""

    class _C:
        async def create(self, **kwargs):
            raise AssertionError("清單點選回合 ⛔ 不得呼叫模型")

    def __init__(self):
        from types import SimpleNamespace
        self.async_client = SimpleNamespace(
            chat=SimpleNamespace(completions=self._C())
        )


class _Assembler:
    def build_messages(self, identity, outline, slots, dialog, tool_specs, nonce):
        return []


def _runtime(pool):
    rules = VerifierRules(
        version="test", sha256="0" * 64, sensitive_patterns=[], negation_terms=[],
        forbid_terms=[], allowed_routes=[], assertion_terms=[],
    )
    return AgentRuntime(
        _NoProvider(), _registry(), OutputVerifier(rules), _Assembler(), Budget(),
        stage="M1", db_pool=pool,
    )


async def _insert_collecting(pool, session_id: str) -> None:
    await pool.execute(
        "INSERT INTO form_sessions (session_id, user_id, vendor_id, form_id, state, "
        "current_field_index, collected_data) VALUES ($1,$2,$3,$4,'COLLECTING',0,$5::jsonb)",
        session_id, "1", 1, _CONVERSATIONAL_FORM_ID,
        '{"config_key": "test_cfg", "collected_fields": {"identity": "pm"}}',
    )


@pytest.mark.req(_REQ)
async def test_select_writes_the_ref_slot_into_real_jsonb(pool, fake_api):
    """命中 ⇒ `bill_ref` 真的落進 `collected_data.slots`，⛔ 不蓋掉既有鍵。"""
    session_id = _session_id()
    await _insert_collecting(pool, session_id)

    result = await _runtime(pool).run_turn(
        _identity(session_id), f"select:bill:{_BILL_ROW['id']}", {}
    )

    assert result.kind == "answer"
    assert result.answer == build_bill_anomaly_facts(_BILL_ROW, "")
    assert result.trace.slot_written is True
    assert result.trace.select_type == "bill" and result.trace.has_ref is True
    assert result.trace.llm_calls == 0

    slots = await read_slots(pool, session_id)
    assert slots["bill_ref"] == {
        "value": str(_BILL_ROW["id"]), "source": "tool", "confirmed": False
    }
    # 正對照組：既有鍵原封不動（證明沒有整包覆蓋 collected_data）
    row = await pool.fetchrow(
        "SELECT collected_data FROM form_sessions WHERE session_id=$1", session_id
    )
    collected = row["collected_data"]
    collected = json.loads(collected) if isinstance(collected, str) else collected
    assert collected["config_key"] == "test_cfg"
    assert collected["collected_fields"] == {"identity": "pm"}


@pytest.mark.req(_REQ)
async def test_select_without_collecting_row_still_answers_and_creates_nothing(pool, fake_api):
    """正對照組：沒有 COLLECTING 列 ⇒ 仍回 facts、`slot_written=False`、⛔ 不建列。"""
    session_id = _session_id()     # 刻意不插 form_sessions 列

    result = await _runtime(pool).run_turn(
        _identity(session_id), f"select:bill:{_BILL_ROW['id']}", {}
    )

    assert result.answer == build_bill_anomaly_facts(_BILL_ROW, "")
    assert result.trace.slot_written is False
    assert await read_slots(pool, session_id) == {}
    count = await pool.fetchval(
        "SELECT count(*) FROM form_sessions WHERE session_id=$1", session_id
    )
    assert count == 0              # ⛔ 沒有偷偷建列


@pytest.mark.req(_REQ)
async def test_missing_row_gives_the_fixed_sentence_and_writes_no_slot(pool, fake_api):
    """查無 ⇒ 固定句、⛔ 不寫槽位。

    正對照組：同一支假 API、換成存在的 id 就寫得進（上一個測試已證）。
    """
    session_id = _session_id()
    await _insert_collecting(pool, session_id)

    result = await _runtime(pool).run_turn(_identity(session_id), "select:bill:999999", {})

    assert result.answer == SELECT_NOT_FOUND_TEXT
    assert result.trace.slot_written is None      # 根本沒走到寫槽位那一步
    assert await read_slots(pool, session_id) == {}


@pytest.mark.req(_REQ)
async def test_only_the_program_summary_reaches_the_persisted_dialog(pool, fake_api):
    """S8-3：facts 原文 ⛔ 不以 assistant 身分進 dialog、⛔ 不落 `collected_data`。"""
    session_id = _session_id()
    await _insert_collecting(pool, session_id)

    state: dict = {}
    result = await _runtime(pool).run_turn(
        _identity(session_id), f"select:bill:{_BILL_ROW['id']}", state
    )
    # 模擬 `agent.turn` 的存回（本檔不接門面，只驗落地內容）
    await pool.execute(
        "UPDATE form_sessions SET collected_data=$2::jsonb WHERE session_id=$1",
        session_id, json.dumps(state, ensure_ascii=False),
    )

    row = await pool.fetchrow(
        "SELECT collected_data FROM form_sessions WHERE session_id=$1", session_id
    )
    collected = row["collected_data"]
    collected = json.loads(collected) if isinstance(collected, str) else collected
    last = collected["agent"]["dialog"][-1]
    assert last["role"] == "assistant"
    assert last["content"] == SELECT_DIALOG_SUMMARY.format(
        select_type="bill", ref=str(_BILL_ROW["id"])
    )
    serialized = json.dumps(collected, ensure_ascii=False)
    for line in [l for l in result.answer.splitlines() if l.strip()]:
        assert line not in serialized
    # 正對照：facts 真的有內容（不是因為空字串才綠）
    assert len([l for l in result.answer.splitlines() if l.strip()]) >= 1
