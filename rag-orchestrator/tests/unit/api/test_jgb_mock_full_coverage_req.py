"""TDD：`JGBMockTransport` 全讀寫覆蓋（transport-extension-full-coverage，2026-09-08）。

業主核可契約：「讀取和寫入在一份 JSON 都行」——`services/jgb/fixture_data/demo_vendor4.json`
是 vendor4 demo 的唯一資料來源，載入為每個 transport 實例的可變記憶體狀態；
寫入改狀態，之後的讀反映。

本檔驗三件事：
1. 每個新遷入的讀端點至少一案（含 viewer 圈定有宣告／無宣告兩態）；
2. 每個寫入路徑一案（建 → 讀反映），含冪等與 PATCH 欄位白名單；
3. fixture 不含真實個資（既有 0912345678／tenant@example.com 陷阱除外，見下方 ALLOWLIST）。
"""
import asyncio
import json
import re
from pathlib import Path

import pytest

from services.jgb.contract_fixtures import ContractFixtureTable
from services.jgb.estate_fixtures import EstateFixtureTable
from services.jgb.fixtures import BillFixtureTable
from services.jgb.meter_fixtures import MeterFixtureTable
from services.jgb.repair_fixtures import RepairFixtureTable
from services.jgb.team_fixtures import TeamMemberFixtureTable
from services.jgb.transport import JGBMockTransport, UnsupportedMockParameterError

pytestmark = pytest.mark.unit

#: 20151 對齊 fixture 三列物件的 `role_id`（estates 端點會 `int(role_id)` 過濾）；
#: bills／meters／repairs 不消費 role_id 的值，只驗 truthy，沿用同一常數即可。
ROLE = {"role_id": "20151"}


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _full_transport() -> JGBMockTransport:
    return JGBMockTransport(
        BillFixtureTable(), ContractFixtureTable(),
        estate_fixtures=EstateFixtureTable(),
        meter_fixtures=MeterFixtureTable(),
        team_fixtures=TeamMemberFixtureTable(),
        repair_fixtures=RepairFixtureTable(),
    )


# ── 讀端點：每個至少一案 ───────────────────────────────────────────────────

def test_estates_index_returns_only_published():
    r = _run(_full_transport().send("GET", "/api/external/v1/estates", params=ROLE))
    assert r["success"] is True
    # 456／400 為跨域連貫修正新增（分別對齊 contract 678／600 與 repairs 3001/3002）；
    # 54305 未刊登（is_open=0），不出現。
    # ⚠️ 真資料子集併入後另有已刊登物件（同 role_id=20151／is_open=1）一併出現，
    # 不再斷言封閉集合——只驗合成四筆仍在其中、54305 不在其中。
    ids = {e["id"] for e in r["data"]}
    assert {400, 456, 54126, 54200} <= ids
    assert 54305 not in ids


def test_estate_detail_found_and_not_found():
    mt = _full_transport()
    ok = _run(mt.send("GET", "/api/external/v1/estates/54126", params=ROLE))
    assert ok["success"] is True and ok["data"]["id"] == 54126
    assert len(ok["data"]["contract_required_fields"]["fields"]) == 16

    closed = _run(mt.send("GET", "/api/external/v1/estates/54305", params=ROLE))
    assert closed["success"] is False           # 未刊登 → 折疊為 404


def test_meters_index_and_estate_filter():
    mt = _full_transport()
    r = _run(mt.send("GET", "/api/external/v1/meters", params=ROLE))
    # 601（B10，estate 456）為跨域連貫修正新增。
    # ⚠️ 真資料子集併入後另有電表（1061）一併出現，不再斷言封閉集合——
    # 只驗合成四筆仍在其中。
    ids = {m["id"] for m in r["data"]}
    assert {501, 502, 503, 601} <= ids

    scoped = _run(mt.send("GET", "/api/external/v1/meters",
                          params={**ROLE, "estate_id": 9001}))
    assert [m["id"] for m in scoped["data"]] == [501]


def test_team_members_requires_keyword_and_matches_email_or_name():
    mt = _full_transport()
    missing = _run(mt.send("GET", "/api/external/v1/roles/20151/members", params={}))
    assert missing["success"] is False and missing["error"]["code"] == 400

    by_email = _run(mt.send("GET", "/api/external/v1/roles/20151/members",
                            params={"keyword": "owner@example.com"}))
    assert [m["match_field"] for m in by_email["data"]] == ["email"]
    for row in by_email["data"]:
        assert "email" not in row and "name" not in row       # 不回明文個資

    by_name = _run(mt.send("GET", "/api/external/v1/roles/20151/members",
                           params={"keyword": "陳小美"}))
    assert [m["member_user_id"] for m in by_name["data"]] == [292]


def test_member_permissions_owner_vs_member_vs_unknown():
    """⚠️ transport 層的 `data` 是**單一物件**（真 API 形狀）——
    包成單元素 list 是 `JGBSystemAPI.get_member_permissions` 的正規化責任，
    直接打 transport 時不應套用那層包裝。"""
    mt = _full_transport()
    owner = _run(mt.send("GET", "/api/external/v1/roles/20151/members/100/permissions"))
    assert owner["data"]["abilities"]["edit_role"] is True
    assert len(owner["data"]["abilities"]) == 32

    member = _run(mt.send("GET", "/api/external/v1/roles/20151/members/292/permissions"))
    assert member["data"]["abilities"]["show_owner_bill"] is True
    assert member["data"]["abilities"]["edit_role"] is False
    assert "character_name" not in member["data"]           # 無此鍵，只有 character 物件

    unknown = _run(mt.send("GET", "/api/external/v1/roles/20151/members/999999/permissions"))
    assert unknown["success"] is False


def test_repairs_index_filters_and_categories():
    """⚠️ 真資料子集併入後 repairs／repair_categories 皆不再是封閉的合成集合——
    修繕改驗合成兩筆為子集；分類樹已換成真 11 類樹（`repair_categories` 頂層
    改由擷取檔取代舊 3 類佔位），改依名稱取 id、⛔ 不寫死 id。
    """
    mt = _full_transport()
    all_rows = _run(mt.send("GET", "/api/external/v1/repairs", params=ROLE))["data"]
    assert {3001, 3002} <= {r["id"] for r in all_rows}

    urgent = _run(mt.send("GET", "/api/external/v1/repairs",
                          params={**ROLE, "is_urgent": 2}))["data"]
    assert [r["id"] for r in urgent] == [3002]

    cats = _run(mt.send("GET", "/api/external/v1/repairs/categories"))
    assert cats["success"] is True
    names = {c["name"] for c in cats["data"]}
    assert {"電路", "水路衛浴", "房屋結構", "門鎖", "通訊網路",
            "家電維修", "家具", "家居品", "家電清洗", "管道疏通", "其他"} == names
    assert len(cats["data"]) == len({c["id"] for c in cats["data"]})   # id 無重複


# ── viewer 圈定：有宣告／無宣告兩態（bills）──────────────────────────────

def test_bill_viewer_scope_declared_state_filters():
    mt = _full_transport()
    r = _run(mt.send("GET", "/api/external/v1/bills",
                     params={**ROLE, "viewer_user_id": "9001"}))
    assert r["success"] is True
    assert sorted(b["id"] for b in r["data"]) == [900001, 900002]   # 9002 的 900003 濾掉


def test_bill_viewer_scope_undeclared_state_still_raises():
    class _NoVisibilityDeclared:
        def rows(self):
            return [BillFixtureTable().by_id(900001)]

        def visible_to(self, bill_id):
            return None

    mt = JGBMockTransport(_NoVisibilityDeclared())
    with pytest.raises(UnsupportedMockParameterError):
        _run(mt.send("GET", "/api/external/v1/bills",
                     params={**ROLE, "viewer_user_id": "9001"}))


# ── 寫入路徑：建 → 讀反映 ──────────────────────────────────────────────────

def test_create_repair_then_list_reflects():
    mt = _full_transport()
    created = _run(mt.send("POST", "/api/external/v1/repairs", data={
        "role_id": "R001", "estate_id": 456, "category_id": 1, "item_id": 101,
        "broken_reason": "不轉",
    }))
    assert created["success"] is True
    new_id = created["data"]["id"]
    assert new_id == 12346                       # 相容既有 e2e 預設票號

    listed = _run(mt.send("GET", "/api/external/v1/repairs", params=ROLE))
    assert new_id in {r["id"] for r in listed["data"]}


def test_create_bill_then_read_reflects():
    mt = _full_transport()
    created1 = _run(mt.send("POST", "/agent/v1/bills", data={
        "role_id": "R001", "contract_id": 700100, "estate_id": 800001,
        "title": "2026年10月租金", "total": 18000.0, "final_total": 18000.0,
        "date_expire": 20261015,
    }))
    assert created1["success"] is True
    assert set(created1["data"]) == {"id", "created_at"}
    new_id1 = created1["data"]["id"]

    created2 = _run(mt.send("POST", "/agent/v1/bills", data={
        "role_id": "R001", "contract_id": 700100, "estate_id": 800001,
        "title": "2026年11月租金", "total": 18000.0, "final_total": 18000.0,
        "date_expire": 20261115,
    }))
    new_id2 = created2["data"]["id"]

    # 兩筆新帳單 id 相異且皆非 0（`_create_bill` 須比照 contract／estate `setdefault id`）。
    assert new_id1 != new_id2
    assert new_id1 != 0 and new_id2 != 0

    listed = _run(mt.send("GET", "/api/external/v1/bills", params=ROLE))
    listed_ids = {b["id"] for b in listed["data"]}
    assert new_id1 in listed_ids and new_id2 in listed_ids

    patched = _run(mt.send("PATCH", f"/agent/v1/bills/{new_id2}",
                           data={"due_date_shift_days": 1}))
    assert patched["success"] is True
    detail1 = _run(mt.send("GET", f"/api/external/v1/bills/{new_id1}", params=ROLE))
    detail2 = _run(mt.send("GET", f"/api/external/v1/bills/{new_id2}", params=ROLE))
    assert detail1["data"]["date_expire"] == 20261015          # 未被 PATCH 影響
    assert detail2["data"]["date_expire"] != 20261115           # 命中正確那筆


def test_create_contract_then_read_reflects():
    mt = _full_transport()
    created = _run(mt.send("POST", "/agent/v1/contracts", data={
        "role_id": "R001", "title": "新建測試合約", "status": 1, "bit_status": 1,
        "active": 1, "is_history": 0, "estate_id": 456,
    }))
    assert created["success"] is True
    new_id = created["data"]["id"]

    listed = _run(mt.send("GET", "/api/external/v1/contracts/status-overview",
                          params={**ROLE, "contract_ids": str(new_id)}))
    assert [c["id"] for c in listed["data"]] == [new_id]


def test_create_estate_then_read_reflects():
    mt = _full_transport()
    created = _run(mt.send("POST", "/agent/v1/estates", data={
        "role_id": "R001", "role_id_comment": None, "title": "新建測試物件",
        "status": 2, "city": "台北市", "district": "北投區",
    }))
    assert created["success"] is True
    new_id = created["data"]["id"]

    detail = _run(mt.send("GET", f"/api/external/v1/estates/{new_id}", params=ROLE))
    assert detail["success"] is True and detail["data"]["id"] == new_id


def test_create_estate_with_string_role_id_appears_in_role_list():
    """`_estates_index` 比對前正規化 role_id（str/int 皆可）：建物件傳字串
    role_id，之後用同一個 role_id 查列表也要出現——這是收案 verifier 抓到的缺陷，
    修前 `int(role_id)` 對種子列（int）成立、對新建列（字串）恆假。"""
    mt = _full_transport()
    created = _run(mt.send("POST", "/agent/v1/estates", data={
        "role_id": "20151", "title": "字串 role_id 測試物件",
        "status": 2, "city": "台北市", "district": "信義區",
    }))
    new_id = created["data"]["id"]

    listed = _run(mt.send("GET", "/api/external/v1/estates", params=ROLE))
    assert new_id in {e["id"] for e in listed["data"]}


def test_patch_bill_shifts_due_date_and_read_reflects():
    mt = _full_transport()
    r = _run(mt.send("PATCH", "/agent/v1/bills/900001",
                     data={"due_date_shift_days": 7}))
    assert r["success"] is True
    assert r["data"]["due_date_before"] == "2026-08-15"
    assert r["data"]["due_date_after"] == "2026-08-22"

    detail = _run(mt.send("GET", "/api/external/v1/bills/900001", params=ROLE))
    assert detail["data"]["date_expire"] == 20260822


def test_patch_bill_rejects_non_due_date_fields():
    mt = _full_transport()
    r = _run(mt.send("PATCH", "/agent/v1/bills/900001",
                     data={"total": 99999.0}))
    assert r["success"] is False
    assert r["error"]["code"] == 422


def test_patch_bill_unknown_id_is_404():
    mt = _full_transport()
    r = _run(mt.send("PATCH", "/agent/v1/bills/999999",
                     data={"due_date": "2026-09-01"}))
    assert r["success"] is False and r["error"]["code"] == 404


# ── 冪等：同 key 重送回同一份 receipt、不重複建 ───────────────────────────

def test_idempotent_create_repair_does_not_duplicate():
    mt = _full_transport()
    first = _run(mt.send("POST", "/api/external/v1/repairs", data={
        "role_id": "R001", "estate_id": 456, "category_id": 1, "item_id": 101,
        "broken_reason": "不轉", "idempotency_key": "req-abc-123",
    }))
    second = _run(mt.send("POST", "/api/external/v1/repairs", data={
        "role_id": "R001", "estate_id": 456, "category_id": 1, "item_id": 101,
        "broken_reason": "不轉（重送，內容刻意相同）", "idempotency_key": "req-abc-123",
    }))
    assert first["data"]["id"] == second["data"]["id"]

    listed = _run(mt.send("GET", "/api/external/v1/repairs", params=ROLE))
    assert sum(1 for r in listed["data"] if r["id"] == first["data"]["id"]) == 1


def test_idempotent_patch_bill_does_not_reapply():
    mt = _full_transport()
    first = _run(mt.send("PATCH", "/agent/v1/bills/900002",
                         data={"due_date_shift_days": 1, "confirmation_token": "tok-1"}))
    second = _run(mt.send("PATCH", "/agent/v1/bills/900002",
                          data={"due_date_shift_days": 1, "confirmation_token": "tok-1"}))
    assert first == second                       # 同一份 receipt，第二次沒有再位移一天

    detail = _run(mt.send("GET", "/api/external/v1/bills/900002", params=ROLE))
    assert detail["data"]["date_expire"] == 20260916   # 只位移了一次（15 → 16）


# ── fixture 不含真實個資 ───────────────────────────────────────────────────

#: 既有刻意保留的個資陷阱（16 回合劇本依賴）與測試用合成聯絡方式，允許存在。
_ALLOWED_CONTACTS = {
    "0912345678", "0923456789", "tenant@example.com", "tenant2@example.com",
    "0911-111-111", "0912-345-678", "02-2345-6789",
    "owner@example.com", "viewer@example.com", "nochar@example.com",
    "manager@example.com", "sales12291@example.com",
}

_PHONE_RE = re.compile(r"09\d{2}[- ]?\d{3}[- ]?\d{3}|0\d{1,2}-\d{4}-\d{4}")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


#: 真資料子集遮罩後的合成樣式（見 `test_demo_fixture_pii_req.py`
#: 與 `scripts/fixtures/build_demo_fixture_from_capture.py` 的遮罩規則）——
#: `09NN-000-0NN` 電話、`userN@example.com` email，皆為遮罩產生的佔位值，非真實個資。
_MASKED_PHONE_RE = re.compile(r"^09\d{2}-000-0\d{2}$")
_MASKED_EMAIL_RE = re.compile(r"^user\d+@example\.com$")


def test_fixture_contains_no_undeclared_real_contacts():
    """掃 fixture JSON 全文的電話／email 字面值，逐一核對是否為既知合成樣式——

    正對照組：0912345678 這個既有陷阱**必須**被掃到且在允許清單內，
    證明本掃描確實會咬到電話號碼格式，而不是規則寫錯導致「什麼都掃不到」。

    ⚠️ 真資料子集遮罩後的合成值（`09NN-000-0NN`／`userN@example.com`）不在舊白名單裡，
    改為「命中值必須落在既有白名單，或符合遮罩後的合成樣式」——
    仍然抓得到任何真實格式的號碼／信箱（不符合兩者皆非，直接判定未登記）。
    """
    path = (Path(__file__).resolve().parents[3]
            / "services" / "jgb" / "fixture_data" / "demo_vendor4.json")
    text = path.read_text(encoding="utf-8")

    phones = set(_PHONE_RE.findall(text))
    emails = set(_EMAIL_RE.findall(text))

    assert "0912345678" in phones, "正對照組未命中——掃描規則本身可能壞了"

    def _undeclared(values, masked_re):
        return {v for v in values
                if v not in _ALLOWED_CONTACTS and not masked_re.match(v)}

    undeclared = _undeclared(phones, _MASKED_PHONE_RE) | _undeclared(emails, _MASKED_EMAIL_RE)
    assert not undeclared, f"fixture 含未登記的聯絡方式（可能是真實個資混入）：{undeclared}"


# ── 失敗注入（MOCK_FAIL_NEXT_WRITE）─────────────────────────────────────────

def test_mock_fail_next_write_flag_fails_once_state_unchanged():
    """實例屬性旗標：命中一次即清除，狀態不變（帳單數未增加），下一次寫入恢復正常。"""
    mt = _full_transport()
    before = len(_run(mt.send("GET", "/api/external/v1/bills", params=ROLE))["data"])

    mt.fail_next_write = True
    failed = _run(mt.send("POST", "/agent/v1/bills", data={
        "role_id": "R001", "title": "應失敗", "total": 100.0, "date_expire": 20261001,
    }))
    assert failed == {"success": False, "error": {"code": 500,
                      "message": "模擬寫入失敗（MOCK_FAIL_NEXT_WRITE）"}}
    assert mt.fail_next_write is False        # 旗自動清除

    after_fail = len(_run(mt.send("GET", "/api/external/v1/bills", params=ROLE))["data"])
    assert after_fail == before                # 狀態不變：沒有新增帳單

    ok = _run(mt.send("POST", "/agent/v1/bills", data={
        "role_id": "R001", "title": "應成功", "total": 100.0, "date_expire": 20261001,
    }))
    assert ok["success"] is True                # 旗清除後恢復正常

    after_ok = len(_run(mt.send("GET", "/api/external/v1/bills", params=ROLE))["data"])
    assert after_ok == before + 1


def test_mock_fail_next_write_env_var_fails_once_and_clears(monkeypatch):
    """env 旗同樣一次性、命中後自動清除（`os.environ` 直接移除該鍵）。"""
    import os
    mt = _full_transport()
    monkeypatch.setenv("MOCK_FAIL_NEXT_WRITE", "1")

    failed = _run(mt.send("POST", "/agent/v1/estates", data={
        "role_id": "20151", "title": "應失敗物件",
    }))
    assert failed["success"] is False and failed["error"]["code"] == 500
    assert os.getenv("MOCK_FAIL_NEXT_WRITE") is None    # 旗自動清除

    ok = _run(mt.send("POST", "/agent/v1/estates", data={
        "role_id": "20151", "title": "應成功物件",
    }))
    assert ok["success"] is True


def test_mock_fail_next_write_does_not_affect_read_endpoints():
    """失敗注入只作用於寫入端點——讀端點不受影響（範圍宣告：`WRITE_ENDPOINTS`）。"""
    mt = _full_transport()
    mt.fail_next_write = True
    r = _run(mt.send("GET", "/api/external/v1/bills", params=ROLE))
    assert r["success"] is True
    assert mt.fail_next_write is True           # 讀端點不消費這面旗


def test_fixture_json_is_the_single_source_no_duplicate_hardcoded_rows():
    """反事實：`BillFixtureTable` 不再帶類別層級 `_ROWS` 常數（唯一來源改為 JSON）。"""
    assert not hasattr(BillFixtureTable, "_ROWS")
    assert not hasattr(ContractFixtureTable, "_ROWS")
    assert not hasattr(EstateFixtureTable, "_ROWS")
