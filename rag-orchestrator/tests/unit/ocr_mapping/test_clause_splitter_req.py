"""unit 層：未映射條款粗切（design.md 元件 7）。需求 7.1–7.3。

規則：粗切（第N條／一、／（一）／換行）＋保留含金額／期間／義務語者＋剔除已被欄位 raw 吸收者；
⛔ 不摘要、不改寫、不翻譯——輸出必為輸入的逐字子串。
"""
import pytest

from services.ocr_mapping.clause_splitter import split_clauses
from services.ocr_mapping.models import DocuMindPage

pytestmark = pytest.mark.unit


def _pg(n: int, text: str) -> DocuMindPage:
    return DocuMindPage(page_number=n, ocr_raw={"text": text, "confidence": 0.6}, structured_data={})


TEXT_P2 = "第四條 押金 押金新台幣貳萬柒仟陸佰元整 於簽約時一次付清\n第五條 半年繳整年優惠6000\n第六條 電費預繳1000/月共6個月\n第七條 乙方不得飼養寵物"
TEXT_P3 = "第八條 提前終止 任一方須於三十日前以書面通知\n立契約書人 甲方 張三 乙方 歐陽小美"


# ── R7.1 粗切＋三類保留（金額／期間／義務語）──────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:7.1")
def test_keeps_money_period_and_obligation_clauses_verbatim():
    out = split_clauses([_pg(2, TEXT_P2), _pg(3, TEXT_P3)], absorbed_raws=[])
    assert "半年繳整年優惠6000" in out                      # 金額
    assert "電費預繳1000/月共6個月" in out                  # 期間＋金額
    assert "乙方不得飼養寵物" in out                        # 義務語
    assert "提前終止 任一方須於三十日前以書面通知" in out    # 期間＋義務語
    for clause in out:                                     # ⛔ 不改寫：必為原文子串
        assert clause in TEXT_P2 or clause in TEXT_P3


@pytest.mark.req("documind-ocr-mapping:7.1")
def test_drops_segments_without_money_period_or_obligation():
    out = split_clauses([_pg(3, TEXT_P3)], absorbed_raws=[])
    assert not any("立契約書人" in c for c in out)


@pytest.mark.req("documind-ocr-mapping:7.1")
def test_absorbed_raw_removes_the_clause():
    # 押金欄位吸收的是整個視窗（contract_mapper 的 _DEPOSIT_WINDOW）⇒ 該條款整段被吸收 ⇒ 刪
    out = split_clauses([_pg(2, TEXT_P2)], absorbed_raws=["第四條 押金 押金新台幣貳萬柒仟陸佰元整 於簽約時一次付清"])
    assert not any("押金" in c for c in out)
    assert "半年繳整年優惠6000" in out                      # 未被吸收者仍在
    # ⚠️ 只吸收「金額片段」時，剩餘「於簽約時一次付清」仍有期間語 ⇒ ⛔ 不得整條刪（2026-09-03 對抗驗證 ②-2）
    out2 = split_clauses([_pg(2, TEXT_P2)], absorbed_raws=["押金新台幣貳萬柒仟陸佰元整"])
    assert any("一次付清" in c for c in out2)


@pytest.mark.req("documind-ocr-mapping:7.1")
def test_enumerator_styles_and_newlines_all_split():
    text = "一、租金每月壹萬元整\n（二）水電費由乙方負擔\n乙方應於每月五日前繳納"
    out = split_clauses([_pg(1, text)], absorbed_raws=[])
    assert out == ["租金每月壹萬元整", "水電費由乙方負擔", "乙方應於每月五日前繳納"]


# ── R7.2 ⛔ 不摘要、不改寫 ────────────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:7.2")
def test_output_is_exact_substring_no_normalization():
    text = "第五條 半年繳整年優惠  6000 元"           # 內含雙空白
    out = split_clauses([_pg(1, text)], absorbed_raws=[])
    assert out == ["半年繳整年優惠  6000 元"]


# ── R7.3 寵物／吸菸／訪客一律走陣列，⛔ 不映射到 smoke_detector ────────────────
@pytest.mark.req("documind-ocr-mapping:7.3")
@pytest.mark.parametrize("clause", ["乙方不得飼養寵物", "室內禁止吸菸", "訪客不得留宿"])
def test_pet_smoke_visitor_clauses_are_kept_as_unmapped(clause):
    out = split_clauses([_pg(1, f"第九條 {clause}")], absorbed_raws=[])
    assert out == [clause]


@pytest.mark.req("documind-ocr-mapping:7.1")
def test_dedup_and_page_order_stable():
    out = split_clauses([_pg(1, "第一條 乙方不得轉租"), _pg(2, "第一條 乙方不得轉租\n第二條 乙方應按時繳租")], absorbed_raws=[])
    assert out == ["乙方不得轉租", "乙方應按時繳租"]


@pytest.mark.req("documind-ocr-mapping:7.1")
def test_empty_pages_yield_empty_list():
    assert split_clauses([_pg(1, ""), _pg(2, "   ")], absorbed_raws=[]) == []
