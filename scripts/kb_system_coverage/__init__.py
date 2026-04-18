"""
JGB 系統知識覆蓋率工具集

提供模組盤點、問題清單生成、覆蓋缺口分析等功能的共用資料模型。
"""

from .models import (
    CoverageReport,
    Feature,
    GapItem,
    Module,
    ModuleCoverage,
    RoleCoverage,
    SimilarItem,
    SystemQuestion,
)

__all__ = [
    "CoverageReport",
    "Feature",
    "GapItem",
    "Module",
    "ModuleCoverage",
    "RoleCoverage",
    "SimilarItem",
    "SystemQuestion",
]
