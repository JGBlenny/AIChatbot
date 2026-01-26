#!/usr/bin/env python3
"""檢查問題與 SOP 的向量相似度"""

import asyncio
import sys
import os
import psycopg2
import httpx

# 添加專案路徑
sys.path.insert(0, '/Users/lenny/jgb/AIChatbot/rag-orchestrator')

def get_db_connection():
    """連接資料庫"""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="aichatbot_admin",
        user="aichatbot",
        password="aichatbot_password"
    )

async def get_embedding(text: str):
    """取得文本 embedding"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:5001/api/v1/embeddings",
            json={"text": text}
        )
        data = response.json()
        return data.get("embedding")

async def check_similarity(question: str, sop_ids: list):
    """檢查問題與指定 SOP 的相似度"""

    # 獲取問題的向量
    question_embedding = await get_embedding(question)

    if not question_embedding:
        print(f"❌ 無法取得問題向量")
        return

    # 連接資料庫
    conn = get_db_connection()
    cursor = conn.cursor()

    # 查詢相似度（同時測試 primary 和 fallback）
    query = """
    SELECT
        id,
        item_name,
        1 - (primary_embedding <=> %s::vector) as primary_sim,
        1 - (fallback_embedding <=> %s::vector) as fallback_sim,
        GREATEST(
            1 - (primary_embedding <=> %s::vector),
            1 - (fallback_embedding <=> %s::vector)
        ) as max_sim
    FROM vendor_sop_items
    WHERE id = ANY(%s)
    ORDER BY max_sim DESC
    """

    cursor.execute(query, (question_embedding, question_embedding,
                           question_embedding, question_embedding, sop_ids))
    results = cursor.fetchall()

    print(f"\n問題: {question}")
    print(f"{'='*100}")
    print(f"{'ID':<8} {'SOP 名稱':<25} {'Primary':>10} {'Fallback':>10} {'最大值':>10} {'結果':>8}")
    print(f"{'-'*100}")

    for row in results:
        sop_id, item_name, primary_sim, fallback_sim, max_sim = row

        # 判斷哪個更好
        if fallback_sim > primary_sim:
            winner = "Fallback"
        elif primary_sim > fallback_sim:
            winner = "Primary"
        else:
            winner = "相同"

        status = "✅" if max_sim >= 0.55 else "❌"
        print(f"{status} {sop_id:<6} {item_name:<25} {primary_sim:>10.4f} {fallback_sim:>10.4f} {max_sim:>10.4f} {winner:>8}")

    cursor.close()
    conn.close()

async def main():
    test_cases = [
        ("馬桶堵塞", [1648]),
        ("馬桶堵住了", [1648]),
        ("電費怎麼繳", [1632]),
        ("垃圾怎麼丟", [1619]),
        ("想要續約", [1628]),
        ("滯納金怎麼算", [1617]),
        ("跳電了", [1653]),
        ("浴室抽風機很吵", [1651]),
    ]

    for question, sop_ids in test_cases:
        await check_similarity(question, sop_ids)
        print()

if __name__ == "__main__":
    asyncio.run(main())
