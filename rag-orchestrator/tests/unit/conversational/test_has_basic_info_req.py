"""unit:設定驅動收斂門檻（conversational-diagnosis 任務 2 / R2.1, R2.5, R6.1）。

`_has_basic_info(fields, config)`：有 grounding_scope.required_slots → 全部到齊才足夠；
無 → 維持售前預設（identity + (scale|pain)）。純函式。
"""
import pytest

from services.conversational_engine import _has_basic_info
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


def _cfg(required=None):
    gs = {"required_slots": required} if required else {}
    return ConversationalConfig(key="x", grounding_scope=gs)


# ── required_slots 模式（診斷面向）──
@pytest.mark.req("conversational-diagnosis:2.1")
def test_required_slot_missing_insufficient():
    assert _has_basic_info({}, _cfg(["contract_ref"])) is False


@pytest.mark.req("conversational-diagnosis:2.1")
def test_required_slot_present_sufficient():
    assert _has_basic_info({"contract_ref": "基隆"}, _cfg(["contract_ref"])) is True


@pytest.mark.req("conversational-diagnosis:2.1")
def test_required_slots_partial_insufficient():
    assert _has_basic_info({"contract_ref": "基隆"}, _cfg(["contract_ref", "year"])) is False


# ── 無 required_slots → 售前預設（R2.5 向後相容）──
@pytest.mark.req("conversational-diagnosis:2.5")
def test_no_required_slots_presales_insufficient():
    assert _has_basic_info({"identity": "個人房東"}, _cfg()) is False  # 缺 scale/pain


@pytest.mark.req("conversational-diagnosis:2.5")
def test_no_required_slots_presales_sufficient():
    assert _has_basic_info({"identity": "個人房東", "scale": "30"}, _cfg()) is True


@pytest.mark.req("conversational-diagnosis:2.5")
def test_config_none_uses_presales_default():
    assert _has_basic_info({"identity": "x", "pain": "漏水"}, None) is True
    assert _has_basic_info({}, None) is False
