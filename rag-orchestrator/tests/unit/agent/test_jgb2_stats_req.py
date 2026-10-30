"""站內幫手 S1：`jgb2.stats.*` 三支唯讀統計／清單工具（plan-assistant-11-items-20261014 §3d；DSP-074；F7）。

命題（每條都附「改壞會紅」的變異，見回報）：
  1. 兩位成員結果不同：同一工具、不同 viewer（12291 全部可見 / 990002 部分可見）⇒ 筆數、總額、清單不同，
     且 990002 的結果裡一筆都不含他看不到的資料；期望值由測試自己讀 fixture 原始 JSON 獨立算出；
  2. 缺 user_id（或缺 role_id）⇒ `NO_MATCH`、⛔ 不發出任何 API 呼叫；補上 user_id 就過（正對照）；
  3. F7：`success:false` ⇒ 固定句 `ERROR_TEXT`、⛔ 不印 0 / 空清單；真空資料（`success:true, count:0`）是另一回事；
  4. 明細分頁（S1 修正②③）：每頁 ≤20 筆、「共 N 筆」＋該頁＋「還有 M 筆，要看下一頁嗎」、`page` 參數、超頁訊息；
     provenance 單位＝一句總計＋逐筆明細（每筆可單獨引用）；
  5. 工具參數含身分鍵被拒：spec 的 input_schema 不得含身分鍵（`register()` 擋）、呼叫端夾帶的身分鍵被剝除
     且不影響送給 API 的身分。
"""
import json
import types
from pathlib import Path

import pytest

from services import jgb_system_api as api_mod
from services.agent import mcp_facade as F
from services.agent.identity import Identity
from services.agent.tools import jgb2, jgb2_stats as S
from services.agent.tools.registry import ToolRegistry, _IDENTITY_KEYS
from services.jgb import fixture_store

pytestmark = [pytest.mark.unit, pytest.mark.req("agentic-mcp-orchestration:1.5")]

FIXTURE = (Path(__file__).resolve().parents[3]
           / "services" / "jgb" / "fixture_data" / "assistant_demo_vendor4.json")
OWNER, PART = 12291, 990002
AS_OF = "2026-10-14"


def _ident(role_id="20151", user_id=str(OWNER)):
    return types.SimpleNamespace(role_id=role_id, user_id=user_id)


@pytest.fixture(scope="module")
def raw():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


# ── 真替身（assistant fixture）＋固定 as_of：驗『兩位成員結果不同』 ────────────────
class _FixedAsOfApi(api_mod.JGBSystemAPI):
    """與真 `JGBSystemAPI` 完全相同，只把 `as_of` 釘成 2026-10-14（替身預設用伺服器今日，會讓期望值隨日期漂）。"""

    async def get_unpaid_bill_summary(self, role_id, user_id, scope, as_of=None, **kw):
        return await super().get_unpaid_bill_summary(role_id, user_id, scope, as_of=AS_OF, **kw)

    async def get_expiring_contracts(self, role_id, user_id, months=3, as_of=None, **kw):
        return await super().get_expiring_contracts(role_id, user_id, months=months, as_of=AS_OF, **kw)


@pytest.fixture()
def real_api(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.setattr(fixture_store, "_DATA", fixture_store._DATA)       # 讓 monkeypatch 負責還原
    fixture_store.load_from(FIXTURE)
    api = _FixedAsOfApi()
    monkeypatch.setattr(jgb2, "_api_singleton", api)
    return api


def _listed_ids(text, label):
    """從 facts 逐行抓出『<label> <id>、』的編號（label：帳單編號／單號／合約編號）。"""
    out = []
    for line in text.splitlines():
        if line.startswith(label + " "):
            out.append(int(line[len(label) + 1:].split("、", 1)[0]))
    return out


async def _all_pages(fn, ident, args, label):
    """逐頁取完（照工具回的 `total_pages`），回傳 (所有明細編號, 各頁結果)。"""
    ids, results, page = [], [], 1
    while True:
        r = await fn(ident, {**args, "page": page})
        assert r["ok"] is True and r["data"].get("upstream_error") is None
        results.append(r)
        ids += _listed_ids(r["text_for_model"], label)
        if page >= r["data"]["total_pages"]:
            return ids, results
        page += 1


def _oracle_unpaid(raw, viewer, scope):
    out = []
    for b in raw["bills"]:
        if b["status"] not in (2, 8) or viewer not in raw["bill_visibility"][str(b["id"])]:
            continue
        if scope == "overdue" and b["date_expire"] < 20261014:
            out.append(b)
        if scope == "this_month" and 20261001 <= b["date_expire"] <= 20261031:
            out.append(b)
    return out


@pytest.mark.parametrize("scope", ["overdue", "this_month"])
async def test_unpaid_bills_two_members_get_different_results(real_api, raw, scope):
    results = {}
    for viewer in (OWNER, PART):
        want = _oracle_unpaid(raw, viewer, scope)
        ids, rs = await _all_pages(S.unpaid_bills, _ident(user_id=str(viewer)), {"scope": scope}, "帳單編號")
        r, text = rs[0], rs[0]["text_for_model"]
        assert sorted(ids) == sorted(b["id"] for b in want)                    # 逐頁取完、不多不少
        assert f"共 {len(want)} 筆" in text
        assert f"總額 NT$ {sum(b['total'] for b in want):,}" in text           # 每頁都帶全量總額
        assert r["data"]["count"] == len(want) and r["data"]["total_amount"] == sum(b["total"] for b in want)
        results[viewer] = (set(b["id"] for b in want), r["data"]["total_amount"])
    assert results[PART][0] < results[OWNER][0] and results[PART][1] != results[OWNER][1]   # 990002 是真子集
    assert (results[OWNER][0], results[PART][0]) != (set(), set())                           # 正對照：不是兩邊都空


async def test_in_progress_repairs_two_members_get_different_results_and_paginate(real_api, raw):
    ids = {}
    for viewer in (OWNER, PART):
        want = sorted(x["id"] for x in raw["repairs"]
                      if x["status"] in (1, 2, 4, 8, 16) and viewer in raw["repair_visibility"][str(x["id"])])
        got, rs = await _all_pages(S.in_progress_repairs, _ident(user_id=str(viewer)), {}, "單號")
        assert sorted(got) == want and f"共 {len(want)} 筆" in rs[0]["text_for_model"]
        ids[viewer] = set(got)
    assert len(ids[OWNER]) == 77 > 5
    assert ids[PART] < ids[OWNER]
    closed = {x["id"] for x in raw["repairs"] if x["status"] in (32, 64)}
    assert closed and not (ids[OWNER] & closed)               # 結單、封存不出現（正對照：確實有結案列存在）


async def test_repairs_77_rows_page_1_has_20_page_4_has_17_and_beyond_is_a_clear_message(real_api):
    """S1 修正②（A5）：77 筆 ⇒ 共 77 筆＋第 1 頁 20 筆＋「還有 57 筆，要看下一頁嗎」；第 4 頁 17 筆；第 5 頁明確訊息。"""
    ident = _ident(user_id=str(OWNER))
    p1 = await S.in_progress_repairs(ident, {})                        # 缺省＝第 1 頁
    t1 = p1["text_for_model"]
    assert len(_listed_ids(t1, "單號")) == 20
    assert "共 77 筆" in t1 and "還有 57 筆，要看下一頁嗎？" in t1
    assert p1["data"]["page"] == 1 and p1["data"]["total_pages"] == 4 and p1["data"]["listed"] == 20
    p2 = await S.in_progress_repairs(ident, {"page": 2})
    assert not set(_listed_ids(t1, "單號")) & set(_listed_ids(p2["text_for_model"], "單號"))   # 頁與頁不重疊
    p4 = await S.in_progress_repairs(ident, {"page": 4})
    t4 = p4["text_for_model"]
    assert len(_listed_ids(t4, "單號")) == 17 and "第 61 到 77 筆" in t4 and "已是最後一頁" in t4
    assert "要看下一頁嗎" not in t4
    p5 = await S.in_progress_repairs(ident, {"page": 5})
    t5 = p5["text_for_model"]
    assert p5["ok"] is True and "共 77 筆，只有 4 頁，沒有第 5 頁" in t5 and _listed_ids(t5, "單號") == []
    assert S.ERROR_TEXT not in t5                                      # 超頁不是上游錯誤


@pytest.mark.parametrize("bad", [0, -1, True, "2", 1.5, None])
async def test_bad_page_is_invalid_input_and_sends_nothing(fake, bad):
    api = fake(resp=_unpaid_page([], 0, 0))
    for fn, args in ((S.unpaid_bills, {"scope": "overdue"}), (S.in_progress_repairs, {}),
                     (S.expiring_contracts, {})):
        assert await fn(_ident(), {**args, "page": bad}) == {"ok": False, "error": "INVALID_INPUT"}
    assert api.calls == []


async def test_expiring_contracts_default_3_months_and_two_members_differ(real_api):
    def ids(r):
        return _listed_ids(r["text_for_model"], "合約編號")

    # JGB `/contracts/status-overview` 帶 `date_end_*` 時只回已簽名完成（bit_status & 8）的非歷史合約：
    # 85516（bit_status=1，未簽）在 2026-10-31 到期但不在列（真 JGB 同樣不會列），990101／990102 是已簽名合約。
    owner3 = await S.expiring_contracts(_ident(user_id=str(OWNER)), {})
    assert ids(owner3) == [990101]                                           # 預設 3 個月（到 2027-01-14）
    owner6 = await S.expiring_contracts(_ident(user_id=str(OWNER)), {"months": 6})
    part6 = await S.expiring_contracts(_ident(user_id=str(PART)), {"months": 6})
    assert sorted(ids(owner6)) == [990101, 990102]                           # 順序＝JGB 預設（id 新到舊），不在此釘
    assert ids(part6) == [990101]                                            # 990102 在 990002 看不到的物件上
    assert 85516 not in ids(owner6)                                          # 未簽名合約不列（對齊 JGB）
    assert "剩 " in owner6["text_for_model"] and "天）" in owner6["text_for_model"]   # days_left 由 date_end 算出
    assert "6 個月內到期" in owner6["text_for_model"] and "共 2 筆，以下全部列出" in owner6["text_for_model"]
    assert owner6["data"]["months"] == 6


# ── 假 API：固定回應，驗身分閘、F7、全列 ─────────────────────────────────────────
_UNSET = object()


class _FakeApi:
    def __init__(self, pages=None, resp=_UNSET):
        self.calls = []
        self.pages = pages          # {page: response}
        self.resp = resp            # 單一固定回應（優先於 pages）

    def _answer(self, name, *args, **kw):
        self.calls.append((name, args, kw))
        if self.resp is not _UNSET:
            return self.resp
        return self.pages[kw.get("page", 1)]

    async def get_unpaid_bill_summary(self, *a, **k):
        return self._answer("unpaid", *a, **k)

    async def get_in_progress_repairs(self, *a, **k):
        return self._answer("repairs", *a, **k)

    async def get_expiring_contracts(self, *a, **k):
        return self._answer("expiring", *a, **k)


@pytest.fixture()
def fake(monkeypatch):
    def _install(**kw):
        api = _FakeApi(**kw)
        monkeypatch.setattr(jgb2, "_api_singleton", api)
        return api
    return _install


def _bill(i, total=100):
    return {"id": i, "contract_id": 1, "estate_id": 2, "title": f"帳單{i}", "sub_title": None,
            "total": total, "currency": "TWD", "date_expire": 20260901, "status": 2}


def _unpaid_page(items, count, total, has_more=False):
    return {"success": True, "data": {"scope": "overdue", "as_of": AS_OF, "currency": "TWD",
                                      "count": count, "total_amount": total, "items": items},
            "pagination": {"has_more": has_more}}


CALLS = [
    ("unpaid_bills", {"scope": "overdue"}),
    ("in_progress_repairs", {}),
    ("expiring_contracts", {}),
]


@pytest.mark.parametrize("name,args", CALLS)
async def test_missing_user_id_or_role_id_is_no_match_and_sends_nothing(fake, name, args):
    api = fake(resp={"success": True, "data": {"count": 0, "items": [], "total_amount": 0}, "pagination": {}})
    fn = getattr(S, name)
    for ident in (_ident(user_id=None), _ident(user_id=""), _ident(role_id=None),
                  types.SimpleNamespace()):
        assert await fn(ident, args) == {"ok": False, "error": "NO_MATCH"}
    assert api.calls == []                                   # ⛔ 沒有退回整個 role 的查詢
    ok = await fn(_ident(), args)                            # 正對照：補齊雙證就會查
    assert ok["ok"] is True and len(api.calls) == 1


@pytest.mark.parametrize("name,args", CALLS)
async def test_pm_single_proof_is_not_enough_for_stats(fake, name, args):
    """與 `jgb2.query.bills` 的 pm 單證路徑不同：這三支的語義是『這位成員看得到的』，缺 user_id 不退回整個 role。"""
    api = fake(resp={"success": True, "data": {"count": 0, "items": [], "total_amount": 0}, "pagination": {}})
    ident = Identity(vendor_id=4, target_user="property_manager", mode="b2b", role_id="20151", user_id=None)
    assert ident.resolved_audience() == "property_manager"
    assert await getattr(S, name)(ident, args) == {"ok": False, "error": "NO_MATCH"}
    assert api.calls == []


FAILURES = [
    {"success": False, "error": {"code": 404, "message": "不存在或無權存取"}},
    {"success": False, "error": {"code": 500, "message": "暫時無法取得資料"}},
    {"success": True, "data": None},                                  # 形狀不對也不能當 0 筆
    {"success": True, "data": {"count": 0}},                          # 缺 items
    {"success": True, "data": {"items": []}},                         # 缺 count
    None,
]


@pytest.mark.parametrize("bad", FAILURES)
@pytest.mark.parametrize("name,args", CALLS)
async def test_upstream_failure_gives_fixed_sentence_not_zero(fake, name, args, bad):
    fake(resp=bad)
    r = await getattr(S, name)(_ident(), args)
    assert r["ok"] is True and r["text_for_model"] == S.ERROR_TEXT
    assert r["provenance"] == [] and r["data"]["upstream_error"] is True
    assert r["data"]["facts"] == S.ERROR_TEXT                         # facts 非空字串：不會被當成『查無資料』
    for leaked in ("共 0 筆", "NT$ 0", "0 元"):
        assert leaked not in r["text_for_model"]


async def test_genuinely_empty_is_a_fact_not_an_error(fake):
    """正對照：success:true 且 count=0 才是『0 筆』的事實，走正常路徑、有可引用的 provenance。"""
    fake(resp=_unpaid_page([], 0, 0))
    r = await S.unpaid_bills(_ident(), {"scope": "overdue"})
    assert "共 0 筆" in r["text_for_model"] and "NT$ 0" in r["text_for_model"]
    assert S.ERROR_TEXT not in r["text_for_model"] and "upstream_error" not in r["data"]
    assert r["provenance"] and r["provenance"][0]["citable"] is True


async def test_error_on_a_requested_page_is_an_error_not_a_partial_answer(fake):
    fake(pages={1: _unpaid_page([_bill(1)], 21, 2100, has_more=True),
                2: {"success": False, "error": {"code": 500, "message": "x"}}})
    r = await S.unpaid_bills(_ident(), {"scope": "overdue", "page": 2})
    assert r["text_for_model"] == S.ERROR_TEXT
    ok1 = await S.unpaid_bills(_ident(), {"scope": "overdue"})           # 正對照：第 1 頁正常
    assert ok1["text_for_model"] != S.ERROR_TEXT


async def test_listed_page_without_rows_is_an_error_not_zero(fake):
    """上游說有 5 筆卻給空明細 ⇒ 不是『沒有資料』（F7）。"""
    fake(resp=_unpaid_page([], 5, 500))
    r = await S.unpaid_bills(_ident(), {"scope": "overdue"})
    assert r["text_for_model"] == S.ERROR_TEXT and r["provenance"] == []


async def test_up_to_20_rows_are_all_listed_in_one_page_and_the_api_gets_page_and_per_page(fake):
    api = fake(resp=_unpaid_page([_bill(i, 100) for i in range(1, 13)], 12, 1200))
    r = await S.unpaid_bills(_ident(), {"scope": "overdue"})
    text = r["text_for_model"]
    assert sorted(_listed_ids(text, "帳單編號")) == list(range(1, 13))
    assert "共 12 筆，總額 NT$ 1,200，以下全部列出。" in text and "下一頁" not in text.split("\n", 1)[1]
    assert [(c[2]["page"], c[2]["per_page"]) for c in api.calls] == [(1, S._PAGE_SIZE)]


async def test_more_than_20_rows_paginate_with_the_next_page_question(fake):
    api = fake(resp=_unpaid_page([_bill(i, 100) for i in range(1, 21)], 45, 4500))
    r = await S.unpaid_bills(_ident(), {"scope": "overdue"})
    text = r["text_for_model"]
    assert len(_listed_ids(text, "帳單編號")) == 20
    assert "共 45 筆，總額 NT$ 4,500；以下是第 1 頁（第 1 到 20 筆），還有 25 筆，要看下一頁嗎？" in text
    assert api.calls[0][2]["page"] == 1
    await S.unpaid_bills(_ident(), {"scope": "overdue", "page": 3})
    assert api.calls[1][2]["page"] == 3                                  # `page` 直接對應上游頁


@pytest.mark.parametrize("name,args", CALLS)
def test_text_for_model_opens_with_the_list_every_row_rule(name, args):
    spec = {s["name"].rsplit(".", 1)[1]: s for s, _ in S.STATS_SPECS}[name]
    assert "逐筆" in spec["description"] and "下一頁" in spec["description"]   # 模型實際看得到的是 description


@pytest.mark.parametrize("name,args", CALLS)
async def test_text_for_model_starts_with_the_rule_and_provenance_is_facts_only(fake, name, args):
    resp = {"success": True, "data": {"count": 1, "total_amount": 100, "as_of": AS_OF, "window_end": AS_OF,
                                      "items": [{"id": 7, "total": 100, "date_expire": 20260901, "status": 2}]},
            "pagination": {"has_more": False}}
    fake(resp=resp)
    r = await getattr(S, name)(_ident(), args)
    assert r["text_for_model"].startswith("回答須列出")
    assert "逐筆" in r["text_for_model"].split("\n", 1)[0]
    assert r["provenance"][0]["text"] == r["data"]["facts"] and "回答須列出" not in r["provenance"][0]["text"]


def _units(r):
    from services.agent.provenance_units import provenance_units
    return provenance_units(r["provenance"][0]["text"])


async def test_provenance_units_are_one_total_sentence_plus_one_unit_per_row(fake):
    """S1 修正③：單位數＝明細筆數＋1（含總額的總計句）；每筆明細單獨成一個單位、自由文字內的句末標點不會多切。"""
    items = [dict(_bill(i, 100), title=f"帳單{i}。很重要！真的？") for i in range(1, 8)]
    fake(resp=_unpaid_page(items, 7, 700))
    r = await S.unpaid_bills(_ident(), {"scope": "overdue"})
    units = _units(r)
    assert len(units) == 7 + 1
    assert "共 7 筆" in units[0] and "總額 NT$ 700" in units[0]
    assert all(u.strip().startswith("帳單編號 ") for u in units[1:])
    assert [int(u.split("、", 1)[0].split()[1]) for u in units[1:]] == list(range(1, 8))


async def test_provenance_units_for_repairs_and_contracts_and_across_pages(real_api):
    r = await S.in_progress_repairs(_ident(user_id=str(OWNER)), {})
    assert len(_units(r)) == 20 + 1 and _units(r)[0].startswith("執行中")
    r4 = await S.in_progress_repairs(_ident(user_id=str(OWNER)), {"page": 4})
    assert len(_units(r4)) == 17 + 1
    c = await S.expiring_contracts(_ident(user_id=str(OWNER)), {"months": 6})
    assert len(_units(c)) == 2 + 1


async def test_invalid_args_are_rejected(fake):
    api = fake(resp=_unpaid_page([], 0, 0))
    assert await S.unpaid_bills(_ident(), {"scope": "weird"}) == {"ok": False, "error": "INVALID_INPUT"}
    assert await S.unpaid_bills(_ident(), {}) == {"ok": False, "error": "INVALID_INPUT"}
    for months in (0, 25, True, "3", 2.5):
        assert await S.expiring_contracts(_ident(), {"months": months}) == {"ok": False, "error": "INVALID_INPUT"}
    assert api.calls == []


# ── 身分鍵：spec 不得含、呼叫端夾帶被剝除 ───────────────────────────────────────────
def _deps():
    return F.FacadeDeps(get_db_pool=lambda: None, get_kb_pool=lambda: None, get_retriever=lambda: None)


def test_stats_specs_have_no_identity_keys_and_register_rejects_one_that_does():
    assert [s["name"] for s, _ in S.STATS_SPECS] == [
        "jgb2.stats.unpaid_bills", "jgb2.stats.in_progress_repairs", "jgb2.stats.expiring_contracts"]
    for spec, _ in S.STATS_SPECS:
        assert not (set(spec["input_schema"].get("properties", {})) & _IDENTITY_KEYS), spec["name"]
        assert spec["scope"] == "read" and spec["stage"] == {"property_manager": "M0"}
    # 反對照：真的塞身分鍵進去，register() 必須擋（否則上面那圈是空跑）
    for key in sorted(_IDENTITY_KEYS):
        bad = dict(S.UNPAID_BILLS_SPEC, name="jgb2.stats.bad",
                   input_schema={"type": "object", "properties": {key: {"type": "string"}}})
        with pytest.raises(ValueError, match="身分鍵"):
            ToolRegistry().register(bad, lambda *_a, **_k: None)


async def test_identity_keys_in_args_are_stripped_and_cannot_change_the_viewer(fake):
    api = fake(resp=_unpaid_page([_bill(1)], 1, 100))
    reg = F.build_registry(_deps())
    ident = Identity(vendor_id=4, target_user="property_manager", mode="b2b",
                     role_id="20151", user_id=str(OWNER), api_key_id=1)
    res = await reg.call(ident, "jgb2.stats.unpaid_bills",
                         {"scope": "overdue", "user_id": str(PART), "role_id": "30999", "viewer_user_id": "1"},
                         5.0, stage="M0")
    assert res.ok is True
    assert api.calls[0][1][:2] == ("20151", str(OWNER))                    # 送給 API 的是 identity 的身分
    notes = {v["note"] for v in reg.last_violations()}
    assert {"IDENTITY_KEY:user_id", "IDENTITY_KEY:role_id", "IDENTITY_KEY:viewer_user_id"} <= notes


def test_tools_are_property_manager_only():
    reg = F.build_registry(_deps())
    names = {s["name"] for s, _ in S.STATS_SPECS}
    for target, mode, expect in (("property_manager", "b2b", True), ("tenant", "b2c", False),
                                 ("prospect", "b2c", False)):
        ident = Identity(vendor_id=4, target_user=target, mode=mode)
        visible = {s["name"] for s in reg.specs_for(ident, "M0", for_model=False)}
        assert (names <= visible) is expect, target
        assert expect or not (names & visible)


# ── DSP-074：既有 jgb2.query.* 的物件、電表、帳號（與修繕）查詢補帶 viewer（user_id）──────────
class _Recorder:
    """每個讀取方法都回 `success:false`（工具回 NO_MATCH），只記下收到的 kwargs。"""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        async def _m(*a, **kw):
            self.calls.append((name, kw))
            return {"success": False, "data": []}
        return _m


async def test_query_tools_forward_viewer_user_id(monkeypatch):
    from services.jgb.accounts import ACCOUNT_FACE_BUILDERS
    from services.jgb.iot import METER_FACE_BUILDERS
    from services.jgb.estates import ESTATE_FACE_BUILDERS
    from services.jgb.repairs import REPAIR_FACE_BUILDERS

    rec = _Recorder()
    monkeypatch.setattr(jgb2, "_api_singleton", rec)
    ident = types.SimpleNamespace(role_id="20151", user_id=str(PART))
    face = lambda reg: sorted(k for k in reg if k not in ("登入排障", "修繕分類"))[0]
    await jgb2.query_meters(ident, {"face": face(METER_FACE_BUILDERS), "keyword": "x"})
    await jgb2.query_estates(ident, {"face": face(ESTATE_FACE_BUILDERS), "keyword": "x"})
    await jgb2.query_accounts(ident, {"face": face(ACCOUNT_FACE_BUILDERS), "keyword": "x"})
    await jgb2.query_accounts(ident, {"face": face(ACCOUNT_FACE_BUILDERS), "ref": "990002"})
    await jgb2.query_repairs(ident, {"face": face(REPAIR_FACE_BUILDERS)})
    sent = {name: kw for name, kw in rec.calls}
    assert set(sent) == {"get_meters", "get_estate_status", "get_team_members",
                         "get_member_permissions", "get_repairs"}           # 正對照：五個查詢都真的發了
    for name, kw in rec.calls:
        assert kw.get("viewer_user_id") == str(PART), name
