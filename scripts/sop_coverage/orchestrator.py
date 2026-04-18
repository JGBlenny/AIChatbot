"""
SOP 覆蓋率補齊 Pipeline Orchestrator

Phase 1: 讀取流程清單
Phase 2: 停用現有 SOP
Phase 3: 批量建立分類
Phase 4: 批量生成 SOP
Phase 5: 暫停等待人工審核
Phase 6: 回測驗證
Phase 7: 聚焦 LLM 判定

Usage:
    # Phase 1-5（生成後暫停等待審核）
    python scripts/sop_coverage/orchestrator.py --vendor-id 2

    # 保留特定 SOP
    python scripts/sop_coverage/orchestrator.py --vendor-id 2 --exclude-sop-ids 1,2,3

    # 審核完成後，執行回測 + LLM 判定（Phase 6-7）
    python scripts/sop_coverage/orchestrator.py --vendor-id 2 --skip-phases load,deactivate,create,generate

    # 指定回測測試集
    python scripts/sop_coverage/orchestrator.py --vendor-id 2 --skip-phases load,deactivate,create,generate --scenario-ids 1,2,3
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

# 將 rag-orchestrator 加入 Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'rag-orchestrator'))

from coverage_utils import (
    init_db_pool,
    create_loop_record,
    deactivate_existing_sops,
    clear_old_generated_knowledge,
    create_categories_from_checklist,
    checklist_to_gaps,
    load_checklist,
)
from llm_answer_evaluator import evaluate_batch


ALL_PHASES = ["load", "deactivate", "create", "generate", "pause", "backtest", "evaluate"]


async def run_pipeline(
    vendor_id: int,
    exclude_sop_ids: Optional[List[int]] = None,
    skip_phases: Optional[List[str]] = None,
    backtest_scenario_ids: Optional[List[int]] = None,
    checklist_path: str = "scripts/sop_coverage/process_checklist.json",
    batch_size: int = 5,
) -> Dict:
    """完整 pipeline 執行"""
    skip_phases = set(skip_phases or [])
    results = {}

    print("=" * 60)
    print(f"SOP 覆蓋率補齊 Pipeline")
    print(f"  vendor_id: {vendor_id}")
    print(f"  skip_phases: {skip_phases or '(none)'}")
    print(f"  batch_size: {batch_size}")
    print(f"  時間: {datetime.now().isoformat()}")
    print("=" * 60)

    # 初始化 DB
    db_pool = await init_db_pool()

    try:
        # ============================================
        # Phase 1: 讀取流程清單
        # ============================================
        if "load" not in skip_phases:
            print("\n📋 Phase 1: 讀取流程清單")
            checklist = load_checklist(checklist_path)
            total = sum(len(c["subtopics"]) for c in checklist)
            print(f"  載入 {len(checklist)} 個分類, {total} 個子題")
            results["checklist_total"] = total
        else:
            print("\n⏭️  Phase 1: 跳過（load）")
            checklist = load_checklist(checklist_path)

        # ============================================
        # Phase 2: 停用現有 SOP
        # ============================================
        if "deactivate" not in skip_phases:
            print("\n🗑️  Phase 2: 停用現有 SOP")
            deactivate_result = await deactivate_existing_sops(
                db_pool, vendor_id, exclude_sop_ids
            )
            results["deactivated"] = deactivate_result

            # 清除舊的 loop_generated_knowledge（避免重複偵測誤判）
            clear_result = await clear_old_generated_knowledge(db_pool, vendor_id)
            results["cleared_knowledge"] = clear_result
        else:
            print("\n⏭️  Phase 2: 跳過（deactivate）")

        # ============================================
        # Phase 3: 批量建立分類
        # ============================================
        if "create" not in skip_phases:
            print("\n📁 Phase 3: 批量建立分類")
            category_map = await create_categories_from_checklist(
                db_pool, vendor_id, checklist
            )
            results["categories"] = category_map
        else:
            print("\n⏭️  Phase 3: 跳過（create）")
            # 仍需要 category_map 給後續使用
            category_map = {}
            for cat in checklist:
                row = await db_pool.fetchrow(
                    "SELECT id FROM vendor_sop_categories WHERE vendor_id = $1 AND category_name = $2",
                    vendor_id, cat["category_name"]
                )
                if row:
                    category_map[cat["category_name"]] = row["id"]

        # ============================================
        # Phase 4: 批量生成 SOP
        # ============================================
        if "generate" not in skip_phases:
            print("\n📝 Phase 4: 批量生成 SOP")

            # 建立 loop 記錄
            loop_id = await create_loop_record(db_pool, vendor_id)
            print(f"  loop_id: {loop_id}")
            results["loop_id"] = loop_id

            # 轉換格式
            gaps = checklist_to_gaps(checklist, category_map)

            # 生成 SOP
            from services.knowledge_completion_loop.sop_generator import SOPGenerator
            import psycopg2.pool
            openai_api_key = os.getenv("OPENAI_API_KEY", "")
            # SOPGenerator 使用 psycopg2（同步），需要獨立的同步連線池
            sync_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1, maxconn=5,
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                database=os.getenv("DB_NAME", "aichatbot_admin"),
                user=os.getenv("DB_USER", "aichatbot"),
                password=os.getenv("DB_PASSWORD", "aichatbot_password"),
            )
            generator = SOPGenerator(db_pool=sync_pool, openai_api_key=openai_api_key)
            generated = await generator.generate_from_checklist(
                loop_id=loop_id,
                vendor_id=vendor_id,
                gaps=gaps,
                iteration=1,
                batch_size=batch_size,
            )
            results["generated_count"] = len(generated)
            print(f"\n  生成完成：{len(generated)} 筆 SOP")
        else:
            print("\n⏭️  Phase 4: 跳過（generate）")

        # ============================================
        # Phase 5: 暫停等待人工審核
        # ============================================
        if "pause" not in skip_phases and "generate" not in skip_phases:
            print("\n" + "=" * 60)
            print(f"⏸️  Phase 5: 等待人工審核")
            print(f"  {results.get('generated_count', '?')} 筆 SOP 待審核")
            print(f"  請至審核介面操作：http://localhost:8087/review-center")
            print(f"  審核完成後，執行以下命令進行回測驗證：")
            print(f"")
            print(f"  python scripts/sop_coverage/orchestrator.py \\")
            print(f"    --vendor-id {vendor_id} \\")
            print(f"    --skip-phases load,deactivate,create,generate")
            print("=" * 60)
            results["status"] = "waiting_for_review"
            return results

        # ============================================
        # Phase 6: 回測驗證
        # ============================================
        if "backtest" not in skip_phases:
            print("\n🧪 Phase 6: 回測驗證")

            from services.knowledge_completion_loop.backtest_client import BacktestFrameworkClient
            backtest_client = BacktestFrameworkClient(db_pool=db_pool)

            # 取得 loop_id（如果是從 Phase 6 開始，需要從 DB 查）
            loop_id = results.get("loop_id")
            if not loop_id:
                row = await db_pool.fetchrow(
                    """SELECT id FROM knowledge_completion_loops
                       WHERE vendor_id = $1 ORDER BY id DESC LIMIT 1""",
                    vendor_id
                )
                loop_id = row["id"] if row else await create_loop_record(db_pool, vendor_id)

            backtest_result = await backtest_client.execute_batch_backtest(
                loop_id=loop_id,
                iteration=1,
                vendor_id=vendor_id,
                batch_size=500,
                scenario_ids=backtest_scenario_ids,
            )
            results["backtest"] = backtest_result
            print(f"  pass_rate: {backtest_result.get('pass_rate', 'N/A')}")
            print(f"  passed: {backtest_result.get('passed', 0)} / {backtest_result.get('total_tested', 0)}")
        else:
            print("\n⏭️  Phase 6: 跳過（backtest）")

        # ============================================
        # Phase 7: 聚焦 LLM 判定
        # ============================================
        if "evaluate" not in skip_phases and "backtest" not in skip_phases:
            print("\n🤖 Phase 7: 聚焦 LLM 答案品質判定")

            backtest_result = results.get("backtest", {})
            # 從回測結果取得詳細資料
            failed_scenarios = backtest_result.get("failed_scenarios", [])

            # 查詢回測結果明細
            run_id = backtest_result.get("backtest_run_id")
            if run_id:
                rows = await db_pool.fetch(
                    """SELECT scenario_id, test_question, system_answer, passed,
                              confidence, evaluation
                       FROM backtest_results WHERE run_id = $1""",
                    run_id
                )
                test_results = [dict(r) for r in rows]
            else:
                test_results = []

            if test_results:
                evaluated = await evaluate_batch(test_results)

                # 更新 evaluation JSONB
                for r in evaluated:
                    if r.get("llm_judgment"):
                        await db_pool.execute(
                            """UPDATE backtest_results
                               SET evaluation = evaluation || $1::jsonb
                               WHERE run_id = $2 AND scenario_id = $3""",
                            json.dumps({
                                "llm_judgment": r["llm_judgment"],
                                "final_passed": r.get("final_passed", r.get("passed", False)),
                            }),
                            run_id,
                            r["scenario_id"],
                        )

                results["llm_evaluation"] = {
                    "total": len(evaluated),
                    "yes": sum(1 for r in evaluated if r.get("llm_judgment", {}).get("verdict") == "yes"),
                    "partial": sum(1 for r in evaluated if r.get("llm_judgment", {}).get("verdict") == "partial"),
                    "no": sum(1 for r in evaluated if r.get("llm_judgment", {}).get("verdict") == "no"),
                }
        else:
            print("\n⏭️  Phase 7: 跳過（evaluate）")

        # ============================================
        # 最終報告
        # ============================================
        print("\n" + "=" * 60)
        print("📊 Pipeline 完成")
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        print("=" * 60)

        results["status"] = "completed"
        return results

    finally:
        await db_pool.close()


def parse_args():
    parser = argparse.ArgumentParser(description="SOP 覆蓋率補齊 Pipeline")
    parser.add_argument("--vendor-id", type=int, required=True, help="業者 ID")
    parser.add_argument("--exclude-sop-ids", type=str, default="",
                        help="要保留的 SOP ID（逗號分隔）")
    parser.add_argument("--skip-phases", type=str, default="",
                        help="要跳過的 phase（逗號分隔）")
    parser.add_argument("--scenario-ids", type=str, default="",
                        help="回測測試集 ID（逗號分隔）")
    parser.add_argument("--checklist", type=str,
                        default="scripts/sop_coverage/process_checklist.json",
                        help="流程清單 JSON 路徑")
    parser.add_argument("--batch-size", type=int, default=5,
                        help="SOP 生成批次大小")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    exclude_sop_ids = [int(x) for x in args.exclude_sop_ids.split(",") if x.strip()]
    skip_phases = [x.strip() for x in args.skip_phases.split(",") if x.strip()]
    scenario_ids = [int(x) for x in args.scenario_ids.split(",") if x.strip()] or None

    asyncio.run(run_pipeline(
        vendor_id=args.vendor_id,
        exclude_sop_ids=exclude_sop_ids or None,
        skip_phases=skip_phases or None,
        backtest_scenario_ids=scenario_ids,
        checklist_path=args.checklist,
        batch_size=args.batch_size,
    ))
