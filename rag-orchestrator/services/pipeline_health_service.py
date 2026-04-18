"""
Pipeline 健康檢查服務
聚合各元件健康檢查，提供統一的健康狀態查詢介面
"""
import os
import time
import asyncio
import logging
from datetime import datetime, timezone
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

    async def check_all_components(self) -> Dict[str, Any]:
        """
        並行檢查所有元件，每個 checker 5 秒 timeout，整體 15 秒內完成。

        Returns:
            PipelineHealthResponse dict，包含：
            - overall_status: "healthy" / "degraded" / "unhealthy"
            - healthy_count: 正常元件數
            - total_count: 總元件數
            - components: ComponentCheckResult 列表
            - checked_at: ISO 8601 時間戳
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

        checker_names = [
            "PostgreSQL", "Redis", "Embedding API",
            "Reranker", "LLM API", "Vector Search", "Keyword Search",
        ]
        checker_is_core = [
            True, False, True,
            False, True, False, False,
        ]

        tasks = [asyncio.wait_for(checker(), timeout=5.0) for checker in checkers]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        components: List[Dict[str, Any]] = []

        for i, raw in enumerate(raw_results):
            if isinstance(raw, Exception):
                name = checker_names[i]
                is_core = checker_is_core[i]
                if isinstance(raw, asyncio.TimeoutError):
                    error_msg = "檢查逾時（5 秒）"
                else:
                    error_msg = str(raw)
                components.append({
                    "name": name,
                    "status": "unhealthy",
                    "latency_ms": 5000.0,
                    "version": None,
                    "error": error_msg,
                    "is_core": is_core,
                    "degradation_impact": None if is_core else DEGRADATION_IMPACTS.get(name),
                })
            else:
                components.append(raw)

        # 計算整體狀態
        healthy_count = sum(
            1 for c in components if c["status"] == "healthy"
        )
        total_count = len(components)

        core_all_healthy = all(
            c["status"] == "healthy"
            for c in components
            if c["is_core"]
        )
        any_core_unhealthy = any(
            c["status"] != "healthy"
            for c in components
            if c["is_core"]
        )

        if healthy_count == total_count:
            overall_status = "healthy"
        elif any_core_unhealthy:
            overall_status = "unhealthy"
        else:
            # 核心全部正常，非核心有異常
            overall_status = "degraded"

        return {
            "overall_status": overall_status,
            "healthy_count": healthy_count,
            "total_count": total_count,
            "components": components,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

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

    # ------------------------------------------------------------------
    # 端到端測試
    # ------------------------------------------------------------------

    async def run_e2e_test(self) -> Dict[str, Any]:
        """
        端到端 pipeline 測試：embedding → vector search → keyword search → reranker
        使用固定測試查詢「漏水怎麼處理」，vendor_id=2。

        Returns:
            E2ETestResponse dict，包含：
            - overall_status: "healthy" / "unhealthy"
            - test_query: 使用的測試查詢
            - stages: E2EStageResult 列表
            - total_latency_ms: 總耗時
            - tested_at: ISO 8601 時間戳
        """
        test_query = "漏水怎麼處理"
        vendor_id = 2
        stages: List[Dict[str, Any]] = []
        stage_names = ["Embedding", "Vector Search", "Keyword Search", "Reranker"]
        total_start = time.time()
        failed = False

        # --- 共享狀態：跨階段傳遞中間結果 ---
        embedding: Optional[List[float]] = None
        vector_results: List[Dict[str, Any]] = []
        keyword_results: List[Dict[str, Any]] = []

        # ------ Stage 1: Embedding ------
        if not failed:
            start = time.time()
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        self.embedding_api_url,
                        json={"text": test_query},
                    )
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"Embedding API returned {resp.status_code}"
                    )
                embedding = resp.json().get("embedding")
                if not embedding:
                    raise RuntimeError("Embedding API returned empty embedding")
                latency = (time.time() - start) * 1000
                stages.append({
                    "stage": "Embedding",
                    "status": "healthy",
                    "latency_ms": round(latency, 2),
                    "error": None,
                    "detail": f"維度 {len(embedding)}",
                })
            except Exception as e:
                latency = (time.time() - start) * 1000
                stages.append({
                    "stage": "Embedding",
                    "status": "unhealthy",
                    "latency_ms": round(latency, 2),
                    "error": str(e),
                    "detail": None,
                })
                failed = True

        # ------ Stage 2: Vector Search ------
        if not failed:
            start = time.time()
            try:
                vector_str = "[" + ",".join(map(str, embedding)) + "]"
                config = get_db_config()
                conn = psycopg2.connect(**config)
                try:
                    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cursor.execute(
                        """
                        SELECT id, question_summary, answer
                        FROM knowledge_base
                        WHERE vendor_id = %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT 5
                        """,
                        (vendor_id, vector_str),
                    )
                    rows = cursor.fetchall()
                    vector_results = [dict(r) for r in rows]
                    cursor.close()
                finally:
                    conn.close()

                result_count = len(vector_results)
                if result_count == 0:
                    raise RuntimeError("Vector search returned 0 results")
                latency = (time.time() - start) * 1000
                stages.append({
                    "stage": "Vector Search",
                    "status": "healthy",
                    "latency_ms": round(latency, 2),
                    "error": None,
                    "detail": f"找到 {result_count} 筆",
                })
            except Exception as e:
                latency = (time.time() - start) * 1000
                stages.append({
                    "stage": "Vector Search",
                    "status": "unhealthy",
                    "latency_ms": round(latency, 2),
                    "error": str(e),
                    "detail": None,
                })
                failed = True

        # ------ Stage 3: Keyword Search ------
        if not failed:
            start = time.time()
            try:
                import jieba

                tokens = list(jieba.cut(test_query))
                valid_tokens = [t for t in tokens if t.strip() and len(t) > 1]

                config = get_db_config()
                conn = psycopg2.connect(**config)
                try:
                    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    if valid_tokens:
                        like_clauses = " OR ".join(
                            ["question ILIKE %s" for _ in valid_tokens]
                        )
                        params: list = [vendor_id] + [f"%{t}%" for t in valid_tokens]
                        cursor.execute(
                            f"""
                            SELECT id, question_summary, answer
                            FROM knowledge_base
                            WHERE vendor_id = %s AND ({like_clauses})
                            LIMIT 5
                            """,
                            tuple(params),
                        )
                        rows = cursor.fetchall()
                        keyword_results = [dict(r) for r in rows]
                    else:
                        keyword_results = []
                    cursor.close()
                finally:
                    conn.close()

                latency = (time.time() - start) * 1000
                stages.append({
                    "stage": "Keyword Search",
                    "status": "healthy",
                    "latency_ms": round(latency, 2),
                    "error": None,
                    "detail": f"找到 {len(keyword_results)} 筆（tokens: {valid_tokens}）",
                })
            except Exception as e:
                latency = (time.time() - start) * 1000
                stages.append({
                    "stage": "Keyword Search",
                    "status": "unhealthy",
                    "latency_ms": round(latency, 2),
                    "error": str(e),
                    "detail": None,
                })
                failed = True

        # ------ Stage 4: Reranker ------
        if not failed:
            start = time.time()
            try:
                # 合併 vector + keyword 結果作為 reranker 輸入
                seen_ids: set = set()
                candidates: List[Dict[str, Any]] = []
                for r in vector_results + keyword_results:
                    rid = r.get("id")
                    if rid not in seen_ids:
                        seen_ids.add(rid)
                        candidates.append({
                            "id": rid,
                            "answer": r.get("answer", ""),
                            "content": r.get("answer", ""),
                            "question_summary": r.get("question_summary", ""),
                        })

                if not candidates:
                    raise RuntimeError("No candidates available for reranker")

                request_data = {
                    "query": test_query,
                    "candidates": candidates,
                    "top_k": min(5, len(candidates)),
                }

                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"{self.semantic_api_url}/rerank",
                        json=request_data,
                    )

                if resp.status_code != 200:
                    raise RuntimeError(
                        f"Reranker API returned {resp.status_code}"
                    )

                rerank_data = resp.json()
                reranked = rerank_data.get("results", [])
                latency = (time.time() - start) * 1000
                stages.append({
                    "stage": "Reranker",
                    "status": "healthy",
                    "latency_ms": round(latency, 2),
                    "error": None,
                    "detail": f"重排 {len(candidates)} 筆 → 回傳 {len(reranked)} 筆",
                })
            except Exception as e:
                latency = (time.time() - start) * 1000
                stages.append({
                    "stage": "Reranker",
                    "status": "unhealthy",
                    "latency_ms": round(latency, 2),
                    "error": str(e),
                    "detail": None,
                })
                failed = True

        # ------ 補齊 skipped 階段 ------
        completed_stage_names = {s["stage"] for s in stages}
        for name in stage_names:
            if name not in completed_stage_names:
                stages.append({
                    "stage": name,
                    "status": "skipped",
                    "latency_ms": 0.0,
                    "error": None,
                    "detail": "因前一階段失敗而跳過",
                })

        total_latency = (time.time() - total_start) * 1000
        all_healthy = all(s["status"] == "healthy" for s in stages)

        return {
            "overall_status": "healthy" if all_healthy else "unhealthy",
            "test_query": test_query,
            "stages": stages,
            "total_latency_ms": round(total_latency, 2),
            "tested_at": datetime.now(timezone.utc).isoformat(),
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
