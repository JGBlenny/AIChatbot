"""unit：`OutlineAssembler`＋正本組裝（spec knowledge-outline-and-intent-architecture 3.2）。

⚠️ **檔名帶 `_unit_`，⛔ 不要改回 `test_outline_req.py`**——理由與
`test_kb_tools_unit_req.py` 檔頭完全相同：`tests/` 底下沒有 `__init__.py`，
`tests/unit/agent/test_outline_req.py` 與
`tests/integration/agent/test_outline_req.py` 同名會在全量收集時
`import file mismatch`，整個 unit 層一題都跑不到（單獨跑
`tests/unit/agent` 不會踩到，容易誤判為綠）。

## 2026-09-07（任務 3.2）改寫範圍
售前大綱的來源從「DB 售前池列＋六模組分類表」改成「git 正本逐細目」：
`SIX_MODULES`／`_classify_row`／`_extract_boundary_sentences`／`DSP009_DELIBERATE_GAPS`／
`_CTA_TEXT` 已退役，對應的測試一併退役（⛔ 不是刪測達成綠——換成
`build_outline`／`canon_visible`／`build_canon_toc`／`resolve_canon_section` 的正反例）。
**`build_toc`（pm／tenant 的 DB 目錄）與 `make_outline_resolver` 的 cache 路徑照舊測。**
"""
from datetime import datetime, timezone

import pytest

from services.agent.canon.canon_assembler import (
    TOC_SECTION_ID,
    build_canon_toc,
    build_outline,
    canon_visible,
    register_canon,
    reset_canon_registry,
    resolve_canon_section,
)
from services.agent.canon.canon_parser import CanonDoc, CoarseItem, FineItem
from services.agent.identity import Identity
from services.agent.outline import (
    OutlineBudgetExceeded,
    OutlineDoc,
    OutlineSection,
    build_toc,
    check_budget,
    make_outline_resolver,
)
from services.agent.tools.registry import ToolResult

pytestmark = pytest.mark.unit

_SPEC = "knowledge-outline-and-intent-architecture:3.2"


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_canon_registry()
    yield
    reset_canon_registry()


# ---------------------------------------------------------------------------
# 假 pool（psycopg2 getconn/putconn 介面）——只剩 build_toc 用得到
# ---------------------------------------------------------------------------


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.executed = None

    def execute(self, sql, params):
        self.executed = (sql, params)

    def fetchall(self):
        return self._rows

    def close(self):
        pass


class _FakeConn:
    def __init__(self, rows):
        self.cursor_obj = _FakeCursor(rows)

    def cursor(self):
        return self.cursor_obj


class _FakePool:
    def __init__(self, rows):
        self.conn = _FakeConn(rows)
        self.put_calls = 0

    def getconn(self):
        return self.conn

    def putconn(self, conn):
        self.put_calls += 1
        assert conn is self.conn


def _dt(day: int):
    return datetime(2026, 9, day, tzinfo=timezone.utc)


def _pool(rows):
    return _FakePool(rows)


# ---------------------------------------------------------------------------
# 正本替身（`CanonDoc`／`FineItem` 都是 frozen dataclass，直接建）
# ---------------------------------------------------------------------------


def _fine(
    fid="prospect/A/alpha",
    *,
    title="細目標題",
    units=("這是一句可引用的內容。",),
    reviewed_by="owner",
    target_user=("prospect",),
    business_types=("system_provider",),
):
    return FineItem(
        id=fid,
        coarse_id=fid.split("/")[1],
        title=title,
        phrasings=(),
        content_units=tuple(units),
        content_sha256="0" * 64,
        sources=("kb:1",),
        reviewed_by=reviewed_by,
        reviewed_at="2026-09-07" if reviewed_by else None,
        see_also=(),
        policy="answerable",
        policy_ref=None,
        target_user=tuple(target_user),
        business_types=tuple(business_types),
        categories=(),
        instance_applicability="general",
    )


def _canon(fines, *, audience="prospect", version="2026-09-07.1", budget_tokens=10_000):
    return CanonDoc(
        audience=audience,
        version=version,
        reviewers=("owner",),
        language="zh-TW",
        budget_tokens=budget_tokens,
        target_user=("prospect",),
        business_types=("system_provider",),
        coarses=(CoarseItem(id="A", title="粗目 A", fines=tuple(fines)),),
        canon_sha256="a" * 64,
        phrasing_set_sha256="b" * 64,
    )


def _prospect_identity():
    return Identity(vendor_id=0, target_user="prospect", mode="b2b")


# ---------------------------------------------------------------------------
# §4.1 build_outline：每細目一節
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
def test_build_outline_one_section_per_fine_with_fine_id():
    doc = _canon([_fine("prospect/A/alpha"), _fine("prospect/A/beta", title="第二個")])
    outline = build_outline(doc)
    assert [s.id for s in outline.sections] == ["prospect/A/alpha", "prospect/A/beta"]
    assert outline.audience == "prospect"
    assert outline.version == doc.version


@pytest.mark.req(_SPEC)
def test_build_outline_title_line_carries_fine_id_marker_once():
    """`_build_doc` 已自動加 `【<id>】`（DSP-020）——⛔ 標題本身不得重複帶 id。"""
    doc = _canon([_fine("prospect/A/alpha", title="系統總覽")])
    outline = build_outline(doc)
    assert "【prospect/A/alpha】系統總覽" in outline.text
    assert outline.text.count("prospect/A/alpha") == 1
    assert outline.sections[0].title == "系統總覽"


@pytest.mark.req(_SPEC)
def test_build_outline_reviewed_fine_is_citable_with_content():
    doc = _canon([_fine(units=("第一句。", "第二句。"))])
    section = build_outline(doc).sections[0]
    assert section.citable is True
    assert section.text == "第一句。\n第二句。"


@pytest.mark.req(_SPEC)
def test_build_outline_unreviewed_fine_is_title_only_and_not_citable():
    doc = _canon([_fine(reviewed_by=None, units=("這句不該出現在大綱裡。",))])
    section = build_outline(doc).sections[0]
    assert section.citable is False
    assert section.text == ""
    assert "這句不該出現在大綱裡" not in build_outline(doc).text


@pytest.mark.req(_SPEC)
def test_build_outline_is_deterministic():
    doc = _canon([_fine(), _fine("prospect/A/beta")])
    assert build_outline(doc).sha256 == build_outline(doc).sha256


# ---------------------------------------------------------------------------
# §4.4 canon_visible 正反例（真值表）
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
def test_canon_visible_unreviewed_is_invisible():
    fine = _fine(reviewed_by=None)
    assert canon_visible(_prospect_identity(), fine, vendor_business_types=frozenset()) is False


@pytest.mark.req(_SPEC)
def test_canon_visible_b2b_reviewed_prospect_is_visible():
    fine = _fine()
    assert canon_visible(_prospect_identity(), fine, vendor_business_types=frozenset()) is True


@pytest.mark.req(_SPEC)
def test_canon_visible_b2b_requires_system_provider_business_type():
    fine = _fine(business_types=())
    assert canon_visible(_prospect_identity(), fine, vendor_business_types=frozenset()) is False


@pytest.mark.req(_SPEC)
def test_canon_visible_b2b_target_user_mismatch_is_invisible():
    fine = _fine(target_user=("tenant",))
    assert canon_visible(_prospect_identity(), fine, vendor_business_types=frozenset()) is False


@pytest.mark.req(_SPEC)
def test_canon_visible_b2b_empty_target_user_is_visible():
    fine = _fine(target_user=())
    assert canon_visible(_prospect_identity(), fine, vendor_business_types=frozenset()) is True


@pytest.mark.req(_SPEC)
def test_canon_visible_property_manager_in_b2c_mode_takes_strict_branch():
    """⚠️ 分支判準與 SQL `is_b2b_mode` 同式：`target_user=property_manager` 即使
    `mode=b2c` 也走 b2b 嚴格分支 ⇒ `business_types=[]` 的細目**不可見**。

    ⛔ 只看 `mode` 的實作在這條會回 True（b2c 分支對空業態放行）——那正是
    `build_visibility_predicate` 檔頭「手抄會漏的」那一條。
    """
    fine = _fine(business_types=(), target_user=())
    identity = Identity(vendor_id=1, target_user="property_manager", mode="b2c")
    assert canon_visible(identity, fine, vendor_business_types=frozenset({"rental"})) is False


@pytest.mark.req(_SPEC)
def test_canon_visible_b2c_empty_business_types_is_visible():
    fine = _fine(business_types=(), target_user=("tenant",))
    identity = Identity(vendor_id=1, target_user="tenant", mode="b2c")
    assert canon_visible(identity, fine, vendor_business_types=frozenset({"rental"})) is True


@pytest.mark.req(_SPEC)
def test_canon_visible_b2c_business_types_intersecting_vendor_is_visible():
    fine = _fine(business_types=("rental",), target_user=("tenant",))
    identity = Identity(vendor_id=1, target_user="tenant", mode="b2c")
    assert canon_visible(identity, fine, vendor_business_types=frozenset({"rental"})) is True


@pytest.mark.req(_SPEC)
def test_canon_visible_b2c_business_types_not_intersecting_vendor_is_invisible():
    fine = _fine(business_types=("rental",), target_user=("tenant",))
    identity = Identity(vendor_id=1, target_user="tenant", mode="b2c")
    assert canon_visible(identity, fine, vendor_business_types=frozenset({"parking"})) is False


@pytest.mark.req(_SPEC)
def test_canon_visible_b2c_all_users_token_is_visible():
    fine = _fine(business_types=(), target_user=("all_users",))
    identity = Identity(vendor_id=1, target_user="tenant", mode="b2c")
    assert canon_visible(identity, fine, vendor_business_types=frozenset()) is True


@pytest.mark.req(_SPEC)
def test_canon_visible_none_target_user_normalizes_to_tenant():
    """`target_user=None` 走 `_effective_target_user` ⇒ tenant（fail-safe，與 SQL 同一支）。"""
    identity = Identity(vendor_id=1, target_user=None, mode="b2c")
    visible = _fine(business_types=(), target_user=("tenant",))
    invisible = _fine(business_types=(), target_user=("landlord",))
    assert canon_visible(identity, visible, vendor_business_types=frozenset()) is True
    assert canon_visible(identity, invisible, vendor_business_types=frozenset()) is False


@pytest.mark.req(_SPEC)
def test_canon_visible_all_users_is_not_a_b2b_bypass():
    """b2b 分支⛔不吃 `all_users`——那是 b2c 條件 4 的通用標記（SQL 同款）。"""
    fine = _fine(target_user=("all_users",))
    assert canon_visible(_prospect_identity(), fine, vendor_business_types=frozenset()) is False


# ---------------------------------------------------------------------------
# §4.4 build_canon_toc：只列可見已審
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
def test_build_canon_toc_lists_only_visible_reviewed_fines():
    doc = _canon([
        _fine("prospect/A/alpha", title="可見"),
        _fine("prospect/A/beta", title="未審", reviewed_by=None),
        _fine("prospect/A/gamma", title="別的角色", target_user=("tenant",)),
    ])
    toc = build_canon_toc(doc, _prospect_identity(), vendor_business_types=frozenset())
    assert toc.id == TOC_SECTION_ID
    assert toc.citable is False
    assert toc.text == "prospect/A/alpha｜可見"


@pytest.mark.req(_SPEC)
def test_build_canon_toc_line_format_is_id_then_title():
    doc = _canon([_fine("prospect/A/alpha", title="系統總覽")])
    toc = build_canon_toc(doc, _prospect_identity(), vendor_business_types=frozenset())
    assert toc.text.splitlines() == ["prospect/A/alpha｜系統總覽"]


# ---------------------------------------------------------------------------
# §4.4 resolve_canon_section
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
def test_resolve_canon_section_returns_content_for_visible_reviewed_fine():
    doc = _canon([_fine(units=("金箍棒把物件與合約集中管理。",))])
    result = resolve_canon_section(
        doc, _prospect_identity(), "outline:prospect/A/alpha", vendor_business_types=frozenset()
    )
    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert result.data["answer"] == "金箍棒把物件與合約集中管理。"
    assert result.provenance[0].citable is True
    assert result.text_for_model == "金箍棒把物件與合約集中管理。"


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize(
    "fine,section_id",
    [
        (_fine(reviewed_by=None), "outline:prospect/A/alpha"),          # 未審
        (_fine(target_user=("tenant",)), "outline:prospect/A/alpha"),   # 不可見
        (_fine(), "outline:prospect/A/does-not-exist"),                 # 不存在
        (_fine(), "prospect/A/alpha"),                                  # 裸 id（非 outline: 前綴）
    ],
)
def test_resolve_canon_section_no_match_cases(fine, section_id):
    doc = _canon([fine])
    result = resolve_canon_section(
        doc, _prospect_identity(), section_id, vendor_business_types=frozenset()
    )
    assert result.ok is False
    assert result.error == "NO_MATCH"


@pytest.mark.req(_SPEC)
def test_resolve_canon_section_toc_is_not_citable():
    doc = _canon([_fine()])
    result = resolve_canon_section(
        doc, _prospect_identity(), TOC_SECTION_ID, vendor_business_types=frozenset()
    )
    assert result.ok is True
    assert result.provenance[0].citable is False


# ---------------------------------------------------------------------------
# §4.4 接線證明：make_outline_resolver 建出的 resolver 行為一致
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
def test_resolver_uses_registered_canon_and_applies_visibility():
    doc = _canon([
        _fine("prospect/A/alpha", units=("可引用的一句。",)),
        _fine("prospect/A/beta", reviewed_by=None, units=("未審的一句。",)),
    ])
    register_canon("prospect", doc)
    resolver = make_outline_resolver({})       # ⚠️ cache 空：正本路徑不吃 cache
    identity = _prospect_identity()

    hit = resolver(identity, "outline:prospect/A/alpha")
    assert hit.ok is True and hit.provenance[0].citable is True

    for miss_id in ("outline:prospect/A/beta", "outline:prospect/A/nope"):
        miss = resolver(identity, miss_id)
        assert miss.ok is False and miss.error == "NO_MATCH", miss_id

    toc = resolver(identity, TOC_SECTION_ID)
    assert toc.ok is True and toc.provenance[0].citable is False


@pytest.mark.req(_SPEC)
def test_resolver_matches_resolve_canon_section_for_same_inputs():
    """接線證明：經工廠建出的 resolver 與直呼 `resolve_canon_section` 同結果。"""
    doc = _canon([_fine("prospect/A/alpha"), _fine("prospect/A/beta", target_user=("tenant",))])
    register_canon("prospect", doc)
    resolver = make_outline_resolver({})
    identity = _prospect_identity()
    for section_id in (
        "outline:prospect/A/alpha", "outline:prospect/A/beta", TOC_SECTION_ID, "outline:nope",
    ):
        direct = resolve_canon_section(
            doc, identity, section_id, vendor_business_types=frozenset()
        )
        assert resolver(identity, section_id).model_dump() == direct.model_dump(), section_id


@pytest.mark.req(_SPEC)
def test_resolver_identity_is_per_call_not_bound_to_factory():
    """同一個 resolver、兩種身分 ⇒ 兩種結果（⛔ 身分不得綁在工廠上）。"""
    doc = _canon([_fine("prospect/A/alpha", target_user=("prospect",))])
    register_canon("prospect", doc)
    resolver = make_outline_resolver({})
    assert resolver(_prospect_identity(), "outline:prospect/A/alpha").ok is True
    other = Identity(vendor_id=1, target_user="system_admin", mode="b2b", audience="prospect")
    assert resolver(other, "outline:prospect/A/alpha").ok is False


# ---------------------------------------------------------------------------
# check_budget
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
def test_check_budget_raises_when_exceeded():
    doc = OutlineDoc(
        audience="prospect", version="v1", sha256="x" * 64,
        token_count=10_001, sections=[], text="x",
    )
    with pytest.raises(OutlineBudgetExceeded):
        check_budget(doc, 10_000)


@pytest.mark.req(_SPEC)
def test_check_budget_passes_when_within_limit():
    doc = OutlineDoc(
        audience="prospect", version="v1", sha256="x" * 64,
        token_count=9_999, sections=[], text="x",
    )
    check_budget(doc, 10_000)  # 不 raise


# ---------------------------------------------------------------------------
# build_toc（pm／tenant 現役）：citable=False、vendor／target_user 過濾條件在 SQL 中
# ---------------------------------------------------------------------------


_TOC_ROWS = [
    (9001, "系統整體介紹", "金箍棒是一套物業管理系統。\n\n更多細節。", _dt(1)),
]


@pytest.mark.req(_SPEC)
async def test_build_toc_sections_not_citable():
    doc = await build_toc(_pool(list(_TOC_ROWS)), "property_manager", vendor_id=1)
    assert doc.sections
    for section in doc.sections:
        assert section.citable is False


@pytest.mark.req(_SPEC)
async def test_build_toc_title_and_clipped_body():
    doc = await build_toc(_pool(list(_TOC_ROWS)), "tenant", vendor_id=1)
    section = doc.sections[0]
    assert section.title == "系統整體介紹"
    assert section.text == "金箍棒是一套物業管理系統。"  # 只取第一段
    assert section.source_ids == [9001]


@pytest.mark.req(_SPEC)
async def test_build_toc_sql_has_vendor_and_target_user_filters():
    pool = _pool(list(_TOC_ROWS))
    await build_toc(pool, "property_manager", vendor_id=7)
    sql, params = pool.conn.cursor_obj.executed
    assert "vendor_ids" in sql
    assert "target_user" in sql
    assert params[1] == [7]
    assert params[2] == ["property_manager", "all_users"]


@pytest.mark.req(_SPEC)
async def test_build_toc_rejects_prospect_audience():
    with pytest.raises(ValueError):
        await build_toc(_pool([]), "prospect", vendor_id=1)


# ---------------------------------------------------------------------------
# make_outline_resolver：未註冊正本的受眾（pm／tenant）維持 cache 查找
# ---------------------------------------------------------------------------


def _identity(target_user="prospect"):
    return Identity(vendor_id=1, target_user=target_user, mode="b2c", api_key_id=1)


@pytest.mark.req(_SPEC)
def test_resolver_returns_tool_result_hit_from_cache_when_no_canon():
    section = OutlineSection(
        id="outline:toc:9001", title="系統整體介紹", text="系統簡介。", source_ids=[9001], citable=False,
    )
    doc = OutlineDoc(
        audience="tenant", version="v1", sha256="y" * 64, token_count=5,
        sections=[section], text="系統簡介。",
    )
    resolver = make_outline_resolver({"tenant": doc})
    result = resolver(_identity("tenant"), "outline:toc:9001")
    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert result.data == {
        "id": "outline:toc:9001", "question_summary": "系統整體介紹", "answer": "系統簡介。",
    }
    assert result.provenance[0].source == "outline:toc:9001"
    assert result.provenance[0].citable is False
    assert result.text_for_model == "系統簡介。"


@pytest.mark.req(_SPEC)
def test_resolver_no_match_when_section_missing():
    doc = OutlineDoc(
        audience="tenant", version="v1", sha256="x" * 64, token_count=1, sections=[], text="",
    )
    resolver = make_outline_resolver({"tenant": doc})
    result = resolver(_identity("tenant"), "outline:not-exist")
    assert result.ok is False
    assert result.error == "NO_MATCH"


@pytest.mark.req(_SPEC)
def test_resolver_no_match_when_cache_empty_for_audience():
    resolver = make_outline_resolver({})
    result = resolver(_identity("tenant"), "outline:toc:9001")
    assert result.ok is False
    assert result.error == "NO_MATCH"
