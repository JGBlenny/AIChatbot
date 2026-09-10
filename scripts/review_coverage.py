#!/usr/bin/env python3
"""業主審覆蓋閉環用：把 coverage-map 的格攤成人讀表（問句／去向／補法／細目標題／判者指的那一句）。唯讀、不碰 DB。

用法：python3 scripts/review_coverage.py [--bucket not_available|owner_decision|fine|deliberate_no] [--fix add_phrasing|…] [--cells C22,C46]
"""
from __future__ import annotations
import argparse, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, ".kiro/specs/knowledge-outline-and-intent-architecture/inputs")
sys.path.insert(0, os.path.join(ROOT, "rag-orchestrator"))
from services.agent.canon.canon_parser import parse_canon  # noqa: E402

p = argparse.ArgumentParser(); p.add_argument("--bucket"); p.add_argument("--fix"); p.add_argument("--cells")
p.add_argument("--map", default=os.path.join(SPEC, "coverage-map-20260907.json"))
p.add_argument("--canon", default=os.path.join(SPEC, "prospect.draft.review-20260907.md"))
p.add_argument("--answerability", default=os.path.join(ROOT, ".claude/skills/outline-curation/runs/2026-09-06T00-00-00Z/answerability-canon.json"))
a = p.parse_args()
cm = json.load(open(a.map, encoding="utf-8")); fines = {f.id: f for f in parse_canon(a.canon).fines()}
ev = {x["cell_id"]: x for x in json.load(open(a.answerability, encoding="utf-8"))["payload"]["labels"]}
want = set(a.cells.split(",")) if a.cells else None
for c in cm["cells"]:
    if a.bucket and c["disposition"] != a.bucket: continue
    if a.fix and c["fix_type"] != a.fix: continue
    if want and c["cell_id"] not in want: continue
    q = c["min_verification"]["phrasings"]; f = fines.get(c["fine_id"]) if c["fine_id"] else None
    unit = ev[c["cell_id"]].get("evidence_unit"); sent = f.content_units[unit - 1] if (f and unit and unit <= len(f.content_units)) else None
    print(f"\n[{c['cell_id']}] {q[0]}   （去向 {c['disposition']}｜補法 {c['fix_type']}｜判者 {c['judge_label']}｜量測 {c['cause_state']}/{c['coverage']}｜一致 {c['judge_agreement']:.2f}）")
    if f: print(f"   細目：{f.id}「{f.title}」\n   證據第 {unit} 句：{sent}")
    if c["draft_path"]: print(f"   草稿路徑：{c['draft_path']}")
