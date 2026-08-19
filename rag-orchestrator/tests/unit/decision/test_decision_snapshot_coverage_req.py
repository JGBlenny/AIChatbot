"""unit：決策快照全覆蓋（任務 0.1｜R8.3「每輪」）。

契約（D-19）：
- 快照於 **dispatcher 唯一出口**組裝落地，各階段只「貢獻」片段；
- **未貢獻的路徑不得靜默缺席**——落一筆帶 `path` 與 `incomplete: true` 的最小快照；
- 面向內續輪（現況 0% 覆蓋，即 #07 一次黏著五輪全毀的現場）必須貢獻 `facet_event='stay'`
  與面向識別，否則逃生門（P1）上線後無從歸因療效；
- 快取命中輪同樣落快照（否則「快取兩軌路由一致」永遠驗不了）。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

import routers.chat as chat
from services.decision_layer import DECISION_RULE_VERSION

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_ctx(monkeypatch):
    import services.usage_metering as um
    monkeypatch.setenv("USAGE_METERING_ENABLED", "true")
    um._ctx.set(None)
    yield
    um._ctx.set(None)


def _begin():
    import services.usage_metering as um
    um.begin({"message": "查詢帳單目前的狀態", "vendor_id": 2, "mode": "b2b",
              "target_user": "property_manager", "session_id": "u_cov_1",
              "role_id": "20151"})
    return um


# ── 出口組裝：沒有任何階段貢獻 → 落最小快照，不得靜默缺席 ──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_exit_emits_minimal_snapshot_when_nothing_contributed():
    um = _begin()
    chat._finalize_decision_snapshot(path="handle_cache")
    snap = um._ctx.get().decision_snapshot
    assert snap is not None, "未貢獻的路徑必須留下最小快照（可觀測缺口）"
    assert snap["path"] == "handle_cache"
    assert snap["incomplete"] is True
    assert snap["rule_version"] == DECISION_RULE_VERSION


# ── 出口組裝：已有貢獻 → 只補 path，不得覆蓋既有內容、不得標 incomplete ──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_exit_preserves_contributed_snapshot():
    um = _begin()
    chat._meter_decision(snapshot={"verdict": "knowledge", "kb_top1_final": 0.87,
                                   "decision_case": "b2b_knowledge_only"})
    chat._finalize_decision_snapshot(path="handle_retrieval")
    snap = um._ctx.get().decision_snapshot
    assert snap["verdict"] == "knowledge"
    assert snap["kb_top1_final"] == 0.87
    assert snap["path"] == "handle_retrieval"
    assert snap.get("incomplete") is not True


# ── 缺必要欄位的貢獻仍標 incomplete（半套貢獻不算完整）──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_exit_marks_incomplete_when_required_fields_missing():
    um = _begin()
    chat._meter_decision(snapshot={"note": "只貢獻了無關欄位"})
    chat._finalize_decision_snapshot(path="handle_image")
    snap = um._ctx.get().decision_snapshot
    assert snap["incomplete"] is True, "缺 verdict → 視為不完整，讓缺口看得見"
    assert snap["path"] == "handle_image"


# ── 非計量路徑（ctx None）→ 靜默不拋 ──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_exit_silent_without_context():
    import services.usage_metering as um
    assert um._ctx.get() is None
    chat._finalize_decision_snapshot(path="handle_retrieval")


# ── 出口只組裝一次：重複呼叫不得產生 prior 疊加污染 ──
@pytest.mark.req("retrieval-decision-layer:8.3")
def test_exit_is_idempotent():
    um = _begin()
    chat._meter_decision(snapshot={"verdict": "knowledge"})
    chat._finalize_decision_snapshot(path="handle_retrieval")
    chat._finalize_decision_snapshot(path="handle_retrieval")
    snap = um._ctx.get().decision_snapshot
    assert "prior" not in snap, "同一出口重複組裝不得製造假的同輪擺盪紀錄"


# ════════════════════════════════════════════════════════════
# 面向內續輪：現況 0% 覆蓋的缺口（#07 黏著五輪的現場）
# ════════════════════════════════════════════════════════════

@pytest.mark.req("retrieval-decision-layer:8.3")
async def test_facet_continuation_contributes_stay(monkeypatch):
    um = _begin()
    ctx = chat.ChatRequestContext()
    # 真實形狀：config_key 在 collected_data 內（form_sessions 慣例），非 state 頂層
    ctx.session_state = {"form_id": "conversational", "state": "COLLECTING",
                         "collected_data": {"config_key": "bill_diagnosis"},
                         "user_turns": 3}
    req = MagicMock()
    req.app.state.conversational_engine = MagicMock()
    monkeypatch.setattr(chat, "_conversational_respond",
                        AsyncMock(return_value=MagicMock(name="resp")))
    request = MagicMock()
    request.message = "我要如何設定線上金流？"
    request.session_id = "u_cov_1"
    request.image_urls = None

    resp = await chat.handle_conversational_session(request, req, ctx)

    assert resp is not None
    snap = um._ctx.get().decision_snapshot
    assert snap is not None, "面向續輪必須落快照——這是 #07 黏著的歸因現場"
    assert snap["routing_verdict"] == "stay_facet"
    assert snap["facet_key"] == "bill_diagnosis"
    assert um._ctx.get().facet_event == "stay"


# ── 續輪取消分支同樣要落快照（退出也是決策）──
@pytest.mark.req("retrieval-decision-layer:8.3")
async def test_facet_cancel_contributes_exit(monkeypatch):
    um = _begin()
    ctx = chat.ChatRequestContext()
    ctx.session_state = {"form_id": "conversational", "state": "COLLECTING",
                         "collected_data": {"config_key": "bill_diagnosis"}}
    req = MagicMock()
    req.app.state.conversational_engine._close = AsyncMock()
    monkeypatch.setattr(chat, "_finalize_response", lambda r, rq, rr: r)
    request = MagicMock()
    request.message = "取消"
    request.session_id = "u_cov_1"
    request.vendor_id = 2
    request.mode = "b2b"

    await chat.handle_conversational_session(request, req, ctx)

    assert um._ctx.get().facet_event == "exit_user_cancel"
