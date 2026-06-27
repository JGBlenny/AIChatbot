"""補殘留：FormManager._resolve_selected_route 未覆蓋分支（spec unit-coverage-rebuild・任務 1・R2.3/2.4）。

主路徑（next_form_id 子樹／answer_kb 葉／未匹配 None／無路由 None）已由
test_form_option_routing_req.py 覆蓋；本檔只補既有未測的兩個分支：
- 型別容錯：collected_data 值與 option value 型別不同，仍以 str()==str() 匹配（intended，依現行碼）
- 終端欄位退取：末欄非 select 時反向取最後一個 select 欄位；全無 select → None（intended，依 docstring 步驟 1）

純方法、無 DB → unit。
"""
import pytest

from form_manager import FormManager

pytestmark = pytest.mark.unit


@pytest.fixture
def manager():
    return FormManager()


@pytest.mark.req("unit-coverage-rebuild:2.3")
def test_int_collected_matches_str_option_value(manager):
    """intended：collected_data 存 int、option value 為 str → str()==str() 匹配成功。"""
    schema = {
        "form_id": "f",
        "fields": [
            {"field_name": "n", "field_type": "select",
             "options": [{"label": "一", "value": "1", "next_form_id": "x"}]},
        ],
    }
    assert manager._resolve_selected_route(schema, {"n": 1}) == {"next_form_id": "x"}


@pytest.mark.req("unit-coverage-rebuild:2.3")
def test_str_collected_matches_int_option_value(manager):
    """intended：反向——collected_data 存 str、option value 為 int → 仍匹配。"""
    schema = {
        "form_id": "f",
        "fields": [
            {"field_name": "n", "field_type": "select",
             "options": [{"label": "九千", "value": 9001, "answer_kb": 5}]},
        ],
    }
    assert manager._resolve_selected_route(schema, {"n": "9001"}) == {"answer_kb": 5}


@pytest.mark.req("unit-coverage-rebuild:2.4")
def test_terminal_falls_back_to_last_select_when_last_field_not_select(manager):
    """intended：末欄非 select → 反向退取最後一個 select 欄位作終端。"""
    schema = {
        "form_id": "f",
        "fields": [
            {"field_name": "sel", "field_type": "select",
             "options": [{"label": "甲", "value": "a", "next_form_id": "go_a"}]},
            {"field_name": "note", "field_type": "text"},
        ],
    }
    # 以 select 欄位 'sel' 的值解析，而非末欄 text 'note'
    assert manager._resolve_selected_route(schema, {"sel": "a", "note": "略"}) == {"next_form_id": "go_a"}


@pytest.mark.req("unit-coverage-rebuild:2.4")
def test_no_select_field_returns_none(manager):
    """intended：表單全無 select 欄位 → None。"""
    schema = {
        "form_id": "f",
        "fields": [
            {"field_name": "a", "field_type": "text"},
            {"field_name": "b", "field_type": "number"},
        ],
    }
    assert manager._resolve_selected_route(schema, {"a": "x", "b": 1}) is None
