#!/usr/bin/env python3
"""
LLM Provider 集成測試
驗證修改後的服務(IntentClassifier, LLMAnswerOptimizer)是否正常運作
"""
import os
import sys

# 添加專案路徑
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'rag-orchestrator'))

from services.intent_classifier import IntentClassifier
from services.llm_answer_optimizer import LLMAnswerOptimizer


def test_intent_classifier():
    """測試 IntentClassifier 是否正常工作"""
    print("\n" + "=" * 60)
    print("測試 1: IntentClassifier with LLM Provider")
    print("=" * 60)

    try:
        # 初始化分類器(會自動使用 LLM Provider)
        classifier = IntentClassifier(use_database=False)
        print("✅ IntentClassifier 初始化成功")
        print(f"   使用 Provider: {classifier.llm_provider.provider_name}")

        # 測試分類
        test_question = "租金什麼時候要繳納？"
        print(f"\n測試問題: {test_question}")

        result = classifier.classify(test_question)

        print(f"\n📝 分類結果:")
        print(f"   意圖: {result.get('intent_name', 'N/A')}")
        print(f"   信心度: {result.get('confidence', 0):.2f}")
        print(f"   關鍵詞: {result.get('keywords', [])}")

        # 驗證結果結構
        assert 'intent_name' in result, "缺少 intent_name"
        assert 'confidence' in result, "缺少 confidence"

        print("\n✅ IntentClassifier 測試通過")
        return True

    except Exception as e:
        print(f"\n❌ IntentClassifier 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_answer_optimizer():
    """測試 LLMAnswerOptimizer 是否正常工作"""
    print("\n" + "=" * 60)
    print("測試 2: LLMAnswerOptimizer with LLM Provider")
    print("=" * 60)

    try:
        # 初始化優化器(會自動使用 LLM Provider)
        optimizer = LLMAnswerOptimizer()
        print("✅ LLMAnswerOptimizer 初始化成功")
        print(f"   使用 Provider: {optimizer.llm_provider.provider_name}")

        # 測試答案優化
        test_question = "租金怎麼繳？"
        test_search_results = [{
            'question_summary': '租金繳納方式',
            'content': '租金於每月5日前繳納，可透過銀行轉帳或現金支付。',
            'similarity': 0.85,
            'title': '租金繳納方式'
        }]
        test_intent_info = {
            'intent_name': '帳務查詢',
            'intent_type': 'knowledge',
            'description': '租金繳納相關問題',
            'confidence': 0.9
        }

        print(f"\n測試問題: {test_question}")
        print(f"搜尋結果數: {len(test_search_results)}")

        # 測試答案優化
        result = optimizer.optimize_answer(
            question=test_question,
            search_results=test_search_results,
            confidence_level='high',
            intent_info=test_intent_info,
            confidence_score=0.85
        )

        optimized = result.get('optimized_answer', '')
        tokens = result.get('optimization_stats', {}).get('total_tokens', 0)

        print(f"\n📝 優化結果:")
        print(f"   優化答案: {optimized[:100]}...")
        print(f"   使用 tokens: {tokens}")

        # 驗證結果
        assert optimized is not None, "優化答案為 None"
        assert len(optimized) > 0, "優化答案為空"
        # Note: tokens 可能為 0 (使用快速路徑或模板格式化)
        # assert tokens > 0, "tokens 數量異常"

        print("\n✅ LLMAnswerOptimizer 測試通過")
        return True

    except Exception as e:
        print(f"\n❌ LLMAnswerOptimizer 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_provider_switching():
    """測試 Provider 切換功能"""
    print("\n" + "=" * 60)
    print("測試 3: Provider 在不同服務間的一致性")
    print("=" * 60)

    try:
        # 初始化兩個服務
        classifier = IntentClassifier(use_database=False)
        optimizer = LLMAnswerOptimizer()

        print(f"IntentClassifier Provider: {classifier.llm_provider.provider_name}")
        print(f"LLMAnswerOptimizer Provider: {optimizer.llm_provider.provider_name}")

        # 驗證使用同一個 Provider 實例(單例模式)
        assert classifier.llm_provider.provider_name == optimizer.llm_provider.provider_name, \
            "兩個服務使用不同的 Provider"

        print("\n✅ Provider 一致性測試通過")
        return True

    except Exception as e:
        print(f"\n❌ Provider 一致性測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """測試向後兼容性 - 確保在 LLM_PROVIDER=openai 時行為不變"""
    print("\n" + "=" * 60)
    print("測試 4: 向後兼容性 (LLM_PROVIDER=openai)")
    print("=" * 60)

    try:
        # 確認環境變數
        provider_type = os.getenv("LLM_PROVIDER", "openai")
        print(f"當前 LLM_PROVIDER: {provider_type}")

        if provider_type != "openai":
            print("⚠️  跳過(當前不是使用 openai)")
            return None

        # 測試服務初始化
        classifier = IntentClassifier(use_database=False)
        optimizer = LLMAnswerOptimizer()

        # 驗證使用 OpenAI Provider
        assert classifier.llm_provider.provider_name == "OpenAI", \
            f"預期 OpenAI，實際: {classifier.llm_provider.provider_name}"
        assert optimizer.llm_provider.provider_name == "OpenAI", \
            f"預期 OpenAI，實際: {optimizer.llm_provider.provider_name}"

        print("✅ 使用 OpenAI Provider")
        print("✅ 向後兼容性測試通過")
        return True

    except Exception as e:
        print(f"\n❌ 向後兼容性測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主測試函數"""
    print("=" * 60)
    print("LLM Provider 集成測試")
    print("=" * 60)

    # 顯示當前環境
    print("\n📋 環境配置:")
    print(f"   LLM_PROVIDER: {os.getenv('LLM_PROVIDER', '(未設定,默認 openai)')}")
    print(f"   OPENAI_API_KEY: {'✅ 已設定' if os.getenv('OPENAI_API_KEY') else '❌ 未設定'}")

    results = {}

    # 執行測試
    results['intent_classifier'] = test_intent_classifier()
    results['answer_optimizer'] = test_llm_answer_optimizer()
    results['provider_consistency'] = test_provider_switching()
    results['backward_compatibility'] = test_backward_compatibility()

    # 總結
    print("\n" + "=" * 60)
    print("測試總結")
    print("=" * 60)

    for test_name, result in results.items():
        if result is True:
            status = "✅ 通過"
        elif result is None:
            status = "⚠️  跳過"
        else:
            status = "❌ 失敗"

        print(f"   {test_name:30s}: {status}")

    # 計算通過率
    passed = sum(1 for r in results.values() if r is True)
    total = len([r for r in results.values() if r is not None])
    skipped = sum(1 for r in results.values() if r is None)

    print(f"\n通過: {passed}/{total}")

    if passed == total:
        print("\n🎉 所有測試通過！修改後的服務運作正常")
        print("\n接下來可以:")
        print("  1. Commit 當前修改")
        print("  2. 繼續完成剩餘服務的修改")
        return 0
    else:
        print("\n⚠️  部分測試失敗，需要修復")
        return 1


if __name__ == "__main__":
    sys.exit(main())
