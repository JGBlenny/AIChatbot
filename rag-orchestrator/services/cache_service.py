"""
RAG 緩存服務 (Redis)

實作策略 2 (事件驅動) + 策略 1 (TTL 保底) 的混合緩存機制

分層緩存架構:
- Layer 1: Question Cache (相同問題直接返回)
- Layer 2: Vector Cache (常見問題 embedding)
- Layer 3: RAG Result Cache (檢索結果)
"""
import json
import hashlib
import os
from typing import Optional, Dict, Any, List
import redis


class CacheService:
    """RAG 緩存服務"""

    def __init__(self):
        # Redis 連接配置
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"

        # TTL 配置 (秒) - 作為失效通知的保底機制
        self.ttl_config = {
            "question_cache": int(os.getenv("CACHE_TTL_QUESTION", "3600")),      # 1 小時
            "vector_cache": int(os.getenv("CACHE_TTL_VECTOR", "7200")),          # 2 小時
            "rag_result_cache": int(os.getenv("CACHE_TTL_RAG_RESULT", "1800"))   # 30 分鐘
        }

        # Redis 連接
        self.redis_client: Optional[redis.Redis] = None

        if self.enabled:
            try:
                self.redis_client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # 測試連接
                self.redis_client.ping()
                print(f"✅ Redis 緩存已啟用: {self.redis_host}:{self.redis_port}")
            except Exception as e:
                print(f"⚠️  Redis 連接失敗，緩存已禁用: {e}")
                self.enabled = False
                self.redis_client = None
        else:
            print("ℹ️  緩存已禁用 (CACHE_ENABLED=false)")

    def _is_available(self) -> bool:
        """檢查緩存是否可用"""
        return self.enabled and self.redis_client is not None

    # ==================== 問題緩存 (Layer 1) ====================

    def _make_question_key(self, vendor_id: int, question: str, user_role: str = "customer") -> str:
        """生成問題緩存 key"""
        question_hash = hashlib.md5(question.lower().strip().encode()).hexdigest()[:16]
        return f"rag:question:{vendor_id}:{user_role}:{question_hash}"

    def get_cached_answer(self, vendor_id: int, question: str, user_role: str = "customer") -> Optional[Dict[str, Any]]:
        """
        獲取緩存的答案

        Returns:
            Dict 包含完整的 RAG 回應，或 None 如果緩存不存在
        """
        if not self._is_available():
            return None

        try:
            key = self._make_question_key(vendor_id, question, user_role)
            cached = self.redis_client.get(key)

            if cached:
                data = json.loads(cached)
                print(f"🎯 緩存命中: {key}")
                return data

            return None

        except Exception as e:
            print(f"⚠️  緩存讀取失敗: {e}")
            return None

    def cache_answer(
        self,
        vendor_id: int,
        question: str,
        answer_data: Dict[str, Any],
        user_role: str = "customer"
    ) -> bool:
        """
        緩存答案

        Args:
            vendor_id: 業者 ID
            question: 用戶問題
            answer_data: 完整的 RAG 回應數據
            user_role: 用戶角色

        Returns:
            True if successful
        """
        if not self._is_available():
            return False

        try:
            key = self._make_question_key(vendor_id, question, user_role)
            ttl = self.ttl_config["question_cache"]

            # 存儲為 JSON
            self.redis_client.setex(
                key,
                ttl,
                json.dumps(answer_data, ensure_ascii=False)
            )

            # 記錄關聯（用於失效）
            self._track_cache_relations(key, vendor_id, answer_data)

            print(f"💾 答案已緩存: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            print(f"⚠️  緩存寫入失敗: {e}")
            return False

    # ==================== 向量緩存 (Layer 2) ====================

    def _make_vector_key(self, text: str) -> str:
        """生成向量緩存 key"""
        text_hash = hashlib.md5(text.lower().strip().encode()).hexdigest()[:16]
        return f"rag:vector:{text_hash}"

    def get_cached_vector(self, text: str) -> Optional[List[float]]:
        """獲取緩存的向量"""
        if not self._is_available():
            return None

        try:
            key = self._make_vector_key(text)
            cached = self.redis_client.get(key)

            if cached:
                print(f"🎯 向量緩存命中: {key}")
                return json.loads(cached)

            return None

        except Exception as e:
            print(f"⚠️  向量緩存讀取失敗: {e}")
            return None

    def cache_vector(self, text: str, vector: List[float]) -> bool:
        """緩存向量"""
        if not self._is_available():
            return False

        try:
            key = self._make_vector_key(text)
            ttl = self.ttl_config["vector_cache"]

            self.redis_client.setex(
                key,
                ttl,
                json.dumps(vector)
            )

            return True

        except Exception as e:
            print(f"⚠️  向量緩存寫入失敗: {e}")
            return False

    # ==================== RAG 結果緩存 (Layer 3) ====================

    def _make_rag_result_key(self, vendor_id: int, intent_id: int, question: str) -> str:
        """生成 RAG 結果緩存 key"""
        question_hash = hashlib.md5(question.lower().strip().encode()).hexdigest()[:16]
        return f"rag:result:{vendor_id}:{intent_id}:{question_hash}"

    def get_cached_rag_result(
        self,
        vendor_id: int,
        intent_id: int,
        question: str
    ) -> Optional[List[Dict[str, Any]]]:
        """獲取緩存的 RAG 檢索結果"""
        if not self._is_available():
            return None

        try:
            key = self._make_rag_result_key(vendor_id, intent_id, question)
            cached = self.redis_client.get(key)

            if cached:
                print(f"🎯 RAG 結果緩存命中: {key}")
                return json.loads(cached)

            return None

        except Exception as e:
            print(f"⚠️  RAG 結果緩存讀取失敗: {e}")
            return None

    def cache_rag_result(
        self,
        vendor_id: int,
        intent_id: int,
        question: str,
        rag_results: List[Dict[str, Any]]
    ) -> bool:
        """緩存 RAG 檢索結果"""
        if not self._is_available():
            return False

        try:
            key = self._make_rag_result_key(vendor_id, intent_id, question)
            ttl = self.ttl_config["rag_result_cache"]

            self.redis_client.setex(
                key,
                ttl,
                json.dumps(rag_results, ensure_ascii=False)
            )

            # 記錄關聯
            self._track_rag_result_relations(key, vendor_id, intent_id)

            return True

        except Exception as e:
            print(f"⚠️  RAG 結果緩存寫入失敗: {e}")
            return False

    # ==================== 緩存失效 (事件驅動) ====================

    def _track_cache_relations(self, cache_key: str, vendor_id: int, answer_data: Dict[str, Any]):
        """記錄緩存與知識的關聯關係（用於失效）"""
        try:
            # 從答案數據中提取 knowledge_id 和 intent_id
            # 支援 sources 字段（當前格式）
            docs = answer_data.get("sources") or []

            for doc in docs:
                knowledge_id = doc.get("id")
                if knowledge_id:
                    # 記錄 knowledge -> cache key 的關聯
                    relation_key = f"rag:relation:knowledge:{knowledge_id}"
                    self.redis_client.sadd(relation_key, cache_key)
                    self.redis_client.expire(relation_key, self.ttl_config["question_cache"])

            # 處理 intent_ids 列表
            if "intent_ids" in answer_data:
                for intent_id in answer_data["intent_ids"]:
                    relation_key = f"rag:relation:intent:{intent_id}"
                    self.redis_client.sadd(relation_key, cache_key)
                    self.redis_client.expire(relation_key, self.ttl_config["question_cache"])

            # 記錄 vendor -> cache key 的關聯
            vendor_relation_key = f"rag:relation:vendor:{vendor_id}"
            self.redis_client.sadd(vendor_relation_key, cache_key)
            self.redis_client.expire(vendor_relation_key, self.ttl_config["question_cache"])

        except Exception as e:
            print(f"⚠️  緩存關聯記錄失敗: {e}")

    def _track_rag_result_relations(self, cache_key: str, vendor_id: int, intent_id: int):
        """記錄 RAG 結果緩存的關聯關係"""
        try:
            # Intent 關聯
            intent_relation_key = f"rag:relation:intent:{intent_id}"
            self.redis_client.sadd(intent_relation_key, cache_key)
            self.redis_client.expire(intent_relation_key, self.ttl_config["rag_result_cache"])

            # Vendor 關聯
            vendor_relation_key = f"rag:relation:vendor:{vendor_id}"
            self.redis_client.sadd(vendor_relation_key, cache_key)
            self.redis_client.expire(vendor_relation_key, self.ttl_config["rag_result_cache"])

        except Exception as e:
            print(f"⚠️  RAG 結果關聯記錄失敗: {e}")

    def invalidate_by_knowledge_id(self, knowledge_id: int) -> int:
        """
        按知識 ID 失效緩存（知識更新時觸發）

        Returns:
            失效的緩存條目數量
        """
        if not self._is_available():
            return 0

        try:
            relation_key = f"rag:relation:knowledge:{knowledge_id}"
            cache_keys = self.redis_client.smembers(relation_key)

            if cache_keys:
                count = self.redis_client.delete(*cache_keys)
                self.redis_client.delete(relation_key)
                print(f"🗑️  知識更新失效: knowledge_id={knowledge_id}, 清除 {count} 條緩存")
                return count

            return 0

        except Exception as e:
            print(f"⚠️  按知識 ID 失效緩存失敗: {e}")
            return 0

    def invalidate_by_intent_id(self, intent_id: int) -> int:
        """
        按意圖 ID 失效緩存（意圖更新時觸發）

        Returns:
            失效的緩存條目數量
        """
        if not self._is_available():
            return 0

        try:
            relation_key = f"rag:relation:intent:{intent_id}"
            cache_keys = self.redis_client.smembers(relation_key)

            if cache_keys:
                count = self.redis_client.delete(*cache_keys)
                self.redis_client.delete(relation_key)
                print(f"🗑️  意圖更新失效: intent_id={intent_id}, 清除 {count} 條緩存")
                return count

            return 0

        except Exception as e:
            print(f"⚠️  按意圖 ID 失效緩存失敗: {e}")
            return 0

    def invalidate_by_vendor_id(self, vendor_id: int) -> int:
        """
        按業者 ID 失效緩存（業者配置更新時觸發）

        Returns:
            失效的緩存條目數量
        """
        if not self._is_available():
            return 0

        try:
            relation_key = f"rag:relation:vendor:{vendor_id}"
            cache_keys = self.redis_client.smembers(relation_key)

            if cache_keys:
                count = self.redis_client.delete(*cache_keys)
                self.redis_client.delete(relation_key)
                print(f"🗑️  業者更新失效: vendor_id={vendor_id}, 清除 {count} 條緩存")
                return count

            return 0

        except Exception as e:
            print(f"⚠️  按業者 ID 失效緩存失敗: {e}")
            return 0

    def clear_all(self) -> bool:
        """清除所有 RAG 緩存"""
        if not self._is_available():
            return False

        try:
            # 查找所有 rag: 開頭的 key
            keys = self.redis_client.keys("rag:*")

            if keys:
                count = self.redis_client.delete(*keys)
                print(f"🗑️  清除所有緩存: {count} 條")

            return True

        except Exception as e:
            print(f"⚠️  清除所有緩存失敗: {e}")
            return False

    # ==================== 統計與監控 ====================

    def get_stats(self) -> Dict[str, Any]:
        """獲取緩存統計資訊"""
        if not self._is_available():
            return {
                "enabled": False,
                "reason": "Redis 未連接"
            }

        try:
            # 統計各類緩存數量
            question_keys = self.redis_client.keys("rag:question:*")
            vector_keys = self.redis_client.keys("rag:vector:*")
            result_keys = self.redis_client.keys("rag:result:*")
            relation_keys = self.redis_client.keys("rag:relation:*")

            # Redis 資訊
            info = self.redis_client.info("memory")

            return {
                "enabled": True,
                "redis_host": self.redis_host,
                "redis_port": self.redis_port,
                "cache_counts": {
                    "question_cache": len(question_keys),
                    "vector_cache": len(vector_keys),
                    "rag_result_cache": len(result_keys),
                    "relation_tracking": len(relation_keys)
                },
                "ttl_config": self.ttl_config,
                "memory_used_mb": round(info["used_memory"] / 1024 / 1024, 2),
                "peak_memory_mb": round(info["used_memory_peak"] / 1024 / 1024, 2)
            }

        except Exception as e:
            return {
                "enabled": True,
                "error": str(e)
            }

    def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        if not self._is_available():
            return {
                "status": "disabled",
                "enabled": self.enabled
            }

        try:
            # 測試 PING
            response = self.redis_client.ping()

            # 測試寫入
            test_key = "rag:healthcheck:test"
            self.redis_client.setex(test_key, 10, "ok")
            test_value = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)

            return {
                "status": "healthy",
                "ping": response,
                "write_test": test_value == "ok"
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
