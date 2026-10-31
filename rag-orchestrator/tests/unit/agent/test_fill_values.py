"""unit：填欄結構化 S3 型別檢查（`services/agent/fill_values.py`）。

計畫 `.kiro/specs/agentic-mcp-orchestration/plan-fill-structured-20261030.md` §6.1 S3、§7 凍結清單 **A3**（機制項）
與 **A9** 的「型別檢查不引用開放詞表、函式簽名不收原話」（FS-R2）。

分工（DSP-091、DSP-127、DSP-128）：AI 換算好的值由程式只驗格式、範圍、值域。期望值由測試寫死（⛔ 引用被測物輸出）；
今天日期固定 2026-10-17（同 `test_step3_write_lifecycle_req.TODAY`）。正反例只用計畫 §7 A3 列的值。
"""
from __future__ import annotations

import ast
import inspect
from datetime import date
from pathlib import Path

import pytest

from services.agent import fill_values as FV
from services.agent import write_forms as WF

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-fill-structured-20261030")]

TODAY = date(2026, 10, 17)
MB = "manual_bill_create"
EST = "estate_create"
CC = "contract_create"
BDE = "bill_due_extend"
REPAIR = "repair_create"


def _f(action: str, key: str):
    f = WF.FORMS[action].field(key)
    assert f is not None, (action, key)                  # 前提：欄位存在（大聲失敗）
    return f


def _v(action, key, value, **kw):
    return FV.validate_with_reason(action, _f(action, key), value, today=kw.pop("today", TODAY), **kw)


# ════════════════════════════════════════════════════════════════════
# A3 數字欄（int／number）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("action,key,value,stored", [
    (MB, "total", "20000", "20000"),
    (MB, "total", "20,000", "20000"),
    (MB, "total", "800", "800"),
    (MB, "total", " 800 ", "800"),
    (EST, "rent", "20000", "20000"),
    (CC, "rent", "20,000", "20000"),
    (EST, "size", "1.5", "1.5"),
    (EST, "size", "800.0", "800.0"),
    (EST, "room_count", "2", "2"),
    (BDE, "days", "7", "7"),
])
def test_a3_number_positive(action, key, value, stored):
    """A3 正例：ASCII 阿拉伯數字（可有千分位、number 欄可有小數）⇒ 收，存正規化字串，不記標記。"""
    assert _v(action, key, value) == (stored, None)


@pytest.mark.parametrize("value", ["2萬", "兩萬", "NT800", "2e4", "inf", "nan", "800元", "+800",
                                   "1,000,00", "2,0000", "①", "²", "８００", "1.5.1", ",800"])
def test_a3_number_format_invalid(value):
    """A3 反例：沒換算的國字、帶單位或文字、科學記號、inf／nan、正號、錯的千分位、圈號與上標、全形數字 ⇒ 不收，
    記 `V_FS_FORMAT_INVALID`。"""
    assert _v(MB, "total", value) == (None, WF.V_FS_FORMAT_INVALID)


def test_a3_int_field_rejects_decimal_and_800_point_0():
    """A3：int 欄 `1.5` 不收；`800.0` 依 `WF.parse_number(…, "int")` 不是整數 ⇒ 不收（number 欄收，見正例）。"""
    assert WF.parse_number("800.0", "int") is None                     # 前提：依 parse_number 的結果判
    assert _v(MB, "total", "1.5") == (None, WF.V_FS_FORMAT_INVALID)
    assert _v(MB, "total", "800.0") == (None, WF.V_FS_FORMAT_INVALID)
    assert _v(EST, "size", "800.0") == ("800.0", None)


@pytest.mark.parametrize("value", ["-800", "-0", "-1.5"])
def test_a3_negative_out_of_bounds(value):
    """A3：負數（含 `-0`）不收，記 `V_FS_OUT_OF_BOUNDS`。"""
    assert _v(EST, "size", value) == (None, WF.V_FS_OUT_OF_BOUNDS)


def test_a3_upper_bound_from_form_declaration():
    """A3：超出 `hi`（表單宣告，`_ClosedField` 同一來源）不收；界值本身收。"""
    assert _f(MB, "total").hi == 9_999_999                             # 前提：範圍由表單宣告帶出
    assert _v(MB, "total", "9999999") == ("9999999", None)
    assert _v(MB, "total", "10000000") == (None, WF.V_FS_OUT_OF_BOUNDS)
    assert _v(EST, "room_count", "100") == (None, WF.V_FS_OUT_OF_BOUNDS)


def test_a3_rent_lower_bound_differs_by_action():
    """A3（N7）：`rent` 在 estate（下限 0）與 contract（下限 1）兩動作各測下限——依動作取範圍。"""
    assert (_f(EST, "rent").lo, _f(CC, "rent").lo) == (0, 1)
    assert _v(EST, "rent", "0") == ("0", None)
    assert _v(CC, "rent", "0") == (None, WF.V_FS_OUT_OF_BOUNDS)
    assert _v(CC, "rent", "1") == ("1", None)


def test_a3_open_lower_bound_number_field():
    """A3：開下界的 number 欄（`size`，`lo_open`）界值 0 不收、略大於 0 收。"""
    f = _f(EST, "size")
    assert f.kind == "number" and f.lo == 0 and f.lo_open is True
    assert _v(EST, "size", "0") == (None, WF.V_FS_OUT_OF_BOUNDS)
    assert _v(EST, "size", "0.5") == ("0.5", None)


@pytest.mark.parametrize("value", ["99999999999", "9" * 30])
def test_a3_huge_days_rejected_without_exception(value):
    """A3（§9 Q9）：沒有宣告範圍的 `days` 只驗非負與溢位——極大值不收、不丟例外。"""
    f = _f(BDE, "days")
    assert f.lo is None and f.hi is None and f.date_offset is True
    stored, mark = _v(BDE, "days", value)
    assert stored is None and mark in (WF.V_FS_OUT_OF_BOUNDS, WF.V_FS_FORMAT_INVALID)


def test_a3_bill_id_only_inside_open_candidates():
    """A3（N1）：`bill_id` 只收候選已開且屬於候選集的編號；不在集內或候選沒開 ⇒ `V_FS_PICK_NOT_IN_CANDIDATES`。"""
    f = _f(BDE, "bill_id")
    assert FV.is_record_pick_field(BDE, f) and not FV.is_record_pick_field(BDE, _f(BDE, "days"))
    assert _v(BDE, "bill_id", "709744", candidates=["709744", "709745"]) == ("709744", None)
    assert _v(BDE, "bill_id", "709746", candidates=["709744", "709745"]) == (None, WF.V_FS_PICK_NOT_IN_CANDIDATES)
    assert _v(BDE, "bill_id", "709744") == (None, WF.V_FS_PICK_NOT_IN_CANDIDATES)
    assert _v(BDE, "bill_id", "709744", candidates=[]) == (None, WF.V_FS_PICK_NOT_IN_CANDIDATES)


# ════════════════════════════════════════════════════════════════════
# A3 日期欄
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("action,key,value,stored", [
    (MB, "date_expire", "2026-11-12", "2026-11-12"),
    (MB, "date_expire", "2026/11/12", "2026-11-12"),
    (MB, "date_expire", "2026-10-17", "2026-10-17"),          # NOT_BEFORE_TODAY：今天本身收
    (CC, "date_start", "2026-11-01", "2026-11-01"),
    (CC, "date_start", "2025-01-01", "2025-01-01"),           # 未標 NOT_BEFORE_TODAY：早於今天照收
    (CC, "date_end", "2027/10/31", "2027-10-31"),
])
def test_a3_date_positive(action, key, value, stored):
    """A3 正例：`WF.parse_model_date` 解析得出 ⇒ 存 `YYYY-MM-DD`；AI 推的年份照收（DSP-128）。"""
    assert _v(action, key, value) == (stored, None)


@pytest.mark.parametrize("value", ["2026-13-01", "11/12", "2026-02-30", "明天", "20261"])
def test_a3_date_format_invalid(value):
    """A3 反例：月份不合、沒年份、不存在的日期、文字 ⇒ 不收，記 `V_FS_FORMAT_INVALID`。"""
    assert _v(MB, "date_expire", value) == (None, WF.V_FS_FORMAT_INVALID)


def test_a3_not_before_today_rejects_past_date():
    """A3：`NOT_BEFORE_TODAY` 欄（手動帳單繳費期限）早於今天不收（`V_FS_OUT_OF_BOUNDS`），今天本身收。"""
    assert WF.field_not_before_today(MB, "date_expire") and not WF.field_not_before_today(CC, "date_start")
    assert _v(MB, "date_expire", "2026-10-16") == (None, WF.V_FS_OUT_OF_BOUNDS)
    assert _v(MB, "date_expire", "2026-10-17") == ("2026-10-17", None)


# ════════════════════════════════════════════════════════════════════
# A3 文字欄
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("action,key,value,stored", [
    (MB, "title", "清潔費", "清潔費"),
    (MB, "title", " 清潔費 ", "清潔費"),
    (MB, "sub_title", "十一月", "十一月"),
    (EST, "title", "測試新物件甲", "測試新物件甲"),
    (EST, "floor", "3F", "3F"),
])
def test_a3_text_positive(action, key, value, stored):
    """A3 正例：`sanitize_data_piece` 後不變、長度 ≤ `value_max_len` ⇒ 收（去前後空白）。"""
    assert _v(action, key, value) == (stored, None)


@pytest.mark.parametrize("value", ["清潔\u0000費", "清潔​費", "清潔\n費", "清潔‮費", "x" * 61])
def test_a3_text_rejects_control_chars_and_overlong(value):
    """A3 反例：含控制字元、零寬、換行、雙向字元（`sanitize_data_piece` 會改動）或超過 `value_max_len` ⇒ 不收。"""
    assert WF.value_max_len(_f(MB, "title")) == 60                    # 前提
    assert _v(MB, "title", value) == (None, WF.V_FS_FORMAT_INVALID)


# ════════════════════════════════════════════════════════════════════
# A3 任意輸入不丟例外
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("value", [None, True, False, 800, 1.5, ["800"], {"v": "800"}, b"800", object()])
@pytest.mark.parametrize("key", ["total", "date_expire", "title"])
def test_a3_non_string_values_return_none_no_exception(key, value):
    """A3：非字串（含布林、數字、容器）⇒ `(None, V_FS_FORMAT_INVALID)`，不丟例外。"""
    assert _v(MB, key, value) == (None, WF.V_FS_FORMAT_INVALID)


@pytest.mark.parametrize("value", ["", "   ", "\t"])
def test_a3_empty_value_is_not_given(value):
    """A3：空值（去空白後為空）⇒ 沒給，不記標記。"""
    assert _v(MB, "total", value) == (None, None)


@pytest.mark.parametrize("args", [
    ("no_such_action", None, "800"),
    (MB, None, "800"),
    (MB, "not a field", "800"),
    (MB, WF.FORMS[REPAIR].field("emergency_status"), "1"),   # enum：不經 S3
])
def test_a3_bad_field_or_kind_returns_none_no_exception(args):
    action, field, value = args
    assert FV.validate_with_reason(action, field, value, today=TODAY) == (None, WF.V_FS_FORMAT_INVALID)
    assert FV.validate(action, field, value, today=TODAY) is None


@pytest.mark.parametrize("today", [None, "2026-10-17", 0])
def test_a3_bad_today_returns_none_no_exception(today):
    assert FV.validate_with_reason(MB, _f(MB, "total"), "800", today=today) == (None, WF.V_FS_FORMAT_INVALID)


def test_a3_validate_returns_only_value():
    assert FV.validate(MB, _f(MB, "total"), "20,000", today=TODAY) == "20000"
    assert FV.validate(MB, _f(MB, "total"), "2萬", today=TODAY) is None


def test_a3_s3_kinds_exactly_four():
    """A3：S3 只涵蓋 int、number、date、text；enum、category、email、phone、period、range 照現行值閘（DSP-128）。"""
    assert FV.S3_KINDS == frozenset({"int", "number", "date", "text"})


# ════════════════════════════════════════════════════════════════════
# A3／A9（FS-R2）：函式簽名不收原話、不引用開放詞表
# ════════════════════════════════════════════════════════════════════
_FV_PATH = Path(FV.__file__)


def test_a9_a3_signature_takes_no_user_text():
    """FS-R2：參數只有動作、欄位宣告、AI 的值、今天日期、候選集（⛔ 原話、對話紀錄、草稿）。"""
    for fn in (FV.validate_with_reason, FV.validate):
        assert list(inspect.signature(fn).parameters) == ["action", "field", "value", "today", "candidates"]


def test_a9_fill_values_has_no_user_text_or_word_list_references():
    """A9：`fill_values.py` 的程式碼（去掉 docstring 與註解）不引用原話、對話紀錄、讀時鐘或開放詞表。"""
    tree = ast.parse(_FV_PATH.read_text(encoding="utf-8"))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    args = {a.arg for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            for a in n.args.args + n.args.kwonlyargs}
    assert "parse_number" in attrs and "parse_model_date" in attrs          # 正對照：走表單宣告與共用解析
    for banned in ("user_message", "user_texts", "dialog", "message", "texts", "now", "today_fn",
                   "user_text_dates", "parse_number_token", "_number_in_texts", "AFFIRMATIVE_WORDS",
                   "THANKS_WORDS", "_today"):
        assert banned not in names | attrs | args, banned
    # 模組層只允許宣告常數：S3_KINDS 與數字格式 regex（⛔ 其他集合常數＝詞表）。
    consts = [t.id for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign))
              for t in ([n.target] if isinstance(n, ast.AnnAssign) else n.targets) if isinstance(t, ast.Name)]
    assert sorted(consts) == ["S3_KINDS", "_ASCII_NUMBER_RE", "__all__"], consts
