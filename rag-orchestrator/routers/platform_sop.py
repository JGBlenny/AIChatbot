"""
Platform SOP 管理 API
用途：平台管理員管理 SOP 範本（按業種分類的參考範本）
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

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


class PlatformSOPTemplateCreate(BaseModel):
    """建立平台 SOP 範本"""
    category_id: int = Field(..., description="所屬分類ID")
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

            # 插入新範本
            row = await conn.fetchrow("""
                INSERT INTO platform_sop_templates (
                    category_id, business_type, item_number, item_name, content,
                    priority, template_notes, customization_hint
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """,
                template.category_id, template.business_type, template.item_number,
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

            # 建立更新欄位（移除 related_intent_id，改用多意圖關聯表）
            update_fields = []
            values = []
            param_count = 1

            for field in ["category_id", "business_type", "item_number", "item_name", "content",
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
    template_id: int
):
    """
    軟刪除平台 SOP 範本（設置 is_active = FALSE）

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

            # 軟刪除範本
            await conn.execute(
                "UPDATE platform_sop_templates SET is_active = FALSE, updated_at = NOW() WHERE id = $1",
                template_id
            )

            return {"message": "範本已刪除", "template_id": template_id}

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
