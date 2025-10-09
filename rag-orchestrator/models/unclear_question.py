"""
未釐清問題資料模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class UnclearQuestionStatus(str, Enum):
    """未釐清問題狀態"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class UnclearQuestionCreate(BaseModel):
    """建立未釐清問題"""
    question: str = Field(..., description="問題內容")
    user_id: Optional[str] = Field(None, description="使用者 ID")
    intent_type: Optional[str] = Field(None, description="意圖類型")
    similarity_score: Optional[float] = Field(None, ge=0, le=1, description="相似度分數")
    retrieved_docs: Optional[dict] = Field(None, description="檢索到的文件")


class UnclearQuestionUpdate(BaseModel):
    """更新未釐清問題"""
    status: Optional[UnclearQuestionStatus] = None
    assigned_to: Optional[str] = None
    resolution_note: Optional[str] = None
    suggested_answers: Optional[List[str]] = None


class UnclearQuestionResponse(BaseModel):
    """未釐清問題回應"""
    id: int
    question: str
    user_id: Optional[str]
    intent_type: Optional[str]
    similarity_score: Optional[float]
    retrieved_docs: Optional[dict]
    frequency: int
    first_asked_at: datetime
    last_asked_at: datetime
    status: str
    assigned_to: Optional[str]
    resolved_at: Optional[datetime]
    resolution_note: Optional[str]
    suggested_answers: Optional[List[str]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UnclearQuestionStats(BaseModel):
    """未釐清問題統計"""
    total: int = Field(..., description="總數")
    pending: int = Field(..., description="待處理")
    in_progress: int = Field(..., description="處理中")
    resolved: int = Field(..., description="已解決")
    ignored: int = Field(..., description="已忽略")
    top_questions: List[dict] = Field(..., description="最常見問題")
