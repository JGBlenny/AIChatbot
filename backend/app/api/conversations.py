"""
對話管理 API
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.models.conversation import Conversation, ConversationStatus
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationFilter,
    PaginatedResponse,
    ConversationStats,
    LineConversationImport,
)
from app.services.line_parser import LineParser

router = APIRouter()


# ========== CRUD 操作 ==========

@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation: ConversationCreate,
    db: AsyncSession = Depends(get_db)
):
    """建立新對話"""
    db_conversation = Conversation(**conversation.model_dump())
    db.add(db_conversation)
    await db.commit()
    await db.refresh(db_conversation)
    return db_conversation


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """獲取單一對話"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在"
        )

    return conversation


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    conversation_update: ConversationUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新對話"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在"
        )

    # 更新欄位
    update_data = conversation_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conversation, field, value)

    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """刪除對話"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在"
        )

    await db.delete(conversation)
    await db.commit()


# ========== 列表與篩選 ==========

@router.get("/", response_model=PaginatedResponse)
async def list_conversations(
    page: int = 1,
    page_size: int = 20,
    status: Optional[ConversationStatus] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    min_quality: Optional[int] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """獲取對話列表（支援篩選和分頁）"""
    # 建立查詢
    query = select(Conversation)
    count_query = select(func.count(Conversation.id))

    # 應用篩選條件
    filters = []
    if status:
        filters.append(Conversation.status == status)
    if category:
        filters.append(Conversation.primary_category == category)
    if source:
        filters.append(Conversation.source == source)
    if min_quality:
        filters.append(Conversation.quality_score >= min_quality)
    if search:
        # 簡單搜尋（可改用全文搜索）
        search_filter = Conversation.raw_content.astext.contains(search)
        filters.append(search_filter)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # 計算總數
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分頁
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Conversation.created_at.desc())

    # 執行查詢
    result = await db.execute(query)
    conversations = result.scalars().all()

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=conversations
    )


# ========== LINE 對話匯入 ==========

@router.post("/import/line", response_model=ConversationResponse)
async def import_line_conversation(
    line_import: LineConversationImport,
    db: AsyncSession = Depends(get_db)
):
    """匯入 LINE 對話（JSON 格式）"""
    try:
        # 將 LineMessage 格式轉換為標準格式
        messages_data = [
            {
                "timestamp": msg.timestamp,
                "sender": msg.sender,
                "message": msg.message,
            }
            for msg in line_import.messages
        ]

        raw_content = {
            "messages": messages_data,
            "metadata": line_import.metadata or {},
        }

        # 建立對話記錄
        conversation = Conversation(
            raw_content=raw_content,
            source="line",
            source_id=line_import.conversation_id,
            status=ConversationStatus.PENDING,
        )

        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        return conversation

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"匯入失敗: {str(e)}"
        )


@router.post("/import/line/text", response_model=ConversationResponse)
async def import_line_text(
    file: UploadFile = File(...),
    default_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """匯入 LINE 對話（純文字檔案）"""
    try:
        # 讀取檔案內容
        content = await file.read()
        text = content.decode('utf-8')

        # 解析 LINE 對話
        parser = LineParser()
        line_conv = parser.parse_text(text, default_date)
        conv_dict = parser.to_conversation_dict(line_conv)

        # 建立對話記錄
        conversation = Conversation(
            raw_content=conv_dict,
            source="line",
            source_id=file.filename,
            status=ConversationStatus.PENDING,
        )

        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        return conversation

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"解析失敗: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"匯入失敗: {str(e)}"
        )


# ========== 統計 ==========

@router.get("/stats/summary", response_model=ConversationStats)
async def get_conversation_stats(
    db: AsyncSession = Depends(get_db)
):
    """獲取對話統計資訊"""
    # 總數
    total_result = await db.execute(select(func.count(Conversation.id)))
    total = total_result.scalar()

    # 按狀態統計
    status_query = select(
        Conversation.status,
        func.count(Conversation.id)
    ).group_by(Conversation.status)
    status_result = await db.execute(status_query)
    by_status = {status.value: count for status, count in status_result.all()}

    # 按分類統計
    category_query = select(
        Conversation.primary_category,
        func.count(Conversation.id)
    ).where(
        Conversation.primary_category.isnot(None)
    ).group_by(Conversation.primary_category)
    category_result = await db.execute(category_query)
    by_category = {cat: count for cat, count in category_result.all() if cat}

    # 平均品質分數
    avg_score_result = await db.execute(
        select(func.avg(Conversation.quality_score)).where(
            Conversation.quality_score.isnot(None)
        )
    )
    avg_quality_score = avg_score_result.scalar()

    # 最近匯入（7天內）
    from datetime import datetime, timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.created_at >= seven_days_ago
        )
    )
    recent_imports = recent_result.scalar()

    return ConversationStats(
        total=total,
        by_status=by_status,
        by_category=by_category,
        avg_quality_score=float(avg_quality_score) if avg_quality_score else None,
        recent_imports=recent_imports
    )
