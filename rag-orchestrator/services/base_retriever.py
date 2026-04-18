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

        # Query Rewriter
        self.query_rewriter = None
        if os.getenv("ENABLE_QUERY_REWRITE", "false").lower() == "true":
            try:
                from .query_rewriter import get_query_rewriter
                self.query_rewriter = get_query_rewriter()
                if self.query_rewriter.enabled:
                    print("✅ Query Rewriter 已啟用")
                else:
                    self.query_rewriter = None
            except Exception as e:
                print(f"⚠️ Query Rewriter 載入失敗: {e}")

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
        return_unfiltered: bool = False,
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
            return_unfiltered: debug 旁路（followup-debug-visibility 選項 A）。
                True 時跳過 application 端 threshold 過濾，回傳所有候選
                （含 final similarity < threshold 的低分項目）。
                仍會套用 top_k 與 final similarity 排序。
                僅供 chat.py 在 include_debug_info=True 時使用，
                產線流量維持 False（預設）。
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

        # Step 0: Query Rewriting（改寫查詢以提升向量匹配率）
        # 策略：用原始查詢 + 改寫查詢分別做向量檢索，取聯集後統一 rerank/finalize
        original_query = query
        rewritten_queries = []
        if self.query_rewriter:
            rewritten_queries = self.query_rewriter.rewrite(query)
            if rewritten_queries:
                print(f"   🔄 Query Rewrite: {rewritten_queries}")

        # Step 1: 生成查詢向量（原始查詢）
        query_embedding = await self._get_embedding(query)
        if not query_embedding:
            print("⚠️ 向量生成失敗，降級為純關鍵字檢索")
            if enable_keyword_fallback:
                return await self._keyword_search(query, vendor_id, top_k, **kwargs)
            return []

        # Step 2: 向量檢索（原始查詢）
        results = await self._vector_search(
            query_embedding, vendor_id, top_k, similarity_threshold, **kwargs
        )
        print(f"   向量檢索: 找到 {len(results)} 個結果")

        # Step 2.1: 改寫查詢的向量檢索（取聯集，去重）
        if rewritten_queries:
            existing_ids = {r.get('id') for r in results}
            rewrite_added = 0
            for rq in rewritten_queries:
                rq_embedding = await self._get_embedding(rq)
                if not rq_embedding:
                    continue
                rq_results = await self._vector_search(
                    rq_embedding, vendor_id, top_k, similarity_threshold, **kwargs
                )
                for rr in rq_results:
                    if rr.get('id') not in existing_ids:
                        rr['search_method'] = 'query_rewrite'
                        rr['rewrite_source'] = rq
                        results.append(rr)
                        existing_ids.add(rr.get('id'))
                        rewrite_added += 1
            if rewrite_added > 0:
                print(f"   🔄 改寫查詢新增: {rewrite_added} 個候選")

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

        # Step 4: 關鍵字加成（只寫 keyword_boost / keyword_matches）
        if enable_keyword_boost and results:
            results = await self._apply_keyword_boost(results, query)
            print(f"   關鍵字加成: 已應用")

        # Step 5: SemanticReranker（只寫 rerank_score）
        # hotfix (.kiro/issues/reranker-returning-zero.md)：
        # 限制送進 reranker 的候選，避免 bge-reranker-base CPU 推論超時。
        # 兩層過濾：
        #   a) vector_similarity < RERANKER_MIN_VECTOR_SIMILARITY 的 vector 項直接丟棄
        #      （rerank 後幾乎不可能進 top_k，送進去浪費推論時間）
        #      ⚠️ keyword_fallback 項不受下限影響（它們 vector_similarity=0 是設計預設值，
        #      不代表「低相關」而是「走 keyword 路徑」）
        #   b) 若剩餘候選仍超過 RERANKER_INPUT_LIMIT，優先保留 keyword_fallback，
        #      再以 vector_similarity 補足 vector 項
        if self.semantic_reranker and len(results) > 0:
            rerank_input_limit = int(os.getenv("RERANKER_INPUT_LIMIT", "20"))
            rerank_min_vec = float(os.getenv("RERANKER_MIN_VECTOR_SIMILARITY", "0.3"))

            keyword_items = [
                r for r in results
                if r.get('search_method') == 'keyword_fallback'
            ]
            vector_items = [
                r for r in results
                if r.get('search_method') != 'keyword_fallback'
            ]

            # 下限過濾（只作用於 vector 項；keyword_fallback 項一律保留）
            filtered_vector = [
                r for r in vector_items
                if r.get('vector_similarity', 0) >= rerank_min_vec
            ]
            dropped_by_floor = len(vector_items) - len(filtered_vector)
            vector_items = filtered_vector

            before = len(results)
            # 上限截斷
            if len(keyword_items) + len(vector_items) > rerank_input_limit:
                if len(keyword_items) >= rerank_input_limit:
                    results = keyword_items[:rerank_input_limit]
                else:
                    vector_items.sort(
                        key=lambda x: x.get('vector_similarity', 0),
                        reverse=True,
                    )
                    vector_slots = rerank_input_limit - len(keyword_items)
                    results = vector_items[:vector_slots] + keyword_items
            else:
                results = vector_items + keyword_items

            if before != len(results):
                print(
                    f"   Reranker 過濾: {before} → {len(results)} 筆"
                    f"（下限 vector>={rerank_min_vec} 砍 {dropped_by_floor} 筆；"
                    f"剩 {len(keyword_items)} 筆 keyword_fallback"
                    f" + {len(results) - len(keyword_items)} 筆 vector）"
                )

            if results:
                results = self._apply_semantic_reranker(query, results, top_k)
                print(f"   Reranker: 已重排序")
            else:
                print(f"   Reranker: 過濾後無候選，跳過 rerank")

        # Step 6: 統一計算 final similarity 與 score_source（task 4.3）
        results = self._finalize_scores(results)

        # Step 7: application 端 threshold 過濾（比對 final similarity）
        # followup-debug-visibility 選項 A：return_unfiltered=True 時跳過過濾，
        # 讓 chat.py debug 模式拿到完整候選（含低分），供 chat-test 顯示。
        if not return_unfiltered:
            before_filter = len(results)
            results = [r for r in results if r.get('similarity', 0) >= similarity_threshold]
            if before_filter != len(results):
                print(f"   閾值過濾: {before_filter} → {len(results)} 筆 (>= {similarity_threshold})")
        else:
            print(f"   [debug] 跳過 threshold 過濾（return_unfiltered=True），保留 {len(results)} 筆完整候選")

        # Step 8: 依 final similarity 排序，回傳 top_k
        results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        results = results[:top_k]

        print(f"   最終結果: {len(results)} 個")
        return results

    async def _apply_keyword_boost(self, results: List[Dict], query: str) -> List[Dict]:
        """
        應用關鍵字加成（task 4.1）

        只寫入 keyword_boost（倍率）與 keyword_matches，不修改 vector_similarity /
        keyword_score / similarity。最終 similarity 由 _finalize_scores 依公式重算。

        欄位語意：
        - keyword_boost：1.0 + raw_boost（例如 1.0、1.1、1.2、1.3）
          這個倍率由 _finalize_scores 在 keyword/vector 分支套用到 similarity。
        - keyword_matches：命中的關鍵字 list

        排序由 _finalize_scores 完成後在 retrieve() 末端執行，本方法不排序。

        Args:
            results: 檢索結果
            query: 原始查詢

        Returns:
            加成後的結果（順序保持原樣）
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

            # 應用加成（只寫入 keyword_boost 倍率與 keyword_matches）
            if matched_keywords:
                raw_boost = min(0.3, len(matched_keywords) * 0.1)  # 最多 30% 加成
                result['keyword_boost'] = 1.0 + raw_boost  # 倍率：1.0–1.3
                result['keyword_matches'] = matched_keywords

        return results

    def _apply_semantic_reranker(self, query: str, candidates: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        使用 SemanticReranker（外部服務）重排序（task 4.2）

        本方法只寫入 `rerank_score`，不修改 vector_similarity / keyword_score /
        keyword_boost / similarity / original_similarity。最終 similarity 由
        _finalize_scores 依公式重算（rerank 分支：0.1 × vector + 0.9 × rerank）。

        ⚠️ 必須保留 SOP→KB 欄位映射（reranker HTTP 服務需要 answer 與 question_summary）：
            if 'answer' not in item and 'content' in item:
                item['answer'] = item['content']
            if 'question_summary' not in item:
                item['question_summary'] = item.get('item_name', '')

        重構時不可誤刪此映射，否則 SOP 重排序會收到空字串。

        排序由 retrieve() 末端在 _finalize_scores 後執行，本方法不排序。
        """
        if not self.semantic_reranker or not candidates:
            return candidates

        try:
            # ⚠️ SOP→KB 欄位映射（reranker 服務需要 answer 與 question_summary）
            prepared = []
            for c in candidates:
                item = dict(c)
                if 'answer' not in item and 'content' in item:
                    item['answer'] = item['content']
                if 'question_summary' not in item:
                    item['question_summary'] = item.get('item_name', '')
                prepared.append(item)

            reranked = self.semantic_reranker.rerank(query, prepared, top_k=top_k)

            # Issue: reranker-returning-zero 暫行解法
            # 若 reranker 回傳全部 semantic_score 都是 0，視為 reranker 服務異常，
            # 回傳原始 candidates（不寫 rerank_score，讓 _finalize_scores 走 vector/keyword 分支）。
            # 避免 reranker 失效時所有候選的 final similarity 都只剩 10% vector 導致全部被 threshold 過濾。
            if reranked and all(
                (item.get('semantic_score') or 0) == 0 for item in reranked
            ):
                print(
                    f"⚠️ Reranker 回傳全 0 分（{len(reranked)} 筆），視為服務異常，"
                    f"fallback 到原始候選（rerank_score 保持 None）"
                )
                return candidates

            # task 4.2：只寫入 rerank_score，不覆寫其他分數欄位
            for item in reranked:
                item['rerank_score'] = item.get('semantic_score', 0)

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

    def _finalize_scores(self, results: List[Dict]) -> List[Dict]:
        """
        統一計算最終 similarity 與 score_source（pipeline Stage 5）。

        對應規格：
        - requirements.md Requirement 4
        - design.md 決策 4

        三分支公式（按優先順序判斷）：
            1. rerank_score is not None:
                 similarity = 0.1 × vector_similarity + 0.9 × rerank_score
                 score_source = "rerank"
            2. keyword_score is not None:
                 similarity = min(1.0, max(vector_similarity, keyword_score) × keyword_boost)
                 score_source = "keyword"
            3. else:
                 similarity = min(1.0, vector_similarity × keyword_boost)
                 score_source = "vector"

        本方法只寫入 `similarity` 與 `score_source` 兩個欄位，
        不修改 vector_similarity / keyword_score / keyword_boost / rerank_score。

        Args:
            results: 各 pipeline 階段累積分數欄位的結果列表（dict / RetrievalResult）

        Returns:
            同一份 results（in-place 更新 similarity 與 score_source 後回傳）
        """
        rerank_count = 0
        keyword_count = 0
        vector_count = 0

        for r in results:
            vector = r.get('vector_similarity', 0.0) or 0.0
            keyword = r.get('keyword_score')
            boost = r.get('keyword_boost', 1.0) or 1.0
            rerank = r.get('rerank_score')

            if rerank is not None:
                r['similarity'] = 0.1 * vector + 0.9 * rerank
                r['score_source'] = 'rerank'
                rerank_count += 1
            elif keyword is not None:
                r['similarity'] = min(1.0, max(vector, keyword) * boost)
                r['score_source'] = 'keyword'
                keyword_count += 1
            else:
                r['similarity'] = min(1.0, vector * boost)
                r['score_source'] = 'vector'
                vector_count += 1

        print(
            f"   [Finalize] 計算 {len(results)} 筆，分數來源: "
            f"rerank={rerank_count}, keyword={keyword_count}, vector={vector_count}"
        )
        return results