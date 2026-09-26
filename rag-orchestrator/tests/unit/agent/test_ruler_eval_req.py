"""unit：`tools/canon/ruler_eval.py` 的純函式（Plan 9.12 §6）。全部離線、⛔ 不打 embedding。

覆蓋：答案集合＝gold ∪ also_ok 時三層命中一致（跨粗目／跨架 also_ok）、層級斷言、
名次取答案集合最前者、答案不可見大聲失敗、重映只改 id 不改原 items、重映 sha 不符大聲失敗、
分組統計與組成表。
"""
from __future__ import annotations

import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
sys.path.insert(0, _RAG)

import tools.canon.ruler_eval as re_  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:9.12")]

COARSE = {
    "jgb/A/a1": "A-x", "jgb/A/a2": "A-y",
    "jgb/D/d1": "D-tax", "jgb/I/i1": "I-pay", "jgb/B/b1": "B-m",
}


def test_cross_shelf_also_ok_counts_at_every_layer():
    # gold 在 I 架、also_ok 在 D 架；前 5 名只有 D 架那條 ⇒ 細目／粗目／架全中
    order = ["jgb/D/d1", "jgb/B/b1", "jgb/A/a1", "jgb/A/a2", "jgb/I/i1"]
    row = re_.score_row(order, {"jgb/I/i1", "jgb/D/d1"}, COARSE, k=1)
    assert row == {"rank": 1, "hit": True, "hit10": True, "coarse_hit": True, "shelf_hit": True}


def test_primary_only_miss_is_miss_at_all_layers_when_no_overlap():
    order = ["jgb/B/b1", "jgb/A/a1", "jgb/I/i1"]
    row = re_.score_row(order, {"jgb/I/i1"}, COARSE, k=2)
    assert row["rank"] == 3 and not row["hit"] and not row["coarse_hit"] and not row["shelf_hit"]


def test_shelf_hit_without_coarse_hit():
    order = ["jgb/A/a2", "jgb/B/b1", "jgb/A/a1"]
    row = re_.score_row(order, {"jgb/A/a1"}, COARSE, k=2)
    assert not row["hit"] and not row["coarse_hit"] and row["shelf_hit"]


def test_hierarchy_violation_raises():
    # 粗目表與架不一致（B 架細目被標成 A 架的粗目）⇒ 粗目命中、架未命中 ⇒ 層級斷言必須炸
    bad_coarse = dict(COARSE, **{"jgb/B/b1": "A-x"})
    with pytest.raises(re_.RulerError, match="層級斷言"):
        re_.score_row(["jgb/B/b1", "jgb/A/a1"], {"jgb/A/a1"}, bad_coarse, k=1)


def test_answers_not_visible_fail_loud():
    with pytest.raises(re_.RulerError, match="不在可見排序"):
        re_.score_row(["jgb/A/a1"], {"jgb/A/a2"}, COARSE, k=5)
    with pytest.raises(re_.RulerError, match="答案集合為空"):
        re_.score_row(["jgb/A/a1"], set(), COARSE, k=5)


def test_apply_remap_does_not_mutate_and_checks_sha():
    items = [{"id": "r:0", "fine_id": "jgb/A/old", "also_ok": ["jgb/A/old2", "jgb/B/keep"]}]
    remap = {"from_canon_sha": "s0", "to_canon_sha": "s1", "map": {"jgb/A/old": "jgb/A/new", "jgb/A/old2": "jgb/A/new2"}}
    out = re_.apply_remap(items, remap, "s1")
    assert out[0]["fine_id"] == "jgb/A/new" and out[0]["also_ok"] == ["jgb/A/new2", "jgb/B/keep"]
    assert items[0]["fine_id"] == "jgb/A/old"  # 原 items 不動
    with pytest.raises(re_.RulerError, match="to_canon_sha"):
        re_.apply_remap(items, remap, "other")


def test_summarize_and_composition():
    rows = [
        {"hit": True, "hit10": True, "coarse_hit": True, "shelf_hit": True, "leak": "none", "type": "直接", "shelf": "A"},
        {"hit": False, "hit10": True, "coarse_hit": False, "shelf_hit": True, "leak": "mild", "type": "口語", "shelf": "A"},
    ]
    s = {x["value"]: x for x in re_.summarize(rows, "leak")}
    assert s["none"]["n"] == 1 and s["none"]["hit"] == 1.0 and s["mild"]["hit"] == 0.0
    comp = re_.composition(rows)
    assert comp["leak_x_type"] == {"mild|口語": 1, "none|直接": 1}
    assert comp["leak_x_shelf"] == {"mild|A": 1, "none|A": 1}


def test_join_text_verifies_hash_and_fails_loud():
    hn = lambda q: "h:" + q.rstrip("？?")
    items = [{"id": "a", "q_sha256": "h:帳單怎麼開"}, {"id": "b", "q_sha256": "h:合約"}]
    out = re_.join_text(items, [{"id": "a", "q": "帳單怎麼開？"}, {"id": "b", "q": "合約"}], hn)
    assert [o["q"] for o in out] == ["帳單怎麼開？", "合約"] and "q" not in items[0]
    with pytest.raises(re_.RulerError, match="缺題"):
        re_.join_text(items, [{"id": "a", "q": "帳單怎麼開"}], hn)
    with pytest.raises(re_.RulerError, match="hash 不符"):
        re_.join_text(items, [{"id": "a", "q": "別的"}, {"id": "b", "q": "合約"}], hn)


def test_load_hash_norm_is_the_checker_symbol():
    hn = re_.load_hash_norm()
    assert hn.__module__ == "canon_phrasing_frozen_disjoint"
    assert hn("合約可以續約嗎？") == hn("合約 可以續約嗎")
