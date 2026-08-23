#!/usr/bin/env python3
"""P1 `corpus_add_sibling` ×3（任務 5.2｜protocol v1 已凍結）。

凍結定義：**自 exposure surface（144 筆共居 KB）隨機取 5 筆，
複製其 question_summary 加入一筆同義變體並補嵌**；seed 於執行時記錄，凍結後不得更換。

exposure surface 判準取自 gap-analysis 的**結構條件**（實查定義，非本檔發明）：

```text
is_active  AND  answer 非空（＝Knowledge Evidence）
           AND  掛有面向分類（＝Routing Hint）
```

⚠️ **選樣不得因已看過 P3 結果而挑有利／不利的 5 筆**：
以固定 seed 對**排序後的 id 全集**取樣，seed 與被選 id 一併寫進 evidence。

⚠️ 每輪結束**一定刪除**本輪插入的列（`finally`），語料回到基準狀態。
"""
import argparse
import asyncio
import json
import os
import random
import sys
import urllib.request

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/services")
from scripts.routing.run_protocol_v1 import authorize, observe, _conn_kwargs  # noqa: E402

EMB_URL = os.getenv("EMBEDDING_API_URL", "http://embedding-api:5001/api/v1/embeddings")
SEEDS = [20260824001, 20260824002, 20260824003]
SIBLING_TAG = "（P1-sibling）"

#: 決定性同義替換表（**非 LLM**）；皆為保義改寫
SYNONYMS = [("怎麼", "如何"), ("為什麼", "為何"), ("要怎樣", "該如何"), ("可以", "能不能"),
            ("哪裡", "何處"), ("多少", "多少錢"), ("設定", "設置"), ("流程", "步驟")]


def sibling_text(summary: str) -> str:
    for a, b in SYNONYMS:
        if a in summary:
            return summary.replace(a, b, 1)
    return summary + " 說明"          # 無可替換者：加同義補語，仍為近義兄弟句


def embed(text: str):
    req = urllib.request.Request(EMB_URL, data=json.dumps({"text": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        emb = json.loads(r.read())["embedding"]
    assert len(emb) == 1536, f"embedding 維度異常：{len(emb)}"
    return "[" + ",".join(str(x) for x in emb) + "]"


async def main(out_path):
    import asyncpg
    from scripts.routing import protocol_v1 as ruler
    from services import conversational_config as cc
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

    protocol = ruler.load_protocol()
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=3)
    cc.reset_cache()
    await cc._load(pool)
    face_categories = [c for c in (cc._cache.get("by_category") or {}) if c]
    retriever = VendorKnowledgeRetrieverV2()
    os.environ["INSTANCE_REFERENCE_GATE"] = "true"
    os.environ["PREENTRY_ROUTABILITY_GATE"] = "false"
    authorize()

    cases = protocol["case_sets"]["RULE"]["cases"] + protocol["case_sets"]["INSTANCE"]["cases"]
    baseline = {}
    for q in cases:
        row = await observe(pool, retriever, q)
        baseline[q] = (row["kind"], row["facet"])

    async with pool.acquire() as conn:
        pop = await conn.fetch(
            "SELECT id, question_summary, answer, category, categories, target_user"
            " FROM knowledge_base WHERE is_active AND COALESCE(answer,'') <> ''"
            "   AND (categories && $1::text[] OR category = ANY($1::text[]))"
            " ORDER BY id", face_categories)
    population = [dict(r) for r in pop]
    rounds = []

    for idx, seed in enumerate(SEEDS, start=1):
        picked = random.Random(seed).sample(population, 5)
        inserted = []
        try:
            async with pool.acquire() as conn:
                for src in picked:
                    text = sibling_text(src["question_summary"]) + SIBLING_TAG
                    new_id = await conn.fetchval(
                        "INSERT INTO knowledge_base (question_summary, answer, category,"
                        " categories, target_user, is_active, embedding)"
                        " VALUES ($1,$2,$3,$4,$5,TRUE,$6::vector) RETURNING id",
                        text, src["answer"], src["category"], src["categories"],
                        src["target_user"], embed(text))
                    inserted.append({"new_id": new_id, "source_id": src["id"], "text": text})
            observations, flipped = [], []
            for q in cases:
                row = await observe(pool, retriever, q)
                got = (row["kind"], row["facet"])
                if got != baseline[q]:
                    flipped.append(q)
                observations.append({"question": q, "baseline": list(baseline[q]),
                                     "observed": list(got), "flipped": got != baseline[q],
                                     "gate_verdict": row["gate_verdict"]})
        finally:
            if inserted:
                async with pool.acquire() as conn:
                    await conn.execute("DELETE FROM knowledge_base WHERE id = ANY($1::int[])",
                                       [i["new_id"] for i in inserted])
        rounds.append({"round": idx, "seed": seed,
                       "inserted": inserted, "flip_count": len(flipped),
                       "flipped": flipped, "observations": observations})
        print(f"[P1 round {idx}] seed={seed} flips={len(flipped)}/8")

    out = {"perturbation": {"id": "P1", "name": "corpus_add_sibling", "rounds": len(SEEDS)},
           "exposure_surface": {"criteria": "is_active AND answer 非空 AND 掛面向分類",
                                "population_size": len(population),
                                "face_categories": sorted(face_categories)},
           "seeds": SEEDS, "baseline": {q: list(v) for q, v in baseline.items()},
           "total_flips": sum(r["flip_count"] for r in rounds),
           "denominator_this_perturbation": 8 * len(SEEDS),
           "rounds": rounds,
           "cleanup": "每輪 finally 刪除本輪插入列；語料回到基準"}
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(f"[P1] total flips={out['total_flips']}/{out['denominator_this_perturbation']} → {out_path}")
    await pool.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/protocol_v1_p1.json")
    asyncio.run(main(ap.parse_args().out))
