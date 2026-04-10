"""
基礎檢索器 (Base Retriever)
提供 SOP 和知識庫共用的檢索邏輯
Date: 2026-02-11
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
import psycopg2
import psycopg2.extras
from services.db_utils import get_db_config
from services.embedding_utils import get_embedding_client
import jieba
import os


class BaseRetriever(ABC):
    """
    統一的檢索器基類
    提供共用的檢索策略：向量檢索 + 關鍵字備選 + Reranker
    """

    def __init__(self):
        """初始化基礎檢索器"""
        # 資料庫配置
        self.db_config = get_db_config()

        # Embedding 客戶端
        self.embedding_client = get_embedding_client()

        # Reranker：統一使用 SemanticReranker（外部 semantic-model 服務）
        self.reranker = None
        self.semantic_reranker = None
        if os.getenv("ENABLE_RERANKER", "false").lower() == "true":
            try:
                from .semantic_reranker import get_semantic_reranker
                sr = get_semantic_reranker()
                if sr.is_available:
                    self.semantic_reranker = sr
                    print("✅ Reranker 已啟用（SemanticReranker）")
                else:
                    print("⚠️ SemanticReranker 服務不可用，Reranker 未啟用")
            except Exception as e:
                print(f"⚠️ SemanticReranker 載入失敗: {e}，Reranker 未啟用")

        # 檢索配置
        self.default_top_k = 5
        self.default_similarity_threshold = 0.6
        self.keyword_fallback_enabled = True
        self.keyword_boost_enabled = True

    def _get_db_connection(self):
        """建立資料庫連接"""
        return psycopg2.connect(**self.db_config)

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """生成文字向量"""
        return await self.embedding_client.get_embedding(text, verbose=False)

    # ==================== 抽象方法（子類必須實作） ====================

    @abstractmethod
    async def _vector_search(
        self,
        query_embedding: List[float],
        vendor_id: int,
        top_k: int,
        similarity_threshold: float,
        **kwargs
    ) -> List[Dict]:
        """
        向量檢索（子類實作）

        Args:
            query_embedding: 查詢向量
            vendor_id: 業者 ID
            top_k: 返回數量
            similarity_threshold: 相似度閾值
            **kwargs: 其他參數

        Returns:
            檢索結果列表
        """
        pass

    @abstractmethod
    async def _keyword_search(
        self,
        query: str,
        vendor_id: int,
        limit: int,
        **kwargs
    ) -> List[Dict]:
        """
        關鍵字檢索（子類實作）

        Args:
            query: 查詢文字
            vendor_id: 業者 ID
            limit: 返回數量
            **kwargs: 其他參數

        Returns:
            檢索結果列表
        """
        pass

    @abstractmethod
    def _format_result(self, row: Dict) -> Dict:
        """
        格式化結果（子類實作）
        將資料庫記錄轉換為統一格式
        """
        pass

    # ==================== 共用邏輯 ====================

    async def retrieve(
        self,
        query: str,
        vendor_id: int,
        top_k: int = None,
        similarity_threshold: float = None,
        enable_keyword_fallback: bool = None,
        enable_keyword_boost: bool = None,
        **kwargs
    ) -> List[Dict]:
        """
        統一檢索介面
        實作向量檢索 + 關鍵字備選 + Reranker 策略

        Args:
            query: 查詢文字
            vendor_id: 業者 ID
            top_k: 返回數量
            similarity_threshold: 相似度閾值
            enable_keyword_fallback: 是否啟用關鍵字備選
            enable_keyword_boost: 是否啟用關鍵字加成
            **kwargs: 傳遞給子類的額外參數

        Returns:
            檢索結果列表
        """
        # 使用預設值
        top_k = top_k or self.default_top_k
        similarity_threshold = similarity_threshold or self.default_similarity_threshold
        enable_keyword_fallback = enable_keyword_fallback if enable_keyword_fallback is not None else self.keyword_fallback_enabled
        enable_keyword_boost = enable_keyword_boost if enable_keyword_boost is not None else self.keyword_boost_enabled

        print(f"\n🔍 [統一檢索] 查詢: {query}")
        print(f"   業者: {vendor_id}, Top-K: {top_k}, 閾值: {similarity_threshold}")
        print(f"   關鍵字備選: {enable_keyword_fallback}, 關鍵字加成: {enable_keyword_boost}")

        # Step 1: 生成查詢向量
        query_embedding = await self._get_embedding(query)
        if not query_embedding:
            print("⚠️ 向量生成失敗，降級為純關鍵字檢索")
            if enable_keyword_fallback:
                return await self._keyword_search(query, vendor_id, top_k, **kwargs)
            return []

        # Step 2: 向量檢索
        results = await self._vector_search(
            query_embedding, vendor_id, top_k, similarity_threshold, **kwargs
        )
        print(f"   向量檢索: 找到 {len(results)} 個結果")

        # Step 3: 關鍵字備選（如果結果不足）
        if enable_keyword_fallback and len(results) < top_k:
            print(f"   啟動關鍵字備選（需要補充 {top_k - len(results)} 個）")
            keyword_results = await self._keyword_search(
                query, vendor_id, top_k - len(results), **kwargs
            )

            # 合併結果（去重）
            existing_ids = {r.get('id') for r in results}
            added = 0
            for kr in keyword_results:
                if kr.get('id') not in existing_ids:
                    kr['search_method'] = 'keyword_fallback'
                    results.append(kr)
                    added += 1

            if added > 0:
                print(f"   關鍵字備選: 新增 {added} 個結果")

        # Step 4: 關鍵字加成
        if enable_keyword_boost and results:
            results = await self._apply_keyword_boost(results, query)
            print(f"   關鍵字加成: 已應用")

        # Step 5: SemanticReranker
        if self.semantic_reranker and len(results) > 0:
            results = self._apply_semantic_reranker(query, results, top_k)
            print(f"   Reranker: 已重排序")

        print(f"   最終結果: {len(results)} 個")
        return results

    async def _apply_keyword_boost(self, results: List[Dict], query: str) -> List[Dict]:
        """
        應用關鍵字加成

        Args:
            results: 檢索結果
            query: 原始查詢

        Returns:
            加成後的結果
        """
        query_tokens = set(jieba.cut(query.lower()))

        for result in results:
            keywords = result.get('keywords', [])
            if not keywords:
                continue

            # 計算關鍵字匹配
            matched_keywords = []
            for keyword in keywords:
                keyword_tokens = set(jieba.cut(keyword.lower()))
                if query_tokens & keyword_tokens:  # 有交集
                    matched_keywords.append(keyword)

            # 應用加成
            if matched_keywords:
                boost = min(0.3, len(matched_keywords) * 0.1)  # 最多 30% 加成
                original_score = result.get('similarity', 0)
                result['similarity'] = min(1.0, original_score * (1 + boost))
                result['keyword_matches'] = matched_keywords
                result['keyword_boost'] = boost

        # 重新排序
        results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        return results

    def _apply_semantic_reranker(self, query: str, candidates: List[Dict], top_k: int = 5) -> List[Dict]:
        """使用 SemanticReranker（外部服務）重排序"""
        if not self.semantic_reranker or not candidates:
            return candidates

        try:
            # SemanticReranker 需要 candidates 有 content 欄位
            # SOP 用 content，KB 用 answer + question_summary
            prepared = []
            for c in candidates:
                item = dict(c)
                if 'answer' not in item and 'content' in item:
                    item['answer'] = item['content']
                if 'question_summary' not in item:
                    item['question_summary'] = item.get('item_name', '')
                prepared.append(item)

            reranked = self.semantic_reranker.rerank(query, prepared, top_k=top_k)

            # 把 semantic_score 寫回 similarity（10% 原始 + 90% rerank）
            for item in reranked:
                original_score = item.get('similarity', 0)
                semantic_score = item.get('semantic_score', 0)
                item['original_similarity'] = original_score
                item['rerank_score'] = semantic_score
                item['similarity'] = original_score * 0.1 + semantic_score * 0.9

            reranked.sort(key=lambda x: x['similarity'], reverse=True)
            return reranked

        except Exception as e:
            print(f"⚠️ SemanticReranker 執行失敗: {e}")
            return candidates

    def _apply_reranker(self, query: str, candidates: List[Dict]) -> List[Dict]:
        """
        使用 Reranker 重排序

        Args:
            query: 查詢文字
            candidates: 候選結果

        Returns:
            重排序後的結果
        """
        if not self.reranker or not candidates:
            return candidates

        try:
            # 準備 Reranker 輸入
            pairs = []
            for candidate in candidates:
                # 根據結果類型選擇文字
                text = candidate.get('content') or candidate.get('answer', '')
                pairs.append([query, text])

            # 計算 rerank 分數
            scores = self.reranker.compute_score(pairs, normalize=True)
            if not isinstance(scores, list):
                scores = [scores]

            # 更新分數（10% 原始 + 90% rerank）
            for i, candidate in enumerate(candidates):
                original_score = candidate.get('similarity', 0)
                rerank_score = scores[i] if i < len(scores) else 0

                candidate['original_similarity'] = original_score
                candidate['rerank_score'] = rerank_score
                candidate['similarity'] = original_score * 0.1 + rerank_score * 0.9

            # 重新排序
            candidates.sort(key=lambda x: x['similarity'], reverse=True)

            return candidates

        except Exception as e:
            print(f"⚠️ Reranker 執行失敗: {e}")
            return candidates

    def _tokenize_chinese(self, text: str) -> set:
        """中文分詞"""
        return set(jieba.cut(text.lower()))