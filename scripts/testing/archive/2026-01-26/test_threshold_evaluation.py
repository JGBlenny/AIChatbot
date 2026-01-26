#!/usr/bin/env python3
"""
全面評估不同閾值的效果
測試涵蓋率、誤配率、邊界案例
"""

import asyncio
import psycopg2
import httpx
from typing import List, Dict
import json

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

async def test_with_threshold(question: str, threshold: float, vendor_id: int = 2):
    """測試問題在指定閾值下是否能檢索到 SOP"""

    question_embedding = await get_embedding(question)
    if not question_embedding:
        return None

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT
        si.id,
        si.item_name,
        GREATEST(
            COALESCE(1 - (si.primary_embedding <=> %s::vector), 0),
            COALESCE(1 - (si.fallback_embedding <=> %s::vector), 0)
        ) as max_sim
    FROM vendor_sop_items si
    WHERE si.vendor_id = %s
      AND si.is_active = TRUE
      AND GREATEST(
            COALESCE(1 - (si.primary_embedding <=> %s::vector), 0),
            COALESCE(1 - (si.fallback_embedding <=> %s::vector), 0)
          ) >= %s
    ORDER BY max_sim DESC
    LIMIT 3
    """

    cursor.execute(query, (
        question_embedding, question_embedding,
        vendor_id,
        question_embedding, question_embedding,
        threshold
    ))

    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return {
        "found": len(results) > 0,
        "count": len(results),
        "top_match": {
            "id": results[0][0],
            "name": results[0][1],
            "similarity": results[0][2]
        } if results else None
    }

async def evaluate_thresholds():
    """評估不同閾值的效果"""

    print("="*100)
    print("🔬 閾值全面評估測試")
    print("="*100)

    # 測試閾值
    thresholds = [0.48, 0.50, 0.52, 0.55, 0.58]

    # 測試案例分類
    test_cases = {
        "應該匹配 - 租金繳費": [
            "租金每個月幾號要繳？",
            "租金可以用什麼方式付款？",
            "忘記繳房租會怎樣？",
            "電費要怎麼繳？",
            "可以開收據或發票嗎？"
        ],
        "應該匹配 - 合約相關": [
            "想要續約怎麼辦？",
            "可以提前退租嗎？",
            "退租的時候押金怎麼退？",
            "簽約前需要注意什麼？",
            "租約到期怎麼辦？"
        ],
        "應該匹配 - 設備維修": [
            "冰箱不冷了怎麼辦？",
            "馬桶堵住了可以報修嗎？",
            "冷氣不冷而且有異味",
            "熱水器沒有熱水",
            "洗衣機一直顯示錯誤",
            "房間突然跳電了",
            "浴室抽風機很吵"
        ],
        "應該匹配 - 緊急狀況": [
            "水管漏水了怎麼辦？",
            "天花板漏水",
            "房間突然停電"
        ],
        "應該匹配 - 生活相關": [
            "垃圾要怎麼丟？",
            "有什麼生活規則要遵守？",
            "可以養寵物嗎？"
        ],
        "應該匹配 - 費用問題": [
            "押金要繳多少？",
            "什麼是定金？",
            "滯納金怎麼算？",
            "退租要付清潔費嗎？"
        ],
        "完全不相關 - 一般知識": [
            "今天天氣如何？",
            "推薦好吃的餐廳",
            "Python 怎麼寫迴圈？",
            "台北101怎麼去？",
            "明天會下雨嗎？",
            "股票怎麼買？",
            "最近有什麼好看的電影？",
            "如何學習英文？",
            "台灣有幾個縣市？",
            "太陽系有幾顆行星？"
        ],
        "完全不相關 - 其他生活": [
            "我想買車",
            "哪裡可以學游泳？",
            "銀行開戶要什麼文件？",
            "護照怎麼申請？",
            "健保卡遺失怎麼辦？",
            "怎麼訂高鐵票？",
            "信用卡怎麼辦？",
            "駕照考試怎麼報名？",
            "郵局在哪裡？",
            "便利商店有賣什麼？"
        ],
        "邊界案例 - 模糊相關": [
            "房子很髒",
            "鄰居很吵",
            "想換房間",
            "可以帶朋友來住嗎？",
            "房東電話是多少？",
            "附近有便利商店嗎？",
            "網路密碼是什麼？",
            "鑰匙掉了怎麼辦？",
            "房間有蟑螂",
            "窗戶關不緊"
        ],
        "邊界案例 - 語義接近但非 SOP": [
            "租金可以晚幾天繳嗎？",
            "我不想繳電費",
            "馬桶可以丟衛生紙嗎？",
            "冰箱可以放什麼？",
            "可以在房間煮飯嗎？",
            "可以釘釘子嗎？",
            "可以養魚嗎？",
            "可以裝監視器嗎？",
            "可以改裝房間嗎？",
            "可以轉租嗎？"
        ]
    }

    # 統計結果
    results = {threshold: {
        "should_match": {"total": 0, "matched": 0, "questions": []},
        "should_not_match": {"total": 0, "matched": 0, "questions": []},
        "boundary": {"total": 0, "matched": 0, "questions": []}
    } for threshold in thresholds}

    # 執行測試
    for category, questions in test_cases.items():
        print(f"\n{'='*100}")
        print(f"📂 {category}")
        print(f"{'='*100}")

        # 判斷類別
        if "應該匹配" in category:
            category_type = "should_match"
        elif "完全不相關" in category:
            category_type = "should_not_match"
        else:
            category_type = "boundary"

        for question in questions:
            print(f"\n❓ {question}")

            for threshold in thresholds:
                result = await test_with_threshold(question, threshold)

                if result:
                    results[threshold][category_type]["total"] += 1

                    if result["found"]:
                        results[threshold][category_type]["matched"] += 1
                        results[threshold][category_type]["questions"].append({
                            "question": question,
                            "sop_id": result["top_match"]["id"],
                            "sop_name": result["top_match"]["name"],
                            "similarity": result["top_match"]["similarity"]
                        })

                        if threshold == 0.55:  # 只顯示當前閾值的結果
                            print(f"   ✅ [0.55] 找到: [{result['top_match']['id']}] {result['top_match']['name']} (相似度: {result['top_match']['similarity']:.4f})")
                    else:
                        if threshold == 0.55:
                            print(f"   ❌ [0.55] 未找到")

            await asyncio.sleep(0.3)  # 避免請求過快

    # 顯示統計結果
    print("\n" + "="*100)
    print("📊 閾值評估統計")
    print("="*100)

    print(f"\n{'閾值':<10} {'應該匹配':<20} {'不應該匹配':<20} {'邊界案例':<20} {'總評':<10}")
    print("-"*100)

    for threshold in thresholds:
        r = results[threshold]

        should_rate = r["should_match"]["matched"] / r["should_match"]["total"] * 100 if r["should_match"]["total"] > 0 else 0
        should_not_rate = (r["should_not_match"]["total"] - r["should_not_match"]["matched"]) / r["should_not_match"]["total"] * 100 if r["should_not_match"]["total"] > 0 else 0
        boundary_rate = r["boundary"]["matched"] / r["boundary"]["total"] * 100 if r["boundary"]["total"] > 0 else 0

        false_positive_rate = r["should_not_match"]["matched"] / r["should_not_match"]["total"] * 100 if r["should_not_match"]["total"] > 0 else 0

        # 總評分 = 涵蓋率 * 0.6 + (100 - 誤配率) * 0.4
        overall_score = should_rate * 0.6 + should_not_rate * 0.4

        status = "⭐⭐⭐" if threshold == 0.55 else ""

        print(f"{threshold:<10.2f} {r['should_match']['matched']}/{r['should_match']['total']} ({should_rate:.1f}%){'':>7} "
              f"{r['should_not_match']['total']-r['should_not_match']['matched']}/{r['should_not_match']['total']} ({should_not_rate:.1f}%){'':>3} "
              f"{r['boundary']['matched']}/{r['boundary']['total']} ({boundary_rate:.1f}%){'':>7} "
              f"{overall_score:.1f}{'':>5} {status}")

    # 詳細分析
    print("\n" + "="*100)
    print("📋 詳細分析")
    print("="*100)

    for threshold in thresholds:
        r = results[threshold]

        print(f"\n🔍 閾值 {threshold}")
        print("-"*100)

        # 應該匹配
        should_match_rate = r["should_match"]["matched"] / r["should_match"]["total"] * 100
        print(f"✅ 應該匹配: {r['should_match']['matched']}/{r['should_match']['total']} ({should_match_rate:.1f}%)")

        # 誤配（False Positive）
        false_positive = r["should_not_match"]["matched"]
        false_positive_rate = false_positive / r["should_not_match"]["total"] * 100
        print(f"❌ 誤配 (False Positive): {false_positive}/{r['should_not_match']['total']} ({false_positive_rate:.1f}%)")

        if false_positive > 0:
            print(f"   ⚠️  誤配問題:")
            for item in r["should_not_match"]["questions"][:5]:  # 只顯示前 5 個
                print(f"      - 「{item['question']}」→ [{item['sop_id']}] {item['sop_name']} ({item['similarity']:.4f})")

        # 邊界案例
        boundary_rate = r["boundary"]["matched"] / r["boundary"]["total"] * 100
        print(f"⚡ 邊界案例匹配: {r['boundary']['matched']}/{r['boundary']['total']} ({boundary_rate:.1f}%)")

    # 儲存詳細結果
    with open('threshold_evaluation_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n📄 詳細結果已儲存至: threshold_evaluation_results.json")

    # 推薦閾值
    print("\n" + "="*100)
    print("💡 推薦建議")
    print("="*100)

    # 計算各閾值的綜合評分
    scores = {}
    for threshold in thresholds:
        r = results[threshold]
        coverage = r["should_match"]["matched"] / r["should_match"]["total"] * 100
        precision = (r["should_not_match"]["total"] - r["should_not_match"]["matched"]) / r["should_not_match"]["total"] * 100

        # 綜合評分：涵蓋率 60% + 精確率 40%
        scores[threshold] = coverage * 0.6 + precision * 0.4

    best_threshold = max(scores, key=scores.get)

    print(f"\n🏆 最佳閾值: {best_threshold} (綜合評分: {scores[best_threshold]:.1f})")
    print(f"\n各閾值評分:")
    for threshold in sorted(scores, reverse=True, key=lambda x: scores[x]):
        r = results[threshold]
        coverage = r["should_match"]["matched"] / r["should_match"]["total"] * 100
        fp_rate = r["should_not_match"]["matched"] / r["should_not_match"]["total"] * 100

        print(f"  {threshold:.2f}: 評分 {scores[threshold]:.1f} | 涵蓋率 {coverage:.1f}% | 誤配率 {fp_rate:.1f}%")

if __name__ == "__main__":
    asyncio.run(evaluate_thresholds())
