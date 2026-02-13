"""
LLM Provider 抽象層
統一處理所有 LLM API 調用，支援多種 Provider（OpenAI, OpenRouter, Ollama）
"""
import os
import httpx
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
from openai import OpenAI, AsyncOpenAI


class LLMProvider(ABC):
    """
    LLM Provider 抽象基類
    定義所有 LLM Provider 必須實現的介面
    """

    @abstractmethod
    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        執行聊天完成請求

        Args:
            model: 模型名稱
            messages: 訊息列表 [{"role": "user", "content": "..."}]
            temperature: 溫度參數 (0-1)
            max_tokens: 最大生成 tokens 數
            **kwargs: 其他參數（如 functions, function_call 等）

        Returns:
            {
                'content': str,           # 生成的文本
                'usage': dict,            # 使用統計（可選）
                'raw_response': object    # 原始 API 回應（用於特殊功能如 function calling）
            }
        """
        pass

    @abstractmethod
    def embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> Optional[List[float]]:
        """
        生成文本 embedding

        Args:
            text: 要生成 embedding 的文本
            model: embedding 模型名稱（可選）

        Returns:
            embedding 向量列表，失敗時返回 None
        """
        pass


class OpenAIProvider(LLMProvider):
    """
    OpenAI Provider 實現
    使用官方 OpenAI API
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 OpenAI Provider

        Args:
            api_key: OpenAI API Key（可選，默認使用環境變數）
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY 未設定")

        self.client = OpenAI(api_key=self.api_key)
        self.async_client = AsyncOpenAI(api_key=self.api_key)
        self.provider_name = "OpenAI"

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """執行 OpenAI 聊天完成請求"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            # 基本回應結構
            result = {
                'content': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                'model': response.model,
                'provider': self.provider_name,
                'raw_response': response  # 保留原始回應以支援 function calling 等特殊功能
            }

            return result
        except Exception as e:
            raise Exception(f"OpenAI API 調用失敗: {str(e)}")

    def embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> Optional[List[float]]:
        """生成 OpenAI embedding"""
        try:
            model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
            response = self.client.embeddings.create(
                model=model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ OpenAI Embedding 生成失敗: {e}")
            return None

    async def async_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """執行異步 OpenAI 聊天完成請求"""
        try:
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            # 統一回傳格式
            return {
                'content': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                    'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                    'total_tokens': response.usage.total_tokens if response.usage else 0
                },
                'raw_response': response  # 保留原始回應供 function calling 使用
            }
        except Exception as e:
            print(f"❌ OpenAI Async Chat Completion 失敗: {e}")
            raise

    async def async_embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> Optional[List[float]]:
        """生成異步 OpenAI embedding"""
        try:
            model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
            response = await self.async_client.embeddings.create(
                model=model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ OpenAI Async Embedding 生成失敗: {e}")
            return None


class OpenRouterProvider(LLMProvider):
    """
    OpenRouter Provider 實現
    使用 OpenRouter API（支援多種開源模型）
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 OpenRouter Provider

        Args:
            api_key: OpenRouter API Key（可選，默認使用環境變數）
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY 未設定")

        # OpenRouter 使用 OpenAI SDK 但改變 base_url
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.provider_name = "OpenRouter"

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """執行 OpenRouter 聊天完成請求"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            return {
                'content': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                } if response.usage else {},
                'model': response.model,
                'provider': self.provider_name,
                'raw_response': response  # 保留原始回應
            }
        except Exception as e:
            raise Exception(f"OpenRouter API 調用失敗: {str(e)}")

    def embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> Optional[List[float]]:
        """
        OpenRouter 不直接支援 embedding
        建議使用 Ollama 或 OpenAI 的 embedding
        """
        raise NotImplementedError(
            "OpenRouter 不支援 embedding，請使用 OpenAI 或 Ollama"
        )


class OllamaProvider(LLMProvider):
    """
    Ollama Provider 實現
    使用本地或遠端 Ollama 服務
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        初始化 Ollama Provider

        Args:
            base_url: Ollama API URL（可選，默認使用環境變數）
        """
        self.base_url = base_url or os.getenv(
            "OLLAMA_API_URL",
            "http://localhost:11434"
        )
        self.provider_name = "Ollama"

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """執行 Ollama 聊天完成請求"""
        try:
            # Ollama API 格式
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }

            if max_tokens:
                payload["options"]["num_predict"] = max_tokens

            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120.0
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API 錯誤: {response.status_code}")

            data = response.json()

            return {
                'content': data.get('message', {}).get('content', ''),
                'usage': {
                    'prompt_tokens': data.get('prompt_eval_count', 0),
                    'completion_tokens': data.get('eval_count', 0),
                    'total_tokens': data.get('prompt_eval_count', 0) + data.get('eval_count', 0)
                },
                'model': data.get('model', model),
                'provider': self.provider_name,
                'raw_response': data  # 保留原始回應
            }
        except Exception as e:
            raise Exception(f"Ollama API 調用失敗: {str(e)}")

    def embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> Optional[List[float]]:
        """生成 Ollama embedding"""
        try:
            model = model or os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

            response = httpx.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": model,
                    "prompt": text
                },
                timeout=60.0
            )

            if response.status_code != 200:
                print(f"⚠️ Ollama Embedding API 錯誤: {response.status_code}")
                return None

            data = response.json()
            return data.get('embedding')

        except Exception as e:
            print(f"❌ Ollama Embedding 生成失敗: {e}")
            return None


# ============================================================
# Factory 函數（推薦使用方式）
# ============================================================

_default_provider = None


def get_llm_provider(
    provider_type: Optional[str] = None,
    reset: bool = False
) -> LLMProvider:
    """
    獲取 LLM Provider（單例模式）

    Args:
        provider_type: Provider 類型 ('openai', 'openrouter', 'ollama')
                      若為 None，則從環境變數 LLM_PROVIDER 讀取
        reset: 是否重置單例（用於測試）

    Returns:
        LLMProvider 實例

    環境變數:
        LLM_PROVIDER: 'openai' | 'openrouter' | 'ollama'（默認: openai）
        OPENAI_API_KEY: OpenAI API Key
        OPENROUTER_API_KEY: OpenRouter API Key
        OLLAMA_API_URL: Ollama API URL（默認: http://localhost:11434）
    """
    global _default_provider

    if reset:
        _default_provider = None

    if _default_provider is None:
        provider_type = provider_type or os.getenv("LLM_PROVIDER", "openai").lower()

        if provider_type == "openrouter":
            _default_provider = OpenRouterProvider()
        elif provider_type == "ollama":
            _default_provider = OllamaProvider()
        else:  # 默認使用 openai
            _default_provider = OpenAIProvider()

        print(f"🔧 [LLM Provider] 使用 Provider: {_default_provider.provider_name}")

    return _default_provider


# ============================================================
# 便利函數（向後兼容）
# ============================================================

def chat_completion(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    provider_type: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    執行聊天完成請求（便利函數）

    Args:
        model: 模型名稱
        messages: 訊息列表
        temperature: 溫度參數
        max_tokens: 最大 tokens
        provider_type: Provider 類型（可選）
        **kwargs: 其他參數

    Returns:
        包含 content 和 usage 的字典
    """
    provider = get_llm_provider(provider_type)
    return provider.chat_completion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )


# ============================================================
# 使用範例與測試
# ============================================================

if __name__ == "__main__":
    import asyncio

    def test_llm_provider():
        """測試 LLM Provider"""
        print("=" * 60)
        print("測試 LLM Provider")
        print("=" * 60)

        # 測試 1: OpenAI Provider
        print("\n📝 測試 1: OpenAI Provider")
        try:
            provider = OpenAIProvider()
            print(f"✅ Provider 初始化成功: {provider.provider_name}")

            messages = [
                {"role": "user", "content": "請用一句話介紹台灣"}
            ]
            result = provider.chat_completion(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=100
            )

            print(f"   回應: {result['content'][:100]}...")
            print(f"   使用: {result['usage']}")
            print(f"   Provider: {result['provider']}")
        except Exception as e:
            print(f"❌ 測試失敗: {e}")

        # 測試 2: Factory 函數
        print("\n📝 測試 2: Factory 函數")
        try:
            # 使用環境變數決定 provider
            provider = get_llm_provider()
            print(f"✅ 使用 Provider: {provider.provider_name}")

            result = chat_completion(
                model=os.getenv("INTENT_MODEL", "gpt-3.5-turbo"),
                messages=[{"role": "user", "content": "你好"}],
                temperature=0.5
            )

            print(f"   回應: {result['content']}")
        except Exception as e:
            print(f"❌ 測試失敗: {e}")

        # 測試 3: OpenRouter（如果配置了）
        print("\n📝 測試 3: OpenRouter Provider（需要配置）")
        if os.getenv("OPENROUTER_API_KEY"):
            try:
                provider = OpenRouterProvider()
                print(f"✅ Provider 初始化成功: {provider.provider_name}")

                messages = [
                    {"role": "user", "content": "Say hello in Chinese"}
                ]
                result = provider.chat_completion(
                    model="anthropic/claude-3.5-sonnet",
                    messages=messages,
                    temperature=0.7
                )

                print(f"   回應: {result['content']}")
                print(f"   Provider: {result['provider']}")
            except Exception as e:
                print(f"⚠️ 跳過（未配置或錯誤）: {e}")
        else:
            print("⚠️ 跳過（未設定 OPENROUTER_API_KEY）")

        # 測試 4: Ollama（如果有本地服務）
        print("\n📝 測試 4: Ollama Provider（需要本地服務）")
        try:
            provider = OllamaProvider()
            print(f"✅ Provider 初始化成功: {provider.provider_name}")

            messages = [
                {"role": "user", "content": "你好，請用中文回答"}
            ]
            result = provider.chat_completion(
                model="llama2",
                messages=messages,
                temperature=0.7
            )

            print(f"   回應: {result['content'][:100]}...")
            print(f"   Provider: {result['provider']}")
        except Exception as e:
            print(f"⚠️ 跳過（Ollama 未運行或錯誤）: {e}")

        print("\n" + "=" * 60)
        print("測試完成！")
        print("=" * 60)

    # 執行測試
    test_llm_provider()
