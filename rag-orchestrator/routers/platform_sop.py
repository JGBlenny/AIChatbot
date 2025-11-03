"""
Platform SOP 管理 API
用途：平台管理員管理 SOP 範本（按業種分類的參考範本）
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from pydantic import BaseModel, Field
import pandas as pd
import io

router = APIRouter(prefix="/api/v1/platform/sop")


# ========================================
# Pydantic Schemas
# ========================================

class PlatformSOPCategoryCreate(BaseModel):
    """建立平台 SOP 分類"""
    category_name: str = Field(..., description="分類名稱（全局唯一）", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="分類說明")
    display_order: int = Field(0, description="顯示順序", ge=0)
    template_notes: Optional[str] = Field(None, description="範本說明（幫助業者理解此分類）")


class PlatformSOPCategoryUpdate(BaseModel):
    """更新平台 SOP 分類"""
    category_name: Optional[str] = Field(None, description="分類名稱", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="分類說明")
    display_order: Optional[int] = Field(None, description="顯示順序", ge=0)
    template_notes: Optional[str] = Field(None, description="範本說明")


class PlatformSOPGroupCreate(BaseModel):
    """建立平台 SOP 群組"""
    category_id: int = Field(..., description="所屬分類ID")
    group_name: str = Field(..., description="群組名稱（說明）", min_length=1, max_length=500)
    description: Optional[str] = Field(None, description="詳細描述")
    display_order: int = Field(1, description="顯示順序", ge=1)


class PlatformSOPGroupUpdate(BaseModel):
    """更新平台 SOP 群組"""
    group_name: Optional[str] = Field(None, description="群組名稱", min_length=1, max_length=500)
    description: Optional[str] = Field(None, description="詳細描述")
    display_order: Optional[int] = Field(None, description="顯示順序", ge=1)


class PlatformSOPTemplateCreate(BaseModel):
    """建立平台 SOP 範本"""
    category_id: int = Field(..., description="所屬分類ID")
    group_id: Optional[int] = Field(None, description="所屬群組ID（可選，對應 Excel 的「說明」）")
    business_type: Optional[str] = Field(None, description="業種類型（full_service=包租, property_management=代管, NULL=通用）")
    item_number: int = Field(..., description="項次編號", ge=1)
    item_name: str = Field(..., description="項目名稱", min_length=1, max_length=200)
    content: str = Field(..., description="範本內容")
    intent_ids: Optional[List[int]] = Field(None, description="關聯意圖ID列表（支援多意圖）")
    priority: int = Field(50, description="優先級（0-100）", ge=0, le=100)
    template_notes: Optional[str] = Field(None, description="範本說明（解釋此 SOP 的目的）")
    customization_hint: Optional[str] = Field(None, description="自訂提示（建議業者如何調整）")


class PlatformSOPTemplateUpdate(BaseModel):
    """更新平台 SOP 範本"""
    category_id: Optional[int] = Field(None, description="所屬分類ID")
    group_id: Optional[int] = Field(None, description="所屬群組ID")
    business_type: Optional[str] = Field(None, description="業種類型")
    item_number: Optional[int] = Field(None, description="項次編號", ge=1)
    item_name: Optional[str] = Field(None, description="項目名稱", min_length=1, max_length=200)
    content: Optional[str] = Field(None, description="範本內容")
    intent_ids: Optional[List[int]] = Field(None, description="關聯意圖ID列表（支援多意圖）")
    priority: Optional[int] = Field(None, description="優先級", ge=0, le=100)
    template_notes: Optional[str] = Field(None, description="範本說明")
    customization_hint: Optional[str] = Field(None, description="自訂提示")


# ========================================
# 分類管理 API
# ========================================

@router.get("/categories", summary="取得所有平台 SOP 分類")
async def get_platform_sop_categories(
    request: Request,
    include_inactive: bool = False
):
    """
    取得所有平台 SOP 分類

    **權限**: 平台管理員
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            query = """
                SELECT
                    id,
                    category_name,
                    description,
                    display_order,
                    template_notes,
                    is_active,
                    created_at,
                    updated_at
                FROM platform_sop_categories
                WHERE is_active = TRUE OR $1 = TRUE
                ORDER BY display_order, id
            """
            rows = await conn.fetch(query, include_inactive)

            categories = []
            for row in rows:
                categories.append({
                    "id": row["id"],
                    "category_name": row["category_name"],
                    "description": row["description"],
                    "display_order": row["display_order"],
                    "template_notes": row["template_notes"],
                    "is_active": row["is_active"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                })

            return {"categories": categories}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得分類失敗: {str(e)}")


@router.post("/categories", status_code=201, summary="建立平台 SOP 分類")
async def create_platform_sop_category(
    request: Request,
    category: PlatformSOPCategoryCreate
):
    """
    建立新的平台 SOP 分類

    **權限**: 平台管理員
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            # 檢查分類名稱是否重複
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM platform_sop_categories WHERE category_name = $1)",
                category.category_name
            )
            if exists:
                raise HTTPException(
                    status_code=400,
                    detail=f"分類名稱「{category.category_name}」已存在"
                )

            # 插入新分類
            row = await conn.fetchrow("""
                INSERT INTO platform_sop_categories (
                    category_name, description, display_order, template_notes
                )
                VALUES ($1, $2, $3, $4)
                RETURNING id, category_name, description, display_order, template_notes,
                          is_active, created_at, updated_at
            """, category.category_name, category.description, category.display_order, category.template_notes)

            return {
                "id": row["id"],
                "category_name": row["category_name"],
                "description": row["description"],
                "display_order": row["display_order"],
                "template_notes": row["template_notes"],
                "is_active": row["is_active"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立分類失敗: {str(e)}")


@router.put("/categories/{category_id}", summary="更新平台 SOP 分類")
async def update_platform_sop_category(
    request: Request,
    category_id: int,
    category: PlatformSOPCategoryUpdate
):
    """
    更新平台 SOP 分類

    **權限**: 平台管理員
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            # 檢查分類是否存在
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM platform_sop_categories WHERE id = $1)",
                category_id
            )
            if not exists:
                raise HTTPException(status_code=404, detail=f"分類 ID {category_id} 不存在")

            # 建立更新欄位
            update_fields = []
            values = []
            param_count = 1

            if category.category_name is not None:
                # 檢查新名稱是否與其他分類重複
                duplicate = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM platform_sop_categories WHERE category_name = $1 AND id != $2)",
                    category.category_name, category_id
                )
                if duplicate:
                    raise HTTPException(status_code=400, detail=f"分類名稱「{category.category_name}」已被使用")
                update_fields.append(f"category_name = ${param_count}")
                values.append(category.category_name)
                param_count += 1

            if category.description is not None:
                update_fields.append(f"description = ${param_count}")
                values.append(category.description)
                param_count += 1

            if category.display_order is not None:
                update_fields.append(f"display_order = ${param_count}")
                values.append(category.display_order)
                param_count += 1

            if category.template_notes is not None:
                update_fields.append(f"template_notes = ${param_count}")
                values.append(category.template_notes)
                param_count += 1

            if not update_fields:
                raise HTTPException(status_code=400, detail="沒有提供更新欄位")

            # 更新時間
            update_fields.append(f"updated_at = NOW()")

            # 執行更新
            values.append(category_id)
            query = f"""
                UPDATE platform_sop_categories
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
                RETURNING id, category_name, description, display_order, template_notes,
                          is_active, created_at, updated_at
            """
            row = await conn.fetchrow(query, *values)

            return {
                "id": row["id"],
                "category_name": row["category_name"],
                "description": row["description"],
                "display_order": row["display_order"],
                "template_notes": row["template_notes"],
                "is_active": row["is_active"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新分類失敗: {str(e)}")


@router.delete("/categories/{category_id}", summary="刪除平台 SOP 分類")
async def delete_platform_sop_category(
    request: Request,
    category_id: int
):
    """
    軟刪除平台 SOP 分類（設置 is_active = FALSE）

    **權限**: 平台管理員
    **注意**: 會同時停用此分類下的所有範本
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            # 檢查分類是否存在
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM platform_sop_categories WHERE id = $1)",
                category_id
            )
            if not exists:
                raise HTTPException(status_code=404, detail=f"分類 ID {category_id} 不存在")

            # 軟刪除分類及其下的範本
            async with conn.transaction():
                await conn.execute(
                    "UPDATE platform_sop_categories SET is_active = FALSE, updated_at = NOW() WHERE id = $1",
                    category_id
                )
                await conn.execute(
                    "UPDATE platform_sop_templates SET is_active = FALSE, updated_at = NOW() WHERE category_id = $1",
                    category_id
                )

            return {"message": "分類已刪除", "category_id": category_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除分類失敗: {str(e)}")


# ========================================
# 群組管理 API
# ========================================

@router.get("/groups", summary="取得所有平台 SOP 群組")
async def get_platform_sop_groups(
    request: Request,
    category_id: Optional[int] = None,
    include_inactive: bool = False
):
    """
    取得所有平台 SOP 群組（支援 3 層架構）

    **Query Parameters**:
    - category_id: 過濾特定分類（可選）
    - include_inactive: 是否包含已停用的群組

    **權限**: 平台管理員
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            query = """
                SELECT
                    g.id,
                    g.category_id,
                    c.category_name,
                    c.display_order as category_display_order,
                    g.group_name,
                    g.description,
                    g.display_order,
                    g.is_active,
                    g.created_at,
                    g.updated_at,
                    COUNT(t.id) as template_count
                FROM platform_sop_groups g
                INNER JOIN platform_sop_categories c ON g.category_id = c.id
                LEFT JOIN platform_sop_templates t ON t.group_id = g.id AND t.is_active = TRUE
                WHERE (g.is_active = TRUE OR $1 = TRUE)
                  AND ($2::INTEGER IS NULL OR g.category_id = $2)
                GROUP BY g.id, g.category_id, c.category_name, c.display_order,
                         g.group_name, g.description, g.display_order, g.is_active,
                         g.created_at, g.updated_at
                ORDER BY c.display_order, g.display_order
            """
            rows = await conn.fetch(query, include_inactive, category_id)

            groups = []
            for row in rows:
                groups.append({
                    "id": row["id"],
                    "category_id": row["category_id"],
                    "category_name": row["category_name"],
                    "group_name": row["group_name"],
                    "description": row["description"],
                    "display_order": row["display_order"],
                    "is_active": row["is_active"],
                    "template_count": row["template_count"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                })

            return {"groups": groups}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得群組失敗: {str(e)}")


@router.post("/groups", status_code=201, summary="建立平台 SOP 群組")
async def create_platform_sop_group(
    request: Request,
    group: PlatformSOPGroupCreate
):
    """
    建立新的平台 SOP 群組

    **權限**: 平台管理員
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            # 驗證分類是否存在
            category_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM platform_sop_categories WHERE id = $1 AND is_active = TRUE)",
                group.category_id
            )
            if not category_exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"分類 ID {group.category_id} 不存在或已停用"
                )

            # 插入新群組
            row = await conn.fetchrow("""
                INSERT INTO platform_sop_groups (
                    category_id, group_name, description, display_order
                )
                VALUES ($1, $2, $3, $4)
                RETURNING id, category_id, group_name, description, display_order, is_active, created_at, updated_at
            """,
                group.category_id, group.group_name, group.description, group.display_order
            )

            return {
                "id": row["id"],
                "category_id": row["category_id"],
                "group_name": row["group_name"],
                "description": row["description"],
                "display_order": row["display_order"],
                "is_active": row["is_active"],
                "template_count": 0,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立群組失敗: {str(e)}")


@router.put("/groups/{group_id}", summary="更新平台 SOP 群組")
async def update_platform_sop_group(
    request: Request,
    group_id: int,
    group: PlatformSOPGroupUpdate
):
    """
    更新平台 SOP 群組

    **權限**: 平台管理員
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            # 驗證群組是否存在
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM platform_sop_groups WHERE id = $1)",
                group_id
            )
            if not exists:
                raise HTTPException(status_code=404, detail=f"群組 ID {group_id} 不存在")

            # 構建動態更新語句
            updates = []
            params = []
            param_count = 1

            if group.group_name is not None:
                updates.append(f"group_name = ${param_count}")
                params.append(group.group_name)
                param_count += 1

            if group.description is not None:
                updates.append(f"description = ${param_count}")
                params.append(group.description)
                param_count += 1

            if group.display_order is not None:
                updates.append(f"display_order = ${param_count}")
                params.append(group.display_order)
                param_count += 1

            if not updates:
                raise HTTPException(status_code=400, detail="沒有提供任何更新欄位")

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(group_id)

            query = f"""
                UPDATE platform_sop_groups
                SET {', '.join(updates)}
                WHERE id = ${param_count}
                RETURNING id, category_id, group_name, description, display_order, is_active, created_at, updated_at
            """

            row = await conn.fetchrow(query, *params)

            # 查詢模板數量
            template_count = await conn.fetchval(
                "SELECT COUNT(*) FROM platform_sop_templates WHERE group_id = $1 AND is_active = TRUE",
                group_id
            )

            return {
                "id": row["id"],
                "category_id": row["category_id"],
                "group_name": row["group_name"],
                "description": row["description"],
                "display_order": row["display_order"],
                "is_active": row["is_active"],
                "template_count": template_count,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新群組失敗: {str(e)}")


@router.delete("/groups/{group_id}", summary="刪除平台 SOP 群組")
async def delete_platform_sop_group(
    request: Request,
    group_id: int,
    move_to_group_id: Optional[int] = None
):
    """
    刪除平台 SOP 群組

    **Query Parameters**:
    - move_to_group_id: 將關聯模板移動到指定群組（可選，若未指定則設為 NULL）

    **權限**: 平台管理員
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            # 驗證群組是否存在
            group_row = await conn.fetchrow(
                "SELECT id, group_name FROM platform_sop_groups WHERE id = $1",
                group_id
            )
            if not group_row:
                raise HTTPException(status_code=404, detail=f"群組 ID {group_id} 不存在")

            # 查詢關聯的模板數量
            template_count = await conn.fetchval(
                "SELECT COUNT(*) FROM platform_sop_templates WHERE group_id = $1 AND is_active = TRUE",
                group_id
            )

            # 如果有指定move_to_group_id，驗證目標群組是否存在
            if move_to_group_id is not None:
                target_exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM platform_sop_groups WHERE id = $1 AND is_active = TRUE)",
                    move_to_group_id
                )
                if not target_exists:
                    raise HTTPException(
                        status_code=404,
                        detail=f"目標群組 ID {move_to_group_id} 不存在或已停用"
                    )

            # 更新關聯的模板（移動到目標群組或設為 NULL）
            await conn.execute(
                "UPDATE platform_sop_templates SET group_id = $1, updated_at = CURRENT_TIMESTAMP WHERE group_id = $2",
                move_to_group_id, group_id
            )

            # 刪除群組（軟刪除）
            await conn.execute(
                "UPDATE platform_sop_groups SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP WHERE id = $1",
                group_id
            )

            return {
                "message": f"群組「{group_row['group_name']}」已刪除",
                "deleted_group_id": group_id,
                "affected_templates_count": template_count,
                "moved_to_group_id": move_to_group_id
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除群組失敗: {str(e)}")


# ========================================
# 範本管理 API
# ========================================

@router.get("/templates", summary="取得所有平台 SOP 範本")
async def get_platform_sop_templates(
    request: Request,
    category_id: Optional[int] = None,
    business_type: Optional[str] = None,
    include_inactive: bool = False
):
    """
    取得所有平台 SOP 範本

    **Query Parameters**:
    - category_id: 過濾特定分類（可選）
    - business_type: 過濾業種類型（full_service, property_management, NULL=通用）
    - include_inactive: 是否包含已停用的範本（預設 False）

    **權限**: 平台管理員
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            query = """
                SELECT
                    t.id,
                    t.category_id,
                    c.category_name,
                    t.group_id,
                    g.group_name,
                    g.display_order as group_display_order,
                    t.business_type,
                    t.item_number,
                    t.item_name,
                    t.content,
                    t.priority,
                    t.template_notes,
                    t.customization_hint,
                    t.is_active,
                    t.created_at,
                    t.updated_at,
                    COALESCE(
                        (SELECT ARRAY_AGG(psti.intent_id ORDER BY psti.intent_id)
                         FROM platform_sop_template_intents psti
                         WHERE psti.template_id = t.id),
                        ARRAY[]::INTEGER[]
                    ) as intent_ids
                FROM platform_sop_templates t
                INNER JOIN platform_sop_categories c ON t.category_id = c.id
                LEFT JOIN platform_sop_groups g ON t.group_id = g.id
                WHERE (t.is_active = TRUE OR $1 = TRUE)
                  AND ($2::INTEGER IS NULL OR t.category_id = $2)
                  AND ($3::VARCHAR IS NULL OR t.business_type = $3 OR ($3 = 'null' AND t.business_type IS NULL))
                ORDER BY c.display_order, g.display_order NULLS LAST, t.item_number
            """
            rows = await conn.fetch(query, include_inactive, category_id, business_type)

            templates = []
            for row in rows:
                templates.append({
                    "id": row["id"],
                    "category_id": row["category_id"],
                    "category_name": row["category_name"],
                    "group_id": row["group_id"],
                    "group_name": row["group_name"],
                    "business_type": row["business_type"],
                    "item_number": row["item_number"],
                    "item_name": row["item_name"],
                    "content": row["content"],
                    "intent_ids": row["intent_ids"],
                    "priority": row["priority"],
                    "template_notes": row["template_notes"],
                    "customization_hint": row["customization_hint"],
                    "is_active": row["is_active"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                })

            return {"templates": templates}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得範本失敗: {str(e)}")


@router.post("/templates", status_code=201, summary="建立平台 SOP 範本")
async def create_platform_sop_template(
    request: Request,
    template: PlatformSOPTemplateCreate
):
    """
    建立新的平台 SOP 範本

    **權限**: 平台管理員
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            # 驗證分類是否存在
            category_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM platform_sop_categories WHERE id = $1 AND is_active = TRUE)",
                template.category_id
            )
            if not category_exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"分類 ID {template.category_id} 不存在或已停用"
                )

            # 驗證意圖是否存在（如果有指定）
            if template.intent_ids:
                for intent_id in template.intent_ids:
                    intent_exists = await conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM intents WHERE id = $1 AND is_enabled = TRUE)",
                        intent_id
                    )
                    if not intent_exists:
                        raise HTTPException(
                            status_code=404,
                            detail=f"意圖 ID {intent_id} 不存在或已停用"
                        )

            # 驗證 business_type
            if template.business_type and template.business_type not in ['full_service', 'property_management']:
                raise HTTPException(
                    status_code=400,
                    detail="business_type 必須是 full_service, property_management 或 null（通用）"
                )

            # 驗證群組是否存在（如果有指定）
            if template.group_id is not None:
                group_exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM platform_sop_groups WHERE id = $1 AND is_active = TRUE)",
                    template.group_id
                )
                if not group_exists:
                    raise HTTPException(
                        status_code=404,
                        detail=f"群組 ID {template.group_id} 不存在或已停用"
                    )

            # 插入新範本
            row = await conn.fetchrow("""
                INSERT INTO platform_sop_templates (
                    category_id, group_id, business_type, item_number, item_name, content,
                    priority, template_notes, customization_hint
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """,
                template.category_id, template.group_id, template.business_type, template.item_number,
                template.item_name, template.content,
                template.priority, template.template_notes, template.customization_hint
            )

            template_id = row["id"]

            # 插入意圖關聯
            if template.intent_ids:
                for intent_id in template.intent_ids:
                    await conn.execute("""
                        INSERT INTO platform_sop_template_intents (template_id, intent_id)
                        VALUES ($1, $2)
                    """, template_id, intent_id)

            # 查詢完整資訊（包含 intent_ids）
            final_row = await conn.fetchrow("""
                SELECT
                    t.*,
                    COALESCE(
                        (SELECT ARRAY_AGG(psti.intent_id ORDER BY psti.intent_id)
                         FROM platform_sop_template_intents psti
                         WHERE psti.template_id = t.id),
                        ARRAY[]::INTEGER[]
                    ) as intent_ids
                FROM platform_sop_templates t
                WHERE t.id = $1
            """, template_id)

            return {
                "id": final_row["id"],
                "category_id": final_row["category_id"],
                "business_type": final_row["business_type"],
                "item_number": final_row["item_number"],
                "item_name": final_row["item_name"],
                "content": final_row["content"],
                "intent_ids": final_row["intent_ids"],
                "priority": final_row["priority"],
                "template_notes": final_row["template_notes"],
                "customization_hint": final_row["customization_hint"],
                "is_active": final_row["is_active"],
                "created_at": final_row["created_at"].isoformat() if final_row["created_at"] else None,
                "updated_at": final_row["updated_at"].isoformat() if final_row["updated_at"] else None
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立範本失敗: {str(e)}")


@router.put("/templates/{template_id}", summary="更新平台 SOP 範本")
async def update_platform_sop_template(
    request: Request,
    template_id: int,
    template: PlatformSOPTemplateUpdate
):
    """
    更新平台 SOP 範本

    **權限**: 平台管理員
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            # 檢查範本是否存在
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM platform_sop_templates WHERE id = $1)",
                template_id
            )
            if not exists:
                raise HTTPException(status_code=404, detail=f"範本 ID {template_id} 不存在")

            # 驗證分類是否存在（如果有指定）
            if template.category_id:
                category_exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM platform_sop_categories WHERE id = $1 AND is_active = TRUE)",
                    template.category_id
                )
                if not category_exists:
                    raise HTTPException(status_code=404, detail=f"分類 ID {template.category_id} 不存在或已停用")

            # 驗證意圖是否存在（如果有指定）
            if template.intent_ids is not None:
                for intent_id in template.intent_ids:
                    intent_exists = await conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM intents WHERE id = $1 AND is_enabled = TRUE)",
                        intent_id
                    )
                    if not intent_exists:
                        raise HTTPException(status_code=404, detail=f"意圖 ID {intent_id} 不存在或已停用")

            # 驗證 business_type（如果有指定）
            if template.business_type and template.business_type not in ['full_service', 'property_management']:
                raise HTTPException(
                    status_code=400,
                    detail="business_type 必須是 full_service, property_management 或 null"
                )

            # 驗證群組是否存在（如果有指定）
            if template.group_id is not None:
                group_exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM platform_sop_groups WHERE id = $1 AND is_active = TRUE)",
                    template.group_id
                )
                if not group_exists:
                    raise HTTPException(
                        status_code=404,
                        detail=f"群組 ID {template.group_id} 不存在或已停用"
                    )

            # 建立更新欄位（包含 group_id）
            update_fields = []
            values = []
            param_count = 1

            for field in ["category_id", "group_id", "business_type", "item_number", "item_name", "content",
                          "priority", "template_notes", "customization_hint"]:
                value = getattr(template, field, None)
                if value is not None:
                    update_fields.append(f"{field} = ${param_count}")
                    values.append(value)
                    param_count += 1

            # 更新意圖關聯（如果有指定）
            if template.intent_ids is not None:
                # 刪除現有關聯
                await conn.execute(
                    "DELETE FROM platform_sop_template_intents WHERE template_id = $1",
                    template_id
                )

                # 新增新關聯
                for intent_id in template.intent_ids:
                    await conn.execute("""
                        INSERT INTO platform_sop_template_intents (template_id, intent_id)
                        VALUES ($1, $2)
                    """, template_id, intent_id)

            # 如果有欄位需要更新
            if update_fields:
                # 更新時間
                update_fields.append(f"updated_at = NOW()")

                # 執行更新
                values.append(template_id)
                query = f"""
                    UPDATE platform_sop_templates
                    SET {', '.join(update_fields)}
                    WHERE id = ${param_count}
                """
                await conn.execute(query, *values)

            # 查詢完整資料（包含意圖 ID 陣列）
            row = await conn.fetchrow("""
                SELECT
                    t.*,
                    COALESCE(
                        (SELECT ARRAY_AGG(psti.intent_id ORDER BY psti.intent_id)
                         FROM platform_sop_template_intents psti
                         WHERE psti.template_id = t.id),
                        ARRAY[]::INTEGER[]
                    ) as intent_ids
                FROM platform_sop_templates t
                WHERE t.id = $1
            """, template_id)

            return {
                "id": row["id"],
                "category_id": row["category_id"],
                "business_type": row["business_type"],
                "item_number": row["item_number"],
                "item_name": row["item_name"],
                "content": row["content"],
                "intent_ids": row["intent_ids"],
                "priority": row["priority"],
                "template_notes": row["template_notes"],
                "customization_hint": row["customization_hint"],
                "is_active": row["is_active"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新範本失敗: {str(e)}")


@router.delete("/templates/{template_id}", summary="刪除平台 SOP 範本")
async def delete_platform_sop_template(
    request: Request,
    template_id: int,
    permanent: bool = False
):
    """
    刪除平台 SOP 範本

    **Query Parameters**:
    - permanent: 是否永久刪除（預設 False，執行軟刪除）

    **權限**: 平台管理員
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            # 檢查範本是否存在
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM platform_sop_templates WHERE id = $1)",
                template_id
            )
            if not exists:
                raise HTTPException(status_code=404, detail=f"範本 ID {template_id} 不存在")

            if permanent:
                # 永久刪除範本
                await conn.execute(
                    "DELETE FROM platform_sop_templates WHERE id = $1",
                    template_id
                )
                return {"message": "範本已永久刪除", "template_id": template_id, "permanent": True}
            else:
                # 軟刪除範本
                await conn.execute(
                    "UPDATE platform_sop_templates SET is_active = FALSE, updated_at = NOW() WHERE id = $1",
                    template_id
                )
                return {"message": "範本已刪除", "template_id": template_id, "permanent": False}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除範本失敗: {str(e)}")


# ========================================
# 統計與分析 API
# ========================================

@router.get("/statistics/usage", summary="取得範本使用統計")
async def get_template_usage_statistics(
    request: Request
):
    """
    取得範本使用統計（哪些範本最常被業者複製使用）

    **權限**: 平台管理員
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM v_platform_sop_template_usage ORDER BY usage_percentage DESC")

            statistics = []
            for row in rows:
                statistics.append({
                    "template_id": row["template_id"],
                    "category_name": row["category_name"],
                    "business_type": row["business_type"],
                    "item_name": row["item_name"],
                    "copied_by_vendor_count": row["copied_by_vendor_count"],
                    "applicable_vendor_count": row["applicable_vendor_count"],
                    "usage_percentage": float(row["usage_percentage"]) if row["usage_percentage"] else 0.0
                })

            return {"statistics": statistics}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得統計失敗: {str(e)}")


@router.get("/templates/{template_id}/usage", summary="取得範本使用情況")
async def get_template_usage(
    request: Request,
    template_id: int
):
    """
    取得特定範本的使用情況（有哪些業者複製了此範本）

    **權限**: 平台管理員
    """
    try:
        async with request.app.state.db_pool.acquire() as conn:
            # 檢查範本是否存在
            template = await conn.fetchrow(
                "SELECT id, item_name, business_type FROM platform_sop_templates WHERE id = $1",
                template_id
            )
            if not template:
                raise HTTPException(status_code=404, detail=f"範本 ID {template_id} 不存在")

            # 取得使用此範本的業者
            rows = await conn.fetch("""
                SELECT
                    v.id AS vendor_id,
                    v.name AS vendor_name,
                    v.business_type AS vendor_business_type,
                    vsi.id AS vendor_sop_item_id,
                    vsi.created_at
                FROM vendors v
                LEFT JOIN vendor_sop_items vsi
                    ON v.id = vsi.vendor_id
                    AND vsi.template_id = $1
                    AND vsi.is_active = TRUE
                WHERE v.is_active = TRUE
                  AND (v.business_type = $2 OR $2 IS NULL)
                ORDER BY v.name
            """, template_id, template["business_type"])

            usage = []
            for row in rows:
                usage.append({
                    "vendor_id": row["vendor_id"],
                    "vendor_name": row["vendor_name"],
                    "vendor_business_type": row["vendor_business_type"],
                    "has_copied": row["vendor_sop_item_id"] is not None,
                    "copied_at": row["created_at"].isoformat() if row["created_at"] else None
                })

            return {
                "template_id": template["id"],
                "template_name": template["item_name"],
                "business_type": template["business_type"],
                "usage": usage
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得使用情況失敗: {str(e)}")


# ========================================
# Excel 匯入功能
# ========================================

@router.post("/import-excel", summary="匯入 Excel 替換 SOP 資料")
async def import_sop_from_excel(
    request: Request,
    file: UploadFile = File(...),
    replace_mode: str = "replace",  # replace=完全替換, merge=合併
    business_type: str = None  # null=通用範本, full_service=包租業, property_management=代管業
):
    """
    從 Excel 匯入 SOP 資料並替換現有資料

    **Excel 格式要求**:
    - 第1行: 標題（將被忽略）
    - 第2行: 欄位名稱
    - 列結構:
      - 列0: 分類
      - 列1: 說明（群組）
      - 列2: 序號
      - 列3: 應備欄位（項目名稱）
      - 列4: JGB範本（內容）
      - 列7: JGB系統操作備註

    **業種選擇**:
    - null 或 "universal": 通用範本（所有業種共用）
    - "full_service": 包租業範本
    - "property_management": 代管業範本

    **替換模式**:
    - replace: 刪除所有現有資料，完全替換
    - merge: 保留現有資料，僅更新或新增

    **權限**: 平台管理員
    """
    try:
        # 驗證 business_type 參數
        if business_type and business_type not in [None, "universal", "full_service", "property_management"]:
            raise HTTPException(status_code=400, detail=f"不支援的業種類型: {business_type}")

        # 轉換業種參數（"universal" -> NULL）
        db_business_type = None if business_type in [None, "universal"] else business_type

        # 讀取上傳的 Excel 檔案
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents), sheet_name='Sheet1', header=1)

        # 重命名欄位
        df.columns = ['分類', '說明', '序號', '應備欄位', 'JGB範本', '愛租屋管理制度', '空白欄', 'JGB系統操作備註']

        async with request.app.state.db_pool.acquire() as conn:
            # 開始交易
            async with conn.transaction():
                if replace_mode == "replace":
                    # 完全替換模式：只刪除指定 business_type 的範本資料
                    print(f"🗑️  刪除 business_type={db_business_type} 的 SOP 範本...")

                    # 先刪除範本的意圖映射（透過 template_id）
                    await conn.execute("""
                        DELETE FROM platform_sop_template_intents
                        WHERE template_id IN (
                            SELECT id FROM platform_sop_templates
                            WHERE business_type IS NOT DISTINCT FROM $1
                        )
                    """, db_business_type)

                    # 刪除指定 business_type 的範本
                    result = await conn.execute("""
                        DELETE FROM platform_sop_templates
                        WHERE business_type IS NOT DISTINCT FROM $1
                    """, db_business_type)

                    # 從結果中提取刪除的行數
                    deleted_count = int(result.split()[-1]) if result else 0
                    print(f"   已刪除 {deleted_count} 個範本")

                    # 注意：不刪除 categories 和 groups，因為它們可能被其他業種使用

                # 解析 Excel 並建立資料結構
                categories_created = {}
                groups_created = {}
                templates_created = 0

                current_category = None
                current_category_id = None
                current_group = None
                current_group_id = None

                for idx, row in df.iterrows():
                    # 處理分類
                    if pd.notna(row['分類']) and str(row['分類']).strip():
                        category_name = str(row['分類']).replace('\n', '').strip()

                        if category_name not in categories_created:
                            # 創建新分類
                            cat_id = await conn.fetchval("""
                                INSERT INTO platform_sop_categories
                                (category_name, description, display_order, is_active)
                                VALUES ($1, $2, $3, TRUE)
                                ON CONFLICT (category_name) DO UPDATE
                                SET description = EXCLUDED.description
                                RETURNING id
                            """, category_name, f"從 Excel 匯入: {category_name}", len(categories_created) + 1)

                            categories_created[category_name] = cat_id
                            current_category = category_name
                            current_category_id = cat_id
                            print(f"📁 創建分類: {category_name} (ID: {cat_id})")

                    # 處理群組（說明）
                    if pd.notna(row['說明']) and str(row['說明']).strip():
                        group_name = str(row['說明']).strip()
                        group_key = f"{current_category}::{group_name}"

                        if group_key not in groups_created and current_category_id:
                            # 創建新群組（如果已存在則更新）
                            grp_id = await conn.fetchval("""
                                INSERT INTO platform_sop_groups
                                (category_id, group_name, description, display_order)
                                VALUES ($1, $2, $3, $4)
                                ON CONFLICT (category_id, group_name) DO UPDATE
                                SET description = EXCLUDED.description,
                                    display_order = EXCLUDED.display_order
                                RETURNING id
                            """, current_category_id, group_name, "", len([k for k in groups_created if k.startswith(f"{current_category}::")]) + 1)

                            groups_created[group_key] = grp_id
                            current_group = group_name
                            current_group_id = grp_id
                            print(f"  📂 創建群組: {group_name} (ID: {grp_id})")

                    # 處理範本項目
                    if pd.notna(row['序號']) and current_category_id:
                        item_number = int(row['序號']) if not pd.isna(row['序號']) else 0
                        item_name = str(row['應備欄位']).strip() if pd.notna(row['應備欄位']) else f"項目 {item_number}"
                        content = str(row['JGB範本']).strip() if pd.notna(row['JGB範本']) else ""
                        system_note = str(row['JGB系統操作備註']).strip() if pd.notna(row['JGB系統操作備註']) else None

                        # 創建範本
                        template_id = await conn.fetchval("""
                            INSERT INTO platform_sop_templates
                            (category_id, group_id, business_type, item_number, item_name, content,
                             template_notes, priority, is_active)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, 50, TRUE)
                            RETURNING id
                        """, current_category_id, current_group_id, db_business_type, item_number, item_name, content, system_note)

                        templates_created += 1

                        if templates_created % 10 == 0:
                            print(f"  ✅ 已創建 {templates_created} 個範本...")

                print(f"\n✅ 匯入完成！")
                print(f"   • 分類: {len(categories_created)} 個")
                print(f"   • 群組: {len(groups_created)} 個")
                print(f"   • 範本: {templates_created} 個")

                return {
                    "success": True,
                    "message": "Excel 匯入成功",
                    "statistics": {
                        "categories_created": len(categories_created),
                        "groups_created": len(groups_created),
                        "templates_created": templates_created
                    }
                }

    except pd.errors.ParserError as e:
        raise HTTPException(status_code=400, detail=f"Excel 格式錯誤: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"匯入失敗: {str(e)}")
