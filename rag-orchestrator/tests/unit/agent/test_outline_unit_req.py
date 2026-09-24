"""unit：`OutlineAssembler`＋正本組裝（spec knowledge-outline-and-intent-architecture 3.2）。

⚠️ **檔名帶 `_unit_`，⛔ 不要改回 `test_outline_req.py`**——理由與
`test_kb_tools_unit_req.py` 檔頭完全相同：`tests/` 底下沒有 `__init__.py`，
`tests/unit/agent/test_outline_req.py` 與
`tests/integration/agent/test_outline_req.py` 同名會在全量收集時
`import file mismatch`，整個 unit 層一題都跑不到（單獨跑
`tests/unit/agent` 不會踩到，容易誤判為綠）。

## 2026-09-15（DSP-058／9.6 S3）改寫範圍
正本只有一份（`canon/jgb/`），`build_outline(doc, audience, identity, …)` 改切**受眾視圖**；
`register_canon(doc)`／`get_canon()` 改單槽。本檔的合成正本因此一律 `audience="jgb"`、
細目 id 首段 `jgb/`；視圖隔離的完整正反例在 `test_library_view_req.py`（本檔只覆蓋組裝規則）。

## 2026-09-16（9.8 DSP-059 D′ S2）改寫範圍
`make_outline_resolver()` **不再吃 `cache` 參數**（F8：cache 分支已刪——`app.py`
一律先 `register_canon` 再建 resolver，⛔ 不再有「正本尚未註冊」的窗口）；正本未
註冊 ⇒ `NO_MATCH`（fail-closed），⛔ 不回退成任何 cache 查找。

## 2026-09-07（任務 3.2）改寫範圍
售前大綱的來源從「DB 售前池列＋六模組分類表」改成「git 正本逐細目」：
`SIX_MODULES`／`_classify_row`／`_extract_boundary_sentences`／`DSP009_DELIBERATE_GAPS`／
`_CTA_TEXT` 已退役，對應的測試一併退役（⛔ 不是刪測達成綠——換成
`build_outline`／`canon_visible`／`build_canon_toc`／`resolve_canon_section` 的正反例）。
**`build_toc`（pm／tenant 的 DB 目錄）照舊測；`make_outline_resolver` 的 cache
路徑已隨 9.8 S2（F8）刪除，見下方對應區塊改寫。**
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
    fid="jgb/A/alpha",
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


def _canon(fines, *, version="2026-09-07.1"):
    """合成正本（圖書館形態）：`audience`／`name` 恆為 `jgb`，⛔ 無檔級 target_user 預設。"""
    return CanonDoc(
        audience="jgb",
        version=version,
        reviewers=("owner",),
        language="zh-TW",
        budget_tokens=0,
        target_user=(),
        business_types=(),
        coarses=(CoarseItem(id="A", title="粗目 A", fines=tuple(fines)),),
        canon_sha256="a" * 64,
        phrasing_set_sha256="b" * 64,
        name="jgb",
        library=True,
    )


def _prospect_identity():
    return Identity(vendor_id=0, target_user="prospect", mode="b2b")


def _view(doc, audience="prospect", identity=None):
    """受眾視圖（新簽名的薄包裝——本檔大多數斷言只在乎「組裝規則」那一面）。"""
    return build_outline(
        doc, audience, identity or _prospect_identity(), vendor_business_types=frozenset()
    )


# ---------------------------------------------------------------------------
# §4.1 build_outline：每細目一節
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
def test_build_outline_one_section_per_fine_with_fine_id():
    doc = _canon([_fine("jgb/A/alpha"), _fine("jgb/A/beta", title="第二個")])
    outline = _view(doc)
    assert [s.id for s in outline.sections] == ["jgb/A/alpha", "jgb/A/beta"]
    assert outline.audience == "prospect"
    assert outline.version == doc.version


@pytest.mark.req(_SPEC)
def test_build_outline_title_line_carries_fine_id_marker_once():
    """`_build_doc` 已自動加 `【<id>】`（DSP-020）——⛔ 標題本身不得重複帶 id。"""
    doc = _canon([_fine("jgb/A/alpha", title="系統總覽")])
    outline = _view(doc)
    assert "【jgb/A/alpha】系統總覽" in outline.text
    assert outline.text.count("jgb/A/alpha") == 1
    assert outline.sections[0].title == "系統總覽"


@pytest.mark.req(_SPEC)
def test_build_outline_reviewed_fine_is_citable_with_content():
    doc = _canon([_fine(units=("第一句。", "第二句。"))])
    section = _view(doc).sections[0]
    assert section.citable is True
    assert section.text == "第一句。\n第二句。"


@pytest.mark.req(_SPEC)
def test_build_outline_unreviewed_fine_is_title_only_and_not_citable():
    doc = _canon([_fine(reviewed_by=None, units=("這句不該出現在大綱裡。",))])
    section = _view(doc).sections[0]
    assert section.citable is False
    assert section.text == ""
    assert "這句不該出現在大綱裡" not in _view(doc).text


@pytest.mark.req(_SPEC)
def test_build_outline_is_deterministic():
    doc = _canon([_fine(), _fine("jgb/A/beta")])
    assert _view(doc).sha256 == _view(doc).sha256


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
def test_canon_visible_b2b_empty_target_user_is_invisible():
    """b2b 分支**空 `target_user` ⇒ 不可見**（DSP-052 補救 (c)，業主 2026-09-14 裁）。

    ⚠️ 這條 2026-09-14 之前斷言 True（「空＝不設限」）——⛔ 不得改回：`tenant` 是合法值，
    帶 `mode=b2b` 時 `audience_of` 會把它路由到 pm 正本、b2b 分支又拿 tenant 當鑰匙，
    放行空細目即跨受眾可見。b2c 分支的空放行是另一條分支，⛔ 不受本條影響。
    """
    fine = _fine(target_user=())
    assert canon_visible(_prospect_identity(), fine, vendor_business_types=frozenset()) is False


@pytest.mark.req(_SPEC)
def test_canon_visible_b2b_tenant_key_cannot_open_empty_or_foreign_fines():
    """U3（security-reviewer 2026-09-14 病灶形狀）：合法值 `tenant`＋`mode=b2b`。

    `audience_of` 靠 `or mode == "b2b"` 把這個身分路由到 pm 正本，b2b 分支因此拿到
    `tenant` 當鑰匙。補救 (c) 後：`target_user` 空 ⇒ False、標別人的角色 ⇒ False。
    ⚠️ 正對照在 U4（`test_canon_visible_b2b_matching_role_is_visible`）——那條必須是 True，
    否則這兩條只是因為 b2b 分支整個壞掉而綠。
    """
    identity = Identity(vendor_id=0, target_user="tenant", mode="b2b")
    empty = _fine(target_user=())
    foreign = _fine(target_user=("system_provider",))
    assert canon_visible(identity, empty, vendor_business_types=frozenset()) is False
    assert canon_visible(identity, foreign, vendor_business_types=frozenset()) is False


@pytest.mark.req(_SPEC)
def test_canon_visible_b2b_matching_role_is_visible():
    """U4：作者**明標**的角色仍然可見——⛔ 這不是洞，是 b2b 分支的正常放行。

    b2b 側業者向的鑰匙收斂成 `property_manager`：`property_manager` 本人、以及
    折成 pm 的 `system_admin`（DSP-053a），對 `target_user: [property_manager]` 的細目 ⇒ True。
    ⚠️ 反面正對照在 U3（`tenant` 鑰匙開不了這一格），否則這條只是因為 b2b 分支全放行而綠。
    """
    fine = _fine(target_user=("property_manager",))
    pm = Identity(vendor_id=0, target_user="property_manager", mode="b2b")
    system_admin = Identity(vendor_id=0, target_user="system_admin", mode="b2b")
    assert canon_visible(pm, fine, vendor_business_types=frozenset()) is True
    assert canon_visible(system_admin, fine, vendor_business_types=frozenset()) is True


@pytest.mark.req(_SPEC)
def test_canon_visible_b2b_list_target_user_is_normalized_not_typeerror():
    """U5：`target_user` 被傳成 list ⇒ 走 `_effective_target_user` 取首值，⛔ 不再 TypeError。

    ⚠️ 分支判準改讀正規化後的值才修得掉這個——原本 `list in frozenset` 會
    `TypeError: unhashable type: 'list'`。⚠️ SQL 側 `is_b2b_mode` 用 `in [...]` 清單比對，
    list 輸入會落 b2c 分支；`/mcp` 入口 `parse_identity` 已先正規化成純量，正常路徑到不了。
    """
    identity = Identity(vendor_id=0, target_user=["property_manager"], mode="b2b")
    fine = _fine(target_user=("property_manager",))
    assert canon_visible(identity, fine, vendor_business_types=frozenset()) is True


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
    invisible = _fine(business_types=(), target_user=("property_manager",))
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
def test_build_canon_toc_lists_coarse_row_with_visible_reviewed_count():
    """計畫 9.10 S2：目錄改列**粗目**（`<粗目 id>｜<粗目標題>｜<可見細目數>`），⛔ 不列細目。

    這個粗目底下 1 個可見已審（alpha）＋1 個未審（beta，不計數）＋1 個別角色（不計數）
    ⇒ 可見細目數＝1；且行裡不得出現任何細目 id（負對照）。
    """
    doc = _canon([
        _fine("jgb/A/alpha", title="可見"),
        _fine("jgb/A/beta", title="未審", reviewed_by=None),
        _fine("prospect/A/gamma", title="別的角色", target_user=("tenant",)),
    ])
    toc = build_canon_toc(doc, _prospect_identity(), vendor_business_types=frozenset())
    assert toc.id == TOC_SECTION_ID
    assert toc.citable is False
    assert toc.text == "A｜粗目 A｜1"
    assert "jgb/A/alpha" not in toc.text  # 負對照：目錄不得出現細目 id


@pytest.mark.req(_SPEC)
def test_build_canon_toc_line_format_is_coarse_id_title_count():
    doc = _canon([_fine("jgb/A/alpha", title="系統總覽")])
    toc = build_canon_toc(doc, _prospect_identity(), vendor_business_types=frozenset())
    assert toc.text.splitlines() == ["A｜粗目 A｜1"]
    assert "系統總覽" not in toc.text  # 負對照：細目標題不得出現在目錄（那是粗目標題的層級）


# ---------------------------------------------------------------------------
# §4.4 resolve_canon_section
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
def test_resolve_canon_section_returns_content_for_visible_reviewed_fine():
    doc = _canon([_fine(units=("金箍棒把物件與合約集中管理。",))])
    result = resolve_canon_section(
        doc, _prospect_identity(), "outline:jgb/A/alpha", vendor_business_types=frozenset()
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
        (_fine(reviewed_by=None), "outline:jgb/A/alpha"),          # 未審
        (_fine(target_user=("tenant",)), "outline:jgb/A/alpha"),   # 不可見
        (_fine(), "outline:prospect/A/does-not-exist"),                 # 不存在
        (_fine(), "jgb/A/alpha"),                                  # 裸 id（非 outline: 前綴）
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
        _fine("jgb/A/alpha", units=("可引用的一句。",)),
        _fine("jgb/A/beta", reviewed_by=None, units=("未審的一句。",)),
    ])
    register_canon(doc)
    resolver = make_outline_resolver()
    identity = _prospect_identity()

    hit = resolver(identity, "outline:jgb/A/alpha")
    assert hit.ok is True and hit.provenance[0].citable is True

    for miss_id in ("outline:jgb/A/beta", "outline:prospect/A/nope"):
        miss = resolver(identity, miss_id)
        assert miss.ok is False and miss.error == "NO_MATCH", miss_id

    toc = resolver(identity, TOC_SECTION_ID)
    assert toc.ok is True and toc.provenance[0].citable is False


@pytest.mark.req(_SPEC)
def test_resolver_matches_resolve_canon_section_for_same_inputs():
    """接線證明：經工廠建出的 resolver 與直呼 `resolve_canon_section` 同結果。"""
    doc = _canon([_fine("jgb/A/alpha"), _fine("jgb/A/beta", target_user=("tenant",))])
    register_canon(doc)
    resolver = make_outline_resolver()
    identity = _prospect_identity()
    for section_id in (
        "outline:jgb/A/alpha", "outline:jgb/A/beta", TOC_SECTION_ID, "outline:nope",
    ):
        direct = resolve_canon_section(
            doc, identity, section_id, vendor_business_types=frozenset()
        )
        assert resolver(identity, section_id).model_dump() == direct.model_dump(), section_id


@pytest.mark.req(_SPEC)
def test_resolver_identity_is_per_call_not_bound_to_factory():
    """同一個 resolver、兩種身分 ⇒ 兩種結果（⛔ 身分不得綁在工廠上）。"""
    doc = _canon([_fine("jgb/A/alpha", target_user=("prospect",))])
    register_canon(doc)
    resolver = make_outline_resolver()
    assert resolver(_prospect_identity(), "outline:jgb/A/alpha").ok is True
    other = Identity(vendor_id=1, target_user="system_admin", mode="b2b", audience="prospect")
    assert resolver(other, "outline:jgb/A/alpha").ok is False


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
# make_outline_resolver（9.8 DSP-059 D′ S2）：tenant 一律 NO_MATCH；
# 正本未註冊 ⇒ NO_MATCH（fail-closed——cache 分支已刪，F8）
# ---------------------------------------------------------------------------


def _identity(target_user="prospect"):
    return Identity(vendor_id=1, target_user=target_user, mode="b2c", api_key_id=1)


@pytest.mark.req(_SPEC)
def test_resolver_tenant_is_fail_closed_even_with_canon_registered():
    """DSP-058：tenant 沒有正本視圖 ⇒ **一律 `NO_MATCH`**，即使正本已註冊——
    單一正本形態下，「拿別人的大綱來查」是跨受眾外洩的入口。"""
    doc = _canon([_fine("jgb/A/alpha")])
    register_canon(doc)
    resolver = make_outline_resolver()
    result = resolver(_identity("tenant"), "outline:toc")
    assert isinstance(result, ToolResult)
    assert result.ok is False and result.error == "NO_MATCH"


@pytest.mark.req(_SPEC)
def test_resolver_no_match_when_canon_not_registered():
    """9.8 DSP-059 D′ S2（F8）：正本未註冊 ⇒ 一律 `NO_MATCH`（⛔ 不回退成任何
    cache——那個分支已刪；產線 `app.py` 一律先 `register_canon` 再建 resolver，
    這個窗口在產線不會出現，這裡只驗函式本身的 fail-closed 語義）。"""
    resolver = make_outline_resolver()
    result = resolver(_identity("property_manager"), "outline:toc")
    assert result.ok is False
    assert result.error == "NO_MATCH"


@pytest.mark.req(_SPEC)
def test_resolver_no_match_when_section_missing():
    doc = _canon([_fine("jgb/A/alpha", target_user=("property_manager",))])
    register_canon(doc)
    resolver = make_outline_resolver()
    result = resolver(_identity("property_manager"), "outline:not-exist")
    assert result.ok is False
    assert result.error == "NO_MATCH"
