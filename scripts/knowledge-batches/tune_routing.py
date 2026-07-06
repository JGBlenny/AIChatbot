"""一次性調校（不 commit）：進場路由 4 紅案資料側修正。"""
import asyncio, json, os, urllib.request

EMB_URL = os.getenv("EMBEDDING_API_URL", "http://embedding-api:5000/api/v1/embeddings")

def emb(text):
    req = urllib.request.Request(EMB_URL, data=json.dumps({"text": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    e = json.loads(urllib.request.urlopen(req, timeout=60).read())["embedding"]
    assert len(e) == 1536
    return "[" + ",".join(f"{v:.8f}" for v in e) + "]"

async def main():
    import asyncpg
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "postgres"), port=5432,
        user="aichatbot", password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database="aichatbot_admin")

    # A. 3388 回退補標（制度 yes/no 題維持單發；錨點已覆蓋模糊進場）
    await conn.execute(
        "UPDATE knowledge_base SET categories = array_remove(categories, '續約'), updated_at=now() "
        "WHERE id=3388 AND categories @> ARRAY['續約']::text[]")
    print("A. 3388 untag 續約 ✓")

    # C. 3402 question 補「自動產生」重嵌
    q3402 = "點退帳單 自動產生 費用結算"
    await conn.execute(
        "UPDATE knowledge_base SET question_summary=$1, embedding=$2::vector, updated_at=now() WHERE id=3402",
        q3402, emb(q3402))
    print("C. 3402 措辭+重嵌 ✓")

    # D. 3530 question 補「多筆一起續 怎麼操作」語彙重嵌
    q3530 = "批次續約 多筆合約一起續 快速日期設定"
    await conn.execute(
        "UPDATE knowledge_base SET question_summary=$1, embedding=$2::vector, updated_at=now() WHERE id=3530",
        q3530, emb(q3530))
    print("D. 3530 措辭+重嵌 ✓")

    # B. 補知識：點交後下一步（缺口）
    q = "租客同意點交後 下一步 水電基準"
    a = ("租客同意點交後，合約就進入「已點交（執行中）」，點交這一步已經完成，不需要再送出什麼。"
         "點交當下抄錄的水電度數，會作為之後帳單的計算基準；帳單依合約週期自動產生，"
         "與點交與否無關（未點交也會照常發送帳單）。接下來就是日常管理——收租對帳、修繕處理；"
         "合約到期前 30 天起，再依情況走續約或發送點退。")
    exists = await conn.fetchval("SELECT id FROM knowledge_base WHERE question_summary=$1", q)
    if not exists:
        await conn.execute(
            "INSERT INTO knowledge_base (question_summary, answer, categories, target_user, business_types, "
            " keywords, scope, priority, is_active, source_type, created_by, embedding) "
            "VALUES ($1,$2,NULL,$3,$4,$5,'global',5,TRUE,'manual','import_script',$6::vector)",
            q, a, ["property_manager"], ["system_provider"], ["點交完成", "下一步"], emb(q))
        print("B. 新知識（點交後下一步）✓")
    else:
        print(f"B. 已存在 id={exists}")
    await conn.close()

asyncio.run(main())
