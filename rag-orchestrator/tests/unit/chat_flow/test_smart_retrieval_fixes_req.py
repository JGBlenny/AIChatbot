"""unit:串流兜底修正(retrieval-fixes #3 串流富兜底)。

- #3 stream_synthesis_response:無高品質知識時,應走與非串流一致的富兜底
  (_handle_no_knowledge_found),而非回裸句「我目前沒有找到符合您問題的資訊。」。

註:原 #2(決策門檻對齊)已 revert——實際配置 KB_SIMILARITY_THRESHOLD=0.65 已 ≥ 舊決策門檻 0.6,
   不存在「被浪費的 0.55–0.6 知識」,該修正為 no-op 故移除。

mock IO 邊界(_handle_no_knowledge_found)→ 確定性 unit。
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import routers.chat as chat
from routers.chat import VendorChatRequest, VendorChatResponse

pytestmark = pytest.mark.unit


def _req(**state):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(**state)))


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
