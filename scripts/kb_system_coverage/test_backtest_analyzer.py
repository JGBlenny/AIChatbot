"""
回測分析器單元測試

測試覆蓋：
- 模組分組統計（pass_rate 計算）
- 失敗原因分類（NO_MATCH / LOW_CONFIDENCE / ANSWER_QUALITY / TIMEOUT / ERROR）
- 低於平均的模組標記為「需優先補強」
- 前後比較（overall_improvement, module_improvements）
- query_type（static / dynamic）分組統計
- 空結果 / 單一模組 / 多模組混合測試
- 場景生成（question_to_scenario 格式正確性）
- 場景篩選（filter_modules / filter_query_types）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# 確保 project root 在 sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.kb_system_coverage.backtest_analyzer import (
    BacktestSummary,
    ComparisonSummary,
    FailureCategory,
    ModuleStats,
    analyze_results,
    classify_failure,
    compare_results,
    export_summary,
)
from scripts.kb_system_coverage.backtest_scenarios import (
    generate_scenarios,
    question_to_scenario,
)
from scripts.kb_system_coverage.models import SystemQuestion


# ---------------------------------------------------------------------------
# 測試資料工廠
# ---------------------------------------------------------------------------

def _make_result(
    *,
    passed: bool = True,
    module_id: str = "billing",
    query_type: str = "static",
    confidence_score: float = 0.85,
    failure_reason: str = "",
    source_count: int = 2,
    error: str = "",
    test_id: int = 1,
) -> dict:
    """建立模擬的回測結果。"""
    return {
        "test_id": test_id,
        "test_question": f"測試問題_{test_id}",
        "passed": passed,
        "module_id": module_id,
        "query_type": query_type,
        "confidence_score": confidence_score,
        "failure_reason": failure_reason,
        "source_count": source_count,
        "error": error,
        "notes": f"模組: {module_id} | 類型: {query_type}",
        "keywords": [module_id, "測試"],
    }


def _make_question(
    *,
    topic_id: str = "帳務_001",
    module_id: str = "billing",
    question: str = "怎麼在 APP 查看帳單明細",
    roles: list | None = None,
    entry_point: str = "app",
    priority: str = "p0",
    query_type: str = "static",
    question_category: str = "basic_operation",
    keywords: list | None = None,
) -> SystemQuestion:
    return SystemQuestion(
        topic_id=topic_id,
        module_id=module_id,
        question=question,
        roles=roles or ["tenant"],
        entry_point=entry_point,
        priority=priority,
        query_type=query_type,
        question_category=question_category,
        keywords=keywords or ["帳單", "明細"],
    )


# ===========================================================================
# 失敗原因分類測試
# ===========================================================================

class TestClassifyFailure:
    """失敗原因分類邏輯"""

    def test_timeout(self):
        r = _make_result(passed=False, error="timeout")
        assert classify_failure(r) == FailureCategory.TIMEOUT

    def test_generic_error(self):
        r = _make_result(passed=False, error="connection refused")
        assert classify_failure(r) == FailureCategory.ERROR

    def test_no_match_by_failure_reason(self):
        r = _make_result(passed=False, failure_reason="沒有找到資料")
        assert classify_failure(r) == FailureCategory.NO_MATCH

    def test_no_match_by_no_answer(self):
        r = _make_result(passed=False, failure_reason="系統未返回答案")
        assert classify_failure(r) == FailureCategory.NO_MATCH

    def test_no_match_by_zero_sources(self):
        r = _make_result(passed=False, source_count=0, failure_reason="")
        assert classify_failure(r) == FailureCategory.NO_MATCH

    def test_low_confidence_by_score(self):
        r = _make_result(
            passed=False, confidence_score=0.45, failure_reason=""
        )
        assert classify_failure(r) == FailureCategory.LOW_CONFIDENCE

    def test_low_confidence_by_reason(self):
        r = _make_result(
            passed=False, failure_reason="信心度過低 (0.450 < 0.60)"
        )
        assert classify_failure(r) == FailureCategory.LOW_CONFIDENCE

    def test_answer_quality_default(self):
        """其餘情況歸類為答案品質問題"""
        r = _make_result(
            passed=False,
            confidence_score=0.70,
            failure_reason="語義不符",
            source_count=2,
        )
        assert classify_failure(r) == FailureCategory.ANSWER_QUALITY


# ===========================================================================
# 單次分析測試
# ===========================================================================

class TestAnalyzeResults:
    """analyze_results 功能測試"""

    def test_empty_results(self):
        summary = analyze_results([])
        assert summary.total == 0
        assert summary.passed == 0
        assert summary.failed == 0
        assert summary.overall_pass_rate == 0.0
        assert summary.module_stats == {}

    def test_all_passed(self):
        results = [
            _make_result(passed=True, module_id="billing", test_id=1),
            _make_result(passed=True, module_id="billing", test_id=2),
            _make_result(passed=True, module_id="contract", test_id=3),
        ]
        summary = analyze_results(results)
        assert summary.total == 3
        assert summary.passed == 3
        assert summary.failed == 0
        assert summary.overall_pass_rate == 1.0
        assert summary.priority_modules == []

    def test_mixed_results(self):
        results = [
            _make_result(passed=True, module_id="billing", test_id=1),
            _make_result(passed=True, module_id="billing", test_id=2),
            _make_result(passed=False, module_id="billing", test_id=3,
                         failure_reason="信心度過低"),
            _make_result(passed=False, module_id="contract", test_id=4,
                         source_count=0),
            _make_result(passed=False, module_id="contract", test_id=5,
                         source_count=0),
        ]
        summary = analyze_results(results)
        assert summary.total == 5
        assert summary.passed == 2
        assert summary.failed == 3
        assert abs(summary.overall_pass_rate - 0.4) < 1e-9

        billing = summary.module_stats["billing"]
        assert billing.total == 3
        assert billing.passed == 2
        assert abs(billing.pass_rate - 2 / 3) < 1e-9

        contract = summary.module_stats["contract"]
        assert contract.total == 2
        assert contract.passed == 0
        assert contract.pass_rate == 0.0

    def test_priority_modules_marked(self):
        """低於平均的模組應被標記為需優先補強"""
        results = [
            # billing: 2/2 = 100%
            _make_result(passed=True, module_id="billing", test_id=1),
            _make_result(passed=True, module_id="billing", test_id=2),
            # contract: 0/2 = 0%（低於平均 50%）
            _make_result(passed=False, module_id="contract", test_id=3,
                         source_count=0),
            _make_result(passed=False, module_id="contract", test_id=4,
                         source_count=0),
        ]
        summary = analyze_results(results)
        assert summary.overall_pass_rate == 0.5
        assert "contract" in summary.priority_modules
        assert "billing" not in summary.priority_modules
        assert summary.module_stats["contract"].needs_priority is True
        assert summary.module_stats["billing"].needs_priority is False

    def test_failure_counts_by_module(self):
        results = [
            _make_result(passed=False, module_id="billing", test_id=1,
                         error="timeout"),
            _make_result(passed=False, module_id="billing", test_id=2,
                         source_count=0),
            _make_result(passed=False, module_id="billing", test_id=3,
                         confidence_score=0.40, failure_reason=""),
        ]
        summary = analyze_results(results)
        fc = summary.module_stats["billing"].failure_counts
        assert fc[FailureCategory.TIMEOUT] == 1
        assert fc[FailureCategory.NO_MATCH] == 1
        assert fc[FailureCategory.LOW_CONFIDENCE] == 1

    def test_failure_summary_aggregated(self):
        results = [
            _make_result(passed=False, module_id="billing", test_id=1,
                         error="timeout"),
            _make_result(passed=False, module_id="contract", test_id=2,
                         error="timeout"),
        ]
        summary = analyze_results(results)
        assert summary.failure_summary[FailureCategory.TIMEOUT] == 2

    def test_query_type_grouping(self):
        results = [
            _make_result(passed=True, module_id="billing",
                         query_type="static", test_id=1),
            _make_result(passed=False, module_id="billing",
                         query_type="static", test_id=2, source_count=0),
            _make_result(passed=True, module_id="billing",
                         query_type="dynamic", test_id=3),
        ]
        summary = analyze_results(results)
        ms = summary.module_stats["billing"]
        assert ms.static_total == 2
        assert ms.static_passed == 1
        assert ms.dynamic_total == 1
        assert ms.dynamic_passed == 1
        assert ms.static_pass_rate == 0.5
        assert ms.dynamic_pass_rate == 1.0

    def test_module_id_from_notes_fallback(self):
        """如果 module_id 欄位不存在，應從 notes 解析"""
        r = {
            "test_id": 1,
            "passed": True,
            "notes": "模組: repair | 類型: static",
            "keywords": ["repair"],
        }
        summary = analyze_results([r])
        assert "repair" in summary.module_stats

    def test_module_id_from_keywords_fallback(self):
        """如果 module_id 和 notes 都沒有，從 keywords 推斷"""
        r = {
            "test_id": 1,
            "passed": True,
            "keywords": ["payment", "繳費"],
        }
        summary = analyze_results([r])
        assert "payment" in summary.module_stats

    def test_to_dict_serializable(self):
        """摘要結構應可序列化為 JSON"""
        results = [
            _make_result(passed=True, module_id="billing", test_id=1),
            _make_result(passed=False, module_id="billing", test_id=2,
                         source_count=0),
        ]
        summary = analyze_results(results)
        d = summary.to_dict()
        serialized = json.dumps(d, ensure_ascii=False)
        assert isinstance(serialized, str)
        parsed = json.loads(serialized)
        assert parsed["total"] == 2
        assert "billing" in parsed["module_stats"]


# ===========================================================================
# 前後比較測試
# ===========================================================================

class TestCompareResults:
    """compare_results 功能測試"""

    def test_improvement_detected(self):
        before = [
            _make_result(passed=False, module_id="billing", test_id=1,
                         source_count=0),
            _make_result(passed=False, module_id="billing", test_id=2,
                         source_count=0),
        ]
        after = [
            _make_result(passed=True, module_id="billing", test_id=1),
            _make_result(passed=True, module_id="billing", test_id=2),
        ]
        comparison = compare_results(before, after)
        assert comparison.before.overall_pass_rate == 0.0
        assert comparison.after.overall_pass_rate == 1.0
        assert comparison.overall_improvement == 1.0

    def test_module_improvement_tracked(self):
        before = [
            _make_result(passed=False, module_id="billing", test_id=1,
                         source_count=0),
            _make_result(passed=True, module_id="contract", test_id=2),
        ]
        after = [
            _make_result(passed=True, module_id="billing", test_id=1),
            _make_result(passed=True, module_id="contract", test_id=2),
        ]
        comparison = compare_results(before, after)
        assert comparison.module_improvements["billing"] == 1.0
        assert comparison.module_improvements["contract"] == 0.0

    def test_newly_covered_modules(self):
        before = [
            _make_result(passed=False, module_id="repair", test_id=1,
                         source_count=0),
        ]
        after = [
            _make_result(passed=True, module_id="repair", test_id=1),
        ]
        comparison = compare_results(before, after)
        assert "repair" in comparison.newly_covered_modules

    def test_still_failing_modules(self):
        before = [
            _make_result(passed=False, module_id="billing", test_id=1,
                         source_count=0),
            _make_result(passed=True, module_id="contract", test_id=2),
        ]
        after = [
            _make_result(passed=False, module_id="billing", test_id=1,
                         source_count=0),
            _make_result(passed=True, module_id="contract", test_id=2),
        ]
        comparison = compare_results(before, after)
        assert "billing" in comparison.still_failing_modules

    def test_comparison_to_dict_serializable(self):
        before = [_make_result(passed=False, module_id="billing", test_id=1,
                               source_count=0)]
        after = [_make_result(passed=True, module_id="billing", test_id=1)]
        comparison = compare_results(before, after)
        d = comparison.to_dict()
        serialized = json.dumps(d, ensure_ascii=False)
        parsed = json.loads(serialized)
        assert parsed["overall_improvement"] == 1.0
        assert "before" in parsed
        assert "after" in parsed

    def test_no_change(self):
        """前後結果相同時 improvement 為 0"""
        results = [
            _make_result(passed=True, module_id="billing", test_id=1),
        ]
        comparison = compare_results(results, results)
        assert comparison.overall_improvement == 0.0


# ===========================================================================
# 匯出測試
# ===========================================================================

class TestExportSummary:
    """export_summary 功能測試"""

    def test_export_single_summary(self, tmp_path):
        results = [
            _make_result(passed=True, module_id="billing", test_id=1),
            _make_result(passed=False, module_id="contract", test_id=2,
                         source_count=0),
        ]
        summary = analyze_results(results)
        out = tmp_path / "summary.json"
        export_summary(summary, out)

        loaded = json.loads(out.read_text(encoding="utf-8"))
        assert loaded["total"] == 2
        assert loaded["passed"] == 1
        assert "billing" in loaded["module_stats"]

    def test_export_comparison(self, tmp_path):
        before = [_make_result(passed=False, module_id="billing", test_id=1,
                               source_count=0)]
        after = [_make_result(passed=True, module_id="billing", test_id=1)]
        comparison = compare_results(before, after)
        out = tmp_path / "comparison.json"
        export_summary(comparison, out)

        loaded = json.loads(out.read_text(encoding="utf-8"))
        assert loaded["overall_improvement"] == 1.0


# ===========================================================================
# 場景生成測試
# ===========================================================================

class TestScenarioGeneration:
    """backtest_scenarios 模組的場景生成測試"""

    def test_question_to_scenario_format(self):
        q = _make_question()
        s = question_to_scenario(q, scenario_id=42)

        assert s["id"] == 42
        assert s["test_question"] == q.question
        assert q.module_id in s["keywords"]
        assert s["module_id"] == q.module_id
        assert s["query_type"] == q.query_type
        assert s["priority"] == q.priority
        assert s["topic_id"] == q.topic_id
        assert s["roles"] == q.roles

    def test_module_id_in_keywords(self):
        """module_id 應插入 keywords 開頭"""
        q = _make_question(module_id="contract", keywords=["合約", "到期"])
        s = question_to_scenario(q, scenario_id=1)
        assert s["keywords"][0] == "contract"
        assert "合約" in s["keywords"]

    def test_module_id_not_duplicated(self):
        """如果 keywords 已包含 module_id，不重複加入"""
        q = _make_question(module_id="billing", keywords=["billing", "帳單"])
        s = question_to_scenario(q, scenario_id=1)
        assert s["keywords"].count("billing") == 1

    def test_difficulty_mapping(self):
        assert question_to_scenario(
            _make_question(priority="p0"), 1
        )["difficulty"] == "hard"
        assert question_to_scenario(
            _make_question(priority="p1"), 1
        )["difficulty"] == "medium"
        assert question_to_scenario(
            _make_question(priority="p2"), 1
        )["difficulty"] == "easy"

    def test_generate_scenarios_all(self):
        questions = [
            _make_question(module_id="billing", query_type="static"),
            _make_question(module_id="contract", query_type="dynamic"),
            _make_question(module_id="repair", query_type="static"),
        ]
        scenarios = generate_scenarios(questions)
        assert len(scenarios) == 3
        # id 遞增
        assert [s["id"] for s in scenarios] == [1, 2, 3]

    def test_filter_by_modules(self):
        questions = [
            _make_question(module_id="billing"),
            _make_question(module_id="contract"),
            _make_question(module_id="repair"),
        ]
        scenarios = generate_scenarios(questions, filter_modules=["billing", "repair"])
        assert len(scenarios) == 2
        module_ids = {s["module_id"] for s in scenarios}
        assert module_ids == {"billing", "repair"}

    def test_filter_by_query_types(self):
        questions = [
            _make_question(module_id="billing", query_type="static"),
            _make_question(module_id="billing", query_type="dynamic"),
            _make_question(module_id="contract", query_type="static"),
        ]
        scenarios = generate_scenarios(questions, filter_query_types=["dynamic"])
        assert len(scenarios) == 1
        assert scenarios[0]["query_type"] == "dynamic"

    def test_combined_filters(self):
        questions = [
            _make_question(module_id="billing", query_type="static"),
            _make_question(module_id="billing", query_type="dynamic"),
            _make_question(module_id="contract", query_type="dynamic"),
        ]
        scenarios = generate_scenarios(
            questions,
            filter_modules=["billing"],
            filter_query_types=["dynamic"],
        )
        assert len(scenarios) == 1
        assert scenarios[0]["module_id"] == "billing"
        assert scenarios[0]["query_type"] == "dynamic"

    def test_notes_contains_metadata(self):
        q = _make_question(
            module_id="repair",
            query_type="dynamic",
            roles=["tenant", "landlord"],
            entry_point="both",
        )
        s = question_to_scenario(q, scenario_id=1)
        assert "repair" in s["notes"]
        assert "dynamic" in s["notes"]
        assert "tenant,landlord" in s["notes"]
        assert "both" in s["notes"]


# ===========================================================================
# ModuleStats 屬性測試
# ===========================================================================

class TestModuleStats:
    """ModuleStats 計算屬性測試"""

    def test_pass_rate_zero_total(self):
        ms = ModuleStats(module_id="test")
        assert ms.pass_rate == 0.0

    def test_static_pass_rate(self):
        ms = ModuleStats(module_id="test", static_total=4, static_passed=3)
        assert ms.static_pass_rate == 0.75

    def test_dynamic_pass_rate(self):
        ms = ModuleStats(module_id="test", dynamic_total=2, dynamic_passed=1)
        assert ms.dynamic_pass_rate == 0.5

    def test_to_dict_complete(self):
        ms = ModuleStats(
            module_id="billing",
            total=10,
            passed=7,
            failed=3,
            static_total=6,
            static_passed=5,
            dynamic_total=4,
            dynamic_passed=2,
            failure_counts={"NO_MATCH": 2, "LOW_CONFIDENCE": 1},
            needs_priority=False,
        )
        d = ms.to_dict()
        assert d["pass_rate"] == 0.7
        assert d["static_pass_rate"] == round(5 / 6, 4)
        assert d["dynamic_pass_rate"] == 0.5
        assert d["failure_counts"]["NO_MATCH"] == 2
