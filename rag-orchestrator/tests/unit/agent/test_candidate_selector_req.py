"""unit：候選選取 `CandidateSelector`＋`FineIndex.visible_subset`（任務 3.3b）。

Plan `inputs/plan-3.3-fine-index-selector-20260907.md` §4「3.3b」6–8。

⚠️ 本檔**不碰版控正本**（`rag-orchestrator/canon/*`）——正本的真實講法是（去識別後的）
真流量，⛔ 不拿它當測試材料。所有情境都用合成正本（`parse_canon_text`）。
⚠️ 隱私那條測試的正對照組（先證明 `caplog`／`capsys` 兩個擷取器都活著）**⛔ 不得刪**：
沒有它，「沒抓到任何文字」可能只是量尺壞了。

## 假向量怎麼設計
查詢向量固定 `Q=[1,0,0,0]`，其餘向量都是**單位向量**，餘弦＝第一個分量：
`[1,0,0,0]`⇒1.0、`[0.8,0.6,0,0]`⇒0.8、`[0.6,0.8,0,0]`⇒0.6、`[0,0,1,0]`⇒0.0。
⚠️ 未列在 `vectors` 的文字一律拿 `_ORTHOGONAL`（分數 0.0）——⛔ 不用隨機／雜湊向量，
否則「誰排前面」會變成雜湊的性質而不是被測邏輯的性質。
"""
from __future__ import annotations

import asyncio
import json
import logging

import pytest

from services.agent.canon import fine_index as FI
from services.agent.canon.candidate_selector import (
    K,
    QUERY_EMBED_TIMEOUT_S,
    CandidateSelector,
    MissKind,
)
from services.agent.canon.canon_assembler import canon_visible
from services.agent.canon.canon_parser import parse_canon_text
from services.agent.canon.fine_index import FineIndex
from services.agent.identity import Identity

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:3.3"),
]

# ── 合成材料 ────────────────────────────────────────────────────────────
# 標題／講法／查詢都塞唯一可搜尋標記（`ZZ*`），隱私測試就靠它們判外洩。

_FRONT_MATTER = """---
audience: prospect
version: 2026-09-07.test
reviewers: [test]
language: zh-TW
budget_tokens: 12000
target_user: [prospect]
business_types: [system_provider]
---
## 合成粗目 {#A}
"""

QUERY = "查詢文字ZZQUERY"
_Q = [1.0, 0.0, 0.0, 0.0]
_ORTHOGONAL = [0.0, 0.0, 1.0, 0.0]        # 與 Q 正交 ⇒ 餘弦 0.0
_HIGH = [1.0, 0.0, 0.0, 0.0]              # 1.0
_MID_HI = [0.8, 0.6, 0.0, 0.0]            # 0.8
_MID_LO = [0.6, 0.8, 0.0, 0.0]            # 0.6


def _fine_block(slug, title, *, target_user, business_types, phrasings=(), reviewed=True):
    lines = [f"### {title} {{#prospect/A/{slug}}}"]
    if phrasings:
        lines.append("- phrasings:")
        for text, status in phrasings:
            lines.append(f'  - {{text: "{text}", source: "question_summary:1", status: {status}}}')
    lines += [
        "- sources: [kb:1]",
        f"- target_user: [{', '.join(target_user)}]",
        f"- business_types: [{', '.join(business_types)}]",
    ]
    if reviewed:
        lines.append("- reviewed: {by: test, at: 2026-09-07}")
    lines += ["- instance_applicability: general", f"內容句{slug}", ""]
    return "\n".join(lines)


def _doc(*blocks):
    return parse_canon_text(_FRONT_MATTER + "".join(blocks))


def fid(slug: str) -> str:
    return f"prospect/A/{slug}"


class _Missing:
    """「沒有覆寫回傳值」的哨兵——⛔ 不能用 `None`，`None` 本身就是要測的回傳值之一。"""


_MISSING = _Missing()


class _FakeBackend:
    """假 embedding 後端：文字 → 明示向量；未列出的一律 `_ORTHOGONAL`（0.0 分）。"""

    def __init__(self, vectors=None, *, raises=False, returns=_MISSING, sleep_s=None):
        self.vectors = dict(vectors or {})
        self.calls: list[int] = []
        self.texts: list[str] = []
        self._raises = raises
        self._returns = returns          # 明示回傳值（測形狀不合）
        self._sleep_s = sleep_s

    async def embed(self, texts):
        self.calls.append(len(texts))
        self.texts.extend(texts)
        if self._sleep_s is not None:
            await asyncio.sleep(self._sleep_s)
        if self._raises:
            raise RuntimeError("後端故障（測試用）")
        if self._returns is not _MISSING:
            return self._returns
        return [list(self.vectors.get(t, _ORTHOGONAL)) for t in texts]


#: 建構子別名（讀起來短一點；⛔ 無其他行為差異）
_backend = _FakeBackend


# ── 情境 1：可見性與排序（doc S）────────────────────────────────────────

_T_ALPHA, _P_ALPHA = "標題ZZALPHA", "講法ZZALPHA"
_T_BETA, _P_BETA = "標題ZZBETA", "講法ZZBETA"
_T_HIDDEN, _P_HIDDEN = "標題ZZHIDDEN", "講法ZZHIDDEN"

_DOC_S_VECTORS = {
    QUERY: _Q,
    _T_HIDDEN: _HIGH, _P_HIDDEN: _HIGH,      # 分數最高，但對 prospect 不可見
    _T_BETA: _MID_HI, _P_BETA: _ORTHOGONAL,  # 0.8
    _T_ALPHA: _MID_LO, _P_ALPHA: _ORTHOGONAL,  # 0.6
}


def _doc_s():
    """三細目：alpha／beta 對 prospect 可見；hidden-pm 只有 pm 看得到、但分數最高。"""
    return _doc(
        _fine_block("vis-alpha", _T_ALPHA, target_user=["prospect"],
                    business_types=["system_provider"],
                    phrasings=[(_P_ALPHA, "approved")]),
        _fine_block("vis-beta", _T_BETA, target_user=["prospect"],
                    business_types=["system_provider"],
                    phrasings=[(_P_BETA, "approved")]),
        _fine_block("hidden-pm", _T_HIDDEN, target_user=["property_manager"],
                    business_types=["system_provider"],
                    phrasings=[(_P_HIDDEN, "approved")]),
    )


B2B_PROSPECT = Identity(vendor_id=1, target_user="prospect", mode="b2b")
B2B_PM = Identity(vendor_id=1, target_user="property_manager", mode="b2b")
B2C_TENANT = Identity(vendor_id=1, target_user="tenant", mode="b2c")
#: ⚠️ 嚴格分支判準：`target_user=property_manager` **即使 mode=b2c** 也走 b2b 分支。
PM_IN_B2C = Identity(vendor_id=1, target_user="property_manager", mode="b2c")
RENTAL = frozenset({"rental"})


async def _ready(doc, vectors):
    index = FineIndex(_backend(vectors))
    await index.prepare(doc)
    assert index.state == "ready"
    return index


async def test_invisible_fine_never_enters_candidates_even_when_it_scores_highest():
    """⛔ 不可見的細目不得出現在 `candidate_ids`——即使它是全場最高分。"""
    doc = _doc_s()
    index = await _ready(doc, _DOC_S_VECTORS)
    sel = await CandidateSelector(index).select(doc, B2B_PROSPECT, QUERY)

    assert sel is not None
    assert sel["miss_kind"] == "hit"
    assert sel["candidate_ids"] == [fid("vis-beta"), fid("vis-alpha")]
    assert fid("hidden-pm") not in sel["candidate_ids"]
    assert fid("hidden-pm") not in sel["scores"]

    # 正對照：hidden-pm **確實**在索引裡且分數最高（不是因為它根本沒被索引才沒出現）
    hidden_scores = [
        sum(x * y for x, y in zip(_Q, vec)) for _kind, vec in index.entries_for(fid("hidden-pm"))
    ]
    assert hidden_scores and max(hidden_scores) > max(sel["scores"].values())


async def test_scores_are_sorted_desc_and_only_cover_returned_candidates():
    doc = _doc_s()
    index = await _ready(doc, _DOC_S_VECTORS)
    sel = await CandidateSelector(index).select(doc, B2B_PROSPECT, QUERY)

    assert sel["scores"][fid("vis-beta")] == pytest.approx(0.8)
    assert sel["scores"][fid("vis-alpha")] == pytest.approx(0.6)
    assert set(sel["scores"]) == set(sel["candidate_ids"]) == set(sel["winning_key_kind"])
    assert all(v == "title" for v in sel["winning_key_kind"].values())


async def test_top_k_is_five():
    """可見細目多於 K ⇒ 只給前 5 名，且是分數最高的 5 個。"""
    blocks, vectors = [], {QUERY: _Q}
    for i in range(8):
        title = f"標題ZZTOPK{i}"
        blocks.append(_fine_block(f"topk-{i}", title, target_user=["prospect"],
                                  business_types=["system_provider"]))
        # 分數遞減：i=0 最高
        vectors[title] = [1.0 - i * 0.1, (1.0 - (1.0 - i * 0.1) ** 2) ** 0.5, 0.0, 0.0]
    doc = _doc(*blocks)
    index = await _ready(doc, vectors)
    sel = await CandidateSelector(index).select(doc, B2B_PROSPECT, QUERY)

    assert K == 5
    assert len(sel["candidate_ids"]) == K
    assert sel["candidate_ids"] == [fid(f"topk-{i}") for i in range(5)]


async def test_exact_tie_falls_back_to_fine_id_order_not_document_order():
    """同分 ⇒ `fine_id` 字典序。⚠️ 正本序刻意與字典序相反，⛔ 不得靠迭代順序碰巧對。"""
    t_bbb, t_aaa = "標題ZZTIEB", "標題ZZTIEA"
    doc = _doc(
        _fine_block("tie-bbb", t_bbb, target_user=["prospect"],
                    business_types=["system_provider"]),
        _fine_block("tie-aaa", t_aaa, target_user=["prospect"],
                    business_types=["system_provider"]),
    )
    index = await _ready(doc, {QUERY: _Q, t_bbb: _MID_LO, t_aaa: _MID_LO})
    sel = await CandidateSelector(index).select(doc, B2B_PROSPECT, QUERY)

    assert [f.id for f in doc.fines()] == [fid("tie-bbb"), fid("tie-aaa")]   # 正對照：正本序
    assert sel["scores"][fid("tie-aaa")] == sel["scores"][fid("tie-bbb")]    # 真的同分
    assert sel["candidate_ids"] == [fid("tie-aaa"), fid("tie-bbb")]


# ── 情境 2：winning_key_kind ────────────────────────────────────────────

_T_PHR, _P_PHR = "標題ZZPHRWINS", "講法ZZPHRWINS"
_T_KTIE, _P_KTIE = "標題ZZKINDTIE", "講法ZZKINDTIE"


def _doc_w():
    return _doc(
        _fine_block("phr-wins", _T_PHR, target_user=["prospect"],
                    business_types=["system_provider"], phrasings=[(_P_PHR, "approved")]),
        _fine_block("tie-kind", _T_KTIE, target_user=["prospect"],
                    business_types=["system_provider"], phrasings=[(_P_KTIE, "approved")]),
    )


_DOC_W_VECTORS = {
    QUERY: _Q,
    _T_PHR: _ORTHOGONAL, _P_PHR: _HIGH,      # 講法勝
    _T_KTIE: _MID_LO, _P_KTIE: _MID_LO,      # 完全同分 ⇒ 取 title
}


async def test_winning_key_kind_prefers_phrasing_when_it_scores_higher_and_title_on_a_tie():
    doc = _doc_w()
    index = await _ready(doc, _DOC_W_VECTORS)
    sel = await CandidateSelector(index).select(doc, B2B_PROSPECT, QUERY)

    assert sel["winning_key_kind"][fid("phr-wins")] == "phrasing"
    assert sel["winning_key_kind"][fid("tie-kind")] == "title"
    assert set(sel["winning_key_kind"].values()) <= {"title", "phrasing"}
    # 正對照：tie-kind 的標題與講法**確實**都在索引裡（同分不是因為只剩一個鍵）
    assert [k for k, _v in index.entries_for(fid("tie-kind"))] == ["title", "phrasing"]


async def test_serialized_selection_never_contains_a_phrasing_key_id():
    """F18：trace ⛔ 不得帶 `ph:<sha8>`——講法對照表就在 repo，記 id 等於可還原問句。"""
    doc = _doc_w()
    index = await _ready(doc, _DOC_W_VECTORS)
    sel = await CandidateSelector(index).select(doc, B2B_PROSPECT, QUERY)

    serialized = json.dumps(sel, ensure_ascii=False)
    assert "ph:" not in serialized
    # 講法原文同樣不得出現在回傳結構裡
    assert _P_PHR not in serialized and _T_PHR not in serialized
    # 正對照：內部**確實**算得出 `ph:` 形狀的鍵 id（不是因為沒實作才找不到）
    assert FI._phrasing_key_id(_P_PHR).startswith("ph:")


# ── 情境 3：不服務一律 None（⛔ 不變寬）────────────────────────────────

async def test_sha_mismatch_returns_none():
    """索引是對別份正本建的 ⇒ `None`（⛔ 不拿別份的分數服務這份 doc）。"""
    doc_s, doc_w = _doc_s(), _doc_w()
    index = await _ready(doc_s, {**_DOC_S_VECTORS, **_DOC_W_VECTORS})
    assert doc_w.canon_sha256 != index.prepared_sha       # 正對照：sha 真的不同

    assert await CandidateSelector(index).select(doc_w, B2B_PROSPECT, QUERY) is None


async def test_absent_index_returns_none():
    doc = _doc_s()
    index = FineIndex(_backend(_DOC_S_VECTORS))           # 從未 prepare
    assert index.state == "absent"
    assert await CandidateSelector(index).select(doc, B2B_PROSPECT, QUERY) is None


async def test_not_ready_index_returns_none():
    doc = _doc_s()
    index = FineIndex(_backend(raises=True))
    await index.prepare(doc)
    assert index.state == "not_ready"
    assert await CandidateSelector(index).select(doc, B2B_PROSPECT, QUERY) is None


@pytest.mark.parametrize(
    "kwargs,label",
    [
        (dict(raises=True), "後端 raise"),
        (dict(returns=[None]), "回 None 向量"),
        (dict(returns=[]), "回傳筆數不符"),
        (dict(returns=[[1.0, 0.0]]), "維度不符"),
        (dict(returns=[[0.0, 0.0, 0.0, 0.0]]), "零範數"),
        (dict(returns=[[float("nan"), 0.0, 0.0, 0.0]]), "NaN"),
    ],
)
async def test_query_embedding_failures_return_none_and_never_any_candidate(kwargs, label):
    """查詢向量拿不到 ⇒ `None`。⛔ 三者皆不得回任何 candidate（不得退成「全給」）。"""
    doc = _doc_s()
    index = await _ready(doc, _DOC_S_VECTORS)             # 索引本身是好的
    sel = await CandidateSelector(index, _backend(**kwargs)).select(doc, B2B_PROSPECT, QUERY)
    assert sel is None, f"[{label}] 回了 {sel!r}——失敗路徑變寬了"


async def test_query_embedding_timeout_returns_none():
    """後端 sleep 超過注入的小逾時 ⇒ `None`（⛔ 不等滿 3 秒也不回半成品）。"""
    doc = _doc_s()
    index = await _ready(doc, _DOC_S_VECTORS)
    slow = _backend(_DOC_S_VECTORS, sleep_s=5)            # 遠大於下面注入的 0.05s
    sel = await CandidateSelector(index, slow, timeout_s=0.05).select(doc, B2B_PROSPECT, QUERY)

    assert sel is None
    assert slow.calls, "後端根本沒被呼叫 ⇒ 這條測的不是逾時"


async def test_timeout_cannot_be_widened_beyond_the_hard_ceiling():
    """`timeout_s` 是保護不是旋鈕：傳 60 仍以 `QUERY_EMBED_TIMEOUT_S` 為上限。"""
    index = FineIndex(_backend())
    assert CandidateSelector(index, timeout_s=60.0)._timeout_s == QUERY_EMBED_TIMEOUT_S == 3.0
    assert CandidateSelector(index, timeout_s=0.5)._timeout_s == 0.5     # 收緊仍可


async def test_query_backend_defaults_to_the_index_backend():
    """省略 `backend` ⇒ 用建索引的那顆（同模型才有共同向量空間）。"""
    doc = _doc_s()
    backend = _backend(_DOC_S_VECTORS)
    index = FineIndex(backend)
    await index.prepare(doc)
    calls_after_prepare = len(backend.calls)

    sel = await CandidateSelector(index).select(doc, B2B_PROSPECT, QUERY)
    assert sel is not None
    assert len(backend.calls) == calls_after_prepare + 1
    assert backend.texts[-1] == QUERY


# ── 情境 4：none_visible／no_candidate ──────────────────────────────────

async def test_none_visible_when_identity_sees_nothing():
    doc = _doc_s()
    index = await _ready(doc, _DOC_S_VECTORS)
    # b2c 租客＋業者無業態 ⇒ doc S 全部細目都是 system_provider，一個都看不到
    sel = await CandidateSelector(index).select(
        doc, B2C_TENANT, QUERY, vendor_business_types=frozenset()
    )
    assert sel == {
        "candidate_ids": [], "winning_key_kind": {}, "scores": {}, "miss_kind": "none_visible",
    }
    # 正對照：同一份索引對 prospect **有**候選（不是索引壞了才空）
    assert (await CandidateSelector(index).select(doc, B2B_PROSPECT, QUERY))["candidate_ids"]


class _NoEntriesIndex:
    """⚠️ 刻意構造：`ready`、可見子集非空，但每個細目都沒有索引項。

    真實的 `FineIndex` 走不到這裡——`prepare` 對每個細目至少建一個標題鍵，任一鍵失敗
    就整份丟成 `not_ready`。本替身**只為釘住 `no_candidate` 這條分支存在且回空**，
    ⛔ 不代表產線可達。
    """

    def __init__(self, real: FineIndex):
        self._real = real

    state = property(lambda self: self._real.state)
    prepared_sha = property(lambda self: self._real.prepared_sha)
    dim = property(lambda self: self._real.dim)
    backend = property(lambda self: self._real.backend)

    def visible_subset(self, identity, doc, *, vendor_business_types):
        return self._real.visible_subset(identity, doc,
                                         vendor_business_types=vendor_business_types)

    def entries_for(self, fine_id):
        return []


async def test_no_candidate_is_unreachable_with_a_real_index_and_pinned_with_a_stub():
    doc = _doc_s()
    real = await _ready(doc, _DOC_S_VECTORS)

    # ① 真索引：每個細目都有索引項 ⇒ 走不到 no_candidate
    assert all(real.entries_for(f.id) for f in doc.fines()), "有細目沒有索引項 ⇒ 前提已變"
    assert (await CandidateSelector(real).select(doc, B2B_PROSPECT, QUERY))["miss_kind"] == "hit"

    # ② 構造替身才走得到
    stub = _NoEntriesIndex(real)
    sel = await CandidateSelector(stub, _backend(_DOC_S_VECTORS)).select(doc, B2B_PROSPECT, QUERY)
    assert sel == {
        "candidate_ids": [], "winning_key_kind": {}, "scores": {}, "miss_kind": "no_candidate",
    }


async def test_index_unavailable_is_declared_but_never_returned_by_select():
    """`index_unavailable` 在值域內、但 `select` ⛔ 不回它——索引不可用時回 `None`，
    由 4.1 在 trace 上寫這個值（Plan §1.6）。"""
    from typing import get_args as _get_args

    assert "index_unavailable" in _get_args(MissKind)
    doc = _doc_s()
    for index in (FineIndex(_backend()), await _ready(doc, _DOC_S_VECTORS)):
        sel = await CandidateSelector(index, _backend(_DOC_S_VECTORS)).select(
            doc, B2B_PROSPECT, QUERY)
        assert sel is None or sel["miss_kind"] != "index_unavailable"


# ── 情境 5：visible_subset ＝ 逐細目 canon_visible ──────────────────────

_VIS_TITLES = {
    "vis-alpha": "標題ZZVA", "hidden-pm": "標題ZZVH", "tenant-rental": "標題ZZVT",
    "pm-rental": "標題ZZVP", "allusers-nobt": "標題ZZVU", "nobody": "標題ZZVN",
}


def _doc_v():
    """六細目，刻意讓四組身分各看到**不同**的集合（否則等式「處處成立」沒有鑑別力）。"""
    return _doc(
        _fine_block("vis-alpha", _VIS_TITLES["vis-alpha"], target_user=["prospect"],
                    business_types=["system_provider"]),
        _fine_block("hidden-pm", _VIS_TITLES["hidden-pm"], target_user=["property_manager"],
                    business_types=["system_provider"]),
        _fine_block("tenant-rental", _VIS_TITLES["tenant-rental"], target_user=["tenant"],
                    business_types=["rental"]),
        # ⚠️ 嚴格分支的鑑別列：若 (property_manager, b2c) 誤走 b2c 分支，這列會變可見
        _fine_block("pm-rental", _VIS_TITLES["pm-rental"], target_user=["property_manager"],
                    business_types=["rental"]),
        _fine_block("allusers-nobt", _VIS_TITLES["allusers-nobt"], target_user=["all_users"],
                    business_types=[]),
        # 未審：⛔ 記憶體側一律不可見（`canon_visible` 首行）
        _fine_block("nobody", _VIS_TITLES["nobody"], target_user=["prospect"],
                    business_types=["system_provider"], reviewed=False),
    )


_VIS_CASES = [
    (B2B_PROSPECT, RENTAL, {"vis-alpha"}),
    (B2B_PM, RENTAL, {"hidden-pm"}),
    (B2C_TENANT, RENTAL, {"tenant-rental", "allusers-nobt"}),
    (PM_IN_B2C, RENTAL, {"hidden-pm"}),
]


@pytest.mark.parametrize("identity,vendor_bt,expected", _VIS_CASES,
                         ids=["b2b-prospect", "b2b-pm", "b2c-tenant", "pm-in-b2c-strict"])
async def test_visible_subset_equals_per_fine_canon_visible(identity, vendor_bt, expected):
    """薄包裝證明：`visible_subset` ≡ 逐細目 `canon_visible` 的集合。"""
    doc = _doc_v()
    index = FineIndex(_backend())
    got = index.visible_subset(identity, doc, vendor_business_types=vendor_bt)
    reference = frozenset(
        f.id for f in doc.fines() if canon_visible(identity, f, vendor_business_types=vendor_bt)
    )
    assert got == reference
    assert got == frozenset(fid(s) for s in expected), sorted(got)


async def test_pm_in_b2c_uses_the_strict_b2b_branch():
    """`target_user=property_manager` **即使 mode=b2c** 也走嚴格分支（⛔ 不是只看 mode）。

    鑑別列 `pm-rental`（業態 rental、角色 pm）在 b2c 分支下會可見（業者業態含 rental
    且角色相符）；嚴格分支要求業態含 `system_provider` ⇒ 必須不可見。
    """
    doc = _doc_v()
    index = FineIndex(_backend())
    strict = index.visible_subset(PM_IN_B2C, doc, vendor_business_types=RENTAL)
    assert fid("pm-rental") not in strict
    # 正對照：同一列對「真 b2c 角色 + 相符業態」的判準確實會放行（規則本身看得見它）
    assert canon_visible(
        Identity(vendor_id=1, target_user="tenant", mode="b2c"),
        [f for f in doc.fines() if f.id == fid("tenant-rental")][0],
        vendor_business_types=RENTAL,
    )
    assert strict, "嚴格分支下什麼都看不到 ⇒ 正對照失效，⛔ 不得當成『規則有生效』"


async def test_visible_subset_discriminates_between_identities():
    """量尺自證：四組身分不得撈到同一個集合，否則上面的等式毫無意義。"""
    doc = _doc_v()
    index = FineIndex(_backend())
    sets = [index.visible_subset(i, doc, vendor_business_types=bt) for i, bt, _e in _VIS_CASES]
    assert all(s for s in sets), "有身分看到空集合 ⇒ 鑑別力不足"
    assert len({frozenset(s) for s in sets}) >= 3, sets


async def test_unreviewed_fine_is_never_visible_in_memory():
    """未審細目 ⛔ 記憶體側一律不可見（SQL 側沒有審核謂詞——刻意的單向不對稱）。"""
    doc = _doc_v()
    index = FineIndex(_backend())
    for identity, bt, _e in _VIS_CASES:
        assert fid("nobody") not in index.visible_subset(identity, doc, vendor_business_types=bt)
    # 正對照：該列**確實存在**於正本、且只差在沒有 reviewed
    nobody = [f for f in doc.fines() if f.id == fid("nobody")][0]
    assert nobody.reviewed_by is None
    assert nobody.target_user == ("prospect",) and nobody.business_types == ("system_provider",)


async def test_visible_subset_does_not_depend_on_index_state():
    """可見子集與索引狀態無關（不查 DB、不打 embedding）——`absent` 也算得出來。"""
    doc = _doc_v()
    absent = FineIndex(_backend())
    ready = await _ready(doc, {QUERY: _Q})
    assert absent.state == "absent" and ready.state == "ready"
    assert absent.visible_subset(B2B_PROSPECT, doc, vendor_business_types=RENTAL) == \
        ready.visible_subset(B2B_PROSPECT, doc, vendor_business_types=RENTAL)


# ── 情境 6：隱私（§4.8）────────────────────────────────────────────────

async def test_no_query_title_or_phrasing_text_reaches_logs_or_stdout(caplog, capsys):
    """⚠️ 正對照組先跑：先證明 `caplog` 與 `capsys` **兩個擷取器都活著**。

    沒有這一步，「兩邊都乾淨」可能只是量尺壞了（既有 embedding client 走 `print`
    不走 `logging`，只看 `caplog` 會全綠地漏掉 stdout）。
    """
    caplog.set_level(logging.DEBUG)
    marker = "ZZCAPTUREPROBE"
    logging.getLogger("tests.candidate_selector.probe").warning(marker)
    print(marker)
    probe = capsys.readouterr()
    assert marker in caplog.text, "caplog 沒抓到標記 ⇒ 日誌擷取器壞了，下面的斷言不成立"
    assert marker in probe.out, "capsys 沒抓到標記 ⇒ stdout 擷取器壞了，下面的斷言不成立"

    doc = _doc_s()
    secrets = [QUERY] + [f.title for f in doc.fines()] + [
        p.text for f in doc.fines() for p in f.phrasings
    ]
    assert len(secrets) == 1 + 3 + 3

    ready = await _ready(doc, _DOC_S_VECTORS)
    # ① 正常路徑
    await CandidateSelector(ready).select(doc, B2B_PROSPECT, QUERY)
    # ② none_visible
    await CandidateSelector(ready).select(doc, B2C_TENANT, QUERY,
                                          vendor_business_types=frozenset())
    # ③ sha 不符
    await CandidateSelector(ready).select(_doc_w(), B2B_PROSPECT, QUERY)
    # ④ 索引 not_ready
    broken = FineIndex(_backend(raises=True))
    await broken.prepare(doc)
    await CandidateSelector(broken).select(doc, B2B_PROSPECT, QUERY)
    # ⑤ 查詢 embedding raise／形狀不合／逾時
    await CandidateSelector(ready, _backend(raises=True)).select(doc, B2B_PROSPECT, QUERY)
    await CandidateSelector(ready, _backend(returns=[None])).select(doc, B2B_PROSPECT, QUERY)
    await CandidateSelector(ready, _backend(_DOC_S_VECTORS, sleep_s=5), timeout_s=0.05).select(
        doc, B2B_PROSPECT, QUERY)

    captured = capsys.readouterr()
    haystack = caplog.text + captured.out + captured.err
    leaked = [s for s in secrets if s in haystack]
    assert not leaked, f"文字外洩到 log／stdout：{leaked}"
    assert "ph:" not in haystack


def test_module_source_has_no_print_statement():
    """⛔ 本模組不得有 `print`（隱私硬規則；`logging` 只准帶數量／狀態／型別名）。"""
    import ast
    import inspect

    from services.agent.canon import candidate_selector as CS

    tree = ast.parse(inspect.getsource(CS))
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"]
    assert not calls, "模組內出現 print()"
    # 正對照：這個掃描器抓得到 print（不是恆綠）
    assert [n for n in ast.walk(ast.parse("print(1)\n"))
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "print"]
