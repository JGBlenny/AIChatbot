"""補測試：表單／form-chaining／選項路由（spec testing-traceability・任務 8・R5.4）。

聚焦 FormManager._resolve_selected_route 的 per-option 決策樹路由與葉答案、守衛
（純方法、無 DB → unit）。
"""
import pytest

from form_manager import FormManager

pytestmark = pytest.mark.unit


@pytest.mark.req("testing-traceability:5.4")
def test_chain_depth_limit_is_bounded():
    """form-chaining 深度上限存在且為正整數（防無限串接，R6.1）。"""
    assert isinstance(FormManager.MAX_CHAIN_DEPTH, int)
    assert FormManager.MAX_CHAIN_DEPTH >= 1


@pytest.fixture
def manager():
    return FormManager()


def _select_schema(options):
    return {
        "form_id": "presales_intro",
        "fields": [
            {"field_name": "identity", "field_type": "select",
             "prompt": "您是？", "options": options},
        ],
    }


@pytest.mark.req("testing-traceability:5.4")
def test_option_routes_to_next_form_subtree(manager):
    """per-option：選項帶 next_form_id → 回子樹路由（form-chaining 串接）。"""
    schema = _select_schema([
        {"label": "個人房東", "value": "individual", "next_form_id": "presales_individual_units"},
        {"label": "公司團隊", "value": "team"},
    ])
    route = manager._resolve_selected_route(schema, {"identity": "individual"})
    assert route == {"next_form_id": "presales_individual_units"}


@pytest.mark.req("testing-traceability:5.4")
def test_option_routes_to_leaf_answer(manager):
    """per-option：選項帶 answer_kb → 回葉答案路由。"""
    schema = _select_schema([
        {"label": "公司團隊", "value": "team", "answer_kb": 9001},
    ])
    route = manager._resolve_selected_route(schema, {"identity": "team"})
    assert route == {"answer_kb": 9001}


@pytest.mark.req("testing-traceability:5.4")
def test_unknown_option_value_returns_none(manager):
    """守衛：未匹配任何選項 → None（不誤導向）。"""
    schema = _select_schema([
        {"label": "個人房東", "value": "individual", "next_form_id": "x"},
    ])
    assert manager._resolve_selected_route(schema, {"identity": "unknown"}) is None


@pytest.mark.req("testing-traceability:5.4")
def test_option_without_route_returns_none(manager):
    """守衛：匹配到的選項無 next_form_id/answer_kb → None（一般表單流程）。"""
    schema = _select_schema([
        {"label": "個人房東", "value": "individual"},
    ])
    assert manager._resolve_selected_route(schema, {"identity": "individual"}) is None
