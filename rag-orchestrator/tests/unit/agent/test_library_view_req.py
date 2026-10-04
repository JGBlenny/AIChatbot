"""unit：**受眾視圖**（DSP-058／計畫 9.6 S3）——一份正本切兩份視圖，零外洩、不符即 fail-closed。

Plan `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-9.6-library-canon-20260915.md` §2／§3 S3。
brief `inputs/brief-9.6-S3-20260915.md` 驗收 ①～⑥⑨。

材料＝合成 fixture `tests/fixtures/canon_jgb/shelves/`（pm-only／prospect-only／共用／未審各 ≥1）：

| 細目 | target_user | reviewed |
|---|---|---|
| `jgb/A/account-registration` | prospect, property_manager（**共用**） | 是 |
| `jgb/A/password-reset` | property_manager（**pm-only**） | 否 |
| `jgb/B/team-invite` | property_manager（**pm-only**） | 是 |
| `jgb/B/landlord-record` | property_manager（**pm-only**） | 否 |
| `jgb/C/estate-import` | prospect（**prospect-only**） | 是 |
| `jgb/C/community-setup` | prospect（**prospect-only**） | 否 |

⚠️ 每條斷言都配正對照組：只驗「看不到」而沒有「看得到」的那一半，量尺壞掉時會全綠。
"""
from __future__ import annotations

import math
import os
import re
import shutil

import pytest

from services.agent.canon.candidate_selector import CandidateSelector
from services.agent.canon.canon_assembler import (
    CANON_DIR_ENV,
    DB_ENV_KEY,
    TOC_SECTION_ID,
    build_canon_toc,
    build_outline,
    load_canon_or_die,
    register_canon,
    reset_canon_registry,
    resolve_canon_dir,
    resolve_canon_section,
)
from services.agent.canon.canon_parser import (
    CANON_NAME, export_catalog, export_json, parse_canon_dir,
)
from services.agent.canon.fine_index import FineIndex, reset_index_registry
from services.agent.identity import Identity
from services.agent.outline import (
    OUTLINE_K_TOKEN_LIMIT,
    OUTLINE_TOC_TOKEN_LIMIT,
    OutlineBudgetExceeded,
    build_audience_outline,
    check_turn_budget,
    default_k_token_limit,
    default_toc_token_limit,
    make_outline_resolver,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:9.6-S3"),
]

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
_FIXTURE_SHELVES = os.path.join(_RAG, "tests", "fixtures", "canon_jgb", "shelves")

SHARED_ID = "jgb/A/account-registration"
SHARED_TITLE = "怎麼註冊帳號"
PM_ONLY_REVIEWED_ID = "jgb/B/team-invite"
PM_ONLY_REVIEWED_TITLE = "怎麼邀請團隊成員"
PM_ONLY_UNREVIEWED_ID = "jgb/A/password-reset"
PM_ONLY_UNREVIEWED_TITLE = "忘記密碼怎麼辦"
PROSPECT_ONLY_ID = "jgb/C/estate-import"
PROSPECT_ONLY_TITLE = "物件批次匯入"
PROSPECT_ONLY_UNREVIEWED_ID = "jgb/C/community-setup"

PM = Identity(vendor_id=0, target_user="property_manager", mode="b2b", session_id="s-pm")
PROSPECT = Identity(vendor_id=0, target_user="prospect", mode="b2b", session_id="s-pr")
#: ⚠️ `mode="b2b"`＋`target_user="tenant"`：`audience_of` 會把它路由到 pm 受眾，
#: 而 b2b 分支拿 `tenant` 當鑰匙 ⇒ 正本沒有任何 tenant 細目 ⇒ 可見集合必須是空的
#: （DSP-052 補救 (c) 那條不對稱就是為了這個身分）。
TENANT_B2B = Identity(vendor_id=0, target_user="tenant", mode="b2b", session_id="s-tn")


@pytest.fixture(autouse=True)
def _clean_registries():
    reset_canon_registry()
    reset_index_registry()
    yield
    reset_canon_registry()
    reset_index_registry()


@pytest.fixture
def canon():
    return parse_canon_dir(_FIXTURE_SHELVES)


def _view(canon, audience, identity):
    return build_outline(canon, audience, identity, vendor_business_types=frozenset())


# ═══════════════════════════════════════════════════════════════════
# ① 視圖零外洩（id 與標題都不得現身；三個正對照）
# ═══════════════════════════════════════════════════════════════════


def test_pm_only_fine_id_and_title_never_reach_prospect_view(canon):
    prospect_view = _view(canon, "prospect", PROSPECT)
    pm_view = _view(canon, "property_manager", PM)

    assert len(prospect_view.sections) > 0 and len(pm_view.sections) > 0

    for fid, title in (
        (PM_ONLY_REVIEWED_ID, PM_ONLY_REVIEWED_TITLE),
        (PM_ONLY_UNREVIEWED_ID, PM_ONLY_UNREVIEWED_TITLE),
    ):
        assert fid not in {s.id for s in prospect_view.sections}
        assert fid not in prospect_view.text
        assert title not in prospect_view.text

    # 正對照 ①：共用細目兩邊都在
    assert SHARED_ID in {s.id for s in prospect_view.sections}
    assert SHARED_ID in {s.id for s in pm_view.sections}
    assert SHARED_TITLE in prospect_view.text and SHARED_TITLE in pm_view.text
    # 正對照 ②：prospect-only 在 prospect 視圖、⛔ 不在 pm 視圖
    assert PROSPECT_ONLY_ID in {s.id for s in prospect_view.sections}
    assert PROSPECT_ONLY_TITLE in prospect_view.text
    assert PROSPECT_ONLY_ID not in pm_view.text and PROSPECT_ONLY_TITLE not in pm_view.text
    # 正對照 ③：pm-only 在 pm 視圖（證明「看不到」不是因為它根本沒被組進任何視圖）
    assert PM_ONLY_REVIEWED_TITLE in pm_view.text


def test_unreviewed_fine_is_title_only_in_its_own_view(canon):
    """未審細目：在**自己受眾**的視圖裡只出標題（⛔ 不可引用）；在另一受眾連標題都沒有。"""
    pm_view = _view(canon, "property_manager", PM)
    by_id = {s.id: s for s in pm_view.sections}
    assert by_id[PM_ONLY_UNREVIEWED_ID].text == ""
    assert by_id[PM_ONLY_UNREVIEWED_ID].citable is False
    # 正對照：同一視圖裡已審的那條有內容且可引用
    assert by_id[PM_ONLY_REVIEWED_ID].text and by_id[PM_ONLY_REVIEWED_ID].citable is True

    prospect_view = _view(canon, "prospect", PROSPECT)
    assert PM_ONLY_UNREVIEWED_ID not in {s.id for s in prospect_view.sections}
    # 正對照：prospect 自己的未審細目在自己的視圖裡（只出標題）
    assert prospect_view  # noqa: B015 — 下一行才是斷言本體
    p_by_id = {s.id: s for s in prospect_view.sections}
    assert p_by_id[PROSPECT_ONLY_UNREVIEWED_ID].text == ""
    assert p_by_id[PROSPECT_ONLY_UNREVIEWED_ID].citable is False


def test_toc_only_lists_coarses_with_this_audiences_visible_reviewed_fines(canon):
    """計畫 9.10 S2：目錄改列粗目——粗目 A／C 各有 ≥1 條 prospect 可見已審細目 ⇒ 出現；
    粗目 B 全部細目都是 pm-only（無 prospect 可見已審細目）⇒ 整個粗目行都不出現
    （⛔ 不是只驗細目 id／標題不外洩，粗目本身也不該現身——量尺自證見下面的 pm 視圖正對照）。
    """
    toc = build_canon_toc(canon, PROSPECT, vendor_business_types=frozenset())
    lines = toc.text.splitlines()
    # 計畫 9.10 S1／S5：粗目 id 恆為 `<架字母>-<slug>`（⛔ 不再是裸字母），fixture 見
    # tests/fixtures/canon_jgb/shelves/*.md（A-account／B-team／C-community）。
    assert any(line.startswith("A-account｜") for line in lines)   # 正對照：粗目 A 有 1 條 prospect 可見已審
    assert any(line.startswith("C-community｜") for line in lines)   # 正對照：粗目 C 同上
    assert not any(line.startswith("B-team｜") for line in lines)  # 負對照：粗目 B 對 prospect 零可見已審
    assert PM_ONLY_REVIEWED_ID not in toc.text
    assert PM_ONLY_REVIEWED_TITLE not in toc.text
    assert PROSPECT_ONLY_UNREVIEWED_ID not in toc.text                  # 未審不列目錄
    assert toc.citable is False

    # 正對照：pm 視圖看得到粗目 B（證明「B 不出現」是可見性過濾的結果，不是粗目 B 本身沒東西）
    pm_toc = build_canon_toc(canon, PM, vendor_business_types=frozenset())
    assert any(line.startswith("B-team｜") for line in pm_toc.text.splitlines())


# ═══════════════════════════════════════════════════════════════════
# ② kb.get（resolve_canon_section）：跨受眾一律 NO_MATCH
# ═══════════════════════════════════════════════════════════════════


def test_resolve_canon_section_cross_audience_is_no_match(canon):
    miss = resolve_canon_section(
        canon, PROSPECT, f"outline:{PM_ONLY_REVIEWED_ID}", vendor_business_types=frozenset()
    )
    assert miss.ok is False and miss.error == "NO_MATCH"
    # 正對照：pm 身分拿得到內容
    hit = resolve_canon_section(
        canon, PM, f"outline:{PM_ONLY_REVIEWED_ID}", vendor_business_types=frozenset()
    )
    assert hit.ok is True and hit.provenance[0].citable is True
    assert hit.data["question_summary"] == PM_ONLY_REVIEWED_TITLE


# ═══════════════════════════════════════════════════════════════════
# ③ CandidateSelector：跨受眾細目即使分數最高也不進候選
# ═══════════════════════════════════════════════════════════════════

_QUERY = "使用者問題ZZQUERY"


def _vec(score: float) -> list:
    return [score, math.sqrt(max(0.0, 1.0 - score * score)), 0.0, 0.0]


class _FakeBackend:
    """先例：`tests/unit/agent/test_agent_turn_pm_outline_req.py::_FakeBackend`
    ＋`test_candidate_outline_req.py` 的向量表寫法（⛔ 不打真 embedding API）。"""

    def __init__(self, vectors):
        self.vectors = dict(vectors)

    async def embed(self, texts):
        return [list(self.vectors.get(t, [0.0, 0.0, 1.0, 0.0])) for t in texts]


async def _ready_index(canon):
    """讓 **pm-only 那條**與查詢最相似（分數 0.99），其餘明顯較低。"""
    vectors = {_QUERY: [1.0, 0.0, 0.0, 0.0], PM_ONLY_REVIEWED_TITLE: _vec(0.99)}
    for fine in canon.fines():
        vectors.setdefault(fine.title, _vec(0.30))
        for phrasing in fine.phrasings:
            vectors.setdefault(phrasing.text, _vec(0.20))
        for unit in fine.content_units:
            vectors.setdefault(unit, _vec(0.10))
    index = FineIndex(_FakeBackend(vectors))
    await index.prepare(canon)
    assert index.state == "ready"
    return index


async def test_top_scoring_cross_audience_fine_never_enters_candidates(canon):
    index = await _ready_index(canon)
    selector = CandidateSelector(index)

    sel_prospect = await selector.select(canon, PROSPECT, _QUERY)
    assert sel_prospect is not None and sel_prospect["miss_kind"] == "hit"
    assert PM_ONLY_REVIEWED_ID not in sel_prospect["candidate_ids"]

    # 正對照：同一個索引、同一句查詢，pm 身分**第一名**就是它（證明它真的分數最高）
    sel_pm = await selector.select(canon, PM, _QUERY)
    assert sel_pm is not None and sel_pm["candidate_ids"][0] == PM_ONLY_REVIEWED_ID


# ═══════════════════════════════════════════════════════════════════
# ④ tenant：可見集合＝∅、resolver NO_MATCH、_select_outline 走「沒有候選機制」分支
# ═══════════════════════════════════════════════════════════════════


def test_tenant_b2b_sees_nothing(canon):
    index = FineIndex(_FakeBackend({}))          # `visible_subset` ⛔ 不看索引狀態
    tenant_visible = index.visible_subset(TENANT_B2B, canon, vendor_business_types=frozenset())
    assert tenant_visible == frozenset()
    # 正對照：同一支、同一份正本，pm 身分非空
    assert index.visible_subset(PM, canon, vendor_business_types=frozenset())


def test_tenant_resolver_is_no_match_even_with_registered_canon(canon):
    register_canon(canon)
    resolver = make_outline_resolver()
    tenant = Identity(vendor_id=0, target_user="tenant", mode="b2c")
    assert tenant.resolved_audience() == "tenant"
    result = resolver(tenant, f"outline:{SHARED_ID}")
    assert result.ok is False and result.error == "NO_MATCH"
    # 正對照：同一個 resolver、prospect 身分拿得到共用細目
    assert resolver(PROSPECT, f"outline:{SHARED_ID}").ok is True


async def test_select_outline_for_tenant_takes_the_no_canon_branch(canon):
    """tenant 受眾 ∉ `CANON_VIEW_AUDIENCES` ⇒ `canon is None` ⇒ `(None, None)`
    （這**不是**降級，是這條路沒有候選機制；9.8 DSP-059 D′ S2：⛔ 不再有預組
    outline 可「原樣回傳」）。"""
    from services.agent import runtime as runtime_mod

    register_canon(canon)
    runtime = runtime_mod.AgentRuntime.__new__(runtime_mod.AgentRuntime)
    runtime._candidate_selector = None
    runtime._candidate_selectors = {}

    tenant = Identity(vendor_id=0, target_user="tenant", mode="b2c")
    out, sel_meta = await runtime._select_outline(tenant, "問題", [], [])
    assert out is None and sel_meta is None


# ═══════════════════════════════════════════════════════════════════
# ④ 9.8 DSP-059 D′ S2：隔離改釘本體——四格（合成 canon fixture，各帶正對照）
# 本檔原本測「受眾不符」的那條 `_select_outline` 測試（另一支同主題測試留在
# `test_prompt_assembler_req.py`，命名沿用不動）改寫為此四格：
# (a) target_user=[property_manager] 細目 ∉ 售前回合的 sections／text／toc
# (b) business_types=[rental] 細目對業者身分不可見（D-002 回歸網）
# (c) 未審（reviewed 缺）的細目連標題都不進 sections／text／toc
# (d) system_admin 身分的可見集合＝property_manager 的那一份（DSP-053a 折疊）
# ═══════════════════════════════════════════════════════════════════

from services.agent.canon.canon_assembler import build_canon_sections  # noqa: E402
from services.agent.canon.canon_parser import parse_canon_text  # noqa: E402
from services.agent.canon.canon_assembler import CanonSectionInvisibleError  # noqa: E402
from services.agent.outline import CandidateOutlineDoc  # noqa: E402

_ISO_FRONT = """---
audience: prospect
version: 2026-09-16.isolation-test
reviewers: [test]
language: zh-TW
budget_tokens: 12000
target_user: [prospect]
business_types: [system_provider]
---
## 合成粗目 {#A}
### 共用登入問題 {#prospect/A/iso-shared}
- sources: [kb:1]
- target_user: [prospect, property_manager]
- business_types: [system_provider]
- reviewed: {by: test, at: 2026-09-16}
- instance_applicability: general
共用內容ZZISOSHARED

### 業者專屬問題 {#prospect/A/iso-pm-only}
- sources: [kb:2]
- target_user: [property_manager]
- business_types: [system_provider]
- reviewed: {by: test, at: 2026-09-16}
- instance_applicability: general
業者內容ZZISOPMONLY

### 租賃業態限定問題 {#prospect/A/iso-rental-scoped}
- sources: [kb:3]
- target_user: [tenant]
- business_types: [rental]
- reviewed: {by: test, at: 2026-09-16}
- instance_applicability: general
租賃內容ZZISORENTAL

### 售前專屬問題 {#prospect/A/iso-prospect-only}
- sources: [kb:5]
- target_user: [prospect]
- business_types: [system_provider]
- reviewed: {by: test, at: 2026-09-16}
- instance_applicability: general
售前內容ZZISOPROSPECTONLY

### 租客專屬問題 {#prospect/A/iso-tenant-only}
- sources: [kb:6]
- target_user: [tenant]
- business_types: [system_provider]
- reviewed: {by: test, at: 2026-09-16}
- instance_applicability: general
租客內容ZZISOTENANTONLY

### 未審問題 {#prospect/A/iso-unreviewed}
- sources: [kb:4]
- target_user: [prospect, property_manager]
- business_types: [system_provider]
- instance_applicability: general
未審內容ZZISOUNREVIEWED
"""


@pytest.fixture
def iso_canon():
    return parse_canon_text(_ISO_FRONT)


def _iso_doc(canon, identity, ids, *, vendor_business_types=frozenset()):
    toc = build_canon_toc(canon, identity, vendor_business_types=vendor_business_types)
    return CandidateOutlineDoc.from_canon(
        canon, identity, ids, toc, vendor_business_types=vendor_business_types
    )


def test_iso_a_pm_only_fine_absent_from_prospect_sections_text_and_toc(iso_canon):
    """(a) `target_user=[property_manager]` 細目 ∉ 售前回合的 sections／text／toc。"""
    out = _iso_doc(iso_canon, PROSPECT, ["prospect/A/iso-shared"])
    assert "prospect/A/iso-pm-only" not in {s.id for s in out.sections}
    assert "prospect/A/iso-pm-only" not in out.text
    assert "業者內容ZZISOPMONLY" not in out.text
    # 正對照：[prospect, property_manager] 共用細目照樣出現
    assert "prospect/A/iso-shared" in {s.id for s in out.sections}
    assert "共用內容ZZISOSHARED" in out.text


def test_iso_b_rental_scoped_fine_invisible_without_matching_vendor_business_type(iso_canon):
    """(b) `business_types=[rental]` 細目對業者身分不可見（D-002 回歸網，
    ⛔ 不得補 `IS NULL` 放行）——vendor_business_types 不含 rental 時不可見；
    正對照：含 rental 時可見。⚠️ 業態限定走 b2c 分支（`_axes_visible` 的
    `vendor_business_types` 比對只在 b2c 分支生效——`property_manager`／
    `system_admin` 恆走 b2b 分支、業態鎖死 `system_provider`，不看
    `vendor_business_types`），這裡用 tenant 身分才打得到那個分支。"""
    tenant = Identity(vendor_id=1, target_user="tenant", mode="b2c")

    with pytest.raises(CanonSectionInvisibleError):
        build_canon_sections(
            iso_canon, tenant, ["prospect/A/iso-rental-scoped"], vendor_business_types=frozenset()
        )
    # 正對照：vendor_business_types 含 rental ⇒ 可見
    visible = build_canon_sections(
        iso_canon, tenant, ["prospect/A/iso-rental-scoped"],
        vendor_business_types=frozenset({"rental"}),
    )
    assert visible and visible[0].id == "prospect/A/iso-rental-scoped"


def test_iso_c_unreviewed_fine_title_never_enters_candidate_sections_text_or_toc(iso_canon):
    """(c) `reviewed` 缺的細目**連標題都不進** sections／text／toc（候選子集的
    語義比 `build_outline` 的視圖更嚴：視圖未審只藏內文出標題，候選子集
    `build_canon_sections` 整個 raise，⛔ 不產生任何節）。"""
    toc = build_canon_toc(iso_canon, PROSPECT, vendor_business_types=frozenset())
    assert "iso-unreviewed" not in toc.text and "未審問題" not in toc.text

    with pytest.raises(CanonSectionInvisibleError):
        build_canon_sections(
            iso_canon, PROSPECT, ["prospect/A/iso-unreviewed"], vendor_business_types=frozenset()
        )
    # 正對照：已審的共用細目正常組得出來
    ok = build_canon_sections(
        iso_canon, PROSPECT, ["prospect/A/iso-shared"], vendor_business_types=frozenset()
    )
    assert ok and ok[0].id == "prospect/A/iso-shared"


def test_iso_d_system_admin_sees_property_manager_fines_only(iso_canon):
    """(d) `system_admin` 的正本可見集合＝`property_manager` 的那一份（DSP-053a）。

    折疊住在 `_axes_visible` 的 b2b 比對鑰匙：`system_admin` 看得到 `[property_manager]`
    細目，看不到 `[prospect]`／`[tenant]` 專屬細目——⛔ 折疊 ⛔ 不等於 b2b 分支全放行。
    正對照＝真正的 `property_manager` 身分在同一份 fixture 上撈到同一組結果。
    """
    system_admin = Identity(vendor_id=0, target_user="system_admin", mode="b2b")
    assert system_admin.resolved_audience() == "property_manager"

    seen = build_canon_sections(
        iso_canon, system_admin, ["prospect/A/iso-pm-only"], vendor_business_types=frozenset()
    )
    assert seen and seen[0].id == "prospect/A/iso-pm-only"

    for invisible_id in ("prospect/A/iso-prospect-only", "prospect/A/iso-tenant-only"):
        with pytest.raises(CanonSectionInvisibleError):
            build_canon_sections(
                iso_canon, system_admin, [invisible_id], vendor_business_types=frozenset()
            )

    # 正對照：property_manager 身分在同一份 fixture 上得到同一組可見／不可見
    ok = build_canon_sections(
        iso_canon, PM, ["prospect/A/iso-pm-only"], vendor_business_types=frozenset()
    )
    assert ok and ok[0].id == "prospect/A/iso-pm-only"
    for invisible_id in ("prospect/A/iso-prospect-only", "prospect/A/iso-tenant-only"):
        with pytest.raises(CanonSectionInvisibleError):
            build_canon_sections(
                iso_canon, PM, [invisible_id], vendor_business_types=frozenset()
            )


# ═══════════════════════════════════════════════════════════════════
# ④b F1 契約：ids 含一個未審／不可見細目 ⇒ raise 被接成 toc-only 降級
# ═══════════════════════════════════════════════════════════════════


async def test_ids_containing_invisible_fine_degrades_to_toc_only_with_both_violations(canon):
    """選取器回了視圖外／不可見的 id（資料錯／索引對到別份正本）⇒ `_select_outline`
    降級為 toc-only＋`candidate_invisible_id`／`candidate_fallback_toc_only` 兩個
    violation 同時記到，⛔ 不炸掉整個回合、⛔ 不把那個 id 的內容塞進去。"""
    from services.agent import runtime as runtime_mod

    register_canon(canon)
    index = await _ready_index(canon)

    class _StuffingSelector(CandidateSelector):
        async def select(self, doc, identity, query, *, vendor_business_types=frozenset()):
            return {
                "candidate_ids": [PM_ONLY_REVIEWED_ID],      # ⛔ 對 prospect 不可見
                "winning_key_kind": {PM_ONLY_REVIEWED_ID: "title"},
                "scores": {PM_ONLY_REVIEWED_ID: 0.99},
                "miss_kind": "hit",
            }

    runtime = runtime_mod.AgentRuntime.__new__(runtime_mod.AgentRuntime)
    runtime._candidate_selector = None
    runtime._candidate_selectors = {"prospect": _StuffingSelector(index)}

    violations: list = []
    out, sel_meta = await runtime._select_outline(PROSPECT, _QUERY, [], violations)
    assert "candidate_invisible_id" in violations
    assert "candidate_fallback_toc_only" in violations
    assert sel_meta["miss_kind"] == "index_unavailable"
    assert PM_ONLY_REVIEWED_ID not in out.text
    fine_sections = [s for s in out.sections if s.id != TOC_SECTION_ID]
    assert fine_sections == []
    # 正對照見下方 test_all_visible_candidate_ids_produce_fine_sections_as_positive_control


async def test_all_visible_candidate_ids_produce_fine_sections_as_positive_control(canon):
    """正對照：全可見時候選節組得起來、無 `candidate_invisible_id`／
    `candidate_fallback_toc_only`。"""
    from services.agent import runtime as runtime_mod

    register_canon(canon)
    index = await _ready_index(canon)
    runtime = runtime_mod.AgentRuntime.__new__(runtime_mod.AgentRuntime)
    runtime._candidate_selector = None
    runtime._candidate_selectors = {"prospect": CandidateSelector(index)}

    violations: list = []
    out, sel_meta = await runtime._select_outline(PROSPECT, _QUERY, [], violations)
    assert sel_meta["miss_kind"] == "hit"
    assert "candidate_invisible_id" not in violations
    assert "candidate_fallback_toc_only" not in violations
    assert [s.id for s in out.sections if s.id != TOC_SECTION_ID]


# ═══════════════════════════════════════════════════════════════════
# ⑨ 預算：env ⛔ 不得把上限開大；真實兩視圖都在上限內
# ═══════════════════════════════════════════════════════════════════


def test_env_cannot_raise_the_cap_but_can_lower_it(monkeypatch):
    monkeypatch.setenv("AGENT_OUTLINE_K_TOKEN_LIMIT_PROSPECT", "999999")
    assert default_k_token_limit("prospect") == 12_000 == OUTLINE_K_TOKEN_LIMIT["prospect"]
    # 正對照：設小的照樣生效（⛔ 不是「env 一律被忽略」）
    monkeypatch.setenv("AGENT_OUTLINE_K_TOKEN_LIMIT_PROSPECT", "1")
    assert default_k_token_limit("prospect") == 1

    monkeypatch.setenv("AGENT_OUTLINE_TOC_TOKEN_LIMIT_PM", "999999")
    assert default_toc_token_limit("property_manager") == 8_000 == OUTLINE_TOC_TOKEN_LIMIT["property_manager"]
    monkeypatch.setenv("AGENT_OUTLINE_TOC_TOKEN_LIMIT_PM", "1")
    assert default_toc_token_limit("property_manager") == 1


_SHELF_DIR = os.path.join(_RAG, "canon", "jgb")
_FINE_HEADING_RE = re.compile(r"^### .+\{#jgb/[A-Z]/[a-z0-9-]+\}\s*$", re.M)


def _grep_reviewed_count(shelf_dir=None) -> int:
    """獨立於 parser 的第二條管道：直接數 `.md` 原始文字裡的 `- reviewed:` 行數。"""
    d = shelf_dir or _SHELF_DIR
    total = 0
    for fname in sorted(os.listdir(d)):
        if len(fname) == 4 and fname.endswith(".md"):
            text = open(os.path.join(d, fname), encoding="utf-8").read()
            total += len(re.findall(r"^- reviewed:", text, re.M))
    return total


def _mark_first_unreviewed(text: str) -> tuple[str, bool]:
    """在第一個「尚未被標 reviewed」的細目後插入一行；已經有的跳過。回傳 (新文字, 是否插入)。"""
    matches = list(_FINE_HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.end():next_start]
        if re.search(r"^- reviewed:", block, re.M):
            continue
        return (
            text[:m.end()] + "\n- reviewed: {by: s4-measurement, at: 2026-09-23}" + text[m.end():],
            True,
        )
    return text, False


def _single_reviewed_canon_copy(tmp_path):
    """版控正本的 tmp 複本，只把**現樹尚未已審**的細目中的第一條標 `reviewed`
    （⛔ 不動版控 `canon/`；已審的細目跳過，⛔ 無條件附加會撞 `canon_parser` 的
    『屬性重複 reviewed』——S4 之後 D／E 會混入真的 `reviewed`）。

    用途：證明 `test_real_views_fit_the_budget` 的「未審 ⇒ 兩把尺皆 0」斷言不是
    恆零的空判斷——只要正本裡多出一條已審細目，量尺就必須量到非零。
    """
    baseline = _grep_reviewed_count()
    dst = tmp_path / "single-reviewed-canon"
    shelf_dst = dst / CANON_NAME
    shelf_dst.mkdir(parents=True)
    marked_once = False
    for fname in sorted(os.listdir(_SHELF_DIR)):
        if not (len(fname) == 4 and fname.endswith(".md")):
            continue
        text = open(os.path.join(_SHELF_DIR, fname), encoding="utf-8").read()
        if not marked_once:
            new_text, inserted = _mark_first_unreviewed(text)
            if inserted:
                text = new_text
                marked_once = True
        (shelf_dst / fname).write_text(text, encoding="utf-8")
    assert marked_once, "沒有標到任何一條細目（可能全部細目皆已審），注入沒生效"
    doc = parse_canon_dir(str(shelf_dst))
    assert sum(1 for f in doc.fines() if f.reviewed_by is not None) == baseline + 1
    export_json(doc, str(dst / f"{CANON_NAME}.json"))
    export_catalog(doc, str(shelf_dst / "CATALOG.md"))
    return dst


def _all_unreviewed_canon_copy(tmp_path):
    """版控正本的 tmp 複本，撤掉**全部** `- reviewed:` 行（⛔ 不動版控 `canon/`）。

    Plan 9.24：正本全審後已沒有「未審」細目可標，`_single_reviewed_canon_copy` 的
    正對照無從注入；改用反向 mutation——全部撤審 ⇒ 兩把尺必為 0，證明全審時的
    「兩把尺皆非零」斷言不是恆真的空判斷。
    """
    baseline = _grep_reviewed_count()
    assert baseline > 0, "正本沒有任何已審細目，反向 mutation 無從撤審"
    dst = tmp_path / "all-unreviewed-canon"
    shelf_dst = dst / CANON_NAME
    shelf_dst.mkdir(parents=True)
    removed = 0
    for fname in sorted(os.listdir(_SHELF_DIR)):
        if not (len(fname) == 4 and fname.endswith(".md")):
            continue
        text = open(os.path.join(_SHELF_DIR, fname), encoding="utf-8").read()
        text, n = re.subn(r"^- reviewed:[^\n]*\n", "", text, flags=re.M)
        removed += n
        (shelf_dst / fname).write_text(text, encoding="utf-8")
    assert removed == baseline, (removed, baseline)
    doc = parse_canon_dir(str(shelf_dst))
    assert sum(1 for f in doc.fines() if f.reviewed_by is not None) == 0
    export_json(doc, str(dst / f"{CANON_NAME}.json"))
    export_catalog(doc, str(shelf_dst / "CATALOG.md"))
    return dst


async def test_real_views_fit_the_budget(monkeypatch, tmp_path):
    """真實正本兩視圖的 `check_turn_budget` 皆通過；正對照：`k_limit=-1` ⇒ raise；
    mutation：多一條已審細目 ⇒ 兩把尺必變非零。

    計畫 9.10 S4：原本逐數釘住 acceptance ②（9.8 plan-9.8-turn-budget-dprime-20260916
    S1）的是**舊** 210 條正本（含 20 條已審）手算的 k_upper／toc_tokens；`canon_sha256`
    不符前綴時整條 **skip**——換正本後 sha 必不符，量尺因此**靜默停止運作**（skip
    不進紅燈數，「≤9 條紅」這條停止條件看不見它）。改法：
    - 不再靠比對 sha 決定要不要 skip——直接對**現在**的正本斷言（新正本 515 條
      全未審，DSP-066：未審 ⇒ 模型不可見 ⇒ 兩把尺對兩受眾皆為 0，這正是 S4
      量測 (a) 組的控制組數字，見 `inputs/s4-measurement-*.md`）。
    - 原本「`k_limit=1` ⇒ raise」的正對照在 k_upper 恆為 0 時已無法觸發（`0>1`
      恆假），改用不依賴 k_upper 實際值的負值上限（`0>=` 任意 token 數 `>-1` 恆真）。
    - 額外用一份「只多標一條 reviewed」的 tmp 複本證明本測試的斷言不是恆零的
      空判斷：正本裡出現已審細目時，兩把尺確實量得到非零值。
    """
    monkeypatch.delenv("AGENT_OUTLINE_K_TOKEN_LIMIT_PROSPECT", raising=False)
    monkeypatch.delenv("AGENT_OUTLINE_K_TOKEN_LIMIT_PM", raising=False)
    monkeypatch.delenv("AGENT_OUTLINE_TOC_TOKEN_LIMIT_PROSPECT", raising=False)
    monkeypatch.delenv("AGENT_OUTLINE_TOC_TOKEN_LIMIT_PM", raising=False)

    canon = load_canon_or_die(resolve_canon_dir())
    # Plan 9.15 S3b：不再寫死「全未審」——已審集合＝parser 讀出的集合，與一條獨立
    # 管道（grep `- reviewed:` 行數）交叉核對；再以現樹已審集合（而非寫死 0）為基準：
    # 該受眾看得到的細目中只要有一條已審，量尺就該非零；一條都沒有才是 0。
    # 現況兩邊皆為 0，斷言在現況下照樣成立、不變弱。
    reviewed_ids = [f.id for f in canon.fines() if f.reviewed_by is not None]
    assert len(reviewed_ids) == _grep_reviewed_count(), (reviewed_ids, _grep_reviewed_count())
    prospect_has_reviewed = any(
        f.reviewed_by is not None and "prospect" in f.target_user for f in canon.fines()
    )
    pm_has_reviewed = any(
        f.reviewed_by is not None and "property_manager" in f.target_user for f in canon.fines()
    )

    prospect_doc = await build_audience_outline("prospect")
    pm_doc = await build_audience_outline("property_manager")

    prospect_toc = next(s for s in prospect_doc.sections if s.id == TOC_SECTION_ID)
    pm_toc = next(s for s in pm_doc.sections if s.id == TOC_SECTION_ID)

    prospect_budget = check_turn_budget(
        prospect_doc.sections, prospect_toc,
        k_limit=default_k_token_limit("prospect"),
        toc_limit=default_toc_token_limit("prospect"),
    )
    pm_budget = check_turn_budget(
        pm_doc.sections, pm_toc,
        k_limit=default_k_token_limit("property_manager"),
        toc_limit=default_toc_token_limit("property_manager"),
    )

    # 該受眾已審集合非空 ⇒ 兩把尺該非零；現況全未審 ⇒ 仍是 0（可見性判斷壞掉 ⇒
    # 某一項與這裡的期望值對不上，見量測 (a)）。
    if prospect_has_reviewed:
        assert prospect_budget.k_upper > 0 and prospect_budget.toc_tokens > 0
    else:
        assert prospect_budget.k_upper == 0
        assert prospect_budget.toc_tokens == 0
    if pm_has_reviewed:
        assert pm_budget.k_upper > 0 and pm_budget.toc_tokens > 0
    else:
        assert pm_budget.k_upper == 0
        assert pm_budget.toc_tokens == 0

    # 正對照：k_limit=-1（不依賴 k_upper 實際值）⇒ `check_turn_budget` 必 raise。
    with pytest.raises(OutlineBudgetExceeded):
        check_turn_budget(prospect_doc.sections, prospect_toc, k_limit=-1, toc_limit=8_000)

    # mutation：證明上面的斷言會隨已審狀態變動、不是空判斷。
    # - 還有未審細目 ⇒ 複本多標一條已審 ⇒ prospect 兩把尺必非零（原做法）；
    # - 全審（Plan 9.24 起）⇒ 已無未審可標 ⇒ 反向：複本全部撤審 ⇒ 兩受眾兩把尺必為 0。
    monkeypatch.setenv(DB_ENV_KEY, "test")
    fully_reviewed = len(reviewed_ids) == len(canon.fines())
    if fully_reviewed:
        monkeypatch.setenv(CANON_DIR_ENV, str(_all_unreviewed_canon_copy(tmp_path)))
    else:
        monkeypatch.setenv(CANON_DIR_ENV, str(_single_reviewed_canon_copy(tmp_path)))
    reset_canon_registry()
    try:
        mutated = {aud: await build_audience_outline(aud) for aud in ("prospect", "property_manager")}
    finally:
        reset_canon_registry()
    mutated_budget = {}
    for aud, doc in mutated.items():
        toc = next(s for s in doc.sections if s.id == TOC_SECTION_ID)
        mutated_budget[aud] = check_turn_budget(
            doc.sections, toc,
            k_limit=default_k_token_limit(aud), toc_limit=default_toc_token_limit(aud),
        )
    if fully_reviewed:
        for aud, b in mutated_budget.items():
            assert b.k_upper == 0 and b.toc_tokens == 0, (aud, b)
    else:
        assert mutated_budget["prospect"].k_upper > 0 and mutated_budget["prospect"].toc_tokens > 0


def test_versioned_canon_dir_is_untouched(tmp_path):
    """守門：本檔只讀版控正本、⛔ 不寫（複製到 tmp 才改）。"""
    src = resolve_canon_dir()
    dst = tmp_path / "canon"
    dst.mkdir()
    shutil.copytree(src / "jgb", dst / "jgb")
    shutil.copy2(src / "jgb.json", dst / "jgb.json")
    assert load_canon_or_die(dst).canon_sha256 == load_canon_or_die(src).canon_sha256
