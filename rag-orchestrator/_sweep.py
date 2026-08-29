"""S1–S3 結構掃描：只跑 retrieval + nomination，**不跑 resolver**（零 LLM）。"""
import asyncio, json, os, collections

async def main():
    import asyncpg
    from routers.chat import _knowledge_category, _nominate_face_candidates, nomination_candidate_keys
    from services.decision_layer import DecisionConfig, facet_entry_eligible
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
    qs = json.load(open("_sweep_in.json"))
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST","postgres"), port=int(os.getenv("DB_PORT","5432")),
        user=os.getenv("DB_USER","aichatbot"), password=os.getenv("DB_PASSWORD","aichatbot_password"),
        database=os.getenv("DB_NAME","aichatbot_test"), min_size=1, max_size=3)
    cfgs = DecisionConfig.load(); r = VendorKnowledgeRetrieverV2()
    buckets = collections.Counter(); rows=[]
    for q in qs:
        hits = await r.retrieve_knowledge_hybrid(query=q, vendor_id=2, top_k=5,
                similarity_threshold=cfgs.kb_threshold, target_user="property_manager", mode="b2b")
        best = hits[0] if hits else None
        if best is None or not facet_entry_eligible(best, cfgs):
            cats = _knowledge_category(best) if best else []
            b = "S1_no_top1" if best is None else ("S1_below_threshold")
            buckets[b]+=1; rows.append({"q":q,"bucket":b,"cats":cats}); continue
        cats = _knowledge_category(best)
        if not cats:
            buckets["S2_top1_no_categories"]+=1; rows.append({"q":q,"bucket":"S2","cats":[]}); continue
        cands = nomination_candidate_keys(await _nominate_face_candidates(pool, best))
        b = "S3_categories_no_nomination" if not cands else "S4_S5_nominated"
        buckets[b]+=1; rows.append({"q":q,"bucket":b,"cats":cats,"cands":cands})
    print("BUCKETS=" + json.dumps(dict(buckets), ensure_ascii=False))
    json.dump(rows, open("_sweep_out.json","w"), ensure_ascii=False)
    await pool.close()
asyncio.run(main())
