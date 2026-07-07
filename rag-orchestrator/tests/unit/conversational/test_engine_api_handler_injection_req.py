"""unit:引擎注入 api_handler（conversational-diagnosis 任務 3 / R3.1, R7.3）。

`ConversationalEngine.__init__` 接受可選 `api_handler` 並保存；不傳時為 None（向後相容，
既有售前 stub 以 5 參數建構仍可運作）。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.conversational_engine import ConversationalEngine

pytestmark = pytest.mark.unit


def _engine(**extra):
    return ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(), rules_loader=AsyncMock(), **extra)


@pytest.mark.req("conversational-diagnosis:3.1")
def test_api_handler_injected_and_stored():
    h = object()
    eng = _engine(api_handler=h)
    assert eng.api_handler is h


@pytest.mark.req("conversational-diagnosis:3.1")
def test_api_handler_optional_defaults_none():
    eng = _engine()  # 不傳 → 向後相容（既有 5 參數建構）
    assert eng.api_handler is None
