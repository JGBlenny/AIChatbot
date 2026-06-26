"""重建：ConversationalEngine.is_active_state（spec unit-coverage-rebuild・任務 4・R5.1）。

純判斷、零相依 → unit。engine 以全 mock 依賴實例化（is_active_state 不觸及任何依賴）。
註：原 R5.2/5.3/5.4（prepare／grounding）依設計審查 Issue 1 移出 unit 範圍（→ integration 軌道）。
"""
import pytest
from unittest.mock import MagicMock

from conversational_engine import ConversationalEngine, CONVERSATIONAL_FORM_ID

pytestmark = pytest.mark.unit


@pytest.fixture
def engine():
    # 五依賴皆 mock；is_active_state 為純判斷，不會用到它們
    return ConversationalEngine(
        db_pool=MagicMock(),
        optimizer=MagicMock(),
        retriever=MagicMock(),
        get_system_context=MagicMock(),
        rules_loader=MagicMock(),
    )


@pytest.mark.req("unit-coverage-rebuild:5.1")
def test_active_when_form_id_is_conversational(engine):
    assert engine.is_active_state({"form_id": CONVERSATIONAL_FORM_ID}) is True


@pytest.mark.req("unit-coverage-rebuild:5.1")
def test_inactive_when_none(engine):
    assert engine.is_active_state(None) is False


@pytest.mark.req("unit-coverage-rebuild:5.1")
def test_inactive_when_empty_dict(engine):
    assert engine.is_active_state({}) is False


@pytest.mark.req("unit-coverage-rebuild:5.1")
def test_inactive_when_other_form(engine):
    assert engine.is_active_state({"form_id": "rent_info_form_v2"}) is False
