#!/usr/bin/env python3
"""
全量回測 - 支持實時資料庫進度追蹤

功能：
1. 開始時創建 backtest_runs 記錄
2. 執行過程中實時更新進度到資料庫
3. 完成時保存所有結果到 backtest_results 表
4. 前端可以通過 API 查看實時進度
"""

import asyncio
import os
import sys
import datetime
import json
import psycopg2
from psycopg2.extras import execute_values

sys.path.insert(0, '/app/scripts/knowledge_extraction')
from backtest_framework_async import AsyncBacktestFramework


class ProgressTracker:
    """進度追蹤器 - 實時更新到資料庫"""

    def __init__(self, run_id, total_tests):
        self.run_id = run_id
        self.total_tests = total_tests
        self.executed = 0
        self.last_update = datetime.datetime.now()

        # 資料庫連接參數
        self.db_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'aichatbot_admin'),
            'user': os.getenv('DB_USER', 'aichatbot'),
            'password': os.getenv('DB_PASSWORD', '')
        }

    def update_progress(self, executed_count, force=False):
        """更新進度（每5秒或強制更新）"""
        self.executed = executed_count
        now = datetime.datetime.now()

        # 每5秒或強制更新一次
        if force or (now - self.last_update).total_seconds() >= 5:
            try:
                conn = psycopg2.connect(**self.db_params)
                cur = conn.cursor()

                cur.execute("""
                    UPDATE backtest_runs
                    SET executed_scenarios = %s
                    WHERE id = %s
                """, (executed_count, self.run_id))

                conn.commit()
                cur.close()
                conn.close()

                self.last_update = now
                print(f"✓ 進度已更新到資料庫: {executed_count}/{self.total_tests}")
            except Exception as e:
                print(f"⚠️  更新進度失敗: {e}")


async def main():
    print(f"\n{'='*60}")
    print(f"全量回測開始（支持實時進度追蹤）- {datetime.datetime.now()}")
    print(f"{'='*60}\n")

    # 獲取配置
    concurrency = int(os.getenv('BACKTEST_CONCURRENCY', '5'))
    quality_mode = os.getenv('BACKTEST_QUALITY_MODE', 'detailed')
    base_url = os.getenv('RAG_API_URL', 'http://localhost:8100')
    vendor_id = int(os.getenv('VENDOR_ID', '1'))

    # 資料庫連接參數
    db_params = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'aichatbot_admin'),
        'user': os.getenv('DB_USER', 'aichatbot'),
        'password': os.getenv('DB_PASSWORD', '')
    }

    # 創建回測框架
    backtest = AsyncBacktestFramework(
        base_url=base_url,
        vendor_id=vendor_id,
        quality_mode=quality_mode,
        use_database=True,
        concurrency=concurrency
    )

    # 載入測試
    print(f"\n📖 載入測試情境...")
    scenarios = backtest.load_test_scenarios(strategy='full')
    total_tests = len(scenarios)
    print(f'✅ 載入 {total_tests} 個測試情境\n')

    # 創建 backtest_runs 記錄
    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()

    start_time = datetime.datetime.now()

    cur.execute("""
        INSERT INTO backtest_runs (
            quality_mode, test_type, total_scenarios, executed_scenarios,
            status, rag_api_url, vendor_id, started_at, created_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) RETURNING id
    """, (
        quality_mode, 'full', total_tests, 0,
        'running', base_url, vendor_id, start_time, start_time
    ))

    run_id = cur.fetchone()[0]
    conn.commit()
    print(f"✅ 創建回測記錄 (Run ID: {run_id}, Status: running)\n")

    # 創建進度追蹤器
    tracker = ProgressTracker(run_id, total_tests)

    # 執行回測
    print(f"🧪 開始執行回測 (並發數: {concurrency})...")

    # 修改回測框架以支持進度回調
    async def run_with_progress():
        results = []
        semaphore = asyncio.Semaphore(concurrency)

        import aiohttp
        connector = aiohttp.TCPConnector(limit=concurrency * 2)

        async with aiohttp.ClientSession(connector=connector) as session:
            async def bounded_test(scenario, index):
                async with semaphore:
                    result = await backtest._test_single_scenario_async(
                        scenario, index, session,
                        backtest.default_timeout,
                        backtest.default_retry_times,
                        0.2
                    )

                    # 更新進度
                    tracker.update_progress(len(results) + 1)

                    return result

            tasks = [
                bounded_test(scenario, i)
                for i, scenario in enumerate(scenarios, 1)
            ]

            # 並發執行（無進度條，但有資料庫追蹤）
            for coro in asyncio.as_completed(tasks):
                result = await coro
                if result:
                    results.append(result)

        return results

    results = await run_with_progress()

    # 批量 LLM 評估
    if backtest.batch_llm_eval and quality_mode in ['detailed', 'hybrid']:
        print(f"\n📊 執行批量 LLM 評估...")
        results = await backtest._batch_llm_evaluation(results, backtest.llm_batch_size)

    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()

    # 統計結果
    passed_count = sum(1 for r in results if r.get('passed'))
    failed_count = sum(1 for r in results if not r.get('passed') and not r.get('error'))
    error_count = sum(1 for r in results if r.get('error'))
    pass_rate = (passed_count / len(results) * 100) if results else 0

    # 計算平均品質指標
    quality_results = [r for r in results if r.get('relevance') is not None]
    if quality_results:
        avg_relevance = sum(r.get('relevance', 0) for r in quality_results) / len(quality_results)
        avg_completeness = sum(r.get('completeness', 0) for r in quality_results) / len(quality_results)
        avg_accuracy = sum(r.get('accuracy', 0) for r in quality_results) / len(quality_results)
        avg_intent_match = sum(r.get('intent_match', 0) for r in quality_results) / len(quality_results)
        avg_quality_overall = sum(r.get('quality_overall', 0) for r in quality_results) / len(quality_results)
    else:
        avg_relevance = avg_completeness = avg_accuracy = avg_intent_match = avg_quality_overall = None

    # 生成報告文件
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'/app/output/backtest/backtest_full_c{concurrency}_{timestamp}.xlsx'

    print(f"\n📊 生成 Excel 報告...")
    backtest.generate_report(results, output_file)

    # 保存結果到資料庫
    print(f"💾 保存結果到資料庫...")
    try:
        # 準備批量插入數據
        result_values = []
        for r in results:
            result_values.append((
                run_id,
                r.get('scenario_id'),
                r.get('test_question'),
                r.get('system_answer'),
                r.get('actual_intent'),
                r.get('confidence', 0),
                r.get('score', 0),
                r.get('overall_score', 0),
                r.get('passed', False),
                r.get('evaluation', '{}'),
                r.get('optimization_tips', ''),
                r.get('knowledge_sources', ''),
                r.get('source_ids', ''),
                r.get('source_count', 0),
                r.get('difficulty', 'medium'),
                r.get('notes', ''),
                r.get('relevance'),
                r.get('completeness'),
                r.get('accuracy'),
                r.get('intent_match'),
                r.get('quality_overall'),
                r.get('quality_reasoning'),
                r.get('quality_eval'),
                datetime.datetime.now()
            ))

        # 批量插入
        execute_values(cur, """
            INSERT INTO backtest_results (
                run_id, scenario_id, test_question, system_answer, actual_intent,
                confidence, score, overall_score, passed, evaluation,
                optimization_tips, knowledge_sources, source_ids, source_count,
                difficulty, notes, relevance, completeness, accuracy,
                intent_match, quality_overall, quality_reasoning, quality_eval, tested_at
            ) VALUES %s
        """, result_values)

        print(f"✅ 已保存 {len(results)} 條結果到資料庫")
    except Exception as e:
        print(f"❌ 保存結果失敗: {e}")
        import traceback
        traceback.print_exc()

    # 更新 backtest_runs 為完成狀態
    cur.execute("""
        UPDATE backtest_runs SET
            executed_scenarios = %s,
            status = %s,
            passed_count = %s,
            failed_count = %s,
            error_count = %s,
            pass_rate = %s,
            avg_relevance = %s,
            avg_completeness = %s,
            avg_accuracy = %s,
            avg_intent_match = %s,
            avg_quality_overall = %s,
            completed_at = %s,
            duration_seconds = %s,
            output_file_path = %s
        WHERE id = %s
    """, (
        len(results), 'completed',
        passed_count, failed_count, error_count, pass_rate,
        avg_relevance, avg_completeness, avg_accuracy, avg_intent_match, avg_quality_overall,
        end_time, int(duration), output_file, run_id
    ))

    conn.commit()
    cur.close()
    conn.close()

    # 輸出總結
    print(f"\n{'='*60}")
    print(f"回測完成總結")
    print(f"{'='*60}")
    print(f"Run ID: {run_id}")
    print(f"開始時間: {start_time}")
    print(f"結束時間: {end_time}")
    print(f"總耗時: {duration:.2f} 秒 ({duration/60:.2f} 分鐘)")
    print(f"測試總數: {len(results)}")
    print(f"通過數量: {passed_count} ({pass_rate:.1f}%)")
    print(f"失敗數量: {failed_count}")
    print(f"錯誤數量: {error_count}")
    print(f"吞吐量: {len(results)/duration:.2f} 測試/秒")
    print(f"報告位置: {output_file}")
    print(f"資料庫記錄: Run ID {run_id}")
    print(f"\n前端查看: http://localhost:8087/backtest")
    print(f"{'='*60}\n")

    # 保存摘要 JSON
    summary = {
        'run_id': run_id,
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'duration_seconds': duration,
        'duration_minutes': duration/60,
        'total_tests': len(results),
        'passed': passed_count,
        'failed': failed_count,
        'errors': error_count,
        'pass_rate': pass_rate,
        'throughput': len(results)/duration,
        'report_file': output_file,
        'concurrency': concurrency,
        'quality_mode': quality_mode,
        'avg_relevance': avg_relevance,
        'avg_completeness': avg_completeness,
        'avg_accuracy': avg_accuracy,
        'avg_intent_match': avg_intent_match,
        'avg_quality_overall': avg_quality_overall
    }

    summary_file = f'/app/output/backtest/backtest_summary_{timestamp}.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"✅ 摘要已保存: {summary_file}")
    return 0


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
