"""C2-I2：**responsibility-level semantic scoring**（2026-08-30，業主凍結）。

⚠️ 本模組**不接** production retrieval path——⛔ 未改 base_retriever／_finalize_scores／
   RERANKER_INPUT_LIMIT／現行 row selector／R7.2 SCORE_SHIFT_PROBE。transport 是 C2-I4。

## 兩個 semantic arm 的唯一合法來源

```text
responsibility_vector_similarity = similarity(query_embedding, canonical_embedding[R-x])
responsibility_rerank_similarity = rerank(user_query, registry_v2[R-x].canonical_responsibility)
⚠️ 兩邊必須用**同一個 responsibility_id** join。
```

⛔ 以下一律**不得**進 vector 欄位：`max(alias_vector)`／`avg(alias_vector)`／
`nomination_score`／`best_vector_nomination_score`。
⛔ reranker surface 一律**不得**是 row summary／answer／retrieval_representation／best alias text。

## 公式（本輪 ⛔ 不重新校）

```text
final_similarity = 0.1 * responsibility_vector_similarity
                 + 0.9 * responsibility_rerank_similarity
```

## ⚠️ fail-loud：runtime consumer ⛔ 不得偷偷降級

```text
canonical embedding missing   → ❌ raise（⛔ 不用 alias vector）
canonical text missing        → ❌ raise（⛔ 不用 row summary）
responsibility_id 查不到       → ❌ raise（⛔ 不用 row id）
embedding 維度不符             → ❌ raise（⛔ 不用零向量）
```

⚠️ 這**不是**與 INV21／INV23 重複防守：INV23 證 **artifact 完整**，本模組證
**consumer 在 artifact 壞掉時不會偷偷降級**。

## nomination metadata 保留但**分欄**

輸出同時帶 nomination provenance（三欄）與 semantic scoring（三欄），
⛔ 不把它們塞回同一個 `similarity` 欄位——否則無法證明資訊沒串錯。
"""
import math
from typing import Any, Callable, Dict, List

VECTOR_WEIGHT = 0.1
RERANK_WEIGHT = 0.9

#: nomination provenance 欄位（⛔ 不得與 semantic scoring 欄位混寫）
NOMINATION_FIELDS = ("has_keyword_nomination", "best_keyword_source_rank",
                     "best_vector_nomination_score")
SEMANTIC_FIELDS = ("responsibility_vector_similarity", "responsibility_rerank_similarity",
                   "final_similarity")


class CanonicalArtifactError(RuntimeError):
    """canonical artifact 不可用——⚠️ **必須大聲失敗**，⛔ 不得降級。"""


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """與現行 retrieval 相同語義的 cosine：pgvector 的 `1 - (a <=> b)`。

    ⚠️ ⛔ 不另發明 normalization／calibration——parity guard 對照
    `digression_detector_db._cosine_similarity` 與 pgvector 語義。
    """
    if len(a) != len(b):
        raise CanonicalArtifactError(
            f"embedding 維度不符：{len(a)} vs {len(b)}——⛔ 不得以零向量帶過")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class ResponsibilityScorer:
    """以 sealed Registry V2 ＋ derived canonical embeddings 對 candidate 打語義分。"""

    def __init__(self, registry: Dict[str, Any], embedding_index: Dict[str, Any],
                 rerank_fn: Callable[[str, List[str]], List[float]]):
        self._canonical_text: Dict[str, Any] = {}
        for r in registry.get("responsibilities", []):
            if r.get("status") != "reviewed_active":
                continue          # ⚠️ historical ⛔ 不進 active scoring
            self._canonical_text[r["responsibility_id"]] = r.get("canonical_responsibility")
        self._embedding: Dict[str, List[float]] = {
            e["responsibility_id"]: e["embedding"] for e in embedding_index.get("entries", [])}
        self._rerank_fn = rerank_fn

    # ── 兩個 arm 各自的唯一來源 ────────────────────────────────────────
    def canonical_text(self, rid: str) -> str:
        if rid not in self._canonical_text:
            raise CanonicalArtifactError(
                f"{rid}：registry V2 查無 reviewed_active responsibility——⛔ 不得 fallback 到 row id")
        text = self._canonical_text[rid]
        if not text:
            raise CanonicalArtifactError(
                f"{rid}：canonical_responsibility 為空——⛔ 不得改用 row summary")
        return text

    def canonical_embedding(self, rid: str) -> List[float]:
        v = self._embedding.get(rid)
        if not v:
            raise CanonicalArtifactError(
                f"{rid}：canonical embedding 缺漏——⛔ 不得改用 alias vector")
        return v

    def vector_arm(self, rid: str, query_embedding: List[float]) -> float:
        return cosine_similarity(query_embedding, self.canonical_embedding(rid))

    def rerank_arm(self, rid: str, user_query: str) -> float:
        scores = self._rerank_fn(user_query, [self.canonical_text(rid)])
        if not scores:
            raise CanonicalArtifactError(f"{rid}：reranker 未回傳分數——⛔ 不得以 0 帶過")
        return float(scores[0])

    # ── 合成（公式本輪 ⛔ 不重新校）────────────────────────────────────
    def score(self, candidate: Dict[str, Any], user_query: str,
              query_embedding: List[float]) -> Dict[str, Any]:
        rid = candidate["responsibility_id"]
        # ⚠️ 先驗 responsibility 身分：⛔ 不明的 id 必須以「查無 responsibility」失敗，
        #    ⛔ 不得被後面的 embedding 缺漏訊息蓋掉（錯誤訊息指錯地方＝除錯時指錯方向）
        self.canonical_text(rid)
        vec = self.vector_arm(rid, query_embedding)
        rer = self.rerank_arm(rid, user_query)
        out = {"responsibility_id": rid}
        for k in NOMINATION_FIELDS:          # ⚠️ provenance 保留但**分欄**
            out[k] = candidate.get(k)
        out["responsibility_vector_similarity"] = vec
        out["responsibility_rerank_similarity"] = rer
        out["final_similarity"] = VECTOR_WEIGHT * vec + RERANK_WEIGHT * rer
        return out

    def score_all(self, candidates: List[Dict[str, Any]], user_query: str,
                  query_embedding: List[float]) -> List[Dict[str, Any]]:
        return [self.score(c, user_query, query_embedding) for c in candidates]
