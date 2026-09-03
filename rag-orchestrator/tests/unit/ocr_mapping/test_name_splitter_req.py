"""unit 層：承租方姓名切分（design.md 元件 6／name_splitter）。需求 4.1（D3 兩策略皆可測）。"""
import pytest

from services.ocr_mapping.models import FieldSource
from services.ocr_mapping.name_splitter import COMPOUND_SURNAMES, NamePolicy, split_name

pytestmark = pytest.mark.unit


@pytest.mark.req("documind-ocr-mapping:4.1")
@pytest.mark.parametrize("full,last,first", [
    ("歐陽小美", "歐陽", "小美"),
    ("張簡文華", "張簡", "文華"),
    ("陳小美", "陳", "小美"),
    ("王大", "王", "大"),
])
def test_split_policy_uses_compound_surname_table_then_first_char(full, last, first):
    r = split_name(full, NamePolicy.split, confidence=0.8, page=1)
    assert (r.last.value, r.first.value) == (last, first)
    assert r.last.source is FieldSource.derived and r.first.source is FieldSource.derived
    assert r.full.value == full and r.full.source is FieldSource.ocr
    assert set(r.needs_confirmation) == {"to_user_last_name", "to_user_first_name"}   # 恆進待確認


@pytest.mark.req("documind-ocr-mapping:4.1")
def test_keep_full_policy_does_not_split():
    r = split_name("歐陽小美", NamePolicy.keep_full, confidence=0.8, page=1)
    assert r.last.source is FieldSource.absent and r.first.source is FieldSource.absent
    assert r.full.value == "歐陽小美" and r.needs_confirmation == []


@pytest.mark.req("documind-ocr-mapping:4.1")
@pytest.mark.parametrize("full", [None, "", "   "])
def test_empty_name_is_all_absent(full):
    r = split_name(full, NamePolicy.split, confidence=0.8, page=1)
    assert all(f.source is FieldSource.absent for f in (r.last, r.first, r.full))


@pytest.mark.req("documind-ocr-mapping:4.1")
def test_single_char_name_cannot_split_and_is_flagged():
    r = split_name("王", NamePolicy.split, confidence=0.8, page=1)
    assert r.last.value == "王" and r.first.source is FieldSource.absent
    assert "to_user_first_name" in r.needs_confirmation


@pytest.mark.req("documind-ocr-mapping:4.1")
def test_compound_table_is_configurable_and_contains_common_ones():
    assert {"歐陽", "司徒", "張簡", "范姜"} <= set(COMPOUND_SURNAMES)
