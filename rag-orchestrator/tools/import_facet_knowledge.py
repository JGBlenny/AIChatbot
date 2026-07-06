#!/usr/bin/env python3
"""知識批次匯入工具（部署重放依賴——runbook §1.3/§2 引用，非一次性）。

來源：批次 JSON（預設合約面向批次；可帶路徑參數指定，如 scripts/audit/reports/*-import.json）
行為：
  - updates：修正既有知識 answer（重算 embedding）
  - knowledge：INSERT 新知識（含 embedding；冪等：question_summary 已存在則跳過）
  - anchors：INSERT 錨點列（answer 空、掛面向、含 embedding）
匯入後請執行：reranker semantic model 重建＋清系統脈絡/設定快取（tasks 6.3）。

用法：python3 rag-orchestrator/tools/import_facet_knowledge.py [--dry-run]
需求：本機 aichatbot-postgres（5432 對外）與 embedding-api（5001 對外）。
"""
import asyncio
import json
import os
import sys
import urllib.request

_args = [a for a in sys.argv[1:] if not a.startswith("--")]
BATCH = _args[0] if _args else os.path.join(
    os.path.dirname(__file__), "..", "..",
    ".kiro", "specs", "contract-conversational-facets", "knowledge-batch.json")
EMB_URL = os.getenv("EMBEDDING_API_URL", "http://localhost:5001/api/v1/embeddings")
DRY = "--dry-run" in sys.argv


def get_embedding(text: str):
    req = urllib.request.Request(EMB_URL, data=json.dumps({"text": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        emb = json.loads(r.read())["embedding"]
    assert len(emb) == 1536, f"embedding 維度異常：{len(emb)}"
    return "[" + ",".join(f"{v:.8f}" for v in emb) + "]"


async def main():
    import asyncpg
    d = json.load(open(BATCH, encoding="utf-8"))
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"), min_size=1, max_size=2)

    n_upd = n_new = n_anchor = n_skip = 0
    async with pool.acquire() as conn:
        # 1) 既有知識修正（answer 變 → 重算 embedding，embedding 以 question_summary 為準不動？
        #    本庫 embedding 基於 question_summary（feedback_embedding_integrity），answer 修正不影響向量 → 只改 answer）
        for u in d.get("updates", []):
            row = await conn.fetchrow("SELECT id, question_summary FROM knowledge_base WHERE id=$1", u["id"])
            if not row:
                print(f"  ⚠️ UPDATE 目標 id={u['id']} 不存在，跳過")
                continue
            print(f"  ✏️ UPDATE {u['id']} {row['question_summary'][:30]}")
            if not DRY:
                await conn.execute(
                    "UPDATE knowledge_base SET answer=$2, updated_at=now(), updated_by='import_script' WHERE id=$1",
                    u["id"], u["answer"])
            n_upd += 1

        # 2) 新知識
        for k in d.get("knowledge", []):
            exists = await conn.fetchval(
                "SELECT id FROM knowledge_base WHERE question_summary=$1", k["question"])
            if exists:
                print(f"  ⏭️ 已存在（id={exists}）：{k['question']}")
                n_skip += 1
                continue
            print(f"  ＋ [{k.get('facet','單發')}] {k['question']}" + ("（掛面向）" if k.get("categories") else ""))
            if not DRY:
                emb = get_embedding(k["question"])
                await conn.execute(
                    "INSERT INTO knowledge_base (question_summary, answer, categories, target_user, "
                    " business_types, keywords, scope, priority, is_active, source_type, created_by, embedding) "
                    "VALUES ($1,$2,$3,$4,$5,$6,'global',0,TRUE,'manual','import_script',$7::vector)",
                    k["question"], k["answer"],
                    k.get("categories"), k["target_user"], ["system_provider"], k.get("keywords"), emb)
            n_new += 1

        # 3) 錨點（answer 空、掛面向）
        for a in d.get("anchors", []):
            exists = await conn.fetchval(
                "SELECT id FROM knowledge_base WHERE question_summary=$1", a["question"])
            if exists:
                print(f"  ⏭️ 錨點已存在（id={exists}）：{a['question']}")
                n_skip += 1
                continue
            print(f"  ⚓ [{a['facet']}] {a['question']}")
            if not DRY:
                emb = get_embedding(a["question"])
                await conn.execute(
                    "INSERT INTO knowledge_base (question_summary, answer, categories, target_user, "
                    " business_types, keywords, scope, priority, is_active, source_type, created_by, embedding) "
                    "VALUES ($1,'',$2,$3,$4,$5,'global',0,TRUE,'manual','import_script',$6::vector)",
                    a["question"], [a["facet"]], ["property_manager"], ["system_provider"],
                    a.get("keywords"), emb)
            n_anchor += 1

    await pool.close()
    mode = "（dry-run，未寫入）" if DRY else ""
    print(f"完成{mode}：修正 {n_upd}、新知識 {n_new}、錨點 {n_anchor}、跳過 {n_skip}")
    if not DRY:
        print("⚠️ 後續：reranker semantic model 重建＋清快取（tasks 6.3），否則排序不含新知識")


if __name__ == "__main__":
    asyncio.run(main())
