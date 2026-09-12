"""
迴圈管理 API 路由（查詢面）

⚠️ 執行面（啟動／執行迭代／驗證／暫停／恢復／取消／完成批次／下一批次）已於
2026-09 移除：`coordinator.execute_iteration` 每次迭代都會走
`backtest_client.execute_batch_backtest`，其打的 `POST /api/v1/message`
已隨舊 REST 對話鏈刪除，迴圈自那之後一次也跑不完，執行機制已無法運作。
新的回測改走 `.claude/skills/retrieval-improvement-loop/`（打 `/mcp` 的
`agent.turn`），不再有 repo 內的 Python 回測框架。

本檔僅保留純查詢端點，服務既有的 915 筆 `loop_generated_knowledge`（2026-09-12 實查：
469 approved／446 rejected，**0 筆待審**）與 27 筆 `knowledge_completion_loops`
歷史記錄的檢視需求：
- GET /coverage-stats
- GET /
- GET /{loop_id}/iterations
- GET /{loop_id}/iterations/{iteration}/backtest-results
- GET /{loop_id}

Author: AI Assistant
Created: 2026-03-27
"""

import json
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

router = APIRouter()


# ============================================
# Response Models
# ============================================

class LoopStatusResponse(BaseModel):
    """迴圈狀態回應"""
    loop_id: int
    loop_name: str
    vendor_id: int
    status: str
    current_iteration: int
    current_pass_rate: Optional[float]
    target_pass_rate: float
    scenario_ids: List[int]
    total_scenarios: int
    progress: Dict  # {phase: str, percentage: float, message: str}
    created_at: str
    updated_at: str
    completed_at: Optional[str]


# ============================================
# API Endpoints（查詢面）
# ============================================

@router.get("/coverage-stats")
async def get_coverage_stats(req: Request):
    """
    取得回測覆蓋率統計

    返回題庫總題數、已測過的題數、覆蓋率百分比。
    """
    try:
        db_pool_async = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else req.app.extra.get('db_pool')

        async with db_pool_async.acquire() as conn:
            # 題庫中所有 active 題目數
            total_scenarios = await conn.fetchval("""
                SELECT COUNT(*) FROM test_scenarios WHERE is_active = true
            """)

            # 從 backtest_results 查實際測過的不重複題目數
            covered_scenarios = await conn.fetchval("""
                SELECT COUNT(DISTINCT scenario_id)
                FROM backtest_results
                WHERE scenario_id IS NOT NULL
            """)

            # 各迴圈（含 backtest_run）的覆蓋明細
            loop_details = await conn.fetch("""
                SELECT
                    kcl.id AS loop_id,
                    kcl.loop_name,
                    kcl.status,
                    COALESCE(sub.tested_count, 0) AS scenario_count,
                    kcl.current_pass_rate
                FROM knowledge_completion_loops kcl
                LEFT JOIN (
                    SELECT
                        CAST(substring(br.notes FROM 'Loop (\d+)') AS INTEGER) AS loop_id,
                        COUNT(DISTINCT bres.scenario_id) AS tested_count
                    FROM backtest_runs br
                    JOIN backtest_results bres ON bres.run_id = br.id
                    WHERE br.notes LIKE 'Knowledge Completion Loop %'
                      AND bres.scenario_id IS NOT NULL
                    GROUP BY substring(br.notes FROM 'Loop (\d+)')
                ) sub ON sub.loop_id = kcl.id
                ORDER BY kcl.id
            """)

            coverage_rate = (covered_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0

            return {
                "total_scenarios": total_scenarios,
                "covered_scenarios": covered_scenarios,
                "uncovered_scenarios": total_scenarios - covered_scenarios,
                "coverage_rate": round(coverage_rate, 1),
                "loop_details": [
                    {
                        "loop_id": row["loop_id"],
                        "loop_name": row["loop_name"],
                        "status": row["status"],
                        "scenario_count": row["scenario_count"],
                        "current_pass_rate": float(row["current_pass_rate"]) if row["current_pass_rate"] else None
                    }
                    for row in loop_details
                ]
            }

    except Exception as e:
        print(f"❌ 取得覆蓋率統計失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"取得覆蓋率統計失敗：{str(e)}")


@router.get("/", response_model=List[LoopStatusResponse])
async def list_loops(
    req: Request,
    vendor_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    [新增] 列出所有迴圈

    - 支援按 vendor_id 和 status 篩選
    - 支援分頁（limit/offset）
    - 按更新時間倒序排列
    """
    try:
        db_pool_async = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else req.app.extra.get('db_pool')

        # 構建查詢條件
        conditions = []
        params = []
        param_count = 1

        if vendor_id is not None:
            conditions.append(f"vendor_id = ${param_count}")
            params.append(vendor_id)
            param_count += 1

        if status is not None:
            conditions.append(f"status = ${param_count}")
            params.append(status)
            param_count += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # 查詢迴圈列表
        async with db_pool_async.acquire() as conn:
            query = f"""
                SELECT
                    id, loop_name, vendor_id, status,
                    current_iteration,
                    current_pass_rate, target_pass_rate,
                    scenario_ids,
                    created_at, updated_at, completed_at
                FROM knowledge_completion_loops
                {where_clause}
                ORDER BY updated_at DESC
                LIMIT ${param_count} OFFSET ${param_count + 1}
            """
            params.extend([limit, offset])

            loop_records = await conn.fetch(query, *params)

            # 為每個迴圈構建回應
            results = []
            for loop_record in loop_records:
                # 查詢最新執行事件（取得進度資訊）
                latest_event = await conn.fetchrow("""
                    SELECT event_type, event_data, created_at
                    FROM loop_execution_logs
                    WHERE loop_id = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                """, loop_record["id"])

                # 構建進度資訊
                progress = {"phase": "unknown", "percentage": 0.0, "message": ""}
                if latest_event:
                    event_type = latest_event["event_type"]
                    phase_map = {
                        "loop_started": {"phase": "initialized", "percentage": 0.0},
                        "backtest_started": {"phase": "backtesting", "percentage": 10.0},
                        "backtest_completed": {"phase": "analyzing", "percentage": 30.0},
                        "gaps_analyzed": {"phase": "classifying", "percentage": 50.0},
                        "gaps_classified": {"phase": "generating", "percentage": 70.0},
                        "knowledge_generated": {"phase": "reviewing", "percentage": 90.0},
                        "iteration_completed": {"phase": "completed", "percentage": 100.0}
                    }
                    progress = phase_map.get(event_type, progress)
                    progress["message"] = event_type

                # 從 backtest_runs 取實際測試題數（scenario_ids 可能為 NULL）
                actual_scenario_ids = loop_record["scenario_ids"] or []
                if not actual_scenario_ids:
                    loop_id_str = str(loop_record["id"])
                    tested_count = await conn.fetchval("""
                        SELECT COALESCE(MAX(total_scenarios), 0)
                        FROM backtest_runs
                        WHERE notes LIKE 'Knowledge Completion Loop ' || $1 || ' - %'
                    """, loop_id_str)
                else:
                    tested_count = len(actual_scenario_ids)

                results.append(LoopStatusResponse(
                    loop_id=loop_record["id"],
                    loop_name=loop_record["loop_name"],
                    vendor_id=loop_record["vendor_id"],
                    status=loop_record["status"],
                    current_iteration=loop_record["current_iteration"] or 0,
                    current_pass_rate=float(loop_record["current_pass_rate"]) if loop_record["current_pass_rate"] else None,
                    target_pass_rate=float(loop_record["target_pass_rate"]) if loop_record["target_pass_rate"] else 0.85,
                    scenario_ids=actual_scenario_ids,
                    total_scenarios=tested_count,
                    progress=progress,
                    created_at=loop_record["created_at"].isoformat() if loop_record["created_at"] else "",
                    updated_at=loop_record["updated_at"].isoformat() if loop_record["updated_at"] else "",
                    completed_at=loop_record["completed_at"].isoformat() if loop_record["completed_at"] else None
                ))

            return results

    except Exception as e:
        print(f"❌ 列出迴圈失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"列出迴圈失敗：{str(e)}")


@router.get("/{loop_id}/iterations")
async def get_loop_iterations(
    loop_id: int,
    req: Request
):
    """
    [任務 11.2.3] 查詢迴圈迭代歷史（含回測結果）

    從 backtest_runs 和 loop_execution_logs 查詢每次迭代的詳細記錄
    """
    try:
        pool = req.app.state.db_pool
        async with pool.acquire() as conn:
            # 查詢迭代的回測記錄，從 backtest_results 即時計算通過/失敗數
            records = await conn.fetch("""
                SELECT
                    br.id as run_id,
                    CAST(SUBSTRING(br.notes FROM 'Iteration (\\d+)') AS INTEGER) as iteration,
                    br.total_scenarios,
                    br.executed_scenarios,
                    COALESCE(stats.passed_count, br.passed_count, 0) as passed_count,
                    COALESCE(stats.failed_count, br.failed_count, 0) as failed_count,
                    COALESCE(stats.calc_pass_rate, br.pass_rate, 0) as pass_rate,
                    COALESCE(stats.avg_score, br.avg_score, 0) as avg_score,
                    br.started_at,
                    br.completed_at,
                    br.status
                FROM backtest_runs br
                LEFT JOIN LATERAL (
                    SELECT
                        COUNT(*) FILTER (WHERE passed = true) as passed_count,
                        COUNT(*) FILTER (WHERE passed = false) as failed_count,
                        CASE WHEN COUNT(*) > 0
                            THEN COUNT(*) FILTER (WHERE passed = true)::float / COUNT(*)
                            ELSE 0 END as calc_pass_rate,
                        AVG(overall_score) as avg_score
                    FROM backtest_results
                    WHERE run_id = br.id
                ) stats ON true
                WHERE br.notes LIKE $1
                  AND br.status = 'completed'
                ORDER BY br.started_at ASC
            """, f'%Loop {loop_id}%')

            iterations = []
            for record in records:
                iter_num = record["iteration"] if record["iteration"] else 0

                # 查詢該迭代生成的知識數量
                knowledge_count = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM loop_generated_knowledge
                    WHERE loop_id = $1 AND iteration = $2
                """, loop_id, iter_num)

                iterations.append({
                    "run_id": record["run_id"],
                    "iteration": iter_num,
                    "total": record["total_scenarios"] or 0,
                    "passed": record["passed_count"] or 0,
                    "failed": record["failed_count"] or 0,
                    "pass_rate": float(record["pass_rate"]) if record["pass_rate"] else 0.0,
                    "avg_score": float(record["avg_score"]) if record["avg_score"] else 0.0,
                    "knowledge_generated": knowledge_count or 0,
                    "started_at": record["started_at"].isoformat() if record["started_at"] else None,
                    "completed_at": record["completed_at"].isoformat() if record["completed_at"] else None,
                    "status": record["status"]
                })

            return iterations

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 查詢迭代歷史失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"查詢迭代歷史失敗：{str(e)}")


@router.get("/{loop_id}/iterations/{iteration}/backtest-results")
async def get_iteration_backtest_results(
    loop_id: int,
    iteration: int,
    req: Request,
    limit: int = 100,
    offset: int = 0
):
    """
    查詢特定迭代的回測詳細結果

    Returns:
        包含回測結果列表和統計信息
    """
    try:
        pool = req.app.state.db_pool
        async with pool.acquire() as conn:
            # 查詢 backtest_run_id
            run_record = await conn.fetchrow("""
                SELECT id, passed_count, failed_count, pass_rate, total_scenarios
                FROM backtest_runs
                WHERE notes LIKE $1
                  AND notes LIKE $2
                LIMIT 1
            """, f'%Loop {loop_id}%', f'%Iteration {iteration}%')

            if not run_record:
                return {"results": [], "total": 0, "summary": None}

            run_id = run_record["id"]

            # 查詢回測結果（包含 evaluation 和 response_metadata）
            results = await conn.fetch("""
                SELECT
                    br.id,
                    br.scenario_id,
                    br.test_question,
                    br.system_answer,
                    br.passed,
                    br.confidence,
                    br.overall_score,
                    br.relevance,
                    br.completeness,
                    br.accuracy,
                    br.source_count,
                    br.tested_at,
                    br.evaluation,
                    br.actual_intent,
                    br.response_metadata,
                    br.source_ids,
                    br.knowledge_sources,
                    ts.request_target_user,
                    ts.request_mode
                FROM backtest_results br
                LEFT JOIN test_scenarios ts ON ts.id = br.scenario_id
                WHERE br.run_id = $1
                ORDER BY br.id
                LIMIT $2 OFFSET $3
            """, run_id, limit, offset)

            # 獲取總數與通過統計（backtest_runs 的 passed_count 迴圈路徑不回填，須即時算）
            count_row = await conn.fetchrow("""
                SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE passed) AS passed,
                       COUNT(*) FILTER (WHERE NOT passed) AS failed
                FROM backtest_results WHERE run_id = $1
            """, run_id)
            total = count_row["total"]

            result_list = []
            for r in results:
                # 從 evaluation JSON 提取 confidence_score, confidence_level
                # asyncpg 將 jsonb 解析為字串，需要手動 parse
                # 注意：某些情況下數據可能被雙重 JSON 編碼，需要處理
                evaluation = {}

                if r["evaluation"] and isinstance(r["evaluation"], str):
                    try:
                        parsed = json.loads(r["evaluation"])

                        # 如果第一次解碼後還是字串，說明被雙重編碼了，需要再解碼一次
                        if isinstance(parsed, str):
                            parsed = json.loads(parsed)

                        evaluation = parsed
                    except Exception as e:
                        print(f"⚠️ 解析 evaluation JSON 失敗 (ID={r['id']}): {e}")
                        evaluation = {}
                elif r["evaluation"] and isinstance(r["evaluation"], dict):
                    evaluation = r["evaluation"]

                # 優先使用 evaluation 的 confidence_score，否則 fallback 到 0（因為沒有 RAG 結果）
                # 注意：r["confidence"] 是意圖分類信心度，不應該用於 RAG 信心度
                confidence_score = float(evaluation.get("confidence_score", 0.0)) if isinstance(evaluation, dict) else 0.0

                # 根據 source_count 判斷信心度等級（如果 evaluation 沒有提供）
                if isinstance(evaluation, dict) and evaluation.get("confidence_level"):
                    confidence_level = evaluation.get("confidence_level")
                else:
                    # Fallback：根據 source_count 和 confidence_score 判斷
                    if r["source_count"] == 0:
                        confidence_level = "low"
                    elif confidence_score >= 0.85:
                        confidence_level = "high"
                    elif confidence_score >= 0.70:
                        confidence_level = "medium"
                    else:
                        confidence_level = "low"

                # 解析 response_metadata（處理流程詳情）
                response_metadata = {}
                if r["response_metadata"]:
                    if isinstance(r["response_metadata"], str):
                        try:
                            parsed = json.loads(r["response_metadata"])
                            if isinstance(parsed, str):
                                parsed = json.loads(parsed)
                            response_metadata = parsed
                        except:
                            response_metadata = {}
                    elif isinstance(r["response_metadata"], dict):
                        response_metadata = r["response_metadata"]

                result_list.append({
                    "id": r["id"],
                    "scenario_id": r["scenario_id"],
                    "test_question": r["test_question"] or "",
                    "system_answer": r["system_answer"] or "",
                    "expected_category": None,  # backtest_results 沒有這個欄位
                    "actual_intent": r["actual_intent"],
                    "passed": r["passed"],
                    "confidence": float(r["confidence"]) if r["confidence"] else 0.0,  # 意圖分類信心度
                    "confidence_score": confidence_score,  # RAG 檢索信心度（從 evaluation 提取）
                    "confidence_level": confidence_level,  # RAG 檢索信心度等級
                    "overall_score": float(r["overall_score"]) if r["overall_score"] else 0.0,
                    "relevance": float(r["relevance"]) if r["relevance"] else None,
                    "completeness": float(r["completeness"]) if r["completeness"] else None,
                    "accuracy": float(r["accuracy"]) if r["accuracy"] else None,
                    "source_count": r["source_count"] or 0,
                    "tested_at": r["tested_at"].isoformat() if r["tested_at"] else None,
                    "failure_reason": evaluation.get("failure_reason") if isinstance(evaluation, dict) else None,
                    "grade": evaluation.get("grade") if isinstance(evaluation, dict) else None,          # v3 多輪感知評級
                    "grade_reason": evaluation.get("grade_reason") if isinstance(evaluation, dict) else None,
                    # v3 多輪欄位：輪次/逐字稿/評估版本/金標明細
                    "turns_used": evaluation.get("turns_used") if isinstance(evaluation, dict) else None,
                    "transcript": evaluation.get("transcript") if isinstance(evaluation, dict) else None,
                    "eval_version": evaluation.get("eval_version") if isinstance(evaluation, dict) else None,
                    "request_target_user": r["request_target_user"],
                    "request_mode": r["request_mode"],
                    "source_ids": r["source_ids"],
                    "knowledge_sources": r["knowledge_sources"],
                    "turn_sources": evaluation.get("turn_sources") if isinstance(evaluation, dict) else None,
                    "llm_grade": evaluation.get("llm_grade") if isinstance(evaluation, dict) else None,
                    "gold_fails": evaluation.get("gold_fails") if isinstance(evaluation, dict) else None,
                    "is_relevant": evaluation.get("is_relevant") if isinstance(evaluation, dict) else None,
                    "relevance_reason": evaluation.get("relevance_reason") if isinstance(evaluation, dict) else None,
                    "debug_info": response_metadata if response_metadata else None  # 處理流程詳情
                })

            # v3 評級分佈（舊 run 無 grade → 空 dict，前端據此隱藏分佈條）
            grade_rows = await conn.fetch("""
                SELECT COALESCE(evaluation::jsonb->>'grade','') AS grade, count(*) AS n
                FROM backtest_results WHERE run_id = $1 GROUP BY 1
            """, run_id)
            grade_distribution = {gr["grade"]: gr["n"] for gr in grade_rows if gr["grade"]}

            return {
                "results": result_list,
                "total": total,
                "summary": {
                    "run_id": run_id,
                    "grade_distribution": grade_distribution,
                    "total": run_record["total_scenarios"] or count_row["total"] or 0,
                    "passed": count_row["passed"] or 0,
                    "failed": count_row["failed"] or 0,
                    "pass_rate": (count_row["passed"] / count_row["total"]) if count_row["total"] else 0.0,
                    "avg_score": 0.0  # 暫時設為 0，後續可從結果計算
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 查詢回測結果失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"查詢回測結果失敗：{str(e)}")


@router.get("/{loop_id}", response_model=LoopStatusResponse)
async def get_loop_status(loop_id: int, req: Request):
    """
    [需求 10.2] 查詢迴圈狀態

    - 返回當前狀態與進度
    - 前端輪詢使用
    """
    try:
        db_pool_async = req.app.state.db_pool if hasattr(req.app.state, 'db_pool') else req.app.extra.get('db_pool')

        # 從資料庫查詢迴圈記錄
        async with db_pool_async.acquire() as conn:
            loop_record = await conn.fetchrow("""
                SELECT
                    id, loop_name, vendor_id, status,
                    current_iteration,
                    current_pass_rate, target_pass_rate,
                    scenario_ids,
                    created_at, updated_at, completed_at
                FROM knowledge_completion_loops
                WHERE id = $1
            """, loop_id)

            if not loop_record:
                raise HTTPException(status_code=404, detail=f"迴圈 {loop_id} 不存在")

            # 查詢最新執行事件（取得進度資訊）
            latest_event = await conn.fetchrow("""
                SELECT event_type, event_data, created_at
                FROM loop_execution_logs
                WHERE loop_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """, loop_id)

            # 構建進度資訊
            progress = {"phase": "unknown", "percentage": 0.0, "message": ""}
            if latest_event:
                event_type = latest_event["event_type"]
                # 根據事件類型判斷進度
                phase_map = {
                    "loop_started": {"phase": "initialized", "percentage": 0.0},
                    "backtest_started": {"phase": "backtesting", "percentage": 10.0},
                    "backtest_completed": {"phase": "analyzing", "percentage": 30.0},
                    "gaps_analyzed": {"phase": "classifying", "percentage": 50.0},
                    "gaps_classified": {"phase": "generating", "percentage": 70.0},
                    "knowledge_generated": {"phase": "reviewing", "percentage": 90.0},
                    "iteration_completed": {"phase": "completed", "percentage": 100.0}
                }
                progress = phase_map.get(event_type, progress)
                progress["message"] = event_type

            return LoopStatusResponse(
                loop_id=loop_record["id"],
                loop_name=loop_record["loop_name"],
                vendor_id=loop_record["vendor_id"],
                status=loop_record["status"],
                current_iteration=loop_record["current_iteration"] or 0,
                current_pass_rate=float(loop_record["current_pass_rate"]) if loop_record["current_pass_rate"] else None,
                target_pass_rate=float(loop_record["target_pass_rate"]) if loop_record["target_pass_rate"] else 0.85,
                scenario_ids=loop_record["scenario_ids"] or [],
                total_scenarios=len(loop_record["scenario_ids"]) if loop_record["scenario_ids"] else 0,
                progress=progress,
                created_at=loop_record["created_at"].isoformat() if loop_record["created_at"] else "",
                updated_at=loop_record["updated_at"].isoformat() if loop_record["updated_at"] else "",
                completed_at=loop_record["completed_at"].isoformat() if loop_record["completed_at"] else None
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 查詢迴圈狀態失敗：{str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"查詢迴圈狀態失敗：{str(e)}")
