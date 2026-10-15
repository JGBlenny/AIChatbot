"""unit：2026-10-15 正式機部署後的兩個修正。

1. 統計三支（`jgb2.stats.*`，jgb2-req#16～#18）接真 JGB（`use_mock=False`）時 JGB 尚未開放：
   ⛔ 發請求，回「尚未開放」標記；runtime 以程式固定句 `NOT_SUPPORTED_TEXT` 結束回合
   （正式機實測：打到不存在的端點後被模型改成轉人或反問「想處理哪一件事？」）。
2. 細目索引開機 prepare 逾時後，改在背景重建（正式機 embedding 約 9.5 次／秒，2,082 項要
   3～4 分鐘，開機 60 秒必逾時且原本不再重試）。
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from services.agent.tools import jgb2 as jgb2_tools
from services.agent.tools import jgb2_stats as S

from tests.unit.agent.test_not_found_exit_req import _pm, _run

pytestmark = [pytest.mark.unit, pytest.mark.req("agentic-mcp-orchestration:R4.2")]

_ARGS = {
    "jgb2.stats.unpaid_bills": {"scope": "this_month"},
    "jgb2.stats.in_progress_repairs": {},
    "jgb2.stats.expiring_contracts": {"months": 3},
}


class _RealApi:
    """接真 JGB 的替身：`use_mock=False`，三支統計方法被呼叫就記錄（應為 0 次）。"""

    use_mock = False

    def __init__(self):
        self.get_unpaid_bill_summary = AsyncMock(return_value={"success": False})
        self.get_in_progress_repairs = AsyncMock(return_value={"success": False})
        self.get_expiring_contracts = AsyncMock(return_value={"success": False})

    def calls(self):
        return (self.get_unpaid_bill_summary.await_count + self.get_in_progress_repairs.await_count
                + self.get_expiring_contracts.await_count)


@pytest.fixture()
def real_api(monkeypatch):
    api = _RealApi()
    monkeypatch.setattr(jgb2_tools, "_api_singleton", api)
    return api


# ── 1a：工具層——不發請求、回尚未開放標記 ───────────────────────────────────
@pytest.mark.parametrize("spec_handler", S.STATS_SPECS, ids=lambda sh: sh[0]["name"])
async def test_stats_on_real_api_do_not_call_upstream(real_api, spec_handler):
    spec, handler = spec_handler
    out = await handler(_pm(), _ARGS[spec["name"]])
    assert out["data"]["not_supported"] is True
    assert out["text_for_model"] == S.NOT_SUPPORTED_TEXT
    assert real_api.calls() == 0


async def test_stats_on_mock_still_reach_the_handler(monkeypatch):
    """正對照：`use_mock=True` ⇒ 照舊打上游（這裡上游回失敗 ⇒ F7 固定句，不是尚未開放）。"""
    api = _RealApi()
    api.use_mock = True
    monkeypatch.setattr(jgb2_tools, "_api_singleton", api)
    spec, handler = S.STATS_SPECS[0]
    out = await handler(_pm(), _ARGS[spec["name"]])
    assert api.get_unpaid_bill_summary.await_count == 1
    assert "not_supported" not in out["data"]


# ── 1b：runtime——程式固定句結束回合，⛔ 交模型 ──────────────────────────────
@pytest.mark.parametrize("name", sorted(_ARGS))
async def test_runtime_answers_not_supported_text_without_the_model(real_api, name):
    res, reg, provider = await _run(_pm(), [(name, _ARGS[name])])
    assert reg.results[-1][0] == name
    assert res.kind == "answer"
    assert res.answer == S.NOT_SUPPORTED_TEXT
    assert "jgb2_stats_not_supported_exit" in res.trace.violations
    assert len(provider.calls) == 1   # 只有第一步（叫工具）；模型反問沒被叫到
    assert real_api.calls() == 0


# ── 2：細目索引背景重建 ─────────────────────────────────────────────────────
class _SlowIndex:
    def __init__(self, fail=False):
        self.state = "absent"
        self.fail = fail
        self.calls = 0

    async def prepare(self, canon):
        self.calls += 1
        await asyncio.sleep(0)
        if self.fail:
            raise RuntimeError("embedding down")
        self.state = "ready"


async def test_background_prepare_makes_the_index_ready():
    import app as app_mod
    idx = _SlowIndex()
    await app_mod._prepare_index_in_background(idx, object())
    assert (idx.calls, idx.state) == (1, "ready")


async def test_background_prepare_failure_is_fail_soft():
    import app as app_mod
    idx = _SlowIndex(fail=True)
    await app_mod._prepare_index_in_background(idx, object())   # ⛔ raise
    assert (idx.calls, idx.state) == (1, "absent")


def test_background_timeout_is_longer_than_the_startup_timeout():
    import app as app_mod
    from services.agent.canon.fine_index import PREPARE_TOTAL_TIMEOUT_S
    assert app_mod.INDEX_BACKGROUND_PREPARE_TIMEOUT_S >= 300 > PREPARE_TOTAL_TIMEOUT_S


# ── 3：新寫入動作（#19～#21）接真 JGB ⇒ 不出卡、程式固定句 ─────────────────────
from services.agent.tools import confirm as C  # noqa: E402

_WRITE_PAYLOADS = {
    "estate_create": {"action": "estate_create", "title": "測試物件", "city": "台北市",
                      "district": "大安區", "address": "測試路1號", "use_for": "residential"},
    "contract_create": {"action": "contract_create", "estate_name": "測試物件",
                        "date_start": "2026-11-01", "date_end": "2027-10-31", "rent": 30000,
                        "to_user_email": "x@example.com"},
    "manual_bill_create": {"action": "manual_bill_create", "contract_id": 79994, "title": "清潔費",
                           "total": 1200, "date_expire": "2026-12-20"},
}


def _confirm(payload):
    return ("confirm.request", {"summary": "建立", "payload": json.dumps(payload, ensure_ascii=False)})


@pytest.mark.parametrize("action", sorted(_WRITE_PAYLOADS))
async def test_new_write_actions_on_real_api_answer_not_supported_without_card(real_api, action):
    res, reg, provider = await _run(_pm(), [_confirm(_WRITE_PAYLOADS[action])])
    name, result = reg.results[-1]
    assert name == "confirm.request" and result.data.get("not_supported") is True
    assert "card" not in result.data and "pending_id" not in result.data
    assert res.kind == "answer" and res.answer == C.WRITE_NOT_SUPPORTED_TEXT
    assert "jgb2_stats_not_supported_exit" in res.trace.violations
    assert len(provider.calls) == 1


def test_write_guard_only_covers_the_three_new_actions():
    assert C.WRITE_NOT_SUPPORTED_ACTIONS == {"estate_create", "contract_create", "manual_bill_create"}
    assert "repair_create" not in C.WRITE_NOT_SUPPORTED_ACTIONS
    assert "bill_due_extend" not in C.WRITE_NOT_SUPPORTED_ACTIONS
