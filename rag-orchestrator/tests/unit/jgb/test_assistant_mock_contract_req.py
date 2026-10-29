"""站內幫手 S0 替身契約（plan-assistant-11-items-20261014 §3b「S0 驗收」2）。

被測物：`JGBMockTransport`／`JGBSystemAPI` 在 `assistant_demo_vendor4.json` 上的 7 支提案替身
（jgb2-req#16～#22；contract: proposed）與 `RecordingTransport` 的 body 紀錄。
命題（每條都附「改壞會紅」的變異，見回報）：
  1. 他團隊資源 ⇒ 折疊錯誤（與「不存在」同一句，且替身狀態不變）；
  2. body 含歸屬欄位或未知欄位 ⇒ 422；
  3. `RecordingTransport` 記到 body，且 `calls` 仍是 3 元組；
  4. 統計／清單依成員可見範圍回正確筆數（兩位成員結果不同），帶 `user_id` 不拋
     `UnsupportedMockParameterError`；
  5. 每支替身在程式與 fixture 皆標 `jgb2-req#n` 與 `contract: proposed`。
期望值一律由測試自己讀 fixture 原始 JSON 獨立算出（再與寫死的數字互證），不引用被測物的輸出。
"""
import asyncio
import inspect
import json
from pathlib import Path

import pytest

from services import jgb_system_api as api_mod
from services.jgb import fixture_store, transport as tr
from services.jgb.transport import (
    JGBMockTransport,
    MissingFixtureError,
    RecordingTransport,
    UnsupportedMockParameterError,
)

pytestmark = pytest.mark.unit

FIXTURE = (Path(__file__).resolve().parents[3]
           / "services" / "jgb" / "fixture_data" / "assistant_demo_vendor4.json")
OWNER, PART = 12291, 990002          # 全部可見的擁有者 / 只可見部分的合成成員
ROLE, FOREIGN_ROLE = 20151, 30999
AS_OF = "2026-10-14"
FOLD = "不存在或無權存取"
SHA = "a" * 64


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(scope="module")
def raw():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture()
def api(monkeypatch):
    """載入 assistant fixture 的 mock API，transport 外包 RecordingTransport。"""
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.setattr(fixture_store, "_DATA", fixture_store._DATA)      # 讓 monkeypatch 負責還原
    fixture_store.load_from(FIXTURE)
    a = api_mod.JGBSystemAPI()
    a._mock_transport = RecordingTransport(a._mock_transport)
    return a


def _items(resp):
    return resp["data"]["items"]


def _ids(resp):
    return [i["id"] for i in _items(resp)]


# ── 原始資料上的獨立 oracle ───────────────────────────────────────────────
def _visible(raw, domain, row_id, viewer):
    return viewer in raw[f"{domain}_visibility"][str(row_id)]


def _oracle_unpaid(raw, viewer, scope):
    asof = 20261014
    out = []
    for b in raw["bills"]:
        if b["status"] not in (2, 8) or not _visible(raw, "bill", b["id"], viewer):
            continue
        if scope == "overdue" and b["date_expire"] < asof:
            out.append(b)
        if scope == "this_month" and 20261001 <= b["date_expire"] <= 20261031:
            out.append(b)
    return out


# ═══ 5. 標記 ═══════════════════════════════════════════════════════════════
def test_seven_endpoints_marked_in_fixture_and_code(raw):
    eps = raw["assistant_demo"]["endpoints"]
    assert sorted(eps) == [f"jgb2-req#{n}" for n in range(16, 23)]       # 7 支，#23／#24 無替身
    assert all(v["contract"] == "proposed" for v in eps.values())
    handlers = {
        16: JGBMockTransport._assistant_unpaid_bills, 17: JGBMockTransport._assistant_in_progress_repairs,
        18: JGBMockTransport._assistant_expiring_contracts, 19: JGBMockTransport._assistant_create_estate,
        20: JGBMockTransport._assistant_create_contract, 21: JGBMockTransport._assistant_create_bill,
        22: JGBMockTransport._assistant_repair_checks,
    }
    public = {
        16: api_mod.JGBSystemAPI.get_unpaid_bill_summary, 17: api_mod.JGBSystemAPI.get_in_progress_repairs,
        18: api_mod.JGBSystemAPI.get_expiring_contracts, 19: api_mod.JGBSystemAPI.assistant_create_estate,
        20: api_mod.JGBSystemAPI.assistant_create_contract, 21: api_mod.JGBSystemAPI.assistant_create_bill,
        22: api_mod.JGBSystemAPI.create_repair,
    }
    for n in range(16, 23):
        for fn in (handlers[n], public[n]):
            doc = inspect.getdoc(fn)
            assert f"jgb2-req#{n}" in doc and "contract: proposed" in doc, (n, fn.__qualname__)


def test_new_endpoints_need_the_assistant_fixture(monkeypatch):
    """換回別的 fixture（沒有 assistant_demo 段）⇒ 大聲失敗，不退回猜測。"""
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    a = api_mod.JGBSystemAPI()                        # conftest 預設的 regression fixture
    with pytest.raises(MissingFixtureError):
        _run(a.get_unpaid_bill_summary("20151", "12291", "overdue"))


def test_real_mode_sends_nothing_for_proposed_endpoints(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "false")
    monkeypatch.setenv("JGB_API_KEY", "unit-test-placeholder")
    a = api_mod.JGBSystemAPI()

    class Boom:
        async def send(self, *a, **k):
            raise AssertionError("提案中的端點不得對真網路發出請求")

    a._real_transport = Boom()
    for call in (a.get_unpaid_bill_summary("20151", "12291", "overdue"),
                 a.get_in_progress_repairs("20151", "12291"),
                 a.get_expiring_contracts("20151", "12291"),
                 a.assistant_create_estate("20151", "12291", {"title": "x"}),
                 a.assistant_create_contract("20151", "12291", {}),
                 a.assistant_create_bill("20151", "12291", {})):
        assert _run(call)["success"] is False


# ═══ 4. 依成員可見範圍 ═════════════════════════════════════════════════════
@pytest.mark.parametrize("viewer,scope,count,total", [
    (OWNER, "overdue", 7, 231400), (PART, "overdue", 3, 114700),
    (OWNER, "this_month", 3, 44800), (PART, "this_month", 2, 36000),
])
def test_unpaid_summary_counts_follow_member_visibility(api, raw, viewer, scope, count, total):
    resp = _run(api.get_unpaid_bill_summary("20151", str(viewer), scope, as_of=AS_OF))
    assert resp["success"] is True
    d = resp["data"]
    expected = _oracle_unpaid(raw, viewer, scope)
    assert (d["count"], d["total_amount"]) == (count, total) == (len(expected), sum(b["total"] for b in expected))
    assert sorted(_ids(resp)) == sorted(b["id"] for b in expected)
    assert d["total_amount"] == sum(i["total"] for i in _items(resp))       # 總額＝明細逐筆相加


def test_two_members_get_different_results(api):
    a = _run(api.get_unpaid_bill_summary("20151", str(OWNER), "overdue", as_of=AS_OF))
    b = _run(api.get_unpaid_bill_summary("20151", str(PART), "overdue", as_of=AS_OF))
    assert set(_ids(b)) < set(_ids(a)) and a["data"]["count"] != b["data"]["count"]
    ra = _run(api.get_in_progress_repairs("20151", str(OWNER), per_page=200))
    rb = _run(api.get_in_progress_repairs("20151", str(PART), per_page=200))
    assert set(_ids(rb)) < set(_ids(ra))
    ea = _run(api.get_expiring_contracts("20151", str(OWNER), months=6, as_of=AS_OF))
    eb = _run(api.get_expiring_contracts("20151", str(PART), months=6, as_of=AS_OF))
    assert set(_ids(eb)) < set(_ids(ea))


def test_unpaid_pagination_does_not_shrink_count_or_total(api):
    resp = _run(api.get_unpaid_bill_summary("20151", str(OWNER), "overdue", as_of=AS_OF, per_page=2))
    assert len(_items(resp)) == 2
    assert resp["data"]["count"] == 7 and resp["data"]["total_amount"] == 231400
    assert resp["pagination"]["total"] == 7 and resp["pagination"]["has_more"] is True


def test_in_progress_repairs_exclude_closed_and_follow_visibility(api, raw):
    open_status = (1, 2, 16)
    for viewer in (OWNER, PART):
        resp = _run(api.get_in_progress_repairs("20151", str(viewer), per_page=200))
        want = sorted(r["id"] for r in raw["repairs"]
                      if r["status"] in open_status and _visible(raw, "repair", r["id"], viewer))
        assert sorted(_ids(resp)) == want and resp["data"]["count"] == len(want)
        assert {i["status"] for i in _items(resp)} <= set(open_status)        # 結單 32／封存 64 不出現
    assert _run(api.get_in_progress_repairs("20151", str(OWNER)))["data"]["count"] == 77


def test_expiring_contracts_window_and_visibility(api):
    def ids(viewer, months):
        return _ids(_run(api.get_expiring_contracts("20151", str(viewer), months=months, as_of=AS_OF)))

    assert ids(OWNER, 3) == [85516, 990101]                  # 到 2027-01-14
    assert ids(OWNER, 6) == [85516, 990101, 990102]          # 到 2027-04-14；80304（0430）不在
    assert ids(PART, 6) == [85516, 990101]                   # 990102 在 B 看不到的物件上
    assert ids(OWNER, 1) == [85516]                          # 到 2026-11-14
    first = _items(_run(api.get_expiring_contracts("20151", str(OWNER), as_of=AS_OF)))[0]
    assert first["days_left"] == 17 and first["date_end"] == 20261031


def test_viewer_user_id_never_raises_unsupported(api):
    """帶 user_id（viewer）呼叫不拋 UnsupportedMockParameterError——舊 /bills 的 viewer_user_id 才拋。"""
    for call in (lambda u: api.get_unpaid_bill_summary("20151", u, "overdue", as_of=AS_OF),
                 lambda u: api.get_in_progress_repairs("20151", u),
                 lambda u: api.get_expiring_contracts("20151", u, as_of=AS_OF)):
        for u in (str(OWNER), str(PART)):
            assert _run(call(u))["success"] is True
    # 正對照組：既有 /bills 的 viewer_user_id 遇到「未宣告可見性」的列仍拋——
    # 先用 agent/v1 寫入端點造一筆未宣告的帳單，證明這個例外類別在這份 fixture 上確實會發生
    t = api._mock_transport
    _run(t.send("POST", "/agent/v1/bills", data={"role_id": "20151", "title": "未宣告"}))
    with pytest.raises(UnsupportedMockParameterError):
        _run(t.send("GET", "/api/external/v1/bills",
                    params={"role_id": "20151", "viewer_user_id": str(OWNER)}))


def test_stats_reject_bad_identity_and_params(api):
    t = api._mock_transport
    path = "/api/external/v1/bills/summary/unpaid"

    def get(**p):
        return _run(t.send("GET", path, params={"scope": "overdue", "as_of": AS_OF, **p}))

    assert get(role_id="20151")["error"]["code"] == 400                         # 缺 user_id
    assert get(role_id="20151", user_id="555555")["error"] == {"code": 404, "message": FOLD}   # 非成員
    assert get(role_id=str(FOREIGN_ROLE), user_id=str(OWNER))["error"] == {"code": 404, "message": FOLD}
    assert get(role_id="20151", user_id=str(OWNER), viewer_user_id="1")["error"]["code"] == 422
    assert get(role_id="20151", user_id=str(OWNER), scope="weird")["error"]["code"] == 422
    assert get(role_id="20151", user_id=str(OWNER), as_of="2026/10/14")["error"]["code"] == 422


# ═══ 1. 他團隊資源折疊 ═════════════════════════════════════════════════════
def _inject_foreign_team(api):
    """在替身狀態裡放一個他團隊（role 30999）的物件＋其上的合約，且宣告對兩位成員『可見』——
    這樣擋住的原因只可能是『歸屬』，不是『不存在』或『不可見』。fixture 檔 ⛔ 放他團隊列
    （/bills、/contracts/status-overview 不依 role 過濾，放進去會漏給本團隊的查詢）。"""
    t = api._mock_transport.inner
    est = dict(t.estate_fixtures.rows()[0], id=9100001, role_id=FOREIGN_ROLE, team_id=FOREIGN_ROLE)
    t.estate_fixtures.create(est)
    con = dict(t.contract_fixtures.rows()[0], id=9100101, estate_id=9100001)
    t.contract_fixtures.create(con)
    t._created_visible[("estate", 9100001)] = [OWNER, PART]
    t._created_visible[("contract", 9100101)] = [OWNER, PART]


def _counts(api):
    t = api._mock_transport.inner
    return (len(t.estate_fixtures.rows()), len(t.contract_fixtures.rows()),
            len(t.fixtures.rows()), len(t.repair_fixtures.rows()))


def test_foreign_and_missing_resources_fold_to_the_same_error(api):
    _inject_foreign_team(api)
    before = _counts(api)
    contract = {"date_start": "2026-11-01", "date_end": "2027-10-31", "rent": 20000,
                "to_user_email": "t@example.com"}
    foreign = _run(api.assistant_create_contract("20151", str(OWNER), {**contract, "estate_id": 9100001}))
    missing = _run(api.assistant_create_contract("20151", str(OWNER), {**contract, "estate_id": 98765432}))
    assert foreign == missing == {"success": False, "error": {"code": 404, "message": FOLD}}
    bill = {"title": "清潔費", "total": 500, "date_expire": "2026-11-30"}
    f2 = _run(api.assistant_create_bill("20151", str(OWNER), {**bill, "contract_id": 9100101}))
    m2 = _run(api.assistant_create_bill("20151", str(OWNER), {**bill, "contract_id": 98765432}))
    assert f2 == m2 == {"success": False, "error": {"code": 404, "message": FOLD}}
    rep = dict(estate_id=9100001, category_id=1, item_id=1, broken_reason="斷裂")
    f3 = _run(api.create_repair("20151", user_id=str(OWNER), **rep))
    m3 = _run(api.create_repair("20151", user_id=str(OWNER), **{**rep, "estate_id": 98765432}))
    assert f3 == m3 == {"success": False, "error": {"code": 404, "message": FOLD}}
    f4 = _run(api.create_repair("20151", user_id=str(OWNER), **{**rep, "estate_id": 25817, "contract_id": 9100101}))
    assert f4["error"] == {"code": 404, "message": FOLD}
    assert _counts(api) == before                                   # 狀態不變


def test_own_team_resource_invisible_to_member_also_folds(api, raw):
    """同團隊但這位成員看不到 ⇒ 折疊；換看得到的成員則成功（證明是可見性在擋，不是壞掉）。"""
    hidden_estate = next(e["id"] for e in raw["estates"] if PART not in raw["estate_visibility"][str(e["id"])])
    contract = {"estate_id": hidden_estate, "date_start": "2026-11-01", "date_end": "2027-10-31",
                "rent": 18000, "to_user_phone": "0900-000-123"}
    assert _run(api.assistant_create_contract("20151", str(PART), contract))["error"]["code"] == 404
    ok = _run(api.assistant_create_contract("20151", str(OWNER), contract))
    assert ok["success"] is True
    hidden_contract = next(c["id"] for c in raw["contracts"] if PART not in raw["contract_visibility"][str(c["id"])])
    bill = {"contract_id": hidden_contract, "title": "管理費", "total": 800, "date_expire": "2026-11-30"}
    assert _run(api.assistant_create_bill("20151", str(PART), bill))["error"]["code"] == 404
    assert _run(api.assistant_create_bill("20151", str(OWNER), bill))["success"] is True


# ═══ 2. 歸屬欄位／未知欄位 422 ═════════════════════════════════════════════
@pytest.mark.parametrize("extra", [{"team_id": 30999}, {"owner_user_id": 1}, {"to_user_id": 5},
                                   {"vendor_id": 4}, {"not_a_field": "x"}])
def test_body_with_ownership_or_unknown_field_is_422(api, extra):
    before = _counts(api)
    est = {"title": "測試物件", "city": "台北市", "district": "大安區", "address": "合成路1號",
           "use_for": "residential"}
    con = {"estate_id": 25817, "date_start": "2026-11-01", "date_end": "2027-10-31", "rent": 1000,
           "to_user_email": "a@b.co"}
    bil = {"contract_id": 89481, "title": "x", "total": 10, "date_expire": "2026-11-30"}
    rep = {"estate_id": 25817, "category_id": 1, "item_id": 1, "broken_reason": "斷裂"}
    results = [
        _run(api.assistant_create_estate("20151", str(OWNER), {**est, **extra})),
        _run(api.assistant_create_contract("20151", str(OWNER), {**con, **extra})),
        _run(api.assistant_create_bill("20151", str(OWNER), {**bil, **extra})),
    ]
    t = api._mock_transport                                          # 繞過 API 層直接送 repair body
    results.append(_run(t.send("POST", "/api/external/v1/repairs",
                               data={"role_id": "20151", "user_id": str(OWNER), **rep, **extra})))
    marker = "不支援的欄位" if "not_a_field" in extra else "歸屬欄位"      # 兩種原因要分得出來
    for r in results:
        assert r["success"] is False and r["error"]["code"] == 422, (extra, r)
        assert marker in r["error"]["message"], (extra, r)
    assert _counts(api) == before


def test_identity_keys_in_fields_cannot_override_the_login_identity(api):
    """fields 夾帶 role_id／user_id 不會蓋掉登入身分（API 層覆寫）；送到 JGB 的 body 只有登入身分。"""
    _run(api.assistant_create_bill("20151", str(OWNER), {
        "role_id": "30999", "user_id": "1", "contract_id": 89481, "title": "x", "total": 10,
        "date_expire": "2026-11-30"}))
    body = api._mock_transport.bodies[-1]
    assert (body["role_id"], body["user_id"]) == ("20151", str(OWNER))


# ═══ 寫入成功路徑：照使用者給的值 ═════════════════════════════════════════
def test_create_estate_stores_exactly_the_given_values(api):
    r = _run(api.assistant_create_estate("20151", str(PART), {
        "title": "合成新物件", "city": "台北市", "district": "大安區", "address": "合成路9號",
        "use_for": "residential", "rent": 23000}))
    assert r["success"] is True
    d = r["data"]
    assert (d["title"], d["city"], d["district"], d["address"], d["rent"]) == (
        "合成新物件", "台北市", "大安區", "合成路9號", 23000)
    assert (d["role_id"], d["team_id"], d["user_id"]) == (20151, 20151, PART)   # 歸屬取自登入身分
    assert d["size"] is None and d["room_count"] is None                        # 沒給的不補隨機值
    listed = _run(api._mock_transport.send(
        "GET", "/api/external/v1/estates", params={"role_id": "20151", "keyword": "合成新物件"}))
    assert [e["id"] for e in listed["data"]] == [d["id"]]                        # 讀得回來
    bad = _run(api.assistant_create_estate("20151", str(OWNER), {
        "title": "x", "city": "不存在市", "district": "某區", "address": "a", "use_for": "residential"}))
    assert bad["error"]["code"] == 422
    miss = _run(api.assistant_create_estate("20151", str(OWNER), {"title": "x"}))
    assert miss["error"]["code"] == 400


def test_created_contract_and_bill_are_stored_and_visible_to_creator(api):
    c = _run(api.assistant_create_contract("20151", str(PART), {
        "estate_id": 67603, "date_start": "2026-11-01", "date_end": "2026-12-31", "rent": 15500,
        "deposit_amount": 31000, "to_user_email": "tenant@example.com"}))
    assert c["success"] is True
    d = c["data"]
    assert (d["rent"], d["deposit_amount"], d["date_start"], d["date_end"], d["to_user_email"]) == (
        15500, 31000, 20261101, 20261231, "tenant@example.com")
    assert "to_user_id" not in d                                                # 內部欄位不外洩
    # 建立者與擁有者在到期查詢裡看得到新合約（沒有拋 Unsupported）
    for viewer in (PART, OWNER):
        assert d["id"] in _ids(_run(api.get_expiring_contracts("20151", str(viewer), months=3, as_of=AS_OF)))
    b = _run(api.assistant_create_bill("20151", str(PART), {
        "contract_id": 85516, "title": "清潔費", "total": 1200, "date_expire": "2026-11-30"}))
    assert b["success"] is True and (b["data"]["total"], b["data"]["date_expire"], b["data"]["type"]) == (
        1200, 20261130, 3)
    assert _run(api.assistant_create_contract("20151", str(OWNER), {
        "estate_id": 67603, "date_start": "2026-12-31", "date_end": "2026-12-01", "rent": 1,
        "to_user_email": "a@b.co"}))["error"]["code"] == 422                    # 結束早於起始


def test_idempotent_replay_returns_same_receipt_without_duplicate(api):
    fields = {"contract_id": 85516, "title": "x", "total": 10, "date_expire": "2026-11-30"}
    one = _run(api.assistant_create_bill("20151", str(OWNER), fields, idempotency_key="k1"))
    n = len(api._mock_transport.inner.fixtures.rows())
    two = _run(api.assistant_create_bill("20151", str(OWNER), fields, idempotency_key="k1"))
    assert one == two and len(api._mock_transport.inner.fixtures.rows()) == n


def test_repair_with_photos_stores_metadata_and_validates_it(api):
    photo = {"filename": "a.jpg", "content_type": "image/jpeg", "size": 1024, "sha256": SHA}
    base = dict(estate_id=25817, category_id=1, item_id=1, broken_reason="斷裂")
    ok = _run(api.create_repair("20151", user_id=str(PART), broken_photos=[photo], **base))
    assert ok["success"] is True
    row = ok["data"]
    assert row["broken_photos"] == [photo] and row["user_id"] == PART
    assert row["estate_title"] and row["category_name"] == "電路" and row["item_name"] == "電線"
    # 新建修繕單在建立者與擁有者的「執行中」清單裡
    for viewer in (PART, OWNER):
        assert row["id"] in _ids(_run(api.get_in_progress_repairs("20151", str(viewer), per_page=200)))
    for bad in ([{**photo, "content_type": "application/pdf"}], [{**photo, "size": 5 * 1024 * 1024 + 1}],
                [{**photo, "sha256": "zz"}], [{**photo, "extra": 1}], [photo] * 11, ["http://x/a.jpg"]):
        r = _run(api.create_repair("20151", user_id=str(OWNER), broken_photos=bad, **base))
        assert r["error"]["code"] == 422, bad
    # UD-3：上限 5→10——10 張可收（正對照：11 張在上面被擋）
    ten = _run(api.create_repair("20151", user_id=str(OWNER), broken_photos=[photo] * 10, **base))
    assert ten["success"] is True and len(ten["data"]["broken_photos"]) == 10
    miss = _run(api.create_repair("20151", **base))                              # 缺 viewer
    assert miss["error"]["code"] == 400


# ═══ 3. RecordingTransport 記 body ═════════════════════════════════════════
def test_recording_transport_records_bodies_and_keeps_calls_shape(api):
    fields = {"contract_id": 85516, "title": "x", "total": 10, "date_expire": "2026-11-30"}
    _run(api.get_in_progress_repairs("20151", str(OWNER)))
    _run(api.assistant_create_bill("20151", str(OWNER), fields, idempotency_key="rec-1"))
    rec = api._mock_transport
    assert all(isinstance(c, tuple) and len(c) == 3 for c in rec.calls)          # 既有三元組形狀
    assert len(rec.bodies) == len(rec.calls)
    assert rec.calls[0][:2] == ("GET", "/api/external/v1/repairs/in-progress") and rec.bodies[0] is None
    assert rec.calls[1][:2] == ("POST", "/api/external/v1/bills/manual")
    assert rec.bodies[1] == {**fields, "role_id": "20151", "user_id": str(OWNER), "idempotency_key": "rec-1"}
    rec.bodies[1]["total"] = 999999                                              # 改紀錄不影響已送出的
    assert rec.inner.fixtures.rows()[-1]["total"] == 10
    sent = {"a": {"b": 1}}
    # 深拷貝：事後改原 dict 不影響紀錄
    r = RecordingTransport(_Echo())
    _run(r.send("POST", "/x", data=sent))
    sent["a"]["b"] = 2
    assert r.bodies[0] == {"a": {"b": 1}}


class _Echo:
    async def send(self, method, path, *, params=None, data=None):
        return {"success": True}


# ═══ S1：既有讀取端點依成員可見範圍過濾（jgb2-req#24／DSP-074；plan §3d）═══════════════
# 期望值一律由測試自己讀 fixture 原始 JSON 的 `*_visibility` 獨立算出，不引用被測物的輸出。
def _contract_ids(resp):
    return sorted(r["id"] for r in resp["data"])


def _oracle_contracts(raw, viewer):
    return sorted(c["id"] for c in raw["contracts"]
                  if c.get("active") == 1 and c.get("is_newest") == 1
                  and viewer in raw["contract_visibility"][str(c["id"])])


def test_contracts_index_filters_by_viewer_user_id(api, raw):
    """合約域：12291 與 990002 以 get_contracts(role_id, viewer_user_id=…) 回傳的 id 集合不同。"""
    owner = _run(api.get_contracts("20151", viewer_user_id=str(OWNER)))
    part = _run(api.get_contracts("20151", viewer_user_id=str(PART)))
    assert _contract_ids(owner) == _oracle_contracts(raw, OWNER)
    assert _contract_ids(part) == _oracle_contracts(raw, PART)
    assert set(_contract_ids(part)) < set(_contract_ids(owner))          # 真子集：不是兩人一樣
    assert any(PART not in raw["contract_visibility"][str(c["id"])] for c in raw["contracts"])  # 正對照：確有看不到的
    # 沒帶 viewer ⇒ 維持現行（整個 role），證明過濾是 viewer 帶來的而不是 fixture 少了資料
    assert _contract_ids(_run(api.get_contracts("20151"))) == _oracle_contracts(raw, OWNER)


def test_contracts_viewer_filter_is_off_for_non_assistant_fixture(monkeypatch):
    """非 assistant fixture（conftest 預設的 regression）下 viewer_user_id 照舊被忽略：既有行為不變。"""
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    a = api_mod.JGBSystemAPI()
    without = _contract_ids(_run(a.get_contracts("20151")))
    with_viewer = _contract_ids(_run(a.get_contracts("20151", viewer_user_id="12291")))
    assert without and with_viewer == without


def test_repairs_filter_by_viewer_user_id(api, raw):
    def ids(viewer):
        return sorted(r["id"] for r in _run(api.get_repairs("20151", str(OWNER), viewer_user_id=str(viewer)))["data"])

    want = lambda v: sorted(r["id"] for r in raw["repairs"] if _visible(raw, "repair", r["id"], v))
    assert ids(OWNER) == want(OWNER) and ids(PART) == want(PART)
    assert set(ids(PART)) < set(ids(OWNER))
    assert len(_run(api.get_repairs("20151", str(OWNER)))["data"]) == len(raw["repairs"])    # 沒帶 viewer ⇒ 全部


def test_estates_filter_by_viewer_user_id(api, raw):
    def ids(viewer):
        return sorted(e["id"] for e in _run(api.get_estate_status("20151", viewer_user_id=str(viewer)))["data"]
                      if e.get("found") is not False)

    want = lambda v: sorted(e["id"] for e in raw["estates"]
                            if e.get("active") == 1 and e.get("is_open") == 1 and _visible(raw, "estate", e["id"], v))
    assert ids(OWNER) == want(OWNER) and ids(PART) == want(PART)
    assert set(ids(PART)) < set(ids(OWNER))


def test_meters_filter_by_viewer_user_id(api, raw):
    owner = _run(api.get_meters("20151", viewer_user_id=str(OWNER)))["data"]
    part = _run(api.get_meters("20151", viewer_user_id=str(PART)))["data"]
    assert sorted(m["id"] for m in owner) == sorted(m["id"] for m in raw["meters"])
    assert sorted(m["id"] for m in part) == sorted(
        m["id"] for m in raw["meters"] if PART in raw["meter_visibility"][str(m["id"])])
    assert len(part) < len(owner)                                     # 兩位成員結果不同
    assert len(_run(api.get_meters("20151"))["data"]) == len(raw["meters"])   # 沒帶 viewer ⇒ 全部


def test_accounts_filter_by_viewer_user_id(api, raw):
    """帳號域：成員清單與單一成員權限都依 account_visibility 過濾；看不到的帳號與『查無此成員』同形。"""
    t = api._mock_transport.inner
    for row in t.team_fixtures._rows:                                  # fixture 的 email／name 是 null，補上才搜得到
        row["name"] = f"成員{row['member_user_id']}"
    owner = _run(api.get_team_members("20151", keyword="成員", viewer_user_id=str(OWNER)))["data"]
    part = _run(api.get_team_members("20151", keyword="成員", viewer_user_id=str(PART)))["data"]
    assert sorted(m["member_user_id"] for m in owner) == [OWNER, PART]
    assert [m["member_user_id"] for m in part] == [PART]               # 非擁有者只看得到自己
    assert len(_run(api.get_team_members("20151", keyword="成員"))["data"]) == 2         # 沒帶 viewer ⇒ 全部
    # 單一成員權限
    assert _run(api.get_member_permissions("20151", str(OWNER), viewer_user_id=str(OWNER)))["success"] is True
    assert _run(api.get_member_permissions("20151", str(PART), viewer_user_id=str(PART)))["success"] is True
    hidden = _run(api.get_member_permissions("20151", str(OWNER), viewer_user_id=str(PART)))
    missing = _run(api.get_member_permissions("20151", "555555", viewer_user_id=str(PART)))
    assert hidden == missing == {"success": False, "data": []}


def test_viewer_user_id_is_forwarded_only_when_given(api):
    """API 層：viewer_user_id 非空才進 params（空值不送，沿 get_bills 先例）。"""
    _run(api.get_meters("20151"))
    _run(api.get_meters("20151", viewer_user_id=str(PART)))
    sent = [dict(c[2] or {}) for c in api._mock_transport.calls if c[1] == "/api/external/v1/meters"]
    assert "viewer_user_id" not in sent[0] and sent[1]["viewer_user_id"] == str(PART)
