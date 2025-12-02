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
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
import json
from openai import OpenAI
import psycopg2
from psycopg2.extras import RealDictCursor
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# 添加父目錄到路徑以便導入 BacktestFramework
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest_framework import BacktestFramework


class AsyncBacktestFramework(BacktestFramework):
    """
    異步並發回測框架

    繼承自 BacktestFramework，添加並發執行能力
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
        # 調用父類初始化
        super().__init__(base_url, vendor_id, quality_mode, use_database)

        # V2 並發配置
        self.concurrency = concurrency or int(os.getenv('BACKTEST_CONCURRENCY', '5'))
        self.default_timeout = default_timeout or int(os.getenv('BACKTEST_TIMEOUT', '60'))
        self.default_retry_times = default_retry_times or int(os.getenv('BACKTEST_RETRY_TIMES', '2'))

        # 批量 LLM 評估配置
        self.batch_llm_eval = os.getenv('BACKTEST_BATCH_LLM_EVAL', 'true').lower() == 'true'
        self.llm_batch_size = int(os.getenv('BACKTEST_LLM_BATCH_SIZE', '10'))

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

    async def _query_rag_async(
        self,
        question: str,
        timeout: int = None,
        session: aiohttp.ClientSession = None
    ) -> Dict:
        """
        異步查詢 RAG 系統

        Args:
            question: 測試問題
            timeout: 超時時間 (秒)
            session: aiohttp session (復用連接)

        Returns:
            系統回應字典
        """
        url = f"{self.base_url}/api/v1/message"

        payload = {
            "message": question,
            "vendor_id": self.vendor_id,
            "mode": "tenant",
            "include_sources": True,
            "skip_sop": True
        }

        # 回測專用配置
        disable_synthesis = os.getenv("BACKTEST_DISABLE_ANSWER_SYNTHESIS", "false").lower() == "true"
        if disable_synthesis:
            payload["disable_answer_synthesis"] = True

        timeout_val = timeout or self.default_timeout
        timeout_obj = aiohttp.ClientTimeout(total=timeout_val)

        try:
            # 使用提供的 session 或創建新的
            if session:
                async with session.post(url, json=payload, timeout=timeout_obj) as response:
                    response.raise_for_status()
                    return await response.json()
            else:
                async with aiohttp.ClientSession() as new_session:
                    async with new_session.post(url, json=payload, timeout=timeout_obj) as response:
                        response.raise_for_status()
                        return await response.json()

        except asyncio.TimeoutError:
            if self.enable_metrics:
                self.metrics['timeout_tests'] += 1
            raise
        except aiohttp.ClientError as e:
            print(f"   ❌ HTTP 請求錯誤: {e}")
            return None
        except Exception as e:
            print(f"   ❌ 未預期錯誤: {e}")
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

    async def _llm_evaluate_async(
        self,
        question: str,
        answer: str
    ) -> Dict:
        """
        異步 LLM 評估 (單個)

        注意: OpenAI Python SDK 目前不支持原生異步
        這裡使用 run_in_executor 在線程池中執行
        """
        loop = asyncio.get_event_loop()

        def sync_llm_eval():
            return self.llm_evaluate_answer(question, answer)

        result = await loop.run_in_executor(None, sync_llm_eval)
        return result

    async def _llm_evaluate_batch_async(
        self,
        qa_pairs: List[Dict[str, str]]
    ) -> List[Dict]:
        """
        批量 LLM 評估

        Args:
            qa_pairs: [{"question": "...", "answer": "..."}, ...]

        Returns:
            評估結果列表
        """
        if not qa_pairs:
            return []

        # 構建批量提示
        batch_prompt = "請評估以下問答對的品質（1-5分，5分最佳）：\n\n"

        for i, pair in enumerate(qa_pairs, 1):
            batch_prompt += f"【問答 {i}】\n"
            batch_prompt += f"問題：{pair['question']}\n"
            batch_prompt += f"答案：{pair['answer']}\n\n"

        batch_prompt += """
請對每個問答對從以下維度評分：
1. 相關性 (Relevance): 答案是否直接回答問題？
2. 完整性 (Completeness): 答案是否完整涵蓋問題所問？
3. 準確性 (Accuracy): 答案內容是否準確可靠？
4. 意圖理解 (Intent Match): 答案是否正確理解問題意圖並回應？

請以 JSON 格式回覆（使用 evaluations 陣列）：
{
    "evaluations": [
        {
            "index": 1,
            "relevance": <1-5>,
            "completeness": <1-5>,
            "accuracy": <1-5>,
            "intent_match": <1-5>,
            "overall": <1-5>,
            "reasoning": "簡短說明評分理由"
        },
        ...
    ]
}
"""

        loop = asyncio.get_event_loop()

        def sync_batch_eval():
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": batch_prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )

                result = json.loads(response.choices[0].message.content)
                return result.get('evaluations', [])

            except Exception as e:
                print(f"⚠️  批量 LLM 評估失敗: {e}")
                # 降級為逐個評估
                return []

        results = await loop.run_in_executor(None, sync_batch_eval)

        # 如果批量失敗，降級為逐個評估
        if not results:
            print(f"   ⚠️  批量評估失敗，降級為逐個評估")
            tasks = [
                self._llm_evaluate_async(pair['question'], pair['answer'])
                for pair in qa_pairs
            ]
            results = await asyncio.gather(*tasks)

        return results

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
        if not question:
            return None

        start_time = time.time()

        try:
            # 查詢 RAG 系統 (帶重試)
            system_response = None
            for attempt in range(retry_times + 1):
                try:
                    system_response = await self._query_rag_async(
                        question, timeout, session
                    )
                    break
                except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                    if attempt < retry_times:
                        wait_time = 2 ** attempt  # 指數退避
                        await asyncio.sleep(wait_time)
                    else:
                        raise

            # 評估答案 (稍後批量處理 LLM 評估)
            evaluation_result = self.evaluate_answer(scenario, system_response)

            # 暫時只返回基礎評估，LLM 評估稍後批量處理
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
            'score': evaluation['score'],
            'overall_score': evaluation['score'],
            'passed': evaluation['passed'],
            'evaluation': json.dumps(evaluation.get('checks', {}), ensure_ascii=False),
            'optimization_tips': '\n'.join(evaluation.get('optimization_tips', [])) if isinstance(evaluation.get('optimization_tips'), list) else evaluation.get('optimization_tips', ''),
            'knowledge_sources': source_summary,
            'source_ids': ','.join(map(str, source_ids)),
            'source_count': len(sources),
            'knowledge_links': knowledge_links,
            'batch_url': batch_url,
            'difficulty': scenario.get('difficulty', 'medium'),
            'notes': scenario.get('notes', ''),
            'timestamp': datetime.now().isoformat()
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
        delay = delay if delay is not None else float(os.getenv('BACKTEST_DELAY', '0.2'))
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

        # 批量 LLM 評估
        if batch_llm_eval and self.quality_mode in ['detailed', 'hybrid']:
            print(f"\n📊 執行批量 LLM 評估...")
            results = await self._batch_llm_evaluation(results, batch_size)

            # 重新計算通過/失敗數 (LLM 評估可能改變 passed 狀態)
            if self.enable_metrics:
                self.metrics['passed_tests'] = sum(1 for r in results if r.get('passed'))
                self.metrics['failed_tests'] = sum(1 for r in results if not r.get('passed') and not r.get('error'))

        # 計算性能指標
        total_duration = time.time() - start_time
        if self.enable_metrics:
            self.metrics['total_duration'] = total_duration
            self.metrics['avg_test_duration'] = total_duration / len(results) if results else 0
            self.metrics['throughput'] = len(results) / total_duration if total_duration > 0 else 0

            self._print_metrics()

        return results

    async def _batch_llm_evaluation(
        self,
        results: List[Dict],
        batch_size: int
    ) -> List[Dict]:
        """
        批量執行 LLM 評估

        Args:
            results: 測試結果列表 (已包含基礎評估)
            batch_size: 批量大小

        Returns:
            更新後的結果列表
        """
        # 篩選需要評估的結果 (有答案的)
        to_evaluate = [
            (i, r) for i, r in enumerate(results)
            if r.get('system_answer') and not r.get('error')
        ]

        if not to_evaluate:
            return results

        print(f"   需評估: {len(to_evaluate)} 個測試")

        # 分批處理
        for batch_start in range(0, len(to_evaluate), batch_size):
            batch_end = min(batch_start + batch_size, len(to_evaluate))
            batch = to_evaluate[batch_start:batch_end]

            # 構建批量問答對
            qa_pairs = [
                {
                    'question': r.get('test_question', ''),
                    'answer': r.get('system_answer', '')
                }
                for _, r in batch
            ]

            # 批量評估
            evaluations = await self._llm_evaluate_batch_async(qa_pairs)

            # 更新結果
            for (idx, result), evaluation in zip(batch, evaluations):
                if evaluation and isinstance(evaluation, dict):
                    # 添加 LLM 評估結果
                    results[idx]['quality_eval'] = json.dumps(evaluation, ensure_ascii=False)
                    results[idx]['relevance'] = evaluation.get('relevance', 0)
                    results[idx]['completeness'] = evaluation.get('completeness', 0)
                    results[idx]['accuracy'] = evaluation.get('accuracy', 0)
                    results[idx]['intent_match'] = evaluation.get('intent_match', 0)
                    results[idx]['quality_overall'] = evaluation.get('overall', 0)
                    results[idx]['quality_reasoning'] = evaluation.get('reasoning', '')

                    # 重新計算混合評分
                    basic_eval = {'score': results[idx]['score'], 'passed': results[idx]['passed']}
                    overall_score = self._calculate_hybrid_score(basic_eval, evaluation)
                    passed = self._determine_pass_status(basic_eval, evaluation, overall_score)

                    results[idx]['overall_score'] = overall_score
                    results[idx]['passed'] = passed

            print(f"   已評估: {batch_end}/{len(to_evaluate)}")

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
    vendor_id = int(os.getenv("VENDOR_ID", "1"))
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
