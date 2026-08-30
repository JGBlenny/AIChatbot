"""unit：C2-I1 responsibility mapping／collapse guards（業主凍結 2026-08-30）。

```text
G1 alias collapse      3939＋3940 同時 recall → 只能有 R-28 一筆
G2 no voting weight    同責任第二個 alias hit → ⛔ 不增加 candidate 數、⛔ 不直接增加分數
G3 slot recovery       同責任多 alias 原佔 2 個 slots → collapse 後只佔 1，第 21 名應有機會進榜
G4 multi-membership    3511 → 恰好 4 個既有責任，⛔ 不產生 responsibility_3511
G5 historical          3498 → ⛔ 不形成 active candidate
G6 unresolved          3512／3513／4255 → ⛔ 不自動生成 candidate
G8 keyword exemption   只有 keyword_fallback contributor、vector=0 → 仍 admissible
G9 mixed-source        keyword ＋ vector 同責任 → 恰好 1 個 candidate、keyword_priority=true
M1 collapse 移到截斷之後            → G3 必紅
M2 改用 SUM(alias scores)          → G2 必紅
M3 row id 自動 fallback 成 resp id  → G6 必紅
```
⚠️ guard exists ≠ guard can fail：M1–M3 是**可執行**的 mutation，⛔ 不是註解。
"""
import json
import os

import pytest

from services import responsibility_collapse as rc

pytestmark = pytest.mark.unit

SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "..", "..", "..", ".kiro", "specs",
                    "conversational-routing-execution", "r10p", "registry-v2.json")


@pytest.fixture(scope="module")
def mapping():
    """⚠️ 用**真的 sealed Registry V2** 導出 mapping，⛔ 不手捏 fixture。"""
    with open(os.path.abspath(SPEC), encoding="utf-8") as f:
        return rc.load_mapping_from_registry(json.load(f))


def _vrow(rid, score, boost=1.0):
    return {"id": rid, "vector_similarity": score, "keyword_boost": boost,
            "search_method": "vector"}


def _krow(rid, rank=0):
    # keyword_fallback 的 vector_similarity=0 是**設計預設值**，⛔ 不代表低相關。
    # ⚠️ rank ＝ **keyword selector 自己回傳順序**中的位置（C2-I3），⛔ 非 global ordinal。
    return {"id": rid, "vector_similarity": 0.0, "search_method": rc.KEYWORD_METHOD,
            rc.KEYWORD_RANK_FIELD: rank}


# ───────────────────────── G1：alias collapse ─────────────────────────
@pytest.mark.req("C2_G1:1")
def test_g1_late_fee_aliases_collapse_to_one(mapping):
    out = rc.select_nominated([_vrow(3939, 0.81), _vrow(3940, 0.77)], mapping)
    assert [c["responsibility_id"] for c in out] == ["R-28"]
    assert sorted(out[0]["contributing_row_ids"]) == [3939, 3940]


# ───────────────────────── G2：no voting weight ────────────────────────
@pytest.mark.req("C2_G2:1")
def test_g2_second_alias_adds_no_candidate_and_no_score(mapping):
    one = rc.select_nominated([_vrow(3939, 0.81)], mapping)
    two = rc.select_nominated([_vrow(3939, 0.81), _vrow(3940, 0.77)], mapping)
    assert len(one) == len(two) == 1
    # ⚠️ 第二個較低分的 alias ⛔ 不得把 nomination 分數推高（MAX 而非 SUM）
    assert two[0]["best_vector_nomination_score"] == pytest.approx(
        one[0]["best_vector_nomination_score"])


@pytest.mark.req("C2_G2:2")
def test_m2_sum_aggregator_makes_g2_red(mapping, monkeypatch):
    monkeypatch.setattr(rc, "NOMINATION_AGGREGATOR", sum)
    one = rc.select_nominated([_vrow(3939, 0.81)], mapping)
    two = rc.select_nominated([_vrow(3939, 0.81), _vrow(3940, 0.77)], mapping)
    assert two[0]["best_vector_nomination_score"] > one[0]["best_vector_nomination_score"], \
        "M2 mutation 未讓 G2 變紅 ⇒ guard 是裝飾"


# ───────────────────────── G3：slot recovery ──────────────────────────
def _slot_scenario(mapping):
    """20 個 slot：3939/3940 是同一責任的兩個 alias，另有 19 個不同責任的 vector row。"""
    others = [3402, 3406, 3495, 3496, 3499, 3519, 4640, 4656, 4657,
              3497, 3500, 3501, 3502, 3503, 3504, 3505, 3506, 3508, 3514]
    rows = [_vrow(3939, 0.95), _vrow(3940, 0.94)]
    rows += [_vrow(rid, 0.90 - i * 0.01) for i, rid in enumerate(others)]
    return rows


@pytest.mark.req("C2_G3:1")
def test_g3_collapse_recovers_a_slot(mapping):
    rows = _slot_scenario(mapping)
    out = rc.select_nominated(rows, mapping, limit=20)
    ids = [c["responsibility_id"] for c in out]
    assert len(ids) == len(set(ids)) == 20
    # collapse 讓 3939/3940 只佔 1 格 ⇒ 原本第 21 名（最後一個 others）也進得來
    last_resp = mapping[3514][0]
    assert last_resp in ids, "slot 未回收 ⇒ C2 要解的 production defect 沒被驗到"


@pytest.mark.req("C2_G3:2")
def test_m1_collapse_after_truncation_makes_g3_red(mapping):
    rows = _slot_scenario(mapping)
    out = rc.select_nominated(rows, mapping, limit=20, collapse_first=False)
    ids = [c["responsibility_id"] for c in out]
    assert mapping[3514][0] not in ids, "M1 mutation 未讓 G3 變紅 ⇒ guard 是裝飾"


# ───────────────────────── G4：multi-membership ───────────────────────
@pytest.mark.req("C2_G4:1")
def test_g4_row_3511_nominates_exactly_four(mapping):
    out = rc.select_nominated([_vrow(3511, 0.72)], mapping)
    ids = sorted(c["responsibility_id"] for c in out)
    assert ids == sorted(mapping[3511]) and len(ids) == 4
    assert all(not i.startswith("row_") for i in ids), "⛔ 不得產生 responsibility_3511"
    for c in out:
        assert c["contributing_row_ids"] == [3511]


# ───────────────────────── G5／G6：不得製造 authority ──────────────────
@pytest.mark.req("C2_G5:1")
def test_g5_historical_row_makes_no_candidate(mapping):
    assert 3498 not in mapping
    assert rc.select_nominated([_vrow(3498, 0.99)], mapping) == []


@pytest.mark.req("C2_G6:1")
@pytest.mark.parametrize("row_id", [3512, 3513, 4255, 3361, 3931])
def test_g6_unresolved_rows_make_no_candidate(mapping, row_id):
    assert row_id not in mapping
    assert rc.select_nominated([_vrow(row_id, 0.99)], mapping) == []


@pytest.mark.req("C2_G6:2")
def test_m3_row_id_fallback_makes_g6_red(mapping):
    out = rc.select_nominated([_vrow(3512, 0.99)], mapping, allow_row_id_fallback=True)
    assert out and out[0]["responsibility_id"] == "row_3512", \
        "M3 mutation 未讓 G6 變紅 ⇒ guard 是裝飾"


# ───────────────────────── G8：keyword 豁免 ───────────────────────────
@pytest.mark.req("C2_G8:1")
def test_g8_keyword_only_survives_threshold(mapping):
    out = rc.select_nominated([_krow(3939)], mapping)
    assert [c["responsibility_id"] for c in out] == ["R-28"]
    c = out[0]
    assert c["has_keyword_nomination"] and c["best_vector_nomination_score"] == 0.0
    assert rc.is_nomination_admissible(c), "keyword 路徑必須豁免 .3 下限"


@pytest.mark.req("C2_G8:2")
def test_vector_only_below_floor_is_rejected(mapping):
    """正對照：同一條路徑對 vector-only 仍然會擋，⛔ 不是無條件放行。"""
    assert rc.select_nominated([_vrow(3939, 0.29)], mapping) == []


# ───────────────────────── G9：mixed-source ──────────────────────────
@pytest.mark.req("C2_G9:1")
def test_g9_mixed_source_is_one_candidate(mapping):
    out = rc.select_nominated([_krow(3939), _vrow(3940, 0.82)], mapping)
    assert len(out) == 1
    c = out[0]
    assert c["responsibility_id"] == "R-28"
    assert c["has_keyword_nomination"] is True
    assert c["best_vector_nomination_score"] == pytest.approx(0.82)
    assert len(c["contributing_row_ids"]) == 2, "⛔ 不得因兩個 entry surface 變兩票"


@pytest.mark.req("C2_G9:2")
def test_keyword_priority_orders_before_vector_only(mapping):
    out = rc.select_nominated([_vrow(3402, 0.99), _krow(3939)], mapping, limit=2)
    assert [c["responsibility_id"] for c in out][0] == "R-28", \
        "keyword-priority responsibility 必須排在 vector-only 之前"
