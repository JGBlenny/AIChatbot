"""
共用資料模型：JGB 系統知識覆蓋率工具集

定義 ModuleMapper、QuestionGenerator、CoverageAnalyzer 等元件間
共用的結構化資料類別。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# ModuleMapper 輸出
# ---------------------------------------------------------------------------

@dataclass
class Feature:
    """單一使用者面向功能項目"""
    feature_id: str          # e.g., "billing_001"
    feature_name: str        # e.g., "租金帳單查詢"
    roles: List[str]         # ["tenant", "landlord", "property_manager"]
    entry_point: str         # "app" | "admin" | "both"


@dataclass
class Module:
    """JGB 功能模組"""
    module_id: str           # e.g., "billing", "contract"
    module_name: str         # e.g., "帳務管理"
    description: str
    features: List[Feature] = field(default_factory=list)


# ---------------------------------------------------------------------------
# QuestionGenerator 輸出
# ---------------------------------------------------------------------------

@dataclass
class SystemQuestion:
    """各角色系統操作問題"""
    topic_id: str            # e.g., "帳務_001"
    module_id: str           # e.g., "billing"
    question: str            # e.g., "怎麼在 APP 查看帳單明細"
    roles: List[str]         # ["tenant"]
    entry_point: str         # "app" | "admin" | "both"
    priority: str            # "p0" | "p1" | "p2"
    query_type: str          # "static" | "dynamic"
    question_category: str   # "basic_operation" | "common_question" | "error_handling"
    keywords: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# CoverageAnalyzer 輸出
# ---------------------------------------------------------------------------

@dataclass
class SimilarItem:
    """與既有 KB/SOP 的相似比對結果"""
    source_type: str         # "kb" | "sop"
    source_id: str
    title: str
    similarity: float


@dataclass
class GapItem:
    """單一覆蓋缺口"""
    topic_id: str
    question: str
    gap_type: str            # "uncovered" | "partial" | "needs_improvement"
    recommendation: str      # "add_kb" | "add_sop" | "improve_existing"
    query_type: str          # "static" | "dynamic"
    priority: str            # "p0" | "p1" | "p2"
    similar_existing: List[SimilarItem] = field(default_factory=list)


@dataclass
class ModuleCoverage:
    """單一模組的覆蓋率統計"""
    module_id: str
    module_name: str
    total: int = 0
    covered_by_kb: int = 0
    covered_by_sop: int = 0
    uncovered: int = 0
    partial_covered: int = 0
    needs_improvement: int = 0

    @property
    def coverage_rate(self) -> float:
        """覆蓋率百分比（已覆蓋 / 總數）"""
        if self.total == 0:
            return 0.0
        return (self.covered_by_kb + self.covered_by_sop) / self.total


@dataclass
class RoleCoverage:
    """單一角色的覆蓋率統計"""
    role: str                # "tenant" | "landlord" | "property_manager" | ...
    total: int = 0
    covered_by_kb: int = 0
    covered_by_sop: int = 0
    uncovered: int = 0
    partial_covered: int = 0
    needs_improvement: int = 0

    @property
    def coverage_rate(self) -> float:
        """覆蓋率百分比（已覆蓋 / 總數）"""
        if self.total == 0:
            return 0.0
        return (self.covered_by_kb + self.covered_by_sop) / self.total


@dataclass
class CoverageReport:
    """覆蓋缺口分析完整報告"""
    total_questions: int = 0
    covered_by_kb: int = 0
    covered_by_sop: int = 0
    uncovered: int = 0
    partial_covered: int = 0
    needs_improvement: int = 0
    coverage_by_module: dict[str, ModuleCoverage] = field(default_factory=dict)
    coverage_by_role: dict[str, RoleCoverage] = field(default_factory=dict)
    gaps: List[GapItem] = field(default_factory=list)
