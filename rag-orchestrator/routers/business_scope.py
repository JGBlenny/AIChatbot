"""
業務範圍配置 API 路由
管理意圖建議的業務範圍配置
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import psycopg2
import psycopg2.extras
import os

router = APIRouter()


class BusinessScopeUpdate(BaseModel):
    """業務範圍更新請求"""
    display_name: Optional[str] = Field(None, description="顯示名稱")
    business_description: Optional[str] = Field(None, description="業務描述")
    example_questions: Optional[List[str]] = Field(None, description="範例問題")
    example_intents: Optional[List[str]] = Field(None, description="範例意圖")
    relevance_prompt: Optional[str] = Field(None, description="OpenAI判斷prompt")
    updated_by: str = Field(..., description="更新人員")


class BusinessScopeSwitch(BaseModel):
    """業務範圍切換請求"""
    scope_name: str = Field(..., description="要啟用的業務範圍")
    updated_by: str = Field(..., description="操作人員")


def get_db_config():
    """取得資料庫配置"""
    return {
        'host': os.getenv('DB_HOST', 'postgres'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'user': os.getenv('DB_USER', 'aichatbot'),
        'password': os.getenv('DB_PASSWORD', 'aichatbot_password'),
        'database': os.getenv('DB_NAME', 'aichatbot_admin')
    }


@router.get("/business-scope")
async def get_all_business_scopes(req: Request):
    """取得所有業務範圍配置"""
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT
                    id,
                    scope_name,
                    scope_type,
                    display_name,
                    business_description,
                    example_questions,
                    example_intents,
                    is_active,
                    updated_at,
                    updated_by
                FROM business_scope_config
                ORDER BY scope_type
            """)

            rows = cursor.fetchall()
            cursor.close()

            return {
                "scopes": [dict(row) for row in rows],
                "total": len(rows)
            }

        finally:
            conn.close()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得業務範圍列表失敗: {str(e)}"
        )


@router.get("/business-scope/active")
async def get_active_business_scope(req: Request):
    """取得當前啟用的業務範圍配置"""
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT
                    id,
                    scope_name,
                    scope_type,
                    display_name,
                    business_description,
                    example_questions,
                    example_intents,
                    relevance_prompt,
                    is_active,
                    updated_at,
                    updated_by
                FROM business_scope_config
                WHERE is_active = true
                LIMIT 1
            """)

            row = cursor.fetchone()
            cursor.close()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="找不到啟用的業務範圍配置"
                )

            return dict(row)

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得啟用業務範圍失敗: {str(e)}"
        )


@router.get("/business-scope/{scope_name}")
async def get_business_scope(scope_name: str, req: Request):
    """取得特定業務範圍配置"""
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT
                    id,
                    scope_name,
                    scope_type,
                    display_name,
                    business_description,
                    example_questions,
                    example_intents,
                    relevance_prompt,
                    is_active,
                    updated_at,
                    updated_by
                FROM business_scope_config
                WHERE scope_name = %s
            """, (scope_name,))

            row = cursor.fetchone()
            cursor.close()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到業務範圍: {scope_name}"
                )

            return dict(row)

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得業務範圍詳情失敗: {str(e)}"
        )


@router.put("/business-scope/{scope_name}")
async def update_business_scope(
    scope_name: str,
    request: BusinessScopeUpdate,
    req: Request
):
    """更新業務範圍配置"""
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor()

            # 檢查業務範圍是否存在
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM business_scope_config WHERE scope_name = %s
                )
            """, (scope_name,))

            exists = cursor.fetchone()[0]

            if not exists:
                cursor.close()
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到業務範圍: {scope_name}"
                )

            # 構建更新語句
            updates = []
            params = []
            param_count = 0

            if request.display_name is not None:
                param_count += 1
                updates.append(f"display_name = ${param_count}")
                params.append(request.display_name)

            if request.business_description is not None:
                param_count += 1
                updates.append(f"business_description = ${param_count}")
                params.append(request.business_description)

            if request.example_questions is not None:
                param_count += 1
                updates.append(f"example_questions = ${param_count}")
                params.append(request.example_questions)

            if request.example_intents is not None:
                param_count += 1
                updates.append(f"example_intents = ${param_count}")
                params.append(request.example_intents)

            if request.relevance_prompt is not None:
                param_count += 1
                updates.append(f"relevance_prompt = ${param_count}")
                params.append(request.relevance_prompt)

            # 加入更新人員
            param_count += 1
            updates.append(f"updated_by = ${param_count}")
            params.append(request.updated_by)

            param_count += 1
            updates.append(f"updated_at = CURRENT_TIMESTAMP")

            if not updates:
                cursor.close()
                return {"message": "沒有要更新的欄位"}

            # 執行更新
            param_count += 1
            query = f"""
                UPDATE business_scope_config
                SET {', '.join(updates)}
                WHERE scope_name = ${param_count}
            """
            params.append(scope_name)

            # 轉換 $ 參數為 % 參數（psycopg2）
            query_psycopg = query
            for i in range(param_count, 0, -1):
                query_psycopg = query_psycopg.replace(f"${i}", "%s")

            cursor.execute(query_psycopg, params)
            conn.commit()
            cursor.close()

            # 如果更新的是當前啟用的業務範圍，重新載入建議引擎
            suggestion_engine = req.app.state.suggestion_engine
            cursor2 = conn.cursor()
            cursor2.execute("""
                SELECT is_active FROM business_scope_config WHERE scope_name = %s
            """, (scope_name,))
            is_active = cursor2.fetchone()[0]
            cursor2.close()

            if is_active:
                suggestion_engine.reload_business_scope()

            return {
                "message": "業務範圍配置已更新",
                "scope_name": scope_name
            }

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新業務範圍失敗: {str(e)}"
        )


@router.post("/business-scope/switch")
async def switch_business_scope(request: BusinessScopeSwitch, req: Request):
    """
    切換業務範圍

    將指定的業務範圍設為啟用，其他的設為停用
    """
    try:
        conn = psycopg2.connect(**get_db_config())

        try:
            cursor = conn.cursor()

            # 檢查目標業務範圍是否存在
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM business_scope_config WHERE scope_name = %s
                )
            """, (request.scope_name,))

            exists = cursor.fetchone()[0]

            if not exists:
                cursor.close()
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到業務範圍: {request.scope_name}"
                )

            # 停用所有業務範圍
            cursor.execute("""
                UPDATE business_scope_config
                SET is_active = false,
                    updated_by = %s,
                    updated_at = CURRENT_TIMESTAMP
            """, (request.updated_by,))

            # 啟用指定業務範圍
            cursor.execute("""
                UPDATE business_scope_config
                SET is_active = true,
                    updated_by = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE scope_name = %s
            """, (request.updated_by, request.scope_name))

            conn.commit()
            cursor.close()

            # 重新載入建議引擎的業務範圍配置
            suggestion_engine = req.app.state.suggestion_engine
            suggestion_engine.reload_business_scope()

            return {
                "message": f"已切換到業務範圍: {request.scope_name}",
                "active_scope": request.scope_name
            }

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"切換業務範圍失敗: {str(e)}"
        )
