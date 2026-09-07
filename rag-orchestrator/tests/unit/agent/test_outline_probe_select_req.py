"""unit：`tools/canon/outline_probe_select.py`（spec knowledge-outline-and-intent-architecture・
任務 4.4；Plan `inputs/plan-4.4a-outline-probe-definition-20260907.md` §2）。

全部離線、無網路——422 重生／md5 排序皆為本機決定性計算，⛔ 不打 embedding。
覆蓋：七層母體的機械可重算定義、md5 排序＋不足記 `insufficient`、id 前綴、
fail-loud（缺檔／母體空／sub 不在 sub-map／G 層 422 三項全等不符）、正對照
（合成材料重現期望取值；改一個 q 會變 md5 排序）、D 層「各類先取最小者」演算法、
F 層多輪 item 組裝與缺 gold 表 fail loud。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from types import SimpleNamespace

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))  # tests/unit/agent → rag-orchestrator
_TOOLS_CANON = os.path.join(_RAG, "tools", "canon")

sys.path.insert(0, _RAG)
if _TOOLS_CANON not in sys.path:
    sys.path.insert(0, _TOOLS_CANON)

import tools.canon.index_eval as ie  # noqa: E402
import tools.canon.outline_probe_select as ops  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:4.4")]

SEED = "test-seed-20260907:"


# ---------------------------------------------------------------------------
# 共用小夾具
# ---------------------------------------------------------------------------

def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def _write_topics(tmp_path, phrasings=None, boundary=None):
    phrasings = phrasings if phrasings is not None else [
        {"q": "A候選甲", "sub": "subA", "type": "直接", "src": "t"},
        {"q": "C候選甲", "sub": "subA", "type": "直接", "src": "t"},
        {"q": "中間候選甲", "sub": "subB", "type": "直接", "src": "t"},
    ]
    boundary = boundary if boundary is not None else [
        {"q": "邊界甲", "sub": "subA", "type": "邊界", "src": "t"},
        {"q": "邊界乙", "sub": "subA", "type": "邊界", "src": "t"},
    ]
    doc = {"_meta": {}, "topics": [{"id": "T1", "phrasings": phrasings, "boundary": boundary}]}
    path = str(tmp_path / "topics-v2.json")
    _write(path, doc)
    return path


def _write_round9(tmp_path, answered_by_idx: dict):
    """`answered_by_idx`：`{idx: n_answered}`，每個 idx 固定 6 rep（r9a 3＋r9b 3）。"""
    round9_dir = tmp_path / "round9"
    for sub, reps in (("r9a", 3), ("r9b", 3)):
        lines = []
        # 每個 idx 在 r9a／r9b 各 3 rep；r9a 取前 min(3,n) 個 rep 為 answered，
        # r9b 補剩下的，跨兩檔湊出總 n_answered/6（reps 參數目前恆為 3，留著只為可讀性）。
        assert reps == 3
        for idx, n_answered in answered_by_idx.items():
            if sub == "r9a":
                n_here = min(3, n_answered)
            else:
                n_here = max(0, n_answered - 3)
            for rep in range(3):
                lines.append(json.dumps({
                    "set": "topics", "idx": idx, "turn": 0, "chain": "agent", "rep": rep,
                    "answered": rep < n_here,
                }, ensure_ascii=False))
        path = round9_dir / sub / "topics.jsonl"
        os.makedirs(path.parent, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(round9_dir)


def _write_sub_map(tmp_path, mapping):
    path = str(tmp_path / "sub-map.json")
    _write(path, mapping)
    return path


def _write_map_v2_and_canon(tmp_path, cells):
    """`cells`：`[{"id","questions","label"}]`。"""
    map_v2_path = str(tmp_path / "map-v2.json")
    _write(map_v2_path, {"_meta": {}, "cells": [{"id": c["id"], "questions": c["questions"]} for c in cells]})
    canon_path = str(tmp_path / "canon-v3.json")
    _write(canon_path, {"payload": {"labels": [
        {"cell_id": c["id"], "label": c["label"], "fine_id": "prospect/X/dummy"} for c in cells
    ]}})
    return map_v2_path, canon_path


def _write_sensitive(tmp_path, items):
    path = str(tmp_path / "sensitive-v1.json")
    _write(path, {"items": items})
    return path


def _write_scenarios(tmp_path, scenarios):
    path = str(tmp_path / "scenarios-v1.json")
    _write(path, {"scenarios": scenarios})
    return path


def _write_scenario_gold(tmp_path, gold):
    path = str(tmp_path / "scenario-gold.json")
    _write(path, gold)
    return path


def _write_koyu(tmp_path, articles):
    path = str(tmp_path / "koyu.json")
    _write(path, {"articles": articles})
    return path


def _write_article_map(tmp_path, articles):
    path = str(tmp_path / "article-map.json")
    _write(path, {"articles": articles})
    return path


def _rank_key(seed, q):
    return (hashlib.md5((seed + q).encode("utf-8")).hexdigest(), q)


# ---------------------------------------------------------------------------
# A／C：round9 答到次數 → 母體圈選＋sub 檢核
# ---------------------------------------------------------------------------

def test_population_a_is_zero_of_six_and_requires_sub_in_map(tmp_path):
    topics_path = _write_topics(tmp_path)
    round9_dir = _write_round9(tmp_path, {
        "T1:phrasing:0": 0,  # A 候選（0/6）
        "T1:phrasing:1": 5,  # C 候選（≥4/6）
        "T1:phrasing:2": 2,  # 兩者都不算
    })
    topics_index = ops.load_topics_index(topics_path)
    round9_counts = ops.load_round9_answered_counts(round9_dir)

    sub_map = {"subA": ["prospect/A/one"], "subB": ["prospect/B/two"]}
    pop_a = ops.population_a(topics_index, round9_counts, sub_map)
    assert [c["q"] for c in pop_a] == ["A候選甲"]
    assert pop_a[0]["gold"] == ["prospect/A/one"]
    assert pop_a[0]["expect_kind"] == "answer"

    pop_c = ops.population_c(topics_index, round9_counts, sub_map)
    assert [c["q"] for c in pop_c] == ["C候選甲"]


def test_population_a_fails_loud_when_sub_missing_from_map(tmp_path):
    topics_path = _write_topics(tmp_path)
    round9_dir = _write_round9(tmp_path, {"T1:phrasing:0": 0, "T1:phrasing:1": 5, "T1:phrasing:2": 2})
    topics_index = ops.load_topics_index(topics_path)
    round9_counts = ops.load_round9_answered_counts(round9_dir)

    sub_map_missing_subA = {"subB": ["prospect/B/two"]}  # subA 缺席
    with pytest.raises(SystemExit) as exc:
        ops.population_a(topics_index, round9_counts, sub_map_missing_subA)
    assert exc.value.code == ops.EXIT_FAIL


# ---------------------------------------------------------------------------
# B：map-v2 deliberate_no／no_source（questions[0]）＋ insufficient 記錄
# ---------------------------------------------------------------------------

def test_population_b_only_deliberate_labels_and_first_question(tmp_path):
    map_v2_path, canon_path = _write_map_v2_and_canon(tmp_path, [
        {"id": "C01", "questions": ["問句一", "問句二"], "label": "deliberate_no"},
        {"id": "C02", "questions": ["問句三"], "label": "no_source"},
        {"id": "C03", "questions": ["問句四"], "label": "answerable"},
    ])
    pop_b = ops.population_b(map_v2_path, canon_path)
    qs = sorted(c["q"] for c in pop_b)
    assert qs == ["問句一", "問句三"]  # C03（answerable）不入；C01 取 questions[0]
    assert all(c["expect_kind"] == "handoff" and c["gold"] == [] for c in pop_b)


def test_select_ordered_marks_insufficient_when_population_below_take_n():
    candidates = [{"q": "只有一句", "gold": [], "expect_kind": "handoff"}]
    picked, insufficient = ops.select_ordered(candidates, SEED, take_n=5)
    assert insufficient is True
    assert len(picked) == 1


# ---------------------------------------------------------------------------
# md5 排序：決定性＋改一個 q 會變序（正對照：排序真的依內容而非插入序）
# ---------------------------------------------------------------------------

def test_md5_ordering_is_deterministic_and_sensitive_to_q_change():
    candidates = [
        {"q": "甲句", "gold": [], "expect_kind": "answer"},
        {"q": "乙句", "gold": [], "expect_kind": "answer"},
        {"q": "丙句", "gold": [], "expect_kind": "answer"},
    ]
    picked1, _ = ops.select_ordered(candidates, SEED, take_n=3)
    picked2, _ = ops.select_ordered(list(reversed(candidates)), SEED, take_n=3)
    assert [c["q"] for c in picked1] == [c["q"] for c in picked2]  # 決定性：與輸入順序無關

    expected_order = sorted([c["q"] for c in candidates], key=lambda q: _rank_key(SEED, q))
    assert [c["q"] for c in picked1] == expected_order

    # 改一句的文字 ⇒ 該句的 md5 鍵改變，排序可能改變（用真的改變過的鍵驗證非巧合）
    mutated = [dict(c) for c in candidates]
    mutated[0]["q"] = "甲句改過了"
    picked_mutated, _ = ops.select_ordered(mutated, SEED, take_n=3)
    original_keys = [_rank_key(SEED, c["q"]) for c in candidates]
    mutated_keys = [_rank_key(SEED, c["q"]) for c in mutated]
    assert original_keys != mutated_keys
    assert _rank_key(SEED, "甲句") != _rank_key(SEED, "甲句改過了")


def test_positive_control_exact_expected_picks():
    """合成材料重現期望取值：手算 md5 排序，斷言選出的就是那幾句、順序也對。"""
    candidates = [{"q": f"句子{i}", "gold": [], "expect_kind": "answer"} for i in range(6)]
    picked, insufficient = ops.select_ordered(candidates, SEED, take_n=3)
    assert insufficient is False
    expected = sorted(candidates, key=lambda c: _rank_key(SEED, c["q"]))[:3]
    assert [c["q"] for c in picked] == [c["q"] for c in expected]


# ---------------------------------------------------------------------------
# D：五類各取 md5 最小者，再依全域 md5 補到 take_n
# ---------------------------------------------------------------------------

def test_select_sensitive_takes_min_per_class_first():
    candidates = [
        {"q": "cls1-a", "fact_class": "cls1"}, {"q": "cls1-b", "fact_class": "cls1"},
        {"q": "cls2-a", "fact_class": "cls2"}, {"q": "cls2-b", "fact_class": "cls2"},
    ]
    picked, insufficient = ops.select_sensitive(candidates, SEED, take_n=2)
    assert insufficient is False
    assert len(picked) == 2
    picked_classes = {c["fact_class"] for c in picked}
    assert picked_classes == {"cls1", "cls2"}  # 兩類都要有代表（take_n==類數 ⇒ 剛好各取最小者）
    # 各類取到的確實是該類 md5 最小者
    for cls in ("cls1", "cls2"):
        pool = [c for c in candidates if c["fact_class"] == cls]
        best = min(pool, key=lambda c: _rank_key(SEED, c["q"]))
        assert any(c["q"] == best["q"] for c in picked)


def test_select_sensitive_fills_beyond_class_count_by_global_md5():
    candidates = [
        {"q": "cls1-a", "fact_class": "cls1"}, {"q": "cls1-b", "fact_class": "cls1"},
        {"q": "cls2-a", "fact_class": "cls2"},
    ]
    picked, insufficient = ops.select_sensitive(candidates, SEED, take_n=3)
    assert insufficient is False
    assert len(picked) == 3  # 3 句全取（母體剛好等於 take_n）
    assert {c["q"] for c in picked} == {"cls1-a", "cls1-b", "cls2-a"}


# ---------------------------------------------------------------------------
# E：只取 topics boundary（不含 koyu 邊界型可答句）
# ---------------------------------------------------------------------------

def test_population_e_is_topics_boundary_only(tmp_path):
    topics_path = _write_topics(tmp_path)
    pop_e = ops.population_e(topics_path)
    assert sorted(c["q"] for c in pop_e) == ["邊界乙", "邊界甲"]
    assert all(c["expect_kind"] == "handoff" and c["gold"] == [] for c in pop_e)


# ---------------------------------------------------------------------------
# F：凍結劇本集合缺一即 fail loud；turn<3 也 fail loud；多輪 item 組裝
# ---------------------------------------------------------------------------

def _scenario(sid, n_turns):
    return {"id": sid, "turns": [{"turn": t + 1, "q": f"{sid}-turn{t + 1}"} for t in range(n_turns)]}


def test_population_f_requires_all_frozen_scenarios_present(tmp_path):
    scenarios_path = _write_scenarios(tmp_path, [
        _scenario("S1-landlord", 3), _scenario("S2-agency", 3),  # 缺 D-import
    ])
    with pytest.raises(SystemExit) as exc:
        ops.population_f(scenarios_path)
    assert exc.value.code == ops.EXIT_FAIL


def test_population_f_requires_at_least_three_turns(tmp_path):
    scenarios_path = _write_scenarios(tmp_path, [
        _scenario("S1-landlord", 2),  # 只 2 turn
        _scenario("S2-agency", 3), _scenario("D-import", 3),
    ])
    with pytest.raises(SystemExit):
        ops.population_f(scenarios_path)


def test_population_f_ok_and_scenario_item_assembly(tmp_path):
    scenarios_path = _write_scenarios(tmp_path, [
        _scenario("S1-landlord", 3), _scenario("S2-agency", 3), _scenario("D-import", 3),
    ])
    pop_f = ops.population_f(scenarios_path)
    assert {c["scenario_id"] for c in pop_f} == {"S1-landlord", "S2-agency", "D-import"}

    picked_f, insufficient = ops.select_scenarios(pop_f, SEED, take_n=3)
    assert insufficient is False
    assert len(picked_f) == 3

    scenario_gold = {
        sid: [{"turn": t + 1, "gold": [f"{sid}-g{t}"], "expect_kind": "answer"} for t in range(3)]
        for sid in ("S1-landlord", "S2-agency", "D-import")
    }
    items = ops.build_scenario_items(picked_f, scenario_gold)
    assert len(items) == 3
    for item in items:
        assert item["id"] == f"F-{item['turns'][0]['q'].rsplit('-turn', 1)[0]}"
        assert item["stratum"] == "multi"
        assert len(item["turns"]) == 3
        assert all("gold" in t and "expect_kind" in t for t in item["turns"])


def test_build_scenario_items_fails_loud_on_missing_gold_entry(tmp_path):
    scenarios_path = _write_scenarios(tmp_path, [
        _scenario("S1-landlord", 3), _scenario("S2-agency", 3), _scenario("D-import", 3),
    ])
    pop_f = ops.population_f(scenarios_path)
    picked_f, _ = ops.select_scenarios(pop_f, SEED, take_n=3)
    # scenario-gold 完全缺 S2-agency
    scenario_gold = {
        "S1-landlord": [{"turn": t + 1, "gold": [], "expect_kind": "answer"} for t in range(3)],
        "D-import": [{"turn": t + 1, "gold": [], "expect_kind": "answer"} for t in range(3)],
    }
    with pytest.raises(SystemExit) as exc:
        ops.build_scenario_items(picked_f, scenario_gold)
    assert exc.value.code == ops.EXIT_FAIL


# ---------------------------------------------------------------------------
# G：422 重生 + 跨粗目篩選 + 三項全等 fail loud
# ---------------------------------------------------------------------------

def _g_koyu_doc():
    return {
        "Landlordonboarding00": {"title": "t", "phrasings": [
            {"n": 1, "type": "直接", "q": "跨粗目甲"},
            {"n": 2, "type": "口語", "q": "跨粗目乙"},
        ]},
        "other-article": {"title": "t2", "phrasings": [
            {"n": 1, "type": "直接", "q": "非跨粗目甲"},
        ]},
    }


def test_population_g_filters_cross_coarse_articles_and_gold(tmp_path):
    koyu_path = _write_koyu(tmp_path, _g_koyu_doc())
    topics_path = _write_topics(tmp_path, phrasings=[], boundary=[])  # 無凍結重疊
    article_map_path = _write_article_map(tmp_path, {
        "Landlordonboarding00": {"file_exists": True, "fine_ids": ["prospect/A/one", "prospect/B/two"]},
        "other-article": {"file_exists": True, "fine_ids": ["prospect/Z/three"]},
    })
    pop_g = ops.population_g(koyu_path, topics_path, article_map_path, rule_path=None)
    assert {c["q"] for c in pop_g} == {"跨粗目甲", "跨粗目乙"}
    for c in pop_g:
        assert sorted(c["gold"]) == ["prospect/A/one", "prospect/B/two"]
        assert c["expect_kind"] == "answer"


def test_population_g_empty_population_fails_loud_downstream(tmp_path):
    koyu_path = _write_koyu(tmp_path, {"unrelated-article": {"title": "t", "phrasings": [
        {"n": 1, "type": "直接", "q": "不相干甲"},
    ]}})
    topics_path = _write_topics(tmp_path, phrasings=[], boundary=[])
    article_map_path = _write_article_map(tmp_path, {"unrelated-article": {"file_exists": True, "fine_ids": []}})
    pop_g = ops.population_g(koyu_path, topics_path, article_map_path, rule_path=None)
    assert pop_g == []  # 母體為空——`run()` 層會對此 fail loud（見下方整合測試）


def test_population_g_freeze_mismatch_fails_loud(tmp_path):
    koyu_path = _write_koyu(tmp_path, _g_koyu_doc())
    topics_path = _write_topics(tmp_path, phrasings=[], boundary=[])
    article_map_path = _write_article_map(tmp_path, {
        "Landlordonboarding00": {"file_exists": True, "fine_ids": ["prospect/A/one"]},
    })
    bad_rule_path = str(tmp_path / "bad-rule.json")
    _write(bad_rule_path, {"n": 99999, "by_type": {}, "excluded_frozen": 0})
    with pytest.raises(SystemExit) as exc:
        ops.population_g(koyu_path, topics_path, article_map_path, rule_path=bad_rule_path)
    assert exc.value.code == ops.EXIT_FAIL


# ---------------------------------------------------------------------------
# 整合：`run()` 全跑（合成材料）＋ `--dry-run` 不寫檔 ＋ id 前綴 ＋ fail-loud 母體空
# ---------------------------------------------------------------------------

def _full_materials(tmp_path):
    topics_path = _write_topics(tmp_path)
    round9_dir = _write_round9(tmp_path, {"T1:phrasing:0": 0, "T1:phrasing:1": 5, "T1:phrasing:2": 2})
    sub_map_path = _write_sub_map(tmp_path, {"subA": ["prospect/A/one"], "subB": ["prospect/B/two"]})
    map_v2_path, canon_path = _write_map_v2_and_canon(tmp_path, [
        {"id": "C01", "questions": ["B候選一"], "label": "deliberate_no"},
        {"id": "C02", "questions": ["B候選二"], "label": "no_source"},
    ])
    sensitive_items = []
    for cls_i, cls in enumerate(("cls1", "cls2", "cls3", "cls4", "cls5")):
        for j in range(2):
            sensitive_items.append({"id": f"{cls}-{j}", "q": f"{cls}敏感句{j}", "fact_class": cls})
    sensitive_path = _write_sensitive(tmp_path, sensitive_items)
    scenarios_path = _write_scenarios(tmp_path, [
        _scenario("S1-landlord", 3), _scenario("S2-agency", 3), _scenario("D-import", 3),
    ])
    scenario_gold_path = _write_scenario_gold(tmp_path, {
        sid: [{"turn": t + 1, "gold": [f"{sid}-g{t}"], "expect_kind": "answer"} for t in range(3)]
        for sid in ("S1-landlord", "S2-agency", "D-import")
    })
    koyu_path = _write_koyu(tmp_path, _g_koyu_doc())
    article_map_path = _write_article_map(tmp_path, {
        "Landlordonboarding00": {"file_exists": True, "fine_ids": ["prospect/A/one", "prospect/B/two"]},
    })
    return SimpleNamespace(
        koyu=koyu_path, rule=str(tmp_path / "no-such-rule.json"), topics=topics_path,
        article_map=article_map_path, map_v2=map_v2_path, answerability_canon=canon_path,
        round9_dir=round9_dir, sensitive=sensitive_path, scenarios=scenarios_path,
        sub_map=sub_map_path, scenario_gold=scenario_gold_path,
        out_items=str(tmp_path / "out" / "outline-probe.json"),
        out_rule=str(tmp_path / "out" / "rule.json"),
        canon=str(tmp_path / "no-such-canon.md"), agent_rules=str(tmp_path / "no-such-agent-rules.py"),
        seed_prefix=SEED, dry_run=False,
    )


def test_dry_run_prints_and_writes_nothing(tmp_path, capsys):
    args = _full_materials(tmp_path)
    args.dry_run = True
    rc = ops.run(args)
    assert rc == ops.EXIT_OK
    assert not os.path.exists(args.out_items)
    assert not os.path.exists(args.out_rule)
    out = capsys.readouterr().out
    for layer in ("A", "B", "C", "D", "E", "F", "G"):
        assert f"[outline_probe_select] {layer}" in out or f"{layer}（multi）" in out


def test_full_run_writes_items_with_frozen_id_prefixes_and_rule_file(tmp_path):
    args = _full_materials(tmp_path)
    rc = ops.run(args)
    assert rc == ops.EXIT_OK
    assert os.path.isfile(args.out_items)
    assert os.path.isfile(args.out_rule)

    with open(args.out_items, encoding="utf-8") as f:
        doc = json.load(f)
    assert "_meta" in doc and {"rule_sha256", "frozen_at", "n", "seed_prefix", "inputs_sha256"} <= set(doc["_meta"])
    ids = [it["id"] for it in doc["items"]]
    # id 前綴＝層碼；F 是 `F-<scenario_id>`
    assert any(i.startswith("A-") for i in ids)
    assert any(i.startswith("B-") for i in ids)
    assert any(i.startswith("C-") for i in ids)
    assert any(i.startswith("D-") for i in ids)
    assert any(i.startswith("E-") for i in ids)
    assert any(i.startswith("G-") for i in ids)
    assert "F-S1-landlord" in ids and "F-S2-agency" in ids and "F-D-import" in ids

    multi_items = [it for it in doc["items"] if it["stratum"] == "multi"]
    assert len(multi_items) == 3
    for it in multi_items:
        assert "turns" in it and len(it["turns"]) == 3
        for t in it["turns"]:
            assert {"turn", "q", "gold", "expect_kind"} <= set(t)

    single_items = [it for it in doc["items"] if it["stratum"] != "multi"]
    for it in single_items:
        assert {"id", "q", "stratum", "gold", "expect_kind"} <= set(it)

    with open(args.out_rule, encoding="utf-8") as f:
        rule_doc = json.load(f)
    assert rule_doc["seed_prefix"] == SEED
    assert rule_doc["md5_normalization"] == "none"
    layer_ids = {s["id"] for s in rule_doc["strata"]}
    assert layer_ids == {"A", "B", "C", "D", "E", "F", "G"}
    for s in rule_doc["strata"]:
        assert {"id", "stratum_literal", "definition", "source_paths", "source_sha256",
                "population_n", "take_n", "insufficient"} <= set(s)


def test_full_run_fails_loud_when_a_stratum_population_is_empty(tmp_path):
    args = _full_materials(tmp_path)
    # 讓 G 母體變空：article-map 對不到任何 fine_ids 且 koyu 不含跨粗目文章
    args.koyu = _write_koyu(tmp_path, {"unrelated": {"title": "t", "phrasings": [
        {"n": 1, "type": "直接", "q": "不相干"},
    ]}})
    args.article_map = _write_article_map(tmp_path, {"unrelated": {"file_exists": True, "fine_ids": []}})
    with pytest.raises(SystemExit) as exc:
        ops.run(args)
    assert exc.value.code == ops.EXIT_FAIL


def test_full_run_fails_loud_on_missing_input_file(tmp_path):
    args = _full_materials(tmp_path)
    args.sensitive = str(tmp_path / "does-not-exist.json")
    with pytest.raises(SystemExit) as exc:
        ops.run(args)
    assert exc.value.code == ops.EXIT_FAIL


# ---------------------------------------------------------------------------
# 正對照：`load_round9_answered_counts` 真的讀得到已知存在的答到列
# （否定結論紀律：先證工具看得見已知存在的訊號，才能信它回報「0/6」）
# ---------------------------------------------------------------------------

def test_round9_loader_sees_known_answered_row(tmp_path):
    round9_dir = _write_round9(tmp_path, {"T1:phrasing:0": 6})  # 6/6 全答到
    counts = ops.load_round9_answered_counts(round9_dir)
    assert counts["T1:phrasing:0"] == (6, 6)


def test_round9_loader_fails_loud_on_missing_dir(tmp_path):
    with pytest.raises(SystemExit):
        ops.load_round9_answered_counts(str(tmp_path / "no-such-round9-dir"))
