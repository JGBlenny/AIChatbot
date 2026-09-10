"""unit：`AgentSession`（Plan R R3｜
`inputs/plan-structural-refactor-20260910.md` §0 R3 列、§1 驗收）。

被測的五件事：

1. **`KEY_SPECS` 封閉且覆蓋 11 鍵**——與各檔既有常數逐一相等的正對照（避免
   `agent_session.py` 的字面值與 `turn_context.py`／`completed_actions.py`／
   `runtime.py` 各自的權威定義漂移，見 `agent_session` 模組 docstring）。
2. **六種生命週期各一案**：`fifo(n)` 的修剪數值（dialog 20／handoff_cache 50／
   pending_confirm 20／completed_actions 5）、`once`（image_suggestion 用掉即
   清）、`until_scope_exit`（estate_carry 在 `scope_exit()` 後清）、`turn`
   （select_scope／last_ask_target 每回合覆寫）、`stamp`（last_turn_at）、
   `session`（fixed_streak 累加不受回合覆寫）。
3. **`prompt_segments` 範圍門檻**：釘住時不回會話實體段，正對照未釘住時有。
4. **`begin_turn`／`end_turn` 是唯一寫點**：AST 掃描 `services/agent/**`
   找 `agent_state[...] = `／`.pop(`／`.setdefault(` 的直接寫入，斷言殘留只在
   `mcp_facade.py`（R3 擁有檔案清單外，⛔ 不碰，見任務 brief）與
   `turn_context._append_dialog`（R1 遺留、三個回合收尾寫點已全部改走
   `AgentSession.end_turn`，這支函式目前是死碼，僅為既有 re-export 路徑保留）
   ——兩者皆列出並說明，⛔ 不是「找不到就算過」。
5. **L8**：`NamespacedStateStore.start()` 依受眾組 `config_key`（pm ⇒
   `agent:property_manager`），舊列（不傳 `audience`）讀取相容。
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from services.agent import completed_actions as completed_actions_mod
from services.agent import runtime as runtime_mod
from services.agent import turn_context as turn_context_mod
from services.agent.agent_session import (
    COMPLETED_ACTIONS_KEY,
    COMPLETED_ACTIONS_MAX,
    DIALOG_KEY,
    DIALOG_MAX_MESSAGES,
    ESTATE_CARRY_KEY,
    FIXED_STREAK_KEY,
    HANDOFF_CACHE_KEY,
    HANDOFF_CACHE_MAX,
    IMAGE_SUGGESTION_KEY,
    KEY_SPECS,
    LAST_ASK_TARGET_KEY,
    LAST_TURN_AT_KEY,
    OUTLINE_KEY,
    PENDING_CONFIRM_KEY,
    PENDING_CONFIRM_MAX,
    SELECT_SCOPE_KEY,
    AgentSession,
    Lifetime,
)
from services.agent.state_store import DEFAULT_CONFIG_KEY, NamespacedStateStore, config_key_for

pytestmark = pytest.mark.unit

_REQ = "knowledge-outline-and-intent-architecture:R3"


# ---------------------------------------------------------------------------
# 1. KEY_SPECS 封閉且覆蓋 11 鍵 ＋ 與各檔權威定義逐一相等
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_key_specs_covers_exactly_eleven_keys():
    assert len(KEY_SPECS) == 11
    assert set(KEY_SPECS) == {
        DIALOG_KEY, OUTLINE_KEY, HANDOFF_CACHE_KEY, FIXED_STREAK_KEY,
        PENDING_CONFIRM_KEY, SELECT_SCOPE_KEY, LAST_ASK_TARGET_KEY,
        COMPLETED_ACTIONS_KEY, IMAGE_SUGGESTION_KEY, ESTATE_CARRY_KEY,
        LAST_TURN_AT_KEY,
    }


@pytest.mark.req(_REQ)
def test_key_specs_lifetimes_are_closed_enum():
    """`Lifetime` 只有六種——每一鍵的 `lifetime` 都落在這六種之內。"""
    valid = {Lifetime.TURN, Lifetime.ONCE, Lifetime.UNTIL_SCOPE_EXIT,
             Lifetime.FIFO, Lifetime.STAMP, Lifetime.SESSION}
    for key, spec in KEY_SPECS.items():
        assert spec.lifetime in valid, key
        assert spec.key == key


@pytest.mark.req(_REQ)
def test_key_names_match_authoritative_definitions_elsewhere():
    """正對照：本檔的字面值不得與各自的權威定義漂移（模組 docstring 說明的
    「重複一份、用測試守住」）。"""
    assert DIALOG_MAX_MESSAGES == turn_context_mod.DIALOG_MAX_MESSAGES
    assert HANDOFF_CACHE_MAX == turn_context_mod.HANDOFF_CACHE_MAX
    assert ESTATE_CARRY_KEY == turn_context_mod.ESTATE_CARRY_KEY
    assert SELECT_SCOPE_KEY == turn_context_mod.SELECT_SCOPE_KEY
    assert LAST_ASK_TARGET_KEY == turn_context_mod.LAST_ASK_TARGET_KEY
    assert COMPLETED_ACTIONS_KEY == completed_actions_mod.COMPLETED_ACTIONS_KEY
    assert COMPLETED_ACTIONS_MAX == completed_actions_mod.MAX_COMPLETED_ACTIONS
    assert PENDING_CONFIRM_KEY == runtime_mod.PENDING_CONFIRM_KEY
    assert PENDING_CONFIRM_MAX == runtime_mod.PENDING_CONFIRM_MAX
    assert IMAGE_SUGGESTION_KEY == runtime_mod.IMAGE_SUGGESTION_KEY
    assert LAST_TURN_AT_KEY == "last_turn_at"


# ---------------------------------------------------------------------------
# 2. 六種生命週期各一案
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_fifo_dialog_trims_at_twenty():
    state: dict = {}
    session = AgentSession(state)
    for i in range(12):
        session.append_dialog(f"u{i}", f"a{i}")
    assert len(state[DIALOG_KEY]) == DIALOG_MAX_MESSAGES == 20
    # 保留最新的一輪（近端），不是最舊的。
    assert state[DIALOG_KEY][-1] == {"role": "assistant", "content": "a11"}
    assert state[DIALOG_KEY][0] == {"role": "user", "content": "u2"}


@pytest.mark.req(_REQ)
def test_fifo_handoff_cache_trims_at_fifty():
    state: dict = {}
    session = AgentSession(state)
    for i in range(HANDOFF_CACHE_MAX + 5):
        session.write_handoff_cache(f"k{i}", {"answer": str(i)})
    cache = state[HANDOFF_CACHE_KEY]
    assert len(cache) == HANDOFF_CACHE_MAX == 50
    assert "k0" not in cache          # 最舊的被擠掉
    assert f"k{HANDOFF_CACHE_MAX + 4}" in cache


@pytest.mark.req(_REQ)
def test_fifo_pending_confirm_trims_at_twenty():
    state: dict = {}
    session = AgentSession(state)
    for i in range(PENDING_CONFIRM_MAX + 3):
        session.write_pending_confirm(f"p{i}", {"action": "repair_create"})
    pending = state[PENDING_CONFIRM_KEY]
    assert len(pending) == PENDING_CONFIRM_MAX == 20
    assert "p0" not in pending


@pytest.mark.req(_REQ)
def test_fifo_completed_actions_trims_at_five():
    state: dict = {}
    session = AgentSession(state)
    items = [{"ref_type": "repair", "ref_id": str(i)} for i in range(8)]
    session.write_completed_actions(items)
    assert len(state[COMPLETED_ACTIONS_KEY]) == COMPLETED_ACTIONS_MAX == 5
    assert state[COMPLETED_ACTIONS_KEY][0]["ref_id"] == "3"   # 只留最新 5 筆
    assert state[COMPLETED_ACTIONS_KEY][-1]["ref_id"] == "7"


@pytest.mark.req(_REQ)
def test_once_image_suggestion_consumed():
    state: dict = {IMAGE_SUGGESTION_KEY: {"category_name": "水電"}}
    session = AgentSession(state)
    assert session.get_image_suggestion() == {"category_name": "水電"}
    session.consume_image_suggestion()
    assert session.get_image_suggestion() is None
    assert IMAGE_SUGGESTION_KEY not in state


@pytest.mark.req(_REQ)
def test_until_scope_exit_estate_carry_cleared_by_scope_exit():
    state: dict = {ESTATE_CARRY_KEY: {"name": "測試大樓", "id": "1"}}
    session = AgentSession(state)
    assert session.get_estate_carry() is not None
    session.scope_exit()
    assert session.get_estate_carry() is None
    assert ESTATE_CARRY_KEY not in state


@pytest.mark.req(_REQ)
def test_turn_keys_overwritten_every_turn():
    """`select_scope`／`last_ask_target` 每回合覆寫（含寫 `None`）。"""
    state: dict = {SELECT_SCOPE_KEY: {"type": "bill", "estate_id": "1"},
                   LAST_ASK_TARGET_KEY: "confirm_intent"}
    session = AgentSession(state)
    session.write_select_scope(None)
    session.write_last_ask_target(None)
    assert session.select_scope is None
    assert session.last_ask_target is None
    session.write_select_scope({"type": "repair", "estate_id": "2"})
    assert session.select_scope == {"type": "repair", "estate_id": "2"}


@pytest.mark.req(_REQ)
def test_stamp_last_turn_at():
    state: dict = {}
    session = AgentSession(state)
    session.write_last_turn_at(123.5)
    assert session.last_turn_at == 123.5
    assert state[LAST_TURN_AT_KEY] == 123.5


@pytest.mark.req(_REQ)
def test_session_fixed_streak_accumulates_across_turns():
    """`fixed_streak` 是 session 累加值——連續 `is_fixed=True` 累加，
    任一次 `False` 就地歸零（⛔ 不受任何回合覆寫或 FIFO 影響）。"""
    state: dict = {}
    session = AgentSession(state)
    session.bump_fixed_streak(True)
    session.bump_fixed_streak(True)
    session.bump_fixed_streak(True)
    assert session.fixed_streak == 3
    session.bump_fixed_streak(False)
    assert session.fixed_streak == 0


# ---------------------------------------------------------------------------
# 3. prompt_segments 範圍門檻（正對照：未釘住有／釘住無）
# ---------------------------------------------------------------------------
@pytest.mark.req(_REQ)
def test_prompt_segments_hides_entity_segments_when_scope_pinned():
    state: dict = {}
    session = AgentSession(state)
    segs = session.prompt_segments(
        "estate-1", recent_refs_ids=["123456"], estate_carry={"name": "測試大樓", "id": "1"},
    )
    assert segs == {"recent_refs_ids": [], "estate_carry": None}


@pytest.mark.req(_REQ)
def test_prompt_segments_shows_entity_segments_when_not_pinned():
    """正對照：未釘住時兩段原樣放行。"""
    state: dict = {}
    session = AgentSession(state)
    segs = session.prompt_segments(
        None, recent_refs_ids=["123456"], estate_carry={"name": "測試大樓", "id": "1"},
    )
    assert segs == {"recent_refs_ids": ["123456"], "estate_carry": {"name": "測試大樓", "id": "1"}}


# ---------------------------------------------------------------------------
# 4. begin_turn／end_turn 是唯一寫點——AST 掃描 services/agent/** 的殘留
# ---------------------------------------------------------------------------
_AGENT_STATE_PARAM_NAMES = {"agent_state"}

#: 允許殘留的 (檔名, 說明) ——⛔ 不是「找不到就算過」，是逐一列名並交代理由。
_ALLOWED_RESIDUALS = {
    # R3 擁有檔案清單明列外（任務 brief）：「⛔ 不碰 verifier.py／mcp_facade.py
    # （門面若直接寫 agent_state，列成 R3b 待辦，不在本片）」。
    "mcp_facade.py",
    # R1 遺留的 `_append_dialog`／`_trim_handoff_cache`：三個回合收尾寫點
    # （`exit_gates.finalize`／`runtime._finish_confirm_turn`／
    # `turn_segments` 的 handoff_cache 重播）R3 已全部改走
    # `AgentSession.end_turn`，這兩支函式目前**沒有任何呼叫端**，僅為
    # `runtime.py` 既有 `# noqa: F401 — re-export` 的 import 路徑相容保留
    # （R1 docstring 自訂的紀律：「本檔原樣 re-export，既有 import 路徑
    # 不變」）。
    "turn_context.py",
}


def _agent_state_mutation_sites(py_file: Path) -> list[str]:
    """回傳這個檔案裡所有「對名為 `agent_state` 的變數做直接寫入」的行號＋種類
    （`subscript-store`／`pop`／`setdefault`）。"""
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            if isinstance(node.value, ast.Name) and node.value.id in _AGENT_STATE_PARAM_NAMES:
                hits.append(f"L{node.lineno}:subscript-store")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("pop", "setdefault"):
                base = node.func.value
                if isinstance(base, ast.Name) and base.id in _AGENT_STATE_PARAM_NAMES:
                    hits.append(f"L{node.lineno}:{node.func.attr}")
    return hits


@pytest.mark.req(_REQ)
def test_agent_state_direct_writes_are_confined_to_allowed_files():
    """`AgentSession` 是唯一寫點：`services/agent/**` 下對 `agent_state[...]`
    的直接寫入（含 `.pop`／`.setdefault`）只准出現在 `agent_session.py` 本身，
    或 `_ALLOWED_RESIDUALS` 列名的例外（見上方常數的逐一說明）。
    """
    agent_dir = Path(runtime_mod.__file__).resolve().parent
    offenders: dict[str, list[str]] = {}
    for py_file in sorted(agent_dir.rglob("*.py")):
        rel = py_file.relative_to(agent_dir)
        if rel.name == "agent_session.py":
            continue
        hits = _agent_state_mutation_sites(py_file)
        if hits:
            offenders[str(rel)] = hits

    unexplained = {
        name: hits for name, hits in offenders.items()
        if Path(name).name not in _ALLOWED_RESIDUALS
    }
    assert not unexplained, (
        f"發現未列名的直接寫入殘留（應改走 AgentSession，或加進 "
        f"_ALLOWED_RESIDUALS 並說明理由）：{unexplained}"
    )
    # 正對照：至少要抓得到已知的兩處殘留，證明這支掃描真的在動（不是空跑）。
    assert any(Path(n).name == "mcp_facade.py" for n in offenders)
    assert any(Path(n).name == "turn_context.py" for n in offenders)


@pytest.mark.req(_REQ)
def test_agent_session_itself_is_the_only_place_using_state_attribute():
    """變異正對照：`_agent_state_mutation_sites` 掃描邏輯本身看得見真的寫入
    ——拿一段已知會寫入的原始碼餵給它，必須抓到。"""
    import tempfile

    src = (
        "def f(agent_state):\n"
        "    agent_state['x'] = 1\n"
        "    agent_state.pop('y', None)\n"
        "    agent_state.setdefault('z', {})\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write(src)
        path = Path(fh.name)
    try:
        hits = _agent_state_mutation_sites(path)
        assert len(hits) == 3
    finally:
        path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 5. L8：pm 會話標籤依受眾；舊列讀取相容
# ---------------------------------------------------------------------------
class _FakeEngine:
    def __init__(self):
        self.started_with: dict = {}

    async def start(self, key, user_id, vendor_id, config_key, *, role_id=None):
        self.started_with = {
            "key": key, "user_id": user_id, "vendor_id": vendor_id,
            "config_key": config_key, "role_id": role_id,
        }
        return {"agent": {}}

    async def get_state(self, key):
        return None


@pytest.mark.req(_REQ)
async def test_start_with_pm_audience_uses_property_manager_config_key():
    engine = _FakeEngine()
    store = NamespacedStateStore(engine, api_key_id=1, vendor_id=2)
    await store.start("sess-1", "user-1", 2, "role-1", audience="property_manager")
    assert engine.started_with["config_key"] == "agent:property_manager"


@pytest.mark.req(_REQ)
async def test_start_without_audience_or_config_key_keeps_old_default():
    """舊列讀取相容：既有呼叫端（`mcp_facade.py`）不傳 `audience`／`config_key`
    ⇒ 行為逐字不變（`DEFAULT_CONFIG_KEY`，⛔ 不因為新增 `audience` 參數而改變）。
    """
    engine = _FakeEngine()
    store = NamespacedStateStore(engine, api_key_id=1, vendor_id=2)
    await store.start("sess-2", "user-2", 2, "role-2")
    assert engine.started_with["config_key"] == DEFAULT_CONFIG_KEY == "agent:prospect"


@pytest.mark.req(_REQ)
async def test_start_explicit_config_key_overrides_audience():
    """`config_key` 顯式給值時贏過 `audience`（既有呼叫端若曾經自己算過
    `config_key` 傳進來，行為不變）。"""
    engine = _FakeEngine()
    store = NamespacedStateStore(engine, api_key_id=1, vendor_id=2)
    await store.start(
        "sess-3", "user-3", 2, "role-3", "agent:custom", audience="property_manager",
    )
    assert engine.started_with["config_key"] == "agent:custom"


@pytest.mark.req(_REQ)
def test_config_key_for_helper():
    assert config_key_for("property_manager") == "agent:property_manager"
    assert config_key_for("tenant") == "agent:tenant"
    assert config_key_for(None) == DEFAULT_CONFIG_KEY
    assert config_key_for("") == DEFAULT_CONFIG_KEY
