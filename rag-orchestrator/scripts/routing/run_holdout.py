#!/usr/bin/env python3
"""Task 6：unseen holdout 實測（**candidate 首次接觸這批資料**）。

⚠️ 讀取的是**已凍結**的 utterances 與 blind labels；本檔不得修改任一。
⚠️ 分側報告：`rule/single` 與 `instance/dialog` 分開，**不得只給 aggregate**。
⚠️ route-level only 與 fully undecidable 只記 observation，**不併入核心成功率**。
"""
import argparse, asyncio, json, os, sys
sys.path.insert(0, "/app"); sys.path.insert(0, "/app/services")
from scripts.routing.run_protocol_v1 import authorize, observe, _conn_kwargs  # noqa: E402

E = "/.kiro/specs/routing-disambiguation/evidence/"


async def main(args):
    import asyncpg
    from services import conversational_config as cc
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

    labels = json.load(open(E + "task-6-holdout-labels.json", encoding="utf-8"))
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    cc.reset_cache()
    retriever = VendorKnowledgeRetrieverV2()
    os.environ["PREENTRY_ROUTABILITY_GATE"] = "false"
    m = authorize()

    rows = []
    for lab in labels["labels"]:
        q = lab["utterance"]
        os.environ["INSTANCE_REFERENCE_GATE"] = "true"
        on = await observe(pool, retriever, q)
        os.environ["INSTANCE_REFERENCE_GATE"] = "false"
        off = await observe(pool, retriever, q)
        actual_on = "single" if on["kind"] == "single" else f"dialog:{on['facet']}"
        actual_off = "single" if off["kind"] == "single" else f"dialog:{off['facet']}"
        rows.append({**{k: lab[k] for k in ("n", "utterance", "intent_class",
                                            "intended_route", "intended_facet", "confidence")},
                     "actual_route_gate_on": on["kind"], "actual_gate_on": actual_on,
                     "actual_gate_off": actual_off, "gate_verdict": on["gate_verdict"],
                     "gate_reason": on["gate_reason"], "top1": on.get("top1")})

    def facet_key_of(actual):
        if not actual.startswith("dialog:"):
            return None
        cat = actual.split(":", 1)[1]
        return {"條件診斷：帳單": "bill_diagnosis", "帳單異常": "billing_anomaly",
                "繳費金流排障": "billing_flow", "發票": "billing_invoice",
                "滯納金": "billing_late_fee", "帳單設定引導": "billing_setup_guide"}.get(cat, cat)

    exact = [r for r in rows if "undecidable" not in (r["intent_class"], r["intended_route"],
                                                      r["intended_facet"])]
    rule = [r for r in exact if r["intent_class"] == "rule"]
    inst = [r for r in exact if r["intent_class"] == "instance"]
    for r in rows:
        r["actual_facet_key"] = facet_key_of(r["actual_gate_on"])
    rule_ok = [r for r in rule if r["actual_route_gate_on"] == "single"]
    inst_route_ok = [r for r in inst if r["actual_route_gate_on"] == "dialog"]
    inst_facet_ok = [r for r in inst if r["actual_facet_key"] == r["intended_facet"]]
    overall_ok = rule_ok + inst_facet_ok

    out = {
      "task": "6 unseen holdout — candidate first contact",
      "frozen_inputs": {
        "utterance_dataset_digest": labels["utterance_dataset_digest"],
        "labels_digest": labels["labels_digest"],
        "ruleset_digest": m.current_manifest().digest,
        "ruleset_version": m.current_manifest().version,
        "protocol_digest": m.ACTIVE_PROTOCOL_DIGEST,
      },
      "authorization": "synthetic matching PASS（production manifest 仍 not_run）",
      "PRIMARY": {
        "exactly_judgeable": len(exact),
        "rule_accuracy": f"{len(rule_ok)}/{len(rule)}",
        "instance_route_accuracy": f"{len(inst_route_ok)}/{len(inst)}",
        "instance_exact_facet_accuracy": f"{len(inst_facet_ok)}/{len(inst)}",
        "overall_exact": f"{len(overall_ok)}/{len(exact)}",
      },
      "OBSERVATION_ONLY": {
        "route_level_only": [r for r in rows if r["intended_route"] != "undecidable"
                             and r["intended_facet"] == "undecidable"],
        "fully_undecidable": [r for r in rows if r["intended_route"] == "undecidable"],
        "note": "不得併入核心成功率",
      },
      "rule_side_failures": [r for r in rule if r not in rule_ok],
      "instance_side_failures": [r for r in inst if r not in inst_facet_ok],
      "all_rows": rows,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    p = out["PRIMARY"]
    print(f"[holdout] rule {p['rule_accuracy']}｜instance route {p['instance_route_accuracy']}"
          f"｜instance exact-facet {p['instance_exact_facet_accuracy']}｜overall {p['overall_exact']}")
    await pool.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/task_6_holdout.json")
    asyncio.run(main(ap.parse_args()))
