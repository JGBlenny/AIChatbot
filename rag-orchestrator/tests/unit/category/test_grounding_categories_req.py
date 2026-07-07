"""補測試：grounding 主題接地改用多值欄位 categories（spec category-multi-select・任務 3.1/3.2・需求 3.1, 3.3, 3.4）。

離線 unit（mock db_pool）：捕捉 `_grounding_by_category` 傳入 conn.fetch 的 SQL 字串，
驗證述詞由單數 `category = $1` 改為多值 `$1 = ANY(categories)`，且 target_user 角色過濾保留。
此為 SQL 構建確定性 unit（mutation 風格：改錯述詞即紅）。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.conversational_engine import ConversationalEngine

pytestmark = pytest.mark.unit


def _engine(db_pool):
    return ConversationalEngine(
        db_pool=db_pool,
        optimizer=MagicMock(),
        retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="md"),
        rules_loader=AsyncMock(return_value="規則"),
    )


@pytest.mark.req("category-multi-select:3.1")
async def test_grounding_by_category_uses_array_any_predicate(mock_db_pool):
    """無 target_user：述詞用 $1 = ANY(categories)，不再用 category = $1。"""
    captured = {}

    async def fake_fetch(sql, *args):
        captured["sql"] = sql
        captured["args"] = args
        return [{"answer": "A1"}, {"answer": "A2"}]

    mock_db_pool._conn.fetch = fake_fetch
    eng = _engine(mock_db_pool)

    out = await eng._grounding_by_category("退租結算")

    assert "= ANY(categories)" in captured["sql"]
    assert "category = $1" not in captured["sql"]
    # 與 admin 篩選一致：父層展開（選父層→撈其子分類）
    assert "parent_value" in captured["sql"]
    assert out == "A1\n\nA2"


@pytest.mark.req("category-multi-select:3.1")
async def test_grounding_by_category_with_target_user_keeps_role_filter(mock_db_pool):
    """有 target_user：仍用 categories 多值述詞，且保留 target_user 角色過濾。"""
    captured = {}

    async def fake_fetch(sql, *args):
        captured["sql"] = sql
        captured["args"] = args
        return [{"answer": "X"}]

    mock_db_pool._conn.fetch = fake_fetch
    eng = _engine(mock_db_pool)

    out = await eng._grounding_by_category("方案", target_user="prospect")

    assert "= ANY(categories)" in captured["sql"]
    assert "category = $1" not in captured["sql"]
    assert "target_user" in captured["sql"]
    assert out == "X"
