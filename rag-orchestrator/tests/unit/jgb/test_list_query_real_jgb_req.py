"""列表統計與查詢對齊真 JGB（plan-list-query-real-jgb-20261029 §4 第 1～6 項）。

被測物：
  - `JGBSystemAPI` 的三支統計方法與 `list_bills_page`：對真 JGB 送出的路徑與參數（jgb2 `origin/staging`：
    `ExternalApiParams::statusList`／`ymd`、`/bills`、`/repairs`、`/contracts/status-overview`）；
  - `JGBMockTransport` 的 `/bills`、`/repairs`、`/contracts/status-overview` 照同一組參數實作，
    並且不再提供三條自訂讀取路由；
  - 寫入一律送 `viewer_user_id`；真 JGB 的修繕單不送照片；延期繳費在真 JGB 不發請求；
  - `scripts/check_jgb_contract.py`：路徑對得上 JGB、沒守衛的外來路徑非 0 退出。
期望值一律由測試自己讀 fixture 原始 JSON 獨立算出，或直接寫 jgb2 的規則。
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from services import jgb_system_api as api_mod
from services.jgb import fixture_store, transport as tr
from services.jgb.transport import RecordingTransport

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "services" / "jgb" / "fixture_data" / "assistant_demo_vendor4.json"
SCRIPT = ROOT / "scripts" / "check_jgb_contract.py"
JGB2 = Path("~/dev/work/jgb2/dev3").expanduser()
OWNER, PART = 12291, 990002
AS_OF = "2026-10-14"


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(scope="module")
def raw():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture()
def api(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.setattr(fixture_store, "_DATA", fixture_store._DATA)
    fixture_store.load_from(FIXTURE)
    a = api_mod.JGBSystemAPI()
    a._mock_transport = RecordingTransport(a._mock_transport)
    return a


class FakeRealTransport:
    """假的「真 JGB」：記下送出的請求，回預先排好的 JGB 形狀回應（⛔ 不碰網路）。"""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.sent: list = []

    async def send(self, method, path, *, params=None, data=None, files=None):
        self.sent.append({"method": method, "path": path, "params": params, "data": data, "files": files})
        return self.responses.pop(0) if self.responses else {"success": True, "data": []}


@pytest.fixture()
def real(monkeypatch):
    """真 JGB 模式的 API（建構需要憑證佔位字串），transport 換成 FakeRealTransport。"""
    monkeypatch.setenv("USE_MOCK_JGB_API", "false")
    monkeypatch.setenv("JGB_API_KEY", "unit-test-placeholder")
    a = api_mod.JGBSystemAPI()
    a._real_transport = FakeRealTransport()
    return a


def _page(rows, total=None, **extra):
    return {"success": True, "data": rows,
            "pagination": {"current_page": 1, "per_page": 50, "total": len(rows) if total is None else total,
                           "has_more": False}, **extra}


# ═══ 1. 真 JGB 的參數對映 ═══════════════════════════════════════════════
def test_unpaid_overdue_sends_status_2_8_and_expire_window_with_summary(real):
    real._real_transport.responses = [_page([{"id": 1, "total": 100}], total=1,
                                            summary={"count": 1, "total_amount": 100})]
    out = _run(real.get_unpaid_bill_summary("20151", "12291", "overdue", as_of=AS_OF))
    sent = real._real_transport.sent[0]
    assert (sent["method"], sent["path"]) == ("GET", "/api/external/v1/bills")
    assert sent["params"] == {
        "role_id": "20151", "viewer_user_id": "12291", "status": "2,8",
        "date_expire_to": "2026-10-13", "sort_by": "date_expire", "sort_direction": "asc", "with_summary": 1}
    assert "user_id" not in sent["params"]                      # /bills 的 user_id 是租客，⛔ 送
    assert out["success"] is True and out["data"]["count"] == 1 and out["data"]["total_amount"] == 100


@pytest.mark.parametrize("kwargs", [
    {"keyword": "安沐居"}, {"bill_ref": "756248"}, {"contract_ids": "85516", "page": 1}])
def test_member_bill_queries_do_not_send_tenant_user_id(real, kwargs):
    # jgb2 `/bills` 的 user_id＝承租方（belongContract.to_user_id）；成員查詢帶 viewer 時送它會濾成空。
    real._real_transport.responses = [_page([]), _page([]), _page([])]
    _run(real.get_bills(role_id="20151", user_id="12291", viewer_user_id="12291", **kwargs))
    assert real._real_transport.sent, "沒有送出請求"
    for sent in real._real_transport.sent:
        if sent["path"] == "/api/external/v1/bills":
            assert sent["params"].get("viewer_user_id") == "12291"
            assert "user_id" not in sent["params"]


def test_tenant_bill_query_without_viewer_keeps_user_id(real):
    # 正對照：沒有 viewer（租客路徑）時 user_id 照送。
    real._real_transport.responses = [_page([])]
    _run(real.get_bills(role_id="20151", user_id="777", keyword="租金"))
    assert real._real_transport.sent[0]["params"].get("user_id") == "777"


def test_unpaid_this_month_window_is_the_calendar_month(real):
    real._real_transport.responses = [_page([], total=0, summary={"count": 0, "total_amount": 0})]
    _run(real.get_unpaid_bill_summary("20151", "12291", "this_month", as_of="2026-02-10"))
    params = real._real_transport.sent[0]["params"]
    assert (params["date_expire_from"], params["date_expire_to"]) == ("2026-02-01", "2026-02-28")


def test_in_progress_repairs_sends_the_five_in_progress_statuses(real):
    real._real_transport.responses = [_page([{"id": 7, "status": 4}], total=1)]
    out = _run(real.get_in_progress_repairs("20151", "12291"))
    sent = real._real_transport.sent[0]
    assert (sent["method"], sent["path"]) == ("GET", "/api/external/v1/repairs")
    assert sent["params"] == {"role_id": "20151", "viewer_user_id": "12291", "status": "1,8,2,4,16"}
    assert out["data"]["count"] == 1 and out["data"]["items"] == [{"id": 7, "status": 4}]


def test_expiring_contracts_sends_date_end_window_and_adds_days_left(real):
    real._real_transport.responses = [_page([{"id": 5, "date_end": 20261114}], total=1)]
    out = _run(real.get_expiring_contracts("20151", "12291", months=3, as_of=AS_OF))
    sent = real._real_transport.sent[0]
    assert (sent["method"], sent["path"]) == ("GET", "/api/external/v1/contracts/status-overview")
    assert sent["params"] == {"role_id": "20151", "viewer_user_id": "12291",
                              "date_end_from": "2026-10-14", "date_end_to": "2027-01-14"}
    assert out["data"]["items"][0]["days_left"] == 31 and out["data"]["window_end"] == "2027-01-14"


def test_month_end_clamps_when_adding_months(real):
    _run(real.get_expiring_contracts("20151", "12291", months=1, as_of="2026-01-31"))
    assert real._real_transport.sent[0]["params"]["date_end_to"] == "2026-02-28"


def test_paging_params_are_forwarded_only_when_given(real):
    real._real_transport.responses = [_page([]), _page([])]
    _run(real.get_in_progress_repairs("20151", "12291"))
    _run(real.get_in_progress_repairs("20151", "12291", page=2, per_page=200))
    first, second = (s["params"] for s in real._real_transport.sent)
    assert "page" not in first and "per_page" not in first
    assert (second["page"], second["per_page"]) == (2, 200)


@pytest.mark.parametrize("call", [
    lambda a: a.get_unpaid_bill_summary("", "12291", "overdue"),
    lambda a: a.get_unpaid_bill_summary("20151", "", "overdue"),
    lambda a: a.get_in_progress_repairs("20151", ""),
    lambda a: a.get_expiring_contracts("", "12291"),
    lambda a: a.list_bills_page("20151", ""),
])
def test_missing_identity_sends_nothing_and_degrades(real, call):
    out = _run(call(real))
    assert out["success"] is False
    assert real._real_transport.sent == []


@pytest.mark.parametrize("call", [
    lambda a: a.get_unpaid_bill_summary("20151", "12291", "yesterday"),     # 範圍值不在 {this_month, overdue}
    lambda a: a.get_unpaid_bill_summary("20151", "12291", "overdue", as_of="2026/10/14"),
    lambda a: a.get_expiring_contracts("20151", "12291", months=0),
    lambda a: a.get_expiring_contracts("20151", "12291", months=True),
    lambda a: a.get_expiring_contracts("20151", "12291", as_of="not-a-date"),
])
def test_invalid_values_are_rejected_before_any_request(real, call):
    out = _run(call(real))
    assert out["success"] is False
    assert real._real_transport.sent == []


# ═══ 2. 上游失敗與形狀不對 ⇒ 失敗回應（工具印 ERROR_TEXT），⛔ 編數字 ═════════
@pytest.mark.parametrize("upstream", [
    {"success": False, "error": {"code": 500, "message": "boom"}},
    {"success": True, "data": {"not": "a list"}, "pagination": {"total": 1}},
    {"success": True, "data": []},                                           # 缺 pagination.total
    {"success": True, "data": [], "pagination": {"total": True}},            # bool 不算整數
    {"success": True, "data": [], "pagination": {"total": -1}},
])
def test_bad_upstream_never_becomes_a_number(real, upstream):
    real._real_transport.responses = [upstream] * 3
    for out in (_run(real.get_unpaid_bill_summary("20151", "12291", "overdue", as_of=AS_OF)),
                _run(real.get_in_progress_repairs("20151", "12291")),
                _run(real.get_expiring_contracts("20151", "12291", as_of=AS_OF))):
        assert out["success"] is False and "count" not in (out.get("data") or {})


def test_unpaid_without_a_consistent_summary_is_a_failure(real):
    for summary in (None, {"count": 1, "total_amount": 5}, {"count": 0, "total_amount": "x"}):
        extra = {} if summary is None else {"summary": summary}
        real._real_transport.responses = [_page([], total=0, **extra)]
        out = _run(real.get_unpaid_bill_summary("20151", "12291", "overdue", as_of=AS_OF))
        assert out["success"] is False, summary


@pytest.mark.asyncio
async def test_stats_tool_prints_error_text_when_upstream_fails(real, monkeypatch):
    from services.agent.tools import jgb2 as jgb2_tools
    from services.agent.tools import jgb2_stats

    import types
    monkeypatch.setattr(jgb2_tools, "_api_singleton", real)
    ident = types.SimpleNamespace(role_id="20151", user_id="12291")
    for fn, args in ((jgb2_stats.in_progress_repairs, {}), (jgb2_stats.expiring_contracts, {}),
                     (jgb2_stats.unpaid_bills, {"scope": "overdue"})):
        real._real_transport.responses = [{"success": False, "error": {"code": 500, "message": "boom"}}]
        res = await fn(ident, args)
        assert jgb2_stats.ERROR_TEXT in json.dumps(res, ensure_ascii=False, default=str)
    assert len(real._real_transport.sent) == 3
    assert all(x["params"]["viewer_user_id"] == "12291" for x in real._real_transport.sent)


# ═══ 3. list_bills_page ═══════════════════════════════════════════════
def test_list_bills_page_sends_viewer_sort_and_paging(real):
    real._real_transport.responses = [_page([], total=0)]
    _run(real.list_bills_page("20151", "12291", sort_by="date_expire", sort_direction="desc",
                              page=1, per_page=8))
    assert real._real_transport.sent[0]["params"] == {
        "role_id": "20151", "viewer_user_id": "12291", "sort_by": "date_expire",
        "sort_direction": "desc", "page": 1, "per_page": 8}


# ═══ 4. 替身照同一組參數實作 ═════════════════════════════════════════════
def _mock_get(api, path, **params):
    return _run(api._mock_transport.send("GET", path, params=params))


def test_mock_no_longer_serves_the_three_proposed_read_routes(api):
    for path in ("/api/external/v1/bills/summary/unpaid", "/api/external/v1/repairs/in-progress",
                 "/api/external/v1/contracts/expiring"):
        with pytest.raises(tr.UnresolvedEndpointError):
            _mock_get(api, path, role_id="20151", viewer_user_id=str(OWNER))
    # 正對照：真端點照常服務
    assert _mock_get(api, "/api/external/v1/bills", role_id="20151", viewer_user_id=str(OWNER))["success"] is True


@pytest.mark.parametrize("path,params", [
    ("/api/external/v1/bills", {"status": "2,x"}),
    ("/api/external/v1/bills", {"status": "3"}),                       # 不在 FILTERABLE_STATUSES
    ("/api/external/v1/bills", {"date_expire_from": "2026/10/01"}),
    ("/api/external/v1/bills", {"date_expire_to": "20261001"}),
    ("/api/external/v1/repairs", {"status": "9"}),
    ("/api/external/v1/repairs", {"status": "1,,2"}),
    ("/api/external/v1/contracts/status-overview", {"date_end_from": "2026-13-01"}),
    ("/api/external/v1/contracts/status-overview", {"date_end_to": "tomorrow"}),
])
def test_mock_rejects_bad_values_with_400(api, path, params):
    resp = _mock_get(api, path, role_id="20151", viewer_user_id=str(OWNER), **params)
    assert resp["success"] is False and resp["error"]["code"] == 400


def test_mock_bills_status_window_summary_and_paging_match_the_fixture(api, raw):
    expected = [b for b in raw["bills"]
                if b["status"] in (1, 2) and OWNER in raw["bill_visibility"][str(b["id"])]]
    resp = _mock_get(api, "/api/external/v1/bills", role_id="20151", viewer_user_id=str(OWNER),
                     status="1,2", with_summary=1, per_page=3, sort_by="date_expire", sort_direction="asc")
    assert resp["pagination"]["total"] == len(expected) and len(resp["data"]) == 3
    assert resp["summary"] == {"count": len(expected), "total_amount": sum(b["total"] for b in expected)}
    dates = [b["date_expire"] for b in resp["data"]]
    assert dates == sorted(dates)
    # 日期範圍含兩端
    one = expected[0]["date_expire"]
    d = f"{str(one)[:4]}-{str(one)[4:6]}-{str(one)[6:]}"
    both = _mock_get(api, "/api/external/v1/bills", role_id="20151", viewer_user_id=str(OWNER),
                     status="1,2", date_expire_from=d, date_expire_to=d)
    assert both["pagination"]["total"] == sum(1 for b in expected if b["date_expire"] == one) >= 1


def test_mock_viewer_user_id_narrows_results_and_other_viewers_differ(api):
    own = _mock_get(api, "/api/external/v1/bills", role_id="20151", viewer_user_id=str(OWNER))
    part = _mock_get(api, "/api/external/v1/bills", role_id="20151", viewer_user_id=str(PART))
    assert part["pagination"]["total"] < own["pagination"]["total"]


def test_mock_repairs_multi_status_and_paging(api, raw):
    ids = {r["id"] for r in raw["repairs"] if r["status"] in (4, 8)}
    resp = _mock_get(api, "/api/external/v1/repairs", role_id="20151", viewer_user_id=str(OWNER),
                     status="4,8", per_page=200)
    assert {r["id"] for r in resp["data"]} == ids and resp["pagination"]["total"] == len(ids)
    page = _mock_get(api, "/api/external/v1/repairs", role_id="20151", viewer_user_id=str(OWNER), per_page=5)
    assert len(page["data"]) == 5 and page["pagination"]["has_more"] is True


def test_mock_contract_end_window_only_returns_signed_non_history(api, raw):
    resp = _mock_get(api, "/api/external/v1/contracts/status-overview", role_id="20151",
                     viewer_user_id=str(OWNER), date_end_from="2026-10-14", date_end_to="2027-04-14")
    got = sorted(c["id"] for c in resp["data"])
    want = sorted(c["id"] for c in raw["contracts"]
                  if c.get("is_history") == 0 and (c.get("bit_status") or 0) & 8
                  and c.get("active") == 1 and c.get("is_newest") == 1
                  and 20261014 <= c["date_end"] <= 20270414
                  and OWNER in raw["contract_visibility"][str(c["id"])])
    assert got == want and want
    # 不帶 date_end_*：未簽名的合約（85516）仍在列表裡
    plain = _mock_get(api, "/api/external/v1/contracts/status-overview", role_id="20151",
                      viewer_user_id=str(OWNER), per_page=200)
    assert 85516 in {c["id"] for c in plain["data"]}


# ═══ 5. 寫入送 viewer_user_id；真 JGB 的修繕單不送照片 ═══════════════════════
def test_real_repair_create_sends_json_without_photos_and_with_viewer(real):
    real._real_transport.responses = [{"success": True, "data": {"id": 1}}]
    photo = {"filename": "a.jpg", "content_type": "image/jpeg", "size": 3, "sha256": "a" * 64}
    out = _run(real.create_repair("20151", 25817, 1, 1, "斷裂", user_id="12291", broken_photos=[photo],
                                  photo_files=[("a.jpg", b"abc", "image/jpeg")], idempotency_key="k"))
    sent = real._real_transport.sent[0]
    assert out["success"] is True
    assert (sent["method"], sent["path"]) == ("POST", "/api/external/v1/repairs")
    assert sent["files"] is None and "broken_photos" not in sent["data"]
    assert sent["data"]["viewer_user_id"] == "12291" and "user_id" not in sent["data"]
    assert sent["data"]["idempotency_key"] == "k"


def test_mock_repair_create_keeps_the_multipart_path(api):
    _run(api.create_repair("20151", 25817, 1, 1, "斷裂", user_id=str(OWNER),
                           photo_files=[("a.jpg", b"abc", "image/jpeg")]))
    assert api._mock_transport.files[-1] is not None             # 替身仍收 multipart（正對照）


def test_real_due_date_patch_sends_nothing(real):
    out = _run(real.agent_patch_bill_due_date(1, "2027-01-01", role_id="20151", user_id="12291"))
    assert out["success"] is False and real._real_transport.sent == []


def test_mock_due_date_patch_carries_viewer_user_id(api):
    _run(api.agent_patch_bill_due_date(1, "2027-01-01", role_id="20151", user_id=str(OWNER)))
    body = api._mock_transport.bodies[-1]
    assert body["viewer_user_id"] == str(OWNER) and "user_id" not in body


def test_mock_writes_accept_viewer_user_id_and_reject_the_old_key(api):
    ok = _run(api.assistant_create_bill("20151", str(OWNER), {
        "contract_id": 85516, "title": "x", "total": 10, "date_expire": "2026-11-30"}))
    assert ok["success"] is True
    bad = _run(api._mock_transport.send("POST", "/api/external/v1/bills/manual", data={
        "role_id": "20151", "user_id": str(OWNER), "contract_id": 85516, "title": "x", "total": 10,
        "date_expire": "2026-11-30"}))
    assert bad["success"] is False                               # 舊鍵名 user_id 不是 JGB 認的身分鍵


# ═══ 6. 出卡前攔下：延期繳費；修繕照片的卡外提醒 ═══════════════════════════
def test_photo_notice_is_outside_the_card_and_only_on_real_jgb(monkeypatch):
    from services.agent import confirm_card
    from services.agent.tools import confirm as confirm_mod

    text = confirm_mod.REPAIR_PHOTOS_NOT_ATTACHABLE_HINT
    assert "照片" in text and "不會送出" in text and "{" not in text           # 固定句、無插值
    assert "REPAIR_PHOTOS_NOT_ATTACHABLE_HINT" in confirm_mod.__all__
    # 提醒在卡外（`hint`）：卡的欄位與雜湊輸入都不含這句
    payload = {"action": "repair_create", "estate_name": "測試物件", "description": "椅面破了",
               "broken_photos": [{"filename": "photo-1.jpg", "content_type": "image/jpeg",
                                  "size": 3, "sha256": "a" * 64}]}
    assert text not in json.dumps(confirm_card.render("repair_create", payload), ensure_ascii=False, default=str)


# ═══ 7. 契約檢查腳本 ═══════════════════════════════════════════════════
def _check(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          cwd=str(ROOT), timeout=120)


def test_contract_script_missing_checkout_is_loud_nonzero():
    r = _check("--jgb2", "/nonexistent/jgb2-checkout")
    assert r.returncode == 2 and "工具壞了" in r.stdout + r.stderr


@pytest.mark.skipif(not (JGB2 / ".git").exists(), reason="本機沒有 jgb2 checkout")
def test_contract_script_passes_and_catches_an_unguarded_fake_path():
    ok = _check()
    out = ok.stdout
    assert ok.returncode == 0, out
    assert "正對照 GET /api/external/v1/bills：兩邊都有" in out
    assert "不在 JGB、沒守衛：0 條" in out and "結果：通過" in out
    bad = _check("--extra-send", "GET /api/external/v1/bills/summary/unpaid")
    assert bad.returncode == 1 and "不在 JGB、沒守衛：1 條" in bad.stdout and "結果：不通過" in bad.stdout
