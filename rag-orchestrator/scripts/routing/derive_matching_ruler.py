#!/usr/bin/env python3
"""依**已凍結**的六項前提導出 matching ruler（routing-authority-model）。

⚠️ 本檔**只算量尺**：不讀任何 applicability label、不輸出配對候選、
   不輸出「哪些 utterance 適合配對」、不試不同 tolerance。
⚠️ 統計量與演算法皆取自 `matching-ruler-premises.md`（commit 3bcfb94），**此處不得更改**。
"""
import argparse, asyncio, json, os, statistics, sys
sys.path.insert(0, "/app"); sys.path.insert(0, "/app/services")
from scripts.routing.run_protocol_v1 import _conn_kwargs  # noqa: E402
from routers.chat import _drop_empty_answer_rows          # noqa: E402

V1 = "/.kiro/specs/routing-disambiguation/evidence/task-6-holdout-utterances.json"
PROTO = "/.kiro/specs/routing-disambiguation/robustness-protocol.json"
VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))


async def main(out):
    import asyncpg
    from services.decision_layer import DecisionConfig
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

    # ── ① source population（僅取 utterance 字串；**不讀 labels**）──
    pool_utts = list(json.load(open(V1, encoding="utf-8"))["utterances"])
    proto = json.load(open(PROTO, encoding="utf-8"))["case_sets"]
    for name in ("RULE", "INSTANCE", "CONTROL", "BLAST", "UNDECIDED"):
        pool_utts += proto[name]["cases"]
    seen, population = set(), []
    for u in pool_utts:
        if u not in seen:
            seen.add(u); population.append(u)

    db = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    cfg = DecisionConfig.load()
    retriever = VendorKnowledgeRetrieverV2()

    gaps, no_gap = [], 0
    for u in population:
        rows = await retriever.retrieve_knowledge_hybrid(
            query=u, vendor_id=VENDOR_ID, top_k=5, similarity_threshold=cfg.kb_threshold,
            target_user="property_manager", mode="b2b")
        rows = _drop_empty_answer_rows(rows)          # ③ 前處理：複刻 production
        if len(rows) < 2:
            no_gap += 1
            continue
        gaps.append(round(abs(float(rows[0]["similarity"]) - float(rows[1]["similarity"])), 6))

    gaps_sorted = sorted(gaps)
    tolerance = round(statistics.median(gaps_sorted), 6)   # ④ 單一統計量：中位數
    q = lambda p: round(gaps_sorted[min(len(gaps_sorted) - 1, int(p * len(gaps_sorted)))], 6)
    out_obj = {
        "task": "matching ruler derivation（依 premises commit 3bcfb94）",
        "premises_commit": "3bcfb94",
        "label_blind": True,
        "outputs_withheld": ["配對候選", "適合配對的 utterance", "applicability labels",
                             "candidate/member outputs", "實際 opposite-pair 數"],
        "population": {"utterances_total": len(population),
                       "with_gap": len(gaps), "excluded_lt2_rows": no_gap,
                       "sources": ["v1 holdout utterances（僅取分數）", "protocol v1 case sets"]},
        "score_field": "similarity（production final score）",
        "matching_statistic": "g = |similarity(rank1) − similarity(rank2)|，後處理後 ≥2 列者",
        "descriptive_statistics": {
            "n": len(gaps), "min": gaps_sorted[0], "max": gaps_sorted[-1],
            "mean": round(statistics.mean(gaps), 6), "median": tolerance,
            "stdev": round(statistics.stdev(gaps), 6) if len(gaps) > 1 else None,
            "p10": q(0.10), "p25": q(0.25), "p75": q(0.75), "p90": q(0.90),
        },
        "derivation_algorithm": "tolerance = median(g)（事前指定，無備選）",
        "TOLERANCE": tolerance,
        "matching_rule": {
            "same_routing_category": True,
            "same_relevant_face_responsibility_context": True,
            "score_proximity": f"abs(score_a - score_b) <= {tolerance}",
            "opposite_ground_truth_applicability": True,
        },
        "minimum_required_pairs": 20,
        "insufficient_consequence": "實配 < 20 → INSUFFICIENT_EVIDENCE；不得放寬 tolerance／換統計量／擴 population",
    }
    with open(out, "w", encoding="utf-8") as f:
        f.write(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n")
    d = out_obj["descriptive_statistics"]
    print(f"[ruler] n={d['n']}（排除 <2 列 {no_gap}）｜median={d['median']}｜"
          f"p25={d['p25']} p75={d['p75']}｜TOLERANCE={tolerance}")
    await db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="/app/matching_ruler.json")
    asyncio.run(main(ap.parse_args().out))
