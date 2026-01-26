#!/usr/bin/env python3
"""驗證 Primary Embedding 的組成問題"""

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

async def test_embedding_hypothesis():
    """測試：如果 item_name 單獨作為 embedding，相似度會如何？"""

    question = "垃圾要怎麼丟？"

    print("="*100)
    print("🔬 驗證假設：item_name 被 group_name 稀釋了")
    print("="*100)

    # 獲取問題向量
    question_embedding = await get_embedding(question)

    # 獲取各種文本的向量並計算相似度
    test_texts = {
        "當前 Primary (group+item)": "租約條款與規定：詳細解釋租約的基本條款、租金支付方式、押金、租期等及進行詞彙定義。：垃圾收取規範:",
        "假設 Primary (只有 item_name)": "垃圾收取規範",
        "當前 Fallback (content)": "多數案場提供垃圾代收服務，代收項目為一般家用垃圾及資源回收。不收取內容為:1.家具、家電、易碎物、棉被、枕頭被套、包包皮件、鞋子、建材廢料等及其他法定不得回收之物品。2. 非日常家用之廢棄物，如：房客遷入、遷出後所產生之大型袋裝或各類非常態性垃圾。如違反垃圾代收規範，會有違約金產生。",
        "對比：馬桶堵塞 item_name": "馬桶堵塞",
        "對比：馬桶堵塞 content": "宣導請勿丟任何物品至馬桶內，包括衛生紙、衛生棉、貓砂、保險套等等。先請房客嘗試自己疏通。如無法疏通或不是單純堵塞，會有滿溢之情形，轉交專業人員處理。"
    }

    print(f"\n❓ 用戶問題：「{question}」\n")
    print(f"{'文本類型':<40} {'長度':>6} {'相似度':>10} {'排名':>6}")
    print("-"*100)

    results = []
    for text_type, text in test_texts.items():
        text_embedding = await get_embedding(text)

        # 計算餘弦相似度
        import numpy as np
        similarity = 1 - np.dot(question_embedding, text_embedding) / (
            np.linalg.norm(question_embedding) * np.linalg.norm(text_embedding)
        )
        # 實際上應該用 cosine distance，這裡簡化為 1 - cosine_similarity
        # 但由於我們是用 API，直接計算點積
        dot_product = sum(a * b for a, b in zip(question_embedding, text_embedding))
        magnitude_q = sum(a * a for a in question_embedding) ** 0.5
        magnitude_t = sum(b * b for b in text_embedding) ** 0.5
        cosine_sim = dot_product / (magnitude_q * magnitude_t)
        similarity = cosine_sim  # OpenAI embeddings 已經正規化，所以直接用點積

        results.append((text_type, len(text), similarity))

    # 排序並顯示
    results.sort(key=lambda x: x[2], reverse=True)

    for i, (text_type, length, similarity) in enumerate(results, 1):
        marker = ""
        if "假設" in text_type:
            marker = " ⭐⭐⭐"
        elif "當前 Primary" in text_type:
            marker = " ← 當前使用"
        elif "馬桶堵塞 content" in text_type:
            marker = " ← 目前贏的"

        print(f"{text_type:<40} {length:>6} {similarity:>10.4f} {i:>6}{marker}")

    print("\n" + "="*100)
    print("💡 分析結果")
    print("="*100)

    # 找出關鍵數據
    current_primary = next(r for r in results if "當前 Primary" in r[0])
    hypothetical_primary = next(r for r in results if "假設 Primary" in r[0])
    current_fallback = next(r for r in results if "當前 Fallback" in r[0])
    toilet_content = next(r for r in results if "馬桶堵塞 content" in r[0])

    print(f"\n【當前狀況】")
    print(f"  垃圾規範 Primary (group+item): {current_primary[2]:.4f}")
    print(f"  垃圾規範 Fallback (content):  {current_fallback[2]:.4f}")
    print(f"  GREATEST(兩者):              {max(current_primary[2], current_fallback[2]):.4f}")
    print(f"  馬桶堵塞 Fallback:            {toilet_content[2]:.4f} ← 目前排第一")

    print(f"\n【如果改用 item_name】")
    print(f"  垃圾規範 Primary (只有item):  {hypothetical_primary[2]:.4f} ⭐")
    print(f"  垃圾規範 Fallback (content):  {current_fallback[2]:.4f}")
    print(f"  GREATEST(兩者):              {max(hypothetical_primary[2], current_fallback[2]):.4f} ⭐")

    # 比較結果
    improvement = max(hypothetical_primary[2], current_fallback[2]) - max(current_primary[2], current_fallback[2])

    print(f"\n【比較】")
    if max(hypothetical_primary[2], current_fallback[2]) > toilet_content[2]:
        print(f"  ✅ 改用 item_name 後：垃圾規範會排第一！")
        print(f"  ✅ 提升幅度: +{improvement:.4f}")
        print(f"  ✅ 會正確匹配「垃圾收取規範」而非「馬桶堵塞」")
    else:
        print(f"  ❌ 即使改用 item_name：還是馬桶堵塞排第一")
        print(f"  提升幅度: +{improvement:.4f} (不夠)")

if __name__ == "__main__":
    asyncio.run(test_embedding_hypothesis())
