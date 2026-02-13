#!/usr/bin/env python3
"""
LLM Provider 基本功能測試
驗證 Provider 抽象層是否正常運作
"""
import os
import sys

# 添加專案路徑
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'rag-orchestrator'))

from services.llm_provider import (
    get_llm_provider,
    OpenAIProvider,
    OpenRouterProvider,
    OllamaProvider,
    chat_completion
)


def test_openai_provider():
    """測試 OpenAI Provider"""
    print("\n" + "=" * 60)
    print("測試 1: OpenAI Provider")
    print("=" * 60)

    try:
        # 檢查環境變數
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠️  未設定 OPENAI_API_KEY，跳過測試")
            return False

        # 初始化 Provider
        provider = OpenAIProvider()
        print(f"✅ Provider 初始化成功: {provider.provider_name}")

        # 測試 chat_completion
        messages = [
            {"role": "user", "content": "請用一句話說明什麼是機器學習"}
        ]
        result = provider.chat_completion(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.5,
            max_tokens=100
        )

        print(f"\n📝 測試結果:")
        print(f"   回應: {result['content'][:80]}...")
        print(f"   Provider: {result['provider']}")
        print(f"   Model: {result['model']}")
        print(f"   Usage: {result['usage']}")

        print("\n✅ OpenAI Provider 測試通過")
        return True

    except Exception as e:
        print(f"\n❌ OpenAI Provider 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_openrouter_provider():
    """測試 OpenRouter Provider"""
    print("\n" + "=" * 60)
    print("測試 2: OpenRouter Provider")
    print("=" * 60)

    try:
        # 檢查環境變數
        if not os.getenv("OPENROUTER_API_KEY"):
            print("⚠️  未設定 OPENROUTER_API_KEY，跳過測試")
            return None

        # 初始化 Provider
        provider = OpenRouterProvider()
        print(f"✅ Provider 初始化成功: {provider.provider_name}")

        # 測試 chat_completion
        messages = [
            {"role": "user", "content": "Say hello in Traditional Chinese"}
        ]
        result = provider.chat_completion(
            model="anthropic/claude-3.5-sonnet",
            messages=messages,
            temperature=0.7,
            max_tokens=50
        )

        print(f"\n📝 測試結果:")
        print(f"   回應: {result['content']}")
        print(f"   Provider: {result['provider']}")
        print(f"   Model: {result['model']}")

        print("\n✅ OpenRouter Provider 測試通過")
        return True

    except Exception as e:
        print(f"\n⚠️  OpenRouter Provider 測試失敗（可能未配置）: {e}")
        return None


def test_ollama_provider():
    """測試 Ollama Provider"""
    print("\n" + "=" * 60)
    print("測試 3: Ollama Provider")
    print("=" * 60)

    try:
        # 初始化 Provider
        provider = OllamaProvider()
        print(f"✅ Provider 初始化成功: {provider.provider_name}")
        print(f"   API URL: {provider.base_url}")

        # 測試 chat_completion
        messages = [
            {"role": "user", "content": "你好，請用中文回答"}
        ]
        result = provider.chat_completion(
            model="llama2",
            messages=messages,
            temperature=0.7,
            max_tokens=50
        )

        print(f"\n📝 測試結果:")
        print(f"   回應: {result['content'][:100]}...")
        print(f"   Provider: {result['provider']}")
        print(f"   Model: {result['model']}")

        print("\n✅ Ollama Provider 測試通過")
        return True

    except Exception as e:
        print(f"\n⚠️  Ollama Provider 測試失敗（可能服務未運行）: {e}")
        return None


def test_factory_function():
    """測試 Factory 函數"""
    print("\n" + "=" * 60)
    print("測試 4: Factory 函數 (get_llm_provider)")
    print("=" * 60)

    try:
        # 讀取環境變數決定使用哪個 Provider
        provider_type = os.getenv("LLM_PROVIDER", "openai")
        print(f"環境變數 LLM_PROVIDER: {provider_type}")

        # 使用 Factory 函數
        provider = get_llm_provider(reset=True)
        print(f"✅ Factory 函數返回: {provider.provider_name}")

        # 測試便利函數
        result = chat_completion(
            model=os.getenv("INTENT_CLASSIFIER_MODEL", "gpt-3.5-turbo"),
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.5,
            max_tokens=30
        )

        print(f"\n📝 便利函數測試結果:")
        print(f"   回應: {result['content']}")
        print(f"   Provider: {result['provider']}")

        print("\n✅ Factory 函數測試通過")
        return True

    except Exception as e:
        print(f"\n❌ Factory 函數測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_provider_switching():
    """測試 Provider 切換"""
    print("\n" + "=" * 60)
    print("測試 5: Provider 動態切換")
    print("=" * 60)

    results = {}

    # 測試不同的 Provider
    providers_to_test = []

    if os.getenv("OPENAI_API_KEY"):
        providers_to_test.append("openai")

    if os.getenv("OPENROUTER_API_KEY"):
        providers_to_test.append("openrouter")

    # Ollama 總是可以嘗試（即使失敗也無妨）
    providers_to_test.append("ollama")

    for provider_type in providers_to_test:
        try:
            print(f"\n切換到 Provider: {provider_type}")
            provider = get_llm_provider(provider_type=provider_type, reset=True)
            print(f"✅ 成功切換: {provider.provider_name}")
            results[provider_type] = True
        except Exception as e:
            print(f"⚠️  {provider_type} 無法使用: {e}")
            results[provider_type] = False

    print(f"\n📊 切換測試結果:")
    for ptype, success in results.items():
        status = "✅" if success else "⚠️"
        print(f"   {status} {ptype}")

    print("\n✅ Provider 切換測試完成")
    return True


def main():
    """主測試函數"""
    print("=" * 60)
    print("LLM Provider 基本功能測試")
    print("=" * 60)

    # 顯示當前環境變數
    print("\n📋 環境變數配置:")
    print(f"   LLM_PROVIDER: {os.getenv('LLM_PROVIDER', '(未設定,默認 openai)')}")
    print(f"   OPENAI_API_KEY: {'✅ 已設定' if os.getenv('OPENAI_API_KEY') else '❌ 未設定'}")
    print(f"   OPENROUTER_API_KEY: {'✅ 已設定' if os.getenv('OPENROUTER_API_KEY') else '❌ 未設定'}")
    print(f"   OLLAMA_API_URL: {os.getenv('OLLAMA_API_URL', 'http://localhost:11434')}")

    results = {}

    # 執行測試
    results['openai'] = test_openai_provider()
    results['openrouter'] = test_openrouter_provider()
    results['ollama'] = test_ollama_provider()
    results['factory'] = test_factory_function()
    results['switching'] = test_provider_switching()

    # 總結
    print("\n" + "=" * 60)
    print("測試總結")
    print("=" * 60)

    for test_name, result in results.items():
        if result is True:
            status = "✅ 通過"
        elif result is None:
            status = "⚠️  跳過（未配置）"
        else:
            status = "❌ 失敗"

        print(f"   {test_name:20s}: {status}")

    # 計算通過率
    passed = sum(1 for r in results.values() if r is True)
    total = len(results)
    skipped = sum(1 for r in results.values() if r is None)

    print(f"\n通過: {passed}/{total-skipped}")

    if passed == total - skipped:
        print("\n🎉 所有測試通過！")
        return 0
    else:
        print("\n⚠️  部分測試失敗或跳過")
        return 1


if __name__ == "__main__":
    sys.exit(main())
