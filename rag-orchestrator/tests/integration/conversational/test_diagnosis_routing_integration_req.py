"""integration:分類路由出口控制流（conversational-diagnosis 任務 6.2 / R1.1, R1.2, R1.4, R7.2, R7.5）。

跨模組驗 `handle_retrieval` 知識分支的分類路由（mock 檢索決策 + 對話引擎，不碰真實 DB/HTTP）：
  - 分類命中 → 進對話（`_conversational_respond(start_if_absent=True, config=diag_cfg)`），
    非 stream / stream 皆回該回應；不走 `_build_knowledge_response`。
  - 未命中 → 維持既有處理（落 `_build_knowledge_response`），不起對話。
  - 引擎降級（回 None）→ 落回既有知識/表單處理，不阻斷。
"""
import types
import pytest
from unittest.mock import AsyncMock, MagicMock

import routers.chat as chat
from services import conversational_config as cc
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.integration

DIAG_CATEGORY = "條件診斷:合約"
KB_SENTINEL = object()        # 代表既有 _build_knowledge_response 回應
CONV_SENTINEL = object()      # 代表 _conversational_respond 回應（JSON 或 StreamingResponse）


def _request(stream=False):
    return types.SimpleNamespace(
        skip_sop=False, stream=stream, session_id="s1", user_id="u1", vendor_id=7,
        message="我的合約狀態怪怪的", target_user="property_manager",
        include_debug_info=False, include_sources=False, mode="b2b")


def _req():
    req = MagicMock()
    req.app.state.db_pool = MagicMock()
    req.app.state.cache_service = MagicMock()
    req.app.state.sop_orchestrator = MagicMock()
    req.app.state.conversational_engine = MagicMock()
    return req


def _ctx():
    return types.SimpleNamespace(vendor_info={"vendor_id": 7, "is_active": True})


def _decision(categories):
    bk = {"id": 1, "similarity": 0.9, "categories": categories,
          "question_summary": "合約查詢", "action_type": "form_fill", "form_id": "contract_form"}
    return {"type": "knowledge", "reason": "kb hit",
            "knowledge_list": [bk], "knowledge_list_unfiltered": [bk]}


def _wire(monkeypatch, decision, conv_return=CONV_SENTINEL):
    """patch handle_retrieval 的協作者：檢索決策、知識回應、對話回應、分類設定查詢。"""
    monkeypatch.setattr(chat, "get_vendor_param_resolver", lambda: MagicMock())
    monkeypatch.setattr(chat, "_smart_retrieval_with_comparison",
                        AsyncMock(return_value=decision))
    build_kb = AsyncMock(return_value=KB_SENTINEL)
    monkeypatch.setattr(chat, "_build_knowledge_response", build_kb)
    conv = AsyncMock(return_value=conv_return)
    monkeypatch.setattr(chat, "_conversational_respond", conv)

    diag_cfg = ConversationalConfig(
        key="contract_diag", persona_role="property_manager",
        topic_scope={"mode": "category", "category": DIAG_CATEGORY})

    async def _fake_config_for_category(db_pool, category):
        return diag_cfg if category == DIAG_CATEGORY else None
    monkeypatch.setattr(cc, "config_for_category", _fake_config_for_category)
    return build_kb, conv, diag_cfg


# ── 分類命中 → 起對話（非 stream）──
@pytest.mark.req("conversational-diagnosis:1.1")
async def test_category_hit_routes_to_conversation(monkeypatch):
    build_kb, conv, diag_cfg = _wire(monkeypatch, _decision([DIAG_CATEGORY]))
    resp = await chat.handle_retrieval(_request(stream=False), _req(), _ctx())
    assert resp is CONV_SENTINEL
    build_kb.assert_not_awaited()              # 不走既有知識/表單
    conv.assert_awaited_once()
    # 起對話：start_if_absent=True、帶診斷設定（續對話會話建立的入口契約，R7.5）
    assert conv.await_args.kwargs["start_if_absent"] is True
    assert conv.await_args.kwargs["config"] is diag_cfg


# ── 分類命中（stream）→ 仍回 _conversational_respond 結果（契約一致）──
@pytest.mark.req("conversational-diagnosis:1.1")
async def test_category_hit_stream_contract(monkeypatch):
    _, conv, _ = _wire(monkeypatch, _decision([DIAG_CATEGORY]))
    resp = await chat.handle_retrieval(_request(stream=True), _req(), _ctx())
    assert resp is CONV_SENTINEL
    conv.assert_awaited_once()                 # stream 由 _conversational_respond 內部處理


# ── 未命中 → 維持既有知識/表單處理 ──
@pytest.mark.req("conversational-diagnosis:1.2")
async def test_category_miss_keeps_existing_handling(monkeypatch):
    build_kb, conv, _ = _wire(monkeypatch, _decision(["一般合約知識"]))
    resp = await chat.handle_retrieval(_request(stream=False), _req(), _ctx())
    assert resp is KB_SENTINEL
    conv.assert_not_awaited()                  # 未起對話
    build_kb.assert_awaited_once()


# ── 引擎降級（_conversational_respond 回 None）→ 落回既有處理，不阻斷 ──
@pytest.mark.req("conversational-diagnosis:7.2")
async def test_engine_degrade_falls_back_not_blocked(monkeypatch):
    build_kb, conv, _ = _wire(monkeypatch, _decision([DIAG_CATEGORY]), conv_return=None)
    resp = await chat.handle_retrieval(_request(stream=False), _req(), _ctx())
    assert resp is KB_SENTINEL                 # 降級後落回知識回應
    conv.assert_awaited_once()                 # 有嘗試起對話，但回 None
    build_kb.assert_awaited_once()
