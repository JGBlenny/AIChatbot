"""unit 層：決定性換算器（design.md 元件 4）。⛔ 無 LLM、無猜測：同輸入恆同輸出，解析不了一律 None。"""
import pytest

from services.ocr_mapping.field_normalizer import (
    normalize_amount,
    normalize_area,
    normalize_cycle_date,
    normalize_date,
    normalize_lease_months,
)

pytestmark = pytest.mark.unit


# ── R5.5 金額：中文大寫／千分位 → 整數；模糊量詞 → None ───────────────────────
@pytest.mark.req("documind-ocr-mapping:5.5")
@pytest.mark.parametrize("text,expected", [
    ("每月租金新台幣壹萬參仟捌佰元整", 13800),
    ("押金新台幣貳萬柒仟陸佰元整", 27600),
    ("租金 13,800 元", 13800),
    ("NT$25000", 25000),
    ("壹拾貳萬元整", 120000),
    ("參萬元", 30000),
    ("2萬5千元", 25000),
])
def test_amount_parses_chinese_numerals_and_thousands(text, expected):
    r = normalize_amount(text)
    assert r is not None and r[0] == expected and r[1] == text.strip()


@pytest.mark.req("documind-ocr-mapping:5.5")
@pytest.mark.parametrize("text", ["約壹萬元", "壹萬元以上", "租金面議", "", "每月五日前"])
def test_amount_vague_or_absent_returns_none(text):
    assert normalize_amount(text) is None


# ── R3.2 面積：千分位與單位 → float ──────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:3.2")
@pytest.mark.parametrize("text,expected", [
    ("3,406.98", 3406.98), ("3406.98平方公尺", 3406.98), ("面積：25.5 坪", 25.5), ("120 ㎡", 120.0),
])
def test_area_strips_thousands_and_units(text, expected):
    r = normalize_area(text)
    assert r is not None and r[0] == pytest.approx(expected) and r[1] == text.strip()


@pytest.mark.req("documind-ocr-mapping:3.2")
@pytest.mark.parametrize("text", ["", "全部", "約三十坪"])
def test_area_unparseable_returns_none(text):
    assert normalize_area(text) is None


# ── R5.4 租期 → 月數；⛔ 不猜 ───────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:5.4")
@pytest.mark.parametrize("text,months", [
    ("租期壹年", 12), ("租賃期間貳年", 24), ("為期十二個月", 12), ("租期 6 個月", 6),
    ("租期一年六個月", 18), ("租期2年", 24),
])
def test_lease_months_from_chinese_and_arabic(text, months):
    r = normalize_lease_months(text)
    assert r is not None and r[0] == months and r[1] == text.strip()


@pytest.mark.req("documind-ocr-mapping:5.4")
@pytest.mark.parametrize("text", ["", "租期另議", "自114年1月21日起", "長期"])
def test_lease_months_unparseable_returns_none(text):
    assert normalize_lease_months(text) is None


# ── R4.1 繳費日：僅可決定性解析為 1–31 的整數日 ─────────────────────────────
@pytest.mark.req("documind-ocr-mapping:4.1")
@pytest.mark.parametrize("text,day", [
    ("每月五日前繳納", 5), ("每月 5 日前", 5), ("每月廿五日", 25), ("每月1號", 1), ("每月三十一日", 31),
])
def test_cycle_date_parses_day_of_month(text, day):
    r = normalize_cycle_date(text)
    assert r is not None and r[0] == day and r[1] == text.strip()


@pytest.mark.req("documind-ocr-mapping:4.1")
@pytest.mark.parametrize("text", ["", "每月三十二日", "每季初", "月初", "每月0日", "114年1月21日"])
def test_cycle_date_out_of_range_or_ambiguous_returns_none(text):
    assert normalize_cycle_date(text) is None


# ── R5.1 民國三格式 → ISO ＋ Ymd 整數，source 由呼叫端標 derived ──────────────
@pytest.mark.req("documind-ocr-mapping:5.1")
@pytest.mark.parametrize("text", [
    "中華民國114年1月21日",
    "民國114年01月21日",
    "114/1/21",
    "1140121",                       # 七碼 NNNMMDD（ContractService lease_signing_date 格式）
    "簽約日期：中華民國114年1月21日（星期二）",   # 內嵌於句子
])
def test_roc_dates_convert_to_gregorian(text):
    d = normalize_date(text)
    assert d is not None
    assert d.iso == "2025-01-21" and d.ymd == 20250121
    assert d.calendar == "roc"
    assert d.raw == text.strip()     # R5.6 可逆對照：raw 含原文全段


# ── R5.2 西元三格式 → 正規化 ─────────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:5.2")
@pytest.mark.parametrize("text", ["2025/1/21", "2025-01-21", "2025年1月21日", "20250121"])
def test_gregorian_dates_normalize(text):
    d = normalize_date(text)
    assert d is not None
    assert (d.iso, d.ymd, d.calendar) == ("2025-01-21", 20250121, "gregorian")


# ── 反例：不可決定性解析者一律 None（⛔ 不猜） ─────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:5.1")
@pytest.mark.parametrize("text", [
    "", "租期壹年", "2025年13月45日", "114年2月30日", "一月二十一日", "2025/1", "約114年初",
])
def test_unparseable_dates_return_none(text):
    assert normalize_date(text) is None


@pytest.mark.req("documind-ocr-mapping:5.6")
def test_raw_is_full_original_segment_not_just_the_match():
    text = "本約自中華民國114年1月21日起生效"
    d = normalize_date(text)
    assert d is not None and d.raw == text
