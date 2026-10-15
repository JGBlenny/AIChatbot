"""站內幫手 S1 修正輪（plan-assistant-11-items-20261014 §3e ①④⑤；DSP-074）。

命題（每條都附「改壞會紅」的變異，見回報）：
  ① 越權：`get_bills` 以編號（`bill_ref`）查帳單／以合約解析時帶 viewer——990002 以編號查 12291 獨有的
     帳單 769258 ⇒ 查不到；12291 ⇒ 查得到（正對照）。`get_bill_detail` 單筆看不到 ⇒ 與「不存在」同形折疊；
     非 assistant fixture 行為不變。
  ④ 新 face「合約基本資料」：在 contracts 的 face 清單與 `jgb2.query.contracts` 的封閉 enum；
     79994 的輸出含結束日；每項一句、可單獨引用；不含承租人個資。
  ⑤ 替身建立帳單不再直接寫金額欄位名（`make audit` 不變量 7）；新帳單實收仍為 0。
期望值一律由測試自己讀 fixture 原始 JSON。
"""
import json
import re
import types
from pathlib import Path

import pytest

from services import jgb_system_api as api_mod
from services.agent import mcp_facade as F
from services.agent.identity import Identity
from services.agent.provenance_units import provenance_units
from services.agent.tools import jgb2
from services.jgb import fixture_store, transport as tr
from services.jgb.contracts import FACE_BUILDERS

pytestmark = pytest.mark.unit

SERVICES = Path(__file__).resolve().parents[3] / "services"
FIXTURE = SERVICES / "jgb" / "fixture_data" / "assistant_demo_vendor4.json"
OWNER, PART = "12291", "990002"
ROLE = "20151"
OWNER_ONLY_BILL = 769258            # 合約 89481 上的帳單，僅 12291 可見
OWNER_ONLY_CONTRACT = 89481
FOLD_BILL = "帳單不存在或無權存取"


@pytest.fixture(scope="module")
def raw():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture()
def api(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.setattr(fixture_store, "_DATA", fixture_store._DATA)
    fixture_store.load_from(FIXTURE)
    a = api_mod.JGBSystemAPI()
    monkeypatch.setattr(jgb2, "_api_singleton", a)
    return a


def test_oracle_the_two_members_really_differ_on_the_target_rows(raw):
    """正對照的前提：fixture 上 769258 與合約 89481 只有 12291 看得到（否則下面的測試是空跑）。"""
    assert raw["bill_visibility"][str(OWNER_ONLY_BILL)] == [int(OWNER)]
    assert raw["contract_visibility"][str(OWNER_ONLY_CONTRACT)] == [int(OWNER)]
    assert int(PART) not in raw["contract_visibility"]["79994"]


# ── ① get_bills 數字 bill_ref ─────────────────────────────────────────────
async def test_bill_ref_number_990002_cannot_see_owner_only_bill_but_12291_can(api):
    mine = await api.get_bills(role_id=ROLE, user_id=OWNER, viewer_user_id=OWNER, bill_ref=str(OWNER_ONLY_BILL))
    assert [r["id"] for r in mine["data"]] == [OWNER_ONLY_BILL]                       # 正對照
    theirs = await api.get_bills(role_id=ROLE, user_id=PART, viewer_user_id=PART, bill_ref=str(OWNER_ONLY_BILL))
    assert theirs == {"success": True, "data": []}                                   # 查不到（與查無同形）
    none = await api.get_bills(role_id=ROLE, user_id=PART, viewer_user_id=PART, bill_ref="99999999")
    assert none == theirs                                                            # 與「不存在」不可區分


async def test_bill_ref_resolved_through_contract_id_and_keyword_is_viewer_scoped(api):
    """帳單查無 ⇒ 當合約 id／關鍵字解析：這兩條也要帶 viewer。"""
    ok = await api.get_bills(role_id=ROLE, user_id=OWNER, viewer_user_id=OWNER, bill_ref=str(OWNER_ONLY_CONTRACT))
    assert ok["data"] and {r["contract_id"] for r in ok["data"]} == {OWNER_ONLY_CONTRACT}   # 正對照
    no = await api.get_bills(role_id=ROLE, user_id=PART, viewer_user_id=PART, bill_ref=str(OWNER_ONLY_CONTRACT))
    assert no == {"success": True, "data": []}
    kw_ok = await api.get_bills(role_id=ROLE, user_id=OWNER, viewer_user_id=OWNER, bill_ref="測試物件")
    assert kw_ok["data"] and {r["contract_id"] for r in kw_ok["data"]} == {OWNER_ONLY_CONTRACT}   # 正對照
    kw_no = await api.get_bills(role_id=ROLE, user_id=PART, viewer_user_id=PART, bill_ref="測試物件")
    assert kw_no == {"success": True, "data": []}                                    # 該戶合約 990002 看不到


async def test_get_bill_detail_folds_invisible_exactly_like_missing(api):
    ok = await api.get_bill_detail(ROLE, OWNER_ONLY_BILL, viewer_user_id=OWNER)
    assert ok["success"] is True and ok["data"]["id"] == OWNER_ONLY_BILL
    hidden = await api.get_bill_detail(ROLE, OWNER_ONLY_BILL, viewer_user_id=PART)
    missing = await api.get_bill_detail(ROLE, 99999999, viewer_user_id=PART)
    assert hidden["success"] is False and hidden == missing                          # 同一句、同一形
    assert hidden["error"]["message"] == FOLD_BILL
    nov = await api.get_bill_detail(ROLE, OWNER_ONLY_BILL)                            # 不帶 viewer＝舊行為（整 role）
    assert nov["success"] is True


async def test_query_bills_tool_990002_by_number_gets_no_match_and_12291_gets_facts(api):
    from services.jgb.bills import BILL_FACE_BUILDERS
    face = sorted(BILL_FACE_BUILDERS)[0]
    ident = types.SimpleNamespace(role_id=ROLE, user_id=PART)
    r_part = await jgb2.query_bills(ident, {"face": face, "ref": str(OWNER_ONLY_BILL)})
    r_own = await jgb2.query_bills(types.SimpleNamespace(role_id=ROLE, user_id=OWNER),
                                   {"face": face, "ref": str(OWNER_ONLY_BILL)})
    assert r_own.get("ok") is True and "provenance" in r_own                         # 正對照：12291 查得到
    # 站內幫手 S5：看不到＝查無（同一句、同一個來源標記；⛔ 細分無權與不存在）
    assert r_part == jgb2._not_found()
    assert r_part["provenance"] == [{"source": "jgb2:not_found#1",
                                     "text": "系統裡查不到這個編號或名稱。", "citable": True}]
    assert str(OWNER_ONLY_BILL) not in json.dumps(r_part, ensure_ascii=False)


async def test_non_assistant_fixture_ignores_viewer_on_bill_detail(monkeypatch):
    """既有行為不變：預設（非 assistant）fixture 的 `_bills_show` 不看 viewer。"""
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.setattr(fixture_store, "_DATA", fixture_store._DATA)
    a = api_mod.JGBSystemAPI()
    t = a._mock_transport
    assert t._assistant_cfg is None
    bid = t.fixtures.rows()[0]["id"]
    plain = await a.get_bill_detail("1", bid)
    with_v = await a.get_bill_detail("1", bid, viewer_user_id="5")
    assert plain["success"] is True and with_v == plain


# ── ④ 合約基本資料 face ────────────────────────────────────────────────────
def test_basic_info_face_is_registered_and_in_the_tool_enum():
    assert "合約基本資料" in FACE_BUILDERS
    reg = F.build_registry(F.FacadeDeps(get_db_pool=lambda: None, get_kb_pool=lambda: None,
                                        get_retriever=lambda: None))
    ident = Identity(vendor_id=4, target_user="property_manager", mode="b2b")
    spec = next(s for s in reg.specs_for(ident, "M0", for_model=False) if s["name"] == "jgb2.query.contracts")
    assert "合約基本資料" in spec["input_schema"]["properties"]["face"]["enum"]
    assert set(spec["input_schema"]["properties"]["face"]["enum"]) == set(FACE_BUILDERS)
    assert {"合約異動", "退租收尾", "簽署排障", "續約"} <= set(FACE_BUILDERS)           # 既有四個不動


async def test_basic_info_for_79994_contains_end_date_and_every_item_is_its_own_unit(api, raw):
    c = next(x for x in raw["contracts"] if x["id"] == 79994)
    r = await jgb2.query_contracts(types.SimpleNamespace(role_id=ROLE, user_id=OWNER),
                                   {"face": "合約基本資料", "ref": "79994"})
    assert r["ok"] is True
    text = r["provenance"][0]["text"]
    end = str(c["date_end"])
    assert f"{end[:4]}/{end[4:6]}/{end[6:]}" in text and "結束日" in text            # 2026/05/31
    start = str(c["date_start"])
    assert f"{start[:4]}/{start[4:6]}/{start[6:]}" in text
    assert f"NT$ {c['rent']:,}" in text and "押金" in text and "目前狀態" in text
    units = provenance_units(text)
    assert len(units) == 5 and all(u.strip().endswith("。") for u in units)
    assert sum("結束日" in u for u in units) == 1                                    # 結束日單獨一句
    assert "@" not in text                                                            # 不含承租人信箱


async def test_basic_info_marks_missing_values_instead_of_inventing_them():
    out = FACE_BUILDERS["合約基本資料"]({"id": 5, "title": "T", "bit_status": 1, "status": 1}, "")
    assert "起始日是 未設定" in out and "結束日是 未設定" in out
    assert "月租是 尚未記錄" in out and "押金是 尚未記錄" in out


async def test_basic_info_990002_cannot_read_owner_only_contract(api):
    r = await jgb2.query_contracts(types.SimpleNamespace(role_id=ROLE, user_id=PART),
                                   {"face": "合約基本資料", "ref": "79994"})
    # 站內幫手 S5：看不到＝查無形狀（NO_MATCH＋查無固定句）
    assert r == {"ok": False, "error": "NO_MATCH",
                 "provenance": [{"source": "jgb2:not_found#1",
                                 "text": "系統裡查不到這個編號或名稱。", "citable": True}],
                 "text_for_model": "系統裡查不到這個編號或名稱。"}
    ok = await jgb2.query_contracts(types.SimpleNamespace(role_id=ROLE, user_id=OWNER),
                                    {"face": "合約基本資料", "ref": "79994"})
    assert ok["ok"] is True                                                           # 正對照


# ── ⑤ 不變量 7 ─────────────────────────────────────────────────────────────
def test_transport_does_not_write_the_amount_field_name_directly():
    """`make audit` 不變量 7：services/jgb/ 除允許清單外，任何非註解行都不得出現金額欄位名。"""
    text = (SERVICES / "jgb" / "transport.py").read_text(encoding="utf-8")
    hits = [ln for ln in text.splitlines() if "final_total" in ln and not ln.lstrip().startswith("#")]
    assert hits == []
    assert "final_total" in (SERVICES / "jgb" / "fixtures.py").read_text(encoding="utf-8")   # 正對照：檢查找得到字樣


async def test_manual_bill_still_starts_with_zero_received_amount(api):
    resp = await api.assistant_create_bill(ROLE, OWNER, {
        "contract_id": 79994, "title": "測試帳單", "total": 1234, "date_expire": "2026-11-30"})
    assert resp["success"] is True
    row = resp["data"]
    assert row["total"] == 1234 and row["rate"] == 1.0 and row["currency"] == "TWD"
    assert row["final_total"] == 0                    # 實收仍為 0（jgb2 投影把 null 壓成 0）
    assert row["date_start"] is None and row["status"] == 1 and row["type"] == 3


# ── r2 修繕進度每行帶單號（S1-live：A1 修繕 6 次 5 次 QUOTE_NOT_COVERING）──────────
async def test_repair_status_every_unit_names_the_repair_and_covers_a_status_sentence(api):
    from services.agent.output_schema import VerifierRules
    from services.agent.verifier import _meaningful_chars
    r = await jgb2.query_repairs(types.SimpleNamespace(role_id=ROLE, user_id=OWNER),
                                 {"face": "修繕進度", "ref": "8915"})
    assert r["ok"] is True
    units = provenance_units(r["provenance"][0]["text"])
    assert len(units) >= 4 and all("#8915" in u for u in units)
    status_unit = next(u for u in units if "目前狀態" in u)
    assert "申請中" in status_unit
    # Verifier 覆蓋率規則（片段側相對值，取嚴）：使用者最常見的答句只引一行也要過
    f = VerifierRules.model_fields
    ratio, floor = f["min_coverage_ratio"].default, f["min_coverage_chars"].default
    for sentence in ("修繕單 8915 目前狀態是申請中。", "修繕單 8915 目前是申請中，尚未指派處理。"):
        frag = _meaningful_chars(sentence)
        best = max(len(frag & _meaningful_chars(u)) for u in units)
        assert best >= max(floor, -(-int(ratio * 100) * len(frag) // 100)), sentence
