"""
對話資料模型
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ARRAY, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import enum

from app.core.database import Base


class ConversationStatus(str, enum.Enum):
    """對話處理狀態"""
    PENDING = "pending"           # 待處理
    PROCESSING = "processing"     # 處理中
    REVIEWED = "reviewed"         # 已審核
    APPROVED = "approved"         # 已批准
    REJECTED = "rejected"         # 已拒絕
    EXPORTED = "exported"         # 已匯出


class Conversation(Base):
    """對話資料表"""
    __tablename__ = "conversations"

    # 主鍵
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 原始資料
    raw_content = Column(JSONB, nullable=False, comment="原始對話內容（JSON 格式）")
    source = Column(String(50), comment="來源系統（如 zendesk, intercom, manual）")
    source_id = Column(String(255), comment="來源系統 ID")
    imported_at = Column(DateTime, default=datetime.utcnow, comment="匯入時間")

    # AI 處理結果
    processed_content = Column(JSONB, comment="AI 處理後的內容")
    quality_score = Column(Integer, comment="品質分數 1-10")
    confidence_score = Column(Float, comment="AI 信心度 0-1")

    # 分類與標記
    primary_category = Column(String(50), comment="主要分類")
    secondary_categories = Column(ARRAY(String), comment="次要分類")
    tags = Column(ARRAY(String), comment="標籤")
    keywords = Column(ARRAY(String), comment="關鍵字")

    # 提取資訊
    entities = Column(JSONB, comment="實體（產品、功能等）")
    intents = Column(ARRAY(String), comment="意圖")
    sentiment = Column(String(20), comment="情感分析")

    # 狀態管理
    status = Column(
        SQLEnum(ConversationStatus),
        default=ConversationStatus.PENDING,
        comment="處理狀態"
    )
    review_notes = Column(Text, comment="審核備註")
    reviewed_by = Column(String(100), comment="審核人員")
    reviewed_at = Column(DateTime, comment="審核時間")

    # MD 生成
    exported_to_md = Column(Boolean, default=False, comment="是否已匯出到 MD")
    md_file_path = Column(String(255), comment="MD 檔案路徑")
    chunk_ids = Column(ARRAY(String), comment="向量塊 IDs")

    # 時間戳記
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Conversation {self.id} - {self.primary_category} - {self.status}>"


class KnowledgeFile(Base):
    """MD 知識庫檔案管理"""
    __tablename__ = "knowledge_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    file_path = Column(String(255), unique=True, nullable=False, comment="檔案路徑")
    category = Column(String(50), comment="分類")

    content = Column(Text, comment="MD 原始內容")
    version = Column(Integer, default=1, comment="版本號")

    # 元數據
    metadata = Column(JSONB, comment="分類元數據")
    conversation_ids = Column(ARRAY(UUID(as_uuid=True)), comment="來源對話 IDs")
    total_chunks = Column(Integer, default=0, comment="總分塊數")

    # 向量化資訊
    embedding_model = Column(String(100), comment="嵌入模型")
    vectorized_at = Column(DateTime, comment="向量化時間")
    vector_ids = Column(ARRAY(String), comment="向量資料庫 IDs")

    # 版本控制
    previous_version_id = Column(UUID(as_uuid=True), comment="前一版本 ID")
    change_summary = Column(Text, comment="變更摘要")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<KnowledgeFile {self.file_path} v{self.version}>"


class ProcessingLog(Base):
    """資料處理日誌"""
    __tablename__ = "processing_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), comment="對話 ID")

    action = Column(String(50), nullable=False, comment="操作類型")
    details = Column(JSONB, comment="操作詳情")
    user_id = Column(String(100), comment="操作人員")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ProcessingLog {self.action} at {self.created_at}>"


class VectorEmbedding(Base):
    """向量嵌入追蹤"""
    __tablename__ = "vector_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    vector_store_id = Column(String(255), unique=True, comment="向量資料庫 ID")
    source_type = Column(String(20), comment="來源類型（conversation/md_chunk）")
    source_id = Column(UUID(as_uuid=True), comment="來源 ID")

    chunk_text = Column(Text, comment="分塊文字")
    chunk_index = Column(Integer, comment="分塊索引")

    metadata = Column(JSONB, comment="元數據")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<VectorEmbedding {self.vector_store_id}>"
