"""unit：`vendor_business_types` 單一來源解析（tasks 6.2 前置 P3-b）。

design 元件 6：呼叫端以 `VendorParameterResolver.get_vendor_info(vendor_id)` 解析
`vendor_business_types` 後傳入，⛔ 不在 `FineIndex`／`canon_visible` 內部查 DB。

四類案例：
(a) prospect／vendor_id 缺 ⇒ 空集合且**不呼叫 resolver**。
(b) pm＋resolver 回 `['system_provider']` ⇒ 該集合傳到
    `build_canon_toc`／`candidate_outline`（`visible_subset`）／`selector.select`
    （用 fake 驗參數）。
(c) resolver raise ⇒ 空集合、不 raise（fail-closed）。
(d) 業態限定細目在 (b) 可見、在 (c) 不可見（用 `canon_visible` 直接驗）。
"""
from __future__ import annotations

import pytest

from services.agent.canon import canon_assembler as canon_assembler_mod
from services.agent.canon.canon_assembler import (
    build_outline,
    canon_visible,
    register_canon,
    reset_canon_registry,
)
from services.agent.canon.canon_parser import CanonDoc, CoarseItem, FineItem
from services.agent.identity import Identity
from services.agent.outline import resolve_vendor_business_types
from services.agent import runtime as runtime_mod

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:6.2"),
]


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_canon_registry()
    yield
    reset_canon_registry()


# ---------------------------------------------------------------------------
# 假 resolver（`VendorParameterResolver.get_vendor_info` 的介面替身）
# ---------------------------------------------------------------------------


class _SpyResolver:
    def __init__(self, *, info=None, raises: Exception | None = None):
        self._info = info
        self._raises = raises
        self.calls: list[int] = []

    def get_vendor_info(self, vendor_id: int):
        self.calls.append(vendor_id)
        if self._raises is not None:
            raise self._raises
        return self._info


class _NeverCallResolver:
    """(a)：resolver 被呼叫即失敗——證明短路路徑真的沒有查 DB。"""

    def get_vendor_info(self, vendor_id: int):
        raise AssertionError(f"resolve_vendor_business_types 不該呼叫 resolver（vendor_id={vendor_id}）")


# ---------------------------------------------------------------------------
# (a) prospect／vendor_id 缺 ⇒ 空集合且不呼叫 resolver
# ---------------------------------------------------------------------------


def test_vendor_id_none_returns_empty_without_calling_resolver():
    identity = Identity(vendor_id=None, target_user="tenant", mode="b2c")
    assert resolve_vendor_business_types(identity, resolver=_NeverCallResolver()) == frozenset()


def test_vendor_id_zero_returns_empty_without_calling_resolver():
    identity = Identity(vendor_id=0, target_user="tenant", mode="b2c")
    assert resolve_vendor_business_types(identity, resolver=_NeverCallResolver()) == frozenset()


def test_prospect_audience_returns_empty_without_calling_resolver_even_with_vendor_id():
    """prospect 走 b2b 分支不看 vendor_business_types——即使帶了真實 vendor_id 也短路。"""
    identity = Identity(vendor_id=42, target_user="prospect", mode="b2b")
    assert resolve_vendor_business_types(identity, resolver=_NeverCallResolver()) == frozenset()


# ---------------------------------------------------------------------------
# (b) pm＋resolver 回 business_types ⇒ 解析成 frozenset[str]
# ---------------------------------------------------------------------------


def test_pm_identity_resolves_business_types_from_resolver():
    identity = Identity(vendor_id=7, target_user="property_manager", mode="b2c")
    resolver = _SpyResolver(info={"id": 7, "business_types": ["system_provider"]})

    result = resolve_vendor_business_types(identity, resolver=resolver)

    assert result == frozenset({"system_provider"})
    assert resolver.calls == [7]


def test_missing_vendor_or_missing_business_types_fails_closed_to_empty():
    identity = Identity(vendor_id=7, target_user="property_manager", mode="b2c")
    assert resolve_vendor_business_types(identity, resolver=_SpyResolver(info=None)) == frozenset()
    assert (
        resolve_vendor_business_types(identity, resolver=_SpyResolver(info={"id": 7}))
        == frozenset()
    )


# ---------------------------------------------------------------------------
# (c) resolver raise ⇒ 空集合、不 raise
# ---------------------------------------------------------------------------


def test_resolver_exception_fails_closed_without_raising():
    identity = Identity(vendor_id=7, target_user="property_manager", mode="b2c")
    resolver = _SpyResolver(raises=RuntimeError("db down"))

    result = resolve_vendor_business_types(identity, resolver=resolver)

    assert result == frozenset()
    assert resolver.calls == [7]


# ---------------------------------------------------------------------------
# (d) 業態限定細目在 (b) 可見、在 (c)（=fail-closed 空集合）不可見
#     ——直接驗 `canon_visible`，不經 runtime。
# ---------------------------------------------------------------------------


def _scoped_fine() -> FineItem:
    return FineItem(
        id="tenant/A/scoped",
        coarse_id="A",
        title="業態限定細目",
        phrasings=(),
        content_units=("內容",),
        content_sha256="0" * 64,
        sources=("kb:1",),
        reviewed_by="owner",
        reviewed_at="2026-09-07",
        see_also=(),
        policy="answerable",
        policy_ref=None,
        target_user=(),  # 空 ⇒ 不受角色限制，只測 business_types
        business_types=("rental",),
        categories=(),
        instance_applicability="general",
    )


def test_scoped_fine_visible_with_matching_vendor_business_types():
    identity = Identity(vendor_id=7, target_user="tenant", mode="b2c")
    fine = _scoped_fine()
    resolver = _SpyResolver(info={"id": 7, "business_types": ["rental"]})

    vendor_business_types = resolve_vendor_business_types(identity, resolver=resolver)

    assert canon_visible(identity, fine, vendor_business_types=vendor_business_types) is True


def test_scoped_fine_invisible_when_resolver_fails_closed():
    identity = Identity(vendor_id=7, target_user="tenant", mode="b2c")
    fine = _scoped_fine()
    resolver = _SpyResolver(raises=RuntimeError("db down"))

    vendor_business_types = resolve_vendor_business_types(identity, resolver=resolver)

    assert vendor_business_types == frozenset()
    assert canon_visible(identity, fine, vendor_business_types=vendor_business_types) is False


# ---------------------------------------------------------------------------
# (b) 續：`AgentRuntime._select_outline` 三個呼叫點都收到同一份解析結果
#     （`build_canon_toc`／`candidate_outline`＝`selector.index.visible_subset`／
#     `selector.select`）——用 fake 驗參數，不驗完整候選邏輯（那是 4.1 的範圍）。
# ---------------------------------------------------------------------------


class _FakeIndex:
    def __init__(self):
        self.visible_subset_calls: list[frozenset] = []

    def visible_subset(self, identity, canon, *, vendor_business_types):
        self.visible_subset_calls.append(vendor_business_types)
        return frozenset()


class _FakeSelector:
    def __init__(self):
        self.index = _FakeIndex()
        self.select_calls: list[frozenset] = []

    async def select(self, canon, identity, query, *, vendor_business_types):
        self.select_calls.append(vendor_business_types)
        # 回 None ⇒ `_select_outline` 落到 `_fallback_visible()`，
        # 連帶行使 `self.index.visible_subset`（三個呼叫點都會被打到）。
        return None


def _pm_canon_and_outline():
    fine = FineItem(
        id="property_manager/A/one",
        coarse_id="A",
        title="標題",
        phrasings=(),
        content_units=("內容",),
        content_sha256="0" * 64,
        sources=("kb:1",),
        reviewed_by="owner",
        reviewed_at="2026-09-07",
        see_also=(),
        policy="answerable",
        policy_ref=None,
        target_user=(),
        business_types=(),
        categories=(),
        instance_applicability="general",
    )
    canon = CanonDoc(
        audience="property_manager",
        version="v1",
        reviewers=("owner",),
        language="zh-TW",
        budget_tokens=10_000,
        target_user=(),
        business_types=(),
        coarses=(CoarseItem(id="A", title="grp", fines=(fine,)),),
        canon_sha256="0" * 64,
        phrasing_set_sha256="0" * 64,
    )
    return canon, build_outline(canon)


async def test_select_outline_forwards_resolved_vendor_business_types_to_all_three_call_sites(
    monkeypatch,
):
    canon, outline = _pm_canon_and_outline()
    register_canon("property_manager", canon)

    sentinel = frozenset({"ZZ_SENTINEL_TYPE"})
    monkeypatch.setattr(runtime_mod, "resolve_vendor_business_types", lambda identity: sentinel)

    toc_calls: list[frozenset] = []
    real_build_canon_toc = canon_assembler_mod.build_canon_toc

    def _spy_build_canon_toc(canon_arg, identity_arg, *, vendor_business_types):
        toc_calls.append(vendor_business_types)
        return real_build_canon_toc(canon_arg, identity_arg, vendor_business_types=vendor_business_types)

    monkeypatch.setattr(runtime_mod, "build_canon_toc", _spy_build_canon_toc)

    selector = _FakeSelector()
    runtime = runtime_mod.AgentRuntime.__new__(runtime_mod.AgentRuntime)
    runtime._candidate_selector = selector
    # ⚠️ 這裡走 `__new__` 繞過 `__init__`，欄位得自己補齊：DSP-037／S1b 起
    # `_select_outline` 經 `_selector_for()` 取 selector，對照表空 ⇒ 沿用單數那一個。
    runtime._candidate_selectors = {}

    identity = Identity(vendor_id=7, target_user="property_manager", mode="b2c")
    violations: list[str] = []

    result_outline, sel_meta = await runtime._select_outline(
        identity, outline, "使用者問題", [], violations
    )

    assert toc_calls == [sentinel]
    assert selector.select_calls == [sentinel]
    assert selector.index.visible_subset_calls == [sentinel]
    assert result_outline is not None
    assert sel_meta["miss_kind"] == "index_unavailable"
    assert "candidate_fallback_full_outline" in violations
