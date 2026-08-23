#!/usr/bin/env python3
"""protocol v1 擾動量測（任務 5.2｜R3.2, R3.3）。

依 **v1 已凍結**的擾動定義執行，**不得因結果不佳回頭調 protocol 或 regex**。

```text
P1 corpus_add_sibling      ×3   自 exposure surface 取 5 筆，加同義變體並補嵌
P2 semantic_model_rebuild  ×1   重建 semantic-model 後重跑
P3 phrasing_variant        ×1   RULE／INSTANCE 各案 2 個保義變體（人撰寫，非 LLM 量產）
```

門檻：`flip_rate ≤ 1/8` 且**不得有任一筆在多輪間反覆翻面**。

⚠️ P3 的分母取**嚴格讀法**：protocol 定 8（RULE∪INSTANCE），而每案有 2 個變體，
故**一案只要任一變體翻面即計為該案翻面**（保守，不因平均而稀釋）。
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/services")
from scripts.routing.run_protocol_v1 import authorize, observe, _conn_kwargs  # noqa: E402

#: P3：保義變體（**人撰寫**；每案 2 個，語義不得改變、類型不得改變）
PHRASING_VARIANTS = {
    "點退帳單的金額是怎麼算的": ["點退帳單金額的計算方式是什麼", "點退的帳單金額怎麼計算出來"],
    "點退做完後，帳單會自動出來嗎？": ["做完點退之後帳單會自動產生嗎", "點退完成後系統會自動開帳單嗎"],
    "收據 PDF 在哪裡下載": ["收據的 PDF 檔要去哪裡下載", "哪裡可以下載收據 PDF"],
    "系統怎麼算點退帳單的金額": ["系統是如何計算點退帳單金額的", "點退帳單的金額系統怎麼計算"],
    "我的這張點退帳單金額怎麼算出來的": ["我這張點退帳單的金額是怎麼算出來的", "我的這筆點退帳單金額怎麼來的"],
    "我這筆點退帳單怎麼會是這個數字": ["我這張點退帳單為什麼是這個金額", "我的這筆點退帳單數字怎麼會這樣"],
    "幫我查點退帳單金額": ["幫我查一下我的點退帳單金額", "請幫我查詢點退帳單的金額"],
    "這張帳單的收據金額多少": ["這筆帳單的收據金額是多少", "我這張帳單收據金額多少錢"],
}


async def main(out_path):
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

    base_cases = protocol["case_sets"]["RULE"]["cases"] + protocol["case_sets"]["INSTANCE"]["cases"]
    baseline = {}
    for q in base_cases:
        row = await observe(pool, retriever, q)
        baseline[q] = (row["kind"], row["facet"])

    rows, flipped_cases = [], set()
    for base_q in base_cases:
        for variant in PHRASING_VARIANTS[base_q]:
            row = await observe(pool, retriever, variant)
            got = (row["kind"], row["facet"])
            flipped = got != baseline[base_q]
            if flipped:
                flipped_cases.add(base_q)
            rows.append({"base": base_q, "variant": variant, "baseline": list(baseline[base_q]),
                         "observed": list(got), "flipped": flipped,
                         "gate_verdict": row["gate_verdict"], "gate_reason": row["gate_reason"]})

    out = {
        "perturbation": {"id": "P3", "name": "phrasing_variant", "rounds": 1,
                         "authoring": "人撰寫（非 LLM 量產）——R7.3"},
        "denominator": {"cases": len(base_cases), "variants": len(rows),
                        "rule": "一案只要任一變體翻面即計為該案翻面（嚴格讀法）"},
        "baseline": {q: list(v) for q, v in baseline.items()},
        "flip_count": len(flipped_cases),
        "flip_rate": f"{len(flipped_cases)}/{len(base_cases)}",
        "threshold": "≤ 1/8",
        "passed": len(flipped_cases) * 8 <= len(base_cases),
        "flipped_cases": sorted(flipped_cases),
        "observations": rows,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(f"[P3] flip={out['flip_rate']} passed={out['passed']} → {out_path}")
    await pool.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/protocol_v1_p3.json")
    asyncio.run(main(ap.parse_args().out))
