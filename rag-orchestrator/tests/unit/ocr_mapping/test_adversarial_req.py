"""unit 層：2026-09-03 獨立對抗性驗證抓到的 5 條 P2 ＋ 流程追蹤自抓的 2 條，逐條釘成回歸測試。

每條註明來源（②＝對抗性代理、⑧＝流程追蹤）與需求條號；⛔ 這些都是 fixture 蓋不到的。
"""
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.ocr_mapping import router
from services.ocr_mapping.clause_splitter import split_clauses
from services.ocr_mapping.contract_mapper import CONTRACT_SOURCE_MAP, map_contract
from services.ocr_mapping.deposit_rule import decide_deposit
from services.ocr_mapping.field_normalizer import normalize_lease_months
from services.ocr_mapping.models import DocuMindPage, FieldSource
from services.ocr_mapping.page_merger import merge_pages

pytestmark = pytest.mark.unit
FIX = Path(__file__).parent / "fixtures"
IDENTITY = {"vendor_id": 1, "role_id": "20151", "user_id": "12291", "mode": "b2c", "target_user": "landlord",
            "session_id": "backtest_session_ocr_adv"}


def _pg(n: int, sd: dict, text: str = "", conf: float = 0.6) -> DocuMindPage:
    return DocuMindPage(page_number=n, ocr_raw={"text": text, "confidence": conf}, structured_data=sd)


def _run(pages):
    merged = merge_pages(pages, CONTRACT_SOURCE_MAP.values(), {}, None)
    return map_contract(merged, pages)


# ── ②-1 租期視窗污染 ＋「一年半」（R5.4／R4.2）───────────────────────────────
@pytest.mark.req("documind-ocr-mapping:5.4")
def test_lease_window_stops_at_punctuation_and_ignores_deposit_months():
    pages = [_pg(1, {"contract_metadata": {"effective_date": "2025/1/21"}}, "為期二年，押金三個月")]
    r = _run(pages)
    assert r.fields["lease_months"].value == 24                      # ⛔ 不是 27
    assert r.fields["date_end"].value == "2027-01-20"


@pytest.mark.req("documind-ocr-mapping:5.4")
@pytest.mark.parametrize("text,months", [("租期一年半", 18), ("租期壹年半", 18), ("租期兩年半", 30), ("租期十八個月", 18)])
def test_lease_months_handles_half_year(text, months):
    r = normalize_lease_months(text)
    assert r is not None and r[0] == months


# ── ②-2 條款與 absorbed_raws 部分重疊 ⛔ 不得整條刪（R7.1／拍板 4）────────────
@pytest.mark.req("documind-ocr-mapping:7.1")
def test_partial_overlap_keeps_clause_with_extra_conditions():
    text = "第三條 乙方應於每月五日前繳納租金，逾期按日加收滯納金千分之一"
    out = split_clauses([_pg(1, {}, text)], absorbed_raws=["每月五日前"])
    assert any("滯納金" in c for c in out), "被 cycle_date 的 raw 部分吸收就整條刪 ⇒ 滯納金條件遺失"


@pytest.mark.req("documind-ocr-mapping:7.1")
def test_fully_absorbed_clause_is_still_dropped():
    text = "第四條 押金 押金新台幣貳萬柒仟陸佰元整 於簽約時一次付清"
    out = split_clauses([_pg(1, {}, text)], absorbed_raws=["第四條 押金 押金新台幣貳萬柒仟陸佰元整 於簽約時一次付清"])
    assert out == []


# ── ②-3 structured_data 葉值是 dict 且跨頁不同 ⛔ 不得 500，且要落計量（R1.1／R9.3）──
@pytest.mark.req("documind-ocr-mapping:1.1")
def test_non_scalar_leaf_values_do_not_crash_merge():
    pages = [_pg(1, {"parties": {"party_b": {"name": "歐陽小美"}}}), _pg(2, {"parties": {"party_b": {"name": "王大明"}}})]
    merged = merge_pages(pages, ["parties.party_b"], {}, None)
    assert merged["parties.party_b"].value is not None                # 不拋例外；值被字串化或視為空皆可


@pytest.mark.req("documind-ocr-mapping:9.3")
def test_unexpected_error_is_500_and_still_metered(monkeypatch):
    from services import usage_metering as um
    import services.ocr_mapping.mapper as mapper_mod
    calls = []
    monkeypatch.setattr(um, "begin", lambda *a, **k: None)
    monkeypatch.setattr(um, "set_path", lambda *a, **k: None)
    monkeypatch.setattr(um, "finalize", lambda status="success", http_status=200, db_pool=None: calls.append((status, http_status)))
    import routers.ocr_mapping as rm
    monkeypatch.setattr(rm, "run_mapping", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    app = FastAPI(); app.include_router(router); c = TestClient(app, raise_server_exceptions=False)
    data = json.loads((FIX / "documind_contract_sample.json").read_text(encoding="utf-8"))
    data = {k: v for k, v in data.items() if not k.startswith("_")} | IDENTITY
    r = c.post("/api/v1/ocr-mapping/contract", json=data)
    assert r.status_code == 500 and r.json()["error_code"] == "MAPPING_ERROR"
    assert calls == [("error", 500)]


# ── ②-4 R6.3 兩者並存不分先後 ────────────────────────────────────────────────
@pytest.mark.req("documind-ocr-mapping:6.3")
@pytest.mark.parametrize("text", ["押金貳個月，計新台幣貳萬柒仟陸佰元整", "押金新台幣貳萬柒仟陸佰元整（貳個月）", "押金二個月租金計 27,600 元"])
def test_amount_and_months_in_any_order_prefer_amount_and_flag(text):
    d = decide_deposit(text, page=1, confidence=0.7)
    assert d.deposit_type.value == 1 and d.deposit_amount.value == 27600 and d.deposit.value is None
    assert d.needs_confirmation is True


# ── ②-5 OCR_MAPPING_MAX_BODY_MB 壞值／負值 ⛔ 不得 500 或恆 413（R1.5）───────────
@pytest.mark.req("documind-ocr-mapping:1.5")
@pytest.mark.parametrize("bad", ["abc", "-1", "0", ""])
def test_bad_max_body_env_falls_back_to_default(monkeypatch, bad):
    monkeypatch.setenv("OCR_MAPPING_MAX_BODY_MB", bad)
    app = FastAPI(); app.include_router(router); c = TestClient(app)
    data = json.loads((FIX / "documind_contract_sample.json").read_text(encoding="utf-8"))
    data = {k: v for k, v in data.items() if not k.startswith("_")} | IDENTITY
    assert c.post("/api/v1/ocr-mapping/contract", json=data).status_code == 200


# ── 實打抓到（2026-09-03 13:2x）：視窗截斷日期尾巴，裸「1月」被當成 +1 個月 ⇒ 誤標衝突 ──
@pytest.mark.req("documind-ocr-mapping:5.4")
@pytest.mark.parametrize("text", [
    "租期壹年 自中華民國114年1月21日起至中華民國115年1月2",       # 視窗截在日期中間
    "租期壹年 自114年1月21日起至115年1月20日止",
])
def test_bare_month_after_year_is_a_date_not_lease_months(text):
    r = normalize_lease_months(text)
    assert r is not None and r[0] == 12


@pytest.mark.req("documind-ocr-mapping:4.2")
def test_window_offset_does_not_create_false_conflict():
    pages = [_pg(1, {"contract_metadata": {"effective_date": "中華民國114年1月21日"}},
                 "租期壹年 自中華民國114年1月21日起至中華民國115年1月20日止")]     # 文首就是「租期」
    r = _run(pages)
    assert r.fields["date_end"].value == "2026-01-20" and r.fields["date_end"].conflicts == []
    assert "date_end" not in r.needs_confirmation


# ── ⑧(a) 明文到期日優先於月數推算（R4.2 補強）──────────────────────────────
@pytest.mark.req("documind-ocr-mapping:4.2")
def test_explicit_end_date_is_read_before_deriving_from_months():
    pages = [_pg(1, {"contract_metadata": {"effective_date": "中華民國114年1月21日"}},
                 "租賃期間 租期壹年 自中華民國114年1月21日起至中華民國115年1月20日止")]
    r = _run(pages)
    de = r.fields["date_end"]
    assert de.value == "2026-01-20" and de.jgb_value == 20260120
    assert de.source is FieldSource.derived and "115年1月20日" in (de.raw or "")   # 讀到的是明文，不是推算
    assert "date_end" not in r.needs_confirmation                     # 明文讀到 ⇒ 不必反白


@pytest.mark.req("documind-ocr-mapping:4.2")
def test_explicit_end_date_conflicting_with_months_is_flagged():
    pages = [_pg(1, {"contract_metadata": {"effective_date": "2025/1/21"}}, "租期壹年 自2025/1/21起至2026/6/30止")]
    r = _run(pages)
    assert r.fields["date_end"].value == "2026-06-30" and "date_end" in r.needs_confirmation
    assert len(r.fields["date_end"].conflicts) == 1                  # 推算值 2026-01-20 進 conflicts


# ── ⑧(b) 「N 日前書面通知」→ early_termination_days（決定性，不用 LLM）──────────
@pytest.mark.req("documind-ocr-mapping:4.1")
@pytest.mark.parametrize("text,days", [
    ("第八條 提前終止 任一方須於三十日前以書面通知", 30),
    ("提前解約應於 60 天前通知對方", 60),
    ("終止租約須於一個月前書面通知", None),                          # 「一個月」非日數 ⇒ 不猜
])
def test_early_termination_days_parsed_deterministically(text, days):
    r = _run([_pg(1, {}, text)])
    f = r.fields["early_termination_days"]
    if days is None:
        assert f.source is FieldSource.absent
    else:
        assert f.value == days and f.source is FieldSource.derived and "early_termination_days" in r.needs_confirmation
