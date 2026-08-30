"""unit：C2-RERANK-REQUIRED-1 guards（業主凍結 2026-08-30）。

```text
G15 rerank required        canonical vector 有、rerank 缺 → ResponsibilitySemanticScoreIncomplete
G16 legacy branches unreachable  即使帶 keyword provenance ／ nomination vector，
                           rerank 缺仍 **hard fail**（⛔ 沒被誤拿去救 finalization）
G17 rerank completeness    requested IDs == returned IDs（缺／多／重複／unknown 皆整批紅）
G18 final score slot authority  alias .99 vs canonical vector .20 ／ rerank .80
                           → similarity **必須** = .1*.20 + .9*.80 = .74
M8  rerank None → vector-only final → **G15 必紅**
```
⚠️ `keyword_fallback` ＝ **nomination mechanism only**，⛔ 永遠不是 responsibility
   final-score 的 fallback——兩者是不同 stage。
"""
import json
import math
import os

import pytest

from services import responsibility_scoring as rs
from services.responsibility_scoring import (ResponsibilityScorer,
                                             ResponsibilitySemanticScoreIncomplete,
                                             finalize_responsibility_score)

pytestmark = pytest.mark.unit

R10P = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", "..", ".kiro", "specs",
                                    "conversational-routing-execution", "r10p"))


@pytest.fixture(scope="module")
def registry():
    with open(os.path.join(R10P, "registry-v2.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def index():
    with open(os.path.join(R10P, "derived", "canonical-embeddings.json"), encoding="utf-8") as f:
        return json.load(f)


def _cand(rid, **over):
    c = {"responsibility_id": rid, "has_keyword_nomination": False,
         "best_keyword_source_rank": None, "best_vector_nomination_score": 0.0}
    c.update(over)
    return c


def _qvec(index, rid):
    return next(e["embedding"] for e in index["entries"] if e["responsibility_id"] == rid)


# ───────────────────────── G15 ─────────────────────────
@pytest.mark.req("C2_G15:1")
@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), "0.8"])
def test_g15_rerank_required(bad):
    with pytest.raises(ResponsibilitySemanticScoreIncomplete):
        finalize_responsibility_score(0.42, bad)


@pytest.mark.req("C2_G15:2")
def test_g15_vector_also_required():
    with pytest.raises(ResponsibilitySemanticScoreIncomplete):
        finalize_responsibility_score(None, 0.8)


@pytest.mark.req("C2_G15:3")
def test_m8_vector_only_fallback_makes_g15_red():
    """M8：rerank None → vector-only final。"""
    def mutated(vec, rer):
        if rer is None:                      # ⛔ 這正是被禁止的降級
            return vec
        return rs.VECTOR_WEIGHT * vec + rs.RERANK_WEIGHT * rer
    assert mutated(0.42, None) == 0.42, "M8 未讓 G15 變紅 ⇒ guard 是裝飾"


# ───────────────────────── G16 ─────────────────────────
@pytest.mark.req("C2_G16:1")
def test_g16_nomination_evidence_cannot_rescue_finalization(registry, index):
    """帶滿 keyword provenance ＋ nomination vector，rerank 仍缺 → 必須 hard fail。"""
    s = ResponsibilityScorer(registry, index, lambda q, t: [0.8])

    def rerank_dies(query, payload):
        raise TimeoutError("reranker timeout")

    rich = _cand("R-28", has_keyword_nomination=True, best_keyword_source_rank=0,
                 best_vector_nomination_score=0.99)
    with pytest.raises(ResponsibilitySemanticScoreIncomplete, match="不得降級為 vector-only"):
        s.score_batch([rich], "q", _qvec(index, "R-28"), rerank_dies)


# ───────────────────────── G17 ─────────────────────────
def _scorer(registry, index):
    return ResponsibilityScorer(registry, index, lambda q, t: [0.8])


@pytest.mark.req("C2_G17:1")
def test_g17_exact_set_contract(registry, index):
    s = _scorer(registry, index)
    q = _qvec(index, "R-01")
    cands = [_cand("R-01"), _cand("R-02"), _cand("R-03")]

    # 正常：exact set 相符
    ok = s.score_batch(cands, "q", q, lambda _q, p: {k: 0.7 for k in p})
    assert [c["responsibility_id"] for c in ok] == ["R-01", "R-02", "R-03"]

    # 缺一筆（19/20 情境）→ **整批**紅，⛔ 不得只算回來的那些
    with pytest.raises(ResponsibilitySemanticScoreIncomplete, match="缺 \\['R-02'\\]"):
        s.score_batch(cands, "q", q,
                      lambda _q, p: {k: 0.7 for k in p if k != "R-02"})

    # 多出未知 id → 紅
    with pytest.raises(ResponsibilitySemanticScoreIncomplete, match="多 \\['R-99'\\]"):
        s.score_batch(cands, "q", q,
                      lambda _q, p: {**{k: 0.7 for k in p}, "R-99": 0.9})


@pytest.mark.req("C2_G17:2")
def test_g17_duplicate_candidate_rejected(registry, index):
    s = _scorer(registry, index)
    with pytest.raises(ResponsibilitySemanticScoreIncomplete, match="重複 responsibility"):
        s.score_batch([_cand("R-01"), _cand("R-01")], "q", _qvec(index, "R-01"),
                      lambda _q, p: {k: 0.7 for k in p})


@pytest.mark.req("C2_G17:3")
def test_g17_count_only_check_would_be_false_green(registry, index):
    """⚠️ 正對照：缺一多一時 **count 仍相符** ⇒ 只比數量會假綠。"""
    s = _scorer(registry, index)
    cands = [_cand("R-01"), _cand("R-02")]

    def swap(_q, p):
        out = {k: 0.7 for k in p if k != "R-02"}
        out["R-99"] = 0.7
        return out

    with pytest.raises(ResponsibilitySemanticScoreIncomplete):
        s.score_batch(cands, "q", _qvec(index, "R-01"), swap)


# ───────────────────────── G18 ─────────────────────────
@pytest.mark.req("C2_G18:1")
def test_g18_downstream_similarity_is_canonical_only(registry, index, monkeypatch):
    """alias .99／canonical vector .20／canonical rerank .80 → similarity 必須 = .74。"""
    monkeypatch.setattr(ResponsibilityScorer, "vector_arm",
                        lambda self, rid, qe: 0.20, raising=True)
    s = ResponsibilityScorer(registry, index, lambda q, t: [0.80])
    cand = _cand("R-28", has_keyword_nomination=True, best_keyword_source_rank=0,
                 best_vector_nomination_score=0.99)
    scored = s.score_batch([cand], "q", _qvec(index, "R-28"), lambda _q, p: {k: 0.80 for k in p})[0]
    out = rs.to_downstream_result(scored)
    assert out["similarity"] == pytest.approx(0.74, abs=1e-12)
    assert out["score_source"] == "responsibility_rerank"
    # ⛔ 任何含 .99 的結果都是錯的
    assert not math.isclose(out["similarity"], 0.99, abs_tol=1e-6)
    assert out["best_vector_nomination_score"] == 0.99, "provenance 應保留但**分欄**"


@pytest.mark.req("C2_G18:2")
def test_g18_cannot_project_before_finalize():
    with pytest.raises(ResponsibilitySemanticScoreIncomplete, match="尚未 finalize"):
        rs.to_downstream_result({"responsibility_id": "R-01"})
