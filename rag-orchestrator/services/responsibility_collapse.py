"""C2-I1：**row／alias → responsibility** 的映射與 collapse（純函式，2026-08-30）。

⚠️ 本模組**不接** production retrieval path——C2-I1 只交付純邏輯 ＋ guards；
   接線是 C2-I4 的事（業主定序 C2-I1→I2→I3→I4）。

## 三種分數的 authority 完全分開（⛔ 不得互相代填）

```text
row／alias recall score  → **nomination evidence**（本模組唯一處理的東西）
canonical vector score   → responsibility semantic vector evidence（C2-I2）
canonical rerank score   → responsibility semantic rerank evidence（C2-I2）
```

## C2-NOMINATION-ADMISSIBILITY-1（取代已被 production fact 推翻的「統一 0.3」）

```text
A responsibility is nomination-admissible iff
    has_keyword_nomination  OR  best_vector_nomination_score >= 0.3
⇒ keyword fallback → threshold **exempt**；vector only → >= 0.3
   （與現行 row policy 一致：keyword_fallback 的 vector_similarity=0 是
     「走 keyword 路徑」的設計預設值，⛔ 不代表低相關）
```

## ⛔ 禁止事項（業主凍結）

```text
⛔ alias／member 數量加權（5 個 alias 不比 1 個多五票）
⛔ SUM(alias scores) 作 nomination
⛔ 把 nomination score 帶進 final semantic score
⛔ 為 unresolved／historical row 自動生成 responsibility candidate
⛔ 趁 collapse 重新定義 keyword relevance（keyword bucket 用 preserve-existing-order）
```
"""
from typing import Any, Callable, Dict, Iterable, List, Optional

#: nomination 聚合器：**MAX**（業主裁定）。⚠️ 這是 mutation 縫（M2 改 sum 必須讓 G2 紅）。
NOMINATION_AGGREGATOR: Callable[[Iterable[float]], float] = max

#: vector nomination 下限（沿用現行 RERANKER_MIN_VECTOR_SIMILARITY 語義）
DEFAULT_VECTOR_FLOOR = 0.3

KEYWORD_METHOD = "keyword_fallback"


class ResponsibilityCandidate(dict):
    """collapse 後的**單一** candidate。⚠️ 一個 responsibility 永遠只有一個 candidate。"""


def map_row_to_responsibilities(row_id: int, mapping: Dict[int, List[str]],
                                allow_row_id_fallback: bool = False) -> List[str]:
    """row → 0..N reviewed_active responsibility ids。

    ⚠️ `allow_row_id_fallback` 是 **mutation 縫**（M3）：⛔ production 永遠是 False。
    ⛔ 缺 responsibility_id 就自動創一個 ＝ 為 unresolved／historical row 製造 authority。
    """
    ids = mapping.get(row_id)
    if ids:
        return list(ids)
    if allow_row_id_fallback:                      # ⛔ M3 mutation only
        return [f"row_{row_id}"]
    return []


def collapse(rows: List[Dict[str, Any]], mapping: Dict[int, List[str]],
             vector_floor: float = DEFAULT_VECTOR_FLOOR,
             allow_row_id_fallback: bool = False) -> List[ResponsibilityCandidate]:
    """把 recall 結果 collapse 成 **distinct** responsibility candidates。

    保留三個 nomination facts（業主指定）：
    `has_keyword_nomination` ／ `best_keyword_source_rank` ／ `best_vector_nomination_score`。
    """
    acc: Dict[str, ResponsibilityCandidate] = {}
    for ordinal, row in enumerate(rows):
        rid = row.get("id")
        is_keyword = row.get("search_method") == KEYWORD_METHOD
        vec = float(row.get("vector_similarity") or 0.0)
        boost = float(row.get("keyword_boost") or 1.0)
        boosted = min(1.0, vec * boost)
        for resp in map_row_to_responsibilities(rid, mapping, allow_row_id_fallback):
            c = acc.get(resp)
            if c is None:
                c = ResponsibilityCandidate(
                    responsibility_id=resp, contributing_row_ids=[],
                    has_keyword_nomination=False, has_vector_nomination=False,
                    best_keyword_source_rank=None, best_vector_nomination_score=0.0,
                    _vector_scores=[], first_ordinal=ordinal)
                acc[resp] = c
            c["contributing_row_ids"].append(rid)
            if is_keyword:
                c["has_keyword_nomination"] = True
                # preserve-existing-order：取 contributing keyword rows 的**最小原始 ordinal**，
                # ⛔ 不新造 keyword score、⛔ 不 SUM／MAX keyword aliases
                if c["best_keyword_source_rank"] is None or ordinal < c["best_keyword_source_rank"]:
                    c["best_keyword_source_rank"] = ordinal
            elif boosted >= vector_floor:
                # ⚠️ 只有**通過既有 admissibility** 的 vector row 才算 vector nomination
                c["has_vector_nomination"] = True
                c["_vector_scores"].append(boosted)
    out = []
    for c in acc.values():
        scores = c.pop("_vector_scores")
        # ⚠️ MAX 只回答「至少有沒有一個 entry surface 足以把它提名進來」，
        #    ⛔ 不是 semantic authority、⛔ 不隨 alias 數量增加
        c["best_vector_nomination_score"] = NOMINATION_AGGREGATOR(scores) if scores else 0.0
        out.append(c)
    return out


def is_nomination_admissible(c: ResponsibilityCandidate,
                             vector_floor: float = DEFAULT_VECTOR_FLOOR) -> bool:
    """C2-NOMINATION-ADMISSIBILITY-1。⚠️ keyword 路徑**豁免** vector 下限。"""
    if c["has_keyword_nomination"]:
        return True
    return c["best_vector_nomination_score"] >= vector_floor


def select_nominated(rows: List[Dict[str, Any]], mapping: Dict[int, List[str]],
                     limit: int = 20, vector_floor: float = DEFAULT_VECTOR_FLOOR,
                     collapse_first: bool = True,
                     allow_row_id_fallback: bool = False) -> List[ResponsibilityCandidate]:
    """collapse → admissibility → top-N **distinct responsibilities**。

    ⚠️ `collapse_first=False` 是 **mutation 縫**（M1：把 collapse 移到 truncation 之後，
    slot-recovery guard 必須紅）；⛔ production 永遠是 True。

    順序：① keyword-priority responsibilities（依 best_keyword_source_rank）
          ② vector-only responsibilities（依 best_vector_nomination_score 遞減，同分取較早 ordinal）
          ③ 補到 limit 個 **distinct** responsibilities
    """
    if collapse_first:
        cands = collapse(rows, mapping, vector_floor, allow_row_id_fallback)
    else:
        # ⛔ M1 mutation：先以 **row** 截斷再 collapse（＝現行 production 的錯誤形狀）
        truncated = rows[:limit]
        cands = collapse(truncated, mapping, vector_floor, allow_row_id_fallback)
    admissible = [c for c in cands if is_nomination_admissible(c, vector_floor)]
    kw = [c for c in admissible if c["has_keyword_nomination"]]
    vec = [c for c in admissible if not c["has_keyword_nomination"]]
    kw.sort(key=lambda c: (c["best_keyword_source_rank"], c["first_ordinal"]))
    vec.sort(key=lambda c: (-c["best_vector_nomination_score"], c["first_ordinal"]))
    return (kw + vec)[:limit]


def load_mapping_from_registry(registry: Dict[str, Any]) -> Dict[int, List[str]]:
    """由 sealed Registry V2 導出 `row_id → [responsibility_id]`。

    ⚠️ **只收 `reviewed_active`**——historical（G5）與 unresolved（G6）一律不進 mapping，
    因此它們在 collapse 階段自然產生 **0 個** candidate，⛔ 不需要另寫排除分支。
    """
    out: Dict[int, List[str]] = {}
    for r in registry.get("responsibilities", []):
        if r.get("status") != "reviewed_active":
            continue
        for m in r.get("members", []):
            out.setdefault(m["row_id"], []).append(r["responsibility_id"])
    for v in out.values():
        v.sort()
    return out
