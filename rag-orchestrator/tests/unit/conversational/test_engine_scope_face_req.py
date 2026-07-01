"""unit:引擎中途切換 scope/face（mid-session-switch 方案B｜元件 3.2/3.5，護欄1/4）。

- scope='switch'（非待答中）→ 關會話、回 None（chat.py 重路由當前訊息，D2）。
- scope='switch' 但 pending_candidates 在 → 插點A 先行（護欄1：待答中不切）。
- face 在面向集合內 → 收斂 system_md 取當輪 face 的脈絡；越界/空 → 退回進入面向（護欄4）。
- state['face'] 記住當輪面向，下一輪 step 沿用。
mock 隔離，確定性 unit。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_engine import ConversationalEngine, _domain_faces
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


def _sysctx():
    # 依領域鍵回 "MD:<key>"，便於斷言取到哪個面向
    async def fn(pool, key=None):
        return f"MD:{key}"
    return AsyncMock(side_effect=fn)


def _engine(step_result):
    optimizer = MagicMock()
    optimizer.conversational_step.return_value = step_result
    optimizer.synthesize_presales_answer = MagicMock(return_value="ans")
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=optimizer, retriever=MagicMock(),
        get_system_context=_sysctx(),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=MagicMock())
    eng._save = AsyncMock()
    eng._close = AsyncMock()
    eng._ground_by_api = AsyncMock(return_value={"kind": "converge", "grounding": "G"})
    return eng


def _cfg(faces=None):
    ts = {"mode": "category", "category": "狀態判斷"}
    if faces is not None:
        ts["faces"] = faces
    return ConversationalConfig(
        key="contract_diag", persona_role="property_manager",
        grounding_scope={"select": "api", "endpoint": "e", "params": {},
                         "result_mapping": {"list_path": "data", "id_field": "id", "label_field": "title"}},
        topic_scope=ts)


class _FacePool:
    """mock category_config：parent_of[cat]=parent；children_of[parent]=[子分類…]。"""
    def __init__(self, parent_of=None, children_of=None):
        self.parent_of = parent_of or {}
        self.children_of = children_of or {}

    def acquire(self):
        po, co = self.parent_of, self.children_of

        class _Conn:
            async def fetchval(self, sql, *a):
                return po.get(a[0])

            async def fetch(self, sql, *a):
                return [{"category_value": c} for c in co.get(a[0], [])]

        conn = _Conn()

        class _Ctx:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *a):
                return False

        return _Ctx()


# ── 明列 topic_scope.faces 優先（不查 DB）──
@pytest.mark.req("mid-session-switch:3.5")
async def test_domain_faces_explicit_wins():
    assert await _domain_faces(MagicMock(), _cfg(faces=["狀態判斷", "違約金"])) == ["狀態判斷", "違約金"]


# ── 未明列 → 由 category_config 衍生（進入面向之母分類的所有子分類）──
@pytest.mark.req("mid-session-switch:3.5")
async def test_domain_faces_derived_from_category_config():
    pool = _FacePool(parent_of={"狀態判斷": "系統合約"},
                     children_of={"系統合約": ["狀態判斷", "違約金", "續約"]})
    assert await _domain_faces(pool, _cfg()) == ["狀態判斷", "違約金", "續約"]


# ── 衍生失敗（DB 例外）→ 回空（不啟用換面向，不阻斷）──
@pytest.mark.req("mid-session-switch:3.5")
async def test_domain_faces_derive_failure_returns_empty():
    class _BoomPool:
        def acquire(self):
            raise RuntimeError("db down")

    assert await _domain_faces(_BoomPool(), _cfg()) == []


# ── scope=switch（非待答中）→ 關會話、回 None（觸發重路由）──
@pytest.mark.req("mid-session-switch:3.3")
async def test_scope_switch_closes_and_reroutes():
    eng = _engine({"action": "ask", "scope": "switch", "next_question": "q", "extracted_fields": {}})
    eng.get_state = AsyncMock(return_value={"config_key": "contract_diag", "collected_fields": {}, "asked_count": 1})
    decision = await eng.prepare("s1", "u1", 7, "我這期帳單怎麼繳", config=_cfg())
    assert decision is None            # None → chat.py 落回重路由
    eng._close.assert_awaited_once()   # 會話已關


# ── 護欄1：pending_candidates 在時，走插點A（不讀 scope，不被切走）──
@pytest.mark.req("mid-session-switch:4.1")
async def test_pending_candidates_not_switched():
    eng = _engine({"action": "ask", "scope": "switch", "next_question": "q", "extracted_fields": {}})
    eng.get_state = AsyncMock(return_value={
        "config_key": "contract_diag", "collected_fields": {},
        "pending_candidates": [{"id": 11, "label": "A"}, {"id": 22, "label": "B"}]})
    decision = await eng.prepare("s1", "u1", 7, "2", config=_cfg())  # 選第 2 筆
    assert decision["kind"] == "converge"   # 候選選擇成立，未被 switch
    eng._close.assert_not_awaited()
    eng.optimizer.conversational_step.assert_not_called()  # 插點A 不跑 brain


# ── face 在集合內 → 收斂 system_md 取當輪 face 脈絡 + 記入 state ──
@pytest.mark.req("mid-session-switch:3.5")
async def test_face_switch_loads_that_face_context():
    eng = _engine({"action": "converge", "converge_kind": "answer",
                   "scope": "stay", "face": "違約金", "extracted_fields": {}})
    state = {"config_key": "contract_diag", "collected_fields": {"contract_ref": "678"}, "asked_count": 1}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "提前解約違約金怎算", config=_cfg(faces=["狀態判斷", "違約金"]))
    assert decision["kind"] == "converge"
    assert decision["system_md"] == "MD:違約金"   # 載違約金面向
    assert state["face"] == "違約金"


# ── 護欄4：face 越界 → 退回進入面向（topic_scope.category）──
@pytest.mark.req("mid-session-switch:4.1")
async def test_invalid_face_falls_back_to_entry():
    eng = _engine({"action": "converge", "converge_kind": "answer",
                   "scope": "stay", "face": "不存在面向", "extracted_fields": {}})
    state = {"config_key": "contract_diag", "collected_fields": {"contract_ref": "678"}, "asked_count": 1}
    eng.get_state = AsyncMock(return_value=state)
    decision = await eng.prepare("s1", "u1", 7, "x", config=_cfg(faces=["狀態判斷", "違約金"]))
    assert decision["system_md"] == "MD:狀態判斷"   # 退回進入面向
    assert state["face"] == "狀態判斷"


# ── state['face'] 沿用：上一輪面向作為本輪 step 的脈絡鍵 ──
@pytest.mark.req("mid-session-switch:3.2")
async def test_previous_face_used_for_step_context():
    eng = _engine({"action": "ask", "scope": "stay", "next_question": "q", "extracted_fields": {}})
    eng.get_state = AsyncMock(return_value={
        "config_key": "contract_diag", "collected_fields": {}, "asked_count": 1, "face": "違約金"})
    await eng.prepare("s1", "u1", 7, "再問一下", config=_cfg(faces=["狀態判斷", "違約金"]))
    # step 的 system_md 應以上一輪面向（違約金）載入
    args, kwargs = eng.optimizer.conversational_step.call_args
    assert args[1] == "MD:違約金"
