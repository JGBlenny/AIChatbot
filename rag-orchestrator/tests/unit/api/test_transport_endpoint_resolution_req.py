"""TDD：transport 的 template endpoint 解析（spec conversational-routing-execution 任務 4.2，R4.1）。

本組只驗 **endpoint identity**：logical/template endpoint → concrete path 的決定性比對。
**不碰** fixture、不碰 response semantics、不碰 routing。

⚠️ 本組存在的首要理由是**殺掉錯誤的 whitelist 實作**：
detail path 實際為 `/api/external/v1/bills/12345`，
任何 `concrete_path in WHITELIST` 的寫法都會在 `test_detail_path_with_arbitrary_id`
當場失敗——該測試刻意使用**未在任何原始碼中出現過**的 ID。
"""
import pytest

from services.jgb.transport import (
    ROUTES,
    UnresolvedEndpointError,
    match_template,
    resolve_endpoint,
)

pytestmark = pytest.mark.unit

BILLS = "/api/external/v1/bills"
DETAIL_TMPL = "/api/external/v1/bills/{bill_id}"


# ── match_template：逐條驗收 ──────────────────────────────────────────────
def test_static_path_matches_exactly():
    """1. exact static path 可命中（無 placeholder → 抽出空 dict）。"""
    assert match_template(BILLS, BILLS) == {}


def test_template_matches_single_segment_and_extracts_param():
    """2. template path 命中單一 segment，且**抽出參數**（matching 與 extraction 分開）。"""
    assert match_template(DETAIL_TMPL, f"{BILLS}/12345") == {"bill_id": "12345"}


def test_placeholder_does_not_eat_two_segments():
    """3. placeholder 只能吃一個 segment——`{bill_id}` 不得匹配 `123/456`。"""
    assert match_template(DETAIL_TMPL, f"{BILLS}/123/456") is None


def test_extra_segment_does_not_match():
    """4. 段數不同 → 不匹配。"""
    assert match_template(DETAIL_TMPL, f"{BILLS}/12345/items") is None


def test_missing_segment_does_not_match():
    """4（另一側）：少一段同樣不匹配。"""
    assert match_template(DETAIL_TMPL, BILLS) is None


def test_empty_placeholder_value_does_not_match():
    """4（邊界）：`/bills/` 的空 segment 不算有效 placeholder 值。"""
    assert match_template(DETAIL_TMPL, f"{BILLS}/") is None


def test_static_segment_must_be_identical():
    """5. 靜態段必須完全相同——`/bills/{bill_id}` 不得匹配 `/contracts/123`。"""
    assert match_template(DETAIL_TMPL, "/api/external/v1/contracts/12345") is None


# ── resolve_endpoint：identity 解析 ───────────────────────────────────────
def test_resolve_list_endpoint():
    assert resolve_endpoint("GET", BILLS) == "bills"


def test_detail_path_with_arbitrary_id():
    """6. **殺 whitelist 實作**：ID 刻意取未在任何原始碼／範例中出現過的值。

    `concrete_path in WHITELIST` 或任何等價 literal membership 判定，
    在此必然失敗——這正是本測試存在的理由。
    """
    assert resolve_endpoint("GET", f"{BILLS}/987654321") == "bill_detail"


def test_unknown_path_resolves_to_none_without_guessing():
    """7. 無 match → 回 None。**不得** fallback／猜最近的 endpoint。

    ⚠️ 依 design.md §元件 3 的三態決定表，`resolve_endpoint` 對「查無」回 None；
    由 4.3 在 transport 邊界決定處置（fail loudly）。此處只確認**不猜**。
    """
    assert resolve_endpoint("GET", "/api/external/v1/contracts/12345") is None
    assert resolve_endpoint("GET", "/api/external/v1/bills/12345/items") is None


def test_method_is_part_of_identity():
    """method 不同不得命中同一 endpoint。"""
    assert resolve_endpoint("POST", BILLS) is None


def test_ambiguous_templates_fail_loudly(monkeypatch):
    """兩個樣板同時命中 → **不得**取宣告順序第一筆，必須 loud failure。

    否則 correctness 會被綁在 registry 的 incidental ordering 上。
    """
    import services.jgb.transport as t

    monkeypatch.setattr(t, "ROUTES", (
        ("GET", "/api/external/v1/bills/{bill_id}", "bill_detail"),
        ("GET", "/api/external/v1/bills/{anything}", "bill_other"),
    ))
    with pytest.raises(UnresolvedEndpointError) as ei:
        t.resolve_endpoint("GET", f"{BILLS}/12345")
    assert ei.value.reason == "ambiguous"


# ── 契約守衛 ──────────────────────────────────────────────────────────────
def test_routes_registry_has_no_duplicate_keys():
    keys = [k for _, _, k in ROUTES]
    assert len(keys) == len(set(keys))


def test_resolver_does_not_consult_migration_state():
    """4.2 ≠ 4.3：resolver 只回答 identity，**不得**回答「可否在 mock 執行」。

    `MIGRATED_ENDPOINTS` 刻意尚未在本模組定義——若日後被加入，
    本測試確保 `resolve_endpoint` 仍不消費它（避免 resolved == safe-to-mock）。
    """
    import services.jgb.transport as t

    assert not hasattr(t, "MIGRATED_ENDPOINTS"), (
        "MIGRATED_ENDPOINTS 屬 4.3；若已加入，請確認 resolve_endpoint 未消費它"
    )
