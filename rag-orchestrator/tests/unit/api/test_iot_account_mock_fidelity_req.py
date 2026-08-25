"""`/meters` 與 `/roles/{id}/members(+permissions)` 替身對照原始碼（inventory §8 第 6、7 項）。

三個共同病灶：**衍生規則沒模擬**（meter_type／is_poweron 三態）、
**查無分支測不到**（不論 keyword 都回同一列）、**憑空多出 production 沒有的鍵**
（permissions 的 character_name）。
"""
import asyncio

import pytest

pytestmark = pytest.mark.unit

ROLE = "20151"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    from services.jgb_system_api import JGBSystemAPI
    return JGBSystemAPI()


# ── /meters（MeterApiController）────────────────────────────────────────

@pytest.mark.req("face-exit-before-grounding:1")
def test_meter_type_follows_manufacturer_whitelist(api):
    """`meter_type = manufacturer ∈ {Miezo, DAE, SkyWatch} ? cloud : manual`（:157/:162）。"""
    rows = _run(api.get_meters(role_id=ROLE))["data"]
    by_id = {m["id"]: m for m in rows}
    assert by_id[501]["manufacturer"] == "DAE" and by_id[501]["meter_type"] == "cloud"
    assert by_id[503]["manufacturer"] == "SkyWatch" and by_id[503]["meter_type"] == "cloud"
    assert by_id[502]["manufacturer"] == "Panasonic" and by_id[502]["meter_type"] == "manual"


@pytest.mark.req("face-exit-before-grounding:1")
def test_is_poweron_is_tri_state(api):
    """`is_poweron`：-1（從未連線）→ **null**，0/1 → false/true（:167）。

    舊 mock 只有 True，null 這一態在替身上從來測不到——而 builder 對它有專門防護。
    """
    rows = {m["id"]: m for m in _run(api.get_meters(role_id=ROLE))["data"]}
    assert rows[501]["is_poweron"] is True
    assert rows[502]["is_poweron"] is None
    assert rows[503]["is_poweron"] is False


@pytest.mark.req("face-exit-before-grounding:1")
def test_estate_id_filter_uses_the_binding(api):
    """production 以 iot_estate 中間表過濾（:31-39）——未綁定物件的電表查不到。"""
    rows = _run(api.get_meters(role_id=ROLE, estate_id="9002"))["data"]
    assert [m["id"] for m in rows] == [502]
    assert _run(api.get_meters(role_id=ROLE, estate_id="404404"))["data"] == []


@pytest.mark.req("face-exit-before-grounding:1")
def test_meter_projection_matches_format_meter(api):
    row = _run(api.get_meters(role_id=ROLE))["data"][0]
    assert set(row) == {"id", "estate_id", "estate_name", "name", "manufacturer",
                        "meter_type", "is_online", "is_topup", "enable_topup",
                        "balance", "available_meter", "current_reading",
                        "is_poweron", "is_low_battery", "synced_at"}


# ── /roles/{id}/members（TeamMemberApiController@members）────────────────

@pytest.mark.req("face-exit-before-grounding:1")
def test_members_match_email_then_name_case_insensitively(api):
    """email 先判、命中即 match_field='email'，否則才比 name（:161-170），皆不分大小寫。"""
    by_email = _run(api.get_team_members(role_id=ROLE, keyword="VIEWER@Example"))["data"]
    assert [m["member_user_id"] for m in by_email] == [292]
    assert by_email[0]["match_field"] == "email"
    by_name = _run(api.get_team_members(role_id=ROLE, keyword="小美"))["data"]
    assert by_name[0]["match_field"] == "name"


@pytest.mark.req("face-exit-before-grounding:1")
def test_members_no_match_returns_empty(api):
    """舊 mock 不論 keyword 一律回同一列 ⇒「查無此成員」分支測不到。"""
    assert _run(api.get_team_members(role_id=ROLE, keyword="查無此人"))["data"] == []


@pytest.mark.req("face-exit-before-grounding:1")
def test_members_cover_owner_and_null_character(api):
    """擁有者（character_id=0）與 **character_name 為 None** 的成員都要能出現。"""
    owner = _run(api.get_team_members(role_id=ROLE, keyword="owner@"))["data"][0]
    assert owner["is_owner"] is True and owner["character_id"] == 0
    assert owner["character_name"] == "團隊擁有者"
    nochar = _run(api.get_team_members(role_id=ROLE, keyword="nochar@"))["data"][0]
    assert nochar["character_id"] is None and nochar["character_name"] is None


@pytest.mark.req("face-exit-before-grounding:1")
def test_members_never_leak_contact_details(api):
    """`members()` 明示不回 email／phone 明文（:112）。"""
    rows = _run(api.get_team_members(role_id=ROLE, keyword="a"))["data"]
    for row in rows:
        assert set(row) == {"member_user_id", "character_id", "character_name",
                            "is_owner", "match_field"}


# ── /roles/{id}/members/{uid}/permissions ───────────────────────────────

@pytest.mark.req("face-exit-before-grounding:1")
def test_permissions_return_all_32_whitelisted_abilities(api):
    """`ABILITY_WHITELIST`（:17-32）**32 鍵**；舊 mock 只回 6 鍵。"""
    row = _run(api.get_member_permissions(role_id=ROLE, user_id="292"))["data"][0]
    assert len(row["abilities"]) == 32
    assert row["abilities"]["show_owner_bill"] is True
    assert row["abilities"]["show_bill"] is False


@pytest.mark.req("face-exit-before-grounding:1")
def test_permissions_row_shape_matches_production(api):
    """production：`{role_id, user_id, is_member, is_owner, character, abilities}`（:88-96）。

    ⚠️ `character` 是 **{id, name, display} 物件**——production **沒有** `character_name` 鍵，
    舊 mock 憑空給了它，而 accounts.build_team_permission_facts 正是讀那個鍵。
    """
    row = _run(api.get_member_permissions(role_id=ROLE, user_id="292"))["data"][0]
    assert set(row) == {"role_id", "user_id", "is_member", "is_owner",
                        "character", "abilities"}
    assert "character_name" not in row
    assert row["character"] == {"id": 1151, "name": "檢視者", "display": None}


@pytest.mark.req("face-exit-before-grounding:1")
def test_owner_gets_every_ability(api):
    """團隊擁有者全權（:64-69），character 為 {id:0, name:'團隊擁有者'}。"""
    row = _run(api.get_member_permissions(role_id=ROLE, user_id="100"))["data"][0]
    assert row["is_owner"] is True and all(row["abilities"].values())
    assert row["character"]["id"] == 0


@pytest.mark.req("face-exit-before-grounding:1")
def test_unknown_member_degrades(api):
    """production 對非成員回 404（:57-59）——我方折疊為 success:False。"""
    assert _run(api.get_member_permissions(role_id=ROLE, user_id="999999"))["success"] is False


@pytest.mark.req("face-exit-before-grounding:1")
def test_builder_reads_character_object(api):
    """accounts.build_team_permission_facts 改讀 character.name，不再依賴替身的 character_name。"""
    from services.jgb.accounts import build_team_permission_facts
    perm = _run(api.get_member_permissions(role_id=ROLE, user_id="292"))["data"][0]
    facts = build_team_permission_facts({"character_name": None, "permissions": [perm]},
                                        "他看不到帳單")
    assert "檢視者" in facts
