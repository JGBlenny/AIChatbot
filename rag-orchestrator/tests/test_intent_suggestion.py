#!/usr/bin/env python3
"""
測試 IntentSuggestionEngine
直接測試新意圖建議功能
"""

import asyncio
import sys
sys.path.insert(0, '/app')

from services.intent_suggestion_engine import IntentSuggestionEngine


async def test_intent_suggestion():
    """測試意圖建議引擎"""

    engine = IntentSuggestionEngine()

    print("=" * 80)
    print("測試 IntentSuggestionEngine")
    print("=" * 80)
    print()

    # 測試問題列表
    test_questions = [
        {
            "question": "你們公司的logo顏色是什麼？",
            "expected": "不相關 - 應該拒絕"
        },
        {
            "question": "請問停車位的租金怎麼算？需要額外付費嗎？",
            "expected": "相關 - 應該建議新增「停車位租金」意圖"
        },
        {
            "question": "寵物飼養有什麼規定嗎？可以養貓狗嗎？",
            "expected": "相關 - 應該建議新增「寵物政策」意圖"
        },
        {
            "question": "今天天氣如何？",
            "expected": "不相關 - 應該拒絕"
        },
        {
            "question": "房東可以隨時進入我的房間嗎？",
            "expected": "相關 - 應該建議新增「隱私權與房東權限」意圖"
        }
    ]

    print(f"📊 當前業務範圍: {engine.business_scope['display_name']}")
    print(f"📝 業務描述: {engine.business_scope['business_description']}")
    print()

    for i, test in enumerate(test_questions, 1):
        print(f"{'='*80}")
        print(f"測試 {i}: {test['question']}")
        print(f"預期: {test['expected']}")
        print(f"{'-'*80}")

        # 分析問題
        analysis = engine.analyze_unclear_question(
            question=test['question'],
            user_id=f"test_user_{i}"
        )

        print(f"✅ 分析結果:")
        print(f"   是否相關: {analysis['is_relevant']}")
        print(f"   相關性分數: {analysis['relevance_score']:.2f}")
        print(f"   是否記錄: {analysis['should_record']}")
        print(f"   推理說明: {analysis['reasoning']}")

        if analysis.get('suggested_intent'):
            print(f"\n   建議意圖:")
            print(f"   - 名稱: {analysis['suggested_intent']['name']}")
            print(f"   - 類型: {analysis['suggested_intent']['type']}")
            print(f"   - 描述: {analysis['suggested_intent']['description']}")
            print(f"   - 關鍵字: {', '.join(analysis['suggested_intent']['keywords'])}")

        # 如果應該記錄，記錄到資料庫
        if analysis['should_record']:
            suggestion_id = engine.record_suggestion(
                question=test['question'],
                analysis=analysis,
                user_id=f"test_user_{i}"
            )
            print(f"\n   ✅ 已記錄建議 ID: {suggestion_id}")

        print()

    # 顯示建議統計
    print("=" * 80)
    print("📊 建議統計")
    print("=" * 80)
    stats = engine.get_suggestion_stats()
    print(f"總建議數: {stats['total']}")
    print(f"待審核: {stats['pending']}")
    print(f"已採納: {stats['approved']}")
    print(f"已拒絕: {stats['rejected']}")
    print(f"已合併: {stats['merged']}")

    if stats['top_suggestions']:
        print("\n高頻建議 (前5個):")
        for sugg in stats['top_suggestions']:
            print(f"  - {sugg['suggested_name']} (頻率: {sugg['frequency']}, 分數: {sugg['relevance_score']:.2f})")

    print()
    print("=" * 80)
    print("✅ 測試完成！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_intent_suggestion())
