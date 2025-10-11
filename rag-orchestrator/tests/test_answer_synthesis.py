"""
答案合成功能測試腳本
測試 LLM Answer Optimizer 的答案合成能力
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.llm_answer_optimizer import LLMAnswerOptimizer


def test_synthesis_trigger():
    """測試合成觸發邏輯"""
    print("\n" + "="*60)
    print("測試 1：合成觸發邏輯")
    print("="*60)

    # 建立優化器（啟用合成）
    optimizer = LLMAnswerOptimizer(config={
        "enable_synthesis": True,
        "synthesis_min_results": 2,
        "synthesis_threshold": 0.7
    })

    # 測試案例 1：應該觸發合成（複合問題 + 低相似度）
    question1 = "如何辦理退租手續？需要準備什麼？"
    results1 = [
        {"title": "退租流程", "content": "提前30天通知...", "similarity": 0.65},
        {"title": "退租注意事項", "content": "需要繳清費用...", "similarity": 0.60}
    ]

    should_synthesize1 = optimizer._should_synthesize(question1, results1)
    print(f"\n案例 1：{question1}")
    print(f"結果數：{len(results1)}, 最高相似度：0.65")
    print(f"應該合成：{should_synthesize1} {'✅' if should_synthesize1 else '❌'}")

    # 測試案例 2：不應該觸發（單一高分答案）
    question2 = "租金是多少？"
    results2 = [
        {"title": "租金資訊", "content": "月租金 15000 元", "similarity": 0.85},
        {"title": "租金計算", "content": "包含管理費", "similarity": 0.55}
    ]

    should_synthesize2 = optimizer._should_synthesize(question2, results2)
    print(f"\n案例 2：{question2}")
    print(f"結果數：{len(results2)}, 最高相似度：0.85")
    print(f"應該合成：{should_synthesize2} {'❌ (預期不觸發)' if not should_synthesize2 else '✅'}")

    # 測試案例 3：不應該觸發（非複合問題）
    question3 = "租金"
    results3 = [
        {"title": "租金資訊", "content": "月租金 15000 元", "similarity": 0.60},
        {"title": "租金計算", "content": "包含管理費", "similarity": 0.55}
    ]

    should_synthesize3 = optimizer._should_synthesize(question3, results3)
    print(f"\n案例 3：{question3}")
    print(f"結果數：{len(results3)}, 最高相似度：0.60")
    print(f"應該合成：{should_synthesize3} {'❌ (預期不觸發)' if not should_synthesize3 else '✅'}")


def test_answer_synthesis():
    """測試實際答案合成"""
    print("\n" + "="*60)
    print("測試 2：實際答案合成")
    print("="*60)

    # 建立優化器（啟用合成）
    optimizer = LLMAnswerOptimizer(config={
        "enable_synthesis": True,
        "synthesis_min_results": 2,
        "synthesis_max_results": 3,
        "synthesis_threshold": 0.7
    })

    # 模擬檢索結果（多個答案各有側重）
    question = "退租時押金要怎麼退還？需要什麼流程？"
    search_results = [
        {
            "id": 1,
            "title": "押金退還時間",
            "category": "租金問題",
            "content": "押金會在退租後 7-14 個工作天內退還。如有損壞，會扣除修復費用後退還餘額。",
            "similarity": 0.68
        },
        {
            "id": 2,
            "title": "退租流程說明",
            "category": "合約問題",
            "content": """退租流程包括：
1. 提前 30 天通知
2. 約定檢查時間
3. 房屋狀況檢查
4. 繳清所有費用""",
            "similarity": 0.65
        },
        {
            "id": 3,
            "title": "退租注意事項",
            "category": "合約問題",
            "content": "退租時需要：\n- 提供銀行帳號（退款用）\n- 歸還所有鑰匙\n- 清空個人物品\n- 恢復房屋原狀",
            "similarity": 0.62
        }
    ]

    intent_info = {
        "intent_name": "退租流程",
        "intent_type": "knowledge",
        "keywords": ["退租", "押金", "退還"]
    }

    print(f"\n問題：{question}")
    print(f"\n檢索結果：{len(search_results)} 個")
    for i, result in enumerate(search_results, 1):
        print(f"  [{i}] {result['title']} (相似度: {result['similarity']:.2f})")

    # 檢查是否觸發合成
    should_synthesize = optimizer._should_synthesize(question, search_results)
    print(f"\n觸發合成：{'是 ✅' if should_synthesize else '否 ❌'}")

    if should_synthesize:
        print("\n開始答案合成...")
        try:
            synthesized_answer, tokens = optimizer.synthesize_answer(
                question=question,
                search_results=search_results,
                intent_info=intent_info
            )

            print(f"\n✅ 合成成功！")
            print(f"Tokens 使用：{tokens}")
            print(f"\n{'='*60}")
            print("合成後的答案：")
            print(f"{'='*60}")
            print(synthesized_answer)
            print(f"{'='*60}")

        except Exception as e:
            print(f"\n❌ 合成失敗：{e}")


def test_end_to_end():
    """測試端到端優化流程（含合成）"""
    print("\n" + "="*60)
    print("測試 3：端到端優化流程")
    print("="*60)

    # 建立優化器（啟用合成）
    optimizer = LLMAnswerOptimizer(config={
        "enable_synthesis": True,
        "synthesis_min_results": 2,
        "synthesis_threshold": 0.7,
        "enable_optimization": True,
        "optimize_for_confidence": ["high", "medium"]
    })

    question = "如何申請退租？押金什麼時候退還？"
    search_results = [
        {
            "id": 1,
            "title": "退租申請方式",
            "category": "合約問題",
            "content": "退租需提前 30 天以書面方式通知房東。可使用掛號信或存證信函。",
            "similarity": 0.66
        },
        {
            "id": 2,
            "title": "押金退還規定",
            "category": "租金問題",
            "content": "押金在房屋檢查完成、確認無損壞後，於 7-14 個工作天內退還。",
            "similarity": 0.64
        }
    ]

    intent_info = {
        "intent_name": "退租流程",
        "intent_type": "knowledge",
        "keywords": ["退租", "申請", "押金"]
    }

    print(f"\n問題：{question}")
    print(f"檢索結果：{len(search_results)} 個")
    print(f"信心度：high")

    print("\n執行優化...")
    result = optimizer.optimize_answer(
        question=question,
        search_results=search_results,
        confidence_level="high",
        intent_info=intent_info
    )

    print(f"\n✅ 優化完成")
    print(f"優化已應用：{result['optimization_applied']}")
    print(f"合成已應用：{result.get('synthesis_applied', False)} {'✨' if result.get('synthesis_applied') else ''}")
    print(f"Tokens 使用：{result['tokens_used']}")
    print(f"處理時間：{result['processing_time_ms']}ms")

    print(f"\n{'='*60}")
    print("最終答案：")
    print(f"{'='*60}")
    print(result['optimized_answer'])
    print(f"{'='*60}")


def test_synthesis_disabled():
    """測試合成功能停用時的行為"""
    print("\n" + "="*60)
    print("測試 4：合成功能停用")
    print("="*60)

    # 建立優化器（停用合成）
    optimizer = LLMAnswerOptimizer(config={
        "enable_synthesis": False  # 停用
    })

    question = "如何辦理退租？"
    search_results = [
        {"title": "退租流程", "content": "流程說明...", "similarity": 0.65},
        {"title": "退租注意事項", "content": "注意事項...", "similarity": 0.60}
    ]

    should_synthesize = optimizer._should_synthesize(question, search_results)
    print(f"\n合成功能：停用")
    print(f"應該合成：{should_synthesize} {'✅ (預期：否)' if not should_synthesize else '❌'}")


if __name__ == "__main__":
    print("\n" + "🧪 " + "="*58)
    print("答案合成功能測試")
    print("="*60)

    has_api_key = bool(os.getenv("OPENAI_API_KEY"))

    if not has_api_key:
        print("\n⚠️  注意：未設定 OPENAI_API_KEY 環境變數")
        print("將只執行邏輯測試（不呼叫 LLM API）")

    try:
        # 執行邏輯測試（不需要 API）
        test_synthesis_trigger()
        test_synthesis_disabled()

        # 如果有 API key，詢問是否執行 API 測試
        if has_api_key:
            print("\n" + "="*60)
            response = input("是否執行需要呼叫 LLM API 的測試？(y/n): ")
            if response.lower() == 'y':
                test_answer_synthesis()
                test_end_to_end()
            else:
                print("跳過 API 測試")
        else:
            print("\n" + "="*60)
            print("⏸️  跳過 API 測試（需要設定 OPENAI_API_KEY）")
            print("設定方式：export OPENAI_API_KEY='your-key-here'")

        print("\n" + "="*60)
        print("✅ 邏輯測試完成！")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ 測試失敗：{e}")
        import traceback
        traceback.print_exc()
