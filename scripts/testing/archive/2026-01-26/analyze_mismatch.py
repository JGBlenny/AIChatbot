#!/usr/bin/env python3
"""分析「垃圾要怎麼丟」的誤配原因"""

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

async def analyze():
    question = "垃圾要怎麼丟？"

    print("="*100)
    print(f"🔍 分析問題：「{question}」")
    print("="*100)

    # 獲取問題向量
    question_embedding = await get_embedding(question)

    conn = get_db_connection()
    cursor = conn.cursor()

    # 查詢兩個 SOP 的詳細資訊
    query = """
    SELECT
        si.id,
        si.item_name,
        si.content,
        sg.group_name,
        CASE
            WHEN sg.group_name IS NOT NULL
            THEN sg.group_name || '：' || si.item_name
            ELSE si.item_name
        END as primary_text,
        1 - (si.primary_embedding <=> %s::vector) as primary_sim,
        1 - (si.fallback_embedding <=> %s::vector) as fallback_sim,
        GREATEST(
            COALESCE(1 - (si.primary_embedding <=> %s::vector), 0),
            COALESCE(1 - (si.fallback_embedding <=> %s::vector), 0)
        ) as max_sim
    FROM vendor_sop_items si
    LEFT JOIN vendor_sop_groups sg ON si.group_id = sg.id
    WHERE si.id IN (1648, 1619)
    ORDER BY max_sim DESC
    """

    cursor.execute(query, (question_embedding, question_embedding,
                          question_embedding, question_embedding))
    results = cursor.fetchall()

    for row in results:
        sop_id, item_name, content, group_name, primary_text, primary_sim, fallback_sim, max_sim = row

        print(f"\n{'='*100}")
        print(f"📋 SOP ID: {sop_id} - {item_name}")
        print(f"{'='*100}")

        print(f"\n【Primary Embedding 組成】")
        print(f"文本: {primary_text[:100]}...")
        print(f"長度: {len(primary_text)} 字")
        print(f"相似度: {primary_sim:.4f}")

        print(f"\n【Fallback Embedding 組成】")
        print(f"文本: {content}")
        print(f"長度: {len(content)} 字")
        print(f"相似度: {fallback_sim:.4f} {'← 使用此值' if fallback_sim > primary_sim else ''}")

        print(f"\n【最終相似度】: {max_sim:.4f}")

        # 分析關鍵字
        print(f"\n【關鍵字分析】")
        keywords = {
            "垃圾": content.count("垃圾"),
            "丟": content.count("丟"),
            "收取": content.count("收取"),
            "代收": content.count("代收")
        }

        for keyword, count in keywords.items():
            print(f"  「{keyword}」出現 {count} 次")

    cursor.close()
    conn.close()

    # 語義結構分析
    print(f"\n{'='*100}")
    print("💡 語義結構分析")
    print(f"{'='*100}")

    print(f"\n用戶問題：「{question}」")
    print("  結構: [垃圾] + [要怎麼] + [丟]")
    print("  核心: 詢問「丟垃圾」的動作/方法")

    print(f"\n馬桶堵塞 SOP:")
    print("  內容: 「請勿丟任何物品至馬桶內...」")
    print("  結構: [請勿] + [丟] + [物品]")
    print("  核心: 關於「丟東西」的動作指示")
    print("  ✅ 動詞匹配: 「丟」")

    print(f"\n垃圾收取規範 SOP:")
    print("  內容: 「提供垃圾代收服務...不收取內容為...」")
    print("  結構: [垃圾] + [代收] / [不收取]")
    print("  核心: 關於「垃圾」的規範列表")
    print("  ✅ 名詞匹配: 「垃圾」")
    print("  ❌ 動詞不匹配: 無「丟」，而是「代收」「收取」")

    print(f"\n{'='*100}")
    print("🎯 結論")
    print(f"{'='*100}")

    print("""
向量相似度算法更看重「語義結構的匹配」而非「關鍵字的出現次數」：

1. 用戶問「怎麼丟」→ 動作導向的問題
2. 馬桶堵塞說「請勿丟」→ 動作導向的指示（完美匹配結構）
3. 垃圾規範說「代收...不收取」→ 規範列表（結構不匹配）

雖然「垃圾規範」有 4 個「垃圾」關鍵字，
但「馬桶堵塞」有「丟」這個核心動詞，所以相似度更高！
    """)

if __name__ == "__main__":
    asyncio.run(analyze())
