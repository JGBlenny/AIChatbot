"""unit:智能檢索決策/串流兜底修正(retrieval-fixes #2 門檻一致、#3 串流富兜底)。

- #2 _smart_retrieval_with_comparison:決策門檻應與檢索門檻一致(同讀 KB_SIMILARITY_THRESHOLD,
  預設 0.55),否則 [0.55,0.6) 的知識檢索得到卻永遠選不上、甚至誤判 none。
- #3 stream_synthesis_response:無 ≥0.8 高品質知識時,應走與非串流一致的富兜底
  (_handle_no_knowledge_found),而非回裸句「我目前沒有找到符合您問題的資訊。」。

mock IO 邊界(_retrieve_knowledge / embedding / sop_orchestrator / _handle_no_knowledge_found)→ 確定性 unit。
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import routers.chat as chat
from routers.chat import VendorChatRequest, VendorChatResponse

pytestmark = pytest.mark.unit


def _req(**state):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(**state)))


# ─────────────────────────── #2 決策門檻一致 ───────────────────────────

@pytest.mark.req("retrieval-fixes:2")
async def test_borderline_knowledge_selected_not_dropped_to_none(monkeypatch):
    """無 SOP + 知識 0.58(落在 [0.55,0.6)):決策應為 knowledge,而非誤判 none。"""
    # 邊界:embedding 與 query rewrite 不打外部
    monkeypatch.setenv("KB_SIMILARITY_THRESHOLD", "0.55")
    monkeypatch.setattr(chat, "get_embedding_client",
                        lambda: SimpleNamespace(get_embedding=AsyncMock(return_value=[0.1, 0.2, 0.3])))
    monkeypatch.setattr(chat, "_retrieve_knowledge",
                        AsyncMock(return_value=([{"id": 1, "similarity": 0.58, "answer": "a"}], [])))

    sop_orch = SimpleNamespace(process_message=AsyncMock(return_value={"has_sop": False}))
    request = VendorChatRequest(message="租金怎麼算", mode="b2c", vendor_id=2, target_user="tenant")

    decision = await chat._smart_retrieval_with_comparison(
        request=request, intent_result={}, sop_orchestrator=sop_orch, resolver=MagicMock())

    assert decision["type"] == "knowledge", f"0.58 知識應被選,實得 {decision['type']}/{decision.get('reason')}"


# ─────────────────────────── #3 串流富兜底 ───────────────────────────

@pytest.mark.req("retrieval-fixes:3")
async def test_stream_low_quality_uses_rich_fallback_not_bare_sentence(monkeypatch):
    """串流時無 ≥0.8 知識 → 走 _handle_no_knowledge_found 富兜底,不回裸句。"""
    async def _fake_fallback(*a, **k):
        return VendorChatResponse(answer="RICH-FALLBACK-SENTINEL", mode="b2c", timestamp="t")

    monkeypatch.setenv("HIGH_QUALITY_THRESHOLD", "0.8")  # 固定門檻,使 0.7 知識確定落入空兜底分支
    monkeypatch.setattr(chat, "_handle_no_knowledge_found", _fake_fallback)

    req = _req(llm_answer_optimizer=MagicMock(), confidence_evaluator=MagicMock())
    request = VendorChatRequest(message="冷門問題", mode="b2c", vendor_id=2, target_user="tenant", stream=True)
    kl = [{"id": 1, "similarity": 0.7, "answer": "x", "question_summary": "q"}]  # 全 < 0.8

    events = [ev async for ev in chat.stream_synthesis_response(
        request, req, {}, kl, MagicMock(), {"name": "X"}, MagicMock(), decision={"type": "knowledge"})]
    text = "".join(events)

    assert "RICH-FALLBACK-SENTINEL" in text, "應輸出富兜底答案"
    assert "我目前沒有找到符合您問題的資訊" not in text, "不應再出現裸句兜底"
