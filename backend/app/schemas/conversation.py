"""
Pydantic Schemas for Conversations
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID

from app.models.conversation import ConversationStatus


# ========== 對話資料 Schemas ==========

class ConversationBase(BaseModel):
    """對話基礎 Schema"""
    raw_content: Dict[str, Any] = Field(..., description="原始對話內容")
    source: Optional[str] = Field("line", description="來源（line/manual）")
    source_id: Optional[str] = Field(None, description="來源系統 ID")


class ConversationCreate(ConversationBase):
    """建立對話"""
    pass


class ConversationUpdate(BaseModel):
    """更新對話"""
    processed_content: Optional[Dict[str, Any]] = None
    quality_score: Optional[int] = Field(None, ge=1, le=10)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    primary_category: Optional[str] = None
    secondary_categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    entities: Optional[Dict[str, Any]] = None
    intents: Optional[List[str]] = None
    sentiment: Optional[str] = None
    status: Optional[ConversationStatus] = None
    review_notes: Optional[str] = None


class ConversationResponse(ConversationBase):
    """對話回應"""
    id: UUID
    processed_content: Optional[Dict[str, Any]] = None
    quality_score: Optional[int] = None
    confidence_score: Optional[float] = None
    primary_category: Optional[str] = None
    secondary_categories: Optional[List[str]] = []
    tags: Optional[List[str]] = []
    keywords: Optional[List[str]] = []
    entities: Optional[Dict[str, Any]] = None
    intents: Optional[List[str]] = []
    sentiment: Optional[str] = None
    status: ConversationStatus
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    exported_to_md: bool = False
    md_file_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== LINE 對話匯入 Schemas ==========

class LineMessage(BaseModel):
    """LINE 訊息格式"""
    timestamp: str = Field(..., description="時間戳記")
    sender: str = Field(..., description="發送者")
    message: str = Field(..., description="訊息內容")


class LineConversationImport(BaseModel):
    """LINE 對話匯入格式"""
    messages: List[LineMessage] = Field(..., description="訊息列表")
    conversation_id: Optional[str] = Field(None, description="對話 ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="額外元數據")


# ========== AI 處理結果 Schemas ==========

class AIProcessingResult(BaseModel):
    """AI 處理結果"""
    question: str = Field(..., description="用戶問題")
    answer: str = Field(..., description="標準答案")
    context: Optional[str] = Field(None, description="重要上下文")
    tags: List[str] = Field(default_factory=list, description="標籤")
    confidence: float = Field(..., ge=0.0, le=1.0, description="信心度")


class QualityEvaluation(BaseModel):
    """品質評估結果"""
    score: int = Field(..., ge=1, le=10, description="品質分數")
    reasoning: str = Field(..., description="評分理由")
    suggestions: List[str] = Field(default_factory=list, description="改進建議")


class CategoryResult(BaseModel):
    """分類結果"""
    primary: str = Field(..., description="主要分類")
    secondary: List[str] = Field(default_factory=list, description="次要分類")
    confidence: float = Field(..., ge=0.0, le=1.0, description="信心度")


# ========== 批次操作 Schemas ==========

class BatchProcessRequest(BaseModel):
    """批次處理請求"""
    conversation_ids: List[UUID] = Field(..., description="對話 ID 列表")
    action: str = Field(..., description="操作類型（process/approve/reject/export）")
    parameters: Optional[Dict[str, Any]] = Field(None, description="操作參數")


class BatchProcessResponse(BaseModel):
    """批次處理回應"""
    total: int = Field(..., description="總數")
    success: int = Field(..., description="成功數")
    failed: int = Field(..., description="失敗數")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="詳細結果")


# ========== 列表與分頁 Schemas ==========

class ConversationFilter(BaseModel):
    """對話篩選條件"""
    status: Optional[ConversationStatus] = None
    primary_category: Optional[str] = None
    source: Optional[str] = None
    min_quality_score: Optional[int] = Field(None, ge=1, le=10)
    tags: Optional[List[str]] = None
    search: Optional[str] = Field(None, description="搜尋關鍵字")


class PaginatedResponse(BaseModel):
    """分頁回應"""
    total: int = Field(..., description="總數")
    page: int = Field(..., description="當前頁碼")
    page_size: int = Field(..., description="每頁數量")
    items: List[ConversationResponse] = Field(..., description="資料列表")


# ========== 統計 Schemas ==========

class ConversationStats(BaseModel):
    """對話統計"""
    total: int = Field(..., description="總數")
    by_status: Dict[str, int] = Field(..., description="按狀態統計")
    by_category: Dict[str, int] = Field(..., description="按分類統計")
    avg_quality_score: Optional[float] = Field(None, description="平均品質分數")
    recent_imports: int = Field(..., description="最近匯入數量")
