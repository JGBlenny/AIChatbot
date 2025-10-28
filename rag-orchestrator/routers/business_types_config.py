"""
業態類型配置 API 路由
管理業者的業態類型選項（系統商、包租型、代管型等）
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import psycopg2
import psycopg2.extras
from services.db_utils import get_db_config

router = APIRouter()


class BusinessTypeCreate(BaseModel):
    """業態類型新增請求"""
    type_value: str = Field(..., min_length=1, max_length=50, description="業態類型值（如：'system_provider'）")
    display_name: str = Field(..., min_length=1, max_length=100, description="顯示名稱（如：'系統商'）")
    description: Optional[str] = Field(None, description="說明")
    display_order: int = Field(0, description="顯示順序")
    icon: Optional[str] = Field(None, max_length=50, description="圖標 emoji")
    color: Optional[str] = Field(None, max_length=20, description="顏色標籤（如：blue, green）")
    tone_prompt: Optional[str] = Field(None, description="語氣 Prompt")


class BusinessTypeUpdate(BaseModel):
    """業態類型更新請求"""
    display_name: Optional[str] = Field(None, max_length=100, description="顯示名稱")
    description: Optional[str] = Field(None, description="說明")
    display_order: Optional[int] = Field(None, description="顯示順序")
    icon: Optional[str] = Field(None, max_length=50, description="圖標 emoji")
    color: Optional[str] = Field(None, max_length=20, description="顏色標籤")
    is_active: Optional[bool] = Field(None, description="是否啟用")
    tone_prompt: Optional[str] = Field(None, description="語氣 Prompt")


@router.get("/business-types-config")
async def get_all_business_types(is_active: Optional[bool] = True):
    """
    取得所有業態類型配置

    Args:
        is_active: 過濾是否啟用，預設只返回啟用的

    Returns:
        業態類型列表（依 display_order 排序）
    """
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            where_clause = "is_active = TRUE" if is_active else "TRUE"

            query = f"""
                SELECT
                    id,
                    type_value,
                    display_name,
                    description,
                    display_order,
                    icon,
                    color,
                    tone_prompt,
                    is_active,
                    created_at,
                    updated_at
                FROM business_types_config
                WHERE {where_clause}
                ORDER BY id
            """

            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()

            return {
                "business_types": [dict(row) for row in rows],
                "total": len(rows)
            }

        finally:
            conn.close()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得業態類型配置失敗: {str(e)}"
        )


@router.get("/business-types-config/{type_value}")
async def get_business_type(type_value: str):
    """取得特定業態類型配置"""
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT
                    id,
                    type_value,
                    display_name,
                    description,
                    display_order,
                    icon,
                    color,
                    tone_prompt,
                    is_active,
                    created_at,
                    updated_at
                FROM business_types_config
                WHERE type_value = %s
            """, (type_value,))

            row = cursor.fetchone()
            cursor.close()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到業態類型: {type_value}"
                )

            return dict(row)

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得業態類型詳情失敗: {str(e)}"
        )


@router.post("/business-types-config")
async def create_business_type(request: BusinessTypeCreate):
    """
    新增業態類型配置
    """
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 檢查是否已存在
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM business_types_config WHERE type_value = %s
                )
            """, (request.type_value,))

            exists = cursor.fetchone()['exists']

            if exists:
                cursor.close()
                raise HTTPException(
                    status_code=409,
                    detail=f"業態類型已存在: {request.type_value}"
                )

            # 插入新配置
            cursor.execute("""
                INSERT INTO business_types_config (
                    type_value,
                    display_name,
                    description,
                    display_order,
                    icon,
                    color,
                    tone_prompt
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                request.type_value,
                request.display_name,
                request.description,
                request.display_order,
                request.icon,
                request.color,
                request.tone_prompt
            ))

            new_id = cursor.fetchone()['id']
            conn.commit()
            cursor.close()

            return {
                "message": "業態類型已新增",
                "id": new_id,
                "type_value": request.type_value
            }

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"新增業態類型失敗: {str(e)}"
        )


@router.put("/business-types-config/{type_value}")
async def update_business_type(
    type_value: str,
    request: BusinessTypeUpdate
):
    """更新業態類型配置"""
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor()

            # 檢查是否存在
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM business_types_config WHERE type_value = %s
                )
            """, (type_value,))

            exists = cursor.fetchone()[0]

            if not exists:
                cursor.close()
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到業態類型: {type_value}"
                )

            # 構建更新語句
            updates = []
            params = []

            if request.display_name is not None:
                updates.append("display_name = %s")
                params.append(request.display_name)

            if request.description is not None:
                updates.append("description = %s")
                params.append(request.description)

            if request.display_order is not None:
                updates.append("display_order = %s")
                params.append(request.display_order)

            if request.icon is not None:
                updates.append("icon = %s")
                params.append(request.icon)

            if request.color is not None:
                updates.append("color = %s")
                params.append(request.color)

            if request.is_active is not None:
                updates.append("is_active = %s")
                params.append(request.is_active)

            if request.tone_prompt is not None:
                updates.append("tone_prompt = %s")
                params.append(request.tone_prompt)

            if not updates:
                cursor.close()
                return {"message": "沒有要更新的欄位"}

            # 加入更新時間
            updates.append("updated_at = CURRENT_TIMESTAMP")

            # 執行更新
            query = f"""
                UPDATE business_types_config
                SET {', '.join(updates)}
                WHERE type_value = %s
            """
            params.append(type_value)

            cursor.execute(query, params)
            conn.commit()
            cursor.close()

            return {
                "message": "業態類型已更新",
                "type_value": type_value
            }

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新業態類型失敗: {str(e)}"
        )


@router.delete("/business-types-config/{type_value}")
async def delete_business_type(type_value: str):
    """
    刪除業態類型（軟刪除：設為 is_active = FALSE）
    """
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor()

            # 檢查是否存在
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM business_types_config WHERE type_value = %s
                )
            """, (type_value,))

            exists = cursor.fetchone()[0]

            if not exists:
                cursor.close()
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到業態類型: {type_value}"
                )

            # 檢查是否有業者正在使用此業態類型
            cursor.execute("""
                SELECT COUNT(*) FROM vendors
                WHERE %s = ANY(business_types) AND is_active = TRUE
            """, (type_value,))

            usage_count = cursor.fetchone()[0]

            if usage_count > 0:
                cursor.close()
                raise HTTPException(
                    status_code=400,
                    detail=f"無法停用：目前有 {usage_count} 個業者正在使用此業態類型"
                )

            # 軟刪除（設為不啟用）
            cursor.execute("""
                UPDATE business_types_config
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE type_value = %s
            """, (type_value,))

            conn.commit()
            cursor.close()

            return {
                "message": "業態類型已停用",
                "type_value": type_value
            }

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"刪除業態類型失敗: {str(e)}"
        )


@router.get("/business-types-config/{type_value}/usage")
async def get_business_type_usage(type_value: str):
    """
    查詢業態類型的使用情況

    Returns:
        使用此業態類型的業者列表
    """
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT
                    id,
                    code,
                    name,
                    short_name,
                    business_types,
                    is_active
                FROM vendors
                WHERE %s = ANY(business_types)
                ORDER BY name
            """, (type_value,))

            rows = cursor.fetchall()
            cursor.close()

            return {
                "type_value": type_value,
                "usage_count": len(rows),
                "vendors": [dict(row) for row in rows]
            }

        finally:
            conn.close()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"查詢使用情況失敗: {str(e)}"
        )


@router.post("/business-types-config/clear-tone-cache")
async def clear_tone_cache():
    """
    清空業態語氣配置快取

    當管理員更新語氣配置後，可以手動清空快取讓變更立即生效
    """
    try:
        from services.llm_answer_optimizer import LLMAnswerOptimizer
        LLMAnswerOptimizer.clear_tone_cache()

        return {
            "message": "語氣配置快取已清空",
            "note": "下次 LLM 優化器使用時將從資料庫重新載入配置"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"清空快取失敗: {str(e)}"
        )
