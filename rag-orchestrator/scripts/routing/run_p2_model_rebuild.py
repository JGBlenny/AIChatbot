#!/usr/bin/env python3
"""P2 `semantic_model_rebuild` ×1（任務 5.2｜protocol v1 已凍結）。

⚠️ **本檔只做量測**：容器重建須在 host 上執行（容器內沒有 docker socket），
重建前後的 `container`／`image` 身分由呼叫端以參數帶入並寫進 evidence。

判定分兩欄，**不得混為一談**（業主 2026-08-24 裁示）：

```text
P2 protocol validity  ：容器確實 force-recreate（container id 前後不同）→ 依 frozen v1 為 VALID
P2 perturbation strength：image digest 前後相同 → LIMITED（近乎 no-op）
支持的主張  ：robust to service recreation
不支持的主張：robust to a different semantic model version
```

⚠️ 即使 image 相同也**不得**事後宣布 P2 無效而從分母刪掉——那是改凍結規則。
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/services")
from scripts.routing.run_protocol_v1 import authorize, observe, _conn_kwargs  # noqa: E402


async def main(args):
    import asyncpg
    from scripts.routing import protocol_v1 as ruler
    from services import conversational_config as cc
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

    protocol = ruler.load_protocol()
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    cc.reset_cache()
    retriever = VendorKnowledgeRetrieverV2()
    os.environ["INSTANCE_REFERENCE_GATE"] = "true"
    os.environ["PREENTRY_ROUTABILITY_GATE"] = "false"
    authorize()

    with open(args.baseline, encoding="utf-8") as f:
        baseline_run = json.load(f)
    baseline = {r["question"]: (r["kind"], r["facet"]) for r in baseline_run["scored_verdicts"]}

    cases = protocol["case_sets"]["RULE"]["cases"] + protocol["case_sets"]["INSTANCE"]["cases"]
    obs, flipped = [], []
    for q in cases:
        row = await observe(pool, retriever, q)
        got = (row["kind"], row["facet"])
        if got != baseline[q]:
            flipped.append(q)
        obs.append({"question": q, "baseline": list(baseline[q]), "observed": list(got),
                    "flipped": got != baseline[q], "gate_verdict": row["gate_verdict"],
                    "decision_margin": row["decision_margin"]})

    recreated = bool(args.container_before and args.container_after
                     and args.container_before != args.container_after)
    same_image = bool(args.image_before and args.image_after
                      and args.image_before == args.image_after)
    out = {
        "perturbation": {"id": "P2", "name": "semantic_model_rebuild", "rounds": 1},
        "host_execution": {
            "command": "docker compose -f docker-compose.prod.yml up -d --force-recreate semantic-model",
            "container_before": args.container_before, "container_after": args.container_after,
            "image_before": args.image_before, "image_after": args.image_after,
            "service_http_status": args.http_status,
        },
        "validity": {
            "protocol_validity": "VALID" if recreated else "INVALID（container id 未變＝未真的重建）",
            "perturbation_strength": "LIMITED（image/model artifact 未變）" if same_image
                                     else "image 已變動",
            "claim_supported": "robust to service recreation",
            "claim_not_supported": "robust to a different semantic model version/model rebuild",
        },
        "denominator_this_perturbation": 8,
        "flip_count": len(flipped), "flipped": flipped, "observations": obs,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(f"[P2] flips={len(flipped)}/8 validity={out['validity']['protocol_validity']} → {args.out}")
    await pool.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default="/.kiro/specs/routing-disambiguation/evidence/protocol-v1-baseline.json")
    ap.add_argument("--out", default="/app/protocol_v1_p2.json")
    ap.add_argument("--container-before", default="")
    ap.add_argument("--container-after", default="")
    ap.add_argument("--image-before", default="")
    ap.add_argument("--image-after", default="")
    ap.add_argument("--http-status", default="")
    asyncio.run(main(ap.parse_args()))
