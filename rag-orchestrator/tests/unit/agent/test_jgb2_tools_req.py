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
