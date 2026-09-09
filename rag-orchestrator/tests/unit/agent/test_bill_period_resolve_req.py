"""unit：期別解析（`bill_period.parse_period`）與缺帳單編號時的帳單對帳
（`confirm.request` 的 `bill_due_extend` 三分支）。

Plan `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-walkthrough-fixes-batch6-20260910.md`
單元 A｜病灶＝line-bot 2026-09-10 回報 #2（模型為了帳單編號反問三輪，房東不會講編號）。

離線：**真 `JGBSystemAPI` ＋替身 transport**（`tests/fixtures/jgb/regression_vendor4.json`，
conftest 以 `JGB_MOCK_FIXTURE` 指過去）＋假 db pool。⛔ 不用假 API：這一段驗的正是
「同一條 keyword 可見性路徑取回來的列被怎麼篩」，假 API 會讓那段程式根本不執行。

⚠️ 每個「對不到／沒出卡」的斷言旁都放一個**已知必然存在**的正對照組
   （同一支函式、同一份 fixture，只差一個條件），工具或條件壞掉時要看得出來是
   工具壞了，不是目標不存在。
"""
from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock

import pytest

from services.agent import bill_period
from services.agent.bill_period import PeriodSpec, parse_period
from services.agent.identity import Identity
from services.agent.tools import action as action_tools
from services.agent.tools import confirm as confirm_tools
from services.agent.tools import jgb2 as jgb2_tools
from services.agent.tools.confirm import BILL_MATCH_HINT, confirm_request
from services.agent.tools.registry import ToolRegistry
from services.jgb import bills as _bills
from services.jgb_system_api import JGBSystemAPI

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:batch6-A"),
]

#: 凍結時鐘：走查那一句（「九月的房租…晚三天」）發生在 2026-09-10。
_TODAY = date(2026, 9, 10)

#: 替身 fixture 的既有資料（`tests/fixtures/jgb/regression_vendor4.json`）：
#:   756248  基隆獨立共生公寓雅房  status 2（待繳費）  date_expire 20260901  期間 0901–0930
#:   756242  基隆獨立共生公寓雅房  status 16（已繳費）  date_expire 20260601  期間 0601–0630
#: 兩列同物件、不同期別、不同狀態 ⇒ 期別篩選寫錯就會對到另一張（結果集不同）。
_ESTATE = "基隆獨立共生公寓雅房"
_SEP_BILL = "756248"
_JUN_BILL = "756242"
#: 同一份 fixture 裡另一個**多筆**物件（測試物件：769258／769246／769249）。
_MULTI_ESTATE = "測試物件"
#: 兩列的可見 viewer（`bill_visibility`）。
_USER = "12291"
_ROLE = "20151"


@pytest.fixture(autouse=True)
def _freeze_today(monkeypatch):
    """唯一時鐘（`bills._today()`）——⛔ 測試不自己讀 `date.today()`。"""
    monkeypatch.setattr(_bills, "_today", lambda: _TODAY)


@pytest.fixture()
def api(monkeypatch) -> JGBSystemAPI:
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    instance = JGBSystemAPI()
    monkeypatch.setattr(jgb2_tools, "_api_singleton", instance)
    return instance


def _identity(**over) -> Identity:
    base = dict(vendor_id=4, target_user="property_manager", mode="b2b",
                role_id=_ROLE, user_id=_USER, session_id="mcp:1:4:s1",
                api_key_id=1, entry="mcp")
    base.update(over)
    return Identity(**base)


def _pool():
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="INSERT 0 1")
    return pool


def _args(**payload_over) -> dict:
    payload = {"action": "bill_due_extend", "days": 3}
    payload.update(payload_over)
    return {"summary": "延後到期日", "payload": json.dumps(payload, ensure_ascii=False)}


async def _request(api, **payload_over):
    return await confirm_request(_identity(), _args(**payload_over), db_pool=_pool())


# ════════════════════════════════════════════════════════════════════
# 一、封閉語法表：逐項正反
# ════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("text,expected", [
    # 這一期／上一期（封閉詞表逐字）
    ("這期", (2026, 9)),
    ("本期", (2026, 9)),
    ("這個月", (2026, 9)),
    ("本月", (2026, 9)),
    ("上期", (2026, 8)),
    ("上個月", (2026, 8)),
    # 阿拉伯數字月
    ("9月", (2026, 9)),
    ("09月", (2026, 9)),
    ("8月的房租", (2026, 8)),
    # 中文數字月（一～十二封閉映射）
    ("九月", (2026, 9)),
    ("一月", (2026, 1)),
    ("十月", (2026, 10)),      # 往未來一個月：允許
    ("十一月", (2025, 11)),    # 往未來兩個月：取最近的過去
    ("十二月", (2025, 12)),    # 往未來三個月：取最近的過去
    # 明確年月
    ("2026-09", (2026, 9)),
    ("2026/9", (2026, 9)),
    ("2025-12 那張", (2025, 12)),
    ("2026-09-14 到期那張", (2026, 9)),
])
def test_parse_period_closed_grammar_month(text, expected):
    spec = parse_period(text, _TODAY)
    assert spec is not None, f"{text!r} 應該解析得到"
    assert (spec.year, spec.month) == expected
    assert spec.has_month is True


@pytest.mark.parametrize("text", ["未繳", "還沒繳", "沒繳", "還沒繳的那張"])
def test_parse_period_unpaid_terms_have_no_month(text):
    """未繳＝狀態篩選，**不限月份**（⛔ 不把狀態折進月份）。"""
    spec = parse_period(text, _TODAY)
    assert spec == PeriodSpec(year=None, month=None, unpaid_only=True)
    assert spec.has_month is False


def test_parse_period_month_and_unpaid_combine():
    assert parse_period("九月 未繳", _TODAY) == PeriodSpec(2026, 9, True)
    assert parse_period("這期的，還沒繳的那張", _TODAY) == PeriodSpec(2026, 9, True)


@pytest.mark.parametrize("text", [
    "",                # 空字串
    "   ",             # 全空白
    None,              # 非字串
    123,               # 非字串
    "房租",            # 表外的講法
    "晚三天繳",        # 天數不是期別（「三個月」也不得被當成 3 月）
    "延三個月",
    "延 3 個月",
    "13月",            # 月份值域外
    "0月",
    "2026-13",
    "帳單 20260901",   # 純日期字串沒有「月」字，⛔ 不猜
])
def test_parse_period_returns_none_outside_closed_grammar(text):
    assert parse_period(text, _TODAY) is None


def test_parse_period_none_check_has_positive_control():
    """正對照：同一支函式對表內講法必須回得出東西——上面那批 `None` 才有意義。"""
    assert parse_period("這期", _TODAY) is not None


def test_parse_period_bare_month_boundary_is_one_month_ahead():
    """裸月份取最近的過去或當月，最多往前看一個月（`MAX_MONTHS_AHEAD`）。"""
    assert bill_period.MAX_MONTHS_AHEAD == 1
    today = date(2026, 9, 10)
    assert parse_period("十月", today).year == 2026     # ahead=1 ⇒ 今年
    assert parse_period("十一月", today).year == 2025   # ahead=2 ⇒ 去年
    # 年初的邊界：一月的「上個月」是去年十二月
    assert parse_period("上個月", date(2026, 1, 5)) == PeriodSpec(2025, 12, False)
    # 年底：十二月看「一月」＝今年一月（過去），⛔ 不是明年
    assert parse_period("一月", date(2026, 12, 20)).year == 2026


def test_parse_period_is_pure_and_takes_clock_from_caller():
    """同輸入同輸出，且不同 `today` 會得到不同答案 ⇒ 時鐘確實來自呼叫端。"""
    assert parse_period("這期", date(2026, 9, 10)) == PeriodSpec(2026, 9, False)
    assert parse_period("這期", date(2027, 3, 1)) == PeriodSpec(2027, 3, False)
    assert parse_period("這期", _TODAY) == parse_period("這期", _TODAY)


def test_cn_month_table_is_closed_twelve_members():
    assert sorted(bill_period.CN_MONTH_VALUES.values()) == list(range(1, 13))


# ════════════════════════════════════════════════════════════════════
# 二、resolver 三分支（唯一／多筆候選／零筆）
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_unique_match_fills_bill_id_and_renders_card(api):
    """走查那一句：物件＋「九月」⇒ 對到唯一一張 ⇒ 照常出卡（⛔ 不反問編號）。"""
    result = await _request(api, estate_name=_ESTATE, period="九月的房租")

    assert result.ok is True, result.error
    payload = result.data["payload"]
    assert payload["bill_id"] == _SEP_BILL
    # 原到期日取自**系統存值**（該列 date_expire=20260901），⛔ 不是模型填的
    assert payload["date_expire_before"] == "20260901"
    # 起算日＝原到期日與今天較晚者（今天 09/10）＋3 天
    assert payload["date_expire_after"] == "20260913"
    card = result.data["card"]
    assert _SEP_BILL in card and "2026/09/13" in card
    # 卡外提示行說明來源（⛔ 不進卡、不進卡雜湊）
    assert result.data["hint"] == BILL_MATCH_HINT
    assert BILL_MATCH_HINT not in card


@pytest.mark.asyncio
async def test_unpaid_only_filter_uses_bills_status_table(api):
    """「未繳」＝待繳費（狀態值由 `bills.STATUS_LABELS` 反查）。

    正對照組：同一物件不加「未繳」時是**多筆**（兩張都在），加了才收斂成一張——
    篩選若整個失效，兩個斷言不可能同時成立。
    """
    both = await _request(api, estate_name=_ESTATE)
    assert both.ok is True and both.data.get("candidates"), "同物件本來就有多張帳單"

    only_unpaid = await _request(api, estate_name=_ESTATE, period="還沒繳的那張")
    assert only_unpaid.ok is True
    assert only_unpaid.data["payload"]["bill_id"] == _SEP_BILL
    assert confirm_tools.UNPAID_STATUS_LABEL == "待繳費"
    assert _bills.STATUS_LABELS[2] == confirm_tools.UNPAID_STATUS_LABEL


@pytest.mark.asyncio
async def test_billing_period_month_matches_not_only_due_date(api):
    """月份同時對**繳費期限**與**計費期間**——只比其中一個就會對到別張。

    `769249`（測試物件）繳費期限 20260914、計費期間 2026/10/12–11/11：
    「九月」靠繳費期限命中、「十月」靠計費期間命中，兩者都是同一列。
    """
    by_due = await _request(api, estate_name=_MULTI_ESTATE, period="九月")
    assert by_due.ok is True and by_due.data["payload"]["bill_id"] == "769249"

    by_period = await _request(api, estate_name=_MULTI_ESTATE, period="十月")
    assert by_period.ok is True and by_period.data["payload"]["bill_id"] == "769249"


@pytest.mark.asyncio
async def test_multiple_matches_return_existing_candidates_shape(api):
    """多筆 ⇒ **既有候選形狀**（`data["candidates"]`＋候選清單 provenance），
    ⛔ 不出卡、⛔ 不是 `NO_MATCH`、⛔ 不是第三種出口形狀。"""
    result = await _request(api, estate_name=_MULTI_ESTATE)

    assert result.ok is True
    assert result.error is None
    rows = result.data["candidates"]
    assert isinstance(rows, list) and len(rows) > 1
    assert "card" not in result.data and "pending_id" not in result.data
    # 候選清單文字由 `jgb2._candidates_text` 產（⛔ 本 spec 不另寫一份投影）
    assert result.text_for_model == jgb2_tools._candidates_text(
        "bills", f"{_MULTI_ESTATE}", rows
    )
    assert result.provenance and result.provenance[0].source.startswith("jgb2:bills#")
    # ⚠️ 安全鍵：`action`＋缺 `bill_id` 的 `payload` 是 runtime
    #    `_scope_gate_confirm_request` 判 fail-closed 的依據（有會話範圍時整回合收掉）
    assert result.data["action"] == "bill_due_extend"
    assert "bill_id" not in result.data["payload"]


@pytest.mark.asyncio
async def test_candidates_are_fail_closed_under_a_select_scope(api):
    """**安全回歸**：有會話範圍（L15）時，候選形狀必須被既有那道閘收掉整個回合。

    病灶形狀：`confirm.request` 的結果**不經** `_enforce_tool_scope`（那支只認
    `jgb2.query.*`）——若候選結果不帶 `action`／缺 `bill_id` 的 `payload`，
    別戶的帳單清單就會直接進模型上下文，繞過「這個對話只看你點選的那一戶」。
    下面第二段是**正對照**：把 `action` 拿掉，同一道閘就放行了 ⇒ 證明那兩個鍵
    是這條防線的實際依據，⛔ 不是裝飾。
    """
    from services.agent import runtime as runtime_mod

    result = await _request(api, estate_name=_MULTI_ESTATE)
    assert result.data.get("candidates"), "前提：這一句本來就會回多筆候選"

    sentinel = object()

    class _FakeRuntime:
        """只提供閘門在**這條路徑**上用得到的那一個收尾函式（缺 `bill_id` ⇒ 不查帳單）。"""

        def _finish_confirm_turn(self, **kwargs):
            return sentinel

    state = {runtime_mod.SELECT_SCOPE_KEY: {"estate_id": "67649"}}
    violations: list = []
    blocked = await runtime_mod.AgentRuntime._scope_gate_confirm_request(
        _FakeRuntime(), _identity(), state, result.data,
        trace_id="t", start=0.0, user_message="m", tool_calls=[],
        violations=violations,
    )
    assert blocked is sentinel and "select_scope_exit" in violations

    leaky = dict(result.data)
    leaky.pop("action")
    passed = await runtime_mod.AgentRuntime._scope_gate_confirm_request(
        _FakeRuntime(), _identity(), state, leaky,
        trace_id="t", start=0.0, user_message="m", tool_calls=[], violations=[],
    )
    assert passed is None, "拿掉 action ⇒ 閘門放行 ⇒ 這正是不得拿掉它的理由"


@pytest.mark.asyncio
async def test_zero_match_returns_no_match(api):
    """零筆 ⇒ 既有 `NO_MATCH`（Runtime 走查無固定句）。

    正對照組：同一物件換一個**有帳單**的期別就會命中——回 `NO_MATCH` 不是因為
    查詢整條路徑壞了。
    """
    miss = await _request(api, estate_name=_ESTATE, period="七月")
    assert miss.ok is False and miss.error == "NO_MATCH"

    hit = await _request(api, estate_name=_ESTATE, period="六月")
    assert hit.ok is True and hit.data["payload"]["bill_id"] == _JUN_BILL


@pytest.mark.asyncio
async def test_unknown_estate_name_returns_no_match(api):
    miss = await _request(api, estate_name="這個物件不存在", period="九月")
    assert miss.ok is False and miss.error == "NO_MATCH"


# ════════════════════════════════════════════════════════════════════
# 三、正對照組：有 bill_id 時完全不走 resolver
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_bill_id_present_never_touches_resolver(api, monkeypatch):
    """有帳單編號 ⇒ 一步都不查（既有路徑逐字不變）。"""
    called = []

    async def _boom(*a, **kw):
        called.append(a)
        raise AssertionError("有 bill_id 時 ⛔ 不得去查帳單")

    monkeypatch.setattr(confirm_tools, "_bills_of_estate", _boom)
    result = await confirm_request(
        _identity(),
        _args(bill_id="900001", date_expire_before="20260915",
              date_expire_after="20260918", days=3),
        db_pool=_pool(),
    )
    assert result.ok is True
    assert result.data["payload"]["bill_id"] == "900001"
    assert result.data["hint"] == ""      # ⛔ 沒有「依物件與期別對到」那一行
    assert called == []


@pytest.mark.asyncio
async def test_resolver_untouched_for_repair_create(api, monkeypatch):
    """另一支 action 完全不受影響（正對照：它照常出得了卡）。"""
    async def _boom(*a, **kw):
        raise AssertionError("repair_create ⛔ 不得走帳單對帳")

    monkeypatch.setattr(confirm_tools, "_bills_of_estate", _boom)
    args = {
        "summary": "開修繕單",
        "payload": json.dumps(
            {"action": "repair_create", "estate_name": _ESTATE, "description": "漏水"},
            ensure_ascii=False,
        ),
    }
    result = await confirm_request(_identity(), args, db_pool=_pool())
    assert result.ok is True and "card" in result.data


# ════════════════════════════════════════════════════════════════════
# 四、身分與兌現端邊界
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_resolver_requires_both_role_and_user(api):
    """寫入面雙證：缺 `user_id` ⇒ 對不到（fail-closed），⛔ 不退回單證查法。

    正對照組：同一句話帶齊兩張證就對得到。
    """
    degraded = await confirm_request(
        _identity(user_id=None), _args(estate_name=_ESTATE, period="九月"),
        db_pool=_pool(),
    )
    assert degraded.ok is False and degraded.error == "NO_MATCH"

    ok = await _request(api, estate_name=_ESTATE, period="九月")
    assert ok.ok is True


@pytest.mark.asyncio
async def test_missing_days_does_not_produce_a_card(api):
    """`days` 是使用者唯一貢獻的數字：缺值 ⇒ ⛔ 不代填、不出卡（`INVALID_INPUT`）。"""
    args = {
        "summary": "延後到期日",
        "payload": json.dumps(
            {"action": "bill_due_extend", "estate_name": _ESTATE, "period": "九月"},
            ensure_ascii=False,
        ),
    }
    result = await confirm_request(_identity(), args, db_pool=_pool())
    assert result.ok is False and result.error == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_redemption_still_rejects_payload_without_bill_id():
    """兌現端只收有 `bill_id` 的 payload（出卡時已填）——⛔ 不在兌現端再對一次帳。"""
    assert action_tools._validated_payload(
        "bill_due_extend",
        {"payload": {"action": "bill_due_extend", "estate_name": _ESTATE,
                     "period": "九月", "days": 3}},
        today=_TODAY,
    ) is None
    # 正對照：同一支函式對填好的 payload 必須放行
    assert action_tools._validated_payload(
        "bill_due_extend",
        {"payload": {"action": "bill_due_extend", "bill_id": _SEP_BILL,
                     "date_expire_before": "20260901", "days": 3,
                     "date_expire_after": "20260913"}},
        today=_TODAY,
    ) is not None


def test_action_description_defines_the_alternative_required_fields():
    text = action_tools.BILL_DUE_EXTEND_SPEC["description"]
    assert "estate_name＝使用者口述的物件名稱，照原話填入" in text
    assert "period＝使用者口述的期別原話，照原話填入" in text
    assert "⛔ 不為了取得帳單編號反問使用者" in text
    # ⛔ 定義不寫例子（同 `test_action_tool_descriptions_req.py` 的紀律）
    for marker in ("（如", "(如", "例如", "例：", "像是"):
        assert marker not in text


@pytest.mark.asyncio
async def test_tool_contract_still_passes_the_real_registry(api):
    """真 registry：改過描述的 `confirm.request` 仍過得了可見性／schema 四步。"""
    reg = ToolRegistry()
    reg.register(
        confirm_tools.CONFIRM_SPEC,
        lambda identity, args: confirm_request(identity, args, db_pool=_pool()),
    )
    result = await reg.call(
        _identity(), "confirm.request",
        _args(estate_name=_ESTATE, period="九月"), 5.0, stage="M1",
    )
    assert result.ok is True
    assert result.data["payload"]["bill_id"] == _SEP_BILL
