"""
LLM Provider 抽象層
統一處理所有 LLM API 調用，支援多種 Provider（OpenAI, OpenRouter, Ollama）
"""
import os
import re
import httpx
from urllib.parse import urlsplit
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
from openai import OpenAI, AsyncOpenAI


def _meter_usage(model: str, result: dict) -> None:
    """usage-metering 統一出口鉤（spec usage-metering 2.1）：累計本請求 token。
    無計量 context（非 /message 路徑、開關關閉、回測 harness）時 no-op；
    任何失敗靜默——計量不得影響 LLM 呼叫。"""
    try:
        from services.usage_metering import add_llm_usage
        add_llm_usage(model, (result or {}).get('usage'))
    except Exception:
        pass



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

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化 OpenAI Provider

        Args:
            api_key: OpenAI API Key（可選，默認使用環境變數）
            base_url: 相容 OpenAI 的端點（可選）。⚠️ 給了 base_url 就**必須**明確給非空
                api_key——⛔ 退回 `OPENAI_API_KEY`（否則 OpenAI 金鑰會被送到別家端點；
                plan-oss-wiring-step1-20261018 §5 F6）。`None`＝現行行為逐字不變。
        """
        if base_url is None:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY 未設定")

            self.client = OpenAI(api_key=self.api_key)
            # 2026-09-07（探針 53）：SDK 預設 timeout 600 s，一個掛住的請求要等 10 分鐘才重試，
            # 對 6 s 回合預算是災難。`OPENAI_TIMEOUT_S` 設了才覆寫；未設維持 SDK 預設（⛔ 不改線上行為）。
            _timeout_env = os.environ.get("OPENAI_TIMEOUT_S", "").strip()
            self.async_client = (
                AsyncOpenAI(api_key=self.api_key, timeout=float(_timeout_env))
                if _timeout_env else AsyncOpenAI(api_key=self.api_key)
            )
        else:
            # ⛔ 錯誤訊息只放固定原因代碼——⛔ 含任何金鑰內容或長度。
            if not isinstance(base_url, str) or not base_url.strip():
                raise ValueError("agent_llm_base_url_empty")
            if not isinstance(api_key, str) or not api_key.strip():
                raise ValueError("agent_llm_api_key_required_with_base_url")
            self.api_key = api_key
            self.client = OpenAI(api_key=self.api_key, base_url=base_url)
            _timeout_env = os.environ.get("OPENAI_TIMEOUT_S", "").strip()
            self.async_client = (
                AsyncOpenAI(api_key=self.api_key, base_url=base_url, timeout=float(_timeout_env))
                if _timeout_env else AsyncOpenAI(api_key=self.api_key, base_url=base_url)
            )
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

            _meter_usage(model, result)     # usage-metering：統一出口計量（無 context 時 no-op）
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
            result = {
                'content': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                    'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                    'total_tokens': response.usage.total_tokens if response.usage else 0
                },
                'raw_response': response  # 保留原始回應供 function calling 使用
            }
            _meter_usage(model, result)     # usage-metering：統一出口計量
            return result
        except Exception as e:
            print(f"❌ OpenAI Async Chat Completion 失敗: {e}")
            raise

    async def stream_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        串流 OpenAI 聊天完成請求，逐 token 產出

        Yields:
            str: 每次產出一個 token/chunk 的文字
        """
        try:
            stream = await self.async_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            _meter_usage(model, {})    # 串流不回 usage：計 1 次呼叫、token 0（設計註記）
        except Exception as e:
            print(f"❌ OpenAI Stream Chat Completion 失敗: {e}")
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
# Factory 函數（支援混合 Provider 配置）
# ============================================================

# Provider 實例緩存（支援多個 Provider 共存）
_provider_cache: Dict[str, LLMProvider] = {}


def get_llm_provider(
    provider_type: Optional[str] = None,
    service_name: Optional[str] = None,
    reset: bool = False
) -> LLMProvider:
    """
    獲取 LLM Provider（支援混合配置）

    Args:
        provider_type: Provider 類型 ('openai', 'openrouter', 'ollama')
                      若為 None，則從環境變數讀取
        service_name: 服務名稱（用於查找服務專屬的 Provider 配置）
                     例如: 'intent_classifier', 'answer_optimizer', 'embedding'
        reset: 是否重置緩存（用於測試）

    Returns:
        LLMProvider 實例

    環境變數（按優先級）:
        1. {SERVICE_NAME}_PROVIDER: 服務專屬 Provider（最高優先級）
        2. LLM_PROVIDER: 全域預設 Provider
        3. 默認: 'openai'

    範例:
        # 使用全域 Provider
        provider = get_llm_provider()

        # 為特定服務使用專屬 Provider
        provider = get_llm_provider(service_name='query_rewriter')
        # 會查找 QUERY_REWRITER_PROVIDER 環境變數
        # ⚠️ 2026-09-12：這是全 repo 唯一有傳 service_name 的呼叫端
        #    （services/query_rewriter.py）——其餘皆無參數、只吃 LLM_PROVIDER

        # 直接指定 Provider 類型
        provider = get_llm_provider(provider_type='openrouter')
    """
    global _provider_cache

    if reset:
        _provider_cache = {}

    # 決定使用哪個 Provider
    if provider_type is None:
        if service_name:
            # 優先使用服務專屬的 Provider 配置
            env_key = f"{service_name.upper()}_PROVIDER"
            provider_type = os.getenv(env_key)

        # 若服務專屬配置不存在，使用全域配置
        if not provider_type:
            provider_type = os.getenv("LLM_PROVIDER", "openai")

    provider_type = provider_type.lower()

    # 從緩存獲取或創建新的 Provider 實例
    if provider_type not in _provider_cache:
        if provider_type == "openrouter":
            _provider_cache[provider_type] = OpenRouterProvider()
        elif provider_type == "ollama":
            _provider_cache[provider_type] = OllamaProvider()
        else:  # 默認使用 openai
            _provider_cache[provider_type] = OpenAIProvider()

        print(f"🔧 [LLM Provider] 初始化 {provider_type.upper()} Provider")

    provider = _provider_cache[provider_type]

    # 只在首次調用或服務切換時打印日誌
    if service_name:
        print(f"🔧 [LLM Provider] {service_name} 使用: {provider.provider_name}")

    return provider


# ============================================================
# 對話端點（agent 專用 provider；plan-oss-wiring-step1-20261018 §3.1）
# ============================================================
# 對話走相容 OpenAI 的別家端點（本機：Bedrock gpt-oss），照片／文件／健康檢查照舊走 OpenAI
# ⇒ 端點與金鑰**成對**、金鑰以檔案提供（Compose secret，⛔ 環境變數）、與全域
# `OPENAI_BASE_URL` 互斥（SDK 在 base_url 為 None 時讀它，會把 OpenAI 金鑰送去別處）。
# ⛔ 本段所有錯誤訊息只含「固定原因代碼＋路徑／變數名」——⛔ 含金鑰檔內容、長度、片段
#   （h11 驗標頭失敗訊息會帶完整 `Bearer <金鑰>`，故格式在源頭驗；§5 F1）。
# ⛔ 回傳的 provider **不進** `_provider_cache`（其他呼叫者照舊拿到 OpenAI 那一個）。

AGENT_LLM_BASE_URL_ENV = "AGENT_LLM_BASE_URL"
AGENT_LLM_API_KEY_FILE_ENV = "AGENT_LLM_API_KEY_FILE"

#: 金鑰檔允許字元（整串 fullmatch；空白、CR/LF、控制字元一律不合格）。
_AGENT_KEY_CHARSET = re.compile(r"[A-Za-z0-9+/=._~-]+")
#: 金鑰檔讀取上限（位元組）；超過即不合格，⛔ 整檔讀入未知大小的檔案。
_AGENT_KEY_FILE_MAX_BYTES = 4096


class AgentLLMConfigError(ValueError):
    """對話端點組態錯誤。訊息＝`<固定原因代碼>: <變數名或路徑>`，⛔ 含金鑰任何資訊。

    `code` 是固定原因代碼（封閉值域，供健康檢查等只放代碼的出口用，⛔ 回 `str(e)`）。
    """

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


def _agent_env_value(name: str) -> str:
    """讀環境變數；空字串（含只有空白）視同未設。"""
    return (os.environ.get(name) or "").strip()


def agent_endpoint_configured() -> bool:
    """`AGENT_LLM_BASE_URL` 是否有設（⛔ 不讀金鑰檔；供健康檢查決定是否列入）。"""
    return bool(_agent_env_value(AGENT_LLM_BASE_URL_ENV))


def agent_endpoint_host() -> Optional[str]:
    """對話端點的主機名（只供日誌／健康檢查顯示；⛔ 帶路徑、帳密、查詢字串）。未設回 None。"""
    base = _agent_env_value(AGENT_LLM_BASE_URL_ENV)
    if not base:
        return None
    try:
        return urlsplit(base).hostname
    except ValueError:
        return None


def _read_agent_key_file(path: str) -> str:
    """讀並驗證金鑰檔；不合格一律 raise `AgentLLMConfigError`（訊息只含代碼與路徑）。

    ⚠️ raise 一律放在 except 區塊**之外**：避免 `__context__` 掛上帶內容片段的原例外
    （例如 `UnicodeDecodeError` 的訊息含位元組值與位置）。
    """
    code = None
    raw = b""
    try:
        with open(path, "rb") as fh:
            raw = fh.read(_AGENT_KEY_FILE_MAX_BYTES + 1)
    except FileNotFoundError:
        code = "agent_llm_key_file_missing"
    except Exception:  # noqa: BLE001 — PermissionError／IsADirectoryError／其他 OSError
        code = "agent_llm_key_file_unreadable"
    if code is not None:
        raise AgentLLMConfigError(code, path)

    if len(raw) > _AGENT_KEY_FILE_MAX_BYTES:
        raise AgentLLMConfigError("agent_llm_key_file_too_large", path)

    text = None
    try:
        text = raw.decode("ascii")
    except Exception:  # noqa: BLE001 — UnicodeDecodeError 訊息含位元組片段，⛔ 外帶
        text = None
    if text is None:
        raise AgentLLMConfigError("agent_llm_key_file_invalid_charset", path)

    key = text.strip()
    if not key:
        raise AgentLLMConfigError("agent_llm_key_file_empty", path)
    if "\n" in key or "\r" in key:
        raise AgentLLMConfigError("agent_llm_key_file_multiline", path)
    if not _AGENT_KEY_CHARSET.fullmatch(key):
        raise AgentLLMConfigError("agent_llm_key_file_invalid_charset", path)
    return key


def build_agent_provider_from_env() -> Optional["OpenAIProvider"]:
    """依 `AGENT_LLM_BASE_URL`＋`AGENT_LLM_API_KEY_FILE` 建對話專用 provider。

    - 兩者皆未設（空字串視同未設）⇒ `None`（呼叫端照舊用 `get_llm_provider()`；正式機路徑不變）。
    - 只設其一 ⇒ raise（⛔ 端點配 `OPENAI_API_KEY`、⛔ 金鑰檔配 OpenAI 預設端點）。
    - 已設端點且環境有 `OPENAI_BASE_URL` ⇒ raise。
    - 金鑰檔不存在／不可讀／過大／空／多行／含 `[A-Za-z0-9+/=._~-]` 以外字元 ⇒ raise。
    - 成功 ⇒ **新的** `OpenAIProvider`（⛔ 進 `_provider_cache`）。

    健康檢查重用本函式驗設定與金鑰檔（單一驗證來源，⛔ 另寫一套）。
    """
    base_url = _agent_env_value(AGENT_LLM_BASE_URL_ENV)
    key_file = _agent_env_value(AGENT_LLM_API_KEY_FILE_ENV)
    if not base_url and not key_file:
        return None
    if not key_file:
        raise AgentLLMConfigError(
            "agent_llm_config_incomplete", f"{AGENT_LLM_API_KEY_FILE_ENV} 未設（{AGENT_LLM_BASE_URL_ENV} 已設）")
    if not base_url:
        raise AgentLLMConfigError(
            "agent_llm_config_incomplete", f"{AGENT_LLM_BASE_URL_ENV} 未設（{AGENT_LLM_API_KEY_FILE_ENV} 已設）")
    if "OPENAI_BASE_URL" in os.environ:
        raise AgentLLMConfigError(
            "agent_llm_openai_base_url_conflict", f"OPENAI_BASE_URL 與 {AGENT_LLM_BASE_URL_ENV} 不可並存")
    api_key = _read_agent_key_file(key_file)
    return OpenAIProvider(api_key=api_key, base_url=base_url)


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
