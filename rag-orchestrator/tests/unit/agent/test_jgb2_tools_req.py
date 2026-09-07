"""`jgb2.query.<domain>` 五域單元測試（spec agentic-mcp-orchestration・任務 1.5）。

假 API（`_FakeApi`）——不觸碰真 transport／mock transport，只驗 `services/agent/
tools/jgb2.py` 的分發邏輯：face enum 拒收、雙證閘門、ref/keyword/候選 cap 三態。

正對照組（CANON 否定結論紀律）：每個「缺 user_id ⇒ NO_MATCH」案例旁都有一個
「補上 user_id 就過」的鏡像案例（`test_*_dual_proof_ok`），證明閘門本身有在動作、
不是 fake API 恆回空的假陰性。
"""
import types

import pytest

from services.agent.tools import jgb2
from services.jgb_system_api import JGBSystemAPI

pytestmark = [pytest.mark.unit, pytest.mark.req("agentic-mcp-orchestration:1.5")]


def _identity(role_id=None, user_id=None):
    return types.SimpleNamespace(role_id=role_id, user_id=user_id)


class _FakeApi:
    """可配置回應的假 `JGBSystemAPI`——每個方法回傳建構時指定的固定值。"""

    def __init__(self, **canned):
        self.canned = canned
        self.calls: list[tuple[str, dict]] = []

    def _resp(self, name, **kwargs):
        self.calls.append((name, kwargs))
        return self.canned.get(name, {"success": False, "data": []})

    async def get_bills(self, **kwargs):
        return self._resp("get_bills", **kwargs)

    async def get_contracts(self, **kwargs):
        return self._resp("get_contracts", **kwargs)

    async def get_team_members(self, **kwargs):
        return self._resp("get_team_members", **kwargs)

    async def get_member_permissions(self, **kwargs):
        return self._resp("get_member_permissions", **kwargs)

    async def get_meters(self, **kwargs):
        return self._resp("get_meters", **kwargs)

    async def get_estate_status(self, **kwargs):
        return self._resp("get_estate_status", **kwargs)

    async def get_estate_detail(self, **kwargs):
        return self._resp("get_estate_detail", **kwargs)

    async def get_repairs(self, **kwargs):
        return self._resp("get_repairs", **kwargs)


@pytest.fixture()
def fake_api(monkeypatch):
    """注入假身：`jgb2._get_api()` 讀 `_api_singleton`，測試直接塞值。"""
    api = _FakeApi()
    monkeypatch.setattr(jgb2, "_api_singleton", api)
    return api


def _set_canned(fake_api, name, value):
    fake_api.canned[name] = value


# ══════════════════════════════════════════════════════════════════════
# face enum 拒收（五域共通）
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("fn,identity_kwargs", [
    (jgb2.query_bills, dict(role_id="1", user_id="1")),
    (jgb2.query_contracts, dict(role_id="1", user_id="1")),
    (jgb2.query_accounts, dict(role_id="1", user_id="1")),
    (jgb2.query_meters, dict(role_id="1", user_id="1")),
    (jgb2.query_estates, dict(role_id="1", user_id="1")),
    (jgb2.query_repairs, dict(role_id="1", user_id="1")),
])
async def test_invalid_face_rejected(fn, identity_kwargs, fake_api):
    result = await fn(_identity(**identity_kwargs), {"face": "不存在的面向"})
    assert result == {"ok": False, "error": "INVALID_INPUT"}


async def test_missing_face_rejected(fake_api):
    result = await jgb2.query_bills(_identity(role_id="1", user_id="1"), {})
    assert result == {"ok": False, "error": "INVALID_INPUT"}


# ══════════════════════════════════════════════════════════════════════
# bills
# ══════════════════════════════════════════════════════════════════════

async def test_bills_missing_role_id_no_match(fake_api):
    result = await jgb2.query_bills(
        _identity(role_id=None, user_id="9"), {"face": "帳單異常", "ref": "12"})
    assert result == {"ok": False, "error": "NO_MATCH"}


async def test_bills_ref_single_hit_calls_builder(monkeypatch, fake_api):
    captured = {}

    def fake_builder(row, question):
        captured["row"] = row
        captured["question"] = question
        return f"FACTS:{row['id']}"

    monkeypatch.setitem(jgb2.BILL_FACE_BUILDERS, "__test_face__", fake_builder)
    _set_canned(fake_api, "get_bills",
               {"success": True, "data": [{"id": 501, "status": 2}]})

    result = await jgb2.query_bills(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "ref": "501"})

    assert result["ok"] is True
    assert result["data"]["facts"] == "FACTS:501"
    assert result["data"]["candidates"] is None
    assert result["data"]["skip_refine"] is True
    assert result["provenance"][0]["source"] == "jgb2:bills#501"
    assert result["text_for_model"] == "FACTS:501"
    assert captured["row"]["id"] == 501
    # viewer_user_id 有轉發（本測試不驗真 API 出向 params，那是 integration 的責任；
    # 這裡只驗假 API 有被帶 identity.user_id）。
    name, kwargs = fake_api.calls[-1]
    assert kwargs["viewer_user_id"] == "9"


async def test_bills_keyword_candidates_within_cap(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.BILL_FACE_BUILDERS, "__test_face__", lambda r, q: "x")
    rows = [{"id": i} for i in range(3)]
    _set_canned(fake_api, "get_bills", {"success": True, "data": rows})

    result = await jgb2.query_bills(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "keyword": "某物件"})

    assert result["ok"] is True
    assert result["data"]["candidates"] == rows
    assert result["data"]["skip_refine"] is True
    assert result["data"]["candidate_cap"] == 5


async def test_bills_keyword_candidates_over_cap(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.BILL_FACE_BUILDERS, "__test_face__", lambda r, q: "x")
    rows = [{"id": i} for i in range(7)]
    _set_canned(fake_api, "get_bills", {"success": True, "data": rows})

    result = await jgb2.query_bills(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "keyword": "常見字"})

    assert result["ok"] is True
    assert len(result["data"]["candidates"]) == 5
    assert result["data"]["skip_refine"] is False


async def test_bills_no_ref_no_keyword_recent_listing(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.BILL_FACE_BUILDERS, "__test_face__", lambda r, q: "x")
    rows = [{"id": i} for i in range(3)]
    _set_canned(fake_api, "get_bills", {"success": True, "data": rows})

    result = await jgb2.query_bills(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__"})

    assert result["ok"] is True
    assert result["data"]["candidates"] == rows
    assert result["data"]["skip_refine"] is True


async def test_bills_zero_hit_no_match(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.BILL_FACE_BUILDERS, "__test_face__", lambda r, q: "x")
    _set_canned(fake_api, "get_bills", {"success": True, "data": []})

    result = await jgb2.query_bills(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "ref": "999"})
    assert result == {"ok": False, "error": "NO_MATCH"}


# ══════════════════════════════════════════════════════════════════════
# contracts（同 bills 三態，僅一例代表；避免與 bills 重複整組）
# ══════════════════════════════════════════════════════════════════════

async def test_contracts_ref_uses_contract_ids_param(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.CONTRACT_FACE_BUILDERS, "__test_face__",
                        lambda r, q: f"C:{r['id']}")
    _set_canned(fake_api, "get_contracts",
               {"success": True, "data": [{"id": 678, "title": "測試合約"}]})

    result = await jgb2.query_contracts(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "ref": "678"})

    assert result["ok"] is True
    assert result["data"]["facts"] == "C:678"
    name, kwargs = fake_api.calls[-1]
    assert kwargs["contract_ids"] == "678"
    assert kwargs["viewer_user_id"] == "9"


async def test_contracts_keyword_candidates(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.CONTRACT_FACE_BUILDERS, "__test_face__", lambda r, q: "x")
    rows = [{"id": 1}, {"id": 2}]
    _set_canned(fake_api, "get_contracts", {"success": True, "data": rows})

    result = await jgb2.query_contracts(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "keyword": "重慶北"})

    assert result["data"]["candidates"] == rows
    name, kwargs = fake_api.calls[-1]
    assert kwargs["keyword"] == "重慶北"


async def test_contracts_missing_role_id_no_match(fake_api):
    result = await jgb2.query_contracts(
        _identity(role_id=None, user_id="9"), {"face": "合約異動", "ref": "1"})
    assert result == {"ok": False, "error": "NO_MATCH"}


# ══════════════════════════════════════════════════════════════════════
# accounts（雙證＋成員/權限兩條路徑）
# ══════════════════════════════════════════════════════════════════════

async def test_accounts_missing_user_id_no_match(fake_api):
    result = await jgb2.query_accounts(
        _identity(role_id="1", user_id=None), {"face": "團隊成員權限", "ref": "292"})
    assert result == {"ok": False, "error": "NO_MATCH"}


async def test_accounts_dual_proof_ok_mirrors_missing_case(monkeypatch, fake_api):
    """正對照組：同一請求補上 user_id 就該過（證明上一條真的是 gate 擋、不是假陰性）。"""
    monkeypatch.setitem(jgb2.ACCOUNT_FACE_BUILDERS, "__test_face__",
                        lambda m, q: f"M:{m.get('user_id')}")
    _set_canned(fake_api, "get_member_permissions",
               {"success": True, "data": [{"user_id": 292, "is_owner": False,
                                            "abilities": {}, "character": None}]})
    result = await jgb2.query_accounts(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "ref": "292"})
    assert result["ok"] is True
    assert result["data"]["facts"] == "M:292"
    assert result["data"]["skip_refine"] is True


async def test_accounts_ref_permission_not_found_no_match(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.ACCOUNT_FACE_BUILDERS, "__test_face__", lambda m, q: "x")
    _set_canned(fake_api, "get_member_permissions", {"success": False, "data": []})
    result = await jgb2.query_accounts(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "ref": "999"})
    assert result == {"ok": False, "error": "NO_MATCH"}


async def test_accounts_keyword_candidates_within_cap(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.ACCOUNT_FACE_BUILDERS, "__test_face__", lambda m, q: "x")
    rows = [{"member_user_id": 100}, {"member_user_id": 292}]
    _set_canned(fake_api, "get_team_members", {"success": True, "data": rows})
    result = await jgb2.query_accounts(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "keyword": "陳"})
    assert result["data"]["candidates"] == rows
    assert result["data"]["skip_refine"] is True


async def test_accounts_no_ref_no_keyword_no_match(fake_api):
    result = await jgb2.query_accounts(
        _identity(role_id="1", user_id="9"), {"face": "團隊成員權限"})
    assert result == {"ok": False, "error": "NO_MATCH"}


# ══════════════════════════════════════════════════════════════════════
# meters
# ══════════════════════════════════════════════════════════════════════

async def test_meters_missing_user_id_no_match(fake_api):
    result = await jgb2.query_meters(
        _identity(role_id="1", user_id=None), {"face": "電表排障", "ref": "501"})
    assert result == {"ok": False, "error": "NO_MATCH"}


async def test_meters_dual_proof_ok_mirrors_missing_case(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.METER_FACE_BUILDERS, "__test_face__",
                        lambda m, q: f"MT:{m['id']}")
    _set_canned(fake_api, "get_meters",
               {"success": True, "data": [{"id": 501, "manufacturer": "DAE"}]})
    result = await jgb2.query_meters(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "ref": "501"})
    assert result["ok"] is True
    assert result["data"]["facts"] == "MT:501"


async def test_meters_keyword_candidates_over_cap(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.METER_FACE_BUILDERS, "__test_face__", lambda m, q: "x")
    rows = [{"id": i} for i in range(6)]
    _set_canned(fake_api, "get_meters", {"success": True, "data": rows})
    result = await jgb2.query_meters(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "keyword": "電表"})
    assert len(result["data"]["candidates"]) == 5
    assert result["data"]["skip_refine"] is False


async def test_meters_no_ref_no_keyword_no_match(fake_api):
    result = await jgb2.query_meters(
        _identity(role_id="1", user_id="9"), {"face": "電表排障"})
    assert result == {"ok": False, "error": "NO_MATCH"}


# ══════════════════════════════════════════════════════════════════════
# estates（secondary get_estate_detail、sentinel 單筆化、keyword 候選）
# ══════════════════════════════════════════════════════════════════════

async def test_estates_missing_user_id_no_match(fake_api):
    result = await jgb2.query_estates(
        _identity(role_id="1", user_id=None), {"face": "物件現況診斷", "ref": "9001"})
    assert result == {"ok": False, "error": "NO_MATCH"}


async def test_estates_ref_calls_secondary_detail(monkeypatch, fake_api):
    captured = {}

    def fake_builder(estate, detail, question):
        captured["estate"] = estate
        captured["detail"] = detail
        return f"E:{estate['id']}:{(detail or {}).get('rent')}"

    monkeypatch.setitem(jgb2.ESTATE_FACE_BUILDERS, "__test_face__", fake_builder)
    _set_canned(fake_api, "get_estate_status",
               {"success": True, "data": [{"id": 9001, "status": 2}]})
    _set_canned(fake_api, "get_estate_detail",
               {"success": True, "data": [{"id": 9001, "rent": 15000}]})

    result = await jgb2.query_estates(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "ref": "9001"})

    assert result["ok"] is True
    assert result["data"]["facts"] == "E:9001:15000"
    assert captured["detail"] == {"id": 9001, "rent": 15000}
    # secondary 真的被呼叫（正對照組：detail 有內容，不是 builder 剛好對 None 也印得出東西）
    names = [c[0] for c in fake_api.calls]
    assert names.count("get_estate_detail") == 1


async def test_estates_sentinel_treated_as_single_no_secondary_call(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.ESTATE_FACE_BUILDERS, "__test_face__",
                        lambda e, d, q: f"NOTFOUND:{e.get('keyword')}")
    _set_canned(fake_api, "get_estate_status",
               {"success": True, "data": [{"found": False, "keyword": "亂打的名稱"}]})

    result = await jgb2.query_estates(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "keyword": "亂打的名稱"})

    assert result["ok"] is True
    assert result["data"]["facts"] == "NOTFOUND:亂打的名稱"
    names = [c[0] for c in fake_api.calls]
    assert "get_estate_detail" not in names  # sentinel 不補 secondary


async def test_estates_keyword_multi_candidates(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.ESTATE_FACE_BUILDERS, "__test_face__", lambda e, d, q: "x")
    rows = [{"id": 1}, {"id": 2}, {"id": 3}]
    _set_canned(fake_api, "get_estate_status", {"success": True, "data": rows})

    result = await jgb2.query_estates(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "keyword": "台北"})

    assert result["data"]["candidates"] == rows
    assert result["data"]["skip_refine"] is True
    names = [c[0] for c in fake_api.calls]
    assert "get_estate_detail" not in names  # 候選階段不逐筆補 detail


async def test_estates_no_ref_no_keyword_no_match(fake_api):
    result = await jgb2.query_estates(
        _identity(role_id="1", user_id="9"), {"face": "物件現況診斷"})
    assert result == {"ok": False, "error": "NO_MATCH"}


# ══════════════════════════════════════════════════════════════════════
# repairs（收案修正 5：新讀工具，ref/keyword/預設列表三態，pm 單證身分閘同 bills）
# ══════════════════════════════════════════════════════════════════════

async def test_repairs_missing_role_id_no_match(fake_api):
    result = await jgb2.query_repairs(
        _identity(role_id=None, user_id="9"), {"face": "修繕進度", "ref": "3001"})
    assert result == {"ok": False, "error": "NO_MATCH"}


async def test_repairs_ref_single_hit_calls_builder(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.REPAIR_FACE_BUILDERS, "__test_face__",
                        lambda r, q: f"R:{r['id']}")
    rows = [{"id": 3001, "status": 16}, {"id": 3002, "status": 1}]
    _set_canned(fake_api, "get_repairs", {"success": True, "data": rows})

    result = await jgb2.query_repairs(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "ref": "3001"})

    assert result["ok"] is True
    assert result["data"]["facts"] == "R:3001"
    assert result["data"]["candidates"] is None
    assert result["data"]["skip_refine"] is True
    assert result["provenance"][0]["source"] == "jgb2:repairs#3001"


async def test_repairs_keyword_matches_estate_title_or_reason(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.REPAIR_FACE_BUILDERS, "__test_face__", lambda r, q: "x")
    rows = [
        {"id": 3001, "estate_title": "信義區套房A", "broken_reason": "漏水"},
        {"id": 3002, "estate_title": "中山區雅房B", "broken_reason": "不冷"},
    ]
    _set_canned(fake_api, "get_repairs", {"success": True, "data": rows})

    result = await jgb2.query_repairs(
        _identity(role_id="1", user_id="9"),
        {"face": "__test_face__", "keyword": "信義區套房A"})

    assert result["ok"] is True
    # 收案 2：keyword 命中恰一筆 ⇒ 直接當單筆算 facts（不再落候選清單）。
    assert result["data"]["candidates"] is None
    assert result["data"]["facts"] == "x"


async def test_repairs_no_ref_no_keyword_returns_open_ticket_default_list(
        monkeypatch, fake_api):
    """無 ref/keyword ⇒ 回該 role 的未結單列表（`fetch_default`）——
    status 32（結單）／64（封存）視為已結，過濾掉；其餘算未結。"""
    monkeypatch.setitem(jgb2.REPAIR_FACE_BUILDERS, "__test_face__", lambda r, q: "x")
    rows = [
        {"id": 3001, "status": 16},   # 完成修繕：未結
        {"id": 3002, "status": 1},    # 申請中：未結
        {"id": 3003, "status": 32},   # 結單：已結，應被濾掉
        {"id": 3004, "status": 64},   # 封存：已結，應被濾掉
    ]
    _set_canned(fake_api, "get_repairs", {"success": True, "data": rows})

    result = await jgb2.query_repairs(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__"})

    assert result["ok"] is True
    assert {r["id"] for r in result["data"]["candidates"]} == {3001, 3002}
    assert result["data"]["skip_refine"] is True


async def test_repairs_zero_hit_no_match(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.REPAIR_FACE_BUILDERS, "__test_face__", lambda r, q: "x")
    _set_canned(fake_api, "get_repairs", {"success": True, "data": []})

    result = await jgb2.query_repairs(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "ref": "999"})
    assert result == {"ok": False, "error": "NO_MATCH"}


# ══════════════════════════════════════════════════════════════════════
# CANDIDATE_CAP env 覆寫
# ══════════════════════════════════════════════════════════════════════

async def test_candidate_cap_env_override(monkeypatch, fake_api):
    monkeypatch.setenv("JGB2_CANDIDATE_CAP", "2")
    monkeypatch.setitem(jgb2.BILL_FACE_BUILDERS, "__test_face__", lambda r, q: "x")
    rows = [{"id": i} for i in range(3)]
    _set_canned(fake_api, "get_bills", {"success": True, "data": rows})

    result = await jgb2.query_bills(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "keyword": "kw"})

    assert result["data"]["candidate_cap"] == 2
    assert len(result["data"]["candidates"]) == 2
    assert result["data"]["skip_refine"] is False


# ══════════════════════════════════════════════════════════════════════
# 正對照組（CANON 否定結論紀律）：`_validate_identity` 本身沒壞
# ══════════════════════════════════════════════════════════════════════

def test_validate_identity_sanity_positive_control():
    assert JGBSystemAPI._validate_identity("1", "9") is True
    assert JGBSystemAPI._validate_identity("1", None) is False
    assert JGBSystemAPI._validate_identity(None, "9") is False


# ══════════════════════════════════════════════════════════════════════
# 1.10 P1：bills／contracts 缺 user_id 時洩整個 role
#
# 病灶（1.9 security review）：兩域原本只查 `if not role_id`，而
# `viewer_user_id` 空值不會被轉發 ⇒ jgb2 只認 role_id ⇒ 回整個 role 的資料。
# 修法：受眾非 property_manager ⇒ 一律雙證（`_validate_identity`）。
#
# 這一整區的 identity 用**真的** `Identity`（不是 SimpleNamespace）——閘門讀的是
# `resolved_audience()`，用假物件等於沒驗到與 identity.py 的接線。
# ══════════════════════════════════════════════════════════════════════
from services.agent.identity import Identity  # noqa: E402


def _real_identity(*, target_user="tenant", mode="b2c", role_id=None, user_id=None):
    return Identity(vendor_id=1, target_user=target_user, mode=mode,
                    role_id=role_id, user_id=user_id, session_id="t")


_LEAK_CASES = [
    ("bills-無ref", jgb2.query_bills, "get_bills", {}),
    ("bills-帶ref", jgb2.query_bills, "get_bills", {"ref": "501"}),
    ("bills-帶keyword", jgb2.query_bills, "get_bills", {"keyword": "重慶北"}),
    ("contracts-無ref", jgb2.query_contracts, "get_contracts", {}),
    ("contracts-帶keyword", jgb2.query_contracts, "get_contracts", {"keyword": "重慶北"}),
]


@pytest.mark.req("agentic-mcp-orchestration:1.10")
@pytest.mark.parametrize("label,fn,api_name,args_extra", _LEAK_CASES,
                         ids=[c[0] for c in _LEAK_CASES])
async def test_tenant_missing_user_id_no_match_and_no_outbound_call(
        monkeypatch, fake_api, label, fn, api_name, args_extra):
    """租客缺 user_id ⇒ NO_MATCH，且**一通出向呼叫都不得發生**。

    ⚠️ 只斷言 NO_MATCH 不夠：假 API 預設就回 `success=False` ⇒ 也是 NO_MATCH，
    那是假陰性。這裡把假 API 配成「查得到資料」，若閘門沒擋就會回 ok=True。
    """
    monkeypatch.setitem(jgb2.BILL_FACE_BUILDERS, "__test_face__", lambda r, q: "x")
    monkeypatch.setitem(jgb2.CONTRACT_FACE_BUILDERS, "__test_face__", lambda r, q: "x")
    _set_canned(fake_api, api_name, {"success": True, "data": [{"id": 501}]})

    identity = _real_identity(target_user="tenant", role_id="1", user_id=None)
    result = await fn(identity, {"face": "__test_face__", **args_extra})

    assert identity.resolved_audience() == "tenant"
    assert result == {"ok": False, "error": "NO_MATCH"}, f"{label}：閘門沒擋下"
    assert fake_api.calls == [], f"{label}：擋下了卻仍發出向呼叫 {fake_api.calls}"


@pytest.mark.req("agentic-mcp-orchestration:1.10")
@pytest.mark.parametrize("label,fn,api_name,args_extra", _LEAK_CASES,
                         ids=[c[0] for c in _LEAK_CASES])
async def test_tenant_with_user_id_positive_control(
        monkeypatch, fake_api, label, fn, api_name, args_extra):
    """正對照組：同一組請求補上 user_id ⇒ 走原路（發出向呼叫、帶 viewer_user_id）。

    ⛔ 沒有這一條，上一條的「全 NO_MATCH」可能只是假 API 恆空的假陰性。
    """
    monkeypatch.setitem(jgb2.BILL_FACE_BUILDERS, "__test_face__", lambda r, q: "FACTS")
    monkeypatch.setitem(jgb2.CONTRACT_FACE_BUILDERS, "__test_face__", lambda r, q: "FACTS")
    _set_canned(fake_api, api_name, {"success": True, "data": [{"id": 501}]})

    identity = _real_identity(target_user="tenant", role_id="1", user_id="9")
    result = await fn(identity, {"face": "__test_face__", **args_extra})

    assert result["ok"] is True, f"{label}：補上 user_id 後仍被擋 → 閘門過嚴"
    assert fake_api.calls, f"{label}：沒有任何出向呼叫"
    _name, kwargs = fake_api.calls[-1]
    assert kwargs["viewer_user_id"] == "9", f"{label}：viewer_user_id 沒轉發"


@pytest.mark.req("agentic-mcp-orchestration:1.10")
@pytest.mark.parametrize("target_user,mode", [
    ("property_manager", "b2c"),
    ("system_admin", "b2c"),
    ("tenant", "b2b"),          # mode=b2b 也推導成 property_manager（audience_of）
])
@pytest.mark.parametrize("fn,api_name", [
    (jgb2.query_bills, "get_bills"),
    (jgb2.query_contracts, "get_contracts"),
])
async def test_property_manager_single_proof_still_queries(
        monkeypatch, fake_api, target_user, mode, fn, api_name):
    """正對照組：pm 缺 user_id、只帶 role_id ⇒ 仍可查（1.5 收案的刻意設計）。

    帶了 user_id 反而會讓 jgb2 用 viewer_user_id 圈定，把 pm 自己的查詢過濾成空。
    """
    monkeypatch.setitem(jgb2.BILL_FACE_BUILDERS, "__test_face__", lambda r, q: "FACTS")
    monkeypatch.setitem(jgb2.CONTRACT_FACE_BUILDERS, "__test_face__", lambda r, q: "FACTS")
    _set_canned(fake_api, api_name, {"success": True, "data": [{"id": 501}]})

    identity = _real_identity(target_user=target_user, mode=mode,
                              role_id="1", user_id=None)
    assert identity.resolved_audience() == "property_manager"

    result = await fn(identity, {"face": "__test_face__", "ref": "501"})

    assert result["ok"] is True, "pm 單證被誤擋——1.5 的 pm 查詢會整個壞掉"
    assert fake_api.calls, "pm 單證沒有發出向呼叫"
    _name, kwargs = fake_api.calls[-1]
    assert kwargs["viewer_user_id"] is None, "pm 不該圈定 viewer_user_id"


@pytest.mark.req("agentic-mcp-orchestration:1.10")
@pytest.mark.parametrize("fn", [jgb2.query_bills, jgb2.query_contracts])
async def test_pm_missing_role_id_still_no_match(fake_api, fn):
    """pm 是「單證」不是「免證」：role_id 也缺 ⇒ 仍 NO_MATCH。"""
    identity = _real_identity(target_user="property_manager", role_id=None, user_id="9")
    face = "帳單異常" if fn is jgb2.query_bills else "合約異動"
    result = await fn(identity, {"face": face})
    assert result == {"ok": False, "error": "NO_MATCH"}


@pytest.mark.req("agentic-mcp-orchestration:1.10")
def test_audience_of_is_fail_closed_on_unknown_identity():
    """`_audience_of` 的 fail-closed：算不出受眾一律當 tenant（要雙證）。

    正對照組：真的 pm identity 必須回 property_manager——否則這條只是恆回 tenant
    的假綠。
    """
    class _Boom:
        def resolved_audience(self):
            raise RuntimeError("boom")

    assert jgb2._audience_of(types.SimpleNamespace()) == "tenant"      # 沒有這個方法
    assert jgb2._audience_of(_Boom()) == "tenant"                       # 方法會炸
    assert jgb2._audience_of(types.SimpleNamespace(
        resolved_audience=lambda: "")) == "tenant"                      # 回空字串
    assert jgb2._audience_of(_real_identity(
        target_user="property_manager")) == "property_manager"          # 正對照


# ══════════════════════════════════════════════════════════════════════
# 收案 1：候選結果要有文字（text_for_model／provenance[0].text 決定性列出候選）
# ══════════════════════════════════════════════════════════════════════

async def test_bills_candidates_text_lists_query_and_rows(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.BILL_FACE_BUILDERS, "__test_face__", lambda r, q: "x")
    rows = [
        {"id": 756248, "title": "基隆獨立共生公寓雅房", "status": 2,
         "date_expire": 20260901, "total": 7500},
        {"id": 756242, "title": "基隆獨立共生公寓雅房", "status": 16,
         "date_expire": 20260601, "total": 21500},
    ]
    _set_canned(fake_api, "get_bills", {"success": True, "data": rows})

    result = await jgb2.query_bills(
        _identity(role_id="1", user_id="9"),
        {"face": "__test_face__", "keyword": "基隆獨立共生公寓雅房"})

    text = result["text_for_model"]
    assert "符合 2 筆" in text
    assert "756248" in text and "756242" in text
    assert text == result["provenance"][0]["text"]


async def test_contracts_candidates_text_lists_rows(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.CONTRACT_FACE_BUILDERS, "__test_face__", lambda r, q: "x")
    rows = [{"id": 1, "title": "A約", "date_end": 20270101},
            {"id": 2, "title": "B約", "date_end": 20270201}]
    _set_canned(fake_api, "get_contracts", {"success": True, "data": rows})

    result = await jgb2.query_contracts(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "keyword": "重慶北"})

    text = result["text_for_model"]
    assert "符合 2 筆" in text and "1" in text and "2" in text


async def test_estates_candidates_text_lists_rows(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.ESTATE_FACE_BUILDERS, "__test_face__", lambda e, d, q: "x")
    rows = [{"id": 1, "title": "物件A", "status": 2}, {"id": 2, "title": "物件B", "status": 1}]
    _set_canned(fake_api, "get_estate_status", {"success": True, "data": rows})

    result = await jgb2.query_estates(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "keyword": "台北"})

    text = result["text_for_model"]
    assert "符合 2 筆" in text and "物件A" in text and "物件B" in text


async def test_meters_candidates_text_lists_rows(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.METER_FACE_BUILDERS, "__test_face__", lambda m, q: "x")
    rows = [{"id": i, "name": f"電表{i}", "estate_name": "測試物件"} for i in range(6)]
    _set_canned(fake_api, "get_meters", {"success": True, "data": rows})

    result = await jgb2.query_meters(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__", "keyword": "電表"})

    text = result["text_for_model"]
    assert "符合 5 筆" in text  # over cap → 只列前 5 筆
    assert "電表0" in text


async def test_repairs_candidates_text_lists_rows(monkeypatch, fake_api):
    monkeypatch.setitem(jgb2.REPAIR_FACE_BUILDERS, "__test_face__", lambda r, q: "x")
    rows = [
        {"id": 3001, "estate_title": "信義區套房A", "category_name": "電路", "status": 1},
        {"id": 3002, "estate_title": "中山區雅房B", "category_name": "水路衛浴", "status": 2},
    ]
    _set_canned(fake_api, "get_repairs", {"success": True, "data": rows})

    result = await jgb2.query_repairs(
        _identity(role_id="1", user_id="9"), {"face": "__test_face__"})

    text = result["text_for_model"]
    assert "符合 2 筆" in text and "3001" in text and "3002" in text
    assert "查詢條件：無" in text
