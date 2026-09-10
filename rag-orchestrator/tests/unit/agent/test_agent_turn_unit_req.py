"""unit：`agent.turn` 整回合工具（spec agentic-mcp-orchestration 任務 2.6｜
R1.1, R1.6, R2.4, R3.6, R3.7, R9.3, R10.2）。

全部離線：假 provider（腳本化）、假引擎（記憶體版 `form_sessions`）、假 app、
可注入時鐘——⛔ 不呼叫真 OpenAI、不接觸真 DB。

覆蓋（任務 brief「測試：unit」節逐條）：
1. `agent.turn` 與直接 `run_turn` 對同一訊息產出同一 `TurnResult`
2. 模型在回合內送 tool_call `agent.turn` ⇒ `NO_MATCH` ＋ `violations` 記到（無遞迴）
3. `specs_for(for_model=True)`／`specs_for(readonly_view=True)` 皆不含
4. `AGENT_TURN_ENABLED=false` ⇒ 不註冊（正對照：true ⇒ 註冊）
5. 命名空間鍵形狀 `mcp:{api_key_id}:{vendor_id}:{session_id}`；跨業者互看不到
6. 逾時 ⇒ 不 save
7. 每小時上限超過 ⇒ `RATE_LIMITED`（走真的 `_invoke`）
8. `handoff_cache` 第 51 筆擠掉第 1 筆
9. trace 無 `args_hash`
10. `term_id` 匹配 `^rule#\\d+$`
"""
from __future__ import annotations

import asyncio
import json
import re
from types import SimpleNamespace

import pytest

from services.agent import mcp_facade as F
from services.agent.budget import Budget
from services.agent.identity import Identity
from services.agent.limits import AGENT_LIMITS_TEST_OVERRIDE_ENV
from services.agent.output_schema import (
    AgentOutput,
    TERM_ID_PATTERN,
    VerifierRules,
    VerifierVerdict,
)
from services.agent.runtime import HANDOFF_CACHE_MAX, AgentRuntime, ToolCallRecord
from services.agent.state_store import NamespacedStateStore
from services.agent.tools.registry import ToolRegistry, ToolResult
from services.agent.verifier import OutputVerifier

pytestmark = pytest.mark.unit


def _set_turns_per_hour(monkeypatch, value: int) -> None:
    """DSP-045：上限不再讀 `AGENT_TURN_CAP` env——改用 limits.py 測試鉤子。"""
    monkeypatch.setenv(
        AGENT_LIMITS_TEST_OVERRIDE_ENV, json.dumps({"turns_per_hour": value})
    )


_SPEC = "agentic-mcp-orchestration:2.6"

API_KEY_ID = 7
VENDOR_A = 1
VENDOR_B = 2
SESSION = "backtest_session_agent_turn_1"


# ═══════════════════════════════════════════════════════════════════
# 假件
# ═══════════════════════════════════════════════════════════════════
def _fake_message(*, content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _fake_tool_call(name: str, args: dict, call_id: str = "call_1"):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(args, ensure_ascii=False)),
    )


def _fake_response(message, *, prompt_tokens=11, completion_tokens=5):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message)],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


def _final_response(*, kind="answer", answer="答案內容", fact_class="feature",
                    handoff_reason=None):
    # DSP-028：逐句一筆；整段當一筆 greeting（假 Verifier 路徑只需形狀正確）
    payload = {
        "kind": kind,
        "sentences": [] if not answer else [{"text": answer, "kind": "greeting", "refs": []}],
        "fact_class": fact_class, "handoff_reason": handoff_reason,
    }
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


class FakeProvider:
    """`provider.async_client.chat.completions.create(**kwargs)` 的最小替身。"""

    def __init__(self, script):
        self.script = list(script)
        self.calls: list[dict] = []
        outer = self

        class _Completions:
            async def create(self, **kwargs):
                outer.calls.append(kwargs)
                assert outer.script, "假 provider 腳本已耗盡——測試少寫了一步"
                step = outer.script.pop(0)
                return step(kwargs) if callable(step) else step

        self.async_client = SimpleNamespace(
            chat=SimpleNamespace(completions=_Completions())
        )


class FakeVerifier:
    def __init__(self, results=None, *, rules_sha="fake-rules-sha"):
        self._results = list(results) if results is not None else []
        self.rules_sha = rules_sha

    def verify(self, out, tool_results, user_message, handoff, *, resolved,
               resolve_errors, audience, document_turn):
        # DSP-029 F-A：替身也要收 `resolved`／`resolve_errors`（必填關鍵字）——
        # 停在舊簽名的話 Runtime 換簽名時會靜靜地少驗一層。
        # W9 U2／U3：`audience` 同樣是**必填關鍵字**（⛔ 不寫成有預設值）：
        # Runtime 忘了傳的話這裡要當場炸，而不是讓 fail-closed 的那條路靜靜地
        # 變成「總是照擋」（症狀是 pm 金額突然又被擋，而沒人知道為什麼）。
        # 第六批（單元 B 接 E）：`document_turn` 同一條紀律。
        self.last_audience = audience
        self.last_document_turn = document_turn
        if not self._results:
            return VerifierVerdict(ok=True)
        return self._results.pop(0)


class FakeAssembler:
    def build_messages(self, identity, outline, slots, dialog, tool_specs, nonce):
        # 大綱有沒有被塞進來，這裡看得見（測試 5／outline 進出場用）。
        self.last_outline = outline
        return [{"role": "system", "content": "persona"}]


class FakeEngine:
    """記憶體版 `form_sessions`：同一把鍵才讀得到，且**存取一律經 json 往返**。

    json 往返不是裝飾——真表是 `jsonb`，任何不可序列化的東西（例如行程級的
    大綱物件）被存進 state 就會在這裡當場炸，這正是測試 5 要抓的事。
    """

    def __init__(self) -> None:
        self.rows: dict = {}
        self.started: list = []
        self.saved: list = []

    async def get_state(self, session_id):
        row = self.rows.get(session_id)
        return json.loads(json.dumps(row)) if row is not None else None

    async def _start(self, session_id, user_id, vendor_id, config_key,
                     seed_topic=None, role_id=None):
        state = {"config_key": config_key, "collected_fields": {}, "asked_count": 0,
                 "session_id": session_id, "user_id": user_id,
                 "vendor_id": vendor_id, "role_id": role_id}
        self.started.append(session_id)
        self.rows[session_id] = json.loads(json.dumps(state))
        return state

    async def _save(self, session_id, state):
        self.saved.append(session_id)
        self.rows[session_id] = json.loads(json.dumps(state))


def _identity(*, vendor_id=VENDOR_A, session_id=SESSION, api_key_id=API_KEY_ID,
              target_user="prospect", mode="b2c", **extra) -> Identity:
    return Identity(vendor_id=vendor_id, target_user=target_user, mode=mode,
                    session_id=session_id, api_key_id=api_key_id, **extra)


def _runtime(provider, *, registry=None, verifier=None, budget=None, assembler=None):
    return AgentRuntime(
        provider,
        registry if registry is not None else ToolRegistry(),
        verifier or FakeVerifier(),
        assembler or FakeAssembler(),
        budget or Budget(),
        stage="M1",
    )


def _app(*, runtime=None, engine=None, outline=None, resolver=None):
    state = SimpleNamespace()
    if runtime is not None:
        state.agent_runtime = runtime
    if engine is not None:
        state.conversational_engine = engine
    if outline is not None:
        state.agent_outline = outline
    if resolver is not None:
        state.outline_resolver = resolver
    return SimpleNamespace(state=state)


def _deps(app, *, stage="M1"):
    return F.FacadeDeps(
        get_db_pool=lambda: None,
        get_kb_pool=lambda: None,
        get_app=lambda: app,
        get_outline_resolver=lambda: getattr(app.state, "outline_resolver", None),
        stage=stage,
    )


def _registry_with_agent_turn(deps) -> ToolRegistry:
    """只註冊 `agent.turn` 的乾淨 registry（⛔ 不連帶拉起 kb／jgb2 的接線）。"""
    reg = ToolRegistry()
    reg.register(F.AGENT_TURN_SPEC, F._make_agent_turn(deps))
    return reg


async def _call_agent_turn(registry, identity, message, *, stage="M1", timeout_s=30.0):
    """⚠️ 一律經 `registry.call(for_model=False)`——那是門面走的同一條路
    （身分鍵剝除／可見性／速率／schema 驗證），⛔ 不直接呼叫 ToolFn。"""
    return await registry.call(
        identity, F.AGENT_TURN_NAME, {"message": message}, timeout_s, stage=stage
    )


# ═══════════════════════════════════════════════════════════════════
# 1. `agent.turn` 與直接 `run_turn` 同一個 TurnResult
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_agent_turn_matches_direct_run_turn():
    """同一則訊息、同一份腳本 ⇒ 對外可見的四個欄位逐一相同。

    `trace_id` 是每回合現產的 uuid，本來就不會相等 ⇒ 只斷言它是非空字串，
    ⛔ 不假裝它該一樣。
    """
    message = "我想了解合約怎麼建立"

    direct_runtime = _runtime(FakeProvider([_final_response(answer="先確認您的身分。")]))
    direct = await direct_runtime.run_turn(_identity(), message, {})

    engine = FakeEngine()
    runtime = _runtime(FakeProvider([_final_response(answer="先確認您的身分。")]))
    deps = _deps(_app(runtime=runtime, engine=engine))
    result = await _call_agent_turn(_registry_with_agent_turn(deps), _identity(), message)

    assert result.ok is True, result.error
    assert result.data["answer"] == direct.answer
    assert result.data["kind"] == direct.kind
    assert result.data["handoff"] == direct.handoff
    assert result.data["quick_replies"] == list(direct.quick_replies)
    assert isinstance(result.data["trace_id"], str) and result.data["trace_id"]

    # ⛔ 回傳形狀＝R3.7 的五個固定鍵＋依落地順序加的選填鍵（DSP-042）——
    #    不多不少（無引用、無被拒文字）。`session_expired` 是第六鍵。
    assert set(result.data) == {
        "answer", "kind", "handoff", "quick_replies", "trace_id", "session_expired", "outcome",
    }
    # 非過期回合：其餘欄位與直呼 `run_turn` 逐值相同，多出來的那一鍵為 false
    assert result.data["session_expired"] is False
    # DSP-043：一般回答的 outcome 由 kind／quick_replies 導出
    assert result.data["outcome"]["state"] in ("answered", "clarifying", "handoff")
    assert result.data["outcome"]["expects"] in ("text", "choice", "button", "none")


# ═══════════════════════════════════════════════════════════════════
# 2. 模型在回合內送 tool_call agent.turn ⇒ NO_MATCH（無遞迴）
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_model_calling_agent_turn_inside_a_turn_is_no_match():
    engine = FakeEngine()
    provider = FakeProvider([
        _fake_response(_fake_message(
            tool_calls=[_fake_tool_call(F.AGENT_TURN_NAME, {"message": "遞迴看看"})])),
        _final_response(answer="不好意思，這題我查不到。"),
    ])
    runtime = _runtime(provider)
    deps = _deps(_app(runtime=runtime, engine=engine))
    registry = _registry_with_agent_turn(deps)
    runtime.registry = registry

    result = await runtime.run_turn(_identity(), "測遞迴", {})

    assert result.kind == "answer"
    # Runtime 端記到「模型叫了不在可見清單裡的名字」
    assert f"FORBIDDEN:{F.AGENT_TURN_NAME}" in result.trace.violations
    # registry 端也記到同一件事，且回的是 NO_MATCH
    assert any(v["name"] == F.AGENT_TURN_NAME and v["note"] == "FORBIDDEN"
               for v in registry.last_violations())
    assert result.trace.tool_calls[0].status == "error"
    # ⛔ 無遞迴：ToolFn 一次都沒被執行到（沒有任何 session 被建起來）
    assert engine.started == [] and engine.saved == []


# ═══════════════════════════════════════════════════════════════════
# 3. 可見性：模型視角與影子視角都看不到
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
def test_agent_turn_hidden_from_model_and_shadow_but_visible_to_facade():
    deps = _deps(_app())
    registry = _registry_with_agent_turn(deps)
    prospect = _identity()

    def names(**kw):
        return {s["name"] for s in registry.specs_for(prospect, "M1", **kw)}

    # 正對照組：門面視角看得到（否則下面三個「看不到」可能只是根本沒註冊）
    assert F.AGENT_TURN_NAME in names(for_model=False)
    assert F.AGENT_TURN_NAME not in names(for_model=True)
    assert F.AGENT_TURN_NAME not in names(for_model=False, readonly_view=True)
    assert F.AGENT_TURN_NAME not in names(for_model=True, readonly_view=True)
    # 模型工具清單（Chat Completions tools[]）同樣看不到
    assert F.AGENT_TURN_NAME not in {
        t["function"]["name"] for t in registry.to_openai_tools(prospect, "M1")
    }


@pytest.mark.req(_SPEC)
def test_agent_turn_stage_is_prospect_and_pm_only():
    """DSP-037（業主 2026-09-07）：prospect ＋ pm 於 M1 開；**tenant 缺鍵＝永不可見**。"""
    deps = _deps(_app())
    registry = _registry_with_agent_turn(deps)

    def visible(identity, stage):
        return F.AGENT_TURN_NAME in {
            s["name"] for s in registry.specs_for(identity, stage, for_model=False)
        }

    assert visible(_identity(), "M1") is True                      # 正對照組
    assert visible(_identity(), "M0") is False                     # stage 未到
    assert visible(_identity(target_user="tenant"), "M5") is False  # 缺鍵
    # DSP-037：pm 從 M1 起可見（S1a）；M0 仍未到
    assert visible(_identity(target_user="property_manager", mode="b2b"), "M1") is True
    assert visible(_identity(target_user="property_manager", mode="b2b"), "M0") is False


@pytest.mark.req(_SPEC)
def test_agent_turn_input_schema_only_takes_message():
    """處置②：屬性集合 == {message, image_urls, context}，⛔ 無 `dialog_ref`。

    W8 (2)：`image_urls` 是**唯一**新增的鍵，且 `message` 改 `minLength 0`
    （仍 required）——純照片回合合法，早退改判「兩者皆空」（見
    `tests/unit/agent/test_image_entry_req.py`）。
    """
    schema = F.AGENT_TURN_SPEC["input_schema"]
    # T1：`context` 是第三個鍵（選填；`context` 的專用測試見
    # `test_context_req.py`）。⛔ 仍無 `dialog_ref`。
    # W9 U1：`attachment_purpose`／`file_urls` 是第四、五個鍵（選填；專用測試見
    # `test_document_turn_req.py`）。屬性集合是**封閉的**，⛔ 不得只加不對帳。
    assert set(schema["properties"]) == {
        "message", "image_urls", "context", "attachment_purpose", "file_urls",
    }
    assert schema["required"] == ["message"]
    assert schema["properties"]["message"]["maxLength"] == 2000
    assert schema["properties"]["message"]["minLength"] == 0
    assert F.AGENT_TURN_SPEC["facade_only"] is True
    assert F.AGENT_TURN_SPEC["mutates_session"] is True
    assert F.AGENT_TURN_SPEC["scope"] == "read"
    assert F.AGENT_TURN_SPEC["stage"] == {"prospect": "M1", "property_manager": "M1"}  # DSP-037


@pytest.mark.req(_SPEC)
async def test_agent_turn_rejects_message_over_max_length():
    engine = FakeEngine()
    deps = _deps(_app(runtime=_runtime(FakeProvider([])), engine=engine))
    registry = _registry_with_agent_turn(deps)
    result = await _call_agent_turn(registry, _identity(), "字" * 2001)
    assert result.ok is False and result.error == "INVALID_INPUT"
    assert engine.started == []


# ═══════════════════════════════════════════════════════════════════
# 4. AGENT_TURN_ENABLED 回切開關
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
def test_agent_turn_registration_is_gated_by_env(monkeypatch):
    def registered(value):
        if value is None:
            monkeypatch.delenv("AGENT_TURN_ENABLED", raising=False)
        else:
            monkeypatch.setenv("AGENT_TURN_ENABLED", value)
        reg = F.build_registry(F.FacadeDeps(get_db_pool=lambda: None,
                                            get_kb_pool=lambda: None, stage="M1"))
        return F.AGENT_TURN_NAME in {s["name"] for s in F.union_specs(reg, "M1")}

    assert registered(None) is False      # 預設 false
    assert registered("false") is False
    assert registered("0") is False
    assert registered("true") is True     # 正對照組
    assert registered("1") is True


@pytest.mark.req(_SPEC)
def test_agent_turn_is_not_governed_by_agent_audiences(monkeypatch):
    """design 1.4.6：`AGENT_AUDIENCES` 只管 REST 入口，⛔ 不左右 `agent.turn`。"""
    monkeypatch.setenv("AGENT_TURN_ENABLED", "true")
    monkeypatch.setenv("AGENT_AUDIENCES", "")   # REST 全關
    reg = F.build_registry(F.FacadeDeps(get_db_pool=lambda: None,
                                        get_kb_pool=lambda: None, stage="M1"))
    assert F.AGENT_TURN_NAME in {s["name"] for s in F.union_specs(reg, "M1")}


# ═══════════════════════════════════════════════════════════════════
# 5. 命名空間鍵形狀與跨業者隔離
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
def test_namespaced_key_shape():
    store = NamespacedStateStore(object(), API_KEY_ID, VENDOR_A)
    assert store.key(SESSION) == f"mcp:{API_KEY_ID}:{VENDOR_A}:{SESSION}"
    # fail-closed：缺 id ⇒ 建不起來（⛔ 不退回裸 session_id）
    for bad in ((None, VENDOR_A), (API_KEY_ID, None)):
        with pytest.raises(ValueError):
            NamespacedStateStore(object(), *bad)
    # fail-closed：鍵超過 form_sessions.session_id 的 VARCHAR(100)
    with pytest.raises(ValueError):
        store.key("s" * 100)


@pytest.mark.req(_SPEC)
async def test_agent_turn_writes_under_namespaced_key():
    engine = FakeEngine()
    runtime = _runtime(FakeProvider([_final_response(answer="好的。")]))
    deps = _deps(_app(runtime=runtime, engine=engine))
    await _call_agent_turn(_registry_with_agent_turn(deps), _identity(), "第一句")

    expected = f"mcp:{API_KEY_ID}:{VENDOR_A}:{SESSION}"
    assert engine.started == [expected]
    assert engine.saved == [expected]
    # ⛔ 裸 session_id 底下不得有任何列
    assert SESSION not in engine.rows


@pytest.mark.req(_SPEC)
async def test_same_session_id_different_vendor_cannot_see_or_change_the_row():
    """前置 security review P1 的驗收句：同 `session_id` 不同 vendor ⇒
    讀不到前回合 slots，且**原列不改**。"""
    engine = FakeEngine()

    runtime_a = _runtime(FakeProvider([_final_response(answer="A 的回答")]))
    deps_a = _deps(_app(runtime=runtime_a, engine=engine))
    await _call_agent_turn(_registry_with_agent_turn(deps_a),
                           _identity(vendor_id=VENDOR_A), "第一句")

    key_a = f"mcp:{API_KEY_ID}:{VENDOR_A}:{SESSION}"
    snapshot_a = json.dumps(engine.rows[key_a], sort_keys=True, ensure_ascii=False)
    assert "handoff_cache" in json.dumps(engine.rows[key_a])  # 正對照：A 真的存了 agent 狀態

    runtime_b = _runtime(FakeProvider([_final_response(answer="B 的回答")]))
    deps_b = _deps(_app(runtime=runtime_b, engine=engine))
    await _call_agent_turn(_registry_with_agent_turn(deps_b),
                           _identity(vendor_id=VENDOR_B), "第二句")

    key_b = f"mcp:{API_KEY_ID}:{VENDOR_B}:{SESSION}"
    assert key_a != key_b
    # B 讀不到 A 的東西：B 是**新開**的一列（started 有它）
    assert key_b in engine.started
    # 原列一字未改
    assert json.dumps(engine.rows[key_a], sort_keys=True, ensure_ascii=False) == snapshot_a


@pytest.mark.req(_SPEC)
async def test_second_turn_sees_first_turn_state():
    """同一 (key, vendor, session) 的第二回合讀得到第一回合留下的狀態。

    用 `fixed_streak`（Runtime 每回合都會寫）當觀測點：第一回合固定句收場 ⇒ 1，
    第二回合再固定句 ⇒ 2。若狀態沒被讀回來，第二回合會從 0 重算成 1。
    """
    engine = FakeEngine()
    deps_app = _app(runtime=None, engine=engine)

    async def _one_turn(message):
        runtime = _runtime(
            FakeProvider([_final_response(answer="草稿")] * 3),
            verifier=FakeVerifier([VerifierVerdict(ok=False, reason="SCHEMA")] * 3),
        )
        deps_app.state.agent_runtime = runtime
        deps = _deps(deps_app)
        return await _call_agent_turn(_registry_with_agent_turn(deps), _identity(), message)

    await _one_turn("第一句")
    key = f"mcp:{API_KEY_ID}:{VENDOR_A}:{SESSION}"
    assert engine.rows[key]["agent"]["fixed_streak"] == 1

    await _one_turn("第二句")
    assert engine.rows[key]["agent"]["fixed_streak"] == 2
    assert engine.started == [key], "第二回合不該再開一列"


@pytest.mark.req(_SPEC)
async def test_outline_is_injected_for_the_turn_but_never_persisted():
    """大綱進場前塞、存檔前 pop——⛔ 不得序列化進 `form_sessions.collected_data`。

    這裡刻意用一個**不可 json 序列化**的假大綱物件：它若漏進 state，
    `FakeEngine._save` 的 json 往返會當場炸（那正是真表 jsonb 會做的事）。
    """
    engine = FakeEngine()
    assembler = FakeAssembler()
    outline = SimpleNamespace(sha256="outline-sha", text="大綱本文")
    runtime = _runtime(FakeProvider([_final_response(answer="好的。")]), assembler=assembler)
    deps = _deps(_app(runtime=runtime, engine=engine, outline=outline))

    result = await _call_agent_turn(_registry_with_agent_turn(deps), _identity(), "問題")

    assert result.ok is True, result.error
    assert assembler.last_outline is outline, "回合內模型組 prompt 時要拿得到大綱"
    key = f"mcp:{API_KEY_ID}:{VENDOR_A}:{SESSION}"
    assert "outline" not in engine.rows[key]["agent"]
    assert "outline-sha" not in json.dumps(engine.rows[key], ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════
# 6. 逾時不 save
# ═══════════════════════════════════════════════════════════════════
class _SlowRuntime:
    rules_sha = "slow"

    def __init__(self) -> None:
        self.cancelled = False

    async def run_turn(self, identity, message, state):
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return SimpleNamespace(answer="不該走到這", kind="answer", handoff=None,
                               quick_replies=[], trace=SimpleNamespace(trace_id="x"))


@pytest.mark.req(_SPEC)
async def test_timeout_returns_tool_timeout_and_does_not_save(monkeypatch):
    monkeypatch.setenv("AGENT_TURN_TIMEOUT_S", "0.05")
    engine = FakeEngine()
    slow = _SlowRuntime()
    deps = _deps(_app(runtime=slow, engine=engine))

    result = await _call_agent_turn(_registry_with_agent_turn(deps), _identity(), "很慢的一句",
                                    timeout_s=5.0)

    assert result.ok is False and result.error == "TOOL_TIMEOUT"
    assert slow.cancelled is True, "run_turn 應該真的被取消（而不是跑完才被丟掉）"
    assert engine.saved == [], "⛔ 逾時不得 save（半寫的回合狀態不落地）"


@pytest.mark.req(_SPEC)
def test_agent_turn_timeout_default_is_greater_than_budget_deadline(monkeypatch):
    """處置③：門面逾時必須 > `Budget.deadline_s`，否則整回合永遠被砍在半路。"""
    monkeypatch.delenv("AGENT_TURN_TIMEOUT_S", raising=False)
    assert F.agent_turn_timeout_s() > Budget().deadline_s
    # 非法值退回預設，⛔ 不讓一個打錯的 env 把逾時變成 0
    monkeypatch.setenv("AGENT_TURN_TIMEOUT_S", "not-a-number")
    assert F.agent_turn_timeout_s() == 30.0
    monkeypatch.setenv("AGENT_TURN_TIMEOUT_S", "0")
    assert F.agent_turn_timeout_s() == 30.0


# ═══════════════════════════════════════════════════════════════════
# 7. 每小時上限（走真的 `_invoke`）
# ═══════════════════════════════════════════════════════════════════
def _patch_metering(monkeypatch):
    """把 `_invoke` 用到的計量三件事換成不打 DB 的替身；`begin` 用真的
    （純記憶體、建 contextvar），`quota_check`／`finalize` 換掉。"""
    from services import usage_metering as um

    finalized: list = []

    async def _quota_check(pool, vendor_id, is_internal):
        return SimpleNamespace(state="ok")

    def _finalize(status, http_status, db_pool=None):
        finalized.append((status, http_status))
        ctx = um._ctx.get()
        if ctx is not None:
            ctx._finalized = True

    monkeypatch.setattr(um, "quota_check", _quota_check)
    monkeypatch.setattr(um, "finalize", _finalize)
    return finalized


def _patch_resolve_call(monkeypatch, *, identity=None):
    async def _resolve(headers, pool, allowed_origins=None):
        return F.ResolvedCall(identity=identity or _identity(), api_key_id=API_KEY_ID,
                              is_internal=False)

    monkeypatch.setattr(F, "resolve_call", _resolve)


@pytest.mark.req(_SPEC)
async def test_hourly_cap_returns_rate_limited(monkeypatch):
    _set_turns_per_hour(monkeypatch, 2)
    monkeypatch.setenv("AGENT_TURN_TIMEOUT_S", "5")
    F.reset_agent_turn_cap()
    finalized = _patch_metering(monkeypatch)
    _patch_resolve_call(monkeypatch)

    engine = FakeEngine()
    runtime = _runtime(FakeProvider([_final_response(answer="好的。")] * 4))
    deps = _deps(_app(runtime=runtime, engine=engine))
    invoke = F._make_invoke(_registry_with_agent_turn(deps), deps)
    ctx = SimpleNamespace(headers={})

    # 正對照組：上限內的兩次都成功
    for _ in range(2):
        out = await invoke(F.AGENT_TURN_NAME, ctx, {"message": "問題"})
        assert out["kind"] == "answer"

    with pytest.raises(Exception) as e:
        await invoke(F.AGENT_TURN_NAME, ctx, {"message": "問題"})
    assert str(e.value) == "RATE_LIMITED"
    # 不變量 31：被擋掉的那次也留下一列（⛔ 不是免費的探測管道）
    assert finalized[-1] == ("blocked", 429)
    assert len(engine.saved) == 2, "被擋掉的第三次不得跑到回合邏輯"


@pytest.mark.req(_SPEC)
async def test_missing_runtime_is_agent_unavailable(monkeypatch):
    _set_turns_per_hour(monkeypatch, 100)
    F.reset_agent_turn_cap()
    finalized = _patch_metering(monkeypatch)
    _patch_resolve_call(monkeypatch)

    engine = FakeEngine()
    deps = _deps(_app(engine=engine))          # ⚠️ 沒有 app.state.agent_runtime
    invoke = F._make_invoke(_registry_with_agent_turn(deps), deps)

    with pytest.raises(Exception) as e:
        await invoke(F.AGENT_TURN_NAME, SimpleNamespace(headers={}), {"message": "問題"})
    assert str(e.value) == F.ERR_AGENT_UNAVAILABLE
    assert finalized[-1] == ("error", 503)
    # 配額不該被這種「服務沒接好」的呼叫吃掉
    assert F.check_and_record_agent_turn((API_KEY_ID, VENDOR_A)) is True


@pytest.mark.req(_SPEC)
def test_cap_key_is_api_key_and_vendor_not_session(monkeypatch):
    """換 `session_id` ⛔ 不重置計數；換 vendor 才是另一個桶。"""
    _set_turns_per_hour(monkeypatch, 1)
    F.reset_agent_turn_cap()
    assert F.check_and_record_agent_turn((API_KEY_ID, VENDOR_A)) is True
    assert F.check_and_record_agent_turn((API_KEY_ID, VENDOR_A)) is False
    assert F.check_and_record_agent_turn((API_KEY_ID, VENDOR_B)) is True   # 另一個桶


@pytest.mark.req(_SPEC)
def test_cap_window_slides(monkeypatch):
    _set_turns_per_hour(monkeypatch, 1)
    F.reset_agent_turn_cap()
    key = (API_KEY_ID, VENDOR_A)
    assert F.check_and_record_agent_turn(key, now=0.0) is True
    assert F.check_and_record_agent_turn(key, now=3599.0) is False
    assert F.check_and_record_agent_turn(key, now=3601.0) is True   # 視窗滑掉了


# ═══════════════════════════════════════════════════════════════════
# 8. handoff_cache ≤50 FIFO
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_handoff_cache_evicts_oldest_beyond_fifty():
    """處置⑦：第 51 筆進來時擠掉第 1 筆（FIFO），⛔ 不是無上限地長。

    S4 §5：`fact_class=other`＋`no_grounding` 的零查詢轉人會被出口閘降級成
    追問、⛔ 不再進快取——本測試改用敏感類＋`sensitive_no_grounding`，那條
    handoff 不受降級影響，快取行為與本測試主張無關、維持原本驗的東西。
    """
    total = HANDOFF_CACHE_MAX + 1
    runtime = _runtime(
        FakeProvider([_final_response(kind="handoff", answer="轉人",
                                      fact_class="pricing", handoff_reason="sensitive_no_grounding")
                      for _ in range(total)])
    )
    state: dict = {}
    for i in range(total):
        await runtime.run_turn(_identity(), f"問題編號 {i}", state)

    cache = state["agent"]["handoff_cache"]
    assert len(cache) == HANDOFF_CACHE_MAX
    keys = list(cache)

    from services.agent.runtime import _cache_key

    assert _cache_key("問題編號 0") not in cache, "第 1 筆應該被擠掉"
    assert _cache_key(f"問題編號 {total - 1}") == keys[-1], "第 51 筆應該在最後"


# ═══════════════════════════════════════════════════════════════════
# 9. trace 無 args_hash
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_trace_has_no_args_hash(monkeypatch):
    """處置⑤：`ToolCallRecord` 與落地的 `decision_snapshot.agent` 都不得有
    `args_hash`（低熵參數的 sha256 可字典反解）。"""
    import dataclasses

    from services import usage_metering as um

    fields = {f.name for f in dataclasses.fields(ToolCallRecord)}
    assert "args_hash" not in fields
    assert "args_summary" in fields          # 正對照組：摘要還在

    captured: list = []
    monkeypatch.setattr(um, "set_agent_decision", lambda payload: captured.append(payload))

    class _Reg(ToolRegistry):
        pass

    registry = _Reg()
    registry.register(
        {"name": "kb.get", "description": "", "scope": "read",
         "input_schema": {"type": "object", "properties": {"kb_id": {"type": "string"}},
                          "required": ["kb_id"], "additionalProperties": False},
         "stage": {"prospect": "M0"}},
        lambda identity, args: _ok_result(),
    )
    provider = FakeProvider([
        _fake_response(_fake_message(tool_calls=[_fake_tool_call("kb.get", {"kb_id": "3600"})])),
        _final_response(answer="查到了。"),
    ])
    runtime = _runtime(provider, registry=registry)
    await runtime.run_turn(_identity(), "查一下 3600", {})

    assert captured, "沒有落地任何 decision_snapshot——這條斷言就什麼都沒證明"
    tool_calls = captured[-1]["tool_calls"]
    assert tool_calls and set(tool_calls[0]) == {"name", "args_summary", "ms", "status", "n_items"}


async def _ok_result():
    return ToolResult(ok=True, data={"id": 3600}, text_for_model="知識原文")


# ═══════════════════════════════════════════════════════════════════
# 10. term_id 匹配 ^rule#\d+$
# ═══════════════════════════════════════════════════════════════════
def _rules(**overrides) -> VerifierRules:
    base = dict(
        version="test", sha256="0" * 64,
        sensitive_patterns=[r"保證獲利"],
        negation_terms=["不"],
        # ⚠️ 第 2 個刻意挑一個「能通過前五步」的詞：禁詞掃描是第⑥步，
        #    句子若先在②～④被判成沒引用的斷言，就永遠走不到⑥。
        forbid_terms=["絕對", "您好"],
        allowed_routes=[],
        assertion_terms=["支援"],
    )
    base.update(overrides)
    return VerifierRules.model_validate(base)


def _output(answer: str, *, fact_class="feature") -> AgentOutput:
    """DSP-028：逐句切成一筆 `Sentence`（全標 greeting，讓②～④不攔，測⑤⑥⑦）。"""
    from services.agent.output_schema import Sentence

    sents = [s for s in re.split(r"(?<=。)", answer) if s]
    out = AgentOutput(
        kind="answer",
        sentences=[Sentence(text=s, kind="greeting", refs=[]) for s in sents],
        fact_class=fact_class,
    )
    assert out.answer == answer, "拼接後必須等於原文——這是 DSP-028 的定義"
    return out


@pytest.mark.req(_SPEC)
def test_forbidden_term_verdict_uses_rule_index_not_the_literal_term():
    verifier = OutputVerifier(_rules())
    verdict = verifier.verify(_output("您好。"), {}, "問句", None,
                              resolved={}, resolve_errors={})
    assert verdict.ok is False and verdict.reason == "FORBIDDEN_TERM"
    assert re.match(TERM_ID_PATTERN, verdict.term_id), verdict.term_id
    assert verdict.term_id == "rule#1", "forbid_terms 內索引（第 2 個）"
    # ⛔ 字面詞不得出現在 verdict 的任何欄位
    assert "您好" not in json.dumps(verdict.model_dump(), ensure_ascii=False)


@pytest.mark.req(_SPEC)
def test_sensitive_pattern_verdict_uses_rule_index():
    verifier = OutputVerifier(_rules())
    verdict = verifier.verify(_output("我們保證獲利。"), {}, "問句", None,
                              resolved={}, resolve_errors={})
    assert verdict.reason == "SENSITIVE_TOPIC"
    assert verdict.term_id == "rule#0"
    assert "保證獲利" not in json.dumps(verdict.model_dump(), ensure_ascii=False)


@pytest.mark.req(_SPEC)
def test_verdict_model_rejects_a_literal_term_id():
    """契約釘在型別上：任何想塞字面詞的呼叫端在建構當下就炸。"""
    from pydantic import ValidationError

    VerifierVerdict(ok=False, reason="FORBIDDEN_TERM", term_id="rule#3")   # 正對照組
    with pytest.raises(ValidationError):
        VerifierVerdict(ok=False, reason="FORBIDDEN_TERM", term_id="literal-term")


@pytest.mark.req(_SPEC)
def test_all_real_ruleset_term_ids_are_rule_indices():
    """對**正式規則集**跑一遍 fixture，任何非 `rule#n` 的 term_id 都算紅。"""
    from pathlib import Path

    from services.agent.provenance_units import resolve_refs
    from services.agent.verifier import _FIXTURE_NONCE

    root = Path(__file__).resolve().parents[3]
    rules = VerifierRules.load(root / "config" / "agent_verifier_rules.json")
    verifier = OutputVerifier(rules)
    cases = json.loads(
        (root / "tests" / "fixtures" / "agent" / "known_fabrications.json")
        .read_text(encoding="utf-8")
    )
    seen_term_ids = 0
    for case in cases:
        out = AgentOutput.model_validate(case["agent_output"])
        tool_results = {
            tid: ToolResult.model_validate(tr)
            for tid, tr in case.get("tool_results", {}).items()
        }
        # DSP-029a：引用解析由系統產生後另傳（⛔ 不從 out 取、⛔ 不在測試裡另寫一份）
        resolved, resolve_errors = resolve_refs(
            out, tool_results, case.get("nonce") or _FIXTURE_NONCE)
        verdict = verifier.verify(out, tool_results, case.get("user_message", ""),
                                  case.get("handoff"),
                                  resolved=resolved, resolve_errors=resolve_errors)
        if verdict.term_id is not None:
            seen_term_ids += 1
            assert re.match(TERM_ID_PATTERN, verdict.term_id), (case["id"], verdict.term_id)
    assert seen_term_ids > 0, "沒有任何案例填了 term_id——這條斷言什麼都沒證明"


# ═══════════════════════════════════════════════════════════════════
# 附：health 的 rules_sha 改讀 runtime（任務 2.6 交付 6）
# ═══════════════════════════════════════════════════════════════════
@pytest.mark.req(_SPEC)
async def test_health_rules_sha_reads_runtime():
    """`rules_sha` 要回**這個行程實際帶著的那把尺**；取不到才 `"pending"`。

    ⚠️ 正產線的接線點是 `routers/agent.py`（任務 2.7 平行進行中，本任務 ⛔ 不改
    該檔）——它要傳
    `get_runtime=lambda: getattr(request.app.state, "agent_runtime", None)`。
    在它接上之前，這裡的行為是「沒給 getter ⇒ pending」，⛔ 不算紅。
    """
    from services.agent.health import compute_agent_health

    registry = _registry_with_agent_turn(_deps(_app()))
    base = dict(registry=registry, get_kb_pool=None, stage="M1")

    assert (await compute_agent_health(**base))["checks"]["rules_sha"] == "pending"
    assert (await compute_agent_health(
        **base, get_runtime=lambda: None))["checks"]["rules_sha"] == "pending"
    assert (await compute_agent_health(
        **base, get_runtime=lambda: SimpleNamespace()))["checks"]["rules_sha"] == "pending"
    # 正對照組：真有 runtime 就回它的 sha（⛔ 不是硬編的 "pending"）
    result = await compute_agent_health(
        **base, get_runtime=lambda: SimpleNamespace(rules_sha="deadbeef" * 8))
    assert result["checks"]["rules_sha"] == "deadbeef" * 8
    # rules_sha 是觀測值，⛔ 不參與致紅判定
    assert "rules_sha" not in result["checks"]["premise"]["red_flags"]


@pytest.mark.req(_SPEC)
async def test_invisible_identity_gets_no_match_not_agent_unavailable(monkeypatch):
    """看不到這支工具的身分，⛔ 不得從錯誤碼分辨出「服務存在但沒起來」。

    preflight（`AGENT_UNAVAILABLE`／`RATE_LIMITED`）只在工具**對該身分可見**時
    才跑；否則一律讓 `registry.call()` 統一回 `NO_MATCH`，也不燒他的配額。
    """
    _set_turns_per_hour(monkeypatch, 1)
    F.reset_agent_turn_cap()
    tenant = _identity(target_user="tenant")
    _patch_metering(monkeypatch)
    _patch_resolve_call(monkeypatch, identity=tenant)

    engine = FakeEngine()
    deps = _deps(_app(engine=engine))          # ⚠️ 沒有 agent_runtime
    invoke = F._make_invoke(_registry_with_agent_turn(deps), deps)

    with pytest.raises(Exception) as e:
        await invoke(F.AGENT_TURN_NAME, SimpleNamespace(headers={}), {"message": "問題"})
    assert str(e.value) == "NO_MATCH", "⛔ 不得對不可見身分回 AGENT_UNAVAILABLE"
    # 配額一格都沒被燒掉（cap=1，還叫得動一次）
    assert F.check_and_record_agent_turn((tenant.api_key_id, tenant.vendor_id)) is True

    # 正對照組：換成 prospect ＋ runtime 缺席，就會拿到 AGENT_UNAVAILABLE
    F.reset_agent_turn_cap()
    _patch_resolve_call(monkeypatch, identity=_identity())
    with pytest.raises(Exception) as e2:
        await invoke(F.AGENT_TURN_NAME, SimpleNamespace(headers={}), {"message": "問題"})
    assert str(e2.value) == F.ERR_AGENT_UNAVAILABLE


# ═══════════════════════════════════════════════════════════════════
# 11. 任務 2.9：門面交給工具的身分＝命名空間身分
# ═══════════════════════════════════════════════════════════════════
_REQ_29 = "agentic-mcp-orchestration:2.9"


class _SpyRegistry(ToolRegistry):
    """記下每次 `call()` 收到的 identity（⛔ 不改行為，只旁錄）。"""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.seen: list = []

    async def call(self, identity, name, args, timeout_s, **kw):
        self.seen.append((name, identity))
        return await super().call(identity, name, args, timeout_s, **kw)


@pytest.mark.req(_REQ_29)
async def test_invoke_hands_tools_a_namespaced_identity(monkeypatch):
    """非 `agent.turn` 的工具拿到的 `session_id` 必須是命名空間鍵。

    這條是 2.6 P1 的側門：`session.slots.*`／`confirm.request` 的 SQL 沒有
    vendor 條件，裸 `session_id` 進去就等於跨業者共用一把鍵。
    """
    _patch_metering(monkeypatch)
    _patch_resolve_call(monkeypatch)

    registry = _SpyRegistry()
    registry.register(
        {"name": "probe.read", "description": "測試用",
         "input_schema": {"type": "object", "properties": {}, "required": []},
         "scope": "read", "stage": {"prospect": "M1"}},
        lambda identity, args: _ok_result(),
    )
    deps = _deps(_app())
    invoke = F._make_invoke(registry, deps)

    await invoke("probe.read", SimpleNamespace(headers={}), {})

    name, seen = registry.seen[-1]
    assert name == "probe.read"
    assert seen.session_id == f"mcp:{API_KEY_ID}:{VENDOR_A}:{SESSION}"
    # 反對照：⛔ 不得是呼叫端給的裸值
    assert seen.session_id != SESSION
    # 其餘身分欄位不動
    assert (seen.vendor_id, seen.api_key_id) == (VENDOR_A, API_KEY_ID)


async def _ok_result():
    from services.agent.tools.registry import ToolResult as _TR

    return _TR(ok=True, data={"ok": 1}, text_for_model="ok")


@pytest.mark.req(_REQ_29)
async def test_invoke_does_not_double_prefix_agent_turn(monkeypatch):
    """`agent.turn` 例外：它自己餵 `NamespacedStateStore`（會加前綴），
    所以門面交給 registry 的必須是**裸**身分——否則變成 `mcp:k:v:mcp:k:v:sid`。"""
    _set_turns_per_hour(monkeypatch, 100)
    monkeypatch.setenv("AGENT_TURN_TIMEOUT_S", "5")
    F.reset_agent_turn_cap()
    _patch_metering(monkeypatch)
    _patch_resolve_call(monkeypatch)

    engine = FakeEngine()
    runtime = _runtime(FakeProvider([_final_response(answer="好的。")]))
    deps = _deps(_app(runtime=runtime, engine=engine))
    registry = _SpyRegistry()
    registry.register(F.AGENT_TURN_SPEC, F._make_agent_turn(deps))
    invoke = F._make_invoke(registry, deps)

    await invoke(F.AGENT_TURN_NAME, SimpleNamespace(headers={}), {"message": "問題"})

    _name, seen = registry.seen[-1]
    assert seen.session_id == SESSION, "⛔ agent.turn 不得先換身分（會雙前綴）"
    key = f"mcp:{API_KEY_ID}:{VENDOR_A}:{SESSION}"
    assert engine.saved == [key]
    assert not any(k.count("mcp:") > 1 for k in engine.rows), sorted(engine.rows)


@pytest.mark.req(_REQ_29)
async def test_runtime_inside_agent_turn_gets_the_namespaced_identity():
    """回合內的工具呼叫同樣落在命名空間鍵下（runtime 收到的身分就是換過的）。"""
    engine = FakeEngine()
    seen: list = []

    class _SpyRuntime:
        rules_sha = "spy"

        async def run_turn(self, identity, message, state):
            seen.append(identity)
            return SimpleNamespace(answer="好的。", kind="answer", handoff=None,
                                   quick_replies=[],
                                   trace=SimpleNamespace(trace_id="t1"))

    deps = _deps(_app(runtime=_SpyRuntime(), engine=engine))
    result = await _call_agent_turn(_registry_with_agent_turn(deps), _identity(), "問題")

    assert result.ok is True, result.error
    assert seen[0].session_id == f"mcp:{API_KEY_ID}:{VENDOR_A}:{SESSION}"
    assert seen[0].session_id != SESSION      # 反對照
    # 但列還是那一列（store 用裸值 + 自己的前綴），⛔ 沒有第二列
    assert list(engine.rows) == [f"mcp:{API_KEY_ID}:{VENDOR_A}:{SESSION}"]


@pytest.mark.req(_REQ_29)
async def test_slots_set_result_survives_end_of_turn_save():
    """回合內 `session.slots.set` 寫進 DB 的槽位，⛔ 不得被回合結束的整包覆寫抹掉。

    `ConversationalEngine._save` 是 `SET collected_data=$2::jsonb`（整包覆蓋，
    不是 merge）。工具改的是 DB，runtime 手上的 `state` 不同步 ⇒ 存回去時
    連同剛寫的槽位一起被蓋掉。故 runtime 以**工具回傳的全表**同步回 state。
    """
    engine = FakeEngine()
    registry = ToolRegistry()

    written: dict = {}

    async def _fake_slots_set(identity, args):
        from services.agent.tools.registry import ToolResult as _TR

        written[args["key"]] = {"value": args["value"], "source": "tool",
                                "confirmed": False}
        return _TR(ok=True, data={"slots": dict(written)},
                   text_for_model=f"{args['key']}={args['value']}")

    from services.agent.tools.session import SLOTS_SET_SPEC

    registry.register(SLOTS_SET_SPEC, _fake_slots_set)

    provider = FakeProvider([
        _fake_response(_fake_message(tool_calls=[
            _fake_tool_call("session.slots.set",
                            {"key": "unit_count", "value": "600"})])),
        _final_response(answer="好的。"),
    ])
    runtime = _runtime(provider, registry=registry)
    deps = _deps(_app(runtime=runtime, engine=engine))
    result = await _call_agent_turn(_registry_with_agent_turn(deps), _identity(), "600 戶")

    assert result.ok is True, result.error
    key = f"mcp:{API_KEY_ID}:{VENDOR_A}:{SESSION}"
    saved = engine.rows[key]
    assert saved["slots"] == {"unit_count": {"value": "600", "source": "tool",
                                             "confirmed": False}}, \
        "回合結束的整包覆寫把剛寫入的槽位抹掉了"
    # 正對照組：工具真的被叫到了（否則上面那條可能只是沒跑到）
    assert written == {"unit_count": {"value": "600", "source": "tool",
                                      "confirmed": False}}


@pytest.mark.req(_REQ_29)
async def test_next_turn_reads_the_slot_written_by_the_tool():
    """下一回合的 prompt 看得到上一回合寫的槽位（且已攤平成純量）。"""
    engine = FakeEngine()
    key = f"mcp:{API_KEY_ID}:{VENDOR_A}:{SESSION}"
    engine.rows[key] = {
        "config_key": "agent:prospect", "collected_fields": {}, "asked_count": 0,
        "slots": {"unit_count": {"value": "600", "source": "tool", "confirmed": False}},
    }

    assembler = FakeAssembler()
    seen: dict = {}

    class _Spy(FakeAssembler):
        def build_messages(self, identity, outline, slots, dialog, tool_specs, nonce):
            seen["slots"] = dict(slots)
            return assembler.build_messages(identity, outline, slots, dialog,
                                            tool_specs, nonce)

    runtime = _runtime(FakeProvider([_final_response(answer="好的。")]),
                       assembler=_Spy())
    deps = _deps(_app(runtime=runtime, engine=engine))
    result = await _call_agent_turn(_registry_with_agent_turn(deps), _identity(), "第二句")

    assert result.ok is True, result.error
    # 任務 4.2：`run_turn` 在 `_slots_for_prompt` 之後覆寫兩個**派生**身分鍵 ⇒
    # 本回合 prompt 槽位恰為「攤平後的儲存槽位＋兩個派生鍵」。
    # ⛔ 不改成子集斷言：多出來的鍵必須被看見。
    assert set(seen["slots"]) == {"unit_count", "identity", "identity_source"}
    # 正對照組保留：`unit_count` 仍是**純量**——拿掉 `_slots_for_prompt` 的攤平
    # 就會變成 `{"value": "600", ...}` 而必紅。
    assert seen["slots"]["unit_count"] == "600", "槽位沒被讀回來（或沒攤平）"
    # 派生值依入口身分（`_identity()` 是 prospect、無 role_id／user_id）現算。
    assert seen["slots"]["identity"] == "prospect"
    assert seen["slots"]["identity_source"] == "anonymous"
