"""
AI 處理 API
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.conversation import Conversation, ConversationStatus
from app.schemas.conversation import ConversationResponse, BatchProcessRequest, BatchProcessResponse
from app.services.openai_service import openai_service

router = APIRouter()


# ========== 單一對話處理 ==========

@router.post("/{conversation_id}/evaluate", response_model=ConversationResponse)
async def evaluate_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """評估對話品質"""
    # 獲取對話
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在"
        )

    # AI 評估
    evaluation = await openai_service.evaluate_quality(conversation.raw_content)

    # 更新對話
    conversation.quality_score = evaluation.get("score")
    conversation.status = ConversationStatus.PROCESSING

    # 儲存評估結果到 processed_content
    if not conversation.processed_content:
        conversation.processed_content = {}
    conversation.processed_content["evaluation"] = evaluation

    await db.commit()
    await db.refresh(conversation)

    return conversation


@router.post("/{conversation_id}/categorize", response_model=ConversationResponse)
async def categorize_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """對話分類"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在"
        )

    # AI 分類
    category_result = await openai_service.categorize_conversation(conversation.raw_content)

    # 更新對話
    conversation.primary_category = category_result.get("primary")
    conversation.secondary_categories = category_result.get("secondary", [])
    conversation.confidence_score = category_result.get("confidence")

    if not conversation.processed_content:
        conversation.processed_content = {}
    conversation.processed_content["category"] = category_result

    await db.commit()
    await db.refresh(conversation)

    return conversation


@router.post("/{conversation_id}/clean", response_model=ConversationResponse)
async def clean_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """清理並改寫對話"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在"
        )

    # AI 清理
    cleaned = await openai_service.clean_and_rewrite(conversation.raw_content)

    # 更新對話
    conversation.tags = cleaned.get("tags", [])

    if not conversation.processed_content:
        conversation.processed_content = {}
    conversation.processed_content["cleaned"] = cleaned

    await db.commit()
    await db.refresh(conversation)

    return conversation


@router.post("/{conversation_id}/extract", response_model=ConversationResponse)
async def extract_entities(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """提取實體、意圖、情感"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在"
        )

    # AI 提取
    entities = await openai_service.extract_entities(conversation.raw_content)

    # 更新對話
    conversation.entities = entities.get("entities", {})
    conversation.intents = entities.get("intents", [])
    conversation.sentiment = entities.get("sentiment")
    conversation.keywords = entities.get("keywords", [])

    if not conversation.processed_content:
        conversation.processed_content = {}
    conversation.processed_content["entities"] = entities

    await db.commit()
    await db.refresh(conversation)

    return conversation


@router.post("/{conversation_id}/process-all", response_model=ConversationResponse)
async def process_conversation_all(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """完整處理對話（品質評估 + 分類 + 清理 + 提取）"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在"
        )

    # 更新狀態為處理中
    conversation.status = ConversationStatus.PROCESSING
    await db.commit()

    try:
        # 批次處理
        results = await openai_service.process_conversation_batch(conversation.raw_content)

        # 更新對話
        conversation.quality_score = results["quality"].get("score")
        conversation.confidence_score = results["category"].get("confidence")
        conversation.primary_category = results["category"].get("primary")
        conversation.secondary_categories = results["category"].get("secondary", [])
        conversation.tags = results["cleaned"].get("tags", [])
        conversation.entities = results["entities"].get("entities", {})
        conversation.intents = results["entities"].get("intents", [])
        conversation.sentiment = results["entities"].get("sentiment")
        conversation.keywords = results["entities"].get("keywords", [])
        conversation.processed_content = results
        conversation.status = ConversationStatus.REVIEWED

        await db.commit()
        await db.refresh(conversation)

        return conversation

    except Exception as e:
        conversation.status = ConversationStatus.PENDING
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"處理失敗: {str(e)}"
        )


# ========== 批次處理 ==========

async def process_single_conversation(conversation_id: UUID, db: AsyncSession):
    """背景任務：處理單一對話"""
    try:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            return

        conversation.status = ConversationStatus.PROCESSING
        await db.commit()

        # 批次處理
        results = await openai_service.process_conversation_batch(conversation.raw_content)

        # 更新對話
        conversation.quality_score = results["quality"].get("score")
        conversation.confidence_score = results["category"].get("confidence")
        conversation.primary_category = results["category"].get("primary")
        conversation.secondary_categories = results["category"].get("secondary", [])
        conversation.tags = results["cleaned"].get("tags", [])
        conversation.entities = results["entities"].get("entities", {})
        conversation.intents = results["entities"].get("intents", [])
        conversation.sentiment = results["entities"].get("sentiment")
        conversation.keywords = results["entities"].get("keywords", [])
        conversation.processed_content = results
        conversation.status = ConversationStatus.REVIEWED

        await db.commit()

    except Exception as e:
        print(f"處理對話 {conversation_id} 失敗: {str(e)}")
        if conversation:
            conversation.status = ConversationStatus.PENDING
            await db.commit()


@router.post("/batch/process", response_model=BatchProcessResponse)
async def batch_process_conversations(
    request: BatchProcessRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """批次處理對話（背景執行）"""
    conversation_ids = request.conversation_ids

    # 驗證對話存在
    result = await db.execute(
        select(Conversation).where(Conversation.id.in_(conversation_ids))
    )
    conversations = result.scalars().all()

    if len(conversations) != len(conversation_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="部分對話不存在"
        )

    # 加入背景任務
    for conv_id in conversation_ids:
        background_tasks.add_task(process_single_conversation, conv_id, db)

    return BatchProcessResponse(
        total=len(conversation_ids),
        success=0,  # 背景執行，稍後更新
        failed=0,
        results=[{"conversation_id": str(cid), "status": "queued"} for cid in conversation_ids]
    )


# ========== 審核操作 ==========

@router.post("/{conversation_id}/approve", response_model=ConversationResponse)
async def approve_conversation(
    conversation_id: UUID,
    review_notes: str = "",
    reviewed_by: str = "admin",
    db: AsyncSession = Depends(get_db)
):
    """批准對話"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在"
        )

    from datetime import datetime
    conversation.status = ConversationStatus.APPROVED
    conversation.review_notes = review_notes
    conversation.reviewed_by = reviewed_by
    conversation.reviewed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(conversation)

    return conversation


@router.post("/{conversation_id}/reject", response_model=ConversationResponse)
async def reject_conversation(
    conversation_id: UUID,
    review_notes: str = "",
    reviewed_by: str = "admin",
    db: AsyncSession = Depends(get_db)
):
    """拒絕對話"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在"
        )

    from datetime import datetime
    conversation.status = ConversationStatus.REJECTED
    conversation.review_notes = review_notes
    conversation.reviewed_by = reviewed_by
    conversation.reviewed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(conversation)

    return conversation
