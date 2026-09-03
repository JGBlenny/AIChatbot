"""多頁合併（design.md 元件 3）：把 DocuMind 逐頁 `structured_data` 收斂成「一欄一值＋衝突清單」。

規則（需求 2.1–2.6）：
- 單頁非空 → 採用並記 `page`。
- 多頁**相同** → 採用、`confidence` 取各頁最大、`page` 記首見。
- 多頁**不同** → `field_confidences` 最高者為值（同分取首見頁），其餘進 `conflicts`；
  ⛔ 不靜默取第一頁——`conflicts` 非空是呼叫端把該欄位列入 `needs_confirmation` 的訊號。
- `llm_postprocessed is None`（LLM 未觸發）的頁照常參與。
- 頂層 `consensus` 有該欄位時**優先採用且不再頁級合併**（`from_consensus=True`），
  信心度取頂層 `field_confidences`；DocuMind 未來自己做跨頁共識時本模組自動退為 fallback。
- 頁缺 `field_confidences[欄位]` → 以該頁 `structured_data.extraction_confidence` 補位，
  並標 `confidence_source="page_level"`（需求 3.5）。

⚠️ contract 型的 `structured_data` 是三組巢狀物件（`contract_metadata.effective_date`），
`field_names` 可用點路徑；信心度以**葉名**查（DocuMind 的 `field_confidences` 是扁平鍵）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, List, Literal, Mapping, Optional, Sequence, Tuple

from services.ocr_mapping.models import DocuMindPage, FieldConflict

_EMPTY: Tuple[Any, ...] = (None, "", [], {})


@dataclass(frozen=True)
class MergedField:
    value: Optional[Any]
    confidence: Optional[float]
    page: Optional[int]
    conflicts: Tuple[FieldConflict, ...]
    confidence_source: Literal["field", "page_level"]
    from_consensus: bool = False


ABSENT = MergedField(value=None, confidence=None, page=None, conflicts=(), confidence_source="field")


def _get_path(sd: Mapping[str, Any], path: str) -> Any:
    cur: Any = sd
    for part in path.split("."):
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(part)
    return cur


def _is_empty(v: Any) -> bool:
    return v in _EMPTY if not isinstance(v, (list, dict)) else len(v) == 0


def _page_confidence(pg: DocuMindPage, leaf: str) -> Tuple[Optional[float], Literal["field", "page_level"]]:
    sd = pg.structured_data or {}
    fc = sd.get("field_confidences") or pg.field_confidences or {}
    if isinstance(fc, Mapping) and leaf in fc and fc[leaf] is not None:
        return float(fc[leaf]), "field"
    ec = sd.get("extraction_confidence")
    if ec is not None:
        return float(ec), "page_level"
    return None, "field"


def _merge_one(pages: Sequence[DocuMindPage], path: str) -> MergedField:
    leaf = path.rsplit(".", 1)[-1]
    hits: List[Tuple[Any, Optional[float], int, Literal["field", "page_level"]]] = []
    for pg in pages:                                            # 順序＝頁序；llm_postprocessed None 亦參與
        v = _get_path(pg.structured_data or {}, path)
        if _is_empty(v):
            continue
        # ⚠️ 2026-09-03 對抗驗證 ②-3：葉值是 dict／含 dict 的 list 時，跨頁比較與 FieldConflict 會炸成 500
        #    ⇒ 非標量一律字串化（sort_keys 使同內容恆等），⛔ 不在此猜它的語義
        if isinstance(v, dict) or (isinstance(v, list) and any(not isinstance(x, (str, int, float)) for x in v)):
            v = json.dumps(v, ensure_ascii=False, sort_keys=True)
        conf, src = _page_confidence(pg, leaf)
        hits.append((v, conf, pg.page_number, src))
    if not hits:
        return ABSENT

    first_v, first_conf, first_page, first_src = hits[0]
    if all(h[0] == first_v for h in hits):                     # 多頁相同 → max confidence、首見頁
        confs = [h[1] for h in hits if h[1] is not None]
        conf = max(confs) if confs else None
        src = next((h[3] for h in hits if h[1] == conf), first_src) if conf is not None else first_src
        return MergedField(first_v, conf, first_page, (), src)

    def _key(h: Tuple[Any, Optional[float], int, str]) -> Tuple[float, int]:
        return (h[1] if h[1] is not None else -1.0, -h[2])    # 信心度高者勝；同分取頁碼小者
    winner = max(hits, key=_key)
    conflicts = tuple(FieldConflict(value=h[0], page=h[2], confidence=h[1]) for h in hits if h is not winner)
    return MergedField(winner[0], winner[1], winner[2], conflicts, winner[3])


def merge_pages(pages: Sequence[DocuMindPage], field_names: Iterable[str],
                top_level_confidences: Mapping[str, float], consensus: Optional[Mapping[str, Any]]) -> dict[str, MergedField]:
    """逐欄合併；`consensus` 有該欄位（葉名或全路徑）時優先且**不做**頁級合併。"""
    out: dict[str, MergedField] = {}
    consensus = consensus or {}
    for path in field_names:
        leaf = path.rsplit(".", 1)[-1]
        cv = consensus.get(path, consensus.get(leaf))
        if not _is_empty(cv):
            conf = top_level_confidences.get(path, top_level_confidences.get(leaf))
            out[path] = MergedField(cv, float(conf) if conf is not None else None, None, (), "field", from_consensus=True)
            continue
        out[path] = _merge_one(pages, path)
    return out


def collect_needs_confirmation(pages: Sequence[DocuMindPage]) -> List[str]:
    """各頁 `structured_data.needs_confirmation` 取聯集，去重且保留首見順序（需求 2.5）。"""
    seen: dict[str, None] = {}
    for pg in pages:
        for name in (pg.structured_data or {}).get("needs_confirmation") or []:
            if isinstance(name, str) and name not in seen:
                seen[name] = None
    return list(seen)


__all__ = ["ABSENT", "MergedField", "collect_needs_confirmation", "merge_pages"]
