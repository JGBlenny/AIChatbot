#!/usr/bin/env python3
"""步 5b 權威來源核對（knowledge-outline-and-intent-architecture｜2026-09-07 業主裁：交業主前先盤查）。

**為什麼有這步**：2026-09-07 步 5 把 11 格列成 not_available／owner_decision 直接交業主問「真的沒有嗎」，
業主回：「先盤查再給我真的不確認的」。事後派 scout 對 jgb2 程式對碼，11 格有 8 格是程式證明得了的事實。
「問業主」不是盤查的替代品——是盤查窮盡後的剩餘。

機制（決定性、⛔ 不呼叫 LLM）：
  worklist  讀 coverage-map.json → 需核對的格（disposition ∈ {not_available, owner_decision}）＋權威來源清單 → worklist.json
  check     讀 coverage-map.json＋source-audit.json（人／scout 填）→ 驗每格有三態之一與證據；
            verified_* 必附 `path:symbol` 證據、verified_absent 必附正對照、verified_fact 必附帳本錨點且錨點存在、
            owner_needed 必附 why_unresolvable；寫狀態檔 `source_audit`；未核對 >0 ⇒ exit 2。
Stop hook：`reweigh.needs_source_audit>0` 且已產 diff_report、而 `source_audit.unaudited` 缺或 >0 ⇒ 擋（交業主前）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _envelope import find_repo_root, load_schema, update_state, validate, write_json  # noqa: E402

_SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schemas", "source-audit.json")
NEEDS_AUDIT = ("not_available", "owner_decision")
STATUSES = ("verified_fact", "verified_absent", "owner_needed", "owner_decided")
#: 證據形狀：`path:symbol`（行號只當輔助）或 `help:<slug>`／`docs:<path>#<anchor>`
EVIDENCE_RE = re.compile(r"^(?:[\w./\-]+\.[A-Za-z0-9]{1,8}:\S.*|help:\S+|docs:\S+|config:\S+)$")
DEFAULT_AUTHORITY = [
    "code:/Users/lenny/jgb/project/jgb/jgb2 (master; git status 乾淨才算)",
    "docs:/Users/lenny/jgb/project/jgb/jgb2/docs",
    "help:/Users/lenny/jgb/幫助中心/JGB幫助中心_HTML_交付_20260818/*_zh-Hant.html",
    "ledger:docs/knowledge/jgb-product-facts.md",
]


class SourceAuditError(ValueError):
    pass


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _sha(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def needs_audit(coverage: dict) -> list[dict]:
    return [c for c in coverage["cells"] if c.get("disposition") in NEEDS_AUDIT]


def build_worklist(coverage_path: str) -> dict:
    cm = _load(coverage_path)
    items = []
    for c in needs_audit(cm):
        items.append({
            "cell_id": c["cell_id"], "topic": c.get("topic"), "question": (c["min_verification"]["phrasings"] or [""])[0],
            "disposition": c["disposition"], "fix_type": c.get("fix_type"),
            "judge_label": c.get("judge_label"), "cause_state": c.get("cause_state"),
            "required": "verified_fact｜verified_absent（附正對照）｜owner_needed（附 why_unresolvable）",
        })
    return {"step": "source_audit_worklist", "coverage_map_sha": _sha(coverage_path),
            "authority_sources": DEFAULT_AUTHORITY, "count": len(items), "items": items,
            "brief": "每格對權威來源盤查；否定結論必帶正對照（同一掃描必須命中一個已知存在的符號）；"
                     "事實寫進帳本並回填 ledger_anchor；只有 owner_needed 才交業主。"}


def _ledger_anchors(ledger_path: str) -> set[str]:
    if not os.path.isfile(ledger_path):
        return set()
    with open(ledger_path, encoding="utf-8") as f:
        return set(re.findall(r"\{#([A-Za-z0-9_-]+)\}", f.read()))


def check(coverage_path: str, audit_path: str, ledger_path: str) -> dict:
    cm = _load(coverage_path)
    audit = _load(audit_path)
    validate(audit, load_schema(_SCHEMA_PATH))
    if audit["coverage_map_sha"] != _sha(coverage_path):
        raise SourceAuditError("source-audit.coverage_map_sha ≠ 目前 coverage-map.json（核對的是另一版去向）")
    need = {c["cell_id"] for c in needs_audit(cm)}
    recs = {r["cell_id"]: r for r in audit["records"]}
    anchors = _ledger_anchors(ledger_path)
    problems: list[str] = []
    for cid in sorted(need):
        r = recs.get(cid)
        if r is None:
            problems.append(f"{cid}: 未核對（無紀錄）"); continue
        st = r["status"]
        if st in ("verified_fact", "verified_absent"):
            ev = r.get("evidence") or []
            bad = [e for e in ev if not EVIDENCE_RE.match(e)]
            if not ev:
                problems.append(f"{cid}: {st} 無證據")
            if bad:
                problems.append(f"{cid}: 證據形狀不對（要 path:symbol／help:／docs:）：{bad[:2]}")
        if st == "verified_absent" and not (r.get("positive_control") or "").strip():
            problems.append(f"{cid}: verified_absent 缺正對照（否定結論不得無正對照）")
        if st == "verified_fact":
            a = r.get("ledger_anchor")
            if not a:
                problems.append(f"{cid}: verified_fact 缺 ledger_anchor")
            elif a not in anchors:
                problems.append(f"{cid}: ledger_anchor #{a} 不在 {ledger_path}")
        if st == "owner_needed" and not (r.get("why_unresolvable") or "").strip():
            problems.append(f"{cid}: owner_needed 缺 why_unresolvable（要說明盤查了什麼、為何仍定不了）")
        if st == "owner_decided" and not (r.get("owner_decision") or "").strip():
            problems.append(f"{cid}: owner_decided 缺 owner_decision")
    extra = sorted(set(recs) - need)
    summary = {
        "needs_audit": len(need),
        "unaudited": len([p for p in problems]),
        "by_status": {s: sum(1 for c in need if recs.get(c, {}).get("status") == s) for s in STATUSES},
        "owner_needed_cells": sorted(c for c in need if recs.get(c, {}).get("status") == "owner_needed"),
        "extra_records_not_required": extra,
        "problems": problems,
    }
    return summary


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="步 5b 權威來源核對：worklist／check")
    sub = p.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("worklist"); w.add_argument("--coverage", required=True); w.add_argument("--out", required=True)
    c = sub.add_parser("check"); c.add_argument("--coverage", required=True); c.add_argument("--audit", required=True)
    c.add_argument("--ledger", default=os.path.join("docs", "knowledge", "jgb-product-facts.md"))
    a = p.parse_args(argv)
    if a.cmd == "worklist":
        wl = build_worklist(a.coverage)
        write_json(a.out, wl)
        print(f"[source_audit] 需核對 {wl['count']} 格 → {a.out}")
        return 0
    try:
        s = check(a.coverage, a.audit, a.ledger)
    except SourceAuditError as e:
        print(f"[source_audit] ⛔ {e}", file=sys.stderr); return 2
    try:
        root = find_repo_root()
        update_state(root, {"source_audit": {"path": os.path.relpath(os.path.abspath(a.audit), root),
                                             "unaudited": s["unaudited"], "owner_needed": len(s["owner_needed_cells"])}})
    except RuntimeError as e:
        print(f"[source_audit] 警告：找不到 repo 根，跳過狀態檔（{e}）", file=sys.stderr)
    print(f"[source_audit] needs={s['needs_audit']} by_status={s['by_status']} owner_needed={s['owner_needed_cells']} unaudited={s['unaudited']}")
    for pr in s["problems"]:
        print(f"  ⛔ {pr}", file=sys.stderr)
    return 2 if s["unaudited"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
