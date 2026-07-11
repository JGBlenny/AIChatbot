#!/usr/bin/env python3
"""conversational-repair 任務 3.3：修繕面向知識 seeds（產出②③，部署重放依賴）。

兩類新知識列（均走既有 embedding 生成路徑——question_summary 進 embedding-api，
不加前綴、不混 keywords，符合 embedding 完整性鐵則）：

  ② 修繕意圖錨點（進場觸發）：answer 空、掛 categories={修繕報修}、vendor_ids 空（全業者）、
     target_user={tenant}、action_type='direct_answer'。question 用主題關鍵字式（短主題詞，
     非完整問句）。命中後 _diagnosis_config_for_knowledge 以 categories→config_for_category
     路由進修繕面向；_drop_empty_answer_rows 於「當回答」前濾除空 answer 錨點（只作進場判定）。

  ③ 查進度（R5.1/5.2）：真 answer ＋ action_type='api_call'＋api_config→jgb_repairs
     （params={role_id:{session.role_id}, user_id:{session.user_id}}，以身份查工單）；
     掛 categories={修繕報修}（同域，但因帶 answer/api_call 不被濾除）。

冪等：以 question_summary 唯一識別，已存在則跳過（不覆寫既有 embedding/answer）。
用法：python3 rag-orchestrator/tools/seed_repair_facet_knowledge.py [--dry-run]
前置：本機 aichatbot-postgres（5432 對外）＋ embedding-api（5001 對外）。
套用後：reranker semantic model 重建＋清系統脈絡/設定快取（否則排序不含新知識）。
"""
import asyncio
import json
import os
import sys
import urllib.request

DRY = "--dry-run" in sys.argv
EMB_URL = os.getenv("EMBEDDING_API_URL", "http://localhost:5001/api/v1/embeddings")

FACET_CATEGORY = "修繕報修"

# ② 意圖錨點（主題關鍵字式；覆蓋常見報修說法：泛報修/漏水/不通堵塞/電器故障）
# 關鍵字精簡（每列聚焦一主題）以維持向量分數——過多雜項會稀釋 cosine，
# 使常見問法（冷氣壞了/我要報修/馬桶不通）掉到觸發門檻 0.75 以下（煙囪實測調校）。
ANCHORS = [
    "報修 修繕 東西壞了 想報修",
    "漏水 滲水 天花板漏水 水管漏水",
    "馬桶不通 排水堵塞 水管堵住",
    "冷氣壞了 電器壞了 家電故障",
]

# 已被上表取代的舊錨點（前一版本 seed 過的措辭）——冪等重放時一併除役，
# 避免 DB 殘留稀釋版錨點與新版並存。
SUPERSEDED_ANCHORS = [
    "漏水 滲水 水管 天花板在滴水",
    "冷氣不冷 電器故障 沒電 燈不亮",
]

# ③ 查進度（api_call → jgb_repairs，以身份查工單）
PROGRESS = {
    "question": "修繕進度 報修單 修得怎樣了 處理到哪",
    "answer": (
        "為您查詢名下的報修單處理進度；若目前沒有任何報修單，代表尚未提出報修——"
        "需要的話跟我說「我要報修」，我可以直接協助您建單。"
    ),
    "api_config": {
        "endpoint": "jgb_repairs",
        "params": {"role_id": "{session.role_id}", "user_id": "{session.user_id}"},
        "combine_with_knowledge": False,
    },
}


def get_embedding(text: str) -> str:
    req = urllib.request.Request(
        EMB_URL, data=json.dumps({"text": text}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        emb = json.loads(r.read())["embedding"]
    assert len(emb) == 1536, f"embedding 維度異常：{len(emb)}"
    return "[" + ",".join(f"{v:.8f}" for v in emb) + "]"


async def main() -> None:
    import asyncpg
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"), min_size=1, max_size=2)

    n_anchor = n_api = n_skip = n_retire = 0
    async with pool.acquire() as conn:
        # 除役被取代的舊錨點（僅限本 seed 建立者，且 answer 空的進場錨點——不誤刪他人資料）
        for old in SUPERSEDED_ANCHORS:
            row = await conn.fetchrow(
                "SELECT id FROM knowledge_base WHERE question_summary=$1 "
                "AND created_by='seed_repair_facet' AND (answer='' OR answer IS NULL)", old)
            if row:
                print(f"  🗑️ 除役舊錨點（id={row['id']}）：{old}")
                if not DRY:
                    await conn.execute("DELETE FROM knowledge_base WHERE id=$1", row["id"])
                n_retire += 1

        # ② 錨點
        for q in ANCHORS:
            exists = await conn.fetchval(
                "SELECT id FROM knowledge_base WHERE question_summary=$1", q)
            if exists:
                print(f"  ⏭️ 錨點已存在（id={exists}）：{q}")
                n_skip += 1
                continue
            print(f"  ⚓ [修繕錨點] {q}")
            if not DRY:
                emb = get_embedding(q)
                await conn.execute(
                    "INSERT INTO knowledge_base (question_summary, answer, category, categories, "
                    " target_user, business_types, vendor_ids, scope, priority, is_active, "
                    " action_type, source, created_by, embedding) "
                    "VALUES ($1,'',NULL,$2,$3,NULL,ARRAY[]::integer[],'global',0,TRUE,"
                    " 'direct_answer','manual','seed_repair_facet',$4::vector)",
                    q, [FACET_CATEGORY], ["tenant"], emb)
            n_anchor += 1

        # ③ 查進度（api_call）
        q = PROGRESS["question"]
        exists = await conn.fetchval(
            "SELECT id FROM knowledge_base WHERE question_summary=$1", q)
        if exists:
            print(f"  ⏭️ 查進度已存在（id={exists}）：{q}")
            n_skip += 1
        else:
            print(f"  🔌 [修繕查進度 api_call→jgb_repairs] {q}")
            if not DRY:
                emb = get_embedding(q)
                await conn.execute(
                    "INSERT INTO knowledge_base (question_summary, answer, category, categories, "
                    " target_user, business_types, vendor_ids, scope, priority, is_active, "
                    " action_type, api_config, source, created_by, embedding) "
                    "VALUES ($1,$2,NULL,$3,$4,NULL,ARRAY[]::integer[],'global',0,TRUE,"
                    " 'api_call',$5::jsonb,'manual','seed_repair_facet',$6::vector)",
                    q, PROGRESS["answer"], [FACET_CATEGORY], ["tenant"],
                    json.dumps(PROGRESS["api_config"]), emb)
            n_api += 1

    await pool.close()
    mode = "（dry-run，未寫入）" if DRY else ""
    print(f"完成{mode}：錨點 {n_anchor}、查進度 {n_api}、跳過 {n_skip}、除役 {n_retire}")
    if not DRY:
        print("⚠️ 後續：reranker semantic model 重建＋清快取，否則排序不含新知識")


if __name__ == "__main__":
    asyncio.run(main())
