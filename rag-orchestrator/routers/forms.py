"""
表單管理 API
提供表單的 CRUD 操作
"""
import json
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

router = APIRouter()


# ============================================================
# Pydantic Models
# ============================================================

class FormField(BaseModel):
    """表單欄位定義"""
    field_name: str = Field(..., description="欄位名稱（英文）")
    field_label: str = Field(..., description="欄位標籤（中文）")
    field_type: str = Field(..., description="欄位類型：text, textarea, select, number, email, date")
    prompt: str = Field(..., description="提示訊息")
    required: bool = Field(True, description="是否必填")
    validation_type: Optional[str] = Field(None, description="驗證類型：taiwan_name, taiwan_id, phone, email, address, none")
    max_length: Optional[int] = Field(None, description="最大長度")
    min: Optional[int] = Field(None, description="最小值（數字類型）")
    max: Optional[int] = Field(None, description="最大值（數字類型）")
    options: Optional[List[str]] = Field(None, description="選項（select 類型必填）")


class FormSchemaCreate(BaseModel):
    """建立表單的請求"""
    form_id: str = Field(..., description="表單ID（英文，唯一）")
    form_name: str = Field(..., description="表單名稱")
    description: Optional[str] = Field(None, description="表單描述")
    default_intro: Optional[str] = Field(None, description="預設引導語")
    fields: List[FormField] = Field(..., description="表單欄位")
    vendor_id: Optional[int] = Field(None, description="業者ID（NULL=全局）")
    is_active: bool = Field(True, description="是否啟用")


class FormSchemaUpdate(BaseModel):
    """更新表單的請求"""
    form_name: Optional[str] = Field(None, description="表單名稱")
    description: Optional[str] = Field(None, description="表單描述")
    default_intro: Optional[str] = Field(None, description="預設引導語")
    fields: Optional[List[FormField]] = Field(None, description="表單欄位")
    is_active: Optional[bool] = Field(None, description="是否啟用")


class FormSchemaResponse(BaseModel):
    """表單回應"""
    id: int
    form_id: str
    form_name: str
    description: Optional[str]
    default_intro: Optional[str]
    fields: List[Dict[str, Any]]
    vendor_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ============================================================
# API Endpoints
# ============================================================

@router.get("/forms", response_model=List[FormSchemaResponse])
async def list_forms(
    request: Request,
    vendor_id: Optional[int] = None,
    is_active: Optional[bool] = None
):
    """
    取得所有表單列表

    - **vendor_id**: 過濾特定業者的表單（不提供則顯示所有）
    - **is_active**: 過濾是否啟用（不提供則顯示所有）
    """
    try:
        db_pool = request.app.state.db_pool

        # 建立查詢條件
        conditions = []
        params = []
        param_count = 0

        if vendor_id is not None:
            param_count += 1
            conditions.append(f"(vendor_id = ${param_count} OR vendor_id IS NULL)")
            params.append(vendor_id)

        if is_active is not None:
            param_count += 1
            conditions.append(f"is_active = ${param_count}")
            params.append(is_active)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT
                id,
                form_id,
                form_name,
                description,
                default_intro,
                fields,
                vendor_id,
                is_active,
                created_at,
                updated_at
            FROM form_schemas
            WHERE {where_clause}
            ORDER BY
                vendor_id NULLS LAST,
                created_at DESC
        """

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        # Parse fields from JSON string to list if needed
        results = []
        for row in rows:
            row_dict = dict(row)
            if isinstance(row_dict.get('fields'), str):
                row_dict['fields'] = json.loads(row_dict['fields'])
            results.append(row_dict)

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢表單失敗: {str(e)}")


@router.get("/forms/{form_id}", response_model=FormSchemaResponse)
async def get_form(request: Request, form_id: str):
    """
    取得單一表單詳細資訊

    - **form_id**: 表單ID
    """
    try:
        db_pool = request.app.state.db_pool

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    id,
                    form_id,
                    form_name,
                    description,
                    default_intro,
                    fields,
                    vendor_id,
                    is_active,
                    created_at,
                    updated_at
                FROM form_schemas
                WHERE form_id = $1
            """, form_id)

        if not row:
            raise HTTPException(status_code=404, detail=f"找不到表單: {form_id}")

        # Parse fields from JSON string to list if needed
        row_dict = dict(row)
        if isinstance(row_dict.get('fields'), str):
            row_dict['fields'] = json.loads(row_dict['fields'])

        return row_dict

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢表單失敗: {str(e)}")


@router.post("/forms", response_model=FormSchemaResponse, status_code=201)
async def create_form(request: Request, form_data: FormSchemaCreate):
    """
    建立新表單

    - **form_id**: 表單ID（唯一，不可重複）
    - **form_name**: 表單名稱
    - **fields**: 表單欄位列表
    """
    try:
        db_pool = request.app.state.db_pool

        # 驗證 form_id 不重複
        async with db_pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id FROM form_schemas WHERE form_id = $1",
                form_data.form_id
            )

            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"表單ID已存在: {form_data.form_id}"
                )

            # 驗證欄位
            _validate_fields(form_data.fields)

            # 轉換欄位為 JSONB 格式
            fields_json = json.dumps([field.dict(exclude_none=True) for field in form_data.fields])

            # 插入表單
            row = await conn.fetchrow("""
                INSERT INTO form_schemas (
                    form_id,
                    form_name,
                    description,
                    default_intro,
                    fields,
                    vendor_id,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, NOW(), NOW())
                RETURNING
                    id,
                    form_id,
                    form_name,
                    description,
                    default_intro,
                    fields,
                    vendor_id,
                    is_active,
                    created_at,
                    updated_at
            """,
                form_data.form_id,
                form_data.form_name,
                form_data.description,
                form_data.default_intro,
                fields_json,
                form_data.vendor_id,
                form_data.is_active
            )

        # Parse fields from JSON string to list if needed
        row_dict = dict(row)
        if isinstance(row_dict.get('fields'), str):
            row_dict['fields'] = json.loads(row_dict['fields'])

        return row_dict

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立表單失敗: {str(e)}")


@router.put("/forms/{form_id}", response_model=FormSchemaResponse)
async def update_form(request: Request, form_id: str, form_data: FormSchemaUpdate):
    """
    更新表單

    - **form_id**: 表單ID
    - 只需提供要更新的欄位
    """
    try:
        db_pool = request.app.state.db_pool

        # 建立更新語句
        updates = []
        params = []
        param_count = 0

        if form_data.form_name is not None:
            param_count += 1
            updates.append(f"form_name = ${param_count}")
            params.append(form_data.form_name)

        if form_data.description is not None:
            param_count += 1
            updates.append(f"description = ${param_count}")
            params.append(form_data.description)

        if form_data.default_intro is not None:
            param_count += 1
            updates.append(f"default_intro = ${param_count}")
            params.append(form_data.default_intro)

        if form_data.fields is not None:
            _validate_fields(form_data.fields)
            fields_json = json.dumps([field.dict(exclude_none=True) for field in form_data.fields])
            param_count += 1
            updates.append(f"fields = ${param_count}::jsonb")
            params.append(fields_json)

        if form_data.is_active is not None:
            param_count += 1
            updates.append(f"is_active = ${param_count}")
            params.append(form_data.is_active)

        if not updates:
            raise HTTPException(status_code=400, detail="沒有提供要更新的欄位")

        updates.append("updated_at = NOW()")

        param_count += 1
        params.append(form_id)

        query = f"""
            UPDATE form_schemas
            SET {', '.join(updates)}
            WHERE form_id = ${param_count}
            RETURNING
                id,
                form_id,
                form_name,
                description,
                default_intro,
                fields,
                vendor_id,
                is_active,
                created_at,
                updated_at
        """

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        if not row:
            raise HTTPException(status_code=404, detail=f"找不到表單: {form_id}")

        # Parse fields from JSON string to list if needed
        row_dict = dict(row)
        if isinstance(row_dict.get('fields'), str):
            row_dict['fields'] = json.loads(row_dict['fields'])

        return row_dict

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新表單失敗: {str(e)}")


@router.delete("/forms/{form_id}")
async def delete_form(request: Request, form_id: str):
    """
    刪除表單

    - **form_id**: 表單ID

    ⚠️ 注意：如果有知識關聯到此表單，刪除會失敗（需先解除關聯）
    """
    try:
        db_pool = request.app.state.db_pool

        async with db_pool.acquire() as conn:
            # 檢查是否有知識關聯
            knowledge_count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM knowledge_base
                WHERE form_id = $1
            """, form_id)

            if knowledge_count > 0:
                raise HTTPException(
                    status_code=409,
                    detail=f"無法刪除：有 {knowledge_count} 筆知識關聯到此表單，請先解除關聯"
                )

            # 刪除表單
            result = await conn.execute("""
                DELETE FROM form_schemas
                WHERE form_id = $1
            """, form_id)

            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail=f"找不到表單: {form_id}")

        return {"message": f"表單 {form_id} 已刪除"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除表單失敗: {str(e)}")


@router.get("/forms/{form_id}/related-knowledge")
async def get_related_knowledge(request: Request, form_id: str):
    """
    查詢關聯到此表單的知識

    - **form_id**: 表單ID
    """
    try:
        db_pool = request.app.state.db_pool

        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    id,
                    question_summary,
                    form_intro,
                    vendor_id,
                    scope,
                    is_active
                FROM knowledge_base
                WHERE form_id = $1
                ORDER BY priority DESC, created_at DESC
            """, form_id)

        return [dict(row) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢關聯知識失敗: {str(e)}")


class FormSubmissionUpdate(BaseModel):
    """更新表單提交的請求"""
    status: Optional[str] = Field(None, description="狀態：pending, processing, completed, rejected")
    notes: Optional[str] = Field(None, description="備註說明")
    updated_by: Optional[str] = Field(None, description="更新者")


@router.get("/form-submissions")
async def list_form_submissions(
    request: Request,
    form_id: Optional[str] = None,
    vendor_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    查詢表單提交記錄

    - **form_id**: 過濾特定表單
    - **vendor_id**: 過濾特定業者
    - **limit**: 每頁筆數 (預設 50)
    - **offset**: 偏移量 (預設 0)
    """
    try:
        db_pool = request.app.state.db_pool

        # 構建查詢條件
        conditions = []
        params = []
        param_count = 0

        if form_id:
            param_count += 1
            conditions.append(f"fs.form_id = ${param_count}")
            params.append(form_id)

        if vendor_id:
            param_count += 1
            conditions.append(f"fs.vendor_id = ${param_count}")
            params.append(vendor_id)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        async with db_pool.acquire() as conn:
            # 查詢提交記錄（含表單名稱和業者名稱）
            param_count += 1
            limit_param = f"${param_count}"
            param_count += 1
            offset_param = f"${param_count}"
            params.extend([limit, offset])

            rows = await conn.fetch(f"""
                SELECT
                    fs.id,
                    fs.form_id,
                    fsc.form_name,
                    fs.user_id,
                    fs.vendor_id,
                    v.name as vendor_name,
                    fs.submitted_data,
                    fs.submitted_at,
                    fs.status,
                    fs.notes,
                    fs.updated_at,
                    fs.updated_by,
                    fses.trigger_question
                FROM form_submissions fs
                LEFT JOIN form_schemas fsc ON fs.form_id = fsc.form_id
                LEFT JOIN vendors v ON fs.vendor_id = v.id
                LEFT JOIN form_sessions fses ON fs.form_session_id = fses.id
                {where_clause}
                ORDER BY fs.submitted_at DESC
                LIMIT {limit_param} OFFSET {offset_param}
            """, *params)

            # 查詢總數
            count_params = params[:-2]  # 移除 limit 和 offset
            total = await conn.fetchval(f"""
                SELECT COUNT(*)
                FROM form_submissions fs
                {where_clause}
            """, *count_params)

        return {
            "items": [dict(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢表單提交記錄失敗: {str(e)}")


@router.patch("/form-submissions/{submission_id}")
async def update_form_submission(
    request: Request,
    submission_id: int,
    update_data: FormSubmissionUpdate
):
    """
    更新表單提交的狀態和備註

    - **submission_id**: 提交記錄ID
    - **status**: 狀態（pending, processing, completed, rejected）
    - **notes**: 備註說明
    - **updated_by**: 更新者
    """
    try:
        db_pool = request.app.state.db_pool

        # 驗證狀態值
        valid_statuses = ['pending', 'processing', 'completed', 'rejected']
        if update_data.status and update_data.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"無效的狀態值，有效值為：{', '.join(valid_statuses)}"
            )

        # 建立更新語句
        updates = []
        params = []
        param_count = 0

        if update_data.status is not None:
            param_count += 1
            updates.append(f"status = ${param_count}")
            params.append(update_data.status)

        if update_data.notes is not None:
            param_count += 1
            updates.append(f"notes = ${param_count}")
            params.append(update_data.notes)

        if update_data.updated_by is not None:
            param_count += 1
            updates.append(f"updated_by = ${param_count}")
            params.append(update_data.updated_by)

        if not updates:
            raise HTTPException(status_code=400, detail="沒有提供要更新的欄位")

        updates.append("updated_at = NOW()")

        param_count += 1
        params.append(submission_id)

        query = f"""
            UPDATE form_submissions
            SET {', '.join(updates)}
            WHERE id = ${param_count}
            RETURNING
                id,
                form_id,
                user_id,
                vendor_id,
                submitted_data,
                submitted_at,
                status,
                notes,
                updated_at,
                updated_by
        """

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        if not row:
            raise HTTPException(status_code=404, detail=f"找不到提交記錄: {submission_id}")

        return dict(row)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新提交記錄失敗: {str(e)}")


# ============================================================
# Helper Functions
# ============================================================

def _validate_fields(fields: List[FormField]):
    """驗證欄位定義"""
    if not fields:
        raise HTTPException(status_code=400, detail="表單至少需要一個欄位")

    field_names = set()
    for field in fields:
        # 檢查欄位名稱不重複
        if field.field_name in field_names:
            raise HTTPException(
                status_code=400,
                detail=f"欄位名稱重複: {field.field_name}"
            )
        field_names.add(field.field_name)

        # 檢查 select 類型必須有 options
        if field.field_type == "select" and not field.options:
            raise HTTPException(
                status_code=400,
                detail=f"欄位 {field.field_name} 的類型為 select，必須提供 options"
            )

        # 檢查欄位類型有效
        valid_types = ["text", "textarea", "select", "multiselect", "number", "email", "date"]
        if field.field_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"欄位 {field.field_name} 的類型 {field.field_type} 無效，有效類型：{valid_types}"
            )
