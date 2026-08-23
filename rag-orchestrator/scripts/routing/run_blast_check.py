#!/usr/bin/env python3
"""5.4 blast radius 實測（**須在 adjudication freeze 之後執行**）。

讀取**已凍結**的 expectation（`task-5-4-frozen-expectations.json`）比對實測。

⚠️ 分母是 **6**（ADJUDICATED），不是 7：
`#6 我要查帳單 編號 12345` 無產品 expectation，**只記 observation、不計 PASS／FAIL**。
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/services")
from scripts.routing.run_protocol_v1 import authorize, observe, _conn_kwargs  # noqa: E402

FROZEN = "/.kiro/specs/routing-disambiguation/evidence/task-5-4-frozen-expectations.json"


async def main(args):
    import asyncpg
    from services import conversational_config as cc
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

    with open(args.frozen, encoding="utf-8") as f:
        frozen = json.load(f)

    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    cc.reset_cache()
    retriever = VendorKnowledgeRetrieverV2()
    os.environ["INSTANCE_REFERENCE_GATE"] = "true"
    os.environ["PREENTRY_ROUTABILITY_GATE"] = "false"
    authorize()

    rows, passed, scored = [], 0, 0
    for case in frozen["cases"]:
        row = await observe(pool, retriever, case["question"])
        actual = "single" if row["kind"] == "single" else f"dialog:{row['facet']}"
        rec = {"n": case["n"], "question": case["question"], "status": case["status"],
               "expected": case["expected"], "actual": actual,
               "gate_verdict": row["gate_verdict"], "decision_margin": row["decision_margin"]}
        if case["status"] == "ADJUDICATED":
            scored += 1
            rec["verdict"] = "pass" if actual == case["expected"] else "fail"
            passed += rec["verdict"] == "pass"
        else:
            rec["verdict"] = "unscored"      # ⚠️ 無產品 expectation → 無 PASS 可言
        rows.append(rec)

    out = {"task": "5.4 blast radius measurement",
           "frozen_expectations_source": args.frozen,
           "freeze_commit": args.freeze_commit,
           "authorization": "synthetic matching PASS（production manifest 仍 not_run）",
           "adjudicated_regression": f"{passed}/{scored}",
           "observation_recorded": f"{len(rows)}/{len(frozen['cases'])}",
           "reporting_rule": frozen["reporting_rule"],
           "results": rows}
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(f"[5.4] adjudicated regression={passed}/{scored}｜observation={len(rows)}/7 → {args.out}")
    await pool.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--frozen", default=FROZEN)
    ap.add_argument("--out", default="/app/task_5_4_measurement.json")
    ap.add_argument("--freeze-commit", default="")
    asyncio.run(main(ap.parse_args()))
