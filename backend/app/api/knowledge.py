"""
知識庫管理 API
"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.config import settings
from app.models.conversation import Conversation, ConversationStatus, KnowledgeFile
from app.services.markdown_generator import MarkdownGenerator
from pydantic import BaseModel

router = APIRouter()


# ========== Schemas ==========

class KnowledgeGenerateRequest(BaseModel):
    """生成知識庫請求"""
    categories: Optional[List[str]] = None  # None = 所有分類
    min_quality_score: Optional[int] = 7    # 最低品質分數
    only_approved: bool = True              # 僅已批准的對話


class KnowledgeGenerateResponse(BaseModel):
    """生成知識庫回應"""
    success: bool
    files_generated: List[str]
    total_conversations: int
    message: str


class KnowledgeFileInfo(BaseModel):
    """知識庫檔案資訊"""
    filename: str
    category: str
    file_path: str
    size_bytes: int
    conversations_count: int
    last_updated: str


class KnowledgeFileListResponse(BaseModel):
    """知識庫檔案列表"""
    files: List[KnowledgeFileInfo]
    total: int


# ========== API 端點 ==========

@router.post("/generate", response_model=KnowledgeGenerateResponse)
async def generate_knowledge_base(
    request: KnowledgeGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    生成 Markdown 知識庫

    從已批准的對話生成 Markdown 檔案
    """
    # 建立查詢條件
    filters = []

    if request.only_approved:
        filters.append(Conversation.status == ConversationStatus.APPROVED)

    if request.min_quality_score:
        filters.append(Conversation.quality_score >= request.min_quality_score)

    if request.categories:
        filters.append(Conversation.primary_category.in_(request.categories))

    # 查詢對話
    query = select(Conversation)
    if filters:
        query = query.where(and_(*filters))

    result = await db.execute(query)
    conversations = result.scalars().all()

    if not conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="沒有符合條件的對話"
        )

    # 轉換為字典格式
    conv_dicts = [
        {
            "id": str(conv.id),
            "primary_category": conv.primary_category,
            "tags": conv.tags or [],
            "quality_score": conv.quality_score,
            "confidence_score": conv.confidence_score,
            "processed_content": conv.processed_content or {},
            "raw_content": conv.raw_content or {}
        }
        for conv in conversations
    ]

    # 生成 Markdown
    generator = MarkdownGenerator(output_dir=settings.KNOWLEDGE_BASE_PATH)
    file_paths = generator.generate_from_conversations(conv_dicts)

    # 生成索引
    generator.generate_index(file_paths)

    # 更新對話的匯出狀態
    for conv in conversations:
        conv.exported_to_md = True
        conv.md_file_path = file_paths.get(f"{conv.primary_category}.md")

    await db.commit()

    return KnowledgeGenerateResponse(
        success=True,
        files_generated=list(file_paths.keys()),
        total_conversations=len(conversations),
        message=f"成功生成 {len(file_paths)} 個知識庫檔案"
    )


@router.post("/generate/{category}", response_model=KnowledgeGenerateResponse)
async def generate_category_knowledge(
    category: str,
    min_quality_score: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """
    生成特定分類的知識庫

    僅生成單一分類的 Markdown 檔案
    """
    # 查詢指定分類的已批准對話
    query = select(Conversation).where(
        and_(
            Conversation.status == ConversationStatus.APPROVED,
            Conversation.primary_category == category,
            Conversation.quality_score >= min_quality_score
        )
    )

    result = await db.execute(query)
    conversations = result.scalars().all()

    if not conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"沒有分類為『{category}』的已批准對話"
        )

    # 轉換為字典
    conv_dicts = [
        {
            "id": str(conv.id),
            "primary_category": conv.primary_category,
            "tags": conv.tags or [],
            "quality_score": conv.quality_score,
            "confidence_score": conv.confidence_score,
            "processed_content": conv.processed_content or {},
            "raw_content": conv.raw_content or {}
        }
        for conv in conversations
    ]

    # 生成 Markdown
    generator = MarkdownGenerator(output_dir=settings.KNOWLEDGE_BASE_PATH)
    file_paths = generator.generate_from_conversations(conv_dicts, category=category)

    # 更新對話狀態
    for conv in conversations:
        conv.exported_to_md = True
        conv.md_file_path = list(file_paths.values())[0] if file_paths else None

    await db.commit()

    return KnowledgeGenerateResponse(
        success=True,
        files_generated=list(file_paths.keys()),
        total_conversations=len(conversations),
        message=f"成功生成分類『{category}』的知識庫"
    )


@router.get("/files", response_model=KnowledgeFileListResponse)
async def list_knowledge_files():
    """
    列出所有知識庫檔案

    掃描 knowledge-base 目錄
    """
    import os
    from pathlib import Path

    kb_path = Path(settings.KNOWLEDGE_BASE_PATH)

    if not kb_path.exists():
        return KnowledgeFileListResponse(files=[], total=0)

    files_info = []

    for md_file in kb_path.glob("*.md"):
        if md_file.name == "README.md":
            continue

        # 讀取檔案資訊
        stat = md_file.stat()
        category = md_file.stem  # 檔名（不含副檔名）

        # 簡單計算對話數（統計 ## 標題數量）
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
            conv_count = content.count("\n## ") - content.count("\n## 📖")  # 排除說明標題

        files_info.append(
            KnowledgeFileInfo(
                filename=md_file.name,
                category=category,
                file_path=str(md_file.absolute()),
                size_bytes=stat.st_size,
                conversations_count=conv_count,
                last_updated=stat.st_mtime.__str__()
            )
        )

    return KnowledgeFileListResponse(
        files=sorted(files_info, key=lambda x: x.category),
        total=len(files_info)
    )


@router.get("/files/{category}")
async def get_knowledge_file_content(category: str):
    """
    獲取知識庫檔案內容

    返回 Markdown 原始內容
    """
    from pathlib import Path

    file_path = Path(settings.KNOWLEDGE_BASE_PATH) / f"{category}.md"

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知識庫檔案『{category}.md』不存在"
        )

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "category": category,
        "filename": f"{category}.md",
        "content": content
    }


@router.post("/export/{conversation_id}")
async def export_conversation_to_md(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    匯出單一對話為 Markdown

    將指定對話匯出為獨立的 MD 檔案
    """
    # 查詢對話
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在"
        )

    # 轉換為字典
    conv_dict = {
        "id": str(conversation.id),
        "primary_category": conversation.primary_category or "未分類",
        "tags": conversation.tags or [],
        "quality_score": conversation.quality_score,
        "confidence_score": conversation.confidence_score,
        "processed_content": conversation.processed_content or {},
        "raw_content": conversation.raw_content or {}
    }

    # 生成 Markdown
    generator = MarkdownGenerator(output_dir=settings.KNOWLEDGE_BASE_PATH)
    file_paths = generator.generate_from_conversations(
        [conv_dict],
        category=conv_dict["primary_category"]
    )

    # 更新對話狀態
    conversation.exported_to_md = True
    conversation.md_file_path = list(file_paths.values())[0] if file_paths else None

    await db.commit()

    return {
        "success": True,
        "conversation_id": str(conversation_id),
        "file_path": conversation.md_file_path,
        "message": "對話已匯出為 Markdown"
    }


@router.delete("/files/{category}")
async def delete_knowledge_file(category: str):
    """
    刪除知識庫檔案

    刪除指定分類的 MD 檔案
    """
    from pathlib import Path

    file_path = Path(settings.KNOWLEDGE_BASE_PATH) / f"{category}.md"

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知識庫檔案『{category}.md』不存在"
        )

    file_path.unlink()

    return {
        "success": True,
        "message": f"已刪除知識庫檔案『{category}.md』"
    }


@router.get("/stats")
async def get_knowledge_stats(db: AsyncSession = Depends(get_db)):
    """
    獲取知識庫統計

    返回知識庫的統計資訊
    """
    from pathlib import Path
    from sqlalchemy import func

    # 檔案統計
    kb_path = Path(settings.KNOWLEDGE_BASE_PATH)
    md_files = list(kb_path.glob("*.md"))
    total_files = len([f for f in md_files if f.name != "README.md"])

    # 計算總大小
    total_size = sum(f.stat().st_size for f in md_files)

    # 對話統計
    exported_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.exported_to_md == True
        )
    )
    exported_count = exported_result.scalar()

    approved_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.status == ConversationStatus.APPROVED
        )
    )
    approved_count = approved_result.scalar()

    return {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "conversations_exported": exported_count,
        "conversations_approved": approved_count,
        "export_coverage": round(exported_count / approved_count * 100, 2) if approved_count > 0 else 0
    }
