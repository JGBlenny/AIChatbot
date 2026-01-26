#!/usr/bin/env python3
"""驗證 Primary Embedding 修復效果"""

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

async def test_garbage_question():
    """測試關鍵問題：「垃圾要怎麼丟？」"""

    question = "垃圾要怎麼丟？"

    print("="*100)
    print(f"🔍 測試問題：「{question}」")
    print("="*100)

    question_embedding = await get_embedding(question)

    conn = get_db_connection()
    cursor = conn.cursor()

    # 查詢 Top 5 相似的 SOP
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
    LIMIT 5
    """

    cursor.execute(query, (question_embedding, question_embedding,
                          question_embedding, question_embedding))
    results = cursor.fetchall()

    print(f"\n📊 相似度排名 (Top 5):")
    print(f"{'排名':<6} {'ID':<8} {'SOP 名稱':<25} {'Primary':>10} {'Fallback':>10} {'最大值':>10} {'勝出':>6}")
    print("-"*100)

    for i, row in enumerate(results, 1):
        sop_id, item_name, content, primary_sim, fallback_sim, max_sim = row
        winner = "P" if primary_sim > fallback_sim else "F"
        marker = " 🎯" if item_name == "垃圾收取規範:" else ""
        marker += " ⚠️" if item_name == "馬桶堵塞:" else ""

        print(f"{i:<6} {sop_id:<8} {item_name:<25} {primary_sim:>10.4f} {fallback_sim:>10.4f} {max_sim:>10.4f} {winner:>6}{marker}")

    # 分析結果
    print(f"\n{'='*100}")
    print("💡 分析結果")
    print(f"{'='*100}")

    top_result = results[0]
    top_name = top_result[1]

    if "垃圾" in top_name:
        print(f"\n✅ 修復成功！")
        print(f"   第一名: {top_name}")
        print(f"   相似度: {top_result[5]:.4f}")
        print(f"   Primary 相似度: {top_result[3]:.4f}")
        print(f"   Fallback 相似度: {top_result[4]:.4f}")

        # 檢查是否是因為 Primary 提升
        if top_result[3] > top_result[4]:
            print(f"\n🎉 Primary Embedding 勝出！（修復前是 Fallback 勝出）")
            print(f"   證明：直接使用 item_name 的策略有效！")
    else:
        print(f"\n❌ 仍有問題")
        print(f"   第一名: {top_name}")
        print(f"   應該是：垃圾收取規範:")

    # 找出「垃圾收取規範」和「馬桶堵塞」的詳細數據
    print(f"\n{'='*100}")
    print("📊 關鍵 SOP 詳細比較")
    print(f"{'='*100}")

    for row in results[:5]:
        sop_id, item_name, content, primary_sim, fallback_sim, max_sim = row
        if "垃圾" in item_name or "馬桶" in item_name:
            print(f"\n【{item_name}】(ID: {sop_id})")
            print(f"  Primary 相似度: {primary_sim:.4f} {'← 勝' if primary_sim > fallback_sim else ''}")
            print(f"  Fallback 相似度: {fallback_sim:.4f} {'← 勝' if fallback_sim >= primary_sim else ''}")
            print(f"  最終相似度: {max_sim:.4f}")
            print(f"  內容: {content[:100]}...")

    cursor.close()
    conn.close()

async def test_coverage():
    """測試整體涵蓋率提升"""

    print(f"\n{'='*100}")
    print("🎯 整體涵蓋率測試")
    print(f"{'='*100}")

    test_questions = [
        "想要續約怎麼辦？",
        "垃圾要怎麼丟？",
        "押金要繳多少？",
        "冷氣不冷而且有異味",
        "浴室抽風機很吵",
    ]

    conn = get_db_connection()
    cursor = conn.cursor()

    matched_count = 0
    threshold = 0.50  # 使用推薦閾值

    for question in test_questions:
        question_embedding = await get_embedding(question)

        cursor.execute("""
            SELECT
                si.item_name,
                GREATEST(
                    COALESCE(1 - (si.primary_embedding <=> %s::vector), 0),
                    COALESCE(1 - (si.fallback_embedding <=> %s::vector), 0)
                ) as max_sim
            FROM vendor_sop_items si
            WHERE si.vendor_id = 2
              AND si.is_active = TRUE
            ORDER BY max_sim DESC
            LIMIT 1
        """, (question_embedding, question_embedding))

        result = cursor.fetchone()
        if result and result[1] >= threshold:
            matched_count += 1
            print(f"✅ {question:<30} → {result[0]:<30} ({result[1]:.4f})")
        else:
            print(f"❌ {question:<30} → 未匹配 ({result[1]:.4f} < {threshold})")

    coverage_rate = matched_count / len(test_questions) * 100
    print(f"\n涵蓋率: {matched_count}/{len(test_questions)} = {coverage_rate:.1f}%")

    cursor.close()
    conn.close()

async def main():
    await test_garbage_question()
    await test_coverage()

if __name__ == "__main__":
    asyncio.run(main())
