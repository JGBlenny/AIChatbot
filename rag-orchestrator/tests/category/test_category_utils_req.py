"""補測試：主題分類寫入正規化 to_categories（spec category-multi-select・任務 4.1/4.3・需求 1.1, 1.3, 1.4, 2.2, 6.3）。

純函式 unit：單值轉陣列、多值優先、保留值剔除、去重保序、空值→空陣列。
"""
import pytest

from services.category_utils import RESERVED_CATEGORIES, to_categories

pytestmark = pytest.mark.unit


@pytest.mark.req("category-multi-select:1.1")
def test_single_value_to_single_element_array():
    assert to_categories("退租結算") == ["退租結算"]


@pytest.mark.req("category-multi-select:1.3")
def test_empty_and_none_yield_empty_list():
    assert to_categories(None) == []
    assert to_categories("") == []
    assert to_categories("   ") == []
    assert to_categories(None, []) == []


@pytest.mark.req("category-multi-select:2.2")
def test_reserved_values_are_stripped():
    # 保留值不得進入主題分類陣列
    assert to_categories("對話規則") == []
    assert to_categories("系統脈絡") == []
    assert to_categories(None, ["對話規則", "退租結算"]) == ["退租結算"]
    # 常數齊備
    assert RESERVED_CATEGORIES == frozenset({"對話規則", "系統脈絡"})


@pytest.mark.req("category-multi-select:6.3")
def test_multi_value_takes_priority_over_single():
    assert to_categories("a", ["b", "c"]) == ["b", "c"]
    # categories 為空 → 回退單值
    assert to_categories("x", []) == ["x"]


@pytest.mark.req("category-multi-select:1.4")
def test_dedupe_preserves_order_and_trims():
    assert to_categories(None, ["b", "b", "a", "  a  "]) == ["b", "a"]
    assert to_categories(None, ["帳務", "", "  ", "合約"]) == ["帳務", "合約"]
