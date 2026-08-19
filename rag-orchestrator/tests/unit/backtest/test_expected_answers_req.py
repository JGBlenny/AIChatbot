"""unit：期望答案表與 answer_verdict（任務 0.7｜R5.4.1、R5.4.2）。

契約：
- `answer_verdict` 的判定母體＝**期望答案表涵蓋的輪**；
- 母體內任一輪為 `unjudged` 即 FAIL（禁止「沒判＝沒問題」）；
- 母體外的輪不計 FAIL，但**必須揭露筆數與佔比**（不得讓分母悄悄縮小）；
- 表本身納入量測前凍結（R2.5），雜湊可查。
"""
import json
import os

import pytest

from scripts.backtest import decision_replay as dr

pytestmark = pytest.mark.unit


def _tbl(entries, excluded=None):
    return {"manifest_version": "1", "entries": entries,
            "totals": {"excluded_cases": excluded or {}}}


# ── 母體判定 ──
@pytest.mark.req("retrieval-decision-layer:5.4")
def test_in_population_only_for_listed_turns():
    t = _tbl({"18|2": {"case_id": "18", "turn": 2, "expected_answer": "x",
                       "key_points": ["a"], "confidence": "explicit"}})
    assert dr.in_answer_population(t, "18", 2) is True
    assert dr.in_answer_population(t, "18", 1) is False
    assert dr.in_answer_population(t, "07", 4) is False


# ── 母體內 unjudged → FAIL；母體外 unjudged → 不罰但揭露 ──
@pytest.mark.req("retrieval-decision-layer:5.4")
def test_unjudged_inside_population_fails():
    t = _tbl({"18|2": {"case_id": "18", "turn": 2, "expected_answer": "x",
                       "key_points": ["a"], "confidence": "explicit"}})
    trs = {("18", 2): {"answer_verdict": "unjudged"},
           ("07", 4): {"answer_verdict": "unjudged"}}
    with pytest.raises(dr.UnjudgedError) as e:
        dr.assert_answer_population_judged(t, trs)
    assert "18|2" in str(e.value)
    assert "07|4" not in str(e.value), "母體外的 unjudged 不得計入 FAIL"


@pytest.mark.req("retrieval-decision-layer:5.4")
def test_population_fully_judged_passes_and_reports_outside():
    t = _tbl({"18|2": {"case_id": "18", "turn": 2, "expected_answer": "x",
                       "key_points": ["a"], "confidence": "explicit"}})
    trs = {("18", 2): {"answer_verdict": "correct"},
           ("07", 4): {"answer_verdict": "unjudged"},
           ("10", 3): {"answer_verdict": "unjudged"}}
    rep = dr.assert_answer_population_judged(t, trs)
    assert rep["in_population"] == 1 and rep["judged"] == 1
    assert rep["outside_population"] == 2
    assert rep["outside_ratio"] == pytest.approx(2 / 3)   # R5.4.2 必須揭露


# ── 表的結構驗證：expected_answer／key_points 不得空，confidence 值域固定 ──
@pytest.mark.req("retrieval-decision-layer:5.4")
@pytest.mark.parametrize("bad,why", [
    ({"18|2": {"case_id": "18", "turn": 2, "expected_answer": "", "key_points": ["a"],
               "confidence": "explicit"}}, "空的期望答案"),
    ({"18|2": {"case_id": "18", "turn": 2, "expected_answer": "x", "key_points": [],
               "confidence": "explicit"}}, "空的判定要點"),
    ({"18|2": {"case_id": "18", "turn": 2, "expected_answer": "x", "key_points": ["a"],
               "confidence": "maybe"}}, "confidence 越界"),
    ({"18|X": {"case_id": "18", "turn": 2, "expected_answer": "x", "key_points": ["a"],
               "confidence": "explicit"}}, "鍵格式錯"),
])
def test_table_structure_is_validated(bad, why):
    with pytest.raises(dr.GateError):
        dr.validate_expected_answers(_tbl(bad))


@pytest.mark.req("retrieval-decision-layer:5.4")
def test_valid_table_passes_validation():
    t = _tbl({"18|2": {"case_id": "18", "turn": 2, "expected_answer": "續約帳單每月逐筆產出",
                       "key_points": ["每月逐筆產出", "隔日才看得到"],
                       "confidence": "explicit"}})
    assert dr.validate_expected_answers(t) is True


# ── derivable 與 explicit 須可分開統計（derivable 有主觀成分）──
@pytest.mark.req("retrieval-decision-layer:5.4")
def test_confidence_breakdown_is_reportable():
    t = _tbl({"18|2": {"case_id": "18", "turn": 2, "expected_answer": "x",
                       "key_points": ["a"], "confidence": "explicit"},
              "23|1": {"case_id": "23", "turn": 1, "expected_answer": "y",
                       "key_points": ["b"], "confidence": "derivable"}})
    b = dr.expected_answers_breakdown(t)
    assert b == {"explicit": 1, "derivable": 1, "total": 2}


# ── R2.5：表須可雜湊（納入量測前凍結）──
@pytest.mark.req("retrieval-decision-layer:2.5")
def test_table_hash_is_stable_and_content_derived():
    t1 = _tbl({"18|2": {"case_id": "18", "turn": 2, "expected_answer": "x",
                        "key_points": ["a"], "confidence": "explicit"}})
    t2 = json.loads(json.dumps(t1))
    assert dr.expected_answers_hash(t1) == dr.expected_answers_hash(t2)
    t2["entries"]["18|2"]["expected_answer"] = "y"
    assert dr.expected_answers_hash(t1) != dr.expected_answers_hash(t2)


# ── 實體表（代理產出後）須通過驗證 ──
@pytest.mark.req("retrieval-decision-layer:5.4")
def test_real_table_validates_if_present():
    p = os.path.join(dr.CORPUS_DIR, "expected_answers.json")
    if not os.path.exists(p):
        pytest.skip("期望答案表尚未產出（任務 0.7 進行中）")
    with open(p, encoding="utf-8") as f:
        t = json.load(f)
    assert dr.validate_expected_answers(t) is True
    b = dr.expected_answers_breakdown(t)
    assert b["total"] > 0


# ── env_limited：preview 查無屬正確行為，判 incorrect 是假陰性 ──
@pytest.mark.req("retrieval-decision-layer:5.4")
def test_env_limited_incorrect_is_rejected_as_false_negative():
    t = _tbl({"35|1": {"case_id": "35", "turn": 1, "expected_answer": "帳單 739330",
                       "key_points": ["先關帳單"], "confidence": "explicit",
                       "env_limited": True}})
    with pytest.raises(dr.GateError) as e:
        dr.assert_answer_population_judged(t, {("35", 1): {"answer_verdict": "incorrect"}})
    assert "假陰性" in str(e.value)


@pytest.mark.req("retrieval-decision-layer:5.4")
def test_env_limited_not_applicable_passes_and_is_counted():
    t = _tbl({"35|1": {"case_id": "35", "turn": 1, "expected_answer": "帳單 739330",
                       "key_points": ["先關帳單"], "confidence": "explicit",
                       "env_limited": True}})
    rep = dr.assert_answer_population_judged(t, {("35", 1): {"answer_verdict": "not_applicable"}})
    assert rep["not_applicable"] == 1 and rep["env_limited_in_population"] == 1
    assert rep["judged"] == 0, "not_applicable 不算已判正確與否，須分開計"


# ── not_applicable ≠ unjudged：前者判過、後者沒判（母體內沒判即 FAIL）──
@pytest.mark.req("retrieval-decision-layer:5.4")
def test_not_applicable_is_not_unjudged():
    assert "not_applicable" in dr.ANSWER_VERDICTS and "unjudged" in dr.ANSWER_VERDICTS
    t = _tbl({"35|1": {"case_id": "35", "turn": 1, "expected_answer": "x",
                       "key_points": ["a"], "confidence": "explicit", "env_limited": True}})
    with pytest.raises(dr.UnjudgedError):
        dr.assert_answer_population_judged(t, {("35", 1): {"answer_verdict": "unjudged"}})
