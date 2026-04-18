#!/usr/bin/env python3
"""
回測結果分析器 — 模組分組統計與覆蓋率改善摘要

接收 AsyncBacktestFramework 的回測結果列表，按 module_id 分組統計
pass_rate，支援前後比較，標記低於平均的模組為「需優先補強」。

主要功能：
1. 按模組分組計算 pass_rate
2. 失敗原因分類（NO_MATCH / LOW_CONFIDENCE / ANSWER_QUALITY）
3. 前後比較（補齊前 vs 補齊後）
4. 標記低於平均的模組
5. 輸出結構化 JSON 摘要

Usage:
    # 單次分析
    python scripts/kb_system_coverage/backtest_analyzer.py --results results.json

    # 前後比較
    python scripts/kb_system_coverage/backtest_analyzer.py \\
        --before before_results.json --after after_results.json
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 確保 project root 在 sys.path
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# 失敗原因分類常數
# ---------------------------------------------------------------------------

class FailureCategory:
    """回測失敗原因分類"""
    NO_MATCH = "NO_MATCH"             # 系統未找到相關知識
    LOW_CONFIDENCE = "LOW_CONFIDENCE" # 有結果但信心度不足
    ANSWER_QUALITY = "ANSWER_QUALITY" # 有結果但答案品質不佳
    TIMEOUT = "TIMEOUT"               # 請求超時
    ERROR = "ERROR"                   # 其他錯誤


# ---------------------------------------------------------------------------
# 資料結構
# ---------------------------------------------------------------------------

@dataclass
class ModuleStats:
    """單一模組的回測統計"""
    module_id: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    # 依 query_type 分組
    static_total: int = 0
    static_passed: int = 0
    dynamic_total: int = 0
    dynamic_passed: int = 0
    # 失敗原因統計
    failure_counts: Dict[str, int] = field(default_factory=dict)
    # 是否需要優先補強
    needs_priority: bool = False

    @property
    def pass_rate(self) -> float:
        """通過率（0.0 ~ 1.0）"""
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    @property
    def static_pass_rate(self) -> float:
        if self.static_total == 0:
            return 0.0
        return self.static_passed / self.static_total

    @property
    def dynamic_pass_rate(self) -> float:
        if self.dynamic_total == 0:
            return 0.0
        return self.dynamic_passed / self.dynamic_total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": round(self.pass_rate, 4),
            "static_total": self.static_total,
            "static_passed": self.static_passed,
            "static_pass_rate": round(self.static_pass_rate, 4),
            "dynamic_total": self.dynamic_total,
            "dynamic_passed": self.dynamic_passed,
            "dynamic_pass_rate": round(self.dynamic_pass_rate, 4),
            "failure_counts": dict(self.failure_counts),
            "needs_priority": self.needs_priority,
        }


@dataclass
class BacktestSummary:
    """回測結果完整摘要"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    overall_pass_rate: float = 0.0
    module_stats: Dict[str, ModuleStats] = field(default_factory=dict)
    failure_summary: Dict[str, int] = field(default_factory=dict)
    priority_modules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "overall_pass_rate": round(self.overall_pass_rate, 4),
            "module_stats": {
                k: v.to_dict() for k, v in self.module_stats.items()
            },
            "failure_summary": dict(self.failure_summary),
            "priority_modules": list(self.priority_modules),
        }


@dataclass
class ComparisonSummary:
    """前後比較摘要"""
    before: BacktestSummary
    after: BacktestSummary
    overall_improvement: float = 0.0  # pass_rate 變化量
    module_improvements: Dict[str, float] = field(default_factory=dict)
    newly_covered_modules: List[str] = field(default_factory=list)
    still_failing_modules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "overall_improvement": round(self.overall_improvement, 4),
            "module_improvements": {
                k: round(v, 4) for k, v in self.module_improvements.items()
            },
            "newly_covered_modules": self.newly_covered_modules,
            "still_failing_modules": self.still_failing_modules,
        }


# ---------------------------------------------------------------------------
# 分析邏輯
# ---------------------------------------------------------------------------

def _extract_module_id(result: Dict[str, Any]) -> str:
    """從回測結果中提取 module_id。

    優先使用 metadata 中的 module_id，
    其次從 keywords 中推斷（第一個 keyword 通常是 module_id）。
    """
    # 直接欄位
    module_id = result.get("module_id")
    if module_id:
        return module_id

    # 從 notes 解析（格式：「模組: billing | 類型: static | ...」）
    notes = result.get("notes", "")
    if "模組:" in notes:
        parts = notes.split("|")
        for part in parts:
            part = part.strip()
            if part.startswith("模組:"):
                return part.replace("模組:", "").strip()

    # 從 keywords 推斷
    keywords = result.get("keywords", [])
    if keywords:
        return keywords[0]

    return "unknown"


def _extract_query_type(result: Dict[str, Any]) -> str:
    """從回測結果中提取 query_type。"""
    qt = result.get("query_type")
    if qt:
        return qt

    notes = result.get("notes", "")
    if "類型:" in notes:
        parts = notes.split("|")
        for part in parts:
            part = part.strip()
            if part.startswith("類型:"):
                return part.replace("類型:", "").strip()

    return "unknown"


def classify_failure(result: Dict[str, Any]) -> str:
    """將失敗結果分類為失敗原因。

    分類邏輯：
    - error='timeout' → TIMEOUT
    - error 欄位有值 → ERROR
    - failure_reason 包含「沒有找到」或 source_count=0 → NO_MATCH
    - failure_reason 包含「信心度」或 confidence_score < 0.60 → LOW_CONFIDENCE
    - 其餘 → ANSWER_QUALITY
    """
    # 超時
    if result.get("error") == "timeout":
        return FailureCategory.TIMEOUT

    # 其他錯誤
    if result.get("error"):
        return FailureCategory.ERROR

    failure_reason = result.get("failure_reason", "") or ""

    # 無匹配結果
    if "沒有找到" in failure_reason or "未返回" in failure_reason:
        return FailureCategory.NO_MATCH
    if result.get("source_count", -1) == 0:
        return FailureCategory.NO_MATCH

    # 低信心度
    confidence = result.get("confidence_score")
    if confidence is not None and confidence < 0.60:
        return FailureCategory.LOW_CONFIDENCE
    if "信心度" in failure_reason:
        return FailureCategory.LOW_CONFIDENCE

    # 預設：答案品質問題
    return FailureCategory.ANSWER_QUALITY


def analyze_results(results: List[Dict[str, Any]]) -> BacktestSummary:
    """分析回測結果，產出模組分組統計摘要。

    Parameters
    ----------
    results : AsyncBacktestFramework 回測結果列表

    Returns
    -------
    BacktestSummary 包含整體與模組分組統計
    """
    summary = BacktestSummary()
    summary.total = len(results)

    for r in results:
        passed = bool(r.get("passed", False))
        module_id = _extract_module_id(r)
        query_type = _extract_query_type(r)

        if passed:
            summary.passed += 1
        else:
            summary.failed += 1

        # 模組統計
        if module_id not in summary.module_stats:
            summary.module_stats[module_id] = ModuleStats(module_id=module_id)

        ms = summary.module_stats[module_id]
        ms.total += 1

        if passed:
            ms.passed += 1
        else:
            ms.failed += 1
            # 失敗原因分類
            category = classify_failure(r)
            ms.failure_counts[category] = ms.failure_counts.get(category, 0) + 1
            summary.failure_summary[category] = summary.failure_summary.get(category, 0) + 1

        # query_type 分組
        if query_type == "static":
            ms.static_total += 1
            if passed:
                ms.static_passed += 1
        elif query_type == "dynamic":
            ms.dynamic_total += 1
            if passed:
                ms.dynamic_passed += 1

    # 整體 pass_rate
    summary.overall_pass_rate = (
        summary.passed / summary.total if summary.total > 0 else 0.0
    )

    # 標記低於平均的模組
    if summary.module_stats:
        avg_pass_rate = summary.overall_pass_rate
        for ms in summary.module_stats.values():
            if ms.pass_rate < avg_pass_rate and ms.total > 0:
                ms.needs_priority = True
                summary.priority_modules.append(ms.module_id)

    return summary


def compare_results(
    before: List[Dict[str, Any]],
    after: List[Dict[str, Any]],
) -> ComparisonSummary:
    """比較補齊前後的回測結果。

    Parameters
    ----------
    before : 補齊前回測結果
    after : 補齊後回測結果

    Returns
    -------
    ComparisonSummary 包含改善幅度分析
    """
    before_summary = analyze_results(before)
    after_summary = analyze_results(after)

    comparison = ComparisonSummary(
        before=before_summary,
        after=after_summary,
        overall_improvement=after_summary.overall_pass_rate - before_summary.overall_pass_rate,
    )

    # 逐模組比較
    all_modules = set(before_summary.module_stats.keys()) | set(after_summary.module_stats.keys())
    for mod in all_modules:
        before_rate = before_summary.module_stats.get(mod, ModuleStats(module_id=mod)).pass_rate
        after_rate = after_summary.module_stats.get(mod, ModuleStats(module_id=mod)).pass_rate
        comparison.module_improvements[mod] = after_rate - before_rate

        # 新覆蓋的模組（從 0% 提升到 >0%）
        if before_rate == 0.0 and after_rate > 0.0:
            comparison.newly_covered_modules.append(mod)

        # 仍然失敗的模組（after pass_rate 仍低於平均）
        if after_rate < after_summary.overall_pass_rate and after_rate < 1.0:
            after_ms = after_summary.module_stats.get(mod)
            if after_ms and after_ms.total > 0:
                comparison.still_failing_modules.append(mod)

    return comparison


def export_summary(
    summary: BacktestSummary | ComparisonSummary,
    path: Path,
) -> Path:
    """將摘要匯出為 JSON。"""
    path.write_text(
        json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI 入口：分析回測結果 JSON，產出摘要。"""
    import argparse

    parser = argparse.ArgumentParser(description="回測結果分析器")
    parser.add_argument("--results", type=str, default=None, help="單次回測結果 JSON")
    parser.add_argument("--before", type=str, default=None, help="補齊前回測結果 JSON")
    parser.add_argument("--after", type=str, default=None, help="補齊後回測結果 JSON")
    parser.add_argument("--output", type=str, default=None, help="輸出摘要 JSON 路徑")
    args = parser.parse_args()

    if args.before and args.after:
        before = json.loads(Path(args.before).read_text(encoding="utf-8"))
        after = json.loads(Path(args.after).read_text(encoding="utf-8"))
        result = compare_results(before, after)
        print(f"整體 pass_rate 變化：{result.overall_improvement:+.2%}")
        print(f"需優先補強模組：{result.still_failing_modules}")
    elif args.results:
        data = json.loads(Path(args.results).read_text(encoding="utf-8"))
        result = analyze_results(data)
        print(f"整體 pass_rate：{result.overall_pass_rate:.2%}")
        print(f"需優先補強模組：{result.priority_modules}")
    else:
        parser.error("請指定 --results 或 --before/--after")
        return

    if args.output:
        out = export_summary(result, Path(args.output))
        print(f"已寫入：{out}")
    else:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
