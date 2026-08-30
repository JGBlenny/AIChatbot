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

## preserve **source-local** ordering，⛔ 不是 container assembly ordering（C2-I3）

```text
best_keyword_source_rank = MIN(keyword_source_rank of contributing keyword rows)
                         ＝ **keyword selector 自己回傳順序**中最早的那一筆
⛔ NOT global concatenated results ordinal
   （後者只是 vector results ＋ keyword fallback 的容器組裝順序；C2 已把兩條 nomination
     provenance 拆開，再把 container order 升格成 ranking authority 等於把它們混回去）
```

## tie-break：`responsibility_id ASC`——**deterministic only，zero semantic meaning**

```text
一個 keyword row → 多個 responsibility（multi-membership）時，
這些 responsibility 的 best_keyword_source_rank **完全相同**，
而舊世界只有一個 row，⛔ 沒有「既有 row order」可 preserve。
⇒ 以 responsibility_id ASC 打破平手，理由只有三個：
   clean checkout 可重現／⛔ 不依 dict accidental order／top20 boundary 可稽核。
⚠️ responsibility_id **永遠不得**成為 relevance signal。
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

#: keyword row 攜帶 **selector-local** rank 的欄位（C2-I3 業主裁定 2026-08-30）
KEYWORD_RANK_FIELD = "keyword_source_rank"


class KeywordRankMissing(RuntimeError):
    """keyword_fallback row 未攜帶 selector-local rank——⚠️ **大聲失敗**。

    ⛔ 不得靜默改用 global results ordinal：那是**容器組裝順序**（implementation artifact），
    ⛔ 不是 keyword nomination path 自己產生的順序。
    """


def annotate_keyword_source_rank(keyword_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """在 **keyword 產生點**就把 selector-local rank 蓋上去（⛔ 不要等 concat 完才算）。

    ```text
    keyword_source_rank = index in keyword_fallback selector output
    ```
    """
    for i, r in enumerate(keyword_rows):
        r[KEYWORD_RANK_FIELD] = i
    return keyword_rows


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
                    _vector_scores=[])
                acc[resp] = c
            c["contributing_row_ids"].append(rid)
            if is_keyword:
                c["has_keyword_nomination"] = True
                # preserve **source-local** ordering：取 contributing keyword rows 在
                # **keyword selector 自己回傳順序**中的最小 rank。
                # ⛔ 不新造 keyword score、⛔ 不 SUM／MAX keyword aliases、
                # ⛔ 不退回 global results ordinal。
                rank = row.get(KEYWORD_RANK_FIELD)
                if rank is None:
                    raise KeywordRankMissing(
                        f"row {rid}：keyword_fallback 未帶 {KEYWORD_RANK_FIELD}"
                        f"——⛔ 不得靜默改用 global results ordinal")
                if c["best_keyword_source_rank"] is None or rank < c["best_keyword_source_rank"]:
                    c["best_keyword_source_rank"] = rank
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

    順序：① keyword-priority responsibilities（依 **selector-local** best_keyword_source_rank）
          ② vector-only responsibilities（依 best_vector_nomination_score 遞減）
          ③ 補到 limit 個 **distinct** responsibilities

    ⚠️ 兩桶的 tie-break 皆為 `responsibility_id ASC`——**deterministic only，zero semantic meaning**。
    ⛔ keyword bucket **不得**用 vector 分數重排：現行 policy 是「keyword fallback 優先保留」，
       ⛔ 不是「keyword 先取得資格、再用 vector 重排」。
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
    # ⛔ keyword bucket 只看 selector-local rank，**完全不看** vector 分數
    kw.sort(key=lambda c: (c["best_keyword_source_rank"], c["responsibility_id"]))
    vec.sort(key=lambda c: (-c["best_vector_nomination_score"], c["responsibility_id"]))
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
