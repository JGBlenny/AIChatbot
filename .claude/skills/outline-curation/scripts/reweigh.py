#!/usr/bin/env python3
"""步 5 reweigh（knowledge-outline-and-intent-architecture 任務 2.6｜design 元件 1 步 5｜E6）。

呼叫 `rag-orchestrator/tools/gapmap/coverage_map.py` 重量：四份凍結材料 → `coverage-map.json`（含 `_meta`）
＋ StepEnvelope `coverage-reweigh.json`（`payload.cells` 只放格；schema 為 additionalProperties:false）。

E6 機制：`answerability.json` 的 `payload.needs_rubric_revision=true` ⇒ **exit 2、不重量**（停下回主 session）。
出口（步 0／步 5；Stop hook 亦查 session.json `reweigh` 鍵）：`cells_without_disposition==0`、`fines_without_sources==0`。
⛔ 不呼叫 LLM、不碰 DB。
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _envelope import find_repo_root, load_schema, make_envelope, update_state, validate, write_json  # noqa: E402

SKILL_VERSION = "0.1.0"
_SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schemas", "coverage-reweigh.json")


def _rag_root(repo_root: str | None) -> str:
    for cand in ([os.path.join(repo_root, "rag-orchestrator")] if repo_root else []) + ["/app"]:
        if os.path.isfile(os.path.join(cand, "tools", "gapmap", "coverage_map.py")):
            return cand
    raise RuntimeError("找不到 rag-orchestrator/tools/gapmap/coverage_map.py（repo 根或 /app）")


def main() -> int:
    p = argparse.ArgumentParser(description="步 5：格 → 去向，包成 StepEnvelope")
    p.add_argument("--canon", required=True)
    p.add_argument("--demand", required=True)
    p.add_argument("--map", required=True)
    p.add_argument("--answerability", required=True)
    p.add_argument("--coverage-out", required=True, help="coverage-map.json（含 _meta）")
    p.add_argument("--out", required=True, help="coverage-reweigh.json（StepEnvelope）")
    a = p.parse_args()

    try:
        repo_root = find_repo_root()
    except RuntimeError:
        repo_root = None
    sys.path.insert(0, _rag_root(repo_root))
    from tools.gapmap.coverage_map import CoverageMapError, build_coverage_map, _load_json  # noqa: E402

    ans = _load_json(a.answerability)
    if (ans.get("payload") or {}).get("needs_rubric_revision") is True:
        print("[reweigh] ⛔ answerability.needs_rubric_revision=true——一致率未達門檻，⛔ 不重量；回主 session 回修 rubric（E6）", file=sys.stderr)
        return 2

    try:
        cm = build_coverage_map(a.canon, a.demand, a.map, a.answerability)
    except CoverageMapError as e:
        print(f"[reweigh] ⛔ {e}", file=sys.stderr)
        return 2

    write_json(a.coverage_out, cm)
    meta = cm["_meta"]
    envelope = make_envelope(
        step="reweigh", skill_version=SKILL_VERSION, inputs_sha=dict(meta["inputs_sha"]), deterministic=True,
        payload={"cells": cm["cells"]},
        raw_outputs_path=os.path.relpath(os.path.abspath(a.coverage_out), repo_root) if repo_root else a.coverage_out,
        cost={"agents": 0, "prompt_tokens": 0, "completion_tokens": 0, "usd": 0.0, "wall_s": 0.0},
    )
    validate(envelope, load_schema(_SCHEMA_PATH))
    write_json(a.out, envelope)

    without = int(meta["summary"]["cells_without_disposition"])
    needs_audit = sum(1 for c in cm["cells"] if c.get("disposition") in ("not_available", "owner_decision"))
    no_src = len(meta["fines_without_sources"])
    if repo_root:
        update_state(repo_root, {"reweigh": {
            "path": os.path.relpath(os.path.abspath(a.out), repo_root),
            "cells_without_disposition": without,
            "fines_without_sources": no_src,
            "needs_source_audit": needs_audit,
        }})
    s = meta["summary"]
    print(f"[reweigh] total={s['total']} by_disposition={s['by_disposition']} by_fix_type={s['by_fix_type']} "
          f"gap={s['gap_classes']} agreement={s['judge_agreement_global']} fines_without_sources={no_src}")
    if without or no_src:
        print("[reweigh] ⛔ 出口未達：無去向格或無來源細目 >0", file=sys.stderr)
        return 2
    if needs_audit:
        print(f"[reweigh] ⚠️ {needs_audit} 格 not_available／owner_decision ⇒ 先走步 5b source_audit.py（權威來源核對），⛔ 不得直接交業主", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
