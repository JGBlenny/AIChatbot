#!/usr/bin/env python3
"""測試特定問題在不同閾值下的匹配情況"""

import asyncio
import psycopg2
import httpx

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="aichatbot_admin",
        user="aichatbot",
        password="aichatbot_password"
    )

async def get_embedding(text: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:5001/api/v1/embeddings",
            json={"text": text}
        )
        data = response.json()
        return data.get("embedding")

async def test_question_detail(question: str, thresholds: list):
    """詳細測試問題在不同閾值下的匹配"""

    print(f"{'='*100}")
    print(f"🔍 問題：「{question}」")
    print(f"{'='*100}\n")

    question_embedding = await get_embedding(question)
    if not question_embedding:
        print("❌ 無法取得問題向量")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    # 查詢所有 SOP 的相似度（不限閾值）
    query = """
    SELECT
        si.id,
        si.item_name,
        si.content,
        1 - (si.primary_embedding <=> %s::vector) as primary_sim,
        1 - (si.fallback_embedding <=> %s::vector) as fallback_sim,
        GREATEST(
            COALESCE(1 - (si.primary_embedding <=> %s::vector), 0),
            COALESCE(1 - (si.fallback_embedding <=> %s::vector), 0)
        ) as max_sim
    FROM vendor_sop_items si
    WHERE si.vendor_id = 2
      AND si.is_active = TRUE
    ORDER BY max_sim DESC
    LIMIT 10
    """

    cursor.execute(query, (
        question_embedding, question_embedding,
        question_embedding, question_embedding
    ))

    results = cursor.fetchall()

    print("📊 相似度排名 (Top 10):")
    print(f"{'排名':<6} {'ID':<8} {'SOP 名稱':<30} {'Primary':>10} {'Fallback':>10} {'最大值':>10}")
    print("-"*100)

    for i, row in enumerate(results, 1):
        sop_id, item_name, content, primary_sim, fallback_sim, max_sim = row
        winner = "P" if primary_sim > fallback_sim else "F"
        print(f"{i:<6} {sop_id:<8} {item_name:<30} {primary_sim:>10.4f} {fallback_sim:>10.4f} {max_sim:>10.4f} ({winner})")

    # 顯示各閾值下的匹配情況
    print(f"\n{'='*100}")
    print("🎯 各閾值下的匹配情況:")
    print(f"{'='*100}\n")

    for threshold in thresholds:
        top_match = results[0] if results and results[0][5] >= threshold else None

        if top_match:
            sop_id, item_name, content, primary_sim, fallback_sim, max_sim = top_match
            print(f"✅ 閾值 {threshold:.2f}: 會匹配")
            print(f"   SOP ID: {sop_id}")
            print(f"   SOP 名稱: {item_name}")
            print(f"   相似度: {max_sim:.4f}")
            print(f"   SOP 內容: {content[:200]}..." if len(content) > 200 else f"   SOP 內容: {content}")
            print()
        else:
            print(f"❌ 閾值 {threshold:.2f}: 不會匹配\n")

    cursor.close()
    conn.close()

    # 實際測試 API 回答 (使用當前閾值 0.55)
    print(f"{'='*100}")
    print("💬 實際 API 回答 (當前閾值 0.55):")
    print(f"{'='*100}\n")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8100/api/v1/message",
                json={
                    "vendor_id": 2,
                    "message": question,
                    "session_id": "test_detail",
                    "user_id": "test"
                }
            )
            data = response.json()

            print(f"找到 SOP: {data.get('source_count', 0)} 個")
            if data.get('sources'):
                for src in data.get('sources', []):
                    print(f"\nSOP ID: {src.get('id')}")
                    print(f"SOP 名稱: {src.get('question_summary')}")

            print(f"\n回答內容:\n{data.get('answer', '')}")
    except Exception as e:
        print(f"API 測試失敗: {e}")

async def main():
    questions = [
        "想要續約怎麼辦？",
        "垃圾要怎麼丟？",
        "押金要繳多少？"
    ]

    thresholds = [0.48, 0.50, 0.52, 0.55]

    for question in questions:
        await test_question_detail(question, thresholds)
        print("\n\n")

if __name__ == "__main__":
    asyncio.run(main())
