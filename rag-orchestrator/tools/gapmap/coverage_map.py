#!/usr/bin/env python3
"""覆蓋閉環：格 → 去向（knowledge-outline-and-intent-architecture 任務 2.6｜design 元件 9｜R3.1–R3.7）。

輸入四份**凍結材料**（⛔ 不碰 DB、不跑系統、$0）：
  正本（`CanonDoc`）、`demand-v2.json`（格與問句）、`map-v2.json`（量測層 cause/entry/coverage）、
  `answerability.json`（元件 2 判者裁定的 StepEnvelope）。
輸出每格一筆 `CellRecord`：去向 ∈ {fine, not_available, deliberate_no, owner_decision}、
補法 ∈ {add_knowledge, add_phrasing, list_not_available, cross_audience_rewrite, merge_similar, owner_decision, None}、
`gap_classes` ⊆ {content_gap, retrieval_gap}（R3.5 兩類分報）、`judge_agreement`（R3.4，逐格由 verdicts 算）。

⛔ fail-loud（`CoverageMapError` → CLI exit 2，⛔ 不填預設）：
  判者裁定的正本 sha ≠ 本次解析的正本；判者 fine_id 不在正本；格在判者或量測層缺席；label 非四值；
  `g0.authority` 形狀不在已知哨兵集合（no_source 列）。

規則表與優先序見 `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-2.6-coverage-map-20260907.md` §3–§4。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(_HERE))
if _RAG not in sys.path:
    sys.path.insert(0, _RAG)
from services.agent.canon.canon_parser import CanonDoc, parse_canon  # noqa: E402

DISPOSITIONS = ("fine", "not_available", "deliberate_no", "owner_decision")
FIX_TYPES = ("add_knowledge", "add_phrasing", "list_not_available", "cross_audience_rewrite", "merge_similar", "owner_decision")
LABELS = ("answerable", "partial", "no_source", "deliberate_no")
GAP_CLASSES = ("content_gap", "retrieval_gap")

#: map-v2 `_meta.states` 的實值；比對一律精確字串或明寫前綴（plan §4）。
RETRIEVAL_GAP_STATES = frozenset({"S", "V", "FALSE_HIT"})
UNSTABLE_PREFIX = "UNSTABLE"
CONTENT_GAP_COVERAGE = frozenset({"未覆蓋(回答未含必含)", "已覆蓋⚠️"})
CROSS_AUDIENCE_STATE = "V"
#: 事實帳本來源前綴：細目 `sources` 含此前綴 ⇒ 該細目已對 jgb2 程式核對（docs/knowledge/jgb-product-facts.md）。
LEDGER_SOURCE_PREFIX = "docs:knowledge/jgb-product-facts.md#"

#: demand-v2 `g0.authority` 是自由文字、55 格無一空值，「沒有」用哨兵（plan-verifier 第 3 輪）。
AUTHORITY_YES_PREFIXES = ("kb:", "help:")
AUTHORITY_NO_PREFIXES = ("none", "n/a")


class CoverageMapError(ValueError):
    """輸入不一致或形狀未知——⛔ 不填預設、不猜。"""


def has_authority(text: Optional[str], *, cell_id: str = "?") -> bool:
    t = (text or "").strip()
    if t.startswith(AUTHORITY_YES_PREFIXES):
        return True
    if t.startswith(AUTHORITY_NO_PREFIXES):
        return False
    raise CoverageMapError(f"{cell_id}: g0.authority 形狀未知（{t[:40]!r}），既非 {AUTHORITY_YES_PREFIXES} 也非 {AUTHORITY_NO_PREFIXES}；⛔ 不預設有來源")


def is_retrieval_gap(cause_state: Optional[str]) -> bool:
    c = (cause_state or "").strip()
    return c in RETRIEVAL_GAP_STATES or c.startswith(UNSTABLE_PREFIX)


def is_content_gap(coverage: Optional[str]) -> bool:
    return (coverage or "").strip() in CONTENT_GAP_COVERAGE


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def judge_agreement(entry: dict) -> Optional[float]:
    """與終判 label 相同的 verdict 數／verdict 數；無 verdicts 回 None（⛔ 不填 1.0）。"""
    vs = entry.get("verdicts") or []
    if not vs:
        return None
    same = sum(1 for v in vs if v.get("label") == entry.get("label"))
    return same / len(vs)


def all_verdicts_agree(entry: dict) -> Optional[bool]:
    vs = entry.get("verdicts") or []
    if not vs:
        return None
    return len({v.get("label") for v in vs}) == 1


def _decide(label: str, *, cause_state: str, coverage: str, authority: str, policy_ref: Optional[str],
            fine_id: Optional[str], cell_id: str) -> tuple[str, Optional[str], list[str], Optional[str]]:
    """回 (disposition, fix_type, gap_classes, draft_path)。規則表＝plan §3；優先序 add_knowledge > add_phrasing > None。"""
    gaps: list[str] = []
    if label in ("answerable", "partial"):
        if is_content_gap(coverage):
            gaps.append("content_gap")
        if is_retrieval_gap(cause_state):
            gaps.append("retrieval_gap")
        if label == "partial" or "content_gap" in gaps:
            return "fine", "add_knowledge", gaps, None
        if "retrieval_gap" in gaps:
            return "fine", "add_phrasing", gaps, None
        return "fine", None, gaps, None
    if label == "no_source":
        if (cause_state or "").strip() == CROSS_AUDIENCE_STATE:
            return "owner_decision", "cross_audience_rewrite", gaps, f"canon/drafts/cross-audience/{cell_id}.md"
        if has_authority(authority, cell_id=cell_id):
            return "owner_decision", "add_knowledge", gaps, None
        return "not_available", "list_not_available", gaps, None
    if label == "deliberate_no":
        if policy_ref:
            return "deliberate_no", None, gaps, None
        return "owner_decision", "owner_decision", gaps, None
    raise CoverageMapError(f"{cell_id}: label 非四值（{label!r}）")


def reweigh(canon: CanonDoc, demand_path: str, map_path: str, answerability_path: str) -> list[dict]:
    demand = _load_json(demand_path)
    measured = _load_json(map_path)
    ans = _load_json(answerability_path)

    if ans.get("step") != "answerability":
        raise CoverageMapError(f"answerability 檔 step≠answerability（{ans.get('step')!r}）")
    judged_sha = (ans.get("inputs_sha") or {}).get("canon")
    if judged_sha != canon.canon_sha256:
        raise CoverageMapError(f"判者裁定的正本 sha（{str(judged_sha)[:12]}…）≠ 本次解析正本（{canon.canon_sha256[:12]}…）；判者看的是另一版正本")

    fines = {f.id: f for f in canon.fines()}
    labels = {}
    for x in (ans.get("payload") or {}).get("labels") or []:
        labels[x["cell_id"]] = x
    mcells = {c["id"]: c for c in measured.get("cells") or []}

    out: list[dict] = []
    for c in demand.get("cells") or []:
        cid = c["id"]
        e = labels.get(cid)
        if e is None:
            raise CoverageMapError(f"{cid}: 判者裁定缺此格")
        m = mcells.get(cid)
        if m is None:
            raise CoverageMapError(f"{cid}: map-v2 量測層缺此格")
        label = e.get("label")
        if label not in LABELS:
            raise CoverageMapError(f"{cid}: label 非四值（{label!r}）")
        fid = e.get("fine_id")
        if fid is not None and fid not in fines:
            raise CoverageMapError(f"{cid}: 判者 fine_id {fid!r} 不在正本 {len(fines)} 個細目內")
        if label in ("answerable", "partial") and fid is None:
            raise CoverageMapError(f"{cid}: label={label} 但 fine_id 為 null")
        policy_ref = c.get("policy_ref") or (fines[fid].policy_ref if fid else None)
        disposition, fix_type, gaps, draft_path = _decide(
            label, cause_state=m.get("cause_state") or "", coverage=m.get("coverage") or "",
            authority=(c.get("g0") or {}).get("authority") or "", policy_ref=policy_ref, fine_id=fid, cell_id=cid,
        )
        out.append({
            "cell_id": cid,
            "audience": canon.audience,
            "topic": c.get("topic") or "",
            "cause_state": m.get("cause_state"),
            "entry_state": m.get("entry_state"),
            "coverage": m.get("coverage"),
            "judge_label": label,
            "disposition": disposition,
            "fine_id": fid,
            "fix_type": fix_type,
            "gap_classes": gaps,
            "draft_path": draft_path,
            "min_verification": {"phrasings": list(c.get("questions") or []), "expected_fine_id": fid},
            "judge_agreement": judge_agreement(e),
            "all_verdicts_agree": all_verdicts_agree(e),
        })
    return out


def merge_similar_candidates(canon: CanonDoc, cells: list[dict]) -> list[dict]:
    """see_also 互指且兩細目都被某格判為正解 ⇒ 提案（⛔ 不合併）。"""
    hit = {c["fine_id"] for c in cells if c.get("fine_id")}
    seen: set[tuple[str, str]] = set()
    out = []
    for f in canon.fines():
        for other in f.see_also:
            if f.id in hit and other in hit and (other, f.id) not in seen:
                seen.add((f.id, other))
                out.append({"a": f.id, "b": other, "fix_type": "merge_similar", "status": "proposed"})
    return out


def summarize(cells: list[dict]) -> dict:
    def count(key):
        d: dict = {}
        for c in cells:
            v = c.get(key)
            k = "null" if v is None else str(v)
            d[k] = d.get(k, 0) + 1
        return dict(sorted(d.items()))
    gap = {"content_gap": 0, "retrieval_gap": 0}
    for c in cells:
        for g in c.get("gap_classes") or []:
            gap[g] += 1
    judged = [c for c in cells if c.get("all_verdicts_agree") is not None]
    agree_n = sum(1 for c in judged if c["all_verdicts_agree"])
    return {
        "total": len(cells),
        "cells_without_disposition": sum(1 for c in cells if c.get("disposition") not in DISPOSITIONS),
        "retrieval_gap_with_null_fix_type": sum(1 for c in cells if "retrieval_gap" in (c.get("gap_classes") or []) and c.get("fix_type") is None),
        "by_disposition": count("disposition"),
        "by_fix_type": count("fix_type"),
        "gap_classes": gap,
        "judge_agreement_global": (agree_n / len(judged)) if judged else None,
        "judged_cells": len(judged),
    }


def build_coverage_map(canon_path: str, demand_path: str, map_path: str, answerability_path: str) -> dict:
    canon = parse_canon(canon_path)
    cells = reweigh(canon, demand_path, map_path, answerability_path)
    no_src = [f.id for f in canon.fines() if not f.sources]
    # 對碼標記（2026-09-07 業主：確認過的事要標）：細目任一 source 指向事實帳本錨點 ＝ 已對 jgb2 程式核對過。
    verified = sorted(f.id for f in canon.fines() if any(src.startswith(LEDGER_SOURCE_PREFIX) for src in f.sources))
    kinds: dict = {}
    for f in canon.fines():
        for src in f.sources:
            k = src.split(":", 1)[0] if ":" in src else "other"
            kinds[k] = kinds.get(k, 0) + 1
    meta = {
        "step": "reweigh",
        "audience": canon.audience,
        "inputs_sha": {
            "canon": canon.canon_sha256,
            "demand": sha256_file(demand_path),
            "map": sha256_file(map_path),
            "answerability": sha256_file(answerability_path),
        },
        "fines_total": len(canon.fines()),
        "fines_without_sources": no_src,
        "fines_referenced": sorted({c["fine_id"] for c in cells if c.get("fine_id")}),
        "fines_verified_against_code": verified,
        "fines_unverified": sorted(f.id for f in canon.fines() if f.id not in set(verified)),
        "fines_source_kinds": dict(sorted(kinds.items())),
        "merge_similar_candidates": merge_similar_candidates(canon, cells),
        "summary": summarize(cells),
        "note": "cause_state／entry_state／coverage 來自 map-v2（對 kb 量測），不是對正本索引；add_phrasing 的最小驗證＝正本索引建好後重跑檢索（元件 10 步 1）。",
    }
    return {"_meta": meta, "cells": cells}


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="格 → 去向（決定性、$0、不碰 DB）")
    p.add_argument("--canon", required=True)
    p.add_argument("--demand", required=True)
    p.add_argument("--map", required=True)
    p.add_argument("--answerability", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    try:
        cm = build_coverage_map(a.canon, a.demand, a.map, a.answerability)
    except CoverageMapError as e:
        print(f"[coverage_map] ⛔ {e}", file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(cm, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    s = cm["_meta"]["summary"]
    print(f"[coverage_map] total={s['total']} by_disposition={s['by_disposition']} by_fix_type={s['by_fix_type']} "
          f"gap={s['gap_classes']} agreement={s['judge_agreement_global']} fines_without_sources={len(cm['_meta']['fines_without_sources'])} → {a.out}")
    if s["cells_without_disposition"] or cm["_meta"]["fines_without_sources"]:
        print("[coverage_map] ⛔ 出口未達：無去向格或無來源細目 >0", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
