"""重建：APICallHandler._handle_branch_answer 四分支（spec unit-coverage-rebuild・任務 5・R6.1/6.2）。

選項分歧知識回覆：依使用者選擇值對照知識 id 回答；對照不到/查無/例外 → fallback。
以既有 conftest mock_db_pool 注入 fetchrow。async + DB mock → unit（不打真實 DB）。
fallback 行為為 docstring 明示 → intended。
"""
import pytest
from unittest.mock import AsyncMock

from services.api_call_handler import APICallHandler

pytestmark = pytest.mark.unit


@pytest.mark.req("unit-coverage-rebuild:6.1")
async def test_branch_answer_hit_returns_kb_answer(mock_db_pool):
    """mapping 命中且 kb 存在 → 回該知識 answer。"""
    mock_db_pool._conn.fetchrow = AsyncMock(return_value={"answer": "藍新金流設定說明…"})
    handler = APICallHandler(db_pool=mock_db_pool)
    out = await handler._handle_branch_answer(
        choice="newebpay",
        mapping={"newebpay": 3551, "sinopac": 3553},
        fallback="找不到說明",
    )
    assert out == {"message": "藍新金流設定說明…"}


@pytest.mark.req("unit-coverage-rebuild:6.2")
async def test_branch_answer_kb_missing_returns_fallback(mock_db_pool):
    """intended：mapping 命中但知識不存在/停用（fetchrow None）→ fallback。"""
    mock_db_pool._conn.fetchrow = AsyncMock(return_value=None)
    handler = APICallHandler(db_pool=mock_db_pool)
    out = await handler._handle_branch_answer(
        choice="newebpay",
        mapping={"newebpay": 3551},
        fallback="找不到說明",
    )
    assert out == {"message": "找不到說明"}


@pytest.mark.req("unit-coverage-rebuild:6.2")
async def test_branch_answer_no_mapping_returns_fallback(mock_db_pool):
    """intended：choice 無對照（mapping 不含該鍵）→ fallback，不查 DB。"""
    handler = APICallHandler(db_pool=mock_db_pool)
    out = await handler._handle_branch_answer(
        choice="unknown_gateway",
        mapping={"newebpay": 3551},
        fallback="找不到說明",
    )
    assert out == {"message": "找不到說明"}


@pytest.mark.req("unit-coverage-rebuild:6.2")
async def test_branch_answer_default_fallback_when_none_choice(mock_db_pool):
    """intended：choice=None 且無 fallback → 用內建預設 fallback 文字。"""
    handler = APICallHandler(db_pool=mock_db_pool)
    out = await handler._handle_branch_answer(choice=None, mapping={"newebpay": 3551})
    assert "請聯繫客服" in out["message"]


@pytest.mark.req("unit-coverage-rebuild:6.2")
async def test_branch_answer_db_exception_returns_fallback(mock_db_pool):
    """intended：DB 查詢拋例外 → 不外拋，回 fallback。"""
    mock_db_pool._conn.fetchrow = AsyncMock(side_effect=RuntimeError("db down"))
    handler = APICallHandler(db_pool=mock_db_pool)
    out = await handler._handle_branch_answer(
        choice="newebpay",
        mapping={"newebpay": 3551},
        fallback="找不到說明",
    )
    assert out == {"message": "找不到說明"}
