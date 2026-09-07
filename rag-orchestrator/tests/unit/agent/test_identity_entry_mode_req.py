"""unit：入口 mode 正規化＋`identity_source` 派生＋計數三處
（Plan `inputs/plan-m-d-runtime-wiring-20260907.md` §4.3-1／-8／-9｜
knowledge-outline-and-intent-architecture:4.2）。

主張：
1. `normalize_entry_mode`：prospect × {缺、非法、明送 b2c、明送 b2b} ⇒ 一律 b2b；
   其餘 target_user 維持原值／預設 b2c。
2. 兩個入口都真的呼叫它：MCP `parse_identity`（含 payload 的 **list 形狀**
   `["prospect"]`——先正規化 target_user 才比得到 prospect）、REST
   `build_identity`（用 `VendorChatRequest` 的 **pydantic 預設** `'b2c'`，
   ⛔ 不明送 null；那是 F-1 現況缺陷的形狀）。
3. 正規化實際發生 ⇒ `_STATS.identity_mode_normalized` 與
   `premise_stats()` 同名鍵各 +1；health 的 `premise` 節有該鍵、
   `red_flags` **不含**它（觀測值，⛔ 不致紅）。
4. `derive_identity_source` 逐形狀（契約見 `docs/jgb2-chat-integration.md`
   §3／§4／§8）：`entry` ⇔ `role_id`／`user_id` 任一非 None，⛔ 不看 vendor_id。
"""
from __future__ import annotations

import json

import pytest

from routers import agent_entry as ae
from routers.chat import VendorChatRequest
from services.agent import health as health_mod
from services.agent import mcp_facade as F
from services.agent.identity import (
    DEFAULT_ENTRY_MODE,
    ENTRY_MODES,
    Identity,
    derive_identity_source,
    normalize_entry_mode,
)
from services.agent.tools.registry import ToolRegistry

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:4.2"),
]


def _headers(payload: str) -> dict:
    return {"x-jgb-identity": payload}


def _always_exists(_vendor_id):
    return True


@pytest.fixture(autouse=True)
def _reset_stats():
    F.reset_premise_stats()
    yield
    F.reset_premise_stats()


# ---------------------------------------------------------------------------
# §4.3-1 純函式：形狀對照表
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("mode", [None, "", "nonsense", "B2B", "b2c", "b2b", ["b2b"], 0])
def test_prospect_always_normalizes_to_b2b(mode):
    """prospect × 任何 mode（含**明送 b2c**）⇒ b2b。

    明送 b2c 也改寫是 F-3 的裁決：`audience_of` 對 prospect 不看 mode，
    放著會留下「受眾說 prospect、可見性謂詞說 b2c」的分裂身分。
    """
    assert normalize_entry_mode("prospect", mode) == "b2b"


@pytest.mark.parametrize("target_user", ["tenant", "property_manager", "system_admin", "landlord"])
@pytest.mark.parametrize("mode,expected", [
    (None, "b2c"),
    ("", "b2c"),
    ("nonsense", "b2c"),
    ("B2B", "b2c"),          # 大小寫不算合法值（沿既有 `_VALID_MODES` 語義）
    ("b2c", "b2c"),
    ("b2b", "b2b"),          # 正對照：非 prospect 的合法值原樣保留
])
def test_non_prospect_keeps_mode_or_falls_back_to_default(target_user, mode, expected):
    assert normalize_entry_mode(target_user, mode) == expected


def test_value_domain_constants_are_the_single_source():
    """`mcp_facade` 的兩個名稱是 `identity` 常數的別名（⛔ 不是第二份字面值）。"""
    assert F._VALID_MODES is ENTRY_MODES
    assert F._DEFAULT_MODE is DEFAULT_ENTRY_MODE


# ---------------------------------------------------------------------------
# §4.3-1 MCP 入口
# ---------------------------------------------------------------------------
async def test_mcp_prospect_list_shape_normalizes_and_counts():
    """payload 的合法形狀含 list：`["prospect"]`＋缺 mode ⇒ target_user=prospect、mode=b2b。

    ⚠️ 這一案在「把 raw payload 值餵給 `normalize_entry_mode`」的實作下必紅
    （`["prospect"] == "prospect"` 是 False ⇒ mode 留在 b2c）。
    """
    payload = json.dumps({"vendor_id": 1, "session_id": "s", "target_user": ["prospect"]})
    ident = await F.parse_identity(_headers(payload), key={"id": 7},
                                   vendor_check=_always_exists)
    assert ident.target_user == "prospect"
    assert ident.mode == "b2b"
    assert F._STATS.identity_mode_normalized == 1


async def test_mcp_prospect_explicit_b2c_is_normalized_and_counted():
    payload = json.dumps({"vendor_id": 1, "session_id": "s",
                          "target_user": "prospect", "mode": "b2c"})
    ident = await F.parse_identity(_headers(payload), key={"id": 7},
                                   vendor_check=_always_exists)
    assert (ident.target_user, ident.mode) == ("prospect", "b2b")
    assert F._STATS.identity_mode_normalized == 1


async def test_mcp_prospect_explicit_b2b_is_not_counted():
    """正對照：本來就是 b2b ⇒ 沒有改寫，計數 ⛔ 不加。"""
    payload = json.dumps({"vendor_id": 1, "session_id": "s",
                          "target_user": "prospect", "mode": "b2b"})
    ident = await F.parse_identity(_headers(payload), key={"id": 7},
                                   vendor_check=_always_exists)
    assert ident.mode == "b2b"
    assert F._STATS.identity_mode_normalized == 0


async def test_mcp_unknown_target_user_is_tenant_b2c_and_not_counted():
    """正對照：`"Prospect"` 不是已知值 ⇒ `_normalize_target_user` 落 tenant、mode 留 b2c。"""
    payload = json.dumps({"vendor_id": 1, "session_id": "s", "target_user": "Prospect"})
    ident = await F.parse_identity(_headers(payload), key={"id": 7},
                                   vendor_check=_always_exists)
    assert (ident.target_user, ident.mode) == ("tenant", "b2c")
    assert F._STATS.identity_mode_normalized == 0


# ---------------------------------------------------------------------------
# §4.3-1 REST 入口（pydantic 預設，⛔ 不明送 null）
# ---------------------------------------------------------------------------
def test_rest_prospect_with_pydantic_default_mode_becomes_b2b():
    """F-1：`VendorChatRequest.mode` 的預設是 `'b2c'`——沒帶 mode 的 prospect 現況會落 b2c。"""
    req = VendorChatRequest(message="請問系統支援哪些功能", target_user="prospect", vendor_id=1)
    assert req.mode == "b2c", "前提變了：pydantic 預設不再是 b2c，本案的意義要重寫"
    ident = ae.build_identity(req)
    assert ident.mode == "b2b"
    assert ident.audience == "prospect"


def test_rest_tenant_with_pydantic_default_mode_stays_b2c():
    """正對照：非 prospect 不受影響。"""
    req = VendorChatRequest(message="我要報修", target_user="tenant", vendor_id=1)
    ident = ae.build_identity(req)
    assert ident.mode == "b2c"


def test_rest_entry_has_no_stats_counter():
    """明列取捨：REST 入口沒有 `_STATS` ⇒ 只 log 不計數。"""
    ae.build_identity(VendorChatRequest(message="hi", target_user="prospect", vendor_id=1))
    assert F._STATS.identity_mode_normalized == 0


# ---------------------------------------------------------------------------
# §4.3-9 計數三處
# ---------------------------------------------------------------------------
async def test_premise_stats_exposes_the_same_key():
    payload = json.dumps({"vendor_id": 1, "session_id": "s", "target_user": "prospect"})
    await F.parse_identity(_headers(payload), key={"id": 7}, vendor_check=_always_exists)
    assert F.premise_stats()["identity_mode_normalized"] == 1


async def test_health_premise_has_the_key_and_never_reds_on_it(monkeypatch):
    """health 的 `premise` 節含該鍵；`red_flags` ⛔ 不含它（觀測值，不致紅）。"""
    F._STATS.identity_mode_normalized = 3
    result = await health_mod.compute_agent_health(
        registry=ToolRegistry(), get_kb_pool=None, stage="M1",
    )
    premise = result["checks"]["premise"]
    assert premise["identity_mode_normalized"] == 3
    assert "identity_mode_normalized" not in premise["red_flags"]
    # 正對照：致紅的旗真的進得了 `red_flags`（否則上一條可能只是清單永遠空）
    F._STATS.origin_not_allowed = 1
    result2 = await health_mod.compute_agent_health(
        registry=ToolRegistry(), get_kb_pool=None, stage="M1",
    )
    assert "origin_not_allowed" in result2["checks"]["premise"]["red_flags"]
    assert "identity_mode_normalized" not in result2["checks"]["premise"]["red_flags"]


# ---------------------------------------------------------------------------
# §4.3-8 `derive_identity_source` 逐形狀
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("identity,expected", [
    # pm：帶 role_id（`entry` 分支今天無活流量——`AGENT_TURN_SPEC` stage 只開
    # prospect，故契約以 pm／tenant 身分構造）
    (Identity(vendor_id=1, target_user="property_manager", mode="b2b", role_id="20151"), "entry"),
    # tenant：帶 role_id＋user_id
    (Identity(vendor_id=1, target_user="tenant", mode="b2c", role_id="R1", user_id="U1"), "entry"),
    # tenant：只帶 user_id
    (Identity(vendor_id=1, target_user="tenant", mode="b2c", user_id="U1"), "entry"),
    # prospect：REST 形狀（vendor_id=0、無兩者）
    (Identity(vendor_id=0, target_user="prospect", mode="b2b"), "anonymous"),
    # prospect：MCP 形狀（vendor_id＝key 所屬業者、無兩者）⇒ ⛔ 不因 vendor_id>0 判 entry
    (Identity(vendor_id=9, target_user="prospect", mode="b2b", api_key_id=7), "anonymous"),
    # MCP 未知／缺 target_user（`_normalize_target_user` ⇒ tenant）且無兩者
    (Identity(vendor_id=9, target_user="tenant", mode="b2c"), "anonymous"),
])
def test_derive_identity_source_by_shape(identity, expected):
    assert derive_identity_source(identity) == expected


def test_prospect_forging_role_id_becomes_entry():
    """F-6（ACCEPT）：呼叫端可送任意 `role_id` 把值翻成 `entry`。

    ⚠️ 這**只影響對話控制**（不再重問身分），⛔ 不進任何可見性謂詞、⛔ 不進 DB；
    `role_id` 的信任由上游承擔（DSP-011）。故此處記錄行為，不是漏洞放行。
    """
    forged = Identity(vendor_id=0, target_user="prospect", mode="b2b", role_id="anything")
    assert derive_identity_source(forged) == "entry"


def test_dropping_credentials_flips_entry_to_anonymous():
    """正對照：把函式改成恆回其中一值，本案必紅。"""
    with_creds = Identity(vendor_id=1, target_user="tenant", mode="b2c",
                          role_id="R1", user_id="U1")
    without = Identity(vendor_id=1, target_user="tenant", mode="b2c")
    assert derive_identity_source(with_creds) == "entry"
    assert derive_identity_source(without) == "anonymous"
    assert derive_identity_source(with_creds) != derive_identity_source(without)
