"""
知識庫完善迴圈 - 資料模型

包含所有狀態機、配置模型、枚舉類別
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator


# ============================================
# 狀態機與配置
# ============================================

class LoopStatus(str, Enum):
    """迴圈狀態枚舉（13 個狀態）"""
    PENDING = "pending"  # 待啟動
    RUNNING = "running"  # 執行中（等待下一輪迭代）
    BACKTESTING = "backtesting"  # 回測中
    ANALYZING = "analyzing"  # 分析缺口中
    GENERATING = "generating"  # 生成知識中
    REVIEWING = "reviewing"  # 人工審核中
    VALIDATING = "validating"  # 迭代驗證中
    SYNCING = "syncing"  # 同步知識中
    PAUSED = "paused"  # 已暫停
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失敗
    CANCELLED = "cancelled"  # 已取消
    TERMINATED = "terminated"  # 已終止


class LoopConfig(BaseModel):
    """迴圈配置"""
    batch_size: int = Field(50, ge=1, le=100, description="每批回測題數")
    max_iterations: int = Field(20, ge=1, le=50, description="最大迭代次數")
    target_pass_rate: float = Field(0.8, ge=0.0, le=1.0, description="目標通過率")
    action_type_mode: str = Field("ai_assisted", description="回應類型判斷模式")
    filters: Dict = Field(default_factory=dict, description="篩選條件")
    backtest_config: Dict = Field(default_factory=dict, description="回測參數配置")

    @validator('action_type_mode')
    def validate_mode(cls, v):
        """驗證 action_type_mode"""
        allowed = ['manual_only', 'ai_assisted', 'auto']
        if v not in allowed:
            raise ValueError(f'action_type_mode 必須為 {allowed}')
        return v


# ============================================
# 知識缺口分析
# ============================================

class FailureReason(str, Enum):
    """失敗原因分類"""
    NO_MATCH = "no_match"  # 無匹配知識（similarity < 0.6）
    LOW_CONFIDENCE = "low_confidence"  # 信心度不足（confidence_score < 0.7）
    SEMANTIC_MISMATCH = "semantic_mismatch"  # 語義攔截（semantic_overlap < 0.4）
    SYSTEM_ERROR = "system_error"  # 系統錯誤（timeout, 5xx）


class GapPriority(str, Enum):
    """缺口優先級"""
    P0 = "p0"  # 高優先級：高頻問題且無匹配知識
    P1 = "p1"  # 中優先級：信心度不足但有部分匹配
    P2 = "p2"  # 低優先級：系統錯誤或邊緣案例


class KnowledgeGap(BaseModel):
    """知識缺口"""
    scenario_id: int = Field(description="測試案例 ID")
    question: str = Field(description="問題內容")
    failure_reason: FailureReason = Field(description="失敗原因")
    priority: GapPriority = Field(description="優先級")
    suggested_action_type: str = Field(description="建議回應類型")
    confidence_score: float = Field(description="當前信心度")
    max_similarity: float = Field(description="最大相似度")
    intent_id: Optional[int] = Field(None, description="意圖 ID")
    intent_name: Optional[str] = Field(None, description="意圖名稱")
    frequency: int = Field(1, description="出現頻率")


# ============================================
# 回應類型判斷
# ============================================

class ActionType(str, Enum):
    """回應類型"""
    DIRECT_ANSWER = "direct_answer"  # 純知識問答
    FORM_FILL = "form_fill"  # 表單+知識
    API_CALL = "api_call"  # API+知識
    FORM_THEN_API = "form_then_api"  # 表單+API+知識


class ActionTypeJudgment(BaseModel):
    """回應類型判斷結果"""
    action_type: ActionType = Field(description="判斷的回應類型")
    confidence: float = Field(ge=0.0, le=1.0, description="判斷信心度")
    reasoning: str = Field(description="判斷理由")
    required_form_fields: Optional[List[str]] = Field(None, description="所需表單欄位")
    suggested_form_id: Optional[str] = Field(None, description="建議的表單 ID")
    required_api_endpoint: Optional[str] = Field(None, description="所需 API endpoint")
    suggested_api_id: Optional[str] = Field(None, description="建議的 API ID")
    needs_manual_review: bool = Field(description="是否需人工確認")


# ============================================
# 回測品質驗證
# ============================================

class SampleStrategy(str, Enum):
    """抽樣策略"""
    RANDOM = "random"  # 隨機抽樣
    CRITICAL_THRESHOLD = "critical_threshold"  # 臨界值案例
    INTENT_BALANCED = "intent_balanced"  # 按 intent 平衡抽樣


class ManualJudgment(str, Enum):
    """人工判斷"""
    CORRECT = "correct"  # 回測評分正確
    INCORRECT = "incorrect"  # 回測評分錯誤


class ErrorType(str, Enum):
    """錯誤類型"""
    TOO_STRICT = "too_strict"  # 評估過嚴
    TOO_LOOSE = "too_loose"  # 評估過鬆
    LOGIC_ERROR = "logic_error"  # 邏輯錯誤
    OTHER = "other"  # 其他


class AnomalyType(str, Enum):
    """異常類型"""
    PASS_RATE_VOLATILITY = "pass_rate_volatility"  # 通過率大幅波動
    LOW_HIGH_CONFIDENCE = "low_high_confidence"  # 高信心度案例過少
    HIGH_SEMANTIC_BLOCK = "high_semantic_block"  # 語義攔截率過高
    HIGH_SYSTEM_ERROR = "high_system_error"  # 系統錯誤率過高
    REPEATED_FAILURES = "repeated_failures"  # 重複失敗案例過多


# ============================================
# 錯誤處理
# ============================================

class ErrorCategory(str, Enum):
    """錯誤分類"""
    VALIDATION_ERROR = "validation_error"  # 參數驗證錯誤（4xx）
    BUSINESS_LOGIC_ERROR = "business_logic_error"  # 業務邏輯錯誤（4xx）
    EXTERNAL_API_ERROR = "external_api_error"  # 外部 API 錯誤（5xx，可重試）
    DATABASE_ERROR = "database_error"  # 資料庫錯誤（5xx，可重試）
    SYSTEM_ERROR = "system_error"  # 系統錯誤（5xx，不可重試）


class KnowledgeCompletionError(Exception):
    """知識庫完善迴圈錯誤基類"""

    def __init__(self, message: str, category: ErrorCategory, details: Optional[Dict] = None):
        self.message = message
        self.category = category
        self.details = details or {}
        super().__init__(self.message)


class InvalidStateError(KnowledgeCompletionError):
    """無效的狀態轉換錯誤"""

    def __init__(self, current_state: str, target_state: str):
        super().__init__(
            message=f"無法從狀態 '{current_state}' 轉換至 '{target_state}'",
            category=ErrorCategory.BUSINESS_LOGIC_ERROR,
            details={"current_state": current_state, "target_state": target_state}
        )


class BacktestError(KnowledgeCompletionError):
    """回測執行錯誤"""

    def __init__(self, message: str, failed_scenarios: List[int]):
        super().__init__(
            message=message,
            category=ErrorCategory.EXTERNAL_API_ERROR,
            details={"failed_scenarios": failed_scenarios}
        )


class BudgetExceededError(KnowledgeCompletionError):
    """預算超支錯誤"""

    def __init__(self, budget_limit: float, total_cost: float):
        super().__init__(
            message=f"OpenAI API 成本已超過預算限制：${total_cost:.2f} > ${budget_limit:.2f}",
            category=ErrorCategory.BUSINESS_LOGIC_ERROR,
            details={"budget_limit": budget_limit, "total_cost": total_cost}
        )


class LoopNotFoundError(KnowledgeCompletionError):
    """迴圈不存在錯誤"""

    def __init__(self, loop_id: int):
        super().__init__(
            message=f"Loop {loop_id} 不存在",
            category=ErrorCategory.VALIDATION_ERROR,
            details={"loop_id": loop_id}
        )


class EmbeddingGenerationError(KnowledgeCompletionError):
    """Embedding 生成失敗錯誤"""

    def __init__(self, text: str, error_detail: str = None):
        details = {"text_length": len(text)}
        if error_detail:
            details["error"] = error_detail

        super().__init__(
            message=f"Embedding 生成失敗：{error_detail or '未知錯誤'}",
            category=ErrorCategory.EXTERNAL_SERVICE_ERROR,
            details=details
        )
