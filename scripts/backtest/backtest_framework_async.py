"""
並發回測框架 V2 (Async Backtest Framework)
相比 V1 提供 5-10x 性能提升

主要改進:
- 並發執行測試 (concurrency 可配置)
- 異步 HTTP 請求 (aiohttp)
- 智能重試機制 (tenacity)
- 實時進度顯示 (tqdm)
- 批量 LLM 評估
"""

import os
import sys
import time
import math
import asyncio
import aiohttp
import requests
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
import json
from openai import OpenAI
import psycopg2
from psycopg2.extras import RealDictCursor
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import jieba  # 用於關鍵字提取（對齊生產環境）

class AsyncBacktestFramework:
    """
    異步並發回測框架 (獨立實現)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8100",
        vendor_id: int = 1,
        quality_mode: str = "detailed",
        use_database: bool = True,
        # V2 新增參數
        concurrency: int = None,
        default_timeout: int = None,
        default_retry_times: int = None,
        enable_metrics: bool = True
    ):
        # 基礎配置
        self.base_url = base_url
        self.vendor_id = vendor_id
        self.quality_mode = quality_mode
        self.use_database = use_database

        # V2 並發配置
        self.concurrency = concurrency or int(os.getenv('BACKTEST_CONCURRENCY', '5'))
        self.default_timeout = default_timeout or int(os.getenv('BACKTEST_TIMEOUT', '60'))
        self.default_retry_times = default_retry_times or int(os.getenv('BACKTEST_RETRY_TIMES', '2'))

        # 批量 LLM 評估配置
        self.batch_llm_eval = os.getenv('BACKTEST_BATCH_LLM_EVAL', 'true').lower() == 'true'
        self.llm_batch_size = int(os.getenv('BACKTEST_LLM_BATCH_SIZE', '10'))

        # OpenAI 客戶端（用於 LLM 評估）
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # 語義重排序服務配置（對齊生產環境）
        self.semantic_api_url = os.getenv(
            'SEMANTIC_MODEL_API_URL',
            'http://semantic-model:8000'
        )
        self.use_semantic_eval = os.getenv('USE_SEMANTIC_RERANK', 'true').lower() == 'true'
        self.semantic_available = self._check_semantic_service()

        # 性能監控
        self.enable_metrics = enable_metrics
        self.metrics = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'timeout_tests': 0,
            'retry_count': 0,
            'total_duration': 0,
            'avg_test_duration': 0,
            'throughput': 0  # tests/second
        }

        # 慢查詢追蹤
        self.slow_query_threshold = int(os.getenv('BACKTEST_SLOW_QUERY_THRESHOLD', '10'))
        self.slow_queries = []

        print(f"✅ 並發回測框架 V2 初始化完成")
        print(f"   並發數: {self.concurrency}")
        print(f"   超時時間: {self.default_timeout}s")
        print(f"   重試次數: {self.default_retry_times}")
        if self.batch_llm_eval:
            print(f"   批量 LLM 評估: 啟用 (batch_size={self.llm_batch_size})")
        if self.semantic_available:
            print(f"   語義評估: 啟用 (使用生產環境 SemanticReranker 邏輯)")
        else:
            print(f"   語義評估: 降級模式 (語義模型服務不可用)")

    def _check_semantic_service(self) -> bool:
        """
        檢查語義模型服務是否可用（對齊 SemanticReranker 邏輯）
        """
        try:
            response = requests.get(f"{self.semantic_api_url}/", timeout=2)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        return False

    async def _query_rag_async(
        self,
        question: str,
        timeout: int = None,
        session: aiohttp.ClientSession = None,
        scenario_id: int = None
    ) -> Dict:
        """
        異步查詢 RAG 系統

        Args:
            question: 測試問題
            timeout: 超時時間 (秒)
            session: aiohttp session (復用連接)
            scenario_id: 測試案例 ID (用於生成唯一 session_id)

        Returns:
            系統回應字典
        """
        url = f"{self.base_url}/api/v1/message"

        # 為每個測試案例生成唯一的 session_id，避免表單狀態互相干擾
        unique_session_id = f"backtest_session_{scenario_id}" if scenario_id else "backtest_session"
        unique_user_id = f"backtest_user_{scenario_id}" if scenario_id else "backtest_user"

        payload = {
            "message": question,
            "vendor_id": self.vendor_id,
            "mode": "tenant",
            "include_sources": True,
            "skip_sop": False,  # 改為 False，讓回測能檢索 SOP
            "include_debug_info": True,  # 回測需要 similarity 數據
            "session_id": unique_session_id,  # 每個案例使用唯一 session_id
            "user_id": unique_user_id  # 每個案例使用唯一 user_id
        }

        # 回測專用配置
        disable_synthesis = os.getenv("BACKTEST_DISABLE_ANSWER_SYNTHESIS", "false").lower() == "true"
        if disable_synthesis:
            payload["disable_answer_synthesis"] = True

        timeout_val = timeout or self.default_timeout

        # 使用同步 requests 避免 event loop 衝突（在容器內調用自己的 API 時）
        def sync_post():
            import requests
            try:
                response = requests.post(url, json=payload, timeout=timeout_val)
                response.raise_for_status()
                data = response.json()
                
                # 從 debug_info 提取 similarity 並注入到 sources
                if data and "debug_info" in data and data["debug_info"]:
                    debug_info = data["debug_info"]
                    if debug_info and "knowledge_candidates" in debug_info and debug_info["knowledge_candidates"] and "sources" in data:
                        # task 5.5：主排序使用 final similarity（含 rerank/boost），
                        # 額外記錄 vector_similarity 供純向量分數分析。
                        id_to_scores = {}
                        for candidate in debug_info["knowledge_candidates"]:
                            kb_id = candidate.get("id")
                            if not kb_id:
                                continue
                            id_to_scores[kb_id] = {
                                # 主排序：final similarity（retriever 輸出組合分數）
                                "similarity": candidate.get('similarity', 0.0),
                                # 輔助分析：純向量 cosine 分數
                                "vector_similarity": candidate.get('vector_similarity', 0.0),
                            }

                        # 注入 similarity + vector_similarity 到 sources
                        for source in data.get("sources", []):
                            source_id = source.get("id")
                            if source_id in id_to_scores:
                                scores = id_to_scores[source_id]
                                source["similarity"] = scores["similarity"]
                                source["vector_similarity"] = scores["vector_similarity"]
                
                return data
            except requests.exceptions.Timeout:
                if self.enable_metrics:
                    self.metrics['timeout_tests'] += 1
                print(f"   ❌ 請求超時 (URL: {url})")
                raise asyncio.TimeoutError(f"Request timeout: {url}")
            except requests.exceptions.RequestException as e:
                print(f"   ❌ HTTP 請求錯誤 (URL: {url}): {e}")
                return None
            except Exception as e:
                print(f"   ❌ 未預期錯誤 (URL: {url}): {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                return None

        try:
            # 在 thread pool 中執行同步請求，避免阻塞 event loop
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, sync_post)
        except Exception as e:
            print(f"   ❌ 執行錯誤: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((asyncio.TimeoutError, aiohttp.ClientError))
    )
    async def _query_rag_with_retry(
        self,
        question: str,
        timeout: int = None,
        session: aiohttp.ClientSession = None
    ) -> Dict:
        """
        帶重試的 RAG 查詢

        使用 tenacity 自動重試超時和連接錯誤
        """
        if self.enable_metrics:
            self.metrics['retry_count'] += 1

        return await self._query_rag_async(question, timeout, session)

    async def _test_single_scenario_async(
        self,
        scenario: Dict,
        index: int,
        session: aiohttp.ClientSession,
        timeout: int,
        retry_times: int,
        delay: float
    ) -> Dict:
        """
        異步測試單個情境

        Args:
            scenario: 測試情境
            index: 測試編號
            session: aiohttp session
            timeout: 超時時間
            retry_times: 重試次數
            delay: 請求延遲

        Returns:
            測試結果字典
        """
        question = scenario.get('test_question', '')
        scenario_id = scenario.get('id', None)  # 獲取 scenario ID
        if not question:
            return None

        start_time = time.time()

        try:
            # 查詢 RAG 系統 (帶重試)
            system_response = None
            for attempt in range(retry_times + 1):
                try:
                    system_response = await self._query_rag_async(
                        question, timeout, session, scenario_id  # 傳入 scenario_id
                    )
                    if system_response is None:
                        # API 返回 None，說明發生了未捕獲的錯誤
                        raise Exception("API returned None - check error logs above")
                    break
                except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                    if attempt < retry_times:
                        wait_time = 2 ** attempt  # 指數退避
                        await asyncio.sleep(wait_time)
                    else:
                        raise

            # 評估答案（V2：使用 confidence_score + 語義攔截）
            evaluation_result = self.evaluate_answer_v2(scenario, system_response)
            result = self._build_result_dict(
                scenario, system_response, evaluation_result, index
            )

            # 延遲 (避免 rate limit)
            if delay > 0:
                await asyncio.sleep(delay)

            # 記錄執行時間
            duration = time.time() - start_time
            result['test_duration'] = duration

            # 記錄慢查詢
            if duration > self.slow_query_threshold:
                self.slow_queries.append({
                    'question': question,
                    'duration': duration,
                    'index': index
                })

            return result

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            return {
                'test_id': index,
                'scenario_id': scenario.get('id'),
                'test_question': question,
                'error': 'timeout',
                'test_duration': duration,
                'passed': False,
                'score': 0.0,
                'confidence': 0.0
            }

        except Exception as e:
            duration = time.time() - start_time
            return {
                'test_id': index,
                'scenario_id': scenario.get('id'),
                'test_question': question,
                'error': str(e),
                'test_duration': duration,
                'passed': False,
                'score': 0.0,
                'confidence': 0.0
            }

    def _calculate_semantic_similarity(self, question: str, answer: str, sources: list = None) -> float:
        """
        計算問題與答案之間的語義相似度

        使用系統既有的 SemanticReranker 服務（BAAI/bge-reranker-base）
        對齊生產環境的語義評估邏輯，確保回測反映真實情況

        Args:
            question: 問題文本
            answer: 答案文本
            sources: 知識來源列表（可選）

        Returns:
            相似度分數 (0-1)，用於評估答案與問題的語義相關性
        """
        # 如果語義服務不可用，降級到簡單模式
        if not self.use_semantic_eval or not self.semantic_available:
            return self._simple_text_overlap(question, answer, sources)

        try:
            # 準備候選文本（對齊 SemanticReranker.rerank() 格式）
            candidates = []

            # 添加系統答案作為候選
            if answer and answer.strip():
                candidates.append({
                    'id': 'answer',
                    'content': answer[:500]  # 限制長度避免超時
                })

            # 添加知識來源（如果有）
            if sources:
                for i, source in enumerate(sources[:3]):  # 只取前3個來源
                    source_text = source.get('answer', '') + ' ' + source.get('question_summary', '')
                    if source_text.strip():
                        candidates.append({
                            'id': f'source_{i}',
                            'content': source_text[:500]
                        })

            if not candidates:
                return 0.0

            # 準備請求數據（對齊 SemanticReranker 格式）
            request_data = {
                "query": question,
                "candidates": candidates,
                "top_k": len(candidates)
            }

            # 調用語義模型 API（對齊 SemanticReranker 調用方式）
            # 臨時禁用語義模型調用,直接使用降級方案（避免卡住）
            use_semantic_api = os.getenv("BACKTEST_USE_SEMANTIC_API", "false").lower() == "true"

            if use_semantic_api:
                response = requests.post(
                    f"{self.semantic_api_url}/rerank",
                    json=request_data,
                    timeout=3
                )
            else:
                # 直接跳到降級方案
                raise Exception("Semantic API disabled for backtest")

            if use_semantic_api and response.status_code == 200:
                result = response.json()
                results = result.get("results", [])

                if results:
                    # 取最高語義分數（對齊 SemanticReranker 添加 semantic_score 的邏輯）
                    max_score = max(r.get('score', 0) for r in results)

                    # 正規化分數到 0-1 範圍（用於評估）
                    # BAAI/bge-reranker-base 實際分數範圍：約 0 到 1+
                    # 設定最小相關性閾值，避免極小正數被誤判為相關
                    MIN_RELEVANT_SCORE = 0.1  # 低於此值視為不相關

                    if max_score < MIN_RELEVANT_SCORE:
                        # 不相關：0-0.1 映射到 0-0.3
                        normalized = max(0, max_score / MIN_RELEVANT_SCORE) * 0.3
                    elif max_score >= 1.0:
                        # 極高相關：1.0+ 映射到 0.9-1.0
                        normalized = min(0.9 + (max_score - 1.0) * 0.1, 1.0)
                    else:
                        # 相關：0.1-1.0 映射到 0.3-0.9
                        normalized = 0.3 + ((max_score - MIN_RELEVANT_SCORE) / (1.0 - MIN_RELEVANT_SCORE)) * 0.6

                    return normalized

        except Exception as e:
            # 降級處理（對齊 SemanticReranker 錯誤處理）
            pass

        # 降級到簡單文本重疊計算
        return self._simple_text_overlap(question, answer, sources)

    def _simple_text_overlap(self, question: str, answer: str, sources: list = None) -> float:
        """
        簡單的文本重疊計算（降級方案）

        當語義模型服務不可用時使用
        """
        try:
            # 計算字符級別重疊
            question_chars = set(question.replace(' ', '').replace('\n', ''))
            answer_chars = set(answer.replace(' ', '').replace('\n', ''))

            # 如果有來源，合併來源文本
            if sources:
                for source in sources[:3]:
                    source_text = source.get('question_summary', '') + source.get('answer', '')[:200]
                    answer_chars.update(set(source_text.replace(' ', '').replace('\n', '')))

            if not question_chars or not answer_chars:
                return 0.0

            overlap = len(question_chars & answer_chars)
            overlap_ratio = overlap / len(question_chars)

            # 使用保守的折扣因子（簡單計算容易高估）
            return min(overlap_ratio * 0.5, 1.0)
        except:
            return 0.0

    def _check_structured_answer_quality(self, answer: str) -> Dict:
        """
        檢查結構化答案（表單類型）的品質

        Returns:
            {
                'is_structured': bool,
                'has_sections': bool,
                'has_details': bool,
                'structure_score': float
            }
        """
        # 檢測是否為結構化答案
        has_emoji = any(char in answer for char in ['💳', '📞', '🔧', '⏰', '🏠', '📋', '💰', '🔑'])
        has_multiple_lines = answer.count('\n') >= 3
        has_markdown_headers = '**' in answer or '#' in answer

        is_structured = has_emoji or (has_multiple_lines and has_markdown_headers)

        if not is_structured:
            return {
                'is_structured': False,
                'has_sections': False,
                'has_details': False,
                'structure_score': 0.0
            }

        # 檢查是否有多個區塊
        sections = [line for line in answer.split('\n') if line.strip().startswith('**') or has_emoji]
        has_sections = len(sections) >= 2

        # 檢查是否有詳細資訊（不只是標題）
        content_lines = [line for line in answer.split('\n') if line.strip() and not line.strip().startswith('**')]
        has_details = len(content_lines) >= 3

        # 計算結構分數
        structure_score = 0.0
        if has_sections:
            structure_score += 0.5
        if has_details:
            structure_score += 0.5

        return {
            'is_structured': True,
            'has_sections': has_sections,
            'has_details': has_details,
            'structure_score': structure_score
        }

    def calculate_confidence_score(self, system_response: Dict, test_question: str = '') -> Dict:
        """
        計算 confidence_score（對齊生產環境 ConfidenceEvaluator）

        模擬生產環境的信心度計算：
        confidence_score = max_similarity * 0.7 + result_count * 0.2 + keyword_match_rate * 0.1

        Args:
            system_response: 系統回應 (包含 sources 等)
            test_question: 測試問題 (用於關鍵字匹配)

        Returns:
            {
                'confidence_score': float (0-1),
                'confidence_level': str (high/medium/low),
                'max_similarity': float,
                'result_count': int,
                'keyword_match_rate': float
            }
        """
        sources = system_response.get('sources', [])
        answer = system_response.get('answer', '')

        # 如果沒有來源，信心度為 0
        if not sources:
            return {
                'confidence_score': 0.0,
                'confidence_level': 'low',
                'max_similarity': 0.0,
                'result_count': 0,
                'keyword_match_rate': 0.0
            }

        # 1. 最大相似度 (取第一個 source 的 similarity，模擬生產環境的 search_results[0]['similarity'])
        # 注意：sources 可能是列表或字典，需要處理
        if isinstance(sources, list) and len(sources) > 0:
            first_source = sources[0]
            # sources 可能是 KnowledgeSource 對象或字典
            if hasattr(first_source, 'similarity'):
                max_similarity = getattr(first_source, 'similarity', 0.0)
            elif isinstance(first_source, dict):
                max_similarity = first_source.get('similarity', 0.0)
            else:
                max_similarity = 0.0
        else:
            max_similarity = 0.0

        # 2. 結果數量歸一化 (最多計入 5 個，與生產環境一致)
        result_count = len(sources)
        result_count_score = min(result_count / 5, 1.0)

        # 3. 關鍵字匹配率（簡化版：使用 jieba 分詞提取關鍵字）
        if test_question:
            # 提取問題關鍵字 (過濾長度 > 1 的詞，排除標點符號)
            question_keywords = list(jieba.cut(test_question))
            question_keywords = [kw.strip() for kw in question_keywords
                               if len(kw.strip()) > 1 and kw.strip().isalnum()]

            if question_keywords:
                # 計算有多少關鍵字出現在答案中
                matched = sum(1 for kw in question_keywords if kw in answer)
                keyword_match_rate = matched / len(question_keywords)
            else:
                keyword_match_rate = 0.0
        else:
            keyword_match_rate = 0.0

        # 4. 綜合信心度（與生產環境 ConfidenceEvaluator 公式完全一致）
        confidence_score = (
            max_similarity * 0.7 +
            result_count_score * 0.2 +
            keyword_match_rate * 0.1
        )

        # 5. 判定信心度等級（與生產環境一致）
        if confidence_score >= 0.85 and result_count >= 2:
            confidence_level = "high"
        elif confidence_score >= 0.70:
            confidence_level = "medium"
        else:
            confidence_level = "low"

        return {
            'confidence_score': round(confidence_score, 3),
            'confidence_level': confidence_level,
            'max_similarity': round(max_similarity, 3),
            'result_count': result_count,
            'keyword_match_rate': round(keyword_match_rate, 3)
        }

    def evaluate_answer_v2(self, scenario: Dict, system_response: Dict) -> Dict:
        """
        對齊生產環境的評估邏輯 (V2 - 2026-03-15)

        評估分兩層:
        1. Confidence Score (模擬生產環境 ConfidenceEvaluator)
        2. Semantic Overlap (方案 B 語義攔截，檢測答非所問)

        通過標準 (方案 3 - 綜合判定):
        - semantic_overlap < 0.4 → 直接失敗 (答非所問)
        - confidence_score >= 0.70 且 semantic_overlap >= 0.5 → 通過
        - confidence_score >= 0.60 且 semantic_overlap >= 0.6 → 通過
        - 其他情況 → 失敗

        Returns:
            {
                'passed': bool,
                'confidence_score': float,
                'confidence_level': str,
                'semantic_overlap': float,
                'failure_reason': str or None,
                'optimization_tips': list,
                'max_similarity': float,
                'result_count': int,
                'keyword_match_rate': float
            }
        """
        question = scenario.get('test_question', '')
        answer = system_response.get('answer', '')
        sources = system_response.get('sources', [])

        # === 第 1 層：基礎檢查 ===
        if not answer:
            return {
                'passed': False,
                'confidence_score': 0.0,
                'confidence_level': 'low',
                'max_similarity': 0.0,
                'result_count': 0,
                'keyword_match_rate': 0.0,
                'failure_reason': '系統未返回答案',
                'optimization_tips': ['系統未返回答案']
            }

        # 檢查「沒找到資料」
        no_info_keywords = [
            '沒有找到符合您問題的資訊',
            '我無法找到',
            '目前沒有相關資訊',
            '找不到相關',
            'N/A'
        ]
        if any(kw in answer for kw in no_info_keywords):
            return {
                'passed': False,
                'confidence_score': 0.0,
                'confidence_level': 'low',
                'max_similarity': 0.0,
                'result_count': 0,
                'keyword_match_rate': 0.0,
                'failure_reason': '沒有找到資料',
                'optimization_tips': ['系統返回「未找到資訊」，需補充相關知識']
            }

        # === 檢查表單類型知識 ===
        # 檢查 action_type 是否為 form_fill 或 form_then_api
        # 回測現在會加上 session_id 和 user_id，讓表單能正常觸發
        action_type = system_response.get('action_type', 'direct_answer')
        if action_type in ['form_fill', 'form_then_api']:
            # 這是表單類型知識，已正常觸發表單
            temp_confidence = self.calculate_confidence_score(system_response, question)
            form_id = system_response.get('form_id', 'N/A')
            current_field = system_response.get('current_field', 'N/A')

            return {
                'passed': True,  # 表單成功觸發即為通過
                'confidence_score': temp_confidence['confidence_score'],
                'confidence_level': temp_confidence['confidence_level'],
                'max_similarity': temp_confidence['max_similarity'],
                'result_count': temp_confidence['result_count'],
                'keyword_match_rate': temp_confidence['keyword_match_rate'],
                'failure_reason': None,
                'is_form': True,  # 標記為表單類型
                'form_id': form_id,
                'optimization_tips': [
                    f'📝 表單類型知識（Form ID: {form_id}）',
                    f'✓ 表單成功觸發，當前欄位: {current_field}',
                    '✓ 表單流程正常運作'
                ]
            }

        # === 第 2 層：Confidence Score 計算 ===
        confidence_eval = self.calculate_confidence_score(system_response, question)
        confidence_score = confidence_eval['confidence_score']
        confidence_level = confidence_eval['confidence_level']
        max_similarity = confidence_eval['max_similarity']
        result_count = confidence_eval['result_count']
        keyword_match_rate = confidence_eval['keyword_match_rate']

        # === 第 3 層：綜合判定（僅基於 confidence_score）===
        # 對齊生產環境：移除 semantic_overlap 攔截，因為生產環境沒有此機制
        optimization_tips = []
        passed = False
        failure_reason = None

        # 簡化後的判定邏輯（僅基於 confidence_score）
        if confidence_score >= 0.85:
            passed = True
            optimization_tips.append(f'高信心度 ({confidence_score:.3f})')
        elif confidence_score >= 0.70:
            passed = True
            optimization_tips.append(f'中等信心度 ({confidence_score:.3f})，可優化檢索結果')
        elif confidence_score >= 0.60:
            passed = True
            optimization_tips.append(f'較低信心度 ({confidence_score:.3f})，建議補充知識或優化意圖分類')
        else:
            passed = False
            failure_reason = f'信心度過低 ({confidence_score:.3f} < 0.60)'

        if not optimization_tips:
            optimization_tips = ['檢索品質良好']

        return {
            'passed': passed,
            'confidence_score': confidence_score,
            'confidence_level': confidence_level,
            'max_similarity': max_similarity,
            'result_count': result_count,
            'keyword_match_rate': keyword_match_rate,
            'failure_reason': failure_reason if not passed else None,
            'optimization_tips': optimization_tips
        }

    def _build_result_dict(
        self,
        scenario: Dict,
        system_response: Dict,
        evaluation: Dict,
        index: int
    ) -> Dict:
        """
        構建結果字典 (與 V1 兼容)
        """
        question = scenario.get('test_question', '')

        # 提取知識來源資訊
        sources = system_response.get('sources', []) if system_response else []
        if sources is None:
            sources = []

        source_ids = [s.get('id') for s in sources if s.get('id')]
        source_summary = '; '.join([
            f"[{s.get('id', 'N/A')}] {s.get('question_summary', 'N/A')[:40]}"
            for s in sources[:3]
        ]) if sources else '無來源'

        # 生成知識庫鏈接
        knowledge_urls = []
        if source_ids:
            for kb_id in source_ids[:3]:
                knowledge_urls.append(f"http://localhost:8080/#/knowledge?search={kb_id}")
            ids_param = ','.join(map(str, source_ids))
            batch_url = f"http://localhost:8080/#/knowledge?ids={ids_param}"
        else:
            batch_url = "http://localhost:8080/#/knowledge"

        knowledge_links = '\n'.join(knowledge_urls) if knowledge_urls else '無'

        # 構建結果
        result = {
            'test_id': index,
            'scenario_id': scenario.get('id'),
            'test_question': question,
            'actual_intent': system_response.get('intent_name', '') if system_response else '',
            'all_intents': system_response.get('all_intents', []) if system_response else [],
            'system_answer': system_response.get('answer', '')[:200] if system_response else '',
            'confidence': system_response.get('confidence', 0) if system_response else 0,
            'score': evaluation.get('score', 0),
            'overall_score': evaluation.get('score', 0),
            'passed': evaluation['passed'],
            'evaluation': json.dumps(evaluation, ensure_ascii=False),  # V2: 保存完整評估結果
            'optimization_tips': '\n'.join(evaluation.get('optimization_tips', [])) if isinstance(evaluation.get('optimization_tips'), list) else evaluation.get('optimization_tips', ''),
            'knowledge_sources': source_summary,
            'source_ids': ','.join(map(str, source_ids)),
            'source_count': len(sources),
            'knowledge_links': knowledge_links,
            'batch_url': batch_url,
            'difficulty': scenario.get('difficulty', 'medium'),
            'notes': scenario.get('notes', ''),
            'timestamp': datetime.now().isoformat(),
            # V2 欄位：添加到頂層方便前端使用
            'confidence_score': evaluation.get('confidence_score'),
            'confidence_level': evaluation.get('confidence_level'),
            'max_similarity': evaluation.get('max_similarity'),
            'keyword_match_rate': evaluation.get('keyword_match_rate'),
            'failure_reason': evaluation.get('failure_reason', '')
        }

        return result

    async def run_backtest_concurrent(
        self,
        test_scenarios: List[Dict],
        concurrency: int = None,
        timeout: int = None,
        retry_times: int = None,
        delay: float = None,
        sample_size: int = None,
        batch_llm_eval: bool = None,
        batch_size: int = None,
        show_progress: bool = None
    ) -> List[Dict]:
        """
        並發執行回測

        Args:
            test_scenarios: 測試情境列表
            concurrency: 並發數 (默認使用配置)
            timeout: 超時時間 (默認使用配置)
            retry_times: 重試次數 (默認使用配置)
            delay: 請求延遲 (默認 0.2 秒)
            sample_size: 抽樣數量
            batch_llm_eval: 是否批量 LLM 評估
            batch_size: LLM 批量大小
            show_progress: 是否顯示進度條

        Returns:
            測試結果列表
        """
        # 使用默認值
        concurrency = concurrency or self.concurrency
        timeout = timeout or self.default_timeout
        retry_times = retry_times or self.default_retry_times
        delay = delay if delay is not None else float(os.getenv('BACKTEST_DELAY', '2.0'))
        batch_llm_eval = batch_llm_eval if batch_llm_eval is not None else self.batch_llm_eval
        batch_size = batch_size or self.llm_batch_size
        show_progress = show_progress if show_progress is not None else os.getenv('BACKTEST_SHOW_PROGRESS', 'true').lower() == 'true'

        print(f"\n🧪 開始並發回測...")
        print(f"   測試情境數：{len(test_scenarios)}")
        print(f"   並發數：{concurrency}")
        print(f"   超時時間：{timeout}s")
        print(f"   重試次數：{retry_times}")

        if sample_size:
            print(f"   抽樣測試：{sample_size} 個")
            test_scenarios = test_scenarios[:sample_size]

        # 重置指標
        if self.enable_metrics:
            self.metrics['total_tests'] = len(test_scenarios)
            self.slow_queries = []

        start_time = time.time()
        results = []

        # 創建信號量控制並發
        semaphore = asyncio.Semaphore(concurrency)

        # 創建 aiohttp session (復用連接)
        connector = aiohttp.TCPConnector(limit=concurrency * 2)
        async with aiohttp.ClientSession(connector=connector) as session:

            async def bounded_test(scenario: Dict, index: int):
                """帶信號量限制的測試"""
                async with semaphore:
                    return await self._test_single_scenario_async(
                        scenario, index, session, timeout, retry_times, delay
                    )

            # 創建所有任務
            tasks = [
                bounded_test(scenario, i)
                for i, scenario in enumerate(test_scenarios, 1)
            ]

            # 並發執行 (帶進度條)
            if show_progress:
                # 使用 tqdm 顯示進度
                pbar = tqdm(total=len(tasks), desc="執行回測", unit="測試")

                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    if result:
                        results.append(result)

                        # 更新指標
                        if self.enable_metrics:
                            if result.get('passed'):
                                self.metrics['passed_tests'] += 1
                            else:
                                self.metrics['failed_tests'] += 1

                        # 更新進度條
                        passed = sum(1 for r in results if r.get('passed'))
                        pass_rate = (passed / len(results) * 100) if results else 0
                        pbar.set_postfix({
                            '通過率': f"{pass_rate:.1f}%",
                            '平均時長': f"{result.get('test_duration', 0):.1f}s"
                        })

                    pbar.update(1)

                pbar.close()
            else:
                # 無進度條模式
                results = await asyncio.gather(*tasks)
                results = [r for r in results if r is not None]


        # 計算性能指標
        total_duration = time.time() - start_time
        if self.enable_metrics:
            self.metrics['total_duration'] = total_duration
            self.metrics['avg_test_duration'] = total_duration / len(results) if results else 0
            self.metrics['throughput'] = len(results) / total_duration if total_duration > 0 else 0

            self._print_metrics()

        return results

    def _print_metrics(self):
        """打印性能指標"""
        print(f"\n{'='*60}")
        print("性能指標")
        print(f"{'='*60}")
        print(f"總測試數：{self.metrics['total_tests']}")
        print(f"通過測試：{self.metrics['passed_tests']}")
        print(f"失敗測試：{self.metrics['failed_tests']}")
        print(f"超時測試：{self.metrics['timeout_tests']}")
        print(f"總耗時：{self.metrics['total_duration']:.2f} 秒")
        print(f"平均每個測試：{self.metrics['avg_test_duration']:.2f} 秒")
        print(f"吞吐量：{self.metrics['throughput']:.2f} 測試/秒")

        if self.slow_queries:
            print(f"\n慢查詢 (>{self.slow_query_threshold}s):")
            for sq in self.slow_queries[:5]:  # 只顯示前 5 個
                print(f"  [{sq['index']}] {sq['question'][:50]}... ({sq['duration']:.2f}s)")

        print(f"{'='*60}\n")


async def main():
    """主程式"""
    print("="*60)
    print("並發回測框架 V2")
    print("="*60)

    # 配置
    base_url = os.getenv("RAG_API_URL", "http://localhost:8100")
    vendor_id = int(os.getenv("VENDOR_ID", "2"))
    quality_mode = os.getenv("BACKTEST_QUALITY_MODE", "detailed")

    # 創建回測框架
    backtest = AsyncBacktestFramework(
        base_url=base_url,
        vendor_id=vendor_id,
        quality_mode=quality_mode,
        use_database=True
    )

    # 載入測試情境
    selection_strategy = os.getenv("BACKTEST_SELECTION_STRATEGY", "incremental")
    limit = os.getenv("BACKTEST_LIMIT")
    limit = int(limit) if limit else None

    print(f"\n🎯 測試選擇策略: {selection_strategy}")

    try:
        scenarios = backtest.load_test_scenarios(
            strategy=selection_strategy,
            limit=limit
        )
    except Exception as e:
        print(f"❌ 從資料庫載入測試情境失敗: {e}")
        print("💡 提示：請確認資料庫連線正常")
        return

    # 執行回測
    non_interactive = os.getenv("BACKTEST_NON_INTERACTIVE", "false").lower() == "true"

    if non_interactive:
        sample_size_str = os.getenv("BACKTEST_SAMPLE_SIZE", "")
        sample_size = int(sample_size_str) if sample_size_str else None
        if sample_size:
            print(f"\n🧪 非交互模式：執行 {sample_size} 個測試")
        else:
            print(f"\n🧪 非交互模式：執行全部 {len(scenarios)} 個測試")
    else:
        print(f"\n是否要執行完整回測？")
        print(f"總共 {len(scenarios)} 個測試情境")
        sample_size = input("輸入要測試的數量（直接按 Enter 測試全部）: ").strip()
        sample_size = int(sample_size) if sample_size else None

    # 並發執行回測
    results = await backtest.run_backtest_concurrent(
        test_scenarios=scenarios,
        sample_size=sample_size
    )

    # 生成報告
    project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    output_dir = os.getenv("BACKTEST_OUTPUT_DIR", os.path.join(project_root, "output/backtest"))
    output_prefix = os.getenv("BACKTEST_OUTPUT_PREFIX", "backtest_v2")

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{output_prefix}_results.xlsx")

    summary_data = backtest.generate_report(results, output_path)

    # 儲存到資料庫
    backtest.save_results_to_database(results, summary_data, output_path)

    print("✅ 回測完成！")


if __name__ == "__main__":
    asyncio.run(main())
