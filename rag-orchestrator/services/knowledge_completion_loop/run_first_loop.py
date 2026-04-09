#!/usr/bin/env python3
"""
執行第一輪知識完善迴圈

目標：
- 執行 50 題小規模回測
- 分析知識缺口
- 生成知識（使用 OpenAI API）
- 人工審核
- 同步到知識庫

執行方式：
  python3 run_first_loop.py
"""

import asyncio
import os
import sys
from datetime import datetime
import psycopg2.pool

# 加入當前目錄到路徑
sys.path.insert(0, os.path.dirname(__file__))

from coordinator import LoopCoordinator

try:
    from models import LoopConfig
except ImportError:
    from services.knowledge_completion_loop.models import LoopConfig


async def main():
    """執行第一輪迴圈"""

    print("\n" + "="*70)
    print("知識庫完善迴圈 - 第一輪執行")
    print("="*70)
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

    # 資料庫連接參數
    db_params = {
        'host': os.getenv('DB_HOST', 'postgres'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'aichatbot_admin'),
        'user': os.getenv('DB_USER', 'aichatbot'),
        'password': os.getenv('DB_PASSWORD', 'aichatbot_password'),
    }

    # OpenAI API Key
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        print("❌ 錯誤：未設定 OPENAI_API_KEY 環境變數")
        print("   請執行: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)

    # 回測服務 URL
    backtest_url = os.getenv('RAG_API_URL', 'http://localhost:8100')

    # 業者 ID
    vendor_id = int(os.getenv('VENDOR_ID', '1'))

    # 檢查是否只執行回測
    backtest_only = os.getenv('BACKTEST_ONLY', 'false').lower() in ('true', '1', 'yes')

    print(f"📋 配置資訊:")
    print(f"   資料庫: {db_params['host']}:{db_params['port']}/{db_params['database']}")
    print(f"   回測服務: {backtest_url}")
    print(f"   業者 ID: {vendor_id}")
    print(f"   OpenAI API Key: {'已設定 ✅' if openai_api_key else '未設定 ❌'}")
    print(f"   僅回測模式: {'是 ✅' if backtest_only else '否'}")
    print()

    # 建立資料庫連接池
    print("🔌 建立資料庫連接池...")
    try:
        db_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            **db_params
        )
        print("   ✅ 連接池建立成功")
    except Exception as e:
        print(f"   ❌ 連接失敗: {e}")
        sys.exit(1)

    # 迴圈配置
    config = LoopConfig(
        batch_size=50,  # 第一輪：50 題
        target_pass_rate=0.85,  # 目標通過率：85%
        action_type_mode="ai_assisted",  # AI 輔助判斷回應類型
    )

    print("\n⚙️  迴圈配置:")
    print(f"   批次大小: {config.batch_size} 題")
    print(f"   目標通過率: {config.target_pass_rate * 100}%")
    print(f"   回應類型判斷: {config.action_type_mode}")
    print()

    # 初始化協調器
    print("🚀 初始化知識完善迴圈協調器...")
    coordinator = LoopCoordinator(
        db_pool=db_pool,
        vendor_id=vendor_id,
        loop_name="第一輪知識完善迴圈（50題）",
        backtest_base_url=backtest_url,
        openai_api_key=openai_api_key
    )
    print("   ✅ 協調器初始化完成")
    print()

    try:
        # 檢查是否只執行回測
        if backtest_only:
            print("="*70)
            print("⚡ 僅回測模式：只執行回測，不生成知識")
            print("="*70)
            print()

            # 直接執行回測
            print("🧪 開始執行回測...")

            # 載入測試場景
            print(f"📖 從資料庫載入測試場景...")
            conn = db_pool.getconn()
            try:
                cur = conn.cursor()

                # 建立 backtest_runs 記錄
                start_time = datetime.now()

                cur.execute("""
                    INSERT INTO backtest_runs (
                        vendor_id, test_type, quality_mode,
                        total_scenarios, executed_scenarios,
                        status, notes, rag_api_url, started_at, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    vendor_id,
                    "batch",  # test_type - 使用 batch 以保證統計正確
                    "detailed",  # quality_mode
                    config.batch_size,  # total_scenarios
                    0,  # executed_scenarios
                    "running",
                    "BACKTEST_ONLY mode",
                    backtest_url,  # rag_api_url
                    start_time,
                    start_time
                ))

                run_id = cur.fetchone()[0]
                conn.commit()
                print(f"✅ 已建立 Run #{run_id}")

                cur.execute("""
                    SELECT id, test_question, difficulty
                    FROM test_scenarios
                    ORDER BY id
                    LIMIT %s
                """, (config.batch_size,))
                rows = cur.fetchall()

                # 轉換為 scenarios 格式
                scenarios = []
                for row in rows:
                    scenarios.append({
                        'id': row[0],
                        'test_question': row[1],
                        'difficulty': row[2] or 'medium'
                    })

                print(f"✓ 已載入 {len(scenarios)} 個測試場景")
            except Exception as e:
                print(f"❌ 資料庫操作失敗: {e}")
                import traceback
                traceback.print_exc()
                db_pool.putconn(conn)
                return

            if not scenarios:
                print("❌ 沒有找到測試場景")
                cur.execute("""
                    UPDATE backtest_runs
                    SET status = 'failed', notes = 'No test scenarios found'
                    WHERE id = %s
                """, (run_id,))
                conn.commit()
                db_pool.putconn(conn)
                return

            # 初始化回測框架
            import sys
            sys.path.insert(0, '/app')
            from backtest_framework_async import AsyncBacktestFramework

            backtest_framework = AsyncBacktestFramework(
                vendor_id=vendor_id,
                base_url=backtest_url
            )

            # 執行回測
            results = await backtest_framework.run_backtest_concurrent(
                test_scenarios=scenarios,
                show_progress=True
            )

            # 統計結果
            total = len(results)
            passed = sum(1 for r in results if r.get('passed'))
            failed = total - passed
            pass_rate = (passed / total) if total > 0 else 0

            # 保存結果到資料庫
            print(f"\n💾 保存結果到資料庫...")
            try:
                from psycopg2.extras import execute_values

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
                        r.get('relevance'),
                        r.get('completeness'),
                        r.get('accuracy'),
                        r.get('intent_match'),
                        r.get('quality_overall'),
                        r.get('quality_reasoning'),
                        datetime.now()
                    ))

                # 批量插入
                execute_values(cur, """
                    INSERT INTO backtest_results (
                        run_id, scenario_id, test_question, system_answer, actual_intent,
                        confidence, score, overall_score, passed, evaluation,
                        optimization_tips, knowledge_sources, source_ids, source_count,
                        relevance, completeness, accuracy,
                        intent_match, quality_overall, quality_reasoning, tested_at
                    ) VALUES %s
                """, result_values)

                # 更新 backtest_runs 統計
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                cur.execute("""
                    UPDATE backtest_runs
                    SET
                        executed_scenarios = %s,
                        passed_count = %s,
                        failed_count = %s,
                        error_count = 0,
                        pass_rate = %s,
                        status = 'completed',
                        completed_at = %s,
                        duration_seconds = %s
                    WHERE id = %s
                """, (
                    total,
                    passed,
                    failed,
                    pass_rate,
                    end_time,
                    duration,
                    run_id
                ))

                conn.commit()
                print(f"✅ 已保存 {len(results)} 條結果到資料庫 (Run #{run_id})")
            except Exception as e:
                print(f"❌ 保存結果失敗: {e}")
                import traceback
                traceback.print_exc()
            finally:
                db_pool.putconn(conn)

            print("\n" + "="*70)
            print("✅ 回測完成")
            print("="*70)
            print(f"Run ID: #{run_id}")
            print(f"測試題數: {total}")
            print(f"通過數: {passed}")
            print(f"失敗數: {failed}")
            print(f"通過率: {pass_rate * 100:.1f}%")
            print()
            print(f"📊 資料庫記錄：SELECT * FROM backtest_results WHERE run_id = {run_id};")
            print("📌 僅回測模式完成，未生成新知識")
            print()
            return

        # 正常流程：啟動迴圈
        print("="*70)
        print("開始執行迴圈")
        print("="*70)
        print()

        result = await coordinator.start_loop(config)

        print("\n" + "="*70)
        print("迴圈啟動成功")
        print("="*70)
        print(f"迴圈 ID: {result.get('loop_id', 'N/A')}")
        print(f"狀態: {result.get('status', 'N/A')}")
        print()

        # 執行第一次迭代
        print("="*70)
        print("開始第一次迭代")
        print("="*70)
        print()

        iteration_result = await coordinator.execute_iteration()

        print("\n" + "="*70)
        print("第一次迭代完成")
        print("="*70)
        print(f"迭代次數: {iteration_result.get('current_iteration', 'N/A')}")
        print(f"狀態: {iteration_result.get('status', 'N/A')}")

        if 'backtest_result' in iteration_result:
            backtest = iteration_result['backtest_result']
            print(f"\n📊 回測結果:")
            print(f"   測試題數: {backtest.get('total_tested', 'N/A')}")
            print(f"   通過數: {backtest.get('passed', 'N/A')}")
            print(f"   失敗數: {backtest.get('failed', 'N/A')}")
            print(f"   通過率: {backtest.get('pass_rate', 0) * 100:.1f}%")

        if 'gaps_found' in iteration_result:
            print(f"\n🔍 知識缺口:")
            print(f"   發現數量: {iteration_result.get('gaps_found', 'N/A')}")

        if 'knowledge_generated' in iteration_result:
            print(f"\n📝 知識生成:")
            print(f"   生成數量: {iteration_result.get('knowledge_generated', 'N/A')}")

        if 'cost_summary' in iteration_result:
            cost = iteration_result['cost_summary']
            print(f"\n💰 成本統計:")
            print(f"   總成本: ${cost.get('total_cost_usd', 0):.4f} USD")
            print(f"   API 調用次數: {cost.get('total_calls', 'N/A')}")
            print(f"   Token 總數: {cost.get('total_tokens', 'N/A')}")
            print(f"   預算使用: {cost.get('budget_used_percentage', 0) * 100:.1f}%")

        print()
        print("="*70)
        print("✅ 第一輪迴圈執行完成！")
        print("="*70)
        print()
        print("📌 下一步:")
        print("   1. 查看生成的知識（資料庫: loop_generated_knowledge 表）")
        print("   2. 進行人工審核（review_status = 'pending'）")
        print("   3. 審核通過後，知識將自動同步到 knowledge_base")
        print()

    except Exception as e:
        print(f"\n❌ 執行失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # 關閉資料庫連接池
        if db_pool:
            db_pool.closeall()
            print("🔌 資料庫連接池已關閉")


if __name__ == "__main__":
    asyncio.run(main())
