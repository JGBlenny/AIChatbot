#!/usr/bin/env python3
"""測試是否會產生誤配（False Positive）"""

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

async def test_question(question: str, threshold: float = 0.55):
    """測試問題是否會匹配到 SOP"""

    # 獲取問題向量
    question_embedding = await get_embedding(question)

    if not question_embedding:
        print(f"❌ 無法取得問題向量")
        return

    # 連接資料庫
    conn = get_db_connection()
    cursor = conn.cursor()

    # 查詢：使用 GREATEST(primary, fallback)
    query = """
    SELECT
        si.id,
        si.item_name,
        1 - (si.primary_embedding <=> %s::vector) as primary_sim,
        1 - (si.fallback_embedding <=> %s::vector) as fallback_sim,
        GREATEST(
            1 - (si.primary_embedding <=> %s::vector),
            1 - (si.fallback_embedding <=> %s::vector)
        ) as max_sim
    FROM vendor_sop_items si
    WHERE si.vendor_id = 2
      AND si.is_active = TRUE
      AND GREATEST(
            1 - (si.primary_embedding <=> %s::vector),
            1 - (si.fallback_embedding <=> %s::vector)
          ) >= %s
    ORDER BY max_sim DESC
    LIMIT 3
    """

    cursor.execute(query, (
        question_embedding, question_embedding,
        question_embedding, question_embedding,
        question_embedding, question_embedding,
        threshold
    ))

    results = cursor.fetchall()

    print(f"\n問題: 「{question}」")
    print(f"閾值: {threshold}")
    print(f"匹配數量: {len(results)}")

    if results:
        print(f"{'ID':<8} {'SOP 名稱':<30} {'Primary':>10} {'Fallback':>10} {'最大值':>10}")
        print("-" * 80)
        for row in results:
            sop_id, item_name, primary_sim, fallback_sim, max_sim = row
            winner = "P" if primary_sim > fallback_sim else "F"
            print(f"{sop_id:<8} {item_name:<30} {primary_sim:>10.4f} {fallback_sim:>10.4f} {max_sim:>10.4f} ({winner})")
    else:
        print("✅ 沒有匹配到任何 SOP（正確）")

    cursor.close()
    conn.close()

async def main():
    print("=" * 80)
    print("🧪 測試 GREATEST(primary, fallback) 是否會產生誤配")
    print("=" * 80)

    # 測試案例分類
    test_cases = {
        "完全不相關（不應該匹配）": [
            "今天天氣如何？",
            "推薦好吃的餐廳",
            "Python 怎麼寫迴圈？",
            "台北101怎麼去？",
            "明天會下雨嗎？"
        ],
        "模糊相關（可能誤配風險）": [
            "房子很髒",
            "鄰居很吵",
            "想換房間",
            "可以帶朋友來住嗎？",
            "房東電話是多少？"
        ],
        "應該匹配（正確案例）": [
            "馬桶堵住了",
            "冰箱不冷",
            "想要退租",
            "租金怎麼繳"
        ]
    }

    for category, questions in test_cases.items():
        print(f"\n{'='*80}")
        print(f"📂 {category}")
        print(f"{'='*80}")

        for question in questions:
            await test_question(question, threshold=0.55)

    # 測試不同閾值
    print(f"\n{'='*80}")
    print(f"🔬 測試不同閾值的影響")
    print(f"{'='*80}")

    test_q = "今天天氣如何？"
    for threshold in [0.45, 0.50, 0.55, 0.60]:
        print(f"\n--- 閾值 {threshold} ---")
        await test_question(test_q, threshold=threshold)

if __name__ == "__main__":
    asyncio.run(main())
