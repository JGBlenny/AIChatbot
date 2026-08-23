#!/usr/bin/env python3
"""凍結 `query × top-k KB` pair（routing-authority-model Q2｜offline replay 第 1 步）。

⚠️ 本檔**只做檢索**，不呼叫 gate、不做任何 applicability 判定。
⚠️ 取的欄位**與 gate 實際看到的完全一致**：`question_summary` ＋ `answer[:180]`
   （見 `routers/chat.py` 的 gate user message 組法）——多給或少給都會讓 replay 失真。
"""
import argparse, asyncio, json, os, sys
sys.path.insert(0, "/app"); sys.path.insert(0, "/app/services")
from scripts.routing.run_protocol_v1 import _conn_kwargs  # noqa: E402

SRC = "/.kiro/specs/routing-disambiguation/evidence/task-6-holdout-utterances.json"
VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))
TARGET_USER, MODE, TOP_K = "property_manager", "b2b", 5
MAX_CHECKS = 2          # 與 `_top1_relevance_gate` 的 max_checks 一致


async def main(out):
    import asyncpg
    from services.decision_layer import DecisionConfig
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

    src = json.load(open(SRC, encoding="utf-8"))
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    cfg = DecisionConfig.load()
    retriever = VendorKnowledgeRetrieverV2()

    pairs, no_hit = [], []
    for i, q in enumerate(src["utterances"], start=1):
        rows = await retriever.retrieve_knowledge_hybrid(
            query=q, vendor_id=VENDOR_ID, top_k=TOP_K,
            similarity_threshold=cfg.kb_threshold, target_user=TARGET_USER, mode=MODE)
        if not rows:
            no_hit.append({"n": i, "utterance": q})
            continue
        for rank, r in enumerate(rows[:MAX_CHECKS], start=1):
            pairs.append({
                "pair_id": f"{i}-{rank}", "n": i, "rank": rank, "utterance": q,
                "kb_id": r.get("id"),
                "kb_question_summary": r.get("question_summary") or "",
                "kb_answer_excerpt": (r.get("answer") or "")[:180],
                "similarity": round(float(r.get("similarity", 0)), 4),
                "action_type": r.get("action_type"), "form_id": r.get("form_id"),
            })
    out_obj = {
        "task": "Q2 offline replay — step 1: freeze query × KB pairs",
        "source_utterances": {"file": SRC, "digest": src["utterance_dataset_digest"],
                              "note": "v1 holdout，已 BURNED；本用途為 failure analysis／signal 研究，允許"},
        "retrieval_conditions": {
            "top_k": TOP_K, "max_checks_mirrored": MAX_CHECKS,
            "target_user": TARGET_USER, "mode": MODE, "vendor_id": VENDOR_ID,
            "kb_threshold": cfg.kb_threshold, "form_trigger_threshold": cfg.form_trigger_threshold,
            "decision_config_hash": cfg.config_hash(),
        },
        "fields_note": "kb_answer_excerpt 取 answer[:180]，與 gate 實際輸入完全一致",
        "pair_count": len(pairs), "no_hit_count": len(no_hit), "no_hit": no_hit,
        "labels": "NOT YET LABELLED", "gate_replayed": False,
        "pairs": pairs,
    }
    with open(out, "w", encoding="utf-8") as f:
        f.write(json.dumps(out_obj, ensure_ascii=False, indent=2) + "\n")
    print(f"[pairs] {len(pairs)} pairs from {len(src['utterances'])} utterances"
          f"（no-hit {len(no_hit)}）→ {out}")
    await pool.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="/app/gate_pairs.json")
    asyncio.run(main(ap.parse_args().out))
