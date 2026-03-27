"""
知識庫完善迴圈系統

此模組實作自動化的知識庫完善迴圈，包含：
- 批次回測執行
- 知識缺口分析
- AI 知識生成
- 回應類型判斷
- 迭代驗證與同步
"""

from .models import (
    LoopStatus,
    LoopConfig,
    FailureReason,
    GapPriority,
    ActionType,
    KnowledgeGap,
)

from .coordinator import LoopCoordinator
from .clients import (
    BacktestFrameworkClient,
    GapAnalyzer,
    ActionTypeClassifier,
    KnowledgeGeneratorClient,
)

__all__ = [
    # Models
    "LoopStatus",
    "LoopConfig",
    "FailureReason",
    "GapPriority",
    "ActionType",
    "KnowledgeGap",
    # Services
    "LoopCoordinator",
    "BacktestFrameworkClient",
    "GapAnalyzer",
    "ActionTypeClassifier",
    "KnowledgeGeneratorClient",
]
