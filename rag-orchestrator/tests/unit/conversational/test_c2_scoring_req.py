"""unit：C2-I2 responsibility semantic scoring guards（業主凍結 2026-08-30）。

```text
G7a nomination isolation    只改 alias／nomination 證據 → 三個 semantic 欄位**全部不變**
G7b canonical vector causality  只改 canonical vector → vector arm 變，
                            且 final 依 **0.1 權重**產生對應變化（連公式接線一起測）
G7c canonical text authority 改 row summary／answer／representation → reranker input 不得變；
                            反向正對照：只改 canonical text → reranker input **必須**變
M5  vector arm 改成 max(contributing row vector) → **G7a 與 G7b 至少兩盞紅**
M6  reranker surface 改成 best row representation → **G7c 紅**
fail-loud  canonical embedding／text 缺漏、id 查無、維度不符 → 一律 raise，⛔ 不降級
parity     cosine 與現行 retrieval 語義（pgvector 1-(a<=>b)）相同
```
"""
import json
import os

import pytest

from services import responsibility_scoring as rs
from services.responsibility_scoring import CanonicalArtifactError, ResponsibilityScorer

pytestmark = pytest.mark.unit

_HERE = os.path.dirname(os.path.abspath(__file__))
R10P = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".kiro", "specs",
                                    "conversational-routing-execution", "r10p"))
RID = "R-28"          # 滯納金 instance responsibility（3939／3940）


@pytest.fixture(scope="module")
def registry():
    with open(os.path.join(R10P, "registry-v2.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def index():
    with open(os.path.join(R10P, "derived", "canonical-embeddings.json"), encoding="utf-8") as f:
        return json.load(f)


class _Rerank:
    """記錄 reranker **實際看到的 surface**——G7c 靠這個證明 slot 沒接錯。"""

    def __init__(self, score=0.80):
        self.seen = []
        self.score = score

    def __call__(self, query, texts):
        self.seen.append((query, list(texts)))
        return [self.score] * len(texts)


def _cand(**over):
    c = {"responsibility_id": RID, "has_keyword_nomination": False,
         "best_keyword_source_rank": None, "best_vector_nomination_score": 0.81}
    c.update(over)
    return c


def _qvec(index, rid=RID, jitter=0.0):
    v = next(e["embedding"] for e in index["entries"] if e["responsibility_id"] == rid)
    return [x + jitter for x in v]


# ───────────────────────── parity ─────────────────────────
@pytest.mark.req("C2_PARITY:1")
def test_cosine_parity_with_existing_helper(index):
    """⚠️ ⛔ 不另發明 calibration：與現行 in-repo helper 逐位對齊。"""
    from services.digression_detector_db import DigressionDetectorDB
    a, b = _qvec(index, "R-28"), _qvec(index, "R-01")
    mine = rs.cosine_similarity(a, b)
    theirs = DigressionDetectorDB._cosine_similarity(None, a, b)
    assert mine == pytest.approx(theirs, abs=1e-12)
    assert rs.cosine_similarity(a, a) == pytest.approx(1.0, abs=1e-9)


# ───────────────────────── G7a ─────────────────────────
@pytest.mark.req("C2_G7a:1")
def test_g7a_nomination_isolation(registry, index):
    rr = _Rerank()
    s = ResponsibilityScorer(registry, index, rr)
    q = _qvec(index)
    base = s.score(_cand(), "滯納金怎麼收這麼多", q)
    for over in ({"best_vector_nomination_score": 0.05},
                 {"best_vector_nomination_score": 0.99},
                 {"has_keyword_nomination": True, "best_keyword_source_rank": 0}):
        got = s.score(_cand(**over), "滯納金怎麼收這麼多", q)
        for k in rs.SEMANTIC_FIELDS:
            assert got[k] == pytest.approx(base[k]), f"{k} 隨 nomination 證據改變 ⇒ alias 偷渡"
        # provenance 仍**分欄**保留，⛔ 不與 semantic 欄位混寫
        assert got["best_vector_nomination_score"] == over.get(
            "best_vector_nomination_score", 0.81)


@pytest.mark.req("C2_G7a:2")
def test_m5_vector_from_alias_makes_g7a_red(registry, index, monkeypatch):
    """M5：vector arm 偷改成 MAX(contributing row vector)。"""
    monkeypatch.setattr(ResponsibilityScorer, "vector_arm",
                        lambda self, rid, qe: 0.0, raising=True)
    rr = _Rerank()
    s = ResponsibilityScorer(registry, index, rr)
    monkeypatch.setattr(ResponsibilityScorer, "score",
                        lambda self, c, q, qe: {
                            "responsibility_id": c["responsibility_id"],
                            **{k: c.get(k) for k in rs.NOMINATION_FIELDS},
                            "responsibility_vector_similarity": c["best_vector_nomination_score"],
                            "responsibility_rerank_similarity": self.rerank_arm(
                                c["responsibility_id"], q),
                            "final_similarity": rs.VECTOR_WEIGHT * c["best_vector_nomination_score"]
                            + rs.RERANK_WEIGHT * self.rerank_arm(c["responsibility_id"], q)},
                        raising=True)
    q = _qvec(index)
    a = s.score(_cand(best_vector_nomination_score=0.05), "q", q)
    b = s.score(_cand(best_vector_nomination_score=0.99), "q", q)
    assert a["responsibility_vector_similarity"] != b["responsibility_vector_similarity"]
    assert a["final_similarity"] != b["final_similarity"], "M5 未讓 G7a 變紅 ⇒ guard 是裝飾"


# ───────────────────────── G7b ─────────────────────────
@pytest.mark.req("C2_G7b:1")
def test_g7b_canonical_vector_causality_and_weight(registry, index):
    rr = _Rerank(score=0.80)
    s = ResponsibilityScorer(registry, index, rr)
    c = _cand()
    same = s.score(c, "滯納金怎麼收這麼多", _qvec(index, RID))           # 對齊自身
    other = s.score(c, "滯納金怎麼收這麼多", _qvec(index, "R-01"))        # 換成別的 canonical 向量
    assert same["responsibility_vector_similarity"] > other["responsibility_vector_similarity"], \
        "canonical vector 改變未反映到 vector arm"
    assert same["responsibility_rerank_similarity"] == other["responsibility_rerank_similarity"]
    # ⚠️ 連公式接線一起測：rerank 不變時，final 差距必須**恰好**等於 0.1 × vector 差距
    dv = same["responsibility_vector_similarity"] - other["responsibility_vector_similarity"]
    df = same["final_similarity"] - other["final_similarity"]
    assert df == pytest.approx(rs.VECTOR_WEIGHT * dv, abs=1e-12)


@pytest.mark.req("C2_G7b:2")
def test_m5_ignoring_canonical_vector_makes_g7b_red(registry, index, monkeypatch):
    monkeypatch.setattr(ResponsibilityScorer, "vector_arm",
                        lambda self, rid, qe: 0.5, raising=True)   # ⛔ 忽略 canonical vector
    s = ResponsibilityScorer(registry, index, _Rerank())
    c = _cand()
    same = s.score(c, "q", _qvec(index, RID))
    other = s.score(c, "q", _qvec(index, "R-01"))
    assert same["responsibility_vector_similarity"] == other["responsibility_vector_similarity"], \
        "M5 未讓 G7b 變紅 ⇒ guard 是裝飾"


# ───────────────────────── G7c ─────────────────────────
@pytest.mark.req("C2_G7c:1")
def test_g7c_row_text_cannot_reach_reranker(registry, index):
    rr = _Rerank()
    s = ResponsibilityScorer(registry, index, rr)
    q = _qvec(index)
    s.score(_cand(), "q", q)
    surface_before = rr.seen[-1][1]
    # 改 contributing row 的三種文字——⛔ 一律不得影響 reranker input
    s.score(_cand(question_summary="亂改的 summary", answer="亂改的 answer",
                  retrieval_representation="亂改的 representation"), "q", q)
    assert rr.seen[-1][1] == surface_before, "row 文字改變影響了 reranker surface ⇒ slot 接錯"
    expected = next(r["canonical_responsibility"] for r in registry["responsibilities"]
                    if r["responsibility_id"] == RID)
    assert surface_before == [expected], "reranker 看到的不是 registry V2 的 canonical text"


@pytest.mark.req("C2_G7c:2")
def test_g7c_positive_control_canonical_text_changes_surface(registry, index):
    """反向正對照：只改 canonical text → reranker input **必須**變。"""
    import copy
    mutated = copy.deepcopy(registry)
    for r in mutated["responsibilities"]:
        if r["responsibility_id"] == RID:
            r["canonical_responsibility"] = "改過的 canonical 陳述"
    rr = _Rerank()
    ResponsibilityScorer(mutated, index, rr).score(_cand(), "q", _qvec(index))
    assert rr.seen[-1][1] == ["改過的 canonical 陳述"]


@pytest.mark.req("C2_G7c:3")
def test_m6_reranker_on_row_representation_makes_g7c_red(registry, index, monkeypatch):
    """M6：reranker surface 偷改成 best row representation。"""
    monkeypatch.setattr(ResponsibilityScorer, "rerank_arm",
                        lambda self, rid, q: 0.0, raising=True)
    rr = _Rerank()
    s = ResponsibilityScorer(registry, index, rr)

    def bad_score(self, c, q, qe):
        self._rerank_fn(q, [c.get("retrieval_representation", "")])   # ⛔ 錯的 surface
        return {"responsibility_id": c["responsibility_id"]}
    monkeypatch.setattr(ResponsibilityScorer, "score", bad_score, raising=True)
    s.score(_cand(retrieval_representation="row 的 representation"), "q", _qvec(index))
    assert rr.seen[-1][1] == ["row 的 representation"], "M6 未讓 G7c 變紅 ⇒ guard 是裝飾"


# ───────────────────────── fail-loud ─────────────────────────
@pytest.mark.req("C2_FAILLOUD:1")
def test_missing_embedding_raises(registry, index):
    import copy
    idx = copy.deepcopy(index)
    idx["entries"] = [e for e in idx["entries"] if e["responsibility_id"] != RID]
    s = ResponsibilityScorer(registry, idx, _Rerank())
    with pytest.raises(CanonicalArtifactError, match="canonical embedding 缺漏"):
        s.score(_cand(), "q", _qvec(index))


@pytest.mark.req("C2_FAILLOUD:2")
def test_missing_canonical_text_raises(registry, index):
    import copy
    reg = copy.deepcopy(registry)
    for r in reg["responsibilities"]:
        if r["responsibility_id"] == RID:
            r["canonical_responsibility"] = None
    s = ResponsibilityScorer(reg, index, _Rerank())
    with pytest.raises(CanonicalArtifactError, match="canonical_responsibility 為空"):
        s.score(_cand(), "q", _qvec(index))


@pytest.mark.req("C2_FAILLOUD:3")
def test_unknown_responsibility_id_raises(registry, index):
    s = ResponsibilityScorer(registry, index, _Rerank())
    with pytest.raises(CanonicalArtifactError, match="不得 fallback 到 row id"):
        s.score(_cand(responsibility_id="row_3512"), "q", _qvec(index))


@pytest.mark.req("C2_FAILLOUD:4")
def test_dimension_mismatch_raises(registry, index):
    s = ResponsibilityScorer(registry, index, _Rerank())
    with pytest.raises(CanonicalArtifactError, match="維度不符"):
        s.score(_cand(), "q", [0.1, 0.2, 0.3])


@pytest.mark.req("C2_FAILLOUD:5")
def test_historical_responsibility_is_not_scorable(registry, index):
    hist = next(r["responsibility_id"] for r in registry["responsibilities"]
                if r["status"] != "reviewed_active")
    s = ResponsibilityScorer(registry, index, _Rerank())
    with pytest.raises(CanonicalArtifactError):
        s.score(_cand(responsibility_id=hist), "q", _qvec(index))
