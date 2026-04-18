"""
Pipeline 健康檢查服務
聚合各元件健康檢查，提供統一的健康狀態查詢介面
"""
import os
import time
import asyncio
import logging
from typing import Dict, List, Optional, Any

import httpx
import psycopg2
import psycopg2.extras
import redis
from openai import AsyncOpenAI

from .db_utils import get_db_config

logger = logging.getLogger(__name__)

# 核心元件集合 — 任一失敗即判定整體 unhealthy
CORE_COMPONENTS = {"PostgreSQL", "Embedding API", "LLM API"}

# 非核心元件降級影響說明
DEGRADATION_IMPACTS = {
    "Redis": "快取不可用，回應速度可能下降",
    "Reranker": "重排序不可用，回答排序品質可能下降",
    "Vector Search": "向量檢索不可用，僅能使用關鍵字備選",
    "Keyword Search": "關鍵字備選不可用，僅能依賴向量檢索",
}


class PipelineHealthService:
    """
    Pipeline 健康檢查聚合服務

    提供 7 個元件的獨立健康檢查方法，以及聚合檢查介面。
    每個 checker 自行計時並捕獲所有例外，保證不會因單一元件失敗而影響整體檢查。
    """

    def __init__(self):
        """初始化健康檢查服務"""
        # Embedding API
        self.embedding_api_url = os.getenv(
            "EMBEDDING_API_URL",
            "http://embedding-api:5000/api/v1/embeddings"
        )
        # 從 embeddings URL 推導 health URL（同 host，路徑改為 /api/v1/health）
        base = self.embedding_api_url.rsplit("/api/v1/", 1)[0]
        self.embedding_health_url = f"{base}/api/v1/health"

        # Semantic Reranker
        self.semantic_api_url = os.getenv(
            "SEMANTIC_MODEL_API_URL",
            "http://aichatbot-semantic-model:8000"
        )

        # Redis
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))

        # OpenAI
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

    # ------------------------------------------------------------------
    # 聚合方法
    # ------------------------------------------------------------------

    async def check_all_components(self) -> List[Dict[str, Any]]:
        """
        並行檢查所有元件，每個 checker 5 秒 timeout。

        Returns:
            ComponentCheckResult 列表
        """
        checkers = [
            self._check_db,
            self._check_redis,
            self._check_embedding,
            self._check_reranker,
            self._check_llm,
            self._check_vector_search,
            self._check_keyword_search,
        ]

        tasks = [asyncio.wait_for(checker(), timeout=5.0) for checker in checkers]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: List[Dict[str, Any]] = []
        checker_names = [
            "PostgreSQL", "Redis", "Embedding API",
            "Reranker", "LLM API", "Vector Search", "Keyword Search",
        ]
        checker_is_core = [
            True, False, True,
            False, True, False, False,
        ]

        for i, raw in enumerate(raw_results):
            if isinstance(raw, Exception):
                # Timeout 或其他未捕獲例外
                name = checker_names[i]
                is_core = checker_is_core[i]
                results.append({
                    "name": name,
                    "status": "unhealthy",
                    "latency_ms": 5000.0,
                    "version": None,
                    "error": f"Checker timeout or error: {raw}",
                    "is_core": is_core,
                    "degradation_impact": None if is_core else DEGRADATION_IMPACTS.get(name),
                })
            else:
                results.append(raw)

        return results

    # ------------------------------------------------------------------
    # 核心元件 Checkers
    # ------------------------------------------------------------------

    async def _check_db(self) -> Dict[str, Any]:
        """PostgreSQL 健康檢查：SELECT 1 + 版本查詢"""
        start = time.time()
        try:
            config = get_db_config()
            conn = psycopg2.connect(**config)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()

                cursor.execute("SELECT version()")
                version_row = cursor.fetchone()
                version = version_row[0] if version_row else None

                cursor.close()
            finally:
                conn.close()

            latency = (time.time() - start) * 1000
            return {
                "name": "PostgreSQL",
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "version": version,
                "error": None,
                "is_core": True,
                "degradation_impact": None,
            }
        except Exception as e:
            latency = (time.time() - start) * 1000
            return {
                "name": "PostgreSQL",
                "status": "unhealthy",
                "latency_ms": round(latency, 2),
                "version": None,
                "error": str(e),
                "is_core": True,
                "degradation_impact": None,
            }

    async def _check_redis(self) -> Dict[str, Any]:
        """Redis 健康檢查：PING + 寫入測試"""
        start = time.time()
        try:
            client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=0,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            client.ping()

            # 寫入測試
            test_key = "pipeline_health:test"
            client.setex(test_key, 10, "ok")
            test_value = client.get(test_key)
            client.delete(test_key)

            if test_value != "ok":
                raise RuntimeError("Redis write-read verification failed")

            latency = (time.time() - start) * 1000
            info = client.info("server")
            version = info.get("redis_version")
            client.close()

            return {
                "name": "Redis",
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "version": version,
                "error": None,
                "is_core": False,
                "degradation_impact": DEGRADATION_IMPACTS["Redis"],
            }
        except Exception as e:
            latency = (time.time() - start) * 1000
            return {
                "name": "Redis",
                "status": "unhealthy",
                "latency_ms": round(latency, 2),
                "version": None,
                "error": str(e),
                "is_core": False,
                "degradation_impact": DEGRADATION_IMPACTS["Redis"],
            }

    async def _check_embedding(self) -> Dict[str, Any]:
        """Embedding API 健康檢查：GET /api/v1/health"""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.embedding_health_url)

            if response.status_code != 200:
                raise RuntimeError(
                    f"Embedding API returned {response.status_code}"
                )

            data = response.json()
            version = data.get("model") or data.get("version")

            latency = (time.time() - start) * 1000
            return {
                "name": "Embedding API",
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "version": version,
                "error": None,
                "is_core": True,
                "degradation_impact": None,
            }
        except Exception as e:
            latency = (time.time() - start) * 1000
            return {
                "name": "Embedding API",
                "status": "unhealthy",
                "latency_ms": round(latency, 2),
                "version": None,
                "error": str(e),
                "is_core": True,
                "degradation_impact": None,
            }

    async def _check_reranker(self) -> Dict[str, Any]:
        """Reranker 健康檢查：GET / to semantic-model，檢查 model_loaded"""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.semantic_api_url}/")

            if response.status_code != 200:
                raise RuntimeError(
                    f"Reranker API returned {response.status_code}"
                )

            data = response.json()
            model_loaded = data.get("model_loaded", False)
            version = data.get("model") or data.get("version")

            if not model_loaded:
                latency = (time.time() - start) * 1000
                return {
                    "name": "Reranker",
                    "status": "degraded",
                    "latency_ms": round(latency, 2),
                    "version": version,
                    "error": "Model not loaded",
                    "is_core": False,
                    "degradation_impact": DEGRADATION_IMPACTS["Reranker"],
                }

            latency = (time.time() - start) * 1000
            return {
                "name": "Reranker",
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "version": version,
                "error": None,
                "is_core": False,
                "degradation_impact": DEGRADATION_IMPACTS["Reranker"],
            }
        except Exception as e:
            latency = (time.time() - start) * 1000
            return {
                "name": "Reranker",
                "status": "unhealthy",
                "latency_ms": round(latency, 2),
                "version": None,
                "error": str(e),
                "is_core": False,
                "degradation_impact": DEGRADATION_IMPACTS["Reranker"],
            }

    async def _check_llm(self) -> Dict[str, Any]:
        """LLM API 健康檢查：openai.models.list() 驗證 API key 有效"""
        start = time.time()
        try:
            if not self.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY not set")

            client = AsyncOpenAI(api_key=self.openai_api_key)
            models_page = await client.models.list()

            # 取第一個模型名稱作為版本資訊
            model_ids = [m.id for m in models_page.data[:3]] if models_page.data else []
            version = ", ".join(model_ids) if model_ids else None

            latency = (time.time() - start) * 1000
            return {
                "name": "LLM API",
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "version": version,
                "error": None,
                "is_core": True,
                "degradation_impact": None,
            }
        except Exception as e:
            latency = (time.time() - start) * 1000
            return {
                "name": "LLM API",
                "status": "unhealthy",
                "latency_ms": round(latency, 2),
                "version": None,
                "error": str(e),
                "is_core": True,
                "degradation_impact": None,
            }

    # ------------------------------------------------------------------
    # 非核心元件 Checkers (端到端子流程驗證)
    # ------------------------------------------------------------------

    async def _check_vector_search(self) -> Dict[str, Any]:
        """向量檢索健康檢查：生成測試 embedding + 執行向量查詢，驗證 results > 0"""
        start = time.time()
        try:
            # Step 1: 取得測試 embedding
            test_query = "漏水怎麼處理"
            async with httpx.AsyncClient(timeout=5.0) as client:
                emb_response = await client.post(
                    self.embedding_api_url,
                    json={"text": test_query},
                )

            if emb_response.status_code != 200:
                raise RuntimeError(
                    f"Embedding API returned {emb_response.status_code} during vector search test"
                )

            embedding = emb_response.json().get("embedding")
            if not embedding:
                raise RuntimeError("Embedding API returned empty embedding")

            # Step 2: 向量查詢
            vector_str = "[" + ",".join(map(str, embedding)) + "]"
            config = get_db_config()
            conn = psycopg2.connect(**config)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id
                    FROM knowledge_base
                    ORDER BY embedding <=> %s::vector
                    LIMIT 5
                    """,
                    (vector_str,),
                )
                rows = cursor.fetchall()
                cursor.close()
            finally:
                conn.close()

            result_count = len(rows)
            if result_count == 0:
                raise RuntimeError("Vector search returned 0 results")

            latency = (time.time() - start) * 1000
            return {
                "name": "Vector Search",
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "version": None,
                "error": None,
                "is_core": False,
                "degradation_impact": DEGRADATION_IMPACTS["Vector Search"],
            }
        except Exception as e:
            latency = (time.time() - start) * 1000
            return {
                "name": "Vector Search",
                "status": "unhealthy",
                "latency_ms": round(latency, 2),
                "version": None,
                "error": str(e),
                "is_core": False,
                "degradation_impact": DEGRADATION_IMPACTS["Vector Search"],
            }

    async def _check_keyword_search(self) -> Dict[str, Any]:
        """關鍵字檢索健康檢查：jieba 分詞 + 執行關鍵字查詢，驗證無例外"""
        start = time.time()
        try:
            import jieba

            test_query = "漏水怎麼處理"
            tokens = list(jieba.cut(test_query))
            if not tokens:
                raise RuntimeError("jieba tokenization returned empty result")

            # 過濾有效 token（長度 > 1）
            valid_tokens = [t for t in tokens if t.strip() and len(t) > 1]

            # 執行關鍵字查詢
            config = get_db_config()
            conn = psycopg2.connect(**config)
            try:
                cursor = conn.cursor()
                # 簡單的 LIKE 查詢驗證 keyword search 可運作
                if valid_tokens:
                    like_clauses = " OR ".join(
                        ["question ILIKE %s" for _ in valid_tokens]
                    )
                    params = [f"%{t}%" for t in valid_tokens]
                    cursor.execute(
                        f"""
                        SELECT id
                        FROM knowledge_base
                        WHERE {like_clauses}
                        LIMIT 5
                        """,
                        tuple(params),
                    )
                    rows = cursor.fetchall()
                else:
                    rows = []

                cursor.close()
            finally:
                conn.close()

            latency = (time.time() - start) * 1000
            return {
                "name": "Keyword Search",
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "version": None,
                "error": None,
                "is_core": False,
                "degradation_impact": DEGRADATION_IMPACTS["Keyword Search"],
            }
        except Exception as e:
            latency = (time.time() - start) * 1000
            return {
                "name": "Keyword Search",
                "status": "unhealthy",
                "latency_ms": round(latency, 2),
                "version": None,
                "error": str(e),
                "is_core": False,
                "degradation_impact": DEGRADATION_IMPACTS["Keyword Search"],
            }
