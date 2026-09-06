"""unit：`OutlineAssembler`（spec agentic-mcp-orchestration 任務 3.2）。

假 pool（psycopg2 `getconn`／`putconn` 介面，見 `tools/kb.py` 與
`test_kb_tools_unit_req.py` 同款替身），離線、不接觸真 DB。

⚠️ **檔名帶 `_unit_`，⛔ 不要改回 `test_outline_req.py`**——理由與
`test_kb_tools_unit_req.py` 檔頭完全相同：`tests/` 底下沒有 `__init__.py`，
`tests/unit/agent/test_outline_req.py` 與
`tests/integration/agent/test_outline_req.py` 同名會在全量收集時
`import file mismatch`，整個 unit 層一題都跑不到（單獨跑
`tests/unit/agent` 不會踩到，容易誤判為綠）。
"""
from datetime import datetime, timezone

import pytest

from services.agent.canon.review_state import content_reviewed_predicate
from services.agent.identity import Identity
from services.agent.outline import (
    DSP009_DELIBERATE_GAPS,
    OutlineBudgetExceeded,
    OutlineDoc,
    OutlineSection,
    _classify_module_row,
    _classify_row,
    _extract_boundary_sentences,
    build_prospect_outline,
    build_toc,
    check_budget,
    make_outline_resolver,
)
from services.agent.tools.registry import ToolResult

pytestmark = pytest.mark.unit

_SPEC = "agentic-mcp-orchestration:3.2"


# ---------------------------------------------------------------------------
# 假 pool（psycopg2 getconn/putconn 介面）
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


#: (id, question_summary, answer, categories, updated_at)
_PROSPECT_ROWS = [
    (3599, "房源管理 物件集中 社區歸戶", "可批次上傳物件、社區歸戶管理。", ["售前模組"], _dt(1)),
    (3600, "建立合約 線上電子簽約", "支援電子簽章；委託合約目前不支援線上簽署。", ["售前模組"], _dt(2)),
    (3602, "團隊管理 多人協作", "可設定角色權限、大房東報表。", ["售前模組"], _dt(3)),
    (3610, "金箍棒怎麼收費", "請參考官網方案頁，恕不提供客製報價。", ["售前價格"], _dt(4)),
    (3606, "管理困擾 痛點", "可解決收租、合約、報修、團隊協作等痛點。", ["售前顧問"], _dt(5)),
]


def _pool(rows):
    return _FakePool(rows)


# ---------------------------------------------------------------------------
# 組裝決定性
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
async def test_build_prospect_outline_deterministic_same_sha():
    doc1 = await build_prospect_outline(_pool(list(_PROSPECT_ROWS)))
    doc2 = await build_prospect_outline(_pool(list(_PROSPECT_ROWS)))
    assert doc1.sha256 == doc2.sha256
    assert doc1.text == doc2.text
    assert doc1.version == doc2.version


@pytest.mark.req(_SPEC)
async def test_build_prospect_outline_sql_filters_unreviewed():
    """SQL 本身即帶內容已審謂詞——未審列在 DB 層就出不來，⛔ 不是本檔事後篩掉。

    ⚠️ 2026-09-07（spec knowledge-outline-and-intent-architecture 任務 3.1）起
    條件**不再是 `IS NOT NULL`**：`IS NOT NULL` 會把值域外的舊標記
    （現況 29 列 `owner-20260905`）當成已審。謂詞的唯一來源是
    `services/agent/canon/review_state.py:content_reviewed_predicate`。
    """
    pool = _pool(list(_PROSPECT_ROWS))
    await build_prospect_outline(pool)
    sql, params = pool.conn.cursor_obj.executed
    predicate_sql, predicate_params = content_reviewed_predicate()
    assert predicate_sql in sql, f"SQL 沒拼上內容已審謂詞：{sql!r}"
    assert "IS NOT NULL" not in sql.upper(), (
        "SQL 仍帶 `IS NOT NULL`——那會把值域外的舊標記當成已審"
    )
    assert predicate_params[0] in params, "謂詞參數沒同序帶進 execute"


@pytest.mark.req(_SPEC)
async def test_updated_at_change_changes_version_and_sha():
    rows_a = list(_PROSPECT_ROWS)
    rows_b = [
        (rid, qs, ans, cats, (_dt(30) if rid == 3599 else upd))
        for rid, qs, ans, cats, upd in _PROSPECT_ROWS
    ]
    doc_a = await build_prospect_outline(_pool(rows_a))
    doc_b = await build_prospect_outline(_pool(rows_b))
    assert doc_a.version != doc_b.version
    # text（可見內容）不變，但 sha 涵蓋 version ⇒ 也跟著變——
    # 快取失效判準是「sha 變」，不能漏掉「只有 updated_at 被 touch」這種變化。
    assert doc_a.text == doc_b.text
    assert doc_a.sha256 != doc_b.sha256


@pytest.mark.req(_SPEC)
async def test_content_change_changes_sha():
    rows_changed = [
        (rid, qs, (ans + "（新增一句）") if rid == 3600 else ans, cats, upd)
        for rid, qs, ans, cats, upd in _PROSPECT_ROWS
    ]
    doc_a = await build_prospect_outline(_pool(list(_PROSPECT_ROWS)))
    doc_b = await build_prospect_outline(_pool(rows_changed))
    assert doc_a.sha256 != doc_b.sha256


# ---------------------------------------------------------------------------
# 六模組歸屬規則（正反例）
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize(
    "question_summary,expected_slug",
    [
        ("房源管理 物件集中 社區歸戶 批次上傳", "listing"),
        ("建立合約 線上電子簽約 合約範本", "lease"),
        ("團隊管理 多人協作 角色權限 大房東報表", "team"),
        ("大房東報表 代收代付 月結", "team"),  # 團隊關鍵字排在帳務之前，優先命中
        ("帳務管理 收租對帳 自動帳單", "billing"),
        ("租客不繳租金怎麼辦 逾期 催繳", "billing"),
        ("智慧電錶 智慧門鎖 抄表 換鎖", "iot"),
        ("修繕系統 線上報修 進度追蹤", "repair"),
        ("舊系統資料可以匯進來嗎 批次匯入 搬資料", "listing"),  # 房源關鍵字優先於帳務/租約
    ],
)
def test_classify_module_row_positive(question_summary, expected_slug):
    slug, _title = _classify_module_row(question_summary, ["售前模組"])
    assert slug == expected_slug


@pytest.mark.req(_SPEC)
def test_classify_module_row_fallback_when_no_keyword_hits():
    slug, title = _classify_module_row("完全沒有關鍵字的一列", ["售前模組"])
    assert slug == "module-misc"
    assert title


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize(
    "categories,expected_slug",
    [
        (["售前顧問"], "positioning"),
        (["售前方案"], "plans"),
        (["售前價格"], "pricing"),
        (["售前競品"], "competitors"),
        (None, "module-misc"),  # categories 缺值 ⇒ 兜底桶，⛔ 不丟資料
        ([], "module-misc"),
        (["未知分類"], "module-misc"),
    ],
)
def test_classify_row_non_module_categories(categories, expected_slug):
    slug, _title = _classify_row(categories, "任意問句")
    assert slug == expected_slug


@pytest.mark.req(_SPEC)
async def test_source_ids_grouped_by_module_section():
    doc = await build_prospect_outline(_pool(list(_PROSPECT_ROWS)))
    by_id = {s.id: s for s in doc.sections}
    assert by_id["outline:listing"].source_ids == [3599]
    assert by_id["outline:lease"].source_ids == [3600]
    assert by_id["outline:team"].source_ids == [3602]
    assert by_id["outline:pricing"].source_ids == [3610]
    assert by_id["outline:positioning"].source_ids == [3606]
    for section in doc.sections:
        assert section.citable is True


# ---------------------------------------------------------------------------
# 邊界句抽取
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
@pytest.mark.parametrize(
    "answer,expected",
    [
        ("支援電子簽章；委託合約目前不支援線上簽署。", ["委託合約目前不支援線上簽署"]),
        ("恕不提供客製報價。", ["恕不提供客製報價"]),
        ("這功能我們暫時無法處理。\n但有替代方案。", ["這功能我們暫時無法處理"]),
        ("完全沒有邊界詞的一句話。", []),
    ],
)
def test_extract_boundary_sentences(answer, expected):
    assert _extract_boundary_sentences(answer) == expected


@pytest.mark.req(_SPEC)
async def test_boundary_section_collects_rows_across_modules():
    doc = await build_prospect_outline(_pool(list(_PROSPECT_ROWS)))
    by_id = {s.id: s for s in doc.sections}
    boundary = by_id["outline:boundary"]
    # 3600（lease）與 3610（pricing）的 answer 都含邊界詞。
    assert set(boundary.source_ids) == {3600, 3610}
    assert "委託合約目前不支援線上簽署" in boundary.text
    # 該列仍留在自己的模組小節，⛔ 邊界句抽取不是整列搬移。
    assert 3600 in by_id["outline:lease"].source_ids


# ---------------------------------------------------------------------------
# DSP-009 刻意不補
# ---------------------------------------------------------------------------


@pytest.mark.req(_SPEC)
async def test_dsp009_section_contains_all_five_fixed_items():
    doc = await build_prospect_outline(_pool(list(_PROSPECT_ROWS)))
    by_id = {s.id: s for s in doc.sections}
    gaps_text = by_id["outline:deliberate-gaps"].text
    assert len(DSP009_DELIBERATE_GAPS) == 5
    for item in DSP009_DELIBERATE_GAPS:
        assert item in gaps_text
    assert by_id["outline:deliberate-gaps"].source_ids == []


@pytest.mark.req(_SPEC)
async def test_cta_section_present():
    doc = await build_prospect_outline(_pool(list(_PROSPECT_ROWS)))
    ids = {s.id for s in doc.sections}
    assert "outline:cta" in ids


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
# build_toc：citable=False、vendor／target_user 過濾條件在 SQL 中
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
# make_outline_resolver
# ---------------------------------------------------------------------------


def _identity(target_user="prospect"):
    return Identity(vendor_id=1, target_user=target_user, mode="b2c", api_key_id=1)


@pytest.mark.req(_SPEC)
async def test_resolver_returns_tool_result_hit():
    section = OutlineSection(
        id="outline:listing", title="房源", text="房源功能說明。", source_ids=[3599], citable=True,
    )
    doc = OutlineDoc(
        audience="prospect", version="v1", sha256="x" * 64,
        token_count=10, sections=[section], text="房源功能說明。",
    )
    resolver = make_outline_resolver({"prospect": doc})
    result = resolver(_identity("prospect"), "outline:listing")
    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert result.data == {"id": "outline:listing", "question_summary": "房源", "answer": "房源功能說明。"}
    assert result.provenance[0].source == "outline:listing"
    assert result.provenance[0].citable is True
    assert result.text_for_model == "房源功能說明。"


@pytest.mark.req(_SPEC)
async def test_resolver_no_match_when_section_missing():
    doc = OutlineDoc(
        audience="prospect", version="v1", sha256="x" * 64, token_count=1, sections=[], text="",
    )
    resolver = make_outline_resolver({"prospect": doc})
    result = resolver(_identity("prospect"), "outline:not-exist")
    assert result.ok is False
    assert result.error == "NO_MATCH"


@pytest.mark.req(_SPEC)
async def test_resolver_no_match_when_cache_empty_for_audience():
    resolver = make_outline_resolver({})
    result = resolver(_identity("tenant"), "outline:toc:9001")
    assert result.ok is False
    assert result.error == "NO_MATCH"


@pytest.mark.req(_SPEC)
async def test_resolver_toc_section_not_citable():
    section = OutlineSection(
        id="outline:toc:9001", title="系統整體介紹", text="系統簡介。", source_ids=[9001], citable=False,
    )
    doc = OutlineDoc(
        audience="tenant", version="v1", sha256="y" * 64, token_count=5,
        sections=[section], text="系統簡介。",
    )
    resolver = make_outline_resolver({"tenant": doc})
    result = resolver(_identity("tenant"), "outline:toc:9001")
    assert result.ok is True
    assert result.provenance[0].citable is False
