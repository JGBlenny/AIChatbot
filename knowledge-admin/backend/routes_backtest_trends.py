"""
回測趨勢分析 API 路由 (Phase 3)
提供回測歷史數據的趨勢分析、統計對比和品質警報
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os

router = APIRouter(prefix="/api/backtest/trends", tags=["Backtest Trends"])

# 資料庫配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "aichatbot_admin")
DB_USER = os.getenv("DB_USER", "aichatbot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "aichatbot_password")


def get_db_connection():
    """建立資料庫連線"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )


# ========== 資料模型 ==========

class TrendDataPoint(BaseModel):
    """趨勢數據點"""
    timestamp: str
    pass_rate: Optional[float] = None
    avg_score: Optional[float] = None
    avg_confidence: Optional[float] = None
    total_tests: Optional[int] = None
    passed_tests: Optional[int] = None
    failed_tests: Optional[int] = None


class TrendResponse(BaseModel):
    """趨勢分析回應"""
    time_range: str
    data_points: List[TrendDataPoint]
    summary: Dict[str, Any]


class StatisticsComparison(BaseModel):
    """統計對比"""
    current_period: Dict[str, Any]
    previous_period: Dict[str, Any]
    changes: Dict[str, Any]


class Alert(BaseModel):
    """品質警報"""
    level: str  # 'critical', 'warning', 'info'
    metric: str
    current_value: float
    threshold: float
    message: str
    timestamp: str


# ========== API 端點 ==========

@router.get("/overview")
async def get_trends_overview(
    time_range: str = Query("30d", pattern="^(7d|30d|90d|all)$", description="時間範圍"),
    metric: str = Query("all", description="指標類型 (pass_rate/avg_score/avg_confidence/all)")
):
    """
    獲取回測趨勢總覽

    Args:
        time_range: 時間範圍 (7d/30d/90d/all)
        metric: 指標類型

    Returns:
        時間序列數據和摘要統計
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 計算時間範圍
        now = datetime.now()
        if time_range == "7d":
            start_date = now - timedelta(days=7)
        elif time_range == "30d":
            start_date = now - timedelta(days=30)
        elif time_range == "90d":
            start_date = now - timedelta(days=90)
        else:  # all
            start_date = datetime(2000, 1, 1)

        # 查詢趨勢數據
        cur.execute("""
            SELECT
                id,
                started_at,
                completed_at,
                quality_mode,
                test_type,
                total_scenarios,
                executed_scenarios,
                passed_count,
                failed_count,
                pass_rate,
                avg_score,
                avg_confidence,
                avg_relevance,
                avg_completeness,
                avg_accuracy,
                avg_intent_match,
                avg_quality_overall
            FROM backtest_runs
            WHERE status = 'completed'
              AND started_at >= %s
            ORDER BY started_at ASC
        """, (start_date,))

        runs = cur.fetchall()

        if not runs:
            return {
                "time_range": time_range,
                "data_points": [],
                "summary": {
                    "message": "指定時間範圍內無回測數據",
                    "total_runs": 0
                }
            }

        # 轉換為數據點
        data_points = []
        for run in runs:
            data_points.append({
                "run_id": run['id'],
                "timestamp": run['started_at'].isoformat(),
                "quality_mode": run['quality_mode'],
                "test_type": run['test_type'],
                "pass_rate": float(run['pass_rate']) if run['pass_rate'] is not None else None,
                "avg_score": float(run['avg_score']) if run['avg_score'] is not None else None,
                "avg_confidence": float(run['avg_confidence']) if run['avg_confidence'] is not None else None,
                "total_tests": run['executed_scenarios'] or run['total_scenarios'],
                "passed_tests": run['passed_count'],
                "failed_tests": run['failed_count'],
                "avg_relevance": float(run['avg_relevance']) if run['avg_relevance'] is not None else None,
                "avg_completeness": float(run['avg_completeness']) if run['avg_completeness'] is not None else None,
                "avg_accuracy": float(run['avg_accuracy']) if run['avg_accuracy'] is not None else None,
                "avg_intent_match": float(run['avg_intent_match']) if run['avg_intent_match'] is not None else None,
                "avg_quality_overall": float(run['avg_quality_overall']) if run['avg_quality_overall'] is not None else None,
            })

        # 計算摘要統計
        pass_rates = [dp['pass_rate'] for dp in data_points if dp['pass_rate'] is not None]
        avg_scores = [dp['avg_score'] for dp in data_points if dp['avg_score'] is not None]
        avg_confidences = [dp['avg_confidence'] for dp in data_points if dp['avg_confidence'] is not None]

        summary = {
            "total_runs": len(runs),
            "time_range": time_range,
            "start_date": runs[0]['started_at'].isoformat(),
            "end_date": runs[-1]['started_at'].isoformat(),
            "pass_rate": {
                "min": round(min(pass_rates), 2) if pass_rates else None,
                "max": round(max(pass_rates), 2) if pass_rates else None,
                "avg": round(sum(pass_rates) / len(pass_rates), 2) if pass_rates else None,
                "latest": round(pass_rates[-1], 2) if pass_rates else None,
                "trend": "improving" if len(pass_rates) >= 2 and pass_rates[-1] > pass_rates[0] else "declining" if len(pass_rates) >= 2 else "stable"
            },
            "avg_score": {
                "min": round(min(avg_scores), 3) if avg_scores else None,
                "max": round(max(avg_scores), 3) if avg_scores else None,
                "avg": round(sum(avg_scores) / len(avg_scores), 3) if avg_scores else None,
                "latest": round(avg_scores[-1], 3) if avg_scores else None,
                "trend": "improving" if len(avg_scores) >= 2 and avg_scores[-1] > avg_scores[0] else "declining" if len(avg_scores) >= 2 else "stable"
            },
            "avg_confidence": {
                "min": round(min(avg_confidences), 3) if avg_confidences else None,
                "max": round(max(avg_confidences), 3) if avg_confidences else None,
                "avg": round(sum(avg_confidences) / len(avg_confidences), 3) if avg_confidences else None,
                "latest": round(avg_confidences[-1], 3) if avg_confidences else None,
                "trend": "improving" if len(avg_confidences) >= 2 and avg_confidences[-1] > avg_confidences[0] else "declining" if len(avg_confidences) >= 2 else "stable"
            }
        }

        return {
            "time_range": time_range,
            "data_points": data_points,
            "summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢趨勢數據失敗: {str(e)}")

    finally:
        cur.close()
        conn.close()


@router.get("/comparison")
async def get_statistics_comparison(
    current_days: int = Query(7, ge=1, le=90, description="當前期間天數"),
    compare_with_previous: bool = Query(True, description="與前一期間對比")
):
    """
    統計對比分析

    對比當前期間與前一期間的統計數據,計算變化率

    Args:
        current_days: 當前期間天數
        compare_with_previous: 是否與前一期間對比

    Returns:
        當前期間、前期間數據及變化率
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        now = datetime.now()
        current_start = now - timedelta(days=current_days)

        # 查詢當前期間統計
        cur.execute("""
            SELECT
                COUNT(*) as total_runs,
                AVG(pass_rate) as avg_pass_rate,
                AVG(avg_score) as avg_score,
                AVG(avg_confidence) as avg_confidence,
                SUM(executed_scenarios) as total_tests,
                SUM(passed_count) as total_passed,
                SUM(failed_count) as total_failed,
                AVG(avg_relevance) as avg_relevance,
                AVG(avg_completeness) as avg_completeness,
                AVG(avg_accuracy) as avg_accuracy,
                AVG(avg_intent_match) as avg_intent_match,
                AVG(avg_quality_overall) as avg_quality_overall
            FROM backtest_runs
            WHERE status = 'completed'
              AND started_at >= %s
              AND started_at <= %s
        """, (current_start, now))

        current_stats = dict(cur.fetchone())

        # 處理 NULL 值
        for key in current_stats:
            if current_stats[key] is None:
                current_stats[key] = 0
            elif isinstance(current_stats[key], float):
                current_stats[key] = round(current_stats[key], 3)

        current_period = {
            "period": f"最近 {current_days} 天",
            "start_date": current_start.isoformat(),
            "end_date": now.isoformat(),
            "statistics": current_stats
        }

        # 如果需要對比
        if compare_with_previous:
            previous_start = current_start - timedelta(days=current_days)
            previous_end = current_start

            cur.execute("""
                SELECT
                    COUNT(*) as total_runs,
                    AVG(pass_rate) as avg_pass_rate,
                    AVG(avg_score) as avg_score,
                    AVG(avg_confidence) as avg_confidence,
                    SUM(executed_scenarios) as total_tests,
                    SUM(passed_count) as total_passed,
                    SUM(failed_count) as total_failed,
                    AVG(avg_relevance) as avg_relevance,
                    AVG(avg_completeness) as avg_completeness,
                    AVG(avg_accuracy) as avg_accuracy,
                    AVG(avg_intent_match) as avg_intent_match,
                    AVG(avg_quality_overall) as avg_quality_overall
                FROM backtest_runs
                WHERE status = 'completed'
                  AND started_at >= %s
                  AND started_at < %s
            """, (previous_start, previous_end))

            previous_stats = dict(cur.fetchone())

            # 處理 NULL 值
            for key in previous_stats:
                if previous_stats[key] is None:
                    previous_stats[key] = 0
                elif isinstance(previous_stats[key], float):
                    previous_stats[key] = round(previous_stats[key], 3)

            previous_period = {
                "period": f"前 {current_days} 天",
                "start_date": previous_start.isoformat(),
                "end_date": previous_end.isoformat(),
                "statistics": previous_stats
            }

            # 計算變化
            changes = {}
            for key in current_stats:
                if key in previous_stats:
                    current_val = current_stats[key]
                    previous_val = previous_stats[key]

                    if previous_val != 0:
                        change_pct = ((current_val - previous_val) / previous_val) * 100
                        changes[key] = {
                            "absolute": round(current_val - previous_val, 3),
                            "percentage": round(change_pct, 2),
                            "direction": "up" if change_pct > 0 else "down" if change_pct < 0 else "stable"
                        }
                    else:
                        changes[key] = {
                            "absolute": round(current_val, 3),
                            "percentage": None,
                            "direction": "new"
                        }

            return {
                "current_period": current_period,
                "previous_period": previous_period,
                "changes": changes
            }
        else:
            return {
                "current_period": current_period,
                "previous_period": None,
                "changes": None
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢統計對比失敗: {str(e)}")

    finally:
        cur.close()
        conn.close()


@router.get("/alerts")
async def get_quality_alerts(
    pass_rate_threshold: float = Query(80.0, ge=0.0, le=100.0, description="通過率閾值 (%)"),
    avg_score_threshold: float = Query(0.6, ge=0.0, le=1.0, description="平均分數閾值"),
    avg_confidence_threshold: float = Query(0.7, ge=0.0, le=1.0, description="平均信心度閾值"),
    check_latest_n_runs: int = Query(3, ge=1, le=10, description="檢查最近 N 次回測")
):
    """
    品質警報檢查

    檢查最近的回測結果是否低於設定閾值,並返回警報

    Args:
        pass_rate_threshold: 通過率閾值
        avg_score_threshold: 平均分數閾值
        avg_confidence_threshold: 平均信心度閾值
        check_latest_n_runs: 檢查最近 N 次回測

    Returns:
        警報列表和建議
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 查詢最近的回測
        cur.execute("""
            SELECT
                id,
                started_at,
                pass_rate,
                avg_score,
                avg_confidence,
                total_scenarios,
                passed_count,
                failed_count,
                quality_mode,
                test_type
            FROM backtest_runs
            WHERE status = 'completed'
            ORDER BY started_at DESC
            LIMIT %s
        """, (check_latest_n_runs,))

        recent_runs = cur.fetchall()

        if not recent_runs:
            return {
                "alerts": [],
                "summary": {
                    "total_alerts": 0,
                    "critical_count": 0,
                    "warning_count": 0,
                    "message": "無最近的回測數據"
                }
            }

        alerts = []

        # 檢查每次回測
        for run in recent_runs:
            run_id = run['id']
            timestamp = run['started_at'].isoformat()

            # 檢查通過率
            if run['pass_rate'] is not None and run['pass_rate'] < pass_rate_threshold:
                severity_diff = pass_rate_threshold - run['pass_rate']
                level = 'critical' if severity_diff >= 20 else 'warning'

                alerts.append({
                    "level": level,
                    "metric": "pass_rate",
                    "run_id": run_id,
                    "current_value": round(float(run['pass_rate']), 2),
                    "threshold": pass_rate_threshold,
                    "message": f"通過率 {run['pass_rate']:.2f}% 低於閾值 {pass_rate_threshold}%",
                    "timestamp": timestamp,
                    "recommendation": "建議檢查失敗測試案例,優化知識庫內容或調整意圖設定"
                })

            # 檢查平均分數
            if run['avg_score'] is not None and run['avg_score'] < avg_score_threshold:
                severity_diff = avg_score_threshold - run['avg_score']
                level = 'critical' if severity_diff >= 0.2 else 'warning'

                alerts.append({
                    "level": level,
                    "metric": "avg_score",
                    "run_id": run_id,
                    "current_value": round(float(run['avg_score']), 3),
                    "threshold": avg_score_threshold,
                    "message": f"平均分數 {run['avg_score']:.3f} 低於閾值 {avg_score_threshold}",
                    "timestamp": timestamp,
                    "recommendation": "建議使用 failed_only 策略重測失敗案例,分析原因並優化"
                })

            # 檢查平均信心度
            if run['avg_confidence'] is not None and run['avg_confidence'] < avg_confidence_threshold:
                severity_diff = avg_confidence_threshold - run['avg_confidence']
                level = 'critical' if severity_diff >= 0.2 else 'warning'

                alerts.append({
                    "level": level,
                    "metric": "avg_confidence",
                    "run_id": run_id,
                    "current_value": round(float(run['avg_confidence']), 3),
                    "threshold": avg_confidence_threshold,
                    "message": f"平均信心度 {run['avg_confidence']:.3f} 低於閾值 {avg_confidence_threshold}",
                    "timestamp": timestamp,
                    "recommendation": "RAG 系統信心度偏低,建議檢查知識庫覆蓋率和向量品質"
                })

        # 統計警報
        critical_count = sum(1 for alert in alerts if alert['level'] == 'critical')
        warning_count = sum(1 for alert in alerts if alert['level'] == 'warning')

        # 檢查趨勢（如果有多次回測）
        trend_alerts = []
        if len(recent_runs) >= 3:
            # 檢查通過率趨勢
            pass_rates = [r['pass_rate'] for r in recent_runs if r['pass_rate'] is not None]
            if len(pass_rates) >= 3:
                # 簡單的趨勢檢測：最近 3 次都在下降
                if pass_rates[0] < pass_rates[1] < pass_rates[2]:
                    trend_alerts.append({
                        "level": "warning",
                        "metric": "pass_rate_trend",
                        "message": f"通過率呈下降趨勢: {pass_rates[2]:.1f}% → {pass_rates[1]:.1f}% → {pass_rates[0]:.1f}%",
                        "recommendation": "需要關注整體品質下降趨勢,建議進行完整的知識庫審查"
                    })

        alerts.extend(trend_alerts)

        summary = {
            "total_alerts": len(alerts),
            "critical_count": critical_count,
            "warning_count": warning_count,
            "info_count": len(trend_alerts),
            "latest_run_id": recent_runs[0]['id'] if recent_runs else None,
            "latest_run_time": recent_runs[0]['started_at'].isoformat() if recent_runs else None,
            "checked_runs": len(recent_runs),
            "thresholds": {
                "pass_rate": pass_rate_threshold,
                "avg_score": avg_score_threshold,
                "avg_confidence": avg_confidence_threshold
            }
        }

        return {
            "alerts": alerts,
            "summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢品質警報失敗: {str(e)}")

    finally:
        cur.close()
        conn.close()


@router.get("/metrics/{metric_name}")
async def get_metric_detail(
    metric_name: str,
    time_range: str = Query("30d", pattern="^(7d|30d|90d|all)$", description="時間範圍")
):
    """
    獲取特定指標的詳細趨勢

    Args:
        metric_name: 指標名稱 (pass_rate/avg_score/avg_confidence 等)
        time_range: 時間範圍

    Returns:
        該指標的詳細時間序列數據和統計
    """
    valid_metrics = [
        'pass_rate', 'avg_score', 'avg_confidence',
        'avg_relevance', 'avg_completeness', 'avg_accuracy',
        'avg_intent_match', 'avg_quality_overall'
    ]

    if metric_name not in valid_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"無效的指標名稱。有效值: {', '.join(valid_metrics)}"
        )

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 計算時間範圍
        now = datetime.now()
        if time_range == "7d":
            start_date = now - timedelta(days=7)
        elif time_range == "30d":
            start_date = now - timedelta(days=30)
        elif time_range == "90d":
            start_date = now - timedelta(days=90)
        else:  # all
            start_date = datetime(2000, 1, 1)

        # 查詢指標數據
        cur.execute(f"""
            SELECT
                id,
                started_at,
                {metric_name},
                quality_mode,
                test_type,
                total_scenarios,
                executed_scenarios
            FROM backtest_runs
            WHERE status = 'completed'
              AND started_at >= %s
              AND {metric_name} IS NOT NULL
            ORDER BY started_at ASC
        """, (start_date,))

        runs = cur.fetchall()

        if not runs:
            return {
                "metric_name": metric_name,
                "time_range": time_range,
                "data_points": [],
                "statistics": {
                    "message": "指定時間範圍內無數據"
                }
            }

        # 提取數據點
        data_points = []
        values = []

        for run in runs:
            value = float(run[metric_name])
            values.append(value)

            data_points.append({
                "run_id": run['id'],
                "timestamp": run['started_at'].isoformat(),
                "value": round(value, 3),
                "quality_mode": run['quality_mode'],
                "test_type": run['test_type'],
                "total_tests": run['executed_scenarios'] or run['total_scenarios']
            })

        # 計算統計
        statistics = {
            "count": len(values),
            "min": round(min(values), 3),
            "max": round(max(values), 3),
            "avg": round(sum(values) / len(values), 3),
            "latest": round(values[-1], 3),
            "first": round(values[0], 3),
            "change": round(values[-1] - values[0], 3),
            "change_percentage": round(((values[-1] - values[0]) / values[0] * 100), 2) if values[0] != 0 else None,
            "trend": "improving" if values[-1] > values[0] else "declining" if values[-1] < values[0] else "stable"
        }

        return {
            "metric_name": metric_name,
            "time_range": time_range,
            "data_points": data_points,
            "statistics": statistics
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢指標詳情失敗: {str(e)}")

    finally:
        cur.close()
        conn.close()
