"""unit：C2-I3 top20 selector ordering guards（業主凍結 2026-08-30）。

```text
裁定  best_keyword_source_rank = earliest contributing keyword row
      **in the keyword selector's own returned ordering**
      ⛔ NOT global concatenated results ordinal

G11 selector-order authority     global ordinal ≠ selector rank 時，順序必須跟 selector rank
G12 mixed-source 不重排 keyword bucket   vector .99 ⛔ 不得讓 keyword rank=2 超車 rank=1
G13 multi-alias earliest surface  ranks{3,9,14} → rank=3、恰好一格；刪掉 9/14 位置不變
G14 tie-break                    同 rank（multi-membership）→ responsibility_id ASC，
                                 **deterministic only，zero semantic meaning**
M7  rank 改用 global results ordinal → G11 必紅
faillow keyword row 未帶 rank → raise，⛔ 不得靜默退回 global ordinal
```
"""
import json
import os

import pytest

from services import responsibility_collapse as rc

pytestmark = pytest.mark.unit

SPEC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", "..", ".kiro", "specs",
                                    "conversational-routing-execution", "r10p",
                                    "registry-v2.json"))


@pytest.fixture(scope="module")
def mapping():
    with open(SPEC, encoding="utf-8") as f:
        return rc.load_mapping_from_registry(json.load(f))


def _k(rid, rank):
    return {"id": rid, "vector_similarity": 0.0, "search_method": rc.KEYWORD_METHOD,
            rc.KEYWORD_RANK_FIELD: rank}


def _v(rid, score):
    return {"id": rid, "vector_similarity": score, "search_method": "vector"}


# ───────────────────── G11：selector order 才是 authority ─────────────────────
@pytest.mark.req("C2_G11:1")
def test_g11_follows_selector_rank_not_global_ordinal(mapping):
    """刻意讓 global ordinal 與 selector rank **相反**。"""
    rows = [_v(3402, 0.95),          # global ordinal 0（vector，先被串進 results）
            _k(3939, 5),             # global ordinal 1，但 selector rank = 5
            _k(3495, 2)]             # global ordinal 2，但 selector rank = 2
    out = rc.select_nominated(rows, mapping, limit=20)
    kw = [c["responsibility_id"] for c in out if c["has_keyword_nomination"]]
    assert kw == [mapping[3495][0], "R-28"], \
        "keyword bucket 未依 selector rank 排 ⇒ 用到了容器組裝順序"


@pytest.mark.req("C2_G11:2")
def test_m7_global_ordinal_rank_makes_g11_red(mapping, monkeypatch):
    """M7：把 rank 換成 global results ordinal。"""
    orig = rc.collapse

    def mutated(rows, mapping_, vector_floor=rc.DEFAULT_VECTOR_FLOOR,
                allow_row_id_fallback=False):
        rows = [dict(r) for r in rows]
        for ordinal, r in enumerate(rows):          # ⛔ 容器組裝順序當 rank
            if r.get("search_method") == rc.KEYWORD_METHOD:
                r[rc.KEYWORD_RANK_FIELD] = ordinal
        return orig(rows, mapping_, vector_floor, allow_row_id_fallback)

    monkeypatch.setattr(rc, "collapse", mutated)
    rows = [_v(3402, 0.95), _k(3939, 5), _k(3495, 2)]
    out = rc.select_nominated(rows, mapping, limit=20)
    kw = [c["responsibility_id"] for c in out if c["has_keyword_nomination"]]
    assert kw == ["R-28", mapping[3495][0]], "M7 未讓 G11 變紅 ⇒ guard 是裝飾"


# ───────────────────── G12：vector ⛔ 不重排 keyword bucket ─────────────────────
@pytest.mark.req("C2_G12:1")
def test_g12_vector_score_does_not_reorder_keyword_bucket(mapping):
    rows = [_k(3939, 1), _v(3940, 0.31),      # R-28：keyword rank=1，vector 很低
            _k(3495, 2), _v(3495, 0.99)]      # R-10：keyword rank=2，vector 很高
    out = [c["responsibility_id"] for c in rc.select_nominated(rows, mapping, limit=20)]
    assert out[:2] == ["R-28", mapping[3495][0]], \
        ".99 讓 keyword rank=2 超車 ⇒ vector 證據偷偷影響了 keyword policy"


# ───────────────────── G13：multi-alias 取最早，且無 alias-count 效應 ─────────────
@pytest.mark.req("C2_G13:1")
def test_g13_earliest_keyword_surface_and_no_alias_count_effect(mapping):
    many = [_k(3939, 3), _k(3940, 9), _k(3939, 14), _k(3402, 4)]
    out_many = rc.select_nominated(many, mapping, limit=20)
    c = next(x for x in out_many if x["responsibility_id"] == "R-28")
    assert c["best_keyword_source_rank"] == 3
    assert sum(1 for x in out_many if x["responsibility_id"] == "R-28") == 1

    few = [_k(3939, 3), _k(3402, 4)]
    out_few = rc.select_nominated(few, mapping, limit=20)
    assert [x["responsibility_id"] for x in out_many] == [x["responsibility_id"] for x in out_few], \
        "刪掉較晚的 alias 改變了順序 ⇒ 出現 alias-count 效應"


# ───────────────────── G14：tie-break 是決定性的、無語義 ─────────────────────
@pytest.mark.req("C2_G14:1")
def test_g14_multi_membership_tie_break_is_deterministic(mapping):
    """一個 keyword row → 四個 responsibility，rank 完全相同。"""
    out = rc.select_nominated([_k(3511, 7)], mapping, limit=20)
    ids = [c["responsibility_id"] for c in out]
    assert ids == sorted(ids), "同 rank 未以 responsibility_id ASC 打破平手 ⇒ 順序不可重現"
    assert len(ids) == 4
    assert all(c["best_keyword_source_rank"] == 7 for c in out)


# ───────────────────── fail-loud ─────────────────────
@pytest.mark.req("C2_G11:3")
def test_keyword_row_without_rank_raises(mapping):
    bad = {"id": 3939, "vector_similarity": 0.0, "search_method": rc.KEYWORD_METHOD}
    with pytest.raises(rc.KeywordRankMissing, match="不得靜默改用 global results ordinal"):
        rc.select_nominated([bad], mapping)


@pytest.mark.req("C2_G11:4")
def test_annotate_helper_stamps_selector_local_rank():
    rows = [{"id": 3939}, {"id": 3940}, {"id": 3495}]
    out = rc.annotate_keyword_source_rank(rows)
    assert [r[rc.KEYWORD_RANK_FIELD] for r in out] == [0, 1, 2]
