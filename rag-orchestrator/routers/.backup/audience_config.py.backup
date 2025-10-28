"""
受眾配置 API 路由
管理知識庫的受眾（audience）選項及其與業務範圍的映射
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import psycopg2
import psycopg2.extras
from services.db_utils import get_db_config
from services.business_scope_utils import clear_audience_cache

router = APIRouter()


class AudienceConfigCreate(BaseModel):
    """受眾配置新增請求"""
    audience_value: str = Field(..., min_length=1, max_length=50, description="受眾值（如：'租客', '管理師'）")
    display_name: str = Field(..., min_length=1, max_length=100, description="顯示名稱")
    business_scope: str = Field(..., description="業務範圍：external, internal, both")
    description: Optional[str] = Field(None, description="說明")
    display_order: int = Field(0, description="顯示順序")


class AudienceConfigUpdate(BaseModel):
    """受眾配置更新請求"""
    display_name: Optional[str] = Field(None, max_length=100, description="顯示名稱")
    business_scope: Optional[str] = Field(None, description="業務範圍：external, internal, both")
    description: Optional[str] = Field(None, description="說明")
    display_order: Optional[int] = Field(None, description="顯示順序")
    is_active: Optional[bool] = Field(None, description="是否啟用")


@router.get("/audience-config")
async def get_all_audience_configs(
    business_scope: Optional[str] = None,
    is_active: Optional[bool] = True
):
    """
    取得所有受眾配置

    Args:
        business_scope: 過濾業務範圍（external/internal/both），不指定則返回全部
        is_active: 過濾是否啟用，預設只返回啟用的

    Returns:
        受眾配置列表（依 display_order 排序）
    """
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 構建查詢條件
            where_clauses = []
            params = []

            if business_scope:
                where_clauses.append("(business_scope = %s OR business_scope = 'both')")
                params.append(business_scope)

            if is_active is not None:
                where_clauses.append("is_active = %s")
                params.append(is_active)

            where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

            query = f"""
                SELECT
                    id,
                    audience_value,
                    display_name,
                    business_scope,
                    description,
                    display_order,
                    is_active,
                    created_at,
                    updated_at
                FROM audience_config
                WHERE {where_sql}
                ORDER BY display_order, id
            """

            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()

            return {
                "audiences": [dict(row) for row in rows],
                "total": len(rows)
            }

        finally:
            conn.close()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得受眾配置列表失敗: {str(e)}"
        )


@router.get("/audience-config/grouped")
async def get_audience_configs_grouped(is_active: Optional[bool] = True):
    """
    取得分組的受眾配置（依業務範圍分組）

    Args:
        is_active: 過濾是否啟用，預設只返回啟用的

    Returns:
        依業務範圍分組的受眾配置
        {
            "external": [...],
            "internal": [...],
            "both": [...]
        }
    """
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            where_clause = "is_active = TRUE" if is_active else "TRUE"

            query = f"""
                SELECT
                    id,
                    audience_value,
                    display_name,
                    business_scope,
                    description,
                    display_order,
                    is_active
                FROM audience_config
                WHERE {where_clause}
                ORDER BY
                    CASE business_scope
                        WHEN 'external' THEN 1
                        WHEN 'both' THEN 2
                        WHEN 'internal' THEN 3
                    END,
                    display_order,
                    id
            """

            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()

            # 分組
            grouped = {
                'external': [],
                'internal': [],
                'both': []
            }

            for row in rows:
                scope = row['business_scope']
                grouped[scope].append(dict(row))

            return grouped

        finally:
            conn.close()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得分組受眾配置失敗: {str(e)}"
        )


@router.get("/audience-config/{audience_value}")
async def get_audience_config(audience_value: str):
    """取得特定受眾配置"""
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT
                    id,
                    audience_value,
                    display_name,
                    business_scope,
                    description,
                    display_order,
                    is_active,
                    created_at,
                    updated_at
                FROM audience_config
                WHERE audience_value = %s
            """, (audience_value,))

            row = cursor.fetchone()
            cursor.close()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到受眾配置: {audience_value}"
                )

            return dict(row)

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得受眾配置詳情失敗: {str(e)}"
        )


@router.post("/audience-config")
async def create_audience_config(request: AudienceConfigCreate):
    """
    新增受眾配置

    注意：新增後會清除 audience 映射緩存
    """
    # 驗證 business_scope
    if request.business_scope not in ['external', 'internal', 'both']:
        raise HTTPException(
            status_code=400,
            detail="business_scope 必須是 'external', 'internal', 或 'both'"
        )

    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 檢查是否已存在
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM audience_config WHERE audience_value = %s
                )
            """, (request.audience_value,))

            exists = cursor.fetchone()['exists']

            if exists:
                cursor.close()
                raise HTTPException(
                    status_code=409,
                    detail=f"受眾配置已存在: {request.audience_value}"
                )

            # 插入新配置
            cursor.execute("""
                INSERT INTO audience_config (
                    audience_value,
                    display_name,
                    business_scope,
                    description,
                    display_order
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                request.audience_value,
                request.display_name,
                request.business_scope,
                request.description,
                request.display_order
            ))

            new_id = cursor.fetchone()['id']
            conn.commit()
            cursor.close()

            # 清除緩存
            clear_audience_cache()

            return {
                "message": "受眾配置已新增",
                "id": new_id,
                "audience_value": request.audience_value
            }

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"新增受眾配置失敗: {str(e)}"
        )


@router.put("/audience-config/{audience_value}")
async def update_audience_config(
    audience_value: str,
    request: AudienceConfigUpdate
):
    """
    更新受眾配置

    注意：更新後會清除 audience 映射緩存
    """
    # 驗證 business_scope
    if request.business_scope and request.business_scope not in ['external', 'internal', 'both']:
        raise HTTPException(
            status_code=400,
            detail="business_scope 必須是 'external', 'internal', 或 'both'"
        )

    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor()

            # 檢查是否存在
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM audience_config WHERE audience_value = %s
                )
            """, (audience_value,))

            exists = cursor.fetchone()[0]

            if not exists:
                cursor.close()
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到受眾配置: {audience_value}"
                )

            # 構建更新語句
            updates = []
            params = []

            if request.display_name is not None:
                updates.append("display_name = %s")
                params.append(request.display_name)

            if request.business_scope is not None:
                updates.append("business_scope = %s")
                params.append(request.business_scope)

            if request.description is not None:
                updates.append("description = %s")
                params.append(request.description)

            if request.display_order is not None:
                updates.append("display_order = %s")
                params.append(request.display_order)

            if request.is_active is not None:
                updates.append("is_active = %s")
                params.append(request.is_active)

            if not updates:
                cursor.close()
                return {"message": "沒有要更新的欄位"}

            # 加入更新時間
            updates.append("updated_at = CURRENT_TIMESTAMP")

            # 執行更新
            query = f"""
                UPDATE audience_config
                SET {', '.join(updates)}
                WHERE audience_value = %s
            """
            params.append(audience_value)

            cursor.execute(query, params)
            conn.commit()
            cursor.close()

            # 清除緩存
            clear_audience_cache()

            return {
                "message": "受眾配置已更新（緩存已清除）",
                "audience_value": audience_value
            }

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新受眾配置失敗: {str(e)}"
        )


@router.delete("/audience-config/{audience_value}")
async def delete_audience_config(audience_value: str):
    """
    刪除受眾配置（軟刪除：設為 is_active = FALSE）

    注意：刪除後會清除 audience 映射緩存
    """
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor()

            # 檢查是否存在
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM audience_config WHERE audience_value = %s
                )
            """, (audience_value,))

            exists = cursor.fetchone()[0]

            if not exists:
                cursor.close()
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到受眾配置: {audience_value}"
                )

            # 軟刪除（設為不啟用）
            cursor.execute("""
                UPDATE audience_config
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE audience_value = %s
            """, (audience_value,))

            conn.commit()
            cursor.close()

            # 清除緩存
            clear_audience_cache()

            return {
                "message": "受眾配置已停用（緩存已清除）",
                "audience_value": audience_value
            }

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"刪除受眾配置失敗: {str(e)}"
        )


@router.post("/audience-config/clear-cache")
async def clear_cache():
    """
    手動清除 audience 映射緩存

    在大量更新 audience_config 後，可以呼叫此端點強制清除緩存
    """
    try:
        clear_audience_cache()
        return {
            "message": "Audience 映射緩存已清除",
            "note": "下次查詢時會自動從數據庫重新載入"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"清除緩存失敗: {str(e)}"
        )
